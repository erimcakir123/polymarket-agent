"""Confidence-based position sizing and risk gatekeeper.

Sizing is driven by AI confidence grade, not edge.
Higher confidence = larger bet as % of bankroll.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass

from src.config import RiskConfig
from src.models import Signal

logger = logging.getLogger(__name__)

# Confidence -> bankroll percentage (the ONLY sizing table)
CONF_BET_PCT: dict[str, float] = {
    "A":  0.05,   # 5% -> $50 on $1000
    "B+": 0.04,   # 4% -> $40
    "B-": 0.03,   # 3% -> $30
}


def confidence_position_size(
    confidence: str,
    bankroll: float,
    max_bet_usdc: float = 75,
    max_bet_pct: float = 0.05,
    is_esports: bool = False,
    is_reentry: bool = False,
    market_price: float = 0.0,
) -> float:
    """Size position by confidence grade. Simple, no Kelly formula."""
    bet_pct = CONF_BET_PCT.get(confidence, 0.03)

    # Heavy favorite boost: 90%+ markets pay little per share, size up 50%
    if market_price >= 0.90:
        bet_pct *= 1.50

    # Esports: 10% smaller (higher variance)
    if is_esports:
        bet_pct *= 0.90

    # Reentry: 20% smaller (already lost once)
    if is_reentry:
        bet_pct *= 0.80

    size = bankroll * bet_pct
    size = min(size, max_bet_usdc, bankroll * max_bet_pct, bankroll)
    return max(0, round(size, 2))


@dataclass
class RiskDecision:
    approved: bool
    size_usdc: float
    reason: str


class RiskManager:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config
        self.consecutive_losses: int = 0
        self.cooldown_remaining: int = 0
        self._cooldown_decremented_this_cycle: bool = False

    def evaluate(
        self,
        signal: Signal,
        bankroll: float,
        open_positions: dict,
        correlated_exposure: float = 0.0,
        **kwargs,
    ) -> RiskDecision:
        # Cooldown check -- decrement once per cycle, not per evaluate() call
        if self.cooldown_remaining > 0:
            if not self._cooldown_decremented_this_cycle:
                self.cooldown_remaining -= 1
                self._cooldown_decremented_this_cycle = True
            if self.cooldown_remaining > 0:
                return RiskDecision(False, 0, "Cooldown active after consecutive losses")

        # Max positions
        if len(open_positions) >= self.config.max_positions:
            return RiskDecision(False, 0, f"max_positions reached ({self.config.max_positions})")

        # Already in this market
        if signal.condition_id in open_positions:
            return RiskDecision(False, 0, "Already have position in this market")

        # Correlation cap
        if correlated_exposure >= self.config.correlation_cap_pct:
            return RiskDecision(False, 0, "Correlation cap exceeded")

        # Confidence-based sizing -- no Kelly formula, confidence drives bet size
        confidence = getattr(signal, 'confidence', "B-")
        category = getattr(signal, 'category', '')
        mkt_price = getattr(signal, 'market_price', 0.0)
        size = confidence_position_size(
            confidence=confidence,
            bankroll=bankroll,
            max_bet_usdc=self.config.max_single_bet_usdc,
            max_bet_pct=self.config.max_bet_pct,
            is_esports=(category == "esports"),
            market_price=mkt_price,
        )

        if size < 5.0:  # Polymarket min order
            return RiskDecision(False, 0, f"Bet too small: ${size:.2f} (min $5, conf={confidence})")

        return RiskDecision(True, size, f"Onaylandı: ${size:.2f} (conf={confidence})")

    def new_cycle(self) -> None:
        """Call once at the start of each cycle to reset per-cycle flags."""
        self._cooldown_decremented_this_cycle = False

    def record_outcome(self, win: bool) -> None:
        if win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.config.consecutive_loss_cooldown:
                self.cooldown_remaining = self.config.cooldown_cycles
                self.consecutive_losses = 0  # Reset to prevent double cooldown
                logger.warning("Cooldown triggered: %d consecutive losses", self.config.consecutive_loss_cooldown)
