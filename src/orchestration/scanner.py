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
from datetime import datetime, timedelta, timezone

from src.config.settings import ScannerConfig
from src.infrastructure.apis.gamma_client import GammaClient
from src.models.market import MarketData

logger = logging.getLogger(__name__)


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
        """Tüm flow: Gamma fetch → filter → sort → top N."""
        raw = self._gamma.fetch_events()
        filtered = [m for m in raw if self._passes_filters(m)]
        filtered.sort(key=_sort_key)
        top = filtered[: self.config.max_markets_per_cycle]
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
