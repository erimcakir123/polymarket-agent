"""EdgeCandidate dataclass (SPEC-R Plan 2 T1)."""
from __future__ import annotations
from dataclasses import dataclass

_VALID_MARKET_TYPES = {"totals", "run_line"}


@dataclass(frozen=True)
class EdgeCandidate:
    """Immutable record of a detected edge in an MLB submarket.

    Attributes:
        model_p: Model probability for the YES outcome, in [0, 1].
        market_p: Market-implied probability for the YES outcome, in [0, 1].
        edge: Signed edge = model_p - market_p.
               Positive → BUY_YES candidate, negative → BUY_NO candidate.
        market_type: One of "totals" or "run_line".
        line: The numeric line value (e.g. 8.5 for totals, 1.5 for run_line).
    """

    model_p: float
    market_p: float
    edge: float
    market_type: str
    line: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.model_p <= 1.0:
            raise ValueError(f"model_p must be in [0,1], got {self.model_p}")
        if not 0.0 <= self.market_p <= 1.0:
            raise ValueError(f"market_p must be in [0,1], got {self.market_p}")
        if self.market_type not in _VALID_MARKET_TYPES:
            raise ValueError(
                f"market_type must be one of {_VALID_MARKET_TYPES}, got {self.market_type!r}"
            )
