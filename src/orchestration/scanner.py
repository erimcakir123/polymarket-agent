"""Market scanner — Gamma fetch + filter + chronological priority sort.

Davranış (memory/project_scanner_behavior.md):
  - Filter: sports_market_type=moneyline, allowed_sport_tags, liquidity ≥ min,
    end_date ≤ max_duration_days
  - Sort: 4-bucket chronological priority (imminent ≤6h → unknown_time ≤48h →
    midrange 6-24h → discovery >24h); bucket içinde hours ASC → volume_24h DESC
  - Top N (config.scanner.max_markets_per_cycle)

Stock pool StockQueue (orchestration/stock_queue.py) tarafından yönetilir —
scanner yalnızca fresh fetch + filter + sort sorumluluğu taşır.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from src.config.settings import ScannerConfig
from src.config.sport_configs import get_sport_config
from src.domain.matching.three_way_title import enrich_three_way_titles
from src.infrastructure.apis.gamma_client import GammaClient
from src.models.market import MarketData

logger = logging.getLogger(__name__)

# SPEC-015: 3-way sum filter constants
_THREE_WAY_SUM_MIN = 0.95
_THREE_WAY_SUM_MAX = 1.05
_THREE_WAY_SPORTS = frozenset({"soccer", "rugby", "afl", "handball"})


def _is_excluded_competition(market: MarketData) -> bool:
    """SPEC-015: sport_config.excluded_competitions listesindeyse True (friendly/preseason)."""
    cfg = get_sport_config(market.sport_tag)
    if not cfg:
        return False
    excluded = cfg.get("excluded_competitions", [])
    if not excluded:
        return False
    tags_str = " ".join(t.lower() for t in (market.tags or []) if isinstance(t, str))
    question_str = (market.question or "").lower()
    text = f"{tags_str} {question_str}"
    return any(exc.lower() in text for exc in excluded)


def _is_three_way_sport(sport_tag: str) -> bool:
    s = (sport_tag or "").lower()
    return any(tw in s for tw in _THREE_WAY_SPORTS)


def _passes_three_way_sum_filter(markets: list[MarketData], event_id: str) -> bool:
    """SPEC-015: 3-way sport için event'teki market'lerin yes_price toplamı 0.95-1.05.

    2-way sporlar (event başına tek market) → her zaman geçer.
    3-way sport + 3 market → toplam check.
    3-way sport + 2 market → sum check (eksik market henüz listelenmemiş olabilir).
    3-way sport + 1 market → geçer (outlier, grup eksik, sum anlamsız).
    """
    if not markets or not event_id:
        return True
    sport = (markets[0].sport_tag or "").lower()
    if not _is_three_way_sport(sport):
        return True
    event_markets = [m for m in markets if m.event_id == event_id]
    if len(event_markets) < 2:
        return True  # tek market, sum check anlamsız
    total = sum(m.yes_price for m in event_markets)
    return _THREE_WAY_SUM_MIN <= total <= _THREE_WAY_SUM_MAX


def _hours_to_start(m: MarketData) -> float:
    """match_start_iso'dan kalan saat. Boşsa end_date_iso fallback. Hiçbiri → +inf."""
    raw = m.match_start_iso or m.end_date_iso
    if not raw:
        return float("inf")
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return float("inf")
    delta = (dt - datetime.now(timezone.utc)).total_seconds() / 3600.0
    return delta


def _sort_key(m: MarketData) -> tuple[int, float, float]:
    """4-bucket chronological priority + tie-break (hours ASC, volume DESC)."""
    hours = _hours_to_start(m)
    has_start = bool(m.match_start_iso)
    if has_start and hours <= 6:
        bucket = 0  # imminent
    elif not has_start and hours <= 48:
        bucket = 1  # unknown_time
    elif hours <= 24:
        bucket = 2  # midrange
    else:
        bucket = 3  # discovery
    return (bucket, hours, -m.volume_24h)


class MarketScanner:
    """Gamma → filter → sort → top N. Eligible-queue dahil."""

    def __init__(
        self,
        config: ScannerConfig,
        gamma_client: GammaClient | None = None,
    ) -> None:
        self.config = config
        self._gamma = gamma_client or GammaClient()

    # ── Public API ──

    def scan(self) -> list[MarketData]:
        """Tüm flow: Gamma fetch → filter → 3-way sum filter → sort → top N."""
        raw = self._gamma.fetch_events()
        filtered = [m for m in raw if self._passes_filters(m)]

        # SPEC-015: excluded_competitions (friendly/preseason) filter
        before = len(filtered)
        filtered = [m for m in filtered if not _is_excluded_competition(m)]
        if before != len(filtered):
            logger.info("Scanner: %d market dropped by excluded_competitions", before - len(filtered))

        # SPEC-015: 3-way sum filter (soccer/rugby/afl/handball double-chance/handicap eler)
        event_groups: dict[str, list[MarketData]] = defaultdict(list)
        for m in filtered:
            if m.event_id:
                event_groups[m.event_id].append(m)

        dropped_event_ids: set[str] = set()
        for eid, ems in event_groups.items():
            if not _passes_three_way_sum_filter(ems, eid):
                dropped_event_ids.add(eid)

        if dropped_event_ids:
            before = len(filtered)
            filtered = [m for m in filtered if m.event_id not in dropped_event_ids]
            logger.info(
                "Scanner: %d market dropped by three_way_sum_filter (%d events)",
                before - len(filtered), len(dropped_event_ids),
            )

        filtered.sort(key=_sort_key)
        top = filtered[: self.config.max_markets_per_cycle]
        # SPEC-015: 3-way home/away sub-market'lerinin match_title alanını
        # draw sub-market'in question'ından türet. 2-way market'ler no-op.
        top = enrich_three_way_titles(top)
        logger.info("Scanner: %d raw → %d filtered → top %d",
                    len(raw), len(filtered), len(top))
        return top

    # ── Filters ──

    def _passes_filters(self, m: MarketData) -> bool:
        """Config kurallarına göre filter. Tek bool."""
        if m.closed or m.resolved or not m.accepting_orders:
            return False

        # Fiyat-based resolved detection — Polymarket flag lag (closed/resolved)
        # güvenilmez; yes_price ~1.0 veya ~0.0 ise sonuç belli, market ölü.
        th = self.config.resolved_price_threshold
        if m.yes_price >= th or m.yes_price <= (1.0 - th):
            return False

        # Sports market type — STRICT: sadece h2h moneyline kabul.
        # Boş string (PGA Top-N props gibi) REDDEDILIR çünkü bookmaker h2h verisi yok.
        if m.sports_market_type != "moneyline":
            return False

        # Sport tag whitelist (MVP)
        if self.config.allowed_sport_tags:
            if not self._sport_tag_allowed(m.sport_tag):
                return False

        # Min likidite
        if m.liquidity < self.config.min_liquidity:
            return False

        # Max süre (futures'ları ele — end_date N günden uzaktaysa atla)
        if not self._within_duration(m):
            return False

        # Odds API h2h penceresi — maç > max_hours_to_start sonraysa bookmaker verisi
        # alamayacağız; stock'a eklenip boşa beklemesin.
        if _hours_to_start(m) > self.config.max_hours_to_start:
            return False

        # Stale match_start: maç 8+ saat önce başlamışsa atla
        # (sezon-uzunluğu futures'lar match_start=sezon başı çok eski tarih atar
        # ve bucket-0 imminent'a düşer; bunu eler)
        if not self._match_start_recent_or_future(m):
            return False

        return True

    def _sport_tag_allowed(self, tag: str) -> bool:
        """Tag whitelist içinde mi? tennis_* joker karakter desteklenir."""
        if not tag:
            return False
        tag_low = tag.lower()
        for allowed in self.config.allowed_sport_tags:
            al = allowed.lower()
            if al.endswith("*"):
                if tag_low.startswith(al[:-1]):
                    return True
            elif tag_low == al:
                return True
        return False

    def _match_start_recent_or_future(self, m: MarketData) -> bool:
        """Maç en fazla 8 saat önce başlamış olabilir (live maçlar dahil).
        Boş match_start → True (unknown_time bucket'ı zaten halleder).
        Çok eski match_start (sezon başı futures gibi) → False, atla.
        """
        if not m.match_start_iso:
            return True
        try:
            start = datetime.fromisoformat(m.match_start_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return True
        hours_since_start = (datetime.now(timezone.utc) - start).total_seconds() / 3600.0
        return hours_since_start <= 8.0

    def _within_duration(self, m: MarketData) -> bool:
        """end_date_iso ≤ max_duration_days günler içinde mi?"""
        if not m.end_date_iso:
            return False
        try:
            end = datetime.fromisoformat(m.end_date_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return False
        cutoff = datetime.now(timezone.utc) + timedelta(days=self.config.max_duration_days)
        return end <= cutoff
