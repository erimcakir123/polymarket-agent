"""Position tracking, PnL, stop-loss, take-profit, drawdown breaker."""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, List

from src.models import Position

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
        confidence: str = "medium",
        ai_probability: float = 0.5,
        scouted: bool = False,
        question: str = "",
        end_date_iso: str = "",
        match_start_iso: str = "",
        number_of_games: int = 0,
        volatility_swing: bool = False,
        entry_reason: str = "",
    ) -> None:
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
    _SPECIAL_ENTRY_REASONS = {"esports_early", "live_dip", "fav_time_gate"}

    @property
    def normal_position_count(self) -> int:
        """Count normal positions (excluding VS, esports_early, live_dip, fav_time_gate)."""
        return sum(
            1 for p in self.positions.values()
            if not p.pending_resolution
            and not p.volatility_swing
            and p.entry_reason not in self._SPECIAL_ENTRY_REASONS
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
            # Track consecutive down cycles for momentum alert
            if pos.previous_cycle_price > 0 and new_price < pos.previous_cycle_price:
                pos.consecutive_down_cycles += 1
                pos.cumulative_drop += (pos.previous_cycle_price - new_price)
            else:
                pos.consecutive_down_cycles = 0
                pos.cumulative_drop = 0.0

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

    def check_stop_losses(self, stop_loss_pct: float = 0.40,
                          vs_stop_loss_pct: float = 0.50,
                          esports_stop_loss_pct: float = 0.40) -> List[str]:
        triggered = []
        for cid, pos in self.positions.items():
            # Skip if price was never updated (stale 0.0 → fake -100% PnL)
            if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
                logger.debug("Skipping stop-loss for %s: price never updated (%.4f)",
                             pos.slug[:30], pos.current_price)
                continue
            # O/U and spread markets: hold to resolution, no stop-loss
            if self._is_totals_or_spread(pos):
                continue
            # Volatility swings use their own stop-loss
            # Esports BO series get wider stop-loss due to natural volatility
            # BO5 gets extra +10% room (more games = more comeback potential)
            if pos.volatility_swing:
                sl = vs_stop_loss_pct
            elif pos.entry_price < 0.09:
                # Ultra-low entry (<9¢): no stop-loss, too volatile
                # Bet size IS the risk ($25-35 max loss)
                continue
            elif pos.entry_price < 0.20:
                # Low-entry (9-20¢): graduated stop-loss
                # Linear scale: 9¢ → 60%, 20¢ → 40%
                t = (pos.entry_price - 0.09) / (0.20 - 0.09)  # 0..1
                sl = 0.60 - t * 0.20  # 60% → 40%
            elif pos.confidence == "medium_low":
                sl = 0.30  # B- experiment: tighter stop-loss
            elif pos.category == "esports":
                sl = esports_stop_loss_pct + (0.10 if pos.number_of_games >= 5 else 0.0)
            else:
                sl = stop_loss_pct
            if pos.unrealized_pnl_pct < -sl:
                triggered.append(cid)
                label = "VS stop-loss" if pos.volatility_swing else "Stop-loss"
                logger.warning("%s triggered for %s: %.1f%%", label, pos.slug, pos.unrealized_pnl_pct * 100)
        return triggered

    def check_trailing_stops(self, trailing_tiers: list | None = None) -> List[str]:
        """Graduated trailing stop: higher peak → tighter protection.

        Default tiers: 10%+ peak → 50% drop, 20%+ → 35%, 40%+ → 25%.
        Highest matching tier wins (tightest stop).
        """
        if trailing_tiers is None:
            trailing_tiers = [
                {"min_peak": 0.10, "drop_pct": 0.50},
                {"min_peak": 0.20, "drop_pct": 0.35},
                {"min_peak": 0.40, "drop_pct": 0.25},
            ]
        # Sort tiers descending by min_peak so tightest matches first
        tiers = sorted(trailing_tiers, key=lambda t: t["min_peak"], reverse=True)

        triggered = []
        for cid, pos in self.positions.items():
            if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
                continue
            # O/U and spread markets: hold to resolution
            if self._is_totals_or_spread(pos):
                continue
            # VS positions: skip trailing stop — they have their own exit logic
            # (VS take-profit, VS stop-loss, mandatory exit before resolution)
            if pos.volatility_swing:
                continue
            # Favorite = AI ≥ 65% for our side + high/medium_high confidence → hold to resolve
            _eff_ai = pos.ai_probability if not (pos.direction and 'NO' in pos.direction) else (1 - pos.ai_probability)
            if _eff_ai >= 0.65 and pos.confidence in ("high", "medium_high"):
                continue  # Favorite: hold to resolve — no trailing stop

            # Find the tightest matching tier
            drop_threshold = None
            for tier in tiers:
                if pos.peak_pnl_pct >= tier["min_peak"]:
                    drop_threshold = tier["drop_pct"]
                    break  # Tightest match (highest min_peak that qualifies)

            if drop_threshold is None:
                continue  # Peak too low for any tier

            drop_from_peak = pos.peak_pnl_pct - pos.unrealized_pnl_pct
            if drop_from_peak >= drop_threshold:
                # Only trigger trailing stop if still in profit (or at least breakeven)
                # If in loss, let stop_loss handle it instead
                if pos.unrealized_pnl_pct < 0:
                    logger.info(
                        "Trailing stop skipped (in loss): %s peaked +%.1f%%, now %.1f%% — deferring to stop_loss",
                        pos.slug[:30], pos.peak_pnl_pct * 100, pos.unrealized_pnl_pct * 100,
                    )
                    continue
                triggered.append(cid)
                logger.warning(
                    "Trailing stop for %s: peaked at +%.1f%%, now +%.1f%% (dropped %.1f%% >= %.0f%% tier)",
                    pos.slug[:30], pos.peak_pnl_pct * 100,
                    pos.unrealized_pnl_pct * 100, drop_from_peak * 100, drop_threshold * 100,
                )
        return triggered

    def check_take_profits(self, take_profit_pct: float = 0.40,
                           vs_take_profit_pct: float = 1.0,
                           vs_tp_floor: float = 0.50,
                           vs_tp_ceiling: float = 2.00) -> List[str]:
        # Dynamic take-profit based on confidence + conviction
        confidence_tp = {
            "low": take_profit_pct,               # low → take profit early (40%)
            "medium_low": take_profit_pct,         # medium_low → same as low (40%)
            "medium": take_profit_pct * 2.0,       # medium (legacy) → 2x patience (80%)
            "medium_high": take_profit_pct * 2.0,  # medium_high → 2x patience (80%)
            "high": take_profit_pct * 3.5,         # high → let it ride (140%)
        }
        triggered = []
        for cid, pos in self.positions.items():
            # Skip if price was never updated (API error → 0.0 inflates PnL)
            if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
                continue
            # O/U and spread markets: hold to resolution
            if self._is_totals_or_spread(pos):
                continue

            # Volatility swing: dynamic take-profit based on entry price
            if pos.volatility_swing:
                # Cheap tokens (3-10¢) → high TP, expensive (20-30¢) → lower TP
                # Linear interpolation: 3¢ → tp_ceiling, 30¢ → tp_floor
                tp_floor = vs_tp_floor
                tp_ceiling = vs_tp_ceiling
                price_range = max(0.30 - 0.03, 0.01)  # avoid div by zero
                ratio = min(1.0, max(0.0, (pos.entry_price - 0.03) / price_range))
                dynamic_tp = tp_ceiling - ratio * (tp_ceiling - tp_floor)
                if pos.unrealized_pnl_pct > dynamic_tp:
                    triggered.append(cid)
                    logger.info("VS take-profit: %s | +%.1f%% (dynamic target: %.0f%%, entry: %.0f¢)",
                                pos.slug[:30], pos.unrealized_pnl_pct * 100,
                                dynamic_tp * 100, pos.entry_price * 100)
                continue  # Skip normal TP logic for VS positions

            # Determine effective AI probability for our bet direction
            effective_ai = pos.ai_probability
            if pos.direction and 'NO' in pos.direction:
                effective_ai = 1 - pos.ai_probability

            # FAVORITE: AI ≥ 65% for our side AND high/medium_high confidence → hold to resolve
            is_favorite = effective_ai >= 0.65 and pos.confidence in ("high", "medium_high")

            if is_favorite:
                # Hold to resolve — only emergency exit on massive overshoot (>50% gain)
                if pos.unrealized_pnl_pct > 0.50:
                    triggered.append(cid)
                    logger.info("Spike exit (favorite overshoot): %s | +%.1f%% > 50%%",
                                pos.slug[:30], pos.unrealized_pnl_pct * 100)
                    continue
                logger.debug("Hold to resolve (favorite): %s (AI=%.0f%% for our side, %s conf)",
                             pos.slug[:30], effective_ai * 100, pos.confidence)
                continue

            # UNDERDOG: everything else → edge trade, take profit at 85% of AI target
            if pos.ai_probability > 0:
                ai_target = pos.ai_probability
                current = pos.current_price or pos.entry_price
                if pos.direction and 'NO' in pos.direction:
                    ai_target = 1 - pos.ai_probability
                    current = 1 - current if current else pos.entry_price

                edge_tp_price = ai_target * 0.85
                if current >= edge_tp_price and current > pos.entry_price * 1.10:
                    triggered.append(cid)
                    logger.info("Edge TP (underdog): %s | price=%.0f¢ → AI target %.0f¢ (85%%=%.0f¢) | +%.1f%%",
                                pos.slug[:30], current * 100, ai_target * 100,
                                edge_tp_price * 100, pos.unrealized_pnl_pct * 100)
                    continue

                logger.debug("Hold for edge (underdog): %s (entry=%.0f¢, now=%.0f¢, target=%.0f¢)",
                             pos.slug[:30], pos.entry_price * 100, (pos.current_price or 0) * 100, ai_target * 100)
                continue

            tp = confidence_tp.get(pos.confidence, take_profit_pct)
            if pos.unrealized_pnl_pct > tp:
                triggered.append(cid)
                logger.info("Take-profit triggered for %s: %.1f%% (threshold: %.0f%%, confidence: %s)",
                            pos.slug, pos.unrealized_pnl_pct * 100, tp * 100, pos.confidence)
        return triggered

    def check_volatility_swing_exits(self) -> List[str]:
        """Mandatory exit for volatility swings approaching resolution.

        Must exit before match ends — holding to resolve = guaranteed loss for underdogs.
        """
        from datetime import datetime, timezone
        triggered = []
        now = datetime.now(timezone.utc)
        for cid, pos in self.positions.items():
            if not pos.volatility_swing:
                continue
            if not pos.end_date_iso:
                continue
            try:
                end_dt = datetime.fromisoformat(pos.end_date_iso.replace("Z", "+00:00"))
                minutes_left = (end_dt - now).total_seconds() / 60
                # Exit 15 minutes before resolution
                if minutes_left <= 15:
                    triggered.append(cid)
                    logger.warning(
                        "VS mandatory exit: %s | %.0f min to resolve — cannot hold underdog to resolve",
                        pos.slug[:30], minutes_left,
                    )
            except (ValueError, TypeError):
                pass
        return triggered

    def check_pre_match_exits(self, minutes_before: int = 30) -> List[str]:
        """Mandatory exit N minutes before match end for non-high-confidence positions.

        High confidence (A-tier) positions are exempt — Claudeus Optimus rule.
        """
        from datetime import datetime, timezone
        triggered = []
        now = datetime.now(timezone.utc)
        for cid, pos in self.positions.items():
            if pos.volatility_swing:
                continue  # VS has its own exit logic
            if pos.confidence in ("high", "medium_high"):
                continue  # Favorite confidence exempt — hold to resolve
            if pos.entry_reason in ("esports_early", "live_dip"):
                continue  # Esports early & live dip have their own exit logic
            if not pos.end_date_iso:
                continue
            try:
                end_dt = datetime.fromisoformat(pos.end_date_iso.replace("Z", "+00:00"))
                minutes_left = (end_dt - now).total_seconds() / 60
                if minutes_left <= minutes_before:
                    triggered.append(cid)
                    logger.warning(
                        "Pre-match exit: %s | %.0f min left | conf=%s — exiting before resolution",
                        pos.slug[:30], minutes_left, pos.confidence,
                    )
            except (ValueError, TypeError):
                pass
        return triggered

    def check_esports_halftime_exits(self) -> List[str]:
        """Exit esports positions at halftime if losing.

        BO3: after ~50 min (1 map done) — if losing, cut losses
        BO5: after ~75 min (2 maps done) — if losing, cut losses
        If in profit, let it ride.
        """
        from datetime import datetime, timezone
        triggered = []
        now = datetime.now(timezone.utc)
        for cid, pos in self.positions.items():
            if pos.category != "esports":
                continue
            if not pos.live_on_clob:
                continue  # Not live yet
            if pos.unrealized_pnl_pct >= 0:
                continue  # In profit — let it ride
            # Need match_start_iso to calculate elapsed time
            start_iso = pos.match_start_iso
            if not start_iso:
                continue
            try:
                start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                elapsed_min = (now - start_dt).total_seconds() / 60
            except (ValueError, TypeError):
                continue
            # BO3: mid map 2 (~62 min), BO5: mid map 3 (~87 min)
            if pos.number_of_games >= 5:
                halftime_min = 87
            else:
                halftime_min = 62
            if elapsed_min >= halftime_min:
                triggered.append(cid)
                logger.warning(
                    "Esports halftime exit: %s | BO%d | %d min elapsed | PnL=%.1f%% — cutting losses",
                    pos.slug[:30], pos.number_of_games, int(elapsed_min),
                    pos.unrealized_pnl_pct * 100,
                )
        return triggered

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

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl_usdc for p in self.positions.values())

    def correlated_exposure(self, category: str) -> float:
        if self.bankroll <= 0:
            return 0.0
        cat_total = sum(p.size_usdc for p in self.positions.values() if p.category == category)
        return cat_total / self.bankroll

    def count_by_category(self, category: str) -> int:
        """Count positions in the same league/category for correlation cap."""
        if not category:
            return 0
        return sum(1 for p in self.positions.values() if p.category == category)
