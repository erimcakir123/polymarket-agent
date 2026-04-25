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
