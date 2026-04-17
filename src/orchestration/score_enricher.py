"""Score enricher — ESPN primary + Odds API fallback (SPEC-005 Task 4).

Light cycle içinde periyodik çağrılır (poll_normal_sec / poll_critical_sec).
Sadece maç penceresindeki pozisyonlar için API çağrısı yapar.

Dispatch kuralı:
  - sport_rules'dan score_source okunur
  - score_source == "espn" → ESPN önce, Odds API fallback (tennis hariç)
  - score_source yok → skor yok, geç
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict

from datetime import datetime, timezone

from src.config.sport_rules import _normalize, get_sport_rule
from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.infrastructure.apis.score_client import MatchScore, fetch_scores
from src.models.position import Position
from src.strategy.enrichment.question_parser import extract_teams

logger = logging.getLogger(__name__)

# Odds API key mapping (fallback için)
_ODDS_API_KEY_MAP: dict[str, str] = {
    "nhl": "icehockey_nhl",
    "ahl": "icehockey_ahl",
    "hockey": "icehockey_nhl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nfl": "americanfootball_nfl",
}


# ── Pure helpers ──────────────────────────────────────────────────────────────

def _is_within_match_window(pos: Position, window_hours: float) -> bool:
    """Pozisyon maç penceresi içinde mi? (match_start ± window saat)."""
    if not pos.match_start_iso:
        return False
    try:
        start = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    now = datetime.now(timezone.utc)
    diff_hours = abs((now - start).total_seconds()) / 3600.0
    return diff_hours <= window_hours


def _team_match(pos_team: str, api_team: str) -> bool:
    """Polymarket team name ile API team name fuzzy eşleşmesi."""
    if not pos_team or not api_team:
        return False
    p = pos_team.lower().strip()
    a = api_team.lower().strip()
    if p == a:
        return True
    # Substring match: "Rangers" in "New York Rangers"
    if p in a or a in p:
        return True
    # Son kelime eşleşmesi: "New York Rangers" → "Rangers"
    p_last = p.rsplit(maxsplit=1)[-1] if " " in p else p
    a_last = a.rsplit(maxsplit=1)[-1] if " " in a else a
    return p_last == a_last and len(p_last) >= 3


def _resolve_tennis_league(slug: str) -> str:
    """WTA/ATP league resolver: slug "wta-*" ise "wta", aksi halde "atp"."""
    return "wta" if (slug or "").lower().startswith("wta") else "atp"


def _find_espn_match(pos: Position, scores: list[ESPNMatchScore]) -> ESPNMatchScore | None:
    """Pozisyonu ESPN skor listesiyle eşleştir (home_name/away_name)."""
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None
    for ms in scores:
        home_a = _team_match(team_a, ms.home_name)
        home_b = _team_match(team_b or "", ms.home_name) if team_b else False
        away_a = _team_match(team_a, ms.away_name)
        away_b = _team_match(team_b or "", ms.away_name) if team_b else False
        if (home_a and away_b) or (home_b and away_a) or (home_a or away_a):
            return ms
    return None


def _find_match(pos: Position, scores: list[MatchScore]) -> MatchScore | None:
    """Pozisyonu Odds API skor listesiyle eşleştir (home_team/away_team)."""
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None
    for ms in scores:
        home_a = _team_match(team_a, ms.home_team)
        home_b = _team_match(team_b or "", ms.home_team) if team_b else False
        away_a = _team_match(team_a, ms.away_team)
        away_b = _team_match(team_b or "", ms.away_team) if team_b else False
        if (home_a and away_b) or (home_b and away_a) or (home_a or away_a):
            return ms
    return None


# MatchScore-like protocol: both MatchScore and ESPNMatchScore share home/away score fields.
# _build_score_info works with any object that has home_score, away_score, period, home_team/home_name.

def _build_score_info(pos: Position, ms: MatchScore | ESPNMatchScore) -> dict:
    """Eşleşen skor verisinden score_info dict oluştur (direction-aware).

    ESPN: home_name/away_name kullanır + linescores içerir.
    Odds API: home_team/away_team kullanır + linescores boş.
    """
    if ms.home_score is None or ms.away_score is None:
        return {"available": False}

    team_a, _ = extract_teams(pos.question)

    # home_name (ESPN) veya home_team (Odds API)
    home_field: str = getattr(ms, "home_name", None) or getattr(ms, "home_team", "")
    a_is_home = _team_match(team_a or "", home_field)

    if a_is_home:
        yes_score, no_score = ms.home_score, ms.away_score
    else:
        yes_score, no_score = ms.away_score, ms.home_score

    # Direction-aware: BUY_YES → YES side bizim; BUY_NO → NO side bizim
    if pos.direction == "BUY_YES":
        our_score, opp_score = yes_score, no_score
    else:
        our_score, opp_score = no_score, yes_score

    deficit = opp_score - our_score  # pozitif = gerideyiz
    linescores: list = getattr(ms, "linescores", []) or []

    # Direction-aware: our side = home?
    our_is_home = (pos.direction == "BUY_YES") == a_is_home

    return {
        "available": True,
        "our_score": our_score,
        "opp_score": opp_score,
        "deficit": deficit,
        "period": ms.period,
        "map_diff": -deficit,   # graduated_sl uyumu: pozitif = öndeyiz
        "linescores": linescores,
        "our_is_home": our_is_home,
    }


# ── ScoreEnricher ─────────────────────────────────────────────────────────────

class ScoreEnricher:
    """ESPN primary + Odds API fallback ile periyodik skor çekme ve eşleştirme."""

    def __init__(
        self,
        espn_client=None,
        odds_client=None,
        poll_normal_sec: int = 60,
        poll_critical_sec: int = 30,
        critical_price_threshold: float = 0.35,
        match_window_hours: float = 4.0,
    ) -> None:
        self._espn = espn_client
        self._odds = odds_client
        self._poll_normal_sec = poll_normal_sec
        self._poll_critical_sec = poll_critical_sec
        self._critical_threshold = critical_price_threshold
        self._window_hours = match_window_hours
        self._poll_sec: int = poll_normal_sec
        self._last_poll_ts: float = 0.0
        # sport_tag → list (ESPNMatchScore | MatchScore)
        self._cached_espn: dict[str, list[ESPNMatchScore]] = {}
        self._cached_odds: dict[str, list[MatchScore]] = {}

    def get_scores_if_due(self, positions: dict[str, Position]) -> dict[str, dict]:
        """Zamanlama uygunsa skor çek, pozisyonlarla eşleştir.

        Returns:
            {condition_id: score_info} dict. Eşleşme yoksa cid dahil olmaz.
        """
        self._update_poll_interval(positions)
        now = time.monotonic()
        if (now - self._last_poll_ts) < self._poll_sec:
            return self._match_cached(positions)

        self._last_poll_ts = now
        self._refresh_scores(positions)
        return self._match_cached(positions)

    # ── Private ───────────────────────────────────────────────────────────────

    def _update_poll_interval(self, positions: dict[str, Position]) -> None:
        """Kritik fiyat varsa poll_critical_sec, yoksa poll_normal_sec kullan."""
        min_price = min(
            (p.current_price for p in positions.values()),
            default=1.0,
        )
        self._poll_sec = (
            self._poll_critical_sec
            if min_price <= self._critical_threshold
            else self._poll_normal_sec
        )

    def _refresh_scores(self, positions: dict[str, Position]) -> None:
        """Maç penceresindeki pozisyonlar için sport bazında skor çek."""
        # sport_tag → pozisyon listesi (pencere içinde olanlar)
        sports: dict[str, list[Position]] = defaultdict(list)
        for pos in positions.values():
            if not _is_within_match_window(pos, self._window_hours):
                continue
            tag = _normalize(pos.sport_tag)
            if tag:
                sports[tag].append(pos)

        self._cached_espn.clear()
        self._cached_odds.clear()

        for tag, sport_positions in sports.items():
            score_source: str | None = get_sport_rule(tag, "score_source")
            if score_source != "espn":
                continue  # skor kaynağı yok, atla

            espn_sport: str = get_sport_rule(tag, "espn_sport", "")
            espn_league: str = get_sport_rule(tag, "espn_league", "")

            # Tenis için slug'dan league belirle
            if tag == "tennis":
                slug = sport_positions[0].slug if sport_positions else ""
                espn_league = _resolve_tennis_league(slug)

            espn_scores = self._fetch_espn(espn_sport, espn_league)

            if espn_scores:
                self._cached_espn[tag] = espn_scores
            elif tag != "tennis" and self._odds is not None:
                # ESPN başarısız + tenis değil → Odds API fallback
                odds_key = _ODDS_API_KEY_MAP.get(tag, "")
                if odds_key:
                    odds_scores = fetch_scores(self._odds, odds_key)
                    if odds_scores:
                        self._cached_odds[tag] = odds_scores
                        logger.info("Odds API fallback: %s → %d events", odds_key, len(odds_scores))

    def _fetch_espn(self, sport: str, league: str) -> list[ESPNMatchScore]:
        """ESPN client çağrısı; hata → boş liste + WARNING log."""
        if self._espn is None or not sport or not league:
            return []
        try:
            scores = self._espn.fetch(sport, league)
            if scores:
                logger.info("ESPN fetch: %s/%s → %d events", sport, league, len(scores))
            return scores
        except Exception as exc:  # noqa: BLE001
            logger.warning("ESPN fetch error [%s/%s]: %s", sport, league, exc)
            return []

    def _match_cached(self, positions: dict[str, Position]) -> dict[str, dict]:
        """Cached skor verisiyle pozisyonları eşleştir."""
        result: dict[str, dict] = {}
        for cid, pos in positions.items():
            tag = _normalize(pos.sport_tag)

            # ESPN cache öncelikli
            espn_scores = self._cached_espn.get(tag, [])
            if espn_scores:
                em = _find_espn_match(pos, espn_scores)
                if em:
                    result[cid] = _build_score_info(pos, em)
                    continue

            # Odds API fallback cache
            odds_scores = self._cached_odds.get(tag, [])
            if odds_scores:
                ms = _find_match(pos, odds_scores)
                if ms:
                    result[cid] = _build_score_info(pos, ms)

        return result
