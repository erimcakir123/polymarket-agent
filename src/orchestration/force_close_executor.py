"""Force-close orchestration — deep-loss positions whose match has ended.

SPEC: docs/superpowers/specs/2026-05-27-force-close-design.md (Task 6).

Akış:
  1. ExitProcessor.run_light normal exit chain'i çalıştırdı, exit_signal=None döndü.
  2. Pozisyon -%50+ zarardaysa (CPU + false-positive guard) force-close kontrol.
  3. ESPN status varsa öncelik (event bitti mi?) — yoksa elapsed-time fallback.
  4. Sinyal varsa: bid book walk (full slippage bypass) → realize @ avg_price.
     Bid yoksa: realize @ 0 (FORCE_CLOSE_NO_BIDS, tam kayıp).

ARCH_GUARD: exit_processor.py 400-satır sınırını korumak için ayrı modül.
Hiçbir state mutation burada YOK — finalize çağrıları ExitProcessor'da kalıyor
(`_finalize_full_exit` helper). DRY: executor._fetch_book + paper_fill.walk_book_sell
reuse — ayrı orderbook client veya kendi walk loop'u yok.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.infrastructure.paper_fill import walk_book_sell
from src.models.enums import ExitReason
from src.models.position import Position
from src.strategy.exit.time_force_close import ForceCloseSignal, check as fc_check

logger = logging.getLogger(__name__)

# Force-close sadece derin zararlı pozisyonlarda — gereksiz ESPN/book fetch'i önle.
# Eşik: unrealized_pnl_pct <= -50% (üstü normal SL/graduated chain'in sorumluluğu).
_DEEP_LOSS_GATE_PCT = -0.50

# ESPN scoreboard polling TTL — light cycle her 30sn çalışıyor, ESPN her cycle
# çağırmak gereksiz; 60sn cache window dakikada en çok 1 ESPN call/event.
_ESPN_CACHE_TTL_SECONDS = 60.0

# walk_book_sell tam bypass için %100 slip — force-close "her fiyata sat" demek.
_FULL_BYPASS_SLIPPAGE = 1.0

# walk_book_sell target_price'i 0 olamaz (REJECTED döner); current_price 0 ise
# bu fallback ile bid book yine de yürünür (min_acceptable_price ≈ 0).
_TARGET_PRICE_FLOOR = 0.001


class ForceCloseExecutor:
    """Pozisyon başına force-close kararı + sıvılaştırma.

    Constructor minimal: gerekli infra (espn_client, executor — book fetch için)
    ExitProcessor üzerinden geliyor. State mutation YOK; ExitProcessor finalize
    helper'ını çağırır.
    """

    def __init__(self, espn_client: Any | None, executor: Any) -> None:
        self._espn = espn_client
        self._executor = executor
        # event_id -> (timestamp, MatchStatus | None). Process-yaşam süresince
        # in-memory; reboot temizler (ESPN status zaten short-lived).
        self._espn_cache: dict[str, tuple[float, Any]] = {}

    def check(
        self,
        pos: Position,
        timeouts: dict[str, int],
    ) -> ForceCloseSignal | None:
        """None = force-close yok; ForceCloseSignal = tetiklendi."""
        if pos.unrealized_pnl_pct >= _DEEP_LOSS_GATE_PCT:
            return None
        if not timeouts:
            return None  # feature disabled

        espn_status = self._fetch_espn_status_cached(pos.event_id, pos.sport_tag)
        market_type_key = _resolve_market_type_key(pos)
        return fc_check(
            pos=pos,
            espn_status=espn_status,
            now=datetime.now(timezone.utc),
            timeouts=timeouts,
            market_type=market_type_key,
        )

    def fill_via_book(self, pos: Position) -> tuple[float, float, bool]:
        """Bid book walk full bypass — (avg_price, filled_shares, no_bids).

        no_bids=True ise caller realize@0 ile FORCE_CLOSE_NO_BIDS yazmalı.
        """
        try:
            book = self._executor._fetch_book(pos.token_id)
        except Exception as e:
            logger.warning(
                "force_close: orderbook fetch failed for %s: %s",
                (pos.slug or pos.token_id)[:40], e,
            )
            book = {"asks": [], "bids": []}

        bids = (book or {}).get("bids", []) or []
        target = pos.current_price if pos.current_price > 0 else _TARGET_PRICE_FLOOR
        fill = walk_book_sell(
            bids=bids,
            target_price=target,
            shares=pos.shares,
            max_slippage_pct=_FULL_BYPASS_SLIPPAGE,
        )
        if fill.status == "REJECTED" or fill.filled_shares <= 0:
            return (0.0, 0.0, True)
        # PARTIAL_FILL'i de "tam realize" sayıyoruz — force-close "ne kadar
        # satılabilirse o" semantik; kalan share için bid yoksa realize@0
        # değil, sadece o kadarını al + audit'e yaz. ExitProcessor karar verir.
        return (fill.avg_price, fill.filled_shares, False)

    def _fetch_espn_status_cached(self, event_id: str, sport: str) -> Any | None:
        """ESPN status — 60sn TTL cache. event_id boşsa None."""
        if not event_id or self._espn is None:
            return None
        now_ts = datetime.now(timezone.utc).timestamp()
        cached = self._espn_cache.get(event_id)
        if cached is not None and (now_ts - cached[0]) < _ESPN_CACHE_TTL_SECONDS:
            return cached[1]
        try:
            status = self._espn.get_match_status(event_id, sport)
        except Exception as e:
            logger.warning(
                "force_close: ESPN fetch failed for event=%s: %s", event_id, e,
            )
            status = None
        self._espn_cache[event_id] = (now_ts, status)
        return status


def _resolve_market_type_key(pos: Position) -> str:
    """time_force_close.check() için market_type lookup key.

    Öncelik: SportsMarketType enum value (e.g. "tennis_first_set_winner") →
    sport_tag fallback (e.g. "tennis"). Her ikisi boşsa "" (timeouts dict
    "default" key'ine düşer).
    """
    smt = getattr(pos, "sports_market_type", None)
    mt_value = getattr(smt, "value", None) if smt is not None else None
    if mt_value:
        return mt_value
    return pos.sport_tag or ""


def reason_to_exit_reason(reason: str) -> ExitReason:
    """ForceCloseSignal.reason → ExitReason enum mapping."""
    if reason == "espn_event_ended":
        return ExitReason.FORCE_CLOSE_ESPN
    if reason == "time_expired":
        return ExitReason.FORCE_CLOSE_TIME
    # Defensive: yeni reason eklenirse silent yutma değil time-expired'a düş +
    # log et — observable.
    logger.warning("force_close: unknown reason=%r → mapping to FORCE_CLOSE_TIME", reason)
    return ExitReason.FORCE_CLOSE_TIME
