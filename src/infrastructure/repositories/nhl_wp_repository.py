"""
NHL empirical win probability table loader (infrastructure layer).

Owns the file I/O for the MoneyPuck precomputed table.
Domain functions in nhl_empirical_wp.py accept the loaded dict as a
parameter — this module is the only place that touches the filesystem.

Build the table first: python scripts/build_nhl_empirical_table.py
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

TABLE_PATH: Path = Path("data/nhl_empirical_win_table.json")


@lru_cache(maxsize=1)
def load_table() -> dict:
    """Load and cache the NHL empirical win probability table from disk."""
    if not TABLE_PATH.exists():
        raise FileNotFoundError(
            f"Empirical WP table not found at {TABLE_PATH}. "
            "Run scripts/build_nhl_empirical_table.py first."
        )
    with open(TABLE_PATH, encoding="utf-8") as f:
        return json.load(f)
