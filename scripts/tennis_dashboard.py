"""Tennis lab sandbox dashboard launcher.

Reuses main bot's Flask app from src/presentation/dashboard/app.py
but reads tennis-specific paths from config_tennis.yaml.

Run:
    python scripts/tennis_dashboard.py

Then: http://127.0.0.1:5051

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §10
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.config.settings import load_config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    cfg = load_config(_ROOT / "config_tennis.yaml")

    from src.presentation.dashboard.app import create_app

    app = create_app(config=cfg, logs_dir=_ROOT / "logs")
    print(f"Tennis dashboard starting on http://{cfg.dashboard.host}:{cfg.dashboard.port}")
    print(f"  Bankroll: ${cfg.initial_bankroll}")
    print(f"  Open in browser: http://localhost:{cfg.dashboard.port}")
    app.run(host=cfg.dashboard.host, port=cfg.dashboard.port, debug=False)


if __name__ == "__main__":
    main()
