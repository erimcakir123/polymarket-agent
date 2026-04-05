"""Pydantic data models for the trading agent."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator


def effective_price(yes_price: float, direction: str) -> float:
    """Convert YES-side price to effective price based on position direction.

    BUY_YES: returns yes_price directly.
    BUY_NO:  returns (1 - yes_price) = NO price.
    """
    return (1.0 - yes_price) if direction == "BUY_NO" else yes_price


class Direction(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    HOLD = "HOLD"


class MarketData(BaseModel):
    condition_id: str
    question: str
    yes_price: float
    no_price: float
    yes_token_id: str
    no_token_id: str
    volume_24h: float = 0
    liquidity: float = 0
    slug: str = ""
    tags: List[str] = []
    end_date_iso: str = ""
    description: str = ""
    event_id: Optional[str] = None
    event_live: bool = False  # True when event is currently live (from Gamma API)
    event_ended: bool = False  # True when event has ended (from Gamma API)
    sport_tag: str = ""  # Source sport tag (e.g. "cs2", "lol", "nba") from tag_id scan
    accepting_orders_at: str = ""  # When trading opened (proxy for market freshness)
    match_start_iso: str = ""  # Actual match start time from Gamma event startTime
    odds_api_implied_prob: Optional[float] = None  # Bookmaker implied probability (0-1) from Odds API
    closed: bool = False                    # Gamma raw "closed" — market closed to trading
    resolved: bool = False                  # Gamma raw "resolved" — outcome finalized
    accepting_orders: bool = True           # Gamma raw "acceptingOrders" — accepting new orders


class Position(BaseModel):
    condition_id: str
    token_id: str
    direction: str
    entry_price: float
    size_usdc: float
    shares: float
    current_price: float
    slug: str = ""
    entry_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    category: str = ""
    confidence: str = "B-"
    ai_probability: float = 0.5  # ALWAYS P(YES outcome). Never direction-adjusted.

    @field_validator("ai_probability")
    @classmethod
    def check_yes_probability(cls, v: float) -> float:
        if not (0.01 <= v <= 0.99):
            raise ValueError(
                f"ai_probability={v} outside [0.01, 0.99]. "
                f"Must be P(YES outcome), never direction-adjusted."
            )
        return v
    scouted: bool = False  # True = pre-game scouted entry, hold to resolve (no take-profit)
    volatility_swing: bool = False  # True = bought cheap underdog for in-game spike, tight TP/SL
    question: str = ""  # Market question (human-readable title)
    end_date_iso: str = ""  # Market resolution deadline (ISO format)
    match_start_iso: str = ""  # Actual match start time from scout (ISO format)
    number_of_games: int = 0   # BO format from PandaScore (3=BO3, 5=BO5, 0=unknown)
    peak_pnl_pct: float = 0.0  # Highest unrealized PnL % seen (for trailing stop)
    live_on_clob: bool = False  # True when market is actively trading on CLOB
    match_live: bool = False  # True when match is live (from Gamma event.live)
    match_ended: bool = False  # True when match ended (from Gamma event.ended)
    match_score: str = ""  # Live score (from Gamma event.score, e.g. "2-1|Bo3")
    match_period: str = ""  # Current period (from Gamma event.period, e.g. "2/3")
    entry_reason: str = ""  # How this position was entered (e.g. "ai", "stock", "live_dip")
    is_consensus: bool = False  # True when AI and market agree on favorite
    pending_resolution: bool = False  # True when price ≥0.95 or ≤0.05 (awaiting oracle)
    sport_tag: str = ""  # Specific sport (e.g. "cs2", "dota2", "lol", "nba") for correlation
    event_id: str = ""  # Gamma event ID -- all outcomes of the same match share this
    bookmaker_prob: float = 0.0  # Bookmaker implied probability at entry (0 = not available)

    # Match-aware exit system fields
    ever_in_profit: bool = False           # True once peak_pnl_pct > 0.01 (never resets)
    consecutive_down_cycles: int = 0       # Consecutive cycles where price dropped
    cumulative_drop: float = 0.0           # Total price drop during current down streak
    previous_cycle_price: float = 0.0      # Price at last cycle (for momentum tracking)
    hold_revoked_at: datetime | None = None  # When hold-to-resolve was revoked
    hold_was_original: bool = False          # Was this originally a hold-to-resolve position

    # Scale Out fields (v2)
    original_shares: float | None = None
    original_size_usdc: float | None = None
    partial_exits: list[dict] = []
    scale_out_tier: int = 0
    scale_out_realized_usdc: float = 0.0  # Cumulative realized PnL from scale-outs (for dashboard net display)
    # Dashboard-only: live best-bid for mark-to-market display. DO NOT read in exit
    # logic — always use current_price (which is ask-side) for SL/TP/match exits.
    # 0.0 means "no WS tick received yet" (falls back to current_price in the UI).
    bid_price: float = 0.0
    # Lossy re-entry fields
    sl_reentry_count: int = 0  # How many times re-entered after stop-loss (max 1, 2nd SL = blacklist)

    # Scale-In fields (v2)
    intended_size_usdc: float = 0.0
    scale_in_complete: bool = False
    # σ-Trailing fields (v2)
    price_history_buffer: list[float] = []
    peak_price: float = 0.0
    # Grace period (v2)
    cycles_held: int = 0

    @computed_field
    @property
    def current_value(self) -> float:
        return self.shares * effective_price(self.current_price, self.direction)

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


class Signal(BaseModel):
    condition_id: str
    direction: Direction
    ai_probability: float  # ALWAYS P(YES outcome). Never direction-adjusted.
    market_price: float
    edge: float
    confidence: str

    @field_validator("ai_probability")
    @classmethod
    def check_yes_probability(cls, v: float) -> float:
        if not (0.01 <= v <= 0.99):
            raise ValueError(
                f"ai_probability={v} outside [0.01, 0.99]. "
                f"Must be P(YES outcome), never direction-adjusted."
            )
        return v
