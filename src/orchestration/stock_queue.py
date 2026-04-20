"""Stock queue — persistent eligible pool + JIT enrichment order (TDD §11 Stock).

Scanner+gate'te sinyal ürettiği ya da no_edge yediği halde exposure_cap,
max_positions veya no_bookmaker_data nedeniyle reddedilen marketler burada
bekler. Her heavy cycle'da match_start ASC sıralanıp top N elemanı
re-evaluate edilir — Odds API kredisi yalnızca gerçekten değerlendirilecek
alt küme için harcanır.

Sorumluluklar:
  - add/remove/top_n_by_match_start/refresh_from_scan
  - TTL-based eviction (match-start cutoff, 24h idle, no_edge streak)
  - Persistence (snapshot dependency injection ile)

I/O yok: StockSnapshot infrastructure katmanı load/save'i yapar.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.models.market import MarketData

logger = logging.getLogger(__name__)


def _parse_iso(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


@dataclass
class StockEntry:
    """Tek market için stock state. MarketData canlı tutulur — her refresh'te
    yeni fiyat + liquidity ile güncellenir.
    """
    market: MarketData
    first_seen_iso: str
    last_eval_iso: str
    last_skip_reason: str
    stale_attempts: int = 0

    @property
    def condition_id(self) -> str:
        return self.market.condition_id

    @property
    def match_start_dt(self) -> datetime | None:
        return _parse_iso(self.market.match_start_iso)


@dataclass
class StockConfig:
    """Stock davranış parametreleri."""
    enabled: bool = True
    jit_batch_multiplier: int = 3         # empty_slots × bu = enrich edilecek max
    ttl_hours: float = 24.0               # first_seen üzerinden; aşınca düşür
    pre_match_cutoff_min: float = 30.0    # match_start'a bu dk kala düşür
    max_stale_attempts: int = 3           # peş peşe bu sayıda skip → düşür


_PUSHABLE_REASONS: frozenset[str] = frozenset({
    "exposure_cap_reached",
    "max_positions_reached",
    "no_edge",
    "no_bookmaker_data",
    "circuit_breaker",
})


class StockQueue:
    """Persistent eligible pool — in-memory dict + snapshot delegation."""

    def __init__(self, config: StockConfig, snapshot=None) -> None:
        self.config = config
        self._entries: dict[str, StockEntry] = {}
        self._snapshot = snapshot  # opsiyonel: StockSnapshot veya benzer

    # ── CRUD ──

    def add(self, market: MarketData, skip_reason: str) -> bool:
        """Market'i stock'a ekle. Reason pushable değilse False döner.

        Varsa mevcut entry güncellenir (last_skip_reason, last_eval, stale_attempts).
        """
        if skip_reason not in _PUSHABLE_REASONS:
            return False
        cid = market.condition_id
        now_iso = datetime.now(timezone.utc).isoformat()
        existing = self._entries.get(cid)
        if existing is None:
            self._entries[cid] = StockEntry(
                market=market,
                first_seen_iso=now_iso,
                last_eval_iso=now_iso,
                last_skip_reason=skip_reason,
                stale_attempts=1,
            )
        else:
            existing.market = market
            existing.last_eval_iso = now_iso
            existing.last_skip_reason = skip_reason
            existing.stale_attempts += 1
        return True

    def remove(self, condition_id: str) -> None:
        self._entries.pop(condition_id, None)

    def has(self, condition_id: str) -> bool:
        return condition_id in self._entries

    def count(self) -> int:
        return len(self._entries)

    def all_entries(self) -> list[StockEntry]:
        """Read-only kopya — sıralama garanti edilmez."""
        return list(self._entries.values())

    # ── Scan entegrasyonu ──

    def refresh_from_scan(self, scan_by_cid: dict[str, MarketData]) -> int:
        """Taze scan sonucuyla MarketData'yı güncelle (yeni fiyat/liquidity).

        scan'de olmayan stock entry'leri SİLİNİR (market artık listelenmiyor).
        Dönüş: refresh edilen entry sayısı.
        """
        refreshed = 0
        to_drop: list[str] = []
        for cid, entry in self._entries.items():
            fresh = scan_by_cid.get(cid)
            if fresh is None:
                to_drop.append(cid)
            else:
                entry.market = fresh
                refreshed += 1
        for cid in to_drop:
            self._entries.pop(cid, None)
        if to_drop:
            logger.info("Stock refresh: %d entry dropped (delisted)", len(to_drop))
        return refreshed

    def evict_expired(
        self,
        now: datetime | None = None,
        open_event_ids: frozenset[str] = frozenset(),
    ) -> int:
        """TTL kurallarını uygula. Dönüş: evict edilen sayı.

        Kurallar:
          - first_seen'den ttl_hours geçti
          - match_start - pre_match_cutoff_min geçti
          - event_id açık pozisyon listesindeyse
          - stale_attempts >= max_stale_attempts
        """
        now = now or datetime.now(timezone.utc)
        ttl_delta = timedelta(hours=self.config.ttl_hours)
        cutoff_delta = timedelta(minutes=self.config.pre_match_cutoff_min)
        to_drop: list[str] = []
        for cid, entry in self._entries.items():
            first_seen = _parse_iso(entry.first_seen_iso)
            if first_seen and (now - first_seen) >= ttl_delta:
                to_drop.append(cid)
                continue
            match_start = entry.match_start_dt
            if match_start and (match_start - now) <= cutoff_delta:
                to_drop.append(cid)
                continue
            if entry.market.event_id and entry.market.event_id in open_event_ids:
                to_drop.append(cid)
                continue
            if entry.stale_attempts >= self.config.max_stale_attempts:
                to_drop.append(cid)
                continue
        for cid in to_drop:
            self._entries.pop(cid, None)
        if to_drop:
            logger.info("Stock evict: %d expired", len(to_drop))
        return len(to_drop)

    # ── JIT batch ──

    def top_n_by_match_start(self, n: int) -> list[MarketData]:
        """En yakın match_start'a sahip ilk N entry'nin MarketData'sını döner.

        match_start olmayan entry'ler sona atılır (+inf). Tie-break: volume_24h DESC.
        """
        if n <= 0 or not self._entries:
            return []
        sorted_entries = sorted(
            self._entries.values(),
            key=lambda e: (
                (e.match_start_dt or datetime.max.replace(tzinfo=timezone.utc)),
                -e.market.volume_24h,
            ),
        )
        return [e.market for e in sorted_entries[:n]]

    # ── Persistence delegation ──

    def load(self) -> int:
        """Snapshot'tan restore et. Dönüş: yüklenen entry sayısı."""
        if self._snapshot is None:
            return 0
        entries = self._snapshot.load()
        self._entries = {e.condition_id: e for e in entries}
        return len(self._entries)

    def save(self) -> None:
        """Snapshot'a yaz."""
        if self._snapshot is None:
            return
        self._snapshot.dump(list(self._entries.values()))
