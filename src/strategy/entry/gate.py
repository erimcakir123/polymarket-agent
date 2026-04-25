"""Entry gate — GateConfig + EntryGate (TODO: tam uygulama yazılacak)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.models.signal import Signal

if TYPE_CHECKING:
    from src.models.market import MarketData


@dataclass
class GateConfig:
    min_favorite_probability: float
    max_entry_price: float
    max_positions: int
    max_exposure_pct: float
    confidence_bet_pct: dict
    max_single_bet_usdc: float
    max_bet_pct: float
    probability_weighted: bool
    min_bookmakers: int
    min_sharps: int
    hard_cap_overflow_pct: float = field(default=0.02)
    min_entry_size_pct: float = field(default=0.015)
    active_sports: list[str] = field(default_factory=list)
    min_gap_threshold: float = field(default=0.08)
    gap_high_zone: float = field(default=0.15)
    gap_extreme_zone: float = field(default=0.25)
    min_polymarket_price: float = field(default=0.15)
    min_market_volume: float = field(default=5000.0)
    max_match_start_hours: float = field(default=6.0)
    confidence_a_pct: float = field(default=0.05)
    confidence_b_pct: float = field(default=0.03)
    high_gap_multiplier: float = field(default=1.2)
    extreme_gap_multiplier: float = field(default=1.3)
    min_bet_usd: float = field(default=5.0)


@dataclass
class GateResult:
    condition_id: str
    signal: Signal | None = None
    skipped_reason: str | None = None
    skip_detail: str | None = None


class EntryGate:
    """Entry gate stub — TODO: implement full evaluation logic."""

    def __init__(
        self,
        config: GateConfig,
        portfolio: Any,
        circuit_breaker: Any,
        cooldown: Any,
        blacklist: Any,
        odds_enricher: Any,
        manipulation_checker: Any,
        cricket_client: Any = None,
    ) -> None:
        self.config = config

    def run(self, markets: list[MarketData]) -> list[GateResult]:  # TODO: yeniden yazılacak
        return []
