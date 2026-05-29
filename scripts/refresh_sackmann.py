"""Refresh Sackmann CSV cache + rebuild ratings.

CLI entrypoint that wraps ``sackmann_refresher.refresh_if_stale`` then runs
``build_tennis_ratings.main`` so the bot's tennis_ratings.json reflects the
fresh CSV data.

Usage:
    python scripts/refresh_sackmann.py          # respect 3-day staleness
    python scripts/refresh_sackmann.py --force  # always refresh + rebuild

Designed for cron (weekly) or manual recovery after long downtime.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import load_config
from src.infrastructure.data.sackmann_refresher import (
    is_cache_stale,
    refresh_cache,
    refresh_if_stale,
)

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true",
        help="Refresh + rebuild even if cache is fresh",
    )
    parser.add_argument(
        "--max-age-days", type=int, default=3,
        help="Staleness threshold (default 3)",
    )
    parser.add_argument(
        "--skip-rebuild", action="store_true",
        help="Download CSVs only; do not rebuild ratings.json",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    cfg = load_config(Path("config_tennis.yaml"))
    cache_dir = Path(cfg.tennis.data_dir)

    if args.force:
        from datetime import datetime
        current = datetime.utcnow().year
        years = [current, current - 1]
        logger.info("Force refresh: years=%s", years)
        counts = refresh_cache(cache_dir, years)
        refreshed = sum(counts.values()) > 0
    else:
        if not is_cache_stale(cache_dir, args.max_age_days):
            logger.info("Cache already fresh — nothing to do (use --force to override)")
            return 0
        refreshed = refresh_if_stale(cache_dir, args.max_age_days)

    if not refreshed:
        logger.warning("Refresh attempted but no files downloaded — skipping rebuild")
        return 1

    if args.skip_rebuild:
        logger.info("--skip-rebuild set — leaving ratings.json untouched")
        return 0

    # Rebuild ratings.json from fresh CSVs. Import inline to avoid pulling
    # the heavy Glicko stack when running download-only.
    logger.info("Rebuilding tennis_ratings.json from refreshed CSVs...")
    from scripts.build_tennis_ratings import main as rebuild_main  # noqa: PLC0415
    rebuild_main()
    logger.info("Refresh + rebuild complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
