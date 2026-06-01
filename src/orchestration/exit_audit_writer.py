"""Exit-side audit + alert helpers — ExitProcessor'dan ayrı modül (ARCH_GUARD §3).

  - emit_force_close_alert: force-close eşik geçti, alarm üret (otomatik exit YOK)
  - write_synth_exit_record: orphan/phantom-yok exit'lerde audit gap kapatıcı
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.models.position import Position

logger = logging.getLogger(__name__)


def emit_force_close_alert(deps, fc_alerts, pos: Position, signal) -> None:
    """Force-close eşik geçti — ALARM ÜRET, otomatik exit YAPMA.

    Kullanıcı kararı (2026-06-01):
      'Belli saati geçince otomatik çık deme. Kırmızı border + bildirim
       gelsin, ben karar veririm. Polymarket bug olsa yanlış exit yapmayalım.'

    Akış:
      1. Alert store'da tek-seferlik kontrol (aynı pozisyon için spam yok)
      2. Telegram bildirimi (notifier opsiyonel, yoksa log only)
      3. Alert store'a kaydet (dashboard kırmızı border için)
      4. Pozisyon AÇIK kalır — manuel review veya Polymarket resolve bekler
    """
    cid = pos.condition_id
    if fc_alerts.is_alerted(cid):
        return
    elapsed_min = 0.0
    try:
        start = datetime.fromisoformat(
            pos.match_start_iso.replace("Z", "+00:00"),
        )
        elapsed_min = (datetime.now(timezone.utc) - start).total_seconds() / 60.0
    except (AttributeError, ValueError):
        pass
    now_iso = datetime.now(timezone.utc).isoformat()
    notifier = getattr(deps, "notifier", None)
    if notifier is not None:
        try:
            notifier.notify_force_close_alert(
                slug=pos.slug or pos.token_id,
                sport=pos.sport_tag or "?",
                pnl_pct=pos.unrealized_pnl_pct,
                elapsed_min=elapsed_min,
            )
        except Exception as exc:  # noqa: BLE001 — infra boundary
            logger.warning("force_close telegram alert failed: %s", exc)
    fc_alerts.mark_alerted(cid, now_iso)
    logger.warning(
        "FORCE_CLOSE_ALERT %s reason=%s pnl=%.2f elapsed=%.0fmin — manuel review",
        (pos.slug or pos.token_id)[:40],
        getattr(signal, "reason", "?"),
        pos.unrealized_pnl_pct,
        elapsed_min,
    )


def write_synth_exit_record(
    deps,
    pos: Position,
    exit_reason_value: str,
    exit_price: float,
    realized: float,
    pnl_pct: float,
    now_iso: str,
) -> None:
    """SPEC-G: orphan/phantom-yok exit'lerde audit gap'i kapatmak icin
    complete synth record yaz. Entry + exit aynı satirda, gercek pos verileriyle.

    2026-05-27: signature signal yerine primitive — force-close path da
    kullanır (signal nesnesi olmayabilir)."""
    from src.infrastructure.persistence.trade_logger import TradeRecord, _split_sport_tag
    category, league = _split_sport_tag(pos.sport_tag or "")
    try:
        record = TradeRecord(
            slug=pos.slug or "",
            condition_id=pos.condition_id,
            event_id=pos.event_id or "",
            token_id=pos.token_id or "",
            question=pos.question or "",
            sport_tag=pos.sport_tag or "",
            sport_category=category,
            league=league,
            direction=pos.direction,
            entry_price=pos.entry_price,
            size_usdc=pos.size_usdc,
            shares=pos.shares,
            confidence=pos.confidence or "",
            bookmaker_prob=pos.bookmaker_prob or 0.0,
            anchor_probability=pos.anchor_probability,
            num_bookmakers=0,
            has_sharp=False,
            entry_reason=f"synth-from-exit:{pos.entry_reason or 'unknown'}",
            entry_timestamp=pos.match_start_iso or now_iso,
            exit_price=exit_price,
            exit_reason=exit_reason_value,
            exit_pnl_usdc=round(realized, 2),
            exit_pnl_pct=round(pnl_pct, 4),
            exit_timestamp=now_iso,
        )
        deps.trade_logger.log(record)
        logger.info(
            "EXIT %s: synth-from-exit kaydi yazildi (orphan recovery, audit gap kapatildi)",
            pos.slug[:35],
        )
    except Exception as e:
        logger.warning(
            "EXIT %s: synth-from-exit yazimi da basarisiz: %s — bakiye in-memory korunur",
            pos.slug[:35], e,
        )
