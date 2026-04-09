"""Fully automatic chess player name -> platform username resolver.

Strategy:
  1. Bootstrap: fetch Chess.com titled directories (GM/IM/WGM/WIM) -> ~5000 usernames
     Cross-reference via Lichess bulk POST /api/users (300 per batch) -> extract realName
     Build reverse map {normalized_real_name: (lichess_username, chesscom_username)}
  2. Per-player lookup: fuzzy match (rapidfuzz >= 85) against reverse map
  3. Fallback: username guessing (firstlast, flast, lastfirst) with .name validation
  4. Persistent cache at logs/chess_cache/username_map.json -- zero re-fetch cost
  5. Failed resolutions: cached with 7-day retry TTL

No manual override layer -- fully automatic per user request (2026-04-09).
"""
from __future__ import annotations

import json
import logging
import threading
import time
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests
from rapidfuzz import fuzz, process

from src.config import load_config

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("logs/chess_cache")
_USERNAME_MAP_PATH = _CACHE_DIR / "username_map.json"
_TITLED_RAW_PATH = _CACHE_DIR / "titled_raw.json"
_FAILED_CACHE_PATH = _CACHE_DIR / "unresolved.json"

_CHESSCOM_BASE = "https://api.chess.com/pub"
_LICHESS_BASE = "https://lichess.org/api"
_UA = "PolymarketAgent/1.0"

# Titles that cover Polymarket's chess player pool (elite + strong titled)
_TITLES = ["GM", "IM", "WGM", "WIM"]


@dataclass
class ResolvedUser:
    real_name: str
    lichess: Optional[str]
    chesscom: Optional[str]
    resolved_at: str  # ISO timestamp


class ChessUsernameResolver:
    """Thread-safe singleton resolver with persistent cache."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cfg = load_config().chess
        self._cache: dict[str, ResolvedUser] = {}
        self._failed: dict[str, str] = {}  # normalized_name -> last_attempt_iso
        self._titled_raw: dict[str, list[str]] = {}
        self._titled_loaded_at: float = 0.0
        self._reverse_map: dict[str, tuple[Optional[str], Optional[str]]] = {}
        self._reverse_map_built: bool = False
        self._last_request_at: float = 0.0
        self._load_persistent_cache()

    # ── Persistence ────────────────────────────────────────────────

    def _load_persistent_cache(self) -> None:
        try:
            if _USERNAME_MAP_PATH.exists():
                raw = json.loads(_USERNAME_MAP_PATH.read_text(encoding="utf-8"))
                self._cache = {k: ResolvedUser(**v) for k, v in raw.items()}
            if _FAILED_CACHE_PATH.exists():
                self._failed = json.loads(
                    _FAILED_CACHE_PATH.read_text(encoding="utf-8")
                )
        except Exception as exc:
            logger.warning("Chess cache load error: %s", exc)

    def _persist_cache(self) -> None:
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            serialized = {k: asdict(v) for k, v in self._cache.items()}
            tmp = _USERNAME_MAP_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
            tmp.replace(_USERNAME_MAP_PATH)
            tmp2 = _FAILED_CACHE_PATH.with_suffix(".tmp")
            tmp2.write_text(json.dumps(self._failed, indent=2), encoding="utf-8")
            tmp2.replace(_FAILED_CACHE_PATH)
        except Exception as exc:
            logger.warning("Chess cache persist error: %s", exc)

    # ── Rate limiting ─────────────────────────────────────────────

    def _throttle(self) -> None:
        now = time.time()
        delta = now - self._last_request_at
        if delta < self._cfg.rate_limit_seconds:
            time.sleep(self._cfg.rate_limit_seconds - delta)
        self._last_request_at = time.time()

    # ── Bootstrap: titled directories ─────────────────────────────

    def _ensure_titled_loaded(self) -> None:
        """Load Chess.com titled directories, cached for 30 days."""
        refresh_seconds = self._cfg.username_resolver_refresh_days * 86400
        now = time.time()
        if self._titled_raw and (now - self._titled_loaded_at) < refresh_seconds:
            return

        # Try disk cache first
        if _TITLED_RAW_PATH.exists():
            try:
                data = json.loads(_TITLED_RAW_PATH.read_text(encoding="utf-8"))
                disk_loaded_at = data.get("loaded_at", 0)
                if (now - disk_loaded_at) < refresh_seconds:
                    self._titled_raw = data.get("titles", {})
                    self._titled_loaded_at = disk_loaded_at
                    logger.info("Chess titled directory loaded from disk cache")
                    return
            except Exception:
                pass

        # Fetch from API
        raw: dict[str, list[str]] = {}
        for title in _TITLES:
            try:
                self._throttle()
                resp = requests.get(
                    f"{_CHESSCOM_BASE}/titled/{title}",
                    headers={"User-Agent": _UA},
                    timeout=15,
                )
                resp.raise_for_status()
                players = resp.json().get("players", [])
                raw[title] = players
                logger.info("Chess.com titled %s: %d players", title, len(players))
            except Exception as exc:
                logger.warning("Chess.com titled %s fetch failed: %s", title, exc)
                raw[title] = []

        self._titled_raw = raw
        self._titled_loaded_at = now

        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _TITLED_RAW_PATH.write_text(
                json.dumps({"loaded_at": now, "titles": raw}),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _ensure_reverse_map_built(self) -> None:
        """Build {real_name: (lichess, chesscom)} reverse map via Lichess bulk API.

        Lichess POST /api/users accepts up to 300 comma-separated usernames
        per call and returns user objects with .profile.realName we trust as
        ground truth for name resolution.
        """
        if self._reverse_map_built:
            return

        self._ensure_titled_loaded()
        all_usernames: list[str] = []
        for title_list in self._titled_raw.values():
            all_usernames.extend(title_list)
        all_usernames = list({u for u in all_usernames if u})
        if not all_usernames:
            self._reverse_map_built = True
            return

        BATCH = 300
        name_map: dict[str, tuple[Optional[str], Optional[str]]] = {}
        chesscom_lower_index = {u.lower(): u for u in all_usernames}

        for i in range(0, len(all_usernames), BATCH):
            batch = all_usernames[i : i + BATCH]
            try:
                self._throttle()
                resp = requests.post(
                    f"{_LICHESS_BASE}/users",
                    data=",".join(batch),
                    headers={
                        "User-Agent": _UA,
                        "Content-Type": "text/plain",
                    },
                    timeout=30,
                )
                if resp.status_code != 200:
                    logger.warning(
                        "Lichess bulk batch %d: HTTP %d",
                        i // BATCH, resp.status_code,
                    )
                    continue
                users = resp.json()
                for u in users:
                    if not isinstance(u, dict):
                        continue
                    if u.get("disabled"):
                        continue
                    profile = u.get("profile") or {}
                    real_name = profile.get("realName") or ""
                    if not real_name:
                        continue
                    normalized = _normalize_name(real_name)
                    lichess_user = u.get("id") or u.get("username")
                    # Same username might exist on both platforms
                    chesscom_user = chesscom_lower_index.get(
                        (lichess_user or "").lower()
                    )
                    name_map[normalized] = (lichess_user, chesscom_user)
            except Exception as exc:
                logger.warning("Lichess bulk batch %d error: %s", i // BATCH, exc)

        self._reverse_map = name_map
        self._reverse_map_built = True
        logger.info("Chess reverse map built: %d name entries", len(name_map))

    # ── Per-player resolution ─────────────────────────────────────

    def resolve(self, real_name: str) -> Optional[ResolvedUser]:
        """Resolve a real player name to (lichess, chesscom) usernames.

        Returns None if resolution fails (marks as unresolved with 7-day TTL).
        """
        if not real_name:
            return None
        normalized = _normalize_name(real_name)
        if not normalized:
            return None

        # Persistent cache hit
        if normalized in self._cache:
            return self._cache[normalized]

        # Failed cache hit — check retry TTL
        if normalized in self._failed:
            try:
                last_attempt = datetime.fromisoformat(self._failed[normalized])
                if last_attempt.tzinfo is None:
                    last_attempt = last_attempt.replace(tzinfo=timezone.utc)
                retry_cutoff = datetime.now(timezone.utc) - timedelta(
                    days=self._cfg.failed_resolve_retry_days,
                )
                if last_attempt > retry_cutoff:
                    return None
            except ValueError:
                pass

        with self._lock:
            # Double-check cache after lock
            if normalized in self._cache:
                return self._cache[normalized]

            # Strategy 1: reverse map lookup
            self._ensure_reverse_map_built()
            resolved = self._lookup_in_reverse_map(real_name, normalized)

            # Strategy 2: username guessing
            if not resolved:
                resolved = self._guess_username(real_name, normalized)

            if resolved and (resolved.lichess or resolved.chesscom):
                self._cache[normalized] = resolved
                if normalized in self._failed:
                    del self._failed[normalized]
                self._persist_cache()
                return resolved

            # Record failure
            self._failed[normalized] = datetime.now(timezone.utc).isoformat()
            self._persist_cache()
            return None

    def _lookup_in_reverse_map(
        self, real_name: str, normalized: str,
    ) -> Optional[ResolvedUser]:
        if not self._reverse_map:
            return None
        # Exact match
        if normalized in self._reverse_map:
            lichess, chesscom = self._reverse_map[normalized]
            return ResolvedUser(
                real_name=real_name,
                lichess=lichess,
                chesscom=chesscom,
                resolved_at=datetime.now(timezone.utc).isoformat(),
            )
        # Fuzzy match
        best = process.extractOne(
            normalized, list(self._reverse_map.keys()),
            scorer=fuzz.WRatio, score_cutoff=85,
        )
        if best:
            matched_key = best[0]
            lichess, chesscom = self._reverse_map[matched_key]
            logger.info(
                "Chess reverse-map fuzzy: %s -> %s (score=%d)",
                real_name, matched_key, int(best[1]),
            )
            return ResolvedUser(
                real_name=real_name,
                lichess=lichess,
                chesscom=chesscom,
                resolved_at=datetime.now(timezone.utc).isoformat(),
            )
        return None

    def _guess_username(
        self, real_name: str, normalized: str,
    ) -> Optional[ResolvedUser]:
        """Try common username patterns and validate via .name field."""
        parts = normalized.split()
        if len(parts) < 2:
            return None
        first = parts[0]
        last = parts[-1]
        guesses = [
            f"{first}{last}",          # anishgiri
            f"{first[0]}{last}",       # agiri
            f"{last}{first}",          # girianish
            f"{first}_{last}",         # anish_giri
            last,                      # giri
            first,                     # anish
        ]

        lichess_user: Optional[str] = None
        chesscom_user: Optional[str] = None

        # Chess.com guessing
        for g in guesses:
            if chesscom_user:
                break
            try:
                self._throttle()
                resp = requests.get(
                    f"{_CHESSCOM_BASE}/player/{g}",
                    headers={"User-Agent": _UA},
                    timeout=10,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                fetched_name = data.get("name") or ""
                if not fetched_name:
                    continue
                score = fuzz.WRatio(_normalize_name(fetched_name), normalized)
                if score >= 85:
                    chesscom_user = data.get("username") or g
                    logger.info(
                        "Chess.com guess hit: %s -> %s (score=%d)",
                        real_name, chesscom_user, score,
                    )
                    break
            except Exception:
                continue

        # Lichess guessing
        for g in guesses:
            if lichess_user:
                break
            try:
                self._throttle()
                resp = requests.get(
                    f"{_LICHESS_BASE}/user/{g}",
                    headers={"User-Agent": _UA},
                    timeout=10,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if data.get("disabled"):
                    continue
                profile = data.get("profile") or {}
                fetched_name = profile.get("realName") or ""
                if not fetched_name:
                    continue
                score = fuzz.WRatio(_normalize_name(fetched_name), normalized)
                if score >= 85:
                    lichess_user = data.get("id") or data.get("username")
                    logger.info(
                        "Lichess guess hit: %s -> %s (score=%d)",
                        real_name, lichess_user, score,
                    )
                    break
            except Exception:
                continue

        if lichess_user or chesscom_user:
            return ResolvedUser(
                real_name=real_name,
                lichess=lichess_user,
                chesscom=chesscom_user,
                resolved_at=datetime.now(timezone.utc).isoformat(),
            )
        return None


# ── Module-level helpers ───────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    if not name:
        return ""
    n = unicodedata.normalize("NFD", name)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = n.lower().strip()
    return " ".join(n.split())


# ── Singleton ──────────────────────────────────────────────────────

_singleton: Optional[ChessUsernameResolver] = None
_singleton_lock = threading.Lock()


def get_resolver() -> ChessUsernameResolver:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = ChessUsernameResolver()
    return _singleton
