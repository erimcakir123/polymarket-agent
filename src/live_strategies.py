"""live_strategies.py -- Live-cycle entry strategies extracted from agent.py.

Contains LiveStrategies class with:
  - light_cooldown_ready / set_light_cooldown: per-strategy cooldown helpers
  - get_held_event_ids: dedup helper
  - check_exposure_limit: exposure guard
  - check_farming_reentry: 3-tier re-entry from pool (no AI cost)
  - check_live_dip: favorite price-drop entry
  - check_live_momentum: score-based probability re-estimation
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import requests

from src.models import effective_price
from src.reentry_farming import check_reentry
from src.risk_manager import exceeds_exposure_limit, confidence_position_size

logger = logging.getLogger(__name__)

# Light-cycle cooldowns: strategy_name → ticks before next run (1 tick = 5s)
_LIGHT_COOLDOWNS = {
    "live_dip": 60,        # 5 min (60 × 5s)
    "momentum": 36,        # 3 min (36 × 5s)
    "farming_reentry": 24, # 2 min (24 × 5s)
    "scale_out": 12,       # 1 min (12 × 5s)
}


class LiveStrategies:
    """Live-cycle entry strategies. Delegates to Agent (ctx) for state access."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    # ── Light-cycle cooldown helpers ──────────────────────────────────────

    def light_cooldown_ready(self, strategy: str) -> bool:
        """Check if strategy is off cooldown in light cycle."""
        return self.ctx.light_cycle_count >= self.ctx._light_cooldowns.get(strategy, 0)

    def set_light_cooldown(self, strategy: str) -> None:
        """Set cooldown for strategy after action."""
        ticks = _LIGHT_COOLDOWNS.get(strategy, 0)
        self.ctx._light_cooldowns[strategy] = self.ctx.light_cycle_count + ticks

    def get_held_event_ids(self) -> set[str]:
        """Get event IDs of all currently held positions. Prevents same-event dual-side."""
        return {p.event_id for p in self.ctx.portfolio.positions.values()}

    # ── Exposure guard ─────────────────────────────────────────────────────

    def check_exposure_limit(self, candidate_size: float) -> bool:
        """Return True if adding candidate_size would exceed exposure limit."""
        return exceeds_exposure_limit(
            self.ctx.portfolio.positions, candidate_size,
            self.ctx.portfolio.bankroll, self.ctx.config.risk.max_exposure_pct,
        )

    # ── Farming re-entry ──────────────────────────────────────────────────

    def check_farming_reentry(self) -> bool:
        """Unified farming re-entry -- check pool for dip opportunities (no AI cost).

        Replaces old spike_reentry and scouted_reentry with a 3-tier system.
        Returns True if any re-entry was made.
        """
        self.ctx.reentry_pool.cleanup_expired(self.ctx.cycle_count)

        # Reset daily reentry count at midnight (UTC)
        now_utc = datetime.now(timezone.utc)
        if self.ctx._last_reentry_reset_date != now_utc.date():
            self.ctx._daily_reentry_count = 0
            self.ctx._last_reentry_reset_date = now_utc.date()

        if not self.ctx.reentry_pool.candidates:
            return False

        held_event_ids = {
            p.event_id for p in self.ctx.portfolio.positions.values()
            if p.event_id
        }

        # Check slot availability
        vs_reserved = self.ctx.config.volatility_swing.reserved_slots
        current_vs = sum(1 for p in self.ctx.portfolio.positions.values() if p.volatility_swing)
        current_normal = self.ctx.portfolio.active_position_count - current_vs

        entered = False
        for cid, candidate in list(self.ctx.reentry_pool.candidates.items()):
            # Cooldown check
            if self.ctx._exit_cooldowns.get(cid, 0) > self.ctx.cycle_count:
                continue

            # RE slot check -- max 3 concurrent re-entry positions
            RE_MAX_SLOTS = 3
            if self.ctx.portfolio.reentry_position_count >= RE_MAX_SLOTS:
                break  # No RE slots available

            # Fetch current price from Gamma
            try:
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"conditionId": cid}, timeout=10,
                )
                if resp.status_code != 200:
                    continue
                mkt_data = resp.json()
                if not mkt_data:
                    self.ctx.reentry_pool.remove(cid)
                    continue
                mkt = mkt_data[0] if isinstance(mkt_data, list) else mkt_data
                prices = json.loads(mkt.get("outcomePrices", '["0.5","0.5"]'))
                current_yes_price = float(prices[0])
            except (requests.RequestException, ValueError, IndexError, json.JSONDecodeError):
                continue

            # Update price history for stabilization tracking (use effective price for direction)
            eff_stab_price = effective_price(current_yes_price, candidate.direction)
            self.ctx.reentry_pool.update_price(cid, eff_stab_price)

            # Fetch match state for esports re-entry candidates
            re_match_state = self.ctx._match_states.get(cid)
            if not re_match_state and candidate.sport_tag.lower() in (
                "cs2", "csgo", "valorant", "lol", "dota2", "val"
            ):
                # Try to get live state from PandaScore for this candidate
                game_slug = self.ctx.esports.detect_game(candidate.question, [candidate.sport_tag])
                if game_slug:
                    team_a, team_b = self.ctx.esports._extract_team_names(candidate.question)
                    if team_a and team_b:
                        try:
                            re_match_state = self.ctx.esports.get_live_match_state(game_slug, team_a, team_b)
                        except Exception:
                            pass

            # Run decision logic
            decision = check_reentry(
                candidate=candidate,
                current_yes_price=current_yes_price,
                current_cycle=self.ctx.cycle_count,
                portfolio_positions=self.ctx.portfolio.positions,
                held_event_ids=held_event_ids,
                daily_reentry_count=self.ctx._daily_reentry_count,
                match_state=re_match_state,
            )

            if decision["action"] == "BLOCK":
                logger.debug("Farming re-entry BLOCK: %s | %s", candidate.slug[:35], decision["reason"])
                # All BLOCKs are permanent -> remove from pool
                self.ctx.reentry_pool.remove(cid)
                continue

            if decision["action"] == "WAIT":
                continue

            # --- ENTER ---
            direction = candidate.direction
            anchor_prob = candidate.anchor_probability
            size_mult = decision["size_mult"]

            # Calculate position size (confidence-based * tier multiplier)
            eff_price = effective_price(current_yes_price, direction)
            base_size = confidence_position_size(
                confidence=getattr(candidate, 'confidence', "B-"),
                bankroll=self.ctx.portfolio.bankroll,
                max_bet_usdc=self.ctx.config.risk.max_single_bet_usdc,
                max_bet_pct=self.ctx.config.risk.max_bet_pct,
                is_reentry=True,
            )
            size = base_size * size_mult

            if size < 5.0:
                continue  # Polymarket minimum

            # Profit protection cap
            if candidate.total_realized_profit > 0:
                max_risk = candidate.total_realized_profit * 0.50
                remaining_risk = max_risk - candidate.total_reentry_risk
                if remaining_risk <= 0:
                    logger.info("Farming skip (profit cap): %s", candidate.slug[:35])
                    continue
                size = min(size, remaining_risk)
                if size < 5.0:
                    continue

            token_id = candidate.token_id

            if self.check_exposure_limit(size):
                logger.info("SKIP exposure cap: would exceed %.0f%%", self.ctx.config.risk.max_exposure_pct * 100)
                continue

            result = self.ctx.executor.place_order(token_id, "BUY", eff_price, size)
            # Stale-price guard may reject (drift >5%) or adjust the fill price.
            if not result or result.get("status") == "error":
                logger.info("REENTRY order rejected: %s -- %s",
                            candidate.slug[:40], result.get("reason") if result else "no result")
                continue
            # Use executor's actual fill price (adjusted to live CLOB if needed).
            _fill = result.get("price", eff_price)
            shares = size / _fill if _fill > 0 else 0
            yes_price_entry = _fill if direction == "BUY_YES" else (1.0 - _fill)

            tier_num = decision["tier"]
            reentry_num = candidate.reentry_count + 1
            _is_lossy = candidate.exit_reason == "stop_loss"
            entry_reason = f"re_entry_t{tier_num}_sl" if _is_lossy else f"re_entry_t{tier_num}"
            _sl_count = (candidate.sl_reentry_count + 1) if _is_lossy else 0

            self.ctx.portfolio.add_position(
                cid, token_id, direction,
                yes_price_entry, size, shares, candidate.slug,
                "", confidence=candidate.confidence,
                anchor_probability=anchor_prob,
                question=candidate.question,
                end_date_iso=candidate.end_date_iso,
                match_start_iso=candidate.match_start_iso,
                scouted=candidate.was_scouted,
                sport_tag=candidate.sport_tag,
                event_id=candidate.event_id,
                entry_reason=entry_reason,
                number_of_games=candidate.number_of_games,
                sl_reentry_count=_sl_count,
            )

            # Record in pool
            self.ctx.reentry_pool.record_reentry(cid, size)
            self.ctx._daily_reentry_count += 1
            current_normal += 1

            self.ctx.trade_log.log({
                "market": candidate.slug, "action": f"FARMING_REENTRY_{direction}",
                "size": size, "price": eff_price,
                "edge": decision["edge"],
                "confidence": candidate.confidence,
                "mode": self.ctx.config.mode.value,
                "status": result.get("status", ""),
                "anchor_probability": anchor_prob,
                "reentry_tier": tier_num,
                "reentry_count": reentry_num,
            })

            logger.info(
                "FARMING RE-ENTRY T%d (#%d): %s | %s @ %.0fc | edge=%.1f%% | size=$%.0f (%.0f%%) | no AI",
                tier_num, reentry_num, candidate.slug[:35], direction,
                eff_price * 100, decision["edge"] * 100, size, size_mult * 100,
            )
            self.ctx.notifier.send(
                f"\U0001f504 *FARMING RE-ENTRY* T{tier_num} (#{reentry_num}) -- Cycle #{self.ctx.cycle_count}\n\n"
                f"{candidate.question}\n"
                f"Exit: `{candidate.last_exit_price:.3f}` -> Re-entry: `{eff_price:.3f}`\n"
                f"Edge: `{decision['edge']:.1%}` | Size: `${size:.0f}` ({size_mult:.0%})\n"
                f"Profit so far: `${candidate.total_realized_profit:.2f}`\n"
                f"_No AI call -- using saved analysis_"
            )
            self.ctx.bets_since_approval += 1
            entered = True

        return entered

    # ── Live dip & momentum ─────────────────────────────────────────────

    def check_live_dip(self, held_events: set[str] | None = None,
                       fresh_markets: list | None = None) -> bool:
        """Enter when favorite's market price drops 10%+ (no ESPN, pure price).

        Called from light cycle with cooldown. Uses cached _pre_match_prices.
        Accepts pre-fetched fresh_markets to avoid redundant scanner calls.
        Returns True if any entry was made.
        """
        if fresh_markets is None:
            fresh_markets = self.ctx.scanner.fetch()
        if not fresh_markets:
            return False

        bankroll = self.ctx.wallet.get_usdc_balance() if self.ctx.wallet else self.ctx.portfolio.bankroll
        cfg = self.ctx.config.live_momentum  # Uses live_momentum config for max_concurrent
        min_drop_pct = 0.10

        # Count current live_dip positions
        dip_count = sum(1 for p in self.ctx.portfolio.positions.values()
                        if getattr(p, "entry_reason", "") == "live_dip")
        if dip_count >= cfg.max_concurrent:
            return False

        # Use provided held_events or build from portfolio
        _dip_existing_eids = held_events if held_events is not None else (
            {getattr(p, "event_id", "") for p in self.ctx.portfolio.positions.values()} - {""}
        )

        entered = False
        for m in fresh_markets:
            if self.ctx.portfolio.active_position_count >= self.ctx.config.risk.max_positions:
                break
            if m.condition_id in self.ctx.portfolio.positions:
                continue
            if self.ctx.blacklist.is_blocked(m.condition_id, self.ctx.cycle_count):
                continue
            if m.condition_id in self.ctx._exited_markets:
                continue

            # Moneyline filter -- skip tournament/advance/qualify props
            _q = (getattr(m, "question", "") or "").lower()
            _slug = (m.slug or "").lower()
            _non_ml = ("advance", "qualify", "championship", "finalist",
                       "make the playoffs", "win the title", "win the tournament",
                       "win the cup", "win the league", "win the series",
                       "relegated", "promoted")
            if any(kw in _q or kw in _slug for kw in _non_ml):
                continue

            # Block non-moneyline markets (Top10, spread, totals, props)
            _smt = getattr(m, "sports_market_type", "") or ""
            if _smt and _smt.lower() != "moneyline":
                continue

            # Same-event dual-side check for live_dip (uses held_events from caller)
            _dip_eid = getattr(m, "event_id", "") or ""
            if _dip_eid and _dip_eid in _dip_existing_eids:
                logger.info("SKIP same-event dedup: %s", _dip_eid)
                continue

            pre_match = self.ctx._pre_match_prices.get(m.condition_id)
            if not pre_match:
                continue

            current_yes = m.yes_price
            if current_yes <= 0:
                continue

            # Check if favorite dropped 10%+
            direction = None
            drop_pct = 0.0

            if pre_match > 0.65:
                # YES was favorite, check if YES dropped
                drop = pre_match - current_yes
                drop_pct = drop / pre_match
                if drop_pct >= min_drop_pct:
                    direction = "BUY_YES"
            elif pre_match < 0.35:
                # NO was favorite, check if NO dropped (YES rose)
                no_pre = 1 - pre_match
                no_current = 1 - current_yes
                drop = no_pre - no_current
                drop_pct = drop / no_pre if no_pre > 0 else 0
                if drop_pct >= min_drop_pct:
                    direction = "BUY_NO"

            if not direction:
                continue

            # Size using confidence-based system
            size = confidence_position_size(
                confidence="B-", bankroll=bankroll,
                max_bet_usdc=self.ctx.config.risk.max_single_bet_usdc,
                max_bet_pct=self.ctx.config.risk.max_bet_pct,
            )
            if size < 5.0:
                continue

            # Get token_id
            if direction == "BUY_YES":
                token_id = m.yes_token_id
                price = current_yes
            else:
                token_id = m.no_token_id
                price = 1 - current_yes

            if not token_id:
                continue

            if self.check_exposure_limit(size):
                logger.info("SKIP exposure cap: would exceed %.0f%%", self.ctx.config.risk.max_exposure_pct * 100)
                continue

            result = self.ctx.executor.place_order(token_id, "BUY", price, size)
            if not result or result.get("status") == "error":
                continue

            # Use executor's actual fill (stale-price guard may have adjusted it).
            _fill = result.get("price", price)
            shares = size / _fill if _fill > 0 else 0
            _yes_entry = _fill if direction == "BUY_YES" else (1.0 - _fill)
            self.ctx.portfolio.add_position(
                m.condition_id, token_id, direction,
                _yes_entry, size, shares, m.slug,
                "", confidence="B-",
                anchor_probability=max(0.01, min(0.99, pre_match)),
                entry_reason="live_dip",
                sport_tag=getattr(m, "sport_tag", "") or "",
                event_id=getattr(m, "event_id", "") or "",
                end_date_iso=getattr(m, "end_date_iso", "") or "",
                match_start_iso=getattr(m, "match_start_iso", "") or "",
            )
            dip_count += 1
            entered = True

            self.ctx.trade_log.log({
                "market": m.slug, "action": f"LIVE_DIP_{direction}",
                "size": size, "price": price,
                "pre_match_price": pre_match,
                "drop_pct": round(drop_pct, 3),
                "mode": self.ctx.config.mode.value,
            })
            logger.info(
                "LIVE DIP: %s | %s | pre=%.2f now=%.2f drop=%.0f%% | size=$%.0f",
                m.slug[:40], direction, pre_match, current_yes, drop_pct * 100, size,
            )
            self.ctx.notifier.send(
                f"📉 *LIVE DIP*: {m.slug[:40]}\n"
                f"Entry {direction} @ {price:.0%} | LIVE\n\n"
                f"📊 Pre-match: {pre_match:.0%} -> Now: {current_yes:.0%} (drop {drop_pct:.0%})\n"
                f"💰 Size: ${size:.0f}"
            )
        return entered

    def check_live_momentum(self, held_events: set[str] | None = None,
                            fresh_markets: list | None = None,
                            match_states: dict | None = None) -> bool:
        """Score-based probability re-estimation for live matches.

        Called from light cycle with cooldown. Accepts pre-fetched fresh_markets
        to avoid redundant scanner calls.
        Returns True if any entry was made.
        """
        if not match_states:
            return False
        from src.live_momentum import detect_momentum_opportunity, calculate_score_adjusted_probability

        cfg = self.ctx.config.live_momentum
        if not cfg.enabled:
            return False

        # Use provided fresh_markets or fetch internally
        if fresh_markets is None:
            fresh_markets = self.ctx.scanner.fetch()
        bankroll = self.ctx.wallet.get_usdc_balance() if self.ctx.wallet else self.ctx.portfolio.bankroll

        # Use provided held_events or build from portfolio
        _mom_held_eids = held_events if held_events is not None else (
            {getattr(p, "event_id", "") for p in self.ctx.portfolio.positions.values()} - {""}
        )

        momentum_count = sum(1 for p in self.ctx.portfolio.positions.values()
                             if getattr(p, "entry_reason", "") == "momentum")

        entered = False
        for cid, state in match_states.items():
            if not state:
                continue

            sport_tag = state.get("sport_tag", "")

            # Mode B: Update existing positions with score-adjusted probability
            if cid in self.ctx.portfolio.positions:
                pos = self.ctx.portfolio.positions[cid]
                adjusted = calculate_score_adjusted_probability(
                    pos.anchor_probability, state, sport_tag, pos.direction,
                )
                if adjusted is not None:
                    pos.anchor_probability = adjusted
                continue

            # Mode A: New entry if edge >= 6%
            if self.ctx.portfolio.active_position_count >= self.ctx.config.risk.max_positions:
                continue
            if momentum_count >= cfg.max_concurrent:
                continue
            if self.ctx.blacklist.is_blocked(cid, self.ctx.cycle_count):
                continue
            if cid in self.ctx._exited_markets:
                continue

            # Need pre-match price as probability baseline
            pre_match = self.ctx._pre_match_prices.get(cid)
            if not pre_match:
                continue

            # Find market in fresh_markets
            market = None
            if fresh_markets:
                for m in fresh_markets:
                    if m.condition_id == cid:
                        market = m
                        break
            if not market:
                continue

            # Same-event dual-side dedup
            _mom_eid = getattr(market, "event_id", "") or ""
            if _mom_eid and _mom_eid in _mom_held_eids:
                logger.info("SKIP same-event dedup: %s", _mom_eid)
                continue

            # Try both directions
            for direction in ("BUY_YES", "BUY_NO"):
                signal = detect_momentum_opportunity(
                    cid, pre_match, market.yes_price,
                    state, sport_tag, direction, min_edge=cfg.min_edge,
                )
                if not signal:
                    continue

                size = confidence_position_size(
                    confidence="B-", bankroll=bankroll,
                    max_bet_usdc=self.ctx.config.risk.max_single_bet_usdc,
                    max_bet_pct=cfg.bet_pct,
                )
                if size < 5.0:
                    continue

                if direction == "BUY_YES":
                    token_id = market.yes_token_id
                    price = market.yes_price
                else:
                    token_id = market.no_token_id
                    price = 1 - market.yes_price

                if not token_id:
                    continue

                if self.check_exposure_limit(size):
                    logger.info("SKIP exposure cap: would exceed %.0f%%", self.ctx.config.risk.max_exposure_pct * 100)
                    continue

                result = self.ctx.executor.place_order(token_id, "BUY", price, size)
                if not result or result.get("status") == "error":
                    continue

                # Use executor's actual fill (stale-price guard may have adjusted it).
                _fill = result.get("price", price)
                shares = size / _fill if _fill > 0 else 0
                _yes_entry = _fill if direction == "BUY_YES" else (1.0 - _fill)
                self.ctx.portfolio.add_position(
                    cid, token_id, direction,
                    _yes_entry, size, shares, market.slug,
                    "", confidence="B-",
                    anchor_probability=signal.adjusted_prob,
                    entry_reason="momentum",
                    sport_tag=sport_tag,
                    event_id=getattr(market, "event_id", ""),
                    end_date_iso=getattr(market, "end_date_iso", ""),
                    match_start_iso=getattr(market, "match_start_iso", "") or "",
                )
                momentum_count += 1
                entered = True

                self.ctx.trade_log.log({
                    "market": market.slug, "action": f"MOMENTUM_{direction}",
                    "size": size, "price": price,
                    "adjusted_prob": signal.adjusted_prob,
                    "edge": signal.edge,
                    "score_diff": signal.score_diff,
                    "mode": self.ctx.config.mode.value,
                })
                logger.info(
                    "MOMENTUM: %s | %s | edge=%.1f%% | adj_prob=%.1f%% | size=$%.0f",
                    market.slug[:40], direction, signal.edge * 100, signal.adjusted_prob * 100, size,
                )
                self.ctx.notifier.send(
                    f"⚡ *MOMENTUM*: {market.slug[:40]}\n"
                    f"Entry {direction} @ {price:.0%} | LIVE\n\n"
                    f"📊 Edge: {signal.edge:.1%} | Score: {signal.score_diff}\n"
                    f"💰 Size: ${size:.0f}"
                )
                break  # Only one direction per market
        return entered
