"""Score enricher — ESPN primary + Odds API fallback (SPEC-005 Task 4).

Light cycle içinde periyodik çağrılır (poll_normal_sec / poll_critical_sec).
Sadece maç penceresindeki pozisyonlar için API çağrısı yapar.

Dispatch table:
- score_source="espn": ESPN primary + Odds API fallback (tennis hariç)
- score_source="cricapi": CricketAPIClient via cricket_score_builder (SPEC-011)
- missing: skip silently
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict

from datetime import datetime, timezone

from src.config.sport_rules import _normalize, get_sport_rule, is_cricket_sport
from src.domain.matching.pair_matcher import match_pair, match_team
from src.infrastructure.apis.cricket_client import CricketAPIClient, CricketMatchScore
from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.infrastructure.apis.score_client import MatchScore, fetch_scores
from src.infrastructure.persistence.archive_logger import (
    ArchiveLogger,
    ArchiveMatchResult,
    ArchiveScoreEvent,
)
from src.models.position import Position
from src.orchestration.cricket_score_builder import build_cricket_score_info, find_cricket_match
from src.orchestration.soccer_score_builder import determine_our_outcome as _soccer_our_outcome, is_knockout_competition as _soccer_is_knockout  # noqa: E501
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


def _resolve_tennis_league(slug: str) -> str:
    """WTA/ATP league resolver: slug "wta-*" ise "wta", aksi halde "atp"."""
    return "wta" if (slug or "").lower().startswith("wta") else "atp"


def _find_match_via_pair(
    pos: Position,
    scores: list,
    home_attr: str,
    away_attr: str,
    min_confidence: float = 0.80,
) -> object | None:
    """pair_matcher kullanarak skor listesinden eslesen event'i bul.

    home_attr/away_attr: ESPN icin "home_name"/"away_name", Odds API icin
    "home_team"/"away_team". Ayni logic her iki kaynakta calisir.

    Pair matching: team_a + team_b verildi → her iki takim da eslemeli
    (swap destekli). Sadece team_a verildi → single-team fallback.
    """
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None

    best_match = None
    best_conf = 0.0

    for ms in scores:
        home = getattr(ms, home_attr, "") or ""
        away = getattr(ms, away_attr, "") or ""
        if not home or not away:
            continue

        if team_b:
            # Pair matching: HER IKI takim da eslemeli (normal + swap)
            is_match, conf = match_pair((team_a, team_b), (home, away))
            if is_match and conf > best_conf:
                best_match = ms
                best_conf = conf
        else:
            # Single team fallback
            mh, ch, _ = match_team(team_a, home)
            ma, ca, _ = match_team(team_a, away)
            best_side = max(ch, ca)
            if (mh or ma) and best_side > best_conf:
                best_match = ms
                best_conf = best_side

    return best_match if best_conf >= min_confidence else None


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
    a_is_home, _, _ = match_team(team_a or "", home_field)

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
        "inning": getattr(ms, "inning", None),   # SPEC-014: MLB inning int (None = N/A)
        "map_diff": -deficit,   # pozitif = öndeyiz (never_in_profit / hold_revoked uyumu)
        "linescores": linescores,
        "our_is_home": our_is_home,
        "espn_start": getattr(ms, "commence_time", ""),
        "minute": getattr(ms, "minute", None),
        "regulation_state": getattr(ms, "regulation_state", ""),
        "our_outcome": _soccer_our_outcome(pos),
        "knockout": _soccer_is_knockout(pos),
        "period_number": getattr(ms, "period_number", None),   # SPEC-A4: NBA/NFL int period
        "clock_seconds": getattr(ms, "clock_seconds", None),   # SPEC-A4: NBA/NFL kalan saniye
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
        archive_logger: ArchiveLogger | None = None,
        cricket_client: CricketAPIClient | None = None,
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
        self._archive_logger = archive_logger
        self._cricket_client = cricket_client
        self._cached_cricket: list[CricketMatchScore] = []
        # event_id → last known score string (skor degisikligi tespiti icin — SPEC-009)
        self._prev_score_by_event: dict[str, str] = {}
        # event_id set'i — daha once match_result log'landi mi? Startup'ta
        # archive'dan yuklenir (duplicate engellemesi).
        self._logged_match_event_ids: set[str] = (
            archive_logger.load_logged_match_event_ids()
            if archive_logger is not None else set()
        )

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

        # Cricket (SPEC-011)
        has_cricket = any(
            is_cricket_sport(pos.sport_tag)
            for pos in positions.values()
            if _is_within_match_window(pos, self._window_hours)
        )
        if has_cricket and self._cricket_client is not None:
            matches = self._cricket_client.get_current_matches()
            if matches is not None:
                self._cached_cricket = matches

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
            # Cricket (SPEC-011)
            if is_cricket_sport(pos.sport_tag):
                if self._cached_cricket:
                    match = find_cricket_match(pos, self._cached_cricket)
                    if match is not None:
                        result[cid] = build_cricket_score_info(pos, match)
                continue

            tag = _normalize(pos.sport_tag)
            matched_score_obj = None

            # ESPN cache öncelikli
            espn_scores = self._cached_espn.get(tag, [])
            if espn_scores:
                em = _find_match_via_pair(pos, espn_scores, "home_name", "away_name")
                if em:
                    result[cid] = _build_score_info(pos, em)
                    matched_score_obj = em

            # Odds API fallback cache (ESPN yoksa)
            if matched_score_obj is None:
                odds_scores = self._cached_odds.get(tag, [])
                if odds_scores:
                    ms = _find_match_via_pair(pos, odds_scores, "home_team", "away_team")
                    if ms:
                        result[cid] = _build_score_info(pos, ms)
                        matched_score_obj = ms

            # Archive: skor degisikligi + match result (SPEC-009)
            if matched_score_obj is not None:
                # SPEC-014: Pozisyon state mutasyonu — match_score/period yaz
                pos.match_score = (
                    f"{matched_score_obj.home_score}-{matched_score_obj.away_score}"
                )
                pos.match_period = getattr(matched_score_obj, "period", "") or ""
                self._maybe_log_score_event(pos, matched_score_obj)
                self._maybe_log_match_result(pos, matched_score_obj)

        return result

    def _maybe_log_score_event(self, pos: Position, ms: object) -> None:
        """Skor degisikligini tespit edip archive'a yaz (SPEC-009)."""
        if self._archive_logger is None:
            return
        event_id = getattr(pos, "event_id", "") or ""
        if not event_id:
            return
        home_score = getattr(ms, "home_score", None)
        away_score = getattr(ms, "away_score", None)
        if home_score is None or away_score is None:
            return
        new_score = f"{home_score}-{away_score}"
        prev_score = self._prev_score_by_event.get(event_id, "")
        # Ilk sefer (prev yok) → log atma, sadece kaydet
        if prev_score == "":
            self._prev_score_by_event[event_id] = new_score
            return
        if new_score == prev_score:
            return
        # Degisiklik var → archive'a yaz
        self._archive_logger.log_score_event(ArchiveScoreEvent(
            event_id=event_id,
            slug=pos.slug,
            sport_tag=pos.sport_tag,
            timestamp=datetime.now(timezone.utc).isoformat(),
            prev_score=prev_score,
            new_score=new_score,
            period=getattr(ms, "period", "") or "",
        ))
        self._prev_score_by_event[event_id] = new_score

    def _maybe_log_match_result(self, pos: Position, ms: object) -> None:
        """Mac tamamlandiysa match_result log'la (SPEC-009). Duplicate atma."""
        if self._archive_logger is None:
            return
        is_completed = getattr(ms, "is_completed", False)
        if not is_completed:
            return
        event_id = getattr(pos, "event_id", "") or ""
        if not event_id or event_id in self._logged_match_event_ids:
            return
        home_score = getattr(ms, "home_score", None)
        away_score = getattr(ms, "away_score", None)
        if home_score is None or away_score is None:
            return
        winner_home: bool | None = None
        if home_score > away_score:
            winner_home = True
        elif away_score > home_score:
            winner_home = False
        # esit skor (draw) → None kalir

        self._archive_logger.log_match_result(ArchiveMatchResult(
            event_id=event_id,
            slug=pos.slug,
            sport_tag=pos.sport_tag,
            final_score=f"{home_score}-{away_score}",
            winner_home=winner_home,
            completed_timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        self._logged_match_event_ids.add(event_id)
