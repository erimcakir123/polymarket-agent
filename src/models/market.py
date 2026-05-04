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

    # SPEC-015 3-way: home/away sub-market'lerinin question'ı tek takım taşır
    # ("Will X win?"). Event-level başlık ("X vs Y") draw sub-market question'ından
    # three_way_title.enrich_three_way_titles ile türetilip buraya yazılır.
    # 2-way market'lerde ve draw sub-market'inde boş kalır. Display amaçlı; ham
    # `question` alanı score matching / question_parser için dokunulmaz kalır.
    match_title: str = ""
