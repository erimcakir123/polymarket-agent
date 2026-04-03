from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.models import effective_price

logger = logging.getLogger(__name__)


class PriceUpdater:
    """Handles price updates, market resolution, and match state tracking."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    # ------------------------------------------------------------------
    # fetch_match_states
    # ------------------------------------------------------------------
    def fetch_match_states(self) -> dict[str, dict]:
        """Fetch live match states for all esports positions from PandaScore.

        Returns dict of condition_id -> match_state dict.
        Rate-limited to once per 30 seconds.
        """
        now = time.time()
        if now - self.ctx._last_match_state_fetch < 30:
            return self.ctx._match_states  # Return cached

        if not self.ctx.esports.available:
            return {}

        states: dict[str, dict] = {}
        # Group esports positions by game slug
        esports_positions = [
            (cid, pos) for cid, pos in self.ctx.portfolio.positions.items()
            if pos.category == "esports" and pos.live_on_clob
        ]
        if not esports_positions:
            self.ctx._match_states = {}
            return {}

        # Also check reentry pool for esports candidates
        esports_games_checked: set[str] = set()

        for cid, pos in esports_positions:
            game_slug = self.ctx.esports.detect_game(pos.question, [pos.sport_tag])
            if not game_slug:
                continue

            team_a, team_b = self.ctx.esports._extract_team_names(pos.question)
            if not team_a or not team_b:
                continue

            cache_key = f"{game_slug}:{team_a}:{team_b}"
            if cache_key in esports_games_checked:
                continue
            esports_games_checked.add(cache_key)

            try:
                ms = self.ctx.esports.get_live_match_state(game_slug, team_a, team_b)
                if ms:
                    states[cid] = ms
                    # Update position fields
                    pos.match_score = ms.get("map_score", "")
                    pos.match_period = f"{ms.get('map_number', '?')}/{ms.get('total_maps', '?')}"
            except Exception as e:
                logger.debug("Match state fetch error for %s: %s", pos.slug[:30], e)

        self.ctx._match_states = states
        self.ctx._last_match_state_fetch = now
        if states:
            logger.info("Fetched %d live match states from PandaScore", len(states))
        return states

    # ------------------------------------------------------------------
    # _lookup_scout_match_time
    # ------------------------------------------------------------------
    def _lookup_scout_match_time(self, slug: str, question: str) -> str:
        """Look up match start time from scout queue (ESPN/PandaScore data).

        Returns ISO timestamp string or empty string if not found.
        """
        scout = getattr(self.ctx, "scout", None)
        if not scout:
            return ""
        q_lower = (question or "").lower()
        s_lower = (slug or "").lower()
        for entry in scout._queue.values():
            mt = entry.get("match_time", "")
            if not mt:
                continue
            team_a = entry.get("team_a", "").lower()
            team_b = entry.get("team_b", "").lower()
            abbrev_a = (entry.get("abbrev_a") or "").lower()
            abbrev_b = (entry.get("abbrev_b") or "").lower()
            if not team_a or not team_b:
                continue
            # Layer 1: Abbreviation in slug tokens
            slug_tokens = set(s_lower.split("-"))
            if abbrev_a and abbrev_b and abbrev_a in slug_tokens and abbrev_b in slug_tokens:
                return mt
            # Layer 2: Full name in question or slug
            a_in = team_a in q_lower or team_a in s_lower
            b_in = team_b in q_lower or team_b in s_lower
            if a_in and b_in:
                return mt
            # Layer 3: Short name in question or slug
            short_a = (entry.get("short_a") or "").lower()
            short_b = (entry.get("short_b") or "").lower()
            if short_a and short_b:
                if (short_a in q_lower or short_a in s_lower) and (short_b in q_lower or short_b in s_lower):
                    return mt
        return ""

    # ------------------------------------------------------------------
    # update_position_prices
    # ------------------------------------------------------------------
    def update_position_prices(self) -> bool:
        """Fetch current YES prices for all open positions via slug query.

        Uses slug-based Gamma query which returns correct prices AND event data
        (startTime, live, score, period). conditionId queries return stale/wrong data.
        Returns True if any live positions found.
        """
        if not self.ctx.portfolio.positions:
            return False
        stale_cids = []
        reentry_resolve_exits = []
        pending_resolve_exits = []
        has_live_clob = False
        for cid, pos in list(self.ctx.portfolio.positions.items()):
            try:
                if not pos.slug:
                    logger.debug("No slug for position %s, skipping price update", cid[:16])
                    continue
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"slug": pos.slug}, timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    logger.warning("Market not found on Gamma: %s (%s..)", pos.slug, cid[:16])
                    stale_cids.append(cid)
                    continue

                market_data = data[0] if isinstance(data, list) else data
                prices = json.loads(market_data.get("outcomePrices", '["0.5","0.5"]'))
                new_yes_price = float(prices[0])
                no_price = float(prices[1]) if len(prices) > 1 else 1 - new_yes_price
                is_closed = market_data.get("closed", False)

                events = market_data.get("events", [])
                if events:
                    ev = events[0]
                    ev_start = ev.get("startTime")
                    ev_live = ev.get("live")
                    ev_ended = ev.get("ended")
                    ev_score = ev.get("score") or ""
                    ev_period = ev.get("period") or ""

                    _start_usable = ev_start and ev_start != pos.end_date_iso
                    if _start_usable and not pos.match_start_iso:
                        pos.match_start_iso = ev_start
                        logger.info("Match start from Gamma event: %s -> %s",
                                    pos.slug[:35], ev_start)

                    if ev_live is not None:
                        pos.match_live = bool(ev_live)
                        pos.live_on_clob = bool(ev_live)
                        if ev_live:
                            has_live_clob = True
                    if ev_ended is not None:
                        pos.match_ended = bool(ev_ended)
                    if ev_score:
                        pos.match_score = ev_score
                    if ev_period:
                        pos.match_period = ev_period

                # Scout queue fallback for match_start_iso (outside events
                # block so it runs even when Gamma returns no events).
                _needs_scout = (not pos.match_start_iso
                                or pos.match_start_iso == pos.end_date_iso)
                if _needs_scout:
                    _scout_time = self._lookup_scout_match_time(pos.slug, pos.question)
                    if _scout_time and _scout_time != pos.match_start_iso:
                        pos.match_start_iso = _scout_time
                        logger.info("Match start from scout queue: %s -> %s",
                                    pos.slug[:35], _scout_time)

                if is_closed:
                    if new_yes_price >= 0.95:
                        yes_won = True
                    elif no_price >= 0.95:
                        yes_won = False
                    elif 0.45 <= new_yes_price <= 0.55 and 0.45 <= no_price <= 0.55:
                        logger.info("VOID/DRAW: %s | prices=[%.2f, %.2f] -- exiting as refund",
                                    pos.slug[:40], new_yes_price, no_price)
                        self.ctx.portfolio.update_price(cid, new_yes_price)
                        self.ctx.exit_executor.exit_position(cid, "resolved_void")
                        continue
                    elif new_yes_price <= 0.05 and no_price <= 0.05:
                        if events and events[0].get("ended"):
                            clob_price = self.get_clob_midpoint(pos.token_id)
                            if clob_price is not None and clob_price > 0.01:
                                if pos.direction == "BUY_NO":
                                    self.ctx.portfolio.update_price(cid, 1.0 - clob_price)
                                else:
                                    self.ctx.portfolio.update_price(cid, clob_price)
                                has_live_clob = True
                                continue
                        if not pos.pending_resolution:
                            self.ctx.portfolio.mark_pending_resolution(cid)
                        logger.info("Closed and awaiting resolution: %s (prices=[%.2f, %.2f])",
                                    pos.slug, new_yes_price, no_price)
                        continue
                    else:
                        match_likely_ended = False
                        if pos.match_start_iso:
                            try:
                                start_dt = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
                                elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds() / 60
                                bo = pos.number_of_games or 0
                                est_duration = 180 if bo >= 5 else 120 if bo >= 3 else 90
                                if elapsed > est_duration:
                                    match_likely_ended = True
                            except (ValueError, TypeError):
                                pass

                        if match_likely_ended:
                            self.ctx.portfolio.update_price(cid, new_yes_price)
                            if not pos.pending_resolution:
                                self.ctx.portfolio.mark_pending_resolution(cid)
                                logger.info("Match likely ended (elapsed > est duration): %s -- marking pending",
                                            pos.slug[:40])
                        else:
                            self.ctx.portfolio.update_price(cid, new_yes_price)
                        continue

                    won = (pos.direction == "BUY_YES" and yes_won) or \
                          (pos.direction == "BUY_NO" and not yes_won)
                    resolution_price = 1.0 if yes_won else 0.0
                    self.ctx.portfolio.update_price(cid, resolution_price)
                    pnl = pos.shares - pos.size_usdc if won else -pos.size_usdc
                    logger.info("RESOLVED: %s | %s | %s | PnL=$%.2f",
                                pos.slug, pos.direction, "WIN" if won else "LOSS", pnl)
                    self.ctx.exit_executor.exit_position(cid, f"resolved_{'win' if won else 'loss'}")
                else:
                    self.ctx.portfolio.update_price(cid, new_yes_price)
                    if not events or events[0].get("live") is None:
                        pos.live_on_clob = PriceUpdater.estimate_match_live(
                            pos.slug, pos.question, pos.end_date_iso,
                            match_start_iso=pos.match_start_iso)
                        if pos.live_on_clob:
                            has_live_clob = True
                    if getattr(pos, "entry_reason", "").startswith("re_entry"):
                        eff_p = effective_price(new_yes_price, pos.direction)
                        if eff_p >= 0.90:
                            logger.info("RE-ENTRY RESOLVE GUARD (WIN): %s @ %.0f%% -- exiting before resolve",
                                        pos.slug[:35], eff_p * 100)
                            reentry_resolve_exits.append((cid, "re_entry_resolve_win"))
                            continue
                        elif eff_p <= 0.10:
                            logger.info("RE-ENTRY RESOLVE GUARD (LOSS): %s @ %.0f%% -- exiting before resolve",
                                        pos.slug[:35], eff_p * 100)
                            reentry_resolve_exits.append((cid, "re_entry_resolve_loss"))
                            continue

                    if not pos.pending_resolution and (new_yes_price >= 0.95 or new_yes_price <= 0.05):
                        match_ended = getattr(pos, 'match_ended', False)
                        event_ended = False
                        if events:
                            event_ended = bool(events[0].get("ended", False))
                        if match_ended or event_ended:
                            self.ctx.portfolio.mark_pending_resolution(cid)
                    if pos.pending_resolution and not is_closed:
                        event_still_live = events and not events[0].get("ended", False)
                        if event_still_live or not events:
                            pos.pending_resolution = False
                            logger.info("Un-pending: %s -- market still open, event not ended", pos.slug[:40])
                    if pos.pending_resolution:
                        pos.live_on_clob = False
                        pos.match_live = False
                        if new_yes_price >= 0.97 or new_yes_price <= 0.03:
                            _yes_won = new_yes_price >= 0.97
                            _won = (pos.direction == "BUY_YES" and _yes_won) or \
                                   (pos.direction == "BUY_NO" and not _yes_won)
                            _res_price = 1.0 if _yes_won else 0.0
                            self.ctx.portfolio.update_price(cid, _res_price)
                            _pnl = pos.shares - pos.size_usdc if _won else -pos.size_usdc
                            logger.info("RESOLVED (pending): %s | %s | %s | PnL=$%.2f",
                                        pos.slug[:40], pos.direction, "WIN" if _won else "LOSS", _pnl)
                            pending_resolve_exits.append((cid, f"resolved_{'win' if _won else 'loss'}"))
                            continue
            except Exception as e:
                logger.debug("Price update failed for %s: %s", pos.slug[:30], e)

        for cid in stale_cids:
            self.ctx._pre_match_prices.pop(cid, None)
            pos = self.ctx.portfolio.remove_position(cid)
            if pos:
                logger.warning("Removed stale position: %s (not on Polymarket)", pos.slug)
                self.ctx.trade_log.log({
                    "market": pos.slug, "action": "REMOVED",
                    "reason": "stale: market not found on Gamma API",
                    "mode": self.ctx.config.mode.value,
                })
        for cid, reason in reentry_resolve_exits:
            self.ctx.exit_executor.exit_position(cid, reason)
            self.ctx.reentry_pool.remove(cid)
        for cid, reason in pending_resolve_exits:
            self.ctx.exit_executor.exit_position(cid, reason)

        if self.ctx.outcome_tracker.tracked_count > 0:
            self.check_tracked_outcomes()

        self.ctx.portfolio.save_prices_to_disk()
        return has_live_clob

    # ------------------------------------------------------------------
    # sync_ws_subscriptions
    # ------------------------------------------------------------------
    def sync_ws_subscriptions(self) -> None:
        token_ids = [pos.token_id for pos in self.ctx.portfolio.positions.values()]
        self.ctx.ws_feed.sync_subscriptions(token_ids)

    # ------------------------------------------------------------------
    # check_price_drift_reanalysis
    # ------------------------------------------------------------------
    def check_price_drift_reanalysis(self) -> None:
        threshold = self.ctx.config.risk.price_drift_reanalysis_pct
        for cid, pos in self.ctx.portfolio.positions.items():
            if pos.current_price <= 0.001:
                continue
            eff_entry = effective_price(pos.entry_price, pos.direction)
            eff_current = effective_price(pos.current_price, pos.direction)
            drift = abs(eff_current - eff_entry) / max(eff_entry, 0.01)
            if drift >= threshold:
                logger.info(
                    "Price drift detected: %s | entry=%.0f¢ now=%.0f¢ drift=%.1f%%",
                    pos.slug, eff_entry * 100, eff_current * 100, drift * 100,
                )

    # ------------------------------------------------------------------
    # check_resolved_markets
    # ------------------------------------------------------------------
    def check_resolved_markets(self) -> None:
        """Check if any past predictions have resolved. Log outcome for calibration."""
        cal_path = Path("logs/calibration.jsonl")
        cal_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing predictions that haven't been resolved yet
        pred_path = Path("logs/predictions.jsonl")
        if not pred_path.exists():
            return

        unresolved = []
        try:
            lines = pred_path.read_text(encoding="utf-8").strip().split("\n")
        except Exception:
            return

        for line in lines:
            if not line.strip():
                continue
            try:
                pred = json.loads(line)
            except json.JSONDecodeError:
                continue

            cid = pred.get("condition_id", "")
            if not cid:
                continue

            # Check if market is resolved
            try:
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"conditionId": cid}, timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    unresolved.append(line)
                    continue

                market = data[0]
                # Must be truly resolved (not just closed for trading)
                # Gamma sets resolved=true only when outcome is final
                if not market.get("resolved", False):
                    unresolved.append(line)
                    continue

                # Market resolved -- log calibration result
                outcome_prices = json.loads(market.get("outcomePrices", '["0.5","0.5"]'))
                yes_price = float(outcome_prices[0])
                # Resolved markets have prices at exactly 1.0 or 0.0 (or very close)
                if 0.02 < yes_price < 0.98:
                    # Not truly resolved -- prices still mid-range
                    unresolved.append(line)
                    continue
                resolved_yes = yes_price > 0.50  # YES won
                ai_prob = pred.get("ai_probability", 0.5)
                ai_was_right = (ai_prob > 0.5 and resolved_yes) or (ai_prob <= 0.5 and not resolved_yes)
                error = abs(ai_prob - (1.0 if resolved_yes else 0.0))

                result = {
                    "condition_id": cid,
                    "question": pred.get("question", ""),
                    "ai_probability": ai_prob,
                    "market_price_at_trade": pred.get("market_price", 0),
                    "direction": pred.get("direction", ""),
                    "resolved_yes": resolved_yes,
                    "ai_correct": ai_was_right,
                    "prediction_error": round(error, 3),
                    "category": pred.get("category", ""),
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                }
                with open(cal_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result) + "\n")
                logger.info(
                    "Calibration: %s | AI=%.0f%% | Result=%s | %s",
                    pred.get("question", "")[:40],
                    ai_prob * 100,
                    "YES" if resolved_yes else "NO",
                    "CORRECT" if ai_was_right else "WRONG",
                )
            except Exception as e:
                logger.debug("Calibration check failed for %s: %s", cid[:20], e)
                unresolved.append(line)

        # Rewrite predictions file atomically (write to temp, then rename)
        if len(unresolved) < len(lines):
            tmp_path = pred_path.with_suffix(".tmp")
            tmp_path.write_text(
                "\n".join(unresolved) + "\n" if unresolved else "",
                encoding="utf-8",
            )
            tmp_path.replace(pred_path)

    # ------------------------------------------------------------------
    # get_clob_midpoint
    # ------------------------------------------------------------------
    def get_clob_midpoint(self, token_id: str) -> float | None:
        try:
            resp = requests.get(
                "https://clob.polymarket.com/midpoint",
                params={"token_id": token_id}, timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            mid = float(data.get("mid", 0))
            return mid if mid > 0 else None
        except Exception as e:
            logger.debug("CLOB midpoint failed for %s: %s", token_id[:16], e)
            return None

    # ------------------------------------------------------------------
    # estimate_match_live (static)
    # ------------------------------------------------------------------
    @staticmethod
    def estimate_match_live(slug: str, question: str, end_date_iso: str,
                            match_start_iso: str = "") -> bool:
        now = datetime.now(timezone.utc)
        if match_start_iso:
            try:
                start_dt = datetime.fromisoformat(
                    match_start_iso.replace("Z", "+00:00")
                    .replace(" ", "T")
                )
                if now < start_dt:
                    return False
                minutes_since_start = (now - start_dt).total_seconds() / 60
                if minutes_since_start <= 5:
                    return False
                return True
            except (ValueError, TypeError):
                pass
        if not end_date_iso:
            return False
        try:
            end_dt = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
            hours_to_end = (end_dt - now).total_seconds() / 3600
        except (ValueError, TypeError):
            return False
        if hours_to_end <= 0:
            return True
        duration_h = PriceUpdater.match_duration(slug, question)
        return hours_to_end <= duration_h

    # ------------------------------------------------------------------
    # match_duration (static)
    # ------------------------------------------------------------------
    @staticmethod
    def match_duration(slug: str, question: str) -> float:
        text = (slug + " " + question).lower()
        if "bo5" in text or "best of 5" in text:
            if "dota" in text:
                return 3.25
            return 2.75
        if "bo1" in text:
            return 0.75
        if "bo3" in text or "best of 3" in text:
            if "dota" in text:
                return 2.0
            if any(k in text for k in ("lol:", "league")):
                return 1.5
            return 1.75
        if any(k in text for k in ("cs2", "cs:", "csgo", "counter-strike", "valorant")):
            return 1.75
        if any(k in text for k in ("lol:", "league")):
            return 1.5
        if "dota" in text:
            return 2.0
        if any(k in text for k in ("nba", "cbb", "ncaa basket")):
            return 2.25
        if any(k in text for k in ("nfl", "football")):
            return 3.25
        if any(k in text for k in ("nhl", "hockey")):
            return 2.33
        if any(k in text for k in ("epl", "ucl", "uel", "soccer", "fc ", "united")):
            return 2.0
        if any(k in text for k in ("mlb", "baseball")):
            return 2.75
        return 2.0

    # ------------------------------------------------------------------
    # check_tracked_outcomes
    # ------------------------------------------------------------------
    def check_tracked_outcomes(self) -> None:
        """Check exited markets for resolution -- no AI cost, just Gamma API."""
        from src.match_outcomes import log_outcome as _log_resolved
        tracked_cids = self.ctx.outcome_tracker.tracked_condition_ids
        if not tracked_cids:
            return

        gamma_events: dict[str, dict] = {}
        for cid in list(tracked_cids):
            tm = self.ctx.outcome_tracker._tracked.get(cid)
            if not tm:
                continue
            try:
                resp = requests.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={"slug": tm.slug}, timeout=10,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if not data:
                    continue
                md = data[0] if isinstance(data, list) else data
                prices = json.loads(md.get("outcomePrices", '["0.5","0.5"]'))
                gamma_events[cid] = {
                    "yes_price": float(prices[0]),
                    "closed": md.get("closed", False),
                    "ended": (md.get("events") or [{}])[0].get("ended", False),
                }
            except Exception:
                continue

        resolved = self.ctx.outcome_tracker.check_resolutions(gamma_events)
        for outcome in resolved:
            # Log resolved outcome to match_outcomes.jsonl
            try:
                _log_resolved(
                    slug=outcome["slug"],
                    question=outcome.get("question", ""),
                    direction=outcome["direction"],
                    ai_probability=outcome["ai_probability"],
                    confidence=outcome["confidence"],
                    entry_price=outcome["entry_price"],
                    exit_price=outcome["exit_price"],
                    exit_reason=f"post_exit_{outcome['exit_reason']}",
                    pnl=outcome["hypothetical_pnl"],
                    size=outcome["size"],
                    sport_tag=outcome.get("sport_tag", ""),
                    entry_reason=outcome.get("entry_reason", ""),
                    scouted=outcome.get("scouted", False),
                    peak_pnl_pct=outcome.get("peak_pnl_pct", 0.0),
                    match_score=outcome.get("match_score", ""),
                    cycles_held=outcome.get("cycles_held", 0),
                    bookmaker_prob=outcome.get("bookmaker_prob", 0.0),
                )
            except Exception:
                pass

            # Auto-calibration check (every 50 resolved outcomes)
            try:
                from src.self_improve import auto_calibrate
                cal_result = auto_calibrate(logger=logger)
                if cal_result:
                    weaknesses = cal_result.get("weaknesses", [])
                    self.ctx.notifier.send(
                        f"\U0001f4ca *AUTO-CALIBRATION* -- {cal_result['resolved_count']} resolved\n\n"
                        f"Win rate: `{cal_result['overall_win_rate']:.0%}`\n"
                        f"Brier: `{cal_result['overall_brier']:.3f}`\n"
                        + (f"Weaknesses: {len(weaknesses)}\n" if weaknesses else "No weaknesses found\n")
                        + (f"Top: {weaknesses[0]}" if weaknesses else "")
                    )
            except Exception as e:
                logger.debug("Auto-calibration skipped: %s", e)

            # Notify
            side = "WIN" if outcome["our_side_won"] else "LOSS"
            left = outcome.get("pnl_left_on_table", 0)
            self.ctx.notifier.send(
                f"\U0001f50d *POST-EXIT* -- {outcome['slug'][:40]}\n\n"
                f"Exited: `{outcome['exit_reason']}` PnL=`${outcome['actual_pnl']:.2f}`\n"
                f"Match result: `{side}`\n"
                f"If held: `${outcome['hypothetical_pnl']:.2f}`"
                + (f" (left `${left:.2f}` on table)" if left > 0.5 else "")
            )
