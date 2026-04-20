"""Entry karar sinyali (TDD §5.3)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from src.models.enums import Direction, EntryReason


class Signal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    condition_id: str
    direction: Direction
    anchor_probability: float  # P(YES)
    market_price: float
    confidence: str
    size_usdc: float
    entry_reason: EntryReason
    bookmaker_prob: float
    num_bookmakers: float = 0.0
    has_sharp: bool = False
    sport_tag: str = ""
    event_id: str = ""

    @field_validator("anchor_probability")
    @classmethod
    def _check_pyes(cls, v: float) -> float:
        if not (0.01 <= v <= 0.99):
            raise ValueError(f"anchor_probability={v} must be P(YES)")
        return v
