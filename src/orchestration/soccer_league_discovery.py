"""Soccer ESPN league runtime discovery (PLAN-012).

Polymarket soccer slug'ı tek başına doğru ESPN league'i vermez — aynı ülkede
birden çok liig var (arg.1, arg.2, arg.copa ...). Bu modül:

1. Slug prefix'inden ülke kodu çıkar (arg / rus / uefa ...)
2. Learned cache'te (prefix, team_name) varsa → direkt döndür
3. Yoksa ESPN league listesinden prefix'le başlayanları al
4. Her aday league'in scoreboard'unu çek → question'daki takım adıyla eşleştir
5. Eşleşen ilk league → learned cache'e yaz + döndür

Orchestration/saf business — I/O dışarıdan inject edilir (test edilebilirlik).
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from src.domain.matching.pair_matcher import match_team
from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.infrastructure.persistence.soccer_league_cache import SoccerLeagueCache
from src.orchestration.score_helpers import slug_country_prefix
from src.strategy.enrichment.question_parser import extract_teams

logger = logging.getLogger(__name__)

_DEFAULT_MIN_CONFIDENCE = 0.80
_DEFAULT_MAX_CANDIDATES = 12  # aynı prefix için N'den fazla league denemeyiz


class SoccerLeagueDiscovery:
    """Polymarket soccer pozisyonu → doğru ESPN league slug'ını çöz."""

    def __init__(
        self,
        leagues_fetcher: Callable[[], list[str]],
        espn_fetcher: Callable[[str, str], list[ESPNMatchScore]],
        cache: SoccerLeagueCache,
        min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
        max_candidates: int = _DEFAULT_MAX_CANDIDATES,
    ) -> None:
        self._fetch_leagues = leagues_fetcher
        self._fetch_espn = espn_fetcher
        self._cache = cache
        self._min_confidence = min_confidence
        self._max_candidates = max_candidates

    def discover(self, pos) -> str | None:
        """Pozisyon için doğru ESPN league slug'ı döndür, bulunamazsa None."""
        slug = getattr(pos, "slug", "") or ""
        prefix = slug_country_prefix(slug)
        if not prefix:
            return None

        team_name = self._primary_team(pos)
        if not team_name:
            return None

        # 1. Learned cache
        learned = self._cache.get_learned(prefix, team_name)
        if learned:
            return learned

        # 2. ESPN league listesi (cache-miss durumunda fetch)
        leagues = self._cache.get_leagues()
        if not leagues:
            leagues = self._fetch_leagues() or []
            if leagues:
                self._cache.set_leagues(leagues)

        # 3. Prefix'e uyan aday league'ler
        candidates = [lg for lg in leagues if lg.split(".", 1)[0] == prefix]
        if not candidates:
            logger.warning(
                "soccer_discovery: no ESPN leagues for prefix=%r (pos slug=%s)",
                prefix, slug,
            )
            return None

        # 4. Adaylar arasında scoreboard + team match
        for league in candidates[: self._max_candidates]:
            scores = self._fetch_espn("soccer", league) or []
            matched = self._find_best_match(team_name, scores)
            if matched is not None:
                self._cache.set_learned(prefix, team_name, league)
                logger.info(
                    "soccer_discovery: learned prefix=%s team=%r → league=%s",
                    prefix, team_name, league,
                )
                return league

        logger.warning(
            "soccer_discovery: no league match for team=%r prefix=%s (tried %d candidates)",
            team_name, prefix, len(candidates),
        )
        return None

    # ── Private ───────────────────────────────────────────────────────────

    @staticmethod
    def _primary_team(pos) -> str:
        team_a, _ = extract_teams(getattr(pos, "question", "") or "")
        return team_a or ""

    def _find_best_match(
        self, team_name: str, scores: list[ESPNMatchScore],
    ) -> ESPNMatchScore | None:
        best: ESPNMatchScore | None = None
        best_conf = 0.0
        for s in scores:
            home = getattr(s, "home_name", "") or ""
            away = getattr(s, "away_name", "") or ""
            _, ch, _ = match_team(team_name, home)
            _, ca, _ = match_team(team_name, away)
            side = max(ch, ca)
            if side >= self._min_confidence and side > best_conf:
                best = s
                best_conf = side
        return best
