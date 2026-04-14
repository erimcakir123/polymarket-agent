"""MarketData — Polymarket Gamma'dan gelen pazar verisi (TDD §5.1)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MarketData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    condition_id: str
    question: str
    slug: str
    yes_token_id: str
    no_token_id: str

    yes_price: float
    no_price: float
    liquidity: float
    volume_24h: float
    tags: list[str] = []

    end_date_iso: str
    match_start_iso: str = ""
    event_id: str | None = None

    event_live: bool = False
    event_ended: bool = False
    sport_tag: str = ""
    sports_market_type: str = ""

    closed: bool = False
    resolved: bool = False
    accepting_orders: bool = True
    odds_api_implied_prob: float | None = None
