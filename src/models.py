"""Pydantic data models for the trading agent."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, computed_field


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

    @computed_field
    @property
    def current_value(self) -> float:
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


class Signal(BaseModel):
    condition_id: str
    direction: Direction
    ai_probability: float
    market_price: float
    edge: float
    confidence: str
    reasoning: str = ""
    whale_boost: float = 0.0


class TradeRecord(BaseModel):
    condition_id: str
    slug: str
    direction: str
    size_usdc: float
    price: float
    edge: float
    confidence: str
    mode: str
    status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reasoning: str = ""
    order_id: Optional[str] = None


class PortfolioSnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    bankroll_usdc: float
    positions_count: int
    unrealized_pnl: float
    high_water_mark: float
    consecutive_losses: int = 0
