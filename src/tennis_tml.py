"""Tennis match data from TML-Database (Tennismylife GitHub) -- ATP only.

Forever-free, MIT-licensed ATP match archive with scores, surface, ranking, and
tournament metadata. Used as supplementary data source when ESPN returns thin
match history (<6 [W]/[L] tokens -> B- confidence -> bot blocked).

Merges current + previous year CSVs to guarantee >=10 matches per active top-200
ATP player year-round, including the January sparse-data window.

WTA is NOT supported -- TML only publishes ATP data. WTA markets skip this
fallback and rely on ESPN only (see TODO.md gap note).
"""
from __future__ import annotations

import csv
import io
import logging
import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from rapidfuzz import fuzz, process

from src.config import load_config

logger = logging.getLogger(__name__)

_TML_BASE = "https://raw.githubusercontent.com/Tennismylife/TML-Database/master"
_CACHE_DIR = Path("logs/tennis_cache")


@dataclass
class TMLMatch:
    date: str       # YYYYMMDD
    tourney: str
    surface: str
    winner: str
    loser: str
    score: str
    w_rank: Optional[int]
    l_rank: Optional[int]


class TennisTMLClient:
    """Forever-free ATP match data from TML GitHub CSV.

    Thread-safe singleton. Caches merged CSV in memory with 6-hour refresh.
    Persists to disk for offline warm starts.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._matches: list[TMLMatch] = []
        self._player_names_normalized: set[str] = set()
        self._loaded_at: float = 0.0
        self._cfg = load_config().tennis

    # ── Loading ────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        now = time.time()
        refresh_seconds = self._cfg.tml_refresh_hours * 3600
        if self._matches and (now - self._loaded_at) < refresh_seconds:
            return
        with self._lock:
            # Double-check after lock
            if self._matches and (now - self._loaded_at) < refresh_seconds:
                return
            self._load_merged_csv()

    def _load_merged_csv(self) -> None:
        """Fetch current + previous years and merge into memory."""
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        current_year = datetime.now(timezone.utc).year
        years = [current_year - i for i in range(self._cfg.tml_years_to_merge)]

        all_matches: list[TMLMatch] = []
        all_names: set[str] = set()

        for year in years:
            text = self._fetch_year_csv(year)
            if not text:
                continue
            parsed, names = self._parse_csv_text(text)
            all_matches.extend(parsed)
            all_names.update(names)

        # Sort by date descending for "most recent first" traversal
        all_matches.sort(key=lambda m: m.date, reverse=True)
        self._matches = all_matches
        self._player_names_normalized = all_names
        if all_matches:
            # Only mark as loaded on success. On total failure (network down AND
            # no disk cache), leave _loaded_at at 0 so the next call retries
            # instead of silently caching the empty state for tml_refresh_hours.
            self._loaded_at = time.time()
            logger.info(
                "TML loaded: %d matches, %d unique players (years=%s)",
                len(all_matches), len(all_names), years,
            )
        else:
            logger.warning(
                "TML load failed: 0 matches fetched from %s -- will retry next call",
                years,
            )

    def _fetch_year_csv(self, year: int) -> Optional[str]:
        """Fetch {year}.csv from GitHub raw, fall back to disk cache on failure."""
        url = f"{_TML_BASE}/{year}.csv"
        cache_path = _CACHE_DIR / f"tml_atp_{year}.csv"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            text = resp.text
            cache_path.write_text(text, encoding="utf-8")
            return text
        except Exception as exc:
            logger.warning("TML fetch failed for %d: %s -- trying disk cache", year, exc)
            if cache_path.exists():
                try:
                    return cache_path.read_text(encoding="utf-8")
                except Exception:
                    return None
            return None

    @staticmethod
    def _parse_csv_text(text: str) -> tuple[list[TMLMatch], set[str]]:
        matches: list[TMLMatch] = []
        names: set[str] = set()
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                winner = (row.get("winner_name") or "").strip()
                loser = (row.get("loser_name") or "").strip()
                if not winner or not loser:
                    continue
                w_rank_raw = (row.get("winner_rank") or "").strip()
                l_rank_raw = (row.get("loser_rank") or "").strip()
                m = TMLMatch(
                    date=(row.get("tourney_date") or "").strip(),
                    tourney=(row.get("tourney_name") or "").strip(),
                    surface=(row.get("surface") or "").strip(),
                    winner=winner,
                    loser=loser,
                    score=(row.get("score") or "").strip(),
                    w_rank=int(w_rank_raw) if w_rank_raw.isdigit() else None,
                    l_rank=int(l_rank_raw) if l_rank_raw.isdigit() else None,
                )
                matches.append(m)
                names.add(_normalize_name(winner))
                names.add(_normalize_name(loser))
            except (ValueError, KeyError):
                continue
        return matches, names

    # ── Query API ──────────────────────────────────────────────────

    def get_player_matches(
        self, name: str, limit: Optional[int] = None,
    ) -> list[tuple[TMLMatch, bool]]:
        """Return [(match, won), ...] for a player, most recent first."""
        self._ensure_loaded()
        if not self._matches:
            return []
        if limit is None:
            limit = self._cfg.tml_max_matches_per_player

        target = _normalize_name(name)
        if not target:
            return []
        # Fuzzy-resolve if exact not present
        if target not in self._player_names_normalized:
            best = process.extractOne(
                target, list(self._player_names_normalized),
                scorer=fuzz.WRatio, score_cutoff=85,
            )
            if not best:
                return []
            target = best[0]

        results: list[tuple[TMLMatch, bool]] = []
        for m in self._matches:
            if _normalize_name(m.winner) == target:
                results.append((m, True))
            elif _normalize_name(m.loser) == target:
                results.append((m, False))
            if len(results) >= limit:
                break
        return results

    def get_head_to_head(
        self, player_a: str, player_b: str, limit: Optional[int] = None,
    ) -> list[tuple[TMLMatch, bool]]:
        """Return [(match, a_won), ...] for H2H matches, most recent first."""
        self._ensure_loaded()
        if limit is None:
            limit = self._cfg.tml_max_h2h_matches
        a = _normalize_name(player_a)
        b = _normalize_name(player_b)
        if not a or not b:
            return []
        # Fuzzy-resolve both sides against the player index
        if a not in self._player_names_normalized:
            best_a = process.extractOne(
                a, list(self._player_names_normalized),
                scorer=fuzz.WRatio, score_cutoff=85,
            )
            if best_a:
                a = best_a[0]
        if b not in self._player_names_normalized:
            best_b = process.extractOne(
                b, list(self._player_names_normalized),
                scorer=fuzz.WRatio, score_cutoff=85,
            )
            if best_b:
                b = best_b[0]

        h2h: list[tuple[TMLMatch, bool]] = []
        for m in self._matches:
            w = _normalize_name(m.winner)
            l = _normalize_name(m.loser)
            if w == a and l == b:
                h2h.append((m, True))
            elif w == b and l == a:
                h2h.append((m, False))
            if len(h2h) >= limit:
                break
        return h2h

    # ── Context formatter ─────────────────────────────────────────

    def format_context(self, question: str, slug: str) -> Optional[str]:
        """Build ESPN-compatible context string with [W]/[L] tokens.

        Returns None if:
          - TML disabled in config
          - WTA market (not supported)
          - No matches found for either player
        """
        if not self._cfg.tml_enabled:
            return None

        # WTA skip
        q_lower = (question or "").lower()
        s_lower = (slug or "").lower()
        if "wta" in s_lower or "wta" in q_lower or s_lower.startswith("wta-"):
            logger.debug("TML skip WTA: %s", s_lower[:40])
            return None

        player_a, player_b = _parse_players_from_question(question)
        if not player_a or not player_b:
            # Weak fallback: try slug
            player_a, player_b = _parse_players_from_slug(slug)
            if not player_a or not player_b:
                return None

        self._ensure_loaded()
        if not self._matches:
            return None

        a_matches = self.get_player_matches(player_a)
        b_matches = self.get_player_matches(player_b)
        if not a_matches and not b_matches:
            return None

        parts: list[str] = ["=== TENNIS DATA (TML) -- ATP ==="]
        parts.extend(_format_player_block("PLAYER A", player_a, a_matches))
        parts.extend(_format_player_block("PLAYER B", player_b, b_matches))

        # H2H section
        h2h = self.get_head_to_head(player_a, player_b)
        if h2h:
            a_wins = sum(1 for _, a_won in h2h if a_won)
            b_wins = len(h2h) - a_wins
            parts.append("")
            parts.append(f"H2H: {player_a} {a_wins}-{b_wins} {player_b}")
            for m, a_won in h2h:
                opp_label = player_b if a_won else player_a
                result = "W" if a_won else "L"
                date_fmt = _format_date(m.date)
                parts.append(
                    f"    [{result}] vs {opp_label} ({m.score}) "
                    f"({m.tourney}, {date_fmt})"
                )

        parts.append("")
        parts.append(
            "This is an ATP tennis match. Use recent form, rankings, "
            "surface, and H2H to estimate win probability."
        )
        return "\n".join(parts)


# ── Module-level helpers ────────────────────────────────────────────────────

def _format_player_block(
    label: str, name: str, matches: list[tuple[TMLMatch, bool]],
) -> list[str]:
    """Render one player's recent form + [W]/[L] match history lines."""
    lines: list[str] = [""]
    if not matches:
        lines.append(f"{label}: {name} -- no recent TML matches")
        return lines
    wins = sum(1 for _, won in matches if won)
    losses = len(matches) - wins
    lines.append(f"{label}: {name}")
    lines.append(f"  Recent form ({len(matches)} matches): {wins}W-{losses}L")
    lines.append("  Recent matches:")
    for m, won in matches:
        opp = m.loser if won else m.winner
        result = "W" if won else "L"
        date_fmt = _format_date(m.date)
        surface_tag = f" [{m.surface}]" if m.surface else ""
        lines.append(
            f"    [{result}] vs {opp} ({m.score}){surface_tag} "
            f"({m.tourney}, {date_fmt})"
        )
    return lines


def _normalize_name(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace. For fuzzy matching only."""
    if not name:
        return ""
    n = unicodedata.normalize("NFD", name)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = n.lower().strip()
    return " ".join(n.split())


def _format_date(yyyymmdd: str) -> str:
    if len(yyyymmdd) == 8 and yyyymmdd.isdigit():
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return yyyymmdd or "?"


def _parse_players_from_question(question: str) -> tuple[Optional[str], Optional[str]]:
    """Extract (player_a, player_b) from Polymarket question text.

    Handles common patterns:
      'Will X beat Y'
      'Will X defeat Y'
      'X to beat Y'
      'X vs Y'
    """
    if not question:
        return None, None
    q = question.strip()
    patterns = [
        r'[Ww]ill\s+(.+?)\s+(?:beat|defeat|win against|win over)\s+(.+?)[\s?]*$',
        r'(.+?)\s+to\s+(?:beat|defeat)\s+(.+?)[\s?]*$',
        r'[Ww]ill\s+(.+?)\s+vs\.?\s+(.+?)\s*$',
    ]
    for pat in patterns:
        m = re.search(pat, q)
        if m:
            a = m.group(1).strip().rstrip("?").strip()
            b = m.group(2).strip().rstrip("?").strip()
            if len(a) >= 3 and len(b) >= 3:
                return a, b
    return None, None


def _parse_players_from_slug(slug: str) -> tuple[Optional[str], Optional[str]]:
    """Extract player tokens from slug like 'atp-sinner-machac-2026-04-09'.

    This is a WEAK fallback -- returns tokens that need fuzzy matching upstream.
    """
    if not slug:
        return None, None
    parts = slug.lower().split("-")
    if len(parts) < 3:
        return None, None
    non_date: list[str] = []
    for p in parts[1:]:  # skip sport prefix
        if len(p) == 4 and p.isdigit():
            break
        non_date.append(p)
    if len(non_date) >= 2:
        return non_date[0], non_date[1]
    return None, None


# ── Singleton access ────────────────────────────────────────────────────────

_singleton: Optional[TennisTMLClient] = None
_singleton_lock = threading.Lock()


def get_tennis_tml() -> TennisTMLClient:
    """Return the shared TennisTMLClient singleton (thread-safe)."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = TennisTMLClient()
    return _singleton
