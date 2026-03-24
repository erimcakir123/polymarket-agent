"""Quarter-Kelly position sizing and risk gatekeeper."""
from __future__ import annotations
import logging
from dataclasses import dataclass

from src.config import RiskConfig
from src.models import Signal
from src.adaptive_kelly import get_adaptive_kelly_fraction

logger = logging.getLogger(__name__)


def kelly_position_size(
    ai_prob: float,
    market_price: float,
    bankroll: float,
    kelly_fraction: float = 0.25,
    max_bet_usdc: float = 75,
    max_bet_pct: float = 0.05,
    direction: str = "BUY_YES",
) -> float:
    if direction == "BUY_YES":
        p, cost = ai_prob, market_price
    else:
        p, cost = 1 - ai_prob, 1 - market_price

    if cost <= 0 or cost >= 1:
        return 0.0

    q = 1 - p
    b = (1 - cost) / cost
    if b <= 0:
        return 0.0

    full_kelly = max(0, (p * b - q) / b)
    actual = full_kelly * kelly_fraction
    bet = min(bankroll * actual, max_bet_usdc, bankroll * max_bet_pct, bankroll)
    return max(0, round(bet, 2))


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

    def evaluate(
        self,
        signal: Signal,
        bankroll: float,
        open_positions: dict,
        correlated_exposure: float = 0.0,
        **kwargs,
    ) -> RiskDecision:
        # Cooldown check (triggered by record_outcome, decremented here)
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1
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

        # Kelly sizing
        size = kelly_position_size(
            ai_prob=signal.ai_probability,
            market_price=signal.market_price,
            bankroll=bankroll,
            kelly_fraction=get_adaptive_kelly_fraction(
                confidence=getattr(signal, 'confidence', "B-"),
                ai_probability=signal.ai_probability,
                category=getattr(signal, 'category', ''),
                is_reentry=False,
                config_kelly_by_conf={"C": 0.08, "B-": 0.12, "B+": 0.20, "A": 0.25},
            ),
            max_bet_usdc=self.config.max_single_bet_usdc,
            max_bet_pct=self.config.max_bet_pct,
            direction=signal.direction.value,
        )

        if size < 5.0:  # Polymarket min order
            return RiskDecision(False, 0, f"Eminlik düşük, bahis çok küçük: ${size:.2f} (min $5)")

        return RiskDecision(True, size, f"Onaylandı: ${size:.2f}")

    def record_outcome(self, win: bool) -> None:
        if win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.config.consecutive_loss_cooldown:
                self.cooldown_remaining = self.config.cooldown_cycles
                self.consecutive_losses = 0  # Reset to prevent double cooldown
                logger.warning("Cooldown triggered: %d consecutive losses", self.config.consecutive_loss_cooldown)
