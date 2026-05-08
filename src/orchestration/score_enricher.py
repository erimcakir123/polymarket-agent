"""Score enricher - sport-dispatch + ESPN primary + Odds fallback (SPEC-B Task 3).

Light cycle'da cagrilir. Pozisyonlardan essiz sport_tag'leri cikar, her sport icin
ESPN sorgu yap, position-based score_map doner.

Polling throttle: kritik fiyatli (<= threshold) pozisyon varsa aggressive interval,
yoksa normal interval. Sport bazli son fetch zamani state'te tutulur.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config.settings import ScoreConfig
from src.config.sport_rules import get_sport_rule
from src.infrastructure.apis.espn_client import ESPNClient, ESPNMatchScore
from src.models.position import Position

logger = logging.getLogger(__name__)


class ScoreEnricher:
    """Pozisyonlar icin skor cekme orkestratoru (SPEC-B)."""

    def __init__(
        self,
        espn_client: ESPNClient,
        odds_client: Any,
        config: ScoreConfig,
    ) -> None:
        self._espn = espn_client
        self._odds = odds_client
        self._cfg = config
        self._last_fetch: dict[str, datetime] = {}

    def get_scores_if_due(
        self,
        positions: dict[str, Position],
    ) -> dict[str, dict]:
        """Polling-throttled score map doner: condition_id -> score_info.

        Disabled config -> {} doner.
        """
        if not self._cfg.enabled or not positions:
            return {}

        # Sport bazli essiz key'leri belirle (espn_sport+espn_league)
        sport_keys: dict[str, list[Position]] = {}
        for pos in positions.values():
            sport_tag = (pos.sport_tag or "").lower()
            score_source = get_sport_rule(sport_tag, "score_source", default=None)
            if score_source != "espn":
                continue
            espn_sport = get_sport_rule(sport_tag, "espn_sport")
            espn_league = get_sport_rule(sport_tag, "espn_league")
            if not espn_sport or not espn_league:
                continue
            key = f"{espn_sport}/{espn_league}"
            sport_keys.setdefault(key, []).append(pos)

        if not sport_keys:
            return {}

        # Polling throttle - fiyat esigi alti pozisyon varsa aggressive interval
        is_critical = any(
            (pos.current_price or 1.0) <= self._cfg.critical_price_threshold
            for pos in positions.values()
        )
        interval_sec = self._cfg.poll_critical_sec if is_critical else self._cfg.poll_normal_sec
        now = datetime.now(timezone.utc)

        score_map: dict[str, dict] = {}
        for key, pos_list in sport_keys.items():
            last = self._last_fetch.get(key)
            if last is not None and (now - last) < timedelta(seconds=interval_sec):
                continue

            espn_sport, espn_league = key.split("/", 1)
            scores = self._espn.fetch_scoreboard(espn_sport, espn_league)
            self._last_fetch[key] = now

            if not scores:
                # Fallback: Odds API skor - su an opt-in, varsayilan skip
                # (defensive - Odds API skoru opsiyonel)
                continue

            for pos in pos_list:
                matched = self._match_position_to_score(pos, scores)
                if matched is None:
                    continue
                score_map[pos.condition_id] = self._to_score_info(pos, matched)

        return score_map

    def _match_position_to_score(
        self,
        pos: Position,
        scores: list[ESPNMatchScore],
    ) -> ESPNMatchScore | None:
        """Pozisyon question/slug'ini ESPN home/away ile eslestir.

        Heuristic: question lowercase'inde home_name veya away_name gecerse match.
        Sadece is_live=True maclar dikkate alinir.
        """
        q = (pos.question or pos.slug or "").lower()
        for s in scores:
            if not s.is_live:
                continue
            home_lower = (s.home_name or "").lower()
            away_lower = (s.away_name or "").lower()
            if home_lower and home_lower in q:
                return s
            if away_lower and away_lower in q:
                return s
        return None

    @staticmethod
    def _to_score_info(pos: Position, score: ESPNMatchScore) -> dict:
        """ESPNMatchScore -> monitor.evaluate'in bekledigi score_info dict."""
        if score.home_score is None or score.away_score is None:
            return {"available": False}
        q = (pos.question or "").lower()
        home_in_q = score.home_name and score.home_name.lower() in q
        if home_in_q:
            our, opp = score.home_score, score.away_score
        else:
            our, opp = score.away_score, score.home_score

        diff = our - opp
        return {
            "available": True,
            "our_score": our,
            "opp_score": opp,
            "deficit": -diff if diff < 0 else 0,
            "map_diff": diff,
            "period": score.period,
        }
