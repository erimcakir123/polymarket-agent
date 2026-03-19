"""Pydantic data models for the trading agent."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

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
    confidence: str = "medium"
    ai_probability: float = 0.5

    @computed_field
    @property
    def current_value(self) -> float:
        # For BUY_NO, value increases when YES price drops (NO price = 1 - YES price)
        if self.direction == "BUY_NO":
            return self.shares * (1 - self.current_price)
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
