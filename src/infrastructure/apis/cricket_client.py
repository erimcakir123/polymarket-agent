"""CricAPI HTTP client — free tier 100 hit/gun (SPEC-011).

Tek endpoint: /v1/currentMatches — TUM aktif cricket maclari doner.
Cache TTL ve timeout config'den (ARCH_GUARD Kural 6).

Hit budget tracking: API response'unda hitsUsed/hitsLimit var.
Limit dolunca get_current_matches() None doner — entry gate skip eder.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.cricapi.com/v1"  # endpoint sabit


@dataclass
class CricketMatchScore:
    """CricAPI response'undan parse edilen tek bir mac."""
    match_id: str
    name: str
    match_type: str                # "t20" | "odi" | "test"
    teams: list[str]
    status: str
    match_started: bool
    match_ended: bool
    venue: str
    date_time_gmt: str
    innings: list[dict]            # [{runs, wickets, overs, team, inning_num}]


@dataclass
class CricAPIQuota:
    """Daily API usage tracking. Response'dan guncelleniyor."""
    used_today: int = 0
    daily_limit: int = 100

    @property
    def remaining(self) -> int:
        return max(0, self.daily_limit - self.used_today)

    @property
    def exhausted(self) -> bool:
        return self.used_today >= self.daily_limit


class CricketAPIClient:
    """CricAPI /currentMatches wrapper + cache + quota tracking."""

    def __init__(
        self,
        api_key: str,
        daily_limit: int = 100,
        cache_ttl_sec: int = 240,
        timeout_sec: int = 15,
        http_get=None,
    ) -> None:
        self._api_key = api_key
        self._http = http_get or self._default_get
        self._cache_ttl = cache_ttl_sec
        self._timeout = timeout_sec
        self._cached_data: list[CricketMatchScore] | None = None
        self._cache_timestamp: float = 0.0
        self.quota = CricAPIQuota(daily_limit=daily_limit)

    def get_current_matches(self) -> list[CricketMatchScore] | None:
        """TUM aktif cricket maclari. None → limit dolu veya hata."""
        if self.quota.exhausted:
            logger.warning(
                "CricAPI quota exhausted (%d/%d) — skipping fetch",
                self.quota.used_today, self.quota.daily_limit,
            )
            return None

        now = time.time()
        if self._cached_data is not None and (now - self._cache_timestamp) < self._cache_ttl:
            return self._cached_data

        try:
            response = self._http(
                f"{_BASE_URL}/currentMatches",
                params={"apikey": self._api_key, "offset": 0},
                timeout=self._timeout,
            )
            if response.status_code != 200:
                logger.warning("CricAPI HTTP %d", response.status_code)
                return None
            data = response.json() or {}
            info = data.get("info", {})
            self.quota.used_today = int(info.get("hitsToday", 0))
            self.quota.daily_limit = int(info.get("hitsLimit", self.quota.daily_limit))
            matches_raw = data.get("data", [])
            matches: list[CricketMatchScore] = []
            for raw in matches_raw:
                parsed = self._parse_match(raw)
                if parsed is not None:
                    matches.append(parsed)
            self._cached_data = matches
            self._cache_timestamp = now
            logger.info(
                "CricAPI fetch: %d matches, quota %d/%d",
                len(matches), self.quota.used_today, self.quota.daily_limit,
            )
            return matches
        except Exception as exc:  # noqa: BLE001
            logger.warning("CricAPI fetch error: %s", exc)
            return None

    def _parse_match(self, raw: dict) -> CricketMatchScore | None:
        """Raw dict → CricketMatchScore. Bozuk kayit None doner."""
        try:
            innings: list[dict] = []
            for s in raw.get("score", []) or []:
                inning_str = s.get("inning", "") or ""
                team_name = ""
                inning_num = 0
                if " Inning " in inning_str:
                    team_name, num_part = inning_str.rsplit(" Inning ", 1)
                    try:
                        inning_num = int(num_part.strip())
                    except ValueError:
                        inning_num = 0
                innings.append({
                    "runs": int(s.get("r", 0)),
                    "wickets": int(s.get("w", 0)),
                    "overs": float(s.get("o", 0)),
                    "team": team_name.strip(),
                    "inning_num": inning_num,
                })
            return CricketMatchScore(
                match_id=str(raw.get("id", "")),
                name=str(raw.get("name", "")),
                match_type=str(raw.get("matchType", "")).lower(),
                teams=list(raw.get("teams", [])),
                status=str(raw.get("status", "")),
                match_started=bool(raw.get("matchStarted", False)),
                match_ended=bool(raw.get("matchEnded", False)),
                venue=str(raw.get("venue", "")),
                date_time_gmt=str(raw.get("dateTimeGMT", "")),
                innings=innings,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("CricAPI parse error: %s", exc)
            return None

    @staticmethod
    def _default_get(url: str, params: dict, timeout: int) -> Any:
        return requests.get(url, params=params, timeout=timeout)
