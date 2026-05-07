"""Bot tek giriş noktası (ARCH Kural 5 — max 50 satır, iş mantığı yok)."""
from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

from src.config.settings import Mode, load_config
from src.orchestration.factory import build_agent
from src.orchestration.process_lock import acquire_lock
from src.orchestration.startup import bootstrap


def _setup_logging() -> None:
    Path("logs/runtime").mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    file_h = RotatingFileHandler("logs/runtime/bot.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_h.setFormatter(logging.Formatter(fmt))
    con_h = logging.StreamHandler()
    con_h.setFormatter(logging.Formatter(fmt))
    logging.basicConfig(level=logging.INFO, handlers=[file_h, con_h])


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="polymarket-agent")
    parser.add_argument("--mode", choices=[m.value for m in Mode], default=None)
    args = parser.parse_args()
    _setup_logging()
    cfg = load_config()
    if args.mode:
        cfg = cfg.model_copy(update={"mode": Mode(args.mode)})
    if cfg.mode == Mode.LIVE:
        if input("Type 'CONFIRM LIVE' to proceed: ").strip() != "CONFIRM LIVE":
            print("Aborted.")
            sys.exit(1)
    acquire_lock()
    state = bootstrap(cfg)
    agent = build_agent(state)
    logging.getLogger(__name__).info("Agent starting: mode=%s", cfg.mode.value)
    agent.run()


if __name__ == "__main__":
    main()
