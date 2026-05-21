"""MLB Stats API client (statsapi.mlb.com).

SPEC-R Plan 3 T1. Infrastructure layer — I/O allowed, no domain imports.
Retry policy: exponential backoff on 429/5xx/timeout; immediate fail on 4xx.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class StatsApiError(Exception):
    """Raised when Stats API request fails persistently."""


class StatsApiClient:
    def __init__(
        self,
        base_url: str = "https://statsapi.mlb.com",
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{self.base_url}{path}"
        for retry in range(self.max_retries + 1):
            try:
                resp = requests.get(url, params=params or {}, timeout=self.timeout)
                if resp.status_code == 200:
                    logger.info("StatsAPI %s → 200 OK", url)
                    return resp.json()
                if resp.status_code in (429,) or 500 <= resp.status_code < 600:
                    if retry < self.max_retries:
                        backoff = 1.0 * (2 ** retry)
                        logger.warning(
                            "StatsAPI %s returned %d, retrying in %.1fs (attempt %d/%d)",
                            url, resp.status_code, backoff, retry + 1, self.max_retries,
                        )
                        time.sleep(backoff)
                        continue
                    logger.error(
                        "StatsAPI %s failed after %d retries (status=%d)",
                        url, self.max_retries, resp.status_code,
                    )
                    raise StatsApiError(
                        f"StatsAPI {url} failed after {self.max_retries} retries"
                        f" (status={resp.status_code})"
                    )
                raise StatsApiError(f"StatsAPI {url} HTTP {resp.status_code}")
            except (requests.Timeout, requests.ConnectionError) as e:
                if retry < self.max_retries:
                    backoff = 1.0 * (2 ** retry)
                    logger.warning(
                        "StatsAPI %s network error, retrying in %.1fs: %s", url, backoff, e
                    )
                    time.sleep(backoff)
                    continue
                logger.error("StatsAPI %s network failure after retries: %s", url, e)
                raise StatsApiError(f"StatsAPI {url} network failure: {e}") from e
        raise StatsApiError(f"StatsAPI {url} unexpected fallthrough")

    def get_schedule(self, date: str) -> list[dict]:
        """date = 'YYYY-MM-DD'. Returns list of {gamePk, home_team_id, away_team_id, status}."""
        data = self._request("/api/v1/schedule", {"sportId": 1, "date": date})
        result = []
        for d in data.get("dates", []):
            for g in d.get("games", []):
                result.append({
                    "gamePk": g.get("gamePk"),
                    "home_team_id": (
                        g.get("teams", {}).get("home", {}).get("team", {}).get("id")
                    ),
                    "away_team_id": (
                        g.get("teams", {}).get("away", {}).get("team", {}).get("id")
                    ),
                    "status": g.get("status", {}).get("abstractGameState"),
                })
        return result

    def get_game_feed(self, game_pk: int) -> dict:
        """Full GUMBO live feed JSON."""
        return self._request(f"/api/v1.1/game/{game_pk}/feed/live")

    def get_probable_pitchers(self, date: str) -> dict[int, dict]:
        """gamePk -> {home_pitcher_id, away_pitcher_id}."""
        data = self._request(
            "/api/v1/schedule",
            {"sportId": 1, "date": date, "hydrate": "probablePitcher"},
        )
        result: dict[int, dict] = {}
        for d in data.get("dates", []):
            for g in d.get("games", []):
                gpk = g.get("gamePk")
                if gpk is None:
                    continue
                result[gpk] = {
                    "home_pitcher_id": (
                        g.get("teams", {}).get("home", {})
                        .get("probablePitcher", {}).get("id")
                    ),
                    "away_pitcher_id": (
                        g.get("teams", {}).get("away", {})
                        .get("probablePitcher", {}).get("id")
                    ),
                }
        return result

    def get_lineup(self, game_pk: int) -> dict[str, list[int]]:
        """{'home': [9 batter mlbam_ids], 'away': [...]}.

        Falls back to empty list if lineup not posted yet.
        """
        feed = self.get_game_feed(game_pk)
        teams = feed.get("liveData", {}).get("boxscore", {}).get("teams", {})
        return {
            "home": list(teams.get("home", {}).get("battingOrder", [])),
            "away": list(teams.get("away", {}).get("battingOrder", [])),
        }

    def get_player_handedness(self, person_id: int) -> dict[str, str]:
        """Fetch batter side + pitcher hand for a player.

        Returns:
            {'bat_side': 'L'|'R'|'S', 'pitch_hand': 'L'|'R'}.
            Missing data defaults to 'R' (MLB-average ~70-75% right-handed).
        """
        data = self._request(f"/api/v1/people/{person_id}")
        people = data.get("people", [])
        if not people:
            return {"bat_side": "R", "pitch_hand": "R"}
        person = people[0]
        return {
            "bat_side": person.get("batSide", {}).get("code", "R"),
            "pitch_hand": person.get("pitchHand", {}).get("code", "R"),
        }
