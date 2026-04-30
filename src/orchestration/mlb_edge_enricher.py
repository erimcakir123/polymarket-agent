"""MLB edge enricher — pitcher + season stats + weather + park enrichment."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.domain.sports.mlb_team_aliases import get_team_info
from src.infrastructure.data.mlb_park_factors import get_park_factor, ParkFactor
from src.infrastructure.data.mlb_stadium_coords import get_stadium_coords

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MLBEnrichedData:
    pitcher_confirmed_home: bool
    pitcher_confirmed_away: bool
    home_pitcher_era: float
    away_pitcher_era: float
    home_season_winpct: float
    away_season_winpct: float
    home_runs_per_game: float
    home_runs_allowed_per_game: float
    away_runs_per_game: float
    away_runs_allowed_per_game: float
    rain_chance: float
    wind_speed_mph: float
    wind_direction_deg: float
    temperature_f: float
    weather_run_bias: float
    park_factor: ParkFactor
    seconds_to_game_start: int


_LEAGUE_AVG_ERA = 4.20
_NEUTRAL_TEMP_F = 70.0
_WIND_SPEED_THRESHOLD_MPH = 15.0
_WIND_BLOWING_OUT_BIAS = 0.3
_WIND_BLOWING_IN_BIAS = -0.3


class MLBEdgeEnricher:
    """Aggregates pitcher + season + weather + park data for an MLB market.

    Returns None if mandatory data missing (pitcher unconfirmed, team stats unfetchable).
    """

    def __init__(self, stats_client: Any, weather_client: Any) -> None:
        self._stats = stats_client
        self._weather = weather_client

    def enrich(
        self,
        *,
        game_pk: int,
        home_abbr: str,
        away_abbr: str,
        game_time: datetime,
        season: int,
    ) -> MLBEnrichedData | None:
        """Enrich an MLB market with pitcher, season stats, weather and park data.

        Returns None when mandatory fields (pitchers or team stats) are unavailable.
        """
        # 1. Pitcher confirmation (mandatory)
        pitchers = self._stats.get_probable_pitchers(game_pk)
        if pitchers.home is None or pitchers.away is None:
            return None

        # 2. Pitcher ERAs (default to league avg if missing)
        home_era = self._stats.get_pitcher_era(pitchers.home.player_id, season) or _LEAGUE_AVG_ERA
        away_era = self._stats.get_pitcher_era(pitchers.away.player_id, season) or _LEAGUE_AVG_ERA

        # 3. Team season stats (mandatory)
        home_info = get_team_info(home_abbr)
        away_info = get_team_info(away_abbr)
        if not home_info or not away_info:
            logger.warning(
                "MLBEdgeEnricher: unknown team abbr home=%s away=%s", home_abbr, away_abbr
            )
            return None
        home_id = int(home_info["espn_id"])
        away_id = int(away_info["espn_id"])

        home_stats = self._stats.get_team_season_stats(home_id, season)
        away_stats = self._stats.get_team_season_stats(away_id, season)
        if not home_stats or not away_stats:
            logger.warning(
                "MLBEdgeEnricher: team season stats unavailable home_id=%s away_id=%s",
                home_id,
                away_id,
            )
            return None

        home_winpct = home_stats.wins / max(1, home_stats.wins + home_stats.losses)
        away_winpct = away_stats.wins / max(1, away_stats.wins + away_stats.losses)

        # 4. Weather (optional — defaults to neutral when unavailable)
        coords = get_stadium_coords(home_abbr)
        seconds_to_start = max(0, int((game_time - datetime.now(timezone.utc)).total_seconds()))

        snapshot = None
        if coords:
            hours_ahead = max(0, seconds_to_start // 3600)
            try:
                snapshot = self._weather.get_forecast(coords[0], coords[1], hours_ahead)
            except Exception as exc:  # noqa: BLE001
                logger.warning("MLBEdgeEnricher: weather fetch failed for %s: %s", home_abbr, exc)
                snapshot = None

        if snapshot is None:
            rain_chance = 0.0
            wind_speed = 0.0
            wind_dir = 0.0
            temp_f = _NEUTRAL_TEMP_F
            weather_run_bias = 0.0
        else:
            rain_chance = snapshot.rain_chance
            wind_speed = snapshot.wind_speed_mph
            wind_dir = snapshot.wind_direction_deg
            temp_f = snapshot.temperature_f
            weather_run_bias = self._compute_weather_run_bias(snapshot)

        # 5. Park factor (always neutral default if unknown)
        park = get_park_factor(home_abbr)

        return MLBEnrichedData(
            pitcher_confirmed_home=True,
            pitcher_confirmed_away=True,
            home_pitcher_era=home_era,
            away_pitcher_era=away_era,
            home_season_winpct=home_winpct,
            away_season_winpct=away_winpct,
            home_runs_per_game=home_stats.runs_per_game,
            home_runs_allowed_per_game=home_stats.runs_allowed_per_game,
            away_runs_per_game=away_stats.runs_per_game,
            away_runs_allowed_per_game=away_stats.runs_allowed_per_game,
            rain_chance=rain_chance,
            wind_speed_mph=wind_speed,
            wind_direction_deg=wind_dir,
            temperature_f=temp_f,
            weather_run_bias=weather_run_bias,
            park_factor=park,
            seconds_to_game_start=seconds_to_start,
        )

    @staticmethod
    def _compute_weather_run_bias(snapshot: Any) -> float:
        """Crude wind-based run bias for totals.

        Wind > threshold blowing out (deg 0-90 + 270-360 from CF) → positive bias.
        Wind > threshold blowing in → negative bias.
        Otherwise 0.
        """
        if snapshot.wind_speed_mph < _WIND_SPEED_THRESHOLD_MPH:
            return 0.0
        deg = snapshot.wind_direction_deg
        if 0 <= deg < 90 or 270 < deg <= 360:
            return _WIND_BLOWING_OUT_BIAS
        if 90 <= deg <= 270:
            return _WIND_BLOWING_IN_BIAS
        return 0.0
