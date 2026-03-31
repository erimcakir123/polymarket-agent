"""main.py -- Entry point only.

All business logic is in:
  src/agent.py        -- thin Agent loop
  src/entry_gate.py   -- unified entry pipeline
  src/exit_monitor.py -- exit detection
"""
from __future__ import annotations

import glob
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.config import load_config, Mode
from src.process_lock import acquire_lock
from src.agent import Agent


def _reset_simulation() -> None:
    """Wipe all simulation state for a clean $1000 start.

    Deletes positions, trades, portfolio logs, predictions cache,
    blacklist, reentry pool, scout queue, and price history.
    Trade reasoning and AI lessons are preserved for analysis.
    """
    reset_files = [
        "logs/positions.json",
        "logs/portfolio.jsonl",
        "logs/trades.jsonl",
        "logs/performance.jsonl",
        "logs/predictions.jsonl",
        "logs/bot_status.json",
        "logs/candidate_stock.json",
        "logs/portfolio_state.json",
        "logs/realized_pnl.json",
        "logs/blacklist.json",
        "logs/reentry_pool.json",
        "logs/scout_queue.json",
        "logs/exited_markets.json",
        "logs/agent.pid",
    ]
    deleted = 0
    for f in reset_files:
        p = Path(f)
        if p.exists():
            p.unlink()
            deleted += 1
    # Clear price history
    for f in glob.glob("logs/price_history/*.json"):
        Path(f).unlink()
        deleted += 1
    print(f"[RESET] Deleted {deleted} files. Clean $1000 start.")


def main() -> None:
    load_dotenv()
    _log_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    from logging.handlers import RotatingFileHandler
    _file_handler = RotatingFileHandler(
        "logs/bot.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    _file_handler.setFormatter(logging.Formatter(_log_fmt))
    _console_handler = logging.StreamHandler()
    _console_handler.setFormatter(logging.Formatter(_log_fmt))
    logging.basicConfig(
        level=logging.INFO,
        handlers=[_file_handler, _console_handler],
    )

    # Handle --reset flag
    if "--reset" in sys.argv:
        _reset_simulation()
        sys.argv.remove("--reset")

    # Prevent multiple instances from running simultaneously
    acquire_lock()

    config = load_config()

    # Iron Rule 6: User must explicitly confirm before live trading
    if config.mode == Mode.LIVE:
        print("\n*** WARNING: LIVE TRADING MODE ***")
        print("This will execute REAL orders with REAL money on Polymarket.")
        confirm = input("Type 'CONFIRM LIVE' to proceed: ")
        if confirm.strip() != "CONFIRM LIVE":
            print("Aborted. Set mode to 'dry_run' or 'paper' in config.yaml.")
            sys.exit(1)

    agent = Agent(config)
    agent.run()


if __name__ == "__main__":
    main()
