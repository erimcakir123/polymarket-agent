"""Basketball data Pydantic modelleri — schema drift fail-fast.

Dış kaynaklardan (nba_api, ESPN) gelen veri buradan geçer. Kolon adı veya
tip değişirse ValidationError fırlar — drift sessizce kabul edilmez.

ARCH_GUARD §12 uyumu: doğrulama hataları yutulmaz, çağıran katman karar verir.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class GameRecord(BaseModel):
    """Tek bir tamamlanmış basket maçı kaydı.

    Possessions Dean Oliver formülünden gelir:
      poss ≈ FGA + 0.44 * FTA - OREB + TOV
    Refresher hesaplar; model layer'da pace × efficiency için kullanılır.
    """

    game_id: str = Field(min_length=1)
    season: str = Field(pattern=r"^\d{4}-\d{2}$")
    game_date_utc: str
    home_team: str = Field(min_length=2, max_length=4)
    away_team: str = Field(min_length=2, max_length=4)
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    home_possessions: float = Field(gt=0)
    away_possessions: float = Field(gt=0)
    is_final: bool
    league: Literal[
        "nba", "wnba", "ncaab", "wncaab", "euroleague",
        "g_league", "summer_league", "eurocup",
        "liga_acb", "turkey_bsl", "italy_lega", "vtb",
    ]


class TeamSnapshot(BaseModel):
    """Takımın güncel rating durumu — cache'in tek satırı.

    Elo: takım gücü (moneyline pricer için).
    AdjO/AdjD/Pace: KenPom-tarzı possession-efficiency (totals/spread için).
    """

    team: str = Field(min_length=2, max_length=4)
    league: Literal[
        "nba", "wnba", "ncaab", "wncaab", "euroleague",
        "g_league", "summer_league", "eurocup",
        "liga_acb", "turkey_bsl", "italy_lega", "vtb",
    ]
    elo_rating: float
    elo_games: int = Field(ge=0)
    adj_o: float = Field(gt=0)
    adj_d: float = Field(gt=0)
    adj_pace: float = Field(gt=0)
    last_updated_utc: str


class RefresherResult(BaseModel):
    """Bir refresh çağrısının özet sonucu."""

    source: Literal["nba_api", "espn", "euroleague_api",
                    "acb_scraper", "bsl_scraper", "lega_scraper", "vtb_scraper"]
    league: Literal[
        "nba", "wnba", "ncaab", "wncaab", "euroleague",
        "g_league", "summer_league", "eurocup",
        "liga_acb", "turkey_bsl", "italy_lega", "vtb",
    ]
    games_fetched: int = Field(ge=0)
    games_persisted: int = Field(ge=0)
    ok: bool
    error: Optional[str] = None


class SourceStatus(BaseModel):
    """Bir veri kaynağının sağlık durumu — health monitor satırı."""

    source: Literal["nba_api", "espn", "euroleague_api",
                    "acb_scraper", "bsl_scraper", "lega_scraper", "vtb_scraper"]
    last_success_utc: Optional[str] = None
    last_fail_utc: Optional[str] = None
    consecutive_fails: int = Field(ge=0)
    active: bool
