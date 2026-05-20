"""Tennis agent process/status writer — pid + bot_status.json (Stage 5/6 PLAN-TENNIS-001).

Single responsibility: tennis-lab dashboard heartbeat dosyalarını yazar.
tennis_agent.py'den ayrıldı (ARCH_GUARD Kural 3: max 400 satır).

Not: main bot'taki BotStatusWriter sınıfı CycleManager.next_heavy_at_iso()
üzerinden çalışır — tennis_agent kendi monotonic clock'unu kullanır, bu yüzden
tennis için ayrı yazıcı tutuyoruz (schema aynı, kaynak farklı).
"""
from __future__ import annotations

import atexit
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def write_pid(pid_file: Path) -> None:
    """Tennis agent process PID dosyası — dashboard bot_is_alive kontrolü için."""
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(lambda: pid_file.unlink(missing_ok=True))


def write_status(
    status_file: Path,
    *,
    stage: str,
    next_heavy_at: datetime,
    mode: str,
) -> None:
    """Dashboard cycle göstergesi için bot_status.json snapshot yaz."""
    try:
        status_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": mode,
            "cycle": "heavy" if stage in ("scanning", "idle") else "light",
            "stage": stage,
            "stage_at": datetime.now(timezone.utc).isoformat(),
            "next_heavy_at": next_heavy_at.isoformat(),
            "light_alive": True,
        }
        status_file.write_text(json.dumps(payload), encoding="utf-8")
    except OSError as exc:
        logger.warning("bot_status write failed: %s", exc)
