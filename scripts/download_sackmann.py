"""Download Sackmann ATP CSV files from GitHub.

Weekly cron: pulls latest year + recent years for re-build.

Run:
    python scripts/download_sackmann.py

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §3.1
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import load_config

logger = logging.getLogger(__name__)

SACKMANN_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{year}.csv"
)
SACKMANN_CHALLENGER_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_qual_chall_{year}.csv"
)


def download_year(year: int, target_dir: Path, timeout: int = 30) -> bool:
    """Download single ATP main-draw year CSV. Returns True on success."""
    url = SACKMANN_URL_TEMPLATE.format(year=year)
    target_dir.mkdir(parents=True, exist_ok=True)
    output = target_dir / f"atp_matches_{year}.csv"
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.RequestException as e:
        logger.warning("Download %s failed: %s", url, e)
        return False
    if resp.status_code != 200:
        logger.warning("Download %s returned %d", url, resp.status_code)
        return False
    output.write_text(resp.text, encoding="utf-8")
    size_kb = len(resp.text) // 1024
    logger.info("Downloaded %s (%d KB)", output.name, size_kb)
    return True


def download_challenger_year(year: int, target_dir: Path, timeout: int = 30) -> bool:
    """Download single Challenger+Qualifier year CSV. Returns True on success."""
    url = SACKMANN_CHALLENGER_URL_TEMPLATE.format(year=year)
    target_dir.mkdir(parents=True, exist_ok=True)
    output = target_dir / f"atp_matches_qual_chall_{year}.csv"
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.RequestException as e:
        logger.warning("Download %s failed: %s", url, e)
        return False
    if resp.status_code != 200:
        logger.warning("Download %s returned %d", url, resp.status_code)
        return False
    output.write_text(resp.text, encoding="utf-8")
    size_kb = len(resp.text) // 1024
    logger.info("Downloaded %s (%d KB)", output.name, size_kb)
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    cfg = load_config(Path("config_tennis.yaml"))
    target_dir = Path(cfg.tennis.data_dir)
    for year in cfg.tennis.sackmann_years:
        download_year(year, target_dir)
    for year in cfg.tennis.challenger_years:
        download_challenger_year(year, target_dir)


if __name__ == "__main__":
    main()
