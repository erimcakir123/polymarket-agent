"""Soccer league cache — disk persist + TTL + learned map (PLAN-012).

İki farklı veriyi tek JSON dosyasında tutar:
1. ESPN soccer league listesi (24h TTL) — discovery başlangıç noktası
2. Learned map: (prefix, normalised_team_name) → confirmed ESPN league slug

Corruption-safe: bozuk veya eksik dosya → boş state + WARNING.
Reboot'ta kalır (logs/ kök dosyası, archive dışında).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def _normalise_team(name: str) -> str:
    return " ".join((name or "").lower().split())


class SoccerLeagueCache:
    """ESPN league list + learned (prefix, team) → league disk cache."""

    def __init__(self, cache_path: Path, ttl_hours: int = 24) -> None:
        self._path = Path(cache_path)
        self._ttl_sec = int(ttl_hours) * 3600
        self._leagues: list[str] = []
        self._league_list_ts: float = 0.0
        # learned: "<prefix>|<normalised_team>" → league slug
        self._learned: dict[str, str] = {}
        self._load()

    # ── League list (TTL'li) ──────────────────────────────────────────────

    def get_leagues(self) -> list[str]:
        """TTL içindeyse cached listeyi döndür, değilse boş."""
        if not self._leagues:
            return []
        if (time.time() - self._league_list_ts) > self._ttl_sec:
            return []
        return list(self._leagues)

    def set_leagues(self, slugs: list[str]) -> None:
        self._leagues = list(slugs)
        self._league_list_ts = time.time()
        self._persist()

    # ── Learned map (süresiz) ─────────────────────────────────────────────

    def get_learned(self, prefix: str, team_name: str) -> str | None:
        key = self._learned_key(prefix, team_name)
        return self._learned.get(key)

    def set_learned(self, prefix: str, team_name: str, league: str) -> None:
        key = self._learned_key(prefix, team_name)
        self._learned[key] = league
        self._persist()

    # ── Private ───────────────────────────────────────────────────────────

    @staticmethod
    def _learned_key(prefix: str, team_name: str) -> str:
        return f"{(prefix or '').lower().strip()}|{_normalise_team(team_name)}"

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("SoccerLeagueCache corrupted [%s]: %s", self._path, exc)
            return
        self._leagues = list(data.get("leagues") or [])
        self._league_list_ts = float(data.get("league_list_ts") or 0.0)
        self._learned = dict(data.get("learned") or {})

    def _persist(self) -> None:
        data = {
            "leagues": self._leagues,
            "league_list_ts": self._league_list_ts,
            "learned": self._learned,
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("SoccerLeagueCache persist failed [%s]: %s", self._path, exc)
