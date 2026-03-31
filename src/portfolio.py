"""Position tracking, PnL, stop-loss, take-profit, drawdown breaker."""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from src.models import Position, effective_price
from src.stop_loss_helper import compute_stop_loss_pct

logger = logging.getLogger(__name__)

POSITIONS_FILE = Path("logs/positions.json")
REALIZED_FILE = Path("logs/realized_pnl.json")


class Portfolio:
    def __init__(self, initial_bankroll: float = 0.0) -> None:
        self.positions: Dict[str, Position] = {}
        self._initial_bankroll = initial_bankroll
        self.bankroll: float = initial_bankroll
        self.high_water_mark: float = initial_bankroll
        self.realized_pnl: float = 0.0
        self.realized_wins: int = 0
        self.realized_losses: int = 0
        self._load_positions()
        self._load_realized()
        # Restore bankroll: initial + realized gains - money locked in open positions
        invested = sum(p.size_usdc for p in self.positions.values())
        self.bankroll = initial_bankroll + self.realized_pnl - invested
        self.high_water_mark = max(self.high_water_mark, self.bankroll)
        if self.realized_pnl != 0 or invested != 0:
            logger.info("Bankroll restored: $%.2f (initial=$%.0f + realized=$%.2f - invested=$%.2f)",
                        self.bankroll, initial_bankroll, self.realized_pnl, invested)

    def _load_positions(self) -> None:
        """Restore positions from disk on startup."""
        if not POSITIONS_FILE.exists():
            return
        try:
            data = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
            for cid, pos_data in data.items():
                self.positions[cid] = Position(**pos_data)
            if self.positions:
                logger.info("Restored %d positions from disk", len(self.positions))
                # Re-save to ensure new fields are serialized to JSON
                self._save_positions()
        except Exception as e:
            logger.warning("Could not load positions: %s", e)

    def _save_positions(self) -> None:
        """Persist current positions to disk."""
        POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {cid: pos.model_dump(mode="json") for cid, pos in self.positions.items()}
        tmp = POSITIONS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(POSITIONS_FILE)

    def add_position(
        self,
        condition_id: str,
        token_id: str,
        direction: str,
        entry_price: float,
        size_usdc: float,
        shares: float,
        slug: str = "",
        category: str = "",
        confidence: str = "B-",
        ai_probability: float = 0.5,
        scouted: bool = False,
        question: str = "",
        end_date_iso: str = "",
        match_start_iso: str = "",
        number_of_games: int = 0,
        volatility_swing: bool = False,
        entry_reason: str = "",
        sport_tag: str = "",
        event_id: str = "",
        bookmaker_prob: float = 0.0,
        is_consensus: bool = False,
        sl_reentry_count: int = 0,
    ) -> None:
        # Event-level duplicate guard -- never bet on two outcomes of the same event
        if event_id:
            for cid, pos in self.positions.items():
                if pos.event_id and pos.event_id == event_id:
                    logger.warning(
                        "BLOCKED: same event already held -- existing %s (%s), attempted %s (%s), event_id=%s",
                        pos.slug[:35], pos.direction, slug[:35], direction, event_id,
                    )
                    return
        # Duplicate guard -- never overwrite an existing position (would lose tracking)
        if condition_id in self.positions:
            logger.warning(
                "BLOCKED duplicate add_position: %s already held (size=$%.2f)",
                slug[:35], self.positions[condition_id].size_usdc,
            )
            return
        self.positions[condition_id] = Position(
            condition_id=condition_id,
            token_id=token_id,
            direction=direction,
            entry_price=entry_price,
            size_usdc=size_usdc,
            shares=shares,
            current_price=entry_price,
            slug=slug,
            category=category,
            confidence=confidence,
            ai_probability=ai_probability,
            scouted=scouted,
            volatility_swing=volatility_swing,
            question=question,
            end_date_iso=end_date_iso,
            match_start_iso=match_start_iso,
            number_of_games=number_of_games,
            entry_reason=entry_reason,
            sport_tag=sport_tag,
            event_id=event_id,
            bookmaker_prob=bookmaker_prob,
            is_consensus=is_consensus,
            sl_reentry_count=sl_reentry_count,
        )
        self.bankroll -= size_usdc
        self._save_positions()

    def _load_realized(self) -> None:
        """Load realized P&L from disk."""
        if not REALIZED_FILE.exists():
            return
        try:
            data = json.loads(REALIZED_FILE.read_text(encoding="utf-8"))
            self.realized_pnl = data.get("total", 0.0)
            self.realized_wins = data.get("wins", 0)
            self.realized_losses = data.get("losses", 0)
            self.high_water_mark = data.get("hwm", self.high_water_mark)
        except Exception as e:
            logger.warning("Could not load realized P&L: %s", e)

    def _save_realized(self) -> None:
        """Persist realized P&L to disk."""
        REALIZED_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = REALIZED_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "total": round(self.realized_pnl, 2),
            "wins": self.realized_wins,
            "losses": self.realized_losses,
            "hwm": round(self.high_water_mark, 2),
        }), encoding="utf-8")
        tmp.replace(REALIZED_FILE)

    def record_realized(self, pnl: float) -> None:
        """Record a closed position's P&L."""
        self.realized_pnl += pnl
        if pnl >= 0:
            self.realized_wins += 1
        else:
            self.realized_losses += 1
        self._save_realized()

    @property
    def active_position_count(self) -> int:
        """Count positions excluding those pending oracle resolution."""
        return sum(1 for p in self.positions.values() if not p.pending_resolution)

    # Special entry reasons that get their own slots (don't eat normal slots)
    _SPECIAL_ENTRY_REASONS = {"live_dip", "fav_time_gate", "early"}

    @property
    def normal_position_count(self) -> int:
        """Count normal positions (excluding VS, live_dip, fav_time_gate, early, re_entry)."""
        return sum(
            1 for p in self.positions.values()
            if not p.pending_resolution
            and not p.volatility_swing
            and p.entry_reason not in self._SPECIAL_ENTRY_REASONS
            and not p.entry_reason.startswith("re_entry")
        )

    @property
    def reentry_position_count(self) -> int:
        """Count active re-entry positions."""
        return sum(
            1 for p in self.positions.values()
            if not p.pending_resolution
            and p.entry_reason.startswith("re_entry")
        )

    def count_by_entry_reason(self, reason: str) -> int:
        """Count active positions with a specific entry_reason."""
        return sum(
            1 for p in self.positions.values()
            if not p.pending_resolution and p.entry_reason == reason
        )

    def mark_pending_resolution(self, condition_id: str) -> None:
        """Mark a position as pending oracle resolution (frees slot for new bets)."""
        if condition_id in self.positions:
            pos = self.positions[condition_id]
            if not pos.pending_resolution:
                pos.pending_resolution = True
                self._save_positions()
                logger.info("Pending resolution: %s (slot freed)", pos.slug[:40])

    def remove_position(self, condition_id: str) -> Position | None:
        pos = self.positions.pop(condition_id, None)
        if pos is not None:
            self.bankroll += pos.size_usdc  # Return invested capital to bankroll
            self._save_positions()
        return pos

    def update_price(self, condition_id: str, new_price: float) -> None:
        if condition_id in self.positions:
            pos = self.positions[condition_id]
            # Momentum tracking
            pos.previous_cycle_price = pos.current_price
            pos.current_price = new_price
            # Track peak PnL for trailing stop
            if pos.unrealized_pnl_pct > pos.peak_pnl_pct:
                pos.peak_pnl_pct = pos.unrealized_pnl_pct
            # Track ever_in_profit (never resets)
            if not pos.ever_in_profit and pos.peak_pnl_pct > 0.01:
                pos.ever_in_profit = True
            # Dynamic FAV promotion/demotion -- based on current market price
            eff_price = effective_price(new_price, pos.direction)
            if not pos.scouted and not pos.volatility_swing:
                if (eff_price >= 0.65
                        and pos.confidence in ("A", "B+")
                        and pos.peak_pnl_pct >= 0.50):
                    pos.scouted = True
                    pos.hold_was_original = False
                    logger.info("FAV PROMOTED: %s | price=%.0f%% | conf=%s | peak=%.0f%%",
                                pos.slug[:35], eff_price * 100, pos.confidence, pos.peak_pnl_pct * 100)
            elif pos.scouted and not pos.hold_was_original:
                if eff_price < 0.65:
                    pos.scouted = False
                    logger.info("FAV DEMOTED: %s | price %.0f%% < 65%% -- no longer favorite",
                                pos.slug[:35], eff_price * 100)
            # Track consecutive down cycles for momentum alert (use effective prices for BUY_NO)
            eff_new = effective_price(new_price, pos.direction)
            eff_prev = effective_price(pos.previous_cycle_price, pos.direction)
            if eff_prev > 0 and eff_new < eff_prev:
                pos.consecutive_down_cycles += 1
                pos.cumulative_drop += (eff_prev - eff_new)
            else:
                pos.consecutive_down_cycles = 0
                pos.cumulative_drop = 0.0

            # V2: Track cycles_held, effective price history, peak effective price
            pos.cycles_held += 1
            eff_price = effective_price(new_price, pos.direction)
            pos.price_history_buffer.append(eff_price)
            if len(pos.price_history_buffer) > 500:
                pos.price_history_buffer = pos.price_history_buffer[-500:]
            if eff_price > pos.peak_price:
                pos.peak_price = eff_price

    def save_prices_to_disk(self) -> None:
        """Persist current prices to disk so dashboard can read them."""
        self._save_positions()
        # Update HWM based on equity (cash + position values)
        total_value = sum(
            getattr(p, 'current_value', p.size_usdc) or p.size_usdc
            for p in self.positions.values()
        )
        equity = self.bankroll + total_value
        if equity > self.high_water_mark:
            self.high_water_mark = equity
            self._save_realized()

    def update_bankroll(self, new_bankroll: float) -> None:
        self.bankroll = new_bankroll
        if new_bankroll > self.high_water_mark:
            self.high_water_mark = new_bankroll

    @staticmethod
    def _is_totals_or_spread(pos: Position) -> bool:
        """Check if position is an O/U totals or spread market (hold to resolution)."""
        q = (pos.question or "").lower()
        slug = (pos.slug or "").lower()
        return any(k in q or k in slug for k in ("o/u", "total", "spread"))

    def check_stop_losses(self, stop_loss_pct: float = 0.30,
                          vs_stop_loss_pct: float = 0.20) -> List[str]:
        triggered = []
        for cid, pos in self.positions.items():
            sl = compute_stop_loss_pct(pos, base_sl_pct=stop_loss_pct, vs_sl_pct=vs_stop_loss_pct)
            if sl is None:
                continue  # Skip SL for this position (penny, totals/spread, stale)
            if pos.unrealized_pnl_pct < -sl:
                triggered.append(cid)
                label = "VS stop-loss" if pos.volatility_swing else "Stop-loss"
                logger.warning("%s triggered for %s: %.1f%%", label, pos.slug, pos.unrealized_pnl_pct * 100)
        return triggered

    def check_consensus_thesis(self, threshold: float = 0.50) -> List[str]:
        """Exit consensus positions when effective price drops below threshold.

        Consensus = both AI and market favor the same side (both >= 50%).
        Thesis broken = market no longer favors that side (dropped below 50%).

        Only applies after 50% of the match has elapsed -- early swings are normal.
        """
        from datetime import datetime, timezone
        from src.match_exit import get_game_duration

        triggered = []
        now = datetime.now(timezone.utc)
        for cid, pos in self.positions.items():
            if not pos.is_consensus:
                continue
            if pos.volatility_swing:
                continue

            # Only apply after 2nd half (50%+ elapsed)
            if pos.match_start_iso:
                try:
                    start_dt = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
                    elapsed_sec = max(0, (now - start_dt).total_seconds())
                    duration_min = get_game_duration(pos.slug, pos.number_of_games, pos.sport_tag)
                    elapsed_pct = min(1.0, elapsed_sec / (duration_min * 60))
                    if elapsed_pct < 0.50:
                        continue  # Too early -- let the match develop
                except (ValueError, TypeError):
                    pass  # No timing data -- fall through to price check

            # Effective price = the side we bought
            eff_price = effective_price(pos.current_price, pos.direction)
            if eff_price < threshold:
                triggered.append(cid)
                logger.warning(
                    "Consensus thesis invalidated: %s | eff=%.0f%% < %d%%",
                    pos.slug[:30], eff_price * 100, int(threshold * 100),
                )
        return triggered

    def check_scale_outs(
        self,
    ) -> list[dict]:
        """Check positions for scale-out tier triggers. Returns list of scale-out actions."""
        from src.scale_out import check_scale_out
        results = []
        for cid, pos in self.positions.items():
            # Pending + profitable: hold for oracle resolve, don't scale out
            if pos.pending_resolution and pos.unrealized_pnl_pct > 0:
                continue
            # Note: scouted positions intentionally participate in scale-out (spec §9j)
            result = check_scale_out(
                scale_out_tier=pos.scale_out_tier,
                unrealized_pnl_pct=pos.unrealized_pnl_pct,
                volatility_swing=pos.volatility_swing,
            )
            if result is not None:
                results.append({"condition_id": cid, **result})
        return results

    def check_match_aware_exits(self) -> list[dict]:
        """Run 4-layer match-aware exit check on all positions.

        Returns list of dicts with: condition_id, layer, reason, exit, revoke_hold, restore_hold
        """
        from src.match_exit import check_match_exit

        results = []
        for cid, pos in self.positions.items():
            # Skip stale prices
            if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
                continue
            # O/U and spread markets: hold to resolution
            if self._is_totals_or_spread(pos):
                continue
            # Pending resolution + profitable: wait for oracle resolve
            # Pending + losing: fall through to match-aware exit evaluation
            if pos.pending_resolution and pos.unrealized_pnl_pct > 0:
                continue

            data = {
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "peak_pnl_pct": pos.peak_pnl_pct,
                "ever_in_profit": pos.ever_in_profit,
                "match_start_iso": pos.match_start_iso,
                "number_of_games": pos.number_of_games,
                "slug": pos.slug,
                "match_score": pos.match_score,
                "direction": pos.direction,
                "scouted": pos.scouted,
                "confidence": pos.confidence,
                "ai_probability": pos.ai_probability,
                "consecutive_down_cycles": pos.consecutive_down_cycles,
                "cumulative_drop": pos.cumulative_drop,
                "hold_revoked_at": pos.hold_revoked_at,
                "hold_was_original": pos.hold_was_original,
                "volatility_swing": pos.volatility_swing,
                "category": pos.category,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                "entry_reason": pos.entry_reason,
                "cycles_held": pos.cycles_held,
                "sport_tag": pos.sport_tag,
                "hold_hours": (datetime.now(timezone.utc) - pos.entry_timestamp).total_seconds() / 3600,
            }

            check = check_match_exit(data)
            if check["exit"] or check["revoke_hold"] or check["restore_hold"]:
                results.append({"condition_id": cid, **check})

        return results

    def is_drawdown_breaker_active(self, halt_pct: float = 0.50) -> bool:
        if self.high_water_mark <= 0:
            return False
        # Use equity (cash + position current values) not just cash
        total_value = sum(
            getattr(p, 'current_value', p.size_usdc) or p.size_usdc
            for p in self.positions.values()
        )
        equity = self.bankroll + total_value
        return equity < self.high_water_mark * (1 - halt_pct)

    def get_drawdown_level(self, soft_pct: float = 0.50, hard_pct: float = 0.65) -> str:
        """Two-level drawdown check.

        Returns: 'none' | 'soft' | 'hard'
        - soft: equity < (1 - soft_pct) * HWM -> no new entries
        - hard: equity < (1 - hard_pct) * HWM -> close everything
        """
        if self.high_water_mark <= 0:
            return "none"
        total_value = sum(
            getattr(p, 'current_value', p.size_usdc) or p.size_usdc
            for p in self.positions.values()
        )
        equity = self.bankroll + total_value
        drawdown = 1 - (equity / self.high_water_mark)
        if drawdown >= hard_pct:
            return "hard"  # Equity < 35% of HWM -> close everything
        elif drawdown >= soft_pct:
            return "soft"  # Equity < 50% of HWM -> no new entries
        return "none"

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl_usdc for p in self.positions.values())

    def correlated_exposure(self, category: str, sport_tag: str = "") -> float:
        """Calculate exposure in same sport (sport_tag preferred, fallback to category)."""
        if self.bankroll <= 0:
            return 0.0
        if sport_tag:
            tag_total = sum(p.size_usdc for p in self.positions.values()
                          if getattr(p, 'sport_tag', '') == sport_tag)
            return tag_total / self.bankroll
        cat_total = sum(p.size_usdc for p in self.positions.values() if p.category == category)
        return cat_total / self.bankroll

    def count_by_category(self, category: str, sport_tag: str = "") -> int:
        """Count positions in the same sport/category for correlation cap."""
        if sport_tag:
            return sum(1 for p in self.positions.values()
                      if getattr(p, 'sport_tag', '') == sport_tag)
        if not category:
            return 0
        return sum(1 for p in self.positions.values() if p.category == category)
