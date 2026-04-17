"""Position modeli (TDD §5.2). ARCH Kural 7: anchor_probability HER ZAMAN P(YES)."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


def effective_price(yes_price: float, direction: str) -> float:
    """BUY_YES → yes_price; BUY_NO → (1 - yes_price)."""
    return (1.0 - yes_price) if direction == "BUY_NO" else yes_price


class Position(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Giriş bilgileri
    condition_id: str
    token_id: str
    direction: str  # BUY_YES | BUY_NO
    entry_price: float
    size_usdc: float
    shares: float
    slug: str = ""
    entry_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entry_reason: str = ""
    confidence: str = "B"
    anchor_probability: float  # P(YES), 0.01-0.99

    @field_validator("anchor_probability")
    @classmethod
    def _check_pyes(cls, v: float) -> float:
        if not (0.01 <= v <= 0.99):
            raise ValueError(
                f"anchor_probability={v} must be P(YES) in [0.01, 0.99]"
            )
        return v

    # Canlı durum
    current_price: float
    bid_price: float = 0.0
    peak_pnl_pct: float = 0.0
    peak_price: float = 0.0
    ever_in_profit: bool = False
    consecutive_down_cycles: int = 0
    cumulative_drop: float = 0.0
    previous_cycle_price: float = 0.0
    cycles_held: int = 0

    # Maç durumu
    sport_tag: str = ""
    event_id: str = ""
    match_start_iso: str = ""
    match_live: bool = False
    match_ended: bool = False
    match_score: str = ""
    match_period: str = ""
    question: str = ""
    end_date_iso: str = ""

    # Durum flag'leri
    favored: bool = False

    # Scale-out state
    original_shares: float | None = None
    original_size_usdc: float | None = None
    partial_exits: list[dict] = []
    scale_out_tier: int = 0
    scale_out_realized_usdc: float = 0.0

    # Lossy reentry
    sl_reentry_count: int = 0

    # Catastrophic watch state (SPEC-004 K5)
    catastrophic_watch: bool = False
    catastrophic_recovery_peak: float = 0.0

    # Bookmaker metadata
    bookmaker_prob: float = 0.0

    @computed_field
    @property
    def current_value(self) -> float:
        # shares ve current_price AYNI token'a aittir (BUY_YES → YES token, BUY_NO → NO token).
        # Dolar değeri = miktar × birim fiyatı. effective_price SADECE SL/FAV eşikleri için kullanılır.
        return self.shares * self.current_price

    @computed_field
    @property
    def unrealized_pnl_usdc(self) -> float:
        return self.current_value - self.size_usdc

    @computed_field
    @property
    def unrealized_pnl_pct(self) -> float:
        if self.size_usdc == 0:
            return 0.0
        return self.unrealized_pnl_usdc / self.size_usdc
