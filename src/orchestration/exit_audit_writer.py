"""Exit-side alert helpers — ExitProcessor'dan ayrı modül (ARCH_GUARD §3).

  - emit_force_close_alert: force-close eşik geçti, alarm üret (otomatik exit YOK)

SPEC-Z17 (2026-06-04): write_synth_exit_record kaldırıldı — event log append-only
tek truth olduğu için orphan/phantom-yok exit fallback path'i artık gereksiz.
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
