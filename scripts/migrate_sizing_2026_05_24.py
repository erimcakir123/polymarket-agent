"""Retroactive bimodal cap resize — 2026-05-24.

Tennis lab state'ini bimodal cap $15 -> $20'ye gore yeniden olcekler.
Sadece bimodal trade'leri (set-handicap + set-totals slug pattern) etkiler.

Etkilenen alanlar:
  size_usdc, shares, scale_out_realized_usdc, partial_exits[*].realized_pnl_usdc

Dosyalar:
  data/positions.json
  logs/audit/trade_history.jsonl
  logs/session/trade_history.jsonl
  logs/audit/equity_history.jsonl  (regenerate snapshot)
  logs/session/equity_history.jsonl (regenerate snapshot)

Calistirmadan once tenis bot durdurulmali (state race riski).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

RATIO = 20.0 / 15.0  # bimodal cap 15 -> 20
BAK_SUFFIX = ".bak.2026-05-24-cap20"
INITIAL_BANKROLL = 1000.0


def is_bimodal_slug(slug: str) -> bool:
    s = (slug or "").lower()
    return "set-handicap" in s or "set-total" in s


def scale_partial_exits(pes: list) -> list:
    out = []
    for pe in pes:
        new_pe = dict(pe)
        if "realized_pnl_usdc" in new_pe:
            new_pe["realized_pnl_usdc"] = new_pe["realized_pnl_usdc"] * RATIO
        if "size_sold_usdc" in new_pe:
            new_pe["size_sold_usdc"] = new_pe["size_sold_usdc"] * RATIO
        if "shares_sold" in new_pe:
            new_pe["shares_sold"] = new_pe["shares_sold"] * RATIO
        out.append(new_pe)
    return out


def scale_position(pos: dict) -> dict:
    new = dict(pos)
    new["size_usdc"] = round(pos.get("size_usdc", 0) * RATIO, 4)
    new["shares"] = pos.get("shares", 0) * RATIO
    new["scale_out_realized_usdc"] = pos.get("scale_out_realized_usdc", 0.0) * RATIO
    if pos.get("original_shares") is not None:
        new["original_shares"] = pos["original_shares"] * RATIO
    if pos.get("original_size_usdc") is not None:
        new["original_size_usdc"] = pos["original_size_usdc"] * RATIO
    new["partial_exits"] = scale_partial_exits(pos.get("partial_exits", []) or [])
    return new


def scale_trade(t: dict) -> dict:
    new = dict(t)
    new["size_usdc"] = round(t.get("size_usdc", 0) * RATIO, 4)
    new["shares"] = t.get("shares", 0) * RATIO
    new["exit_pnl_usdc"] = t.get("exit_pnl_usdc", 0.0) * RATIO
    new["partial_exits"] = scale_partial_exits(t.get("partial_exits", []) or [])
    return new


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + BAK_SUFFIX)
    shutil.copy2(path, bak)
    return bak


def atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def atomic_write_jsonl(path: Path, records: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    tmp.replace(path)


def rebuild_equity_snapshot(positions: dict, trades: list[dict]) -> dict:
    realized = sum(t.get("exit_pnl_usdc", 0.0) for t in trades)
    realized += sum(
        sum(pe.get("realized_pnl_usdc", 0.0) for pe in p.get("partial_exits", []) or [])
        for p in positions.values()
    )
    realized += sum(p.get("scale_out_realized_usdc", 0.0) for p in positions.values())
    invested = sum(p.get("size_usdc", 0.0) for p in positions.values())
    bankroll = INITIAL_BANKROLL - invested + realized
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bankroll": round(bankroll, 2),
        "realized_pnl": round(realized, 2),
        "unrealized_pnl": 0.0,
        "invested": round(invested, 2),
        "open_positions": len(positions),
    }


def run(repo_root: Path, apply: bool) -> dict:
    positions_path = repo_root / "data" / "positions.json"
    audit_dir = repo_root / "logs" / "audit"
    session_dir = repo_root / "logs" / "session"

    report = {"mode": "apply" if apply else "dry-run", "files": [], "positions_resized": 0, "trades_resized": 0}

    # 1. positions.json
    data = json.loads(positions_path.read_text(encoding="utf-8"))
    positions = data.get("positions", {})
    new_positions = {}
    for cid, pos in positions.items():
        if is_bimodal_slug(pos.get("slug", "")):
            new_positions[cid] = scale_position(pos)
            report["positions_resized"] += 1
        else:
            new_positions[cid] = pos
    data["positions"] = new_positions
    if apply:
        backup(positions_path)
        atomic_write_json(positions_path, data)
        report["files"].append(str(positions_path))

    # 2. trade_history.jsonl (audit + session)
    all_trades = []
    for src_dir in (audit_dir, session_dir):
        th = src_dir / "trade_history.jsonl"
        if not th.exists():
            continue
        raw = th.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        trades = [json.loads(line) for line in raw.split("\n") if line.strip()]
        new_trades = []
        for t in trades:
            if is_bimodal_slug(t.get("slug", "")):
                new_trades.append(scale_trade(t))
                report["trades_resized"] += 1
            else:
                new_trades.append(t)
        if apply:
            backup(th)
            atomic_write_jsonl(th, new_trades)
            report["files"].append(str(th))
        all_trades.extend(new_trades)

    # 3. equity_history.jsonl — append new snapshot
    snap = rebuild_equity_snapshot(new_positions, all_trades)
    if apply:
        for eq_dir in (audit_dir, session_dir):
            eq = eq_dir / "equity_history.jsonl"
            if eq.exists():
                backup(eq)
                # append snapshot to existing history
                existing = [json.loads(l) for l in eq.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
                existing.append(snap)
                atomic_write_jsonl(eq, existing)
                report["files"].append(str(eq))
    report["snapshot"] = snap
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Dosyalari guncelle (default dry-run)")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    report = run(repo_root, apply=args.apply)
    print(f"Mode: {report['mode']}")
    print(f"Positions resized: {report['positions_resized']}")
    print(f"Trades resized: {report['trades_resized']}")
    print(f"Snapshot: bankroll=${report['snapshot']['bankroll']} invested=${report['snapshot']['invested']} realized=${report['snapshot']['realized_pnl']}")
    if report["files"]:
        print(f"Files written ({len(report['files'])}):")
        for f in report["files"]:
            print(f"  - {f}")
    else:
        print("[DRY-RUN] no files written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
