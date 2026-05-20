"""Dashboard widget audit — Stage 9 user-facing doğrulama.

Tennis Flask app'i test client modunda kaldırır (gerçek server başlatmaz),
her route'a istek atar, response JSON'unun beklenen anahtarları içerdiğini
+ örnek verinin makul olduğunu doğrular. Pass/fail tablosu basar.

Exit code 0 = tüm pass, 1 = en az bir fail.

Kullanım:
    python scripts/dashboard_audit.py

Tennis sandbox CWD'ye bağımsız: paths _ROOT'a anchor edilir.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.config.settings import load_config
from src.presentation.dashboard.app import create_app

CONFIG_PATH = _ROOT / "config_tennis.yaml"
LOGS_DIR = _ROOT / "logs"

# Sözleşme: her endpoint için (path, beklenen sanity check fn).
# Sanity fn raw response data alır, (ok: bool, mesaj: str) döner.


def _has_keys(data: dict, keys: set[str]) -> tuple[bool, str]:
    missing = keys - set(data.keys())
    if missing:
        return False, f"missing keys: {sorted(missing)}"
    return True, f"keys: {sorted(keys)}"


def _check_status(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, f"not a dict: {type(data).__name__}"
    return _has_keys(data, {"mode", "bot_alive", "cycle", "stage", "stage_at", "next_heavy_at", "light_alive"})


def _check_summary(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "not a dict"
    ok, msg = _has_keys(data, {"equity", "slots", "loss_protection"})
    if not ok:
        return ok, msg
    eq = data["equity"]
    if not isinstance(eq, dict) or "bankroll" not in eq:
        return False, "equity.bankroll missing"
    sl = data["slots"]
    if not isinstance(sl, dict) or "current" not in sl or "max" not in sl:
        return False, "slots.current/max missing"
    lp = data["loss_protection"]
    if not isinstance(lp, dict) or "status" not in lp:
        return False, "loss_protection.status missing"
    return True, f"bankroll={eq['bankroll']} slots={sl['current']}/{sl['max']} risk={lp['status']}"


def _check_equity_history(data: Any) -> tuple[bool, str]:
    if not isinstance(data, list):
        return False, "not a list"
    if not data:
        return True, "empty (acceptable: no snapshots yet)"
    first = data[0]
    if "bankroll" not in first or "timestamp" not in first:
        return False, "snapshot missing bankroll/timestamp"
    return True, f"{len(data)} snapshots, last bankroll={data[-1].get('bankroll')}"


def _check_positions(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "not a dict"
    if not data:
        return True, "0 positions (acceptable)"
    first = next(iter(data.values()))
    required = {"slug", "direction", "entry_price", "current_price", "size_usdc"}
    missing = required - set(first.keys())
    if missing:
        return False, f"position missing fields: {sorted(missing)}"
    return True, f"{len(data)} positions"


def _check_trades(data: Any) -> tuple[bool, str]:
    if not isinstance(data, list):
        return False, "not a list"
    if not data:
        return True, "0 exited trades (acceptable)"
    first = data[0]
    if "slug" not in first or "exit_timestamp" not in first:
        return False, "trade missing slug/exit_timestamp"
    return True, f"{len(data)} exit events, top slug={first.get('slug')}"


def _check_skipped(data: Any) -> tuple[bool, str]:
    if not isinstance(data, list):
        return False, "not a list"
    return True, f"{len(data)} skipped entries"


def _check_stock(data: Any) -> tuple[bool, str]:
    if not isinstance(data, list):
        return False, "not a list"
    return True, f"{len(data)} stock queue entries"


def _check_stats(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "not a dict"
    return _has_keys(data, {"wins", "losses"})


def _check_sport_roi(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "not a dict"
    ok, msg = _has_keys(data, {"summary", "leagues"})
    if not ok:
        return ok, msg
    leagues = data["leagues"]
    if not isinstance(leagues, list):
        return False, "leagues not a list"
    return True, f"{len(leagues)} sports, total_trades={data['summary'].get('total_trades')}"


def _check_trades_history(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "not a dict"
    return _has_keys(data, {"trades", "week_label", "week_offset", "has_older", "total_in_week"})


@dataclass
class Endpoint:
    path: str
    name: str
    check: Callable[[Any], tuple[bool, str]]


ENDPOINTS: list[Endpoint] = [
    Endpoint("/api/status", "Status (cycle/stage/bot_alive)", _check_status),
    Endpoint("/api/summary", "Summary (equity+slots+risk)", _check_summary),
    Endpoint("/api/equity_history", "Equity History (chart)", _check_equity_history),
    Endpoint("/api/positions", "Positions (open)", _check_positions),
    Endpoint("/api/trades", "Trades (Exited tab)", _check_trades),
    Endpoint("/api/skipped", "Skipped trades", _check_skipped),
    Endpoint("/api/stock", "Stock queue", _check_stock),
    Endpoint("/api/stats", "Win/Loss stats", _check_stats),
    Endpoint("/api/sport_roi", "Sport ROI treemap", _check_sport_roi),
    Endpoint("/api/trades/history", "Trade history (weekly)", _check_trades_history),
]

INDEX_PATH = "/"


def main() -> int:
    if not CONFIG_PATH.exists():
        print(f"ERROR: {CONFIG_PATH} not found", file=sys.stderr)
        return 1
    cfg = load_config(CONFIG_PATH)
    app = create_app(config=cfg, logs_dir=LOGS_DIR)
    app.config["TESTING"] = True
    client = app.test_client()

    results: list[tuple[str, str, bool, str]] = []

    # Index sanity (HTML 200)
    r = client.get(INDEX_PATH)
    ok = r.status_code == 200 and (b"PolyAgent" in r.data or b"Polymarket" in r.data)
    results.append((INDEX_PATH, "Index HTML render", ok, f"status={r.status_code} html_len={len(r.data)}"))

    for ep in ENDPOINTS:
        r = client.get(ep.path)
        if r.status_code != 200:
            results.append((ep.path, ep.name, False, f"HTTP {r.status_code}"))
            continue
        try:
            data = r.get_json()
        except (ValueError, json.JSONDecodeError) as exc:
            results.append((ep.path, ep.name, False, f"json parse error: {exc}"))
            continue
        ok, msg = ep.check(data)
        results.append((ep.path, ep.name, ok, msg))

    # Print table
    print("\n" + "=" * 90)
    print(f"{'STATUS':6}  {'ROUTE':28}  {'WIDGET':28}  DETAIL")
    print("-" * 90)
    failed = 0
    for path, name, ok, detail in results:
        flag = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"{flag:6}  {path:28}  {name:28}  {detail}")
    print("=" * 90)
    print(f"Total: {len(results)}, Pass: {len(results) - failed}, Fail: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
