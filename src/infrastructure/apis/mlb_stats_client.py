"""MLB Stats API wrapper (statsapi package).

Wraps statsapi.get() calls in safe try/except. Returns None on any
failure to let upstream skip.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import statsapi

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProbablePitcher:
    player_id: int
    name: str


@dataclass(frozen=True)
class ProbablePitchers:
    home: ProbablePitcher | None
    away: ProbablePitcher | None


@dataclass(frozen=True)
class TeamSeasonStats:
    wins: int
    losses: int
    runs_per_game: float
    runs_allowed_per_game: float
    earned_run_average: float


class MLBStatsClient:
    """Thin wrapper over statsapi (MLB-StatsAPI pip package)."""

    def get_probable_pitchers(self, game_pk: int) -> ProbablePitchers:
        try:
            response = statsapi.get("game", {"gamePk": game_pk})
        except Exception as exc:  # noqa: BLE001
            logger.warning("MLB game fetch failed for gamePk=%s: %s", game_pk, exc)
            return ProbablePitchers(home=None, away=None)

        prob = (response or {}).get("gameData", {}).get("probablePitchers", {})
        home_raw = prob.get("home")
        away_raw = prob.get("away")
        return ProbablePitchers(
            home=self._parse_pitcher(home_raw),
            away=self._parse_pitcher(away_raw),
        )

    def get_team_season_stats(self, team_id: int, season: int) -> TeamSeasonStats | None:
        try:
            response = statsapi.get(
                "team_stats",
                {"teamId": team_id, "season": season, "stats": "season", "group": "hitting,pitching"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("MLB team_stats failed for team_id=%s: %s", team_id, exc)
            return None

        try:
            stat = response["stats"][0]["splits"][0]["stat"]
            return TeamSeasonStats(
                wins=int(stat.get("wins", 0)),
                losses=int(stat.get("losses", 0)),
                runs_per_game=float(stat.get("runsPerGame", 0.0)),
                runs_allowed_per_game=float(stat.get("runsAllowedPerGame", 0.0)),
                earned_run_average=float(stat.get("earnedRunAverage", 0.0)),
            )
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            logger.warning("MLB team_stats parse failed: %s", exc)
            return None

    def get_pitcher_era(self, pitcher_id: int, season: int) -> float | None:
        try:
            response = statsapi.get(
                "people",
                {"personIds": pitcher_id, "hydrate": f"stats(group=[pitching],type=[season],season={season})"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("MLB pitcher ERA fetch failed for pitcher_id=%s: %s", pitcher_id, exc)
            return None

        try:
            for split in response["people"][0]["stats"][0]["splits"]:
                era_str = split["stat"].get("era")
                if era_str:
                    return float(era_str)
        except (KeyError, IndexError, ValueError, TypeError):
            return None
        return None

    @staticmethod
    def _parse_pitcher(raw: dict | None) -> ProbablePitcher | None:
        if not raw:
            return None
        pid = raw.get("id")
        name = raw.get("fullName") or raw.get("name") or ""
        if not pid or not name:
            return None
        return ProbablePitcher(player_id=int(pid), name=name)
