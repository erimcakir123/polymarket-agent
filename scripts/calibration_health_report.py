"""Per-sport model isabet + Brier raporu — dashboard veri kaynağı.

Plan 1.D Task 4. CLI entry point — domain mantığı için:
  src.domain.calibration.health_report.compute_health()

JSON output: data/model_health.json (dashboard cycle başına okur).
Bozulma alarmı: accuracy < eşik → Telegram (24h per-sport rate limit).
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config.settings import load_config
from src.domain.calibration.health_report import compute_health
from src.presentation.notifier import TelegramNotifier


logger = logging.getLogger(__name__)

_OUTPUT_PATH = Path("data/model_health.json")
_ALARM_STATE_PATH = Path("data/model_health_alarms.json")
_ACCURACY_ALARM_THRESHOLD = 0.55
_ALARM_COOLDOWN_HOURS = 24


def _read_trades(path: Path) -> list[dict]:
    trades: list[dict] = []
    if not path.exists():
        return trades
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                trades.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return trades


def _read_alarm_state(path: Path) -> dict[str, str]:
    """{sport: last_fired_iso}. Bozuk/yoksa {}."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Alarm state read failed: %s", e)
        return {}


def _write_alarm_state(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def _should_fire_alarm(last_fired_iso: str, now: datetime) -> bool:
    """24h per-sport cooldown — ardışık alarm spamı engelle."""
    if not last_fired_iso:
        return True
    try:
        last = datetime.fromisoformat(last_fired_iso)
    except ValueError:
        return True
    return (now - last) >= timedelta(hours=_ALARM_COOLDOWN_HOURS)


def _dispatch_alarms(health: dict[str, dict], now: datetime) -> int:
    """Eşik altı her spor için Telegram + rate-limit state güncelle.

    Returns: gönderilen alarm sayısı (test/log için).
    """
    fired = 0
    degraded = {
        sport: stats for sport, stats in health.items()
        if float(stats.get("accuracy", 1.0)) < _ACCURACY_ALARM_THRESHOLD
    }
    if not degraded:
        return 0
    state = _read_alarm_state(_ALARM_STATE_PATH)
    cfg = load_config()
    notifier = TelegramNotifier(
        enabled=cfg.telegram.enabled,
        bot_token=cfg.telegram.bot_token,
        chat_id=cfg.telegram.chat_id,
    )
    for sport, stats in degraded.items():
        if not _should_fire_alarm(state.get(sport, ""), now):
            continue
        ok = notifier.notify_model_degraded(
            sport=sport,
            accuracy=float(stats["accuracy"]),
            n_trades=int(stats.get("n_trades", 0)),
        )
        if ok:
            state[sport] = now.isoformat()
            fired += 1
        else:
            logger.warning("Model alarm send failed for %s", sport)
    if fired:
        _write_alarm_state(_ALARM_STATE_PATH, state)
    return fired


def main() -> int:
    trades_path = Path("logs/audit/trade_history.jsonl")
    trades = _read_trades(trades_path)
    health = compute_health(trades) if trades else {}
    now = datetime.now(timezone.utc)
    payload = {
        "computed_at_utc": now.isoformat(),
        "sports": health,
    }
    print(f"[HEALTH] computed for {len(health)} sports")
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _OUTPUT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(_OUTPUT_PATH)
    fired = _dispatch_alarms(health, now) if health else 0
    if fired:
        print(f"[HEALTH] fired {fired} model-degraded Telegram alarm(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
