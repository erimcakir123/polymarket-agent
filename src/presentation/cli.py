"""CLI araçları — komut satırından hızlı durum/pozisyon sorgusu.

Bot çalışırken veya offline'ken state dosyalarını okur. Read-only.

Kullanım:
  python -m src.presentation.cli status
  python -m src.presentation.cli positions
  python -m src.presentation.cli config
  python -m src.presentation.cli trades [--limit 20]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.config.settings import load_config
from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.presentation.dashboard.computed import _position_unrealized

_LOGS = Path("logs")


def cmd_status() -> int:
    """Bot durumu + bankroll + pozisyon sayısı."""
    cfg = load_config()
    ps = JsonStore(_LOGS / "positions.json").load(default={})
    positions = ps.get("positions", {}) or {}
    realized = ps.get("realized_pnl", 0.0)
    invested = sum((p.get("size_usdc", 0.0) or 0.0) for p in positions.values())
    bankroll = cfg.initial_bankroll + realized - invested
    pid_file = _LOGS / "agent.pid"
    pid = pid_file.read_text(encoding="utf-8").strip() if pid_file.exists() else "—"

    print(f"Mode:           {cfg.mode.value}")
    print(f"Bot PID:        {pid}")
    print(f"Initial:        ${cfg.initial_bankroll:,.2f}")
    print(f"Bankroll (cash): ${bankroll:,.2f}")
    print(f"Invested:       ${invested:,.2f}")
    print(f"Realized PnL:   ${realized:+,.2f}")
    print(f"Positions:      {len(positions)} / {cfg.risk.max_positions}")
    return 0


def cmd_positions() -> int:
    """Açık pozisyonların listesi."""
    ps = JsonStore(_LOGS / "positions.json").load(default={})
    positions = ps.get("positions", {}) or {}
    if not positions:
        print("Açık pozisyon yok.")
        return 0
    print(f"{'SLUG':<35} {'DIR':<8} {'CONF':<5} {'ENTRY':>7} {'CURRENT':>8} {'SIZE':>8} {'PNL%':>7}")
    print("-" * 85)
    for pos in positions.values():
        size = pos.get("size_usdc", 0)
        current = pos.get("current_price", 0)
        direction = pos.get("direction", "BUY_YES")
        pnl = _position_unrealized(pos)
        pnl_pct = (pnl / size * 100) if size > 0 else 0
        print(f"{(pos.get('slug','') or '')[:33]:<35} "
              f"{direction:<8} {pos.get('confidence','B'):<5} "
              f"${pos.get('entry_price',0):>6.3f} ${current:>7.3f} "
              f"${size:>7.2f} {pnl_pct:>6.1f}%")
    return 0


def cmd_config() -> int:
    """Mevcut config'i dump et (secrets hariç)."""
    cfg = load_config()
    data = cfg.model_dump(mode="json")
    # Telegram token güvenlik: mask
    if "telegram" in data and data["telegram"].get("bot_token"):
        data["telegram"]["bot_token"] = "***" + data["telegram"]["bot_token"][-4:]
    print(json.dumps(data, indent=2))
    return 0


def cmd_trades(limit: int = 20) -> int:
    """Son N kapanan trade."""
    logger = TradeHistoryLogger(str(_LOGS / "trade_history.jsonl"))
    rows = [r for r in logger.read_recent(limit * 3)
            if r.get("exit_price") is not None][-limit:]
    if not rows:
        print("Kapanan trade yok.")
        return 0
    print(f"{'CLOSED':<17} {'SLUG':<30} {'DIR':<8} {'ENTRY':>7} {'EXIT':>7} {'PNL $':>8} {'REASON':<15}")
    print("-" * 100)
    for r in rows:
        print(f"{(r.get('exit_timestamp','') or '')[:16]:<17} "
              f"{(r.get('slug','') or '')[:28]:<30} "
              f"{r.get('direction','?'):<8} "
              f"${r.get('entry_price',0):>6.3f} "
              f"${r.get('exit_price',0) or 0:>6.3f} "
              f"${r.get('exit_pnl_usdc',0):>+7.2f} "
              f"{r.get('exit_reason',''):<15}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="polymarket-agent-cli")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    subparsers.add_parser("status", help="Bot + bankroll + pozisyon özeti")
    subparsers.add_parser("positions", help="Açık pozisyonları listele")
    subparsers.add_parser("config", help="Config dump (secret'lar maskelenir)")
    tp = subparsers.add_parser("trades", help="Son kapanan trade'ler")
    tp.add_argument("--limit", type=int, default=20)

    args = parser.parse_args(argv)
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "positions":
        return cmd_positions()
    if args.cmd == "config":
        return cmd_config()
    if args.cmd == "trades":
        return cmd_trades(limit=args.limit)
    return 1


if __name__ == "__main__":
    sys.exit(main())
