"""Market scanner — Gamma fetch + tennis-start enrich + filter + chronological priority sort.

Davranış (memory/project_scanner_behavior.md):
  - Enrich: tennis market'lerin match_start_iso'su ESPN ile override edilir
    (TennisStartEnricher; opsiyonel DI).
  - Filter: sports_market_type=moneyline, allowed_sport_tags, liquidity ≥ min,
    end_date ≤ max_duration_days
  - Sort: 4-bucket chronological priority (imminent ≤6h → unknown_time ≤48h →
    midrange 6-24h → discovery >24h); bucket içinde hours ASC → volume_24h DESC
  - Top N (config.scanner.max_markets_per_cycle)

Stock pool StockQueue (orchestration/stock_queue.py) tarafından yönetilir —
scanner yalnızca fresh fetch + enrich + filter + sort sorumluluğu taşır.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from src.config.settings import ScannerConfig
from src.config.sport_rules import BASKETBALL_TAGS, anchor_source, is_moneyline_only, is_spread_blocked
from src.infrastructure.apis.gamma_client import GammaClient
from src.models.market import MarketData
from src.strategy.entry.mlb_submarket_engine_protocol import MlbSubmarketEngineProtocol

if TYPE_CHECKING:
    from src.orchestration.tennis_start_enricher import TennisStartEnricher

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


def classify_anchor_path(market: MarketData) -> str:
    """Bir market için anchor kaynağı: 'bookmaker' veya 'model'.

    sport_rules.anchor_source wrapper — scanner içinde tek nokta.
    """
    return anchor_source(market.sport_tag, market.sports_market_type)


def collect_model_signals(
    *,
    candidates: list[MarketData],
    engine: MlbSubmarketEngineProtocol | None,
) -> tuple[list, list]:
    """Model-anchor signal toplama (SPEC-R).

    Args:
        candidates: Scan'den gelen tüm market'ler.
        engine: MlbSubmarketEngine instance veya None (disabled config).

    Returns:
        (markets, signals): engine.process'in edge ürettiği çiftler.
        Engine None ise veya hiç model-path market yoksa ([], []).
    """
    if engine is None:
        return [], []
    markets: list = []
    signals: list = []
    for m in candidates:
        if classify_anchor_path(m) != "model":
            continue
        signal = engine.process(m)
        if signal is None:
            continue
        markets.append(m)
        signals.append(signal)
    return markets, signals


class MarketScanner:
    """Gamma → filter → sort → top N. Eligible-queue dahil."""

    def __init__(
        self,
        config: ScannerConfig,
        gamma_client: GammaClient | None = None,
        tennis_start_enricher: "TennisStartEnricher | None" = None,
    ) -> None:
        self.config = config
        self._gamma = gamma_client or GammaClient()
        self._tennis_enricher = tennis_start_enricher

    # ── Public API ──

    def scan(self) -> list[MarketData]:
        """Tüm flow: Gamma fetch → filter → (tennis enrich filter-sonrası) → sort → top N.

        SPEC-Z2 (2026-05-24): tennis_enricher artık filter SONRASI çağrılıyor.
        Eskiden filter öncesi tüm 20k+ raw market'in tenis olanlarına ESPN call
        atıyordu → 6+ dakika cycle bloke. Tenis ana botta allowed_sport_tags'ten
        kaldırıldığı için (SPEC 2026-05-23) filter sonrası 0 tenis market kalır
        → enricher no-op. Açık tenis pozisyonlar için refresh_positions ayrı.
        """
        raw = self._gamma.fetch_events()
        filtered = [m for m in raw if self._passes_filters(m)]
        if self._tennis_enricher is not None:
            filtered = self._tennis_enricher.enrich(filtered)
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

        # SPEC-Z3 (2026-05-24): order book sanity. bestBid None → alıcı yok, pozisyon
        # gerçek dünyada açılamaz (sadece dry_run simulasyon kabul eder). Phantom
        # market detection: 2026-05-24 Detroit-Baltimore bug'ında market YES=0.005
        # ama bestBid None — bot fiyatı yanlış aldı, 4 phantom trade üretti. Bid yoksa
        # her durumda reddet (likidite varlığı sahte).
        if m.best_bid is None or m.best_bid <= 0.0:
            return False

        # Sports market type — SPEC-J: basketbol için spreads + totals da geçer.
        # Boş string (PGA Top-N props gibi) REDDEDILIR çünkü bookmaker h2h verisi yok.
        if m.sports_market_type not in ("moneyline", "spreads", "totals"):
            return False
        # spreads/totals sadece basketbol sport_tag için (NHL/MLB/diğer ayrı spec)
        if m.sports_market_type in ("spreads", "totals"):
            sport_tag_lc = (m.sport_tag or "").lower()
            if sport_tag_lc not in BASKETBALL_TAGS:
                return False
        # Moneyline-only flag (sport_rules.py tek-yer kaynak; SPEC-L NHL ML-only kanıtı).
        # Flag açıksa spreads/totals bu sport için reddedilir — basketbol kontrolüyle
        # örtüşür ama niyet farklı: flag, sport-spesifik kararı sport_rules'a bağlar.
        if is_moneyline_only(m.sport_tag) and m.sports_market_type != "moneyline":
            return False
        # Spread-blocked flag (NBA: Faz 1 Task 3 ile nba_spread_exit silindi + 0 trade
        # kanıtı; Faz 2'de veri ile yeniden açma kararı verilir).
        if is_spread_blocked(m.sport_tag) and m.sports_market_type == "spreads":
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
        """Maç en fazla `config.max_post_start_hours` önce başlamış olabilir (live maçlar dahil).
        Boş match_start → True (unknown_time bucket'ı zaten halleder).
        Çok eski match_start (sezon başı futures gibi) → False, atla.
        Bozuk match_start_iso (ParseError) → False (skip + log warning, SPEC-B audit#5).
        """
        if not m.match_start_iso:
            return True
        try:
            start = datetime.fromisoformat(m.match_start_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError) as e:
            logger.warning(
                "scanner: invalid match_start_iso=%r (slug=%s): %s — skip",
                m.match_start_iso, m.slug, e,
            )
            return False
        hours_since_start = (datetime.now(timezone.utc) - start).total_seconds() / 3600.0
        return hours_since_start <= self.config.max_post_start_hours

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
