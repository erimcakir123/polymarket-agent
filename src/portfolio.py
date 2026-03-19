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
            question=question,
            end_date_iso=end_date_iso,
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

    def remove_position(self, condition_id: str) -> Position | None:
        pos = self.positions.pop(condition_id, None)
        if pos is not None:
            self._save_positions()
        return pos

    def update_price(self, condition_id: str, new_price: float) -> None:
        if condition_id in self.positions:
            pos = self.positions[condition_id]
            pos.current_price = new_price
            # Track peak PnL for trailing stop
            if pos.unrealized_pnl_pct > pos.peak_pnl_pct:
                pos.peak_pnl_pct = pos.unrealized_pnl_pct

    def update_bankroll(self, new_bankroll: float) -> None:
        self.bankroll = new_bankroll
        if new_bankroll > self.high_water_mark:
            self.high_water_mark = new_bankroll

    def check_stop_losses(self, stop_loss_pct: float = 0.30) -> List[str]:
        triggered = []
        for cid, pos in self.positions.items():
            # Skip if price was never updated (stale 0.0 → fake -100% PnL)
            if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
                logger.debug("Skipping stop-loss for %s: price never updated (%.4f)",
                             pos.slug[:30], pos.current_price)
                continue
            if pos.unrealized_pnl_pct < -stop_loss_pct:
                triggered.append(cid)
                logger.warning("Stop-loss triggered for %s: %.1f%%", pos.slug, pos.unrealized_pnl_pct * 100)
        return triggered

    def check_trailing_stops(self, trailing_drop_pct: float = 0.40) -> List[str]:
        """Trailing stop: if position was up significantly and dropped back, protect profit.

        Triggers when: peak PnL was >= 20% AND current PnL dropped 40% from peak.
        Example: peaked at +80%, now at +40% → drop = 40% → triggered.
        """
        triggered = []
        min_peak = 0.20  # Only activate trailing stop if it was up at least 20%
        for cid, pos in self.positions.items():
            if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
                continue
            if pos.scouted:
                continue  # Scouted positions hold to resolve
            if pos.peak_pnl_pct < min_peak:
                continue  # Never reached meaningful profit
            drop_from_peak = pos.peak_pnl_pct - pos.unrealized_pnl_pct
            if drop_from_peak >= trailing_drop_pct:
                triggered.append(cid)
                logger.warning(
                    "Trailing stop for %s: peaked at +%.1f%%, now +%.1f%% (dropped %.1f%%)",
                    pos.slug[:30], pos.peak_pnl_pct * 100,
                    pos.unrealized_pnl_pct * 100, drop_from_peak * 100,
                )
        return triggered

    def check_take_profits(self, take_profit_pct: float = 0.40) -> List[str]:
        # Dynamic take-profit based on confidence + conviction
        confidence_tp = {
            "low": take_profit_pct,          # low confidence → take profit early (40%)
            "medium": take_profit_pct * 2.0,  # medium → 2x patience (80%)
            "high": take_profit_pct * 3.5,    # high confidence → let it ride (140%)
        }
        triggered = []
        for cid, pos in self.positions.items():
            # Skip if price was never updated (API error → 0.0 inflates PnL)
            if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
                continue

            # Pre-scouted positions: hold to resolve, no take-profit
            if pos.scouted:
                logger.debug("Skipping take-profit for scouted position %s — hold to resolve",
                             pos.slug[:30])
                continue

            # Near-certain conviction: AI > 90% sure → wait for resolution, don't take profit
            ai_certainty = max(pos.ai_probability, 1 - pos.ai_probability)
            if ai_certainty >= 0.90:
                logger.debug("Skipping take-profit for %s: AI %.0f%% certain — waiting for resolution",
                             pos.slug[:30], ai_certainty * 100)
                continue

            tp = confidence_tp.get(pos.confidence, take_profit_pct)
            if pos.unrealized_pnl_pct > tp:
                triggered.append(cid)
                logger.info("Take-profit triggered for %s: %.1f%% (threshold: %.0f%%, confidence: %s)",
                            pos.slug, pos.unrealized_pnl_pct * 100, tp * 100, pos.confidence)
        return triggered

    def is_drawdown_breaker_active(self, halt_pct: float = 0.50) -> bool:
        if self.high_water_mark <= 0:
            return False
        return self.bankroll < self.high_water_mark * (1 - halt_pct)

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl_usdc for p in self.positions.values())

    def correlated_exposure(self, category: str) -> float:
        if self.bankroll <= 0:
            return 0.0
        cat_total = sum(p.size_usdc for p in self.positions.values() if p.category == category)
        return cat_total / self.bankroll
