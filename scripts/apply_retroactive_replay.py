"""Retroactive replay uygula — bot'un WS+REST kesintilerinin yaratığı stale state'i düzelt.

Bu script BOT KAPALIYKEN çalıştırılmalıdır (race condition: positions.json yazımı).

Akış:
  1. data/, logs/audit/, logs/session/ → data/_pre_replay_<ts>/ klasörüne yedek
  2. Tüm açık pozisyonları + bazı eski kapanmış kayıtları replay engine'e besle
     (orchestration: src.orchestration.tennis_replay.apply_pipeline)
  3. Sonuçları audit + session trade_history.jsonl ve positions.json'a yaz
  4. equity_history snapshot append
  5. Özet tablosu print (Original vs Simulated)

Default: dry-run (--apply olmadan yazma yok).

Kullanım:
  python scripts/apply_retroactive_replay.py              # dry-run önizleme
  python scripts/apply_retroactive_replay.py --apply      # gerçek uygula (BOT KAPALI)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.orchestration.tennis_replay.apply_pipeline import (  # noqa: E402
    SummaryRow,
    process_closed_records,
    process_open_positions,
)

_DATA_DIR = ROOT / "data"
_AUDIT_DIR = ROOT / "logs" / "audit"
_SESSION_DIR = ROOT / "logs" / "session"
_POSITIONS_FILE = _DATA_DIR / "positions.json"
_AUDIT_TRADE_HISTORY = _AUDIT_DIR / "trade_history.jsonl"
_SESSION_TRADE_HISTORY = _SESSION_DIR / "trade_history.jsonl"
_AUDIT_EQUITY = _AUDIT_DIR / "equity_history.jsonl"
_SESSION_EQUITY = _SESSION_DIR / "equity_history.jsonl"


def _backup_data(ts: str) -> Path:
    backup_dir = _DATA_DIR / f"_pre_replay_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    if _POSITIONS_FILE.exists():
        shutil.copy2(_POSITIONS_FILE, backup_dir / "positions.json")
    if _AUDIT_TRADE_HISTORY.exists():
        shutil.copy2(_AUDIT_TRADE_HISTORY, backup_dir / "audit_trade_history.jsonl")
    if _SESSION_TRADE_HISTORY.exists():
        shutil.copy2(_SESSION_TRADE_HISTORY, backup_dir / "session_trade_history.jsonl")
    return backup_dir


def _load_positions() -> dict:
    if not _POSITIONS_FILE.exists():
        return {"positions": {}, "realized_pnl": 0.0, "high_water_mark": 0.0}
    with open(_POSITIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _print_summary(rows: list[SummaryRow], total_label: str, total_value: float) -> None:
    print(f"{'Position':<60} | {'Original':>12} | {'Simulated':>14} | {'Diff':>10}")
    print("-" * 105)
    for r in rows:
        print(
            f"{r.slug[:60]:<60} | "
            f"{r.original_label:>12} | "
            f"{r.simulated_label:>14} | "
            f"{r.diff_label:>10}"
        )
    print("-" * 105)
    print(f"{total_label:<60} | {'':>12} | {'':>14} | ${total_value:>+8.2f}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true",
        help="Gerçekten yaz. Varsayılan: dry-run önizleme.",
    )
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d_%H%M%S")
    print(f"[replay] Started at {now.isoformat()} (apply={args.apply})")

    state = _load_positions()
    open_outcome = process_open_positions(state)

    audit_records = _load_jsonl(_AUDIT_TRADE_HISTORY)
    closed_outcome = process_closed_records(audit_records, now)

    total_original = sum(
        float(r.get("exit_pnl_usdc", 0.0)) for r in audit_records
        if r.get("exit_reason")
    )
    total_simulated = (
        total_original + open_outcome.total_simulated_pnl + closed_outcome.total_delta_pnl
    )

    print("\n[replay] OPEN positions:")
    if open_outcome.summary_rows:
        _print_summary(
            open_outcome.summary_rows,
            "TOTAL (simulated new)",
            open_outcome.total_simulated_pnl,
        )
    else:
        print("  (none)")

    print("\n[replay] CLOSED records (retroactive correction):")
    if closed_outcome.summary_rows:
        _print_summary(
            closed_outcome.summary_rows,
            "TOTAL (delta)",
            closed_outcome.total_delta_pnl,
        )
    else:
        print("  (none)")

    print(
        f"\n[replay] Realized P&L: original=${total_original:.2f} "
        f"-> simulated=${total_simulated:.2f} "
        f"(delta=${(total_simulated - total_original):+.2f})"
    )

    if not args.apply:
        print("\n[replay] Dry-run only. Pass --apply to commit changes.")
        return 0

    # ── APPLY MODE ──────────────────────────────────────────────────────────
    backup_dir = _backup_data(ts)
    print(f"\n[replay] Backup -> {backup_dir}")

    # 1. trade_history append (audit + session)
    if open_outcome.new_audit_lines:
        for path in (_AUDIT_TRADE_HISTORY, _SESSION_TRADE_HISTORY):
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                for line in open_outcome.new_audit_lines:
                    f.write(json.dumps(line, ensure_ascii=False) + "\n")
        print(
            f"[replay] Appended {len(open_outcome.new_audit_lines)} "
            "simulated exits to audit+session."
        )

    # 2. Rewrite closed records
    if closed_outcome.rewritten_records:
        keys = {
            (r.get("condition_id", ""), r.get("entry_timestamp", ""))
            for r in closed_outcome.rewritten_records
        }
        merged: list[dict] = []
        for rec in audit_records:
            k = (rec.get("condition_id", ""), rec.get("entry_timestamp", ""))
            if k in keys:
                merged.append(next(
                    r for r in closed_outcome.rewritten_records
                    if (r.get("condition_id", ""), r.get("entry_timestamp", "")) == k
                ))
            else:
                merged.append(rec)
        with open(_AUDIT_TRADE_HISTORY, "w", encoding="utf-8") as f:
            for rec in merged:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(
            f"[replay] Rewrote {len(closed_outcome.rewritten_records)} "
            "closed records with partials."
        )

    # 3. positions.json — kapanan pozisyonları sil + realized_pnl güncelle
    positions = state.get("positions", {}) or {}
    for cid in open_outcome.closed_condition_ids:
        positions.pop(cid, None)
    state["positions"] = positions
    state["realized_pnl"] = total_simulated
    with open(_POSITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)
    print(
        f"[replay] positions.json: {len(open_outcome.closed_condition_ids)} closed, "
        f"realized_pnl={total_simulated:.2f}"
    )

    # 4. equity_history snapshot
    snapshot = {
        "timestamp": now.isoformat(),
        "bankroll": 0.0,
        "realized_pnl": total_simulated,
        "unrealized_pnl": 0.0,
        "invested": 0.0,
        "open_positions": len(positions),
        "simulated_replay": True,
    }
    for path in (_AUDIT_EQUITY, _SESSION_EQUITY):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
    print("[replay] equity_history snapshot appended.")

    print("\n[replay] Done. Bot can be restarted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
