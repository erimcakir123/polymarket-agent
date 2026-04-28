"""NHL empirical puck line cover probability table loader.

Build the table first: python scripts/build_nhl_puck_line_table.py
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

TABLE_PATH: Path = Path("data/nhl_empirical_puck_line_table.json")


@lru_cache(maxsize=1)
def load_table() -> dict:
    """Load + cache NHL puck line cover lookup table from disk."""
    if not TABLE_PATH.exists():
        raise FileNotFoundError(
            f"Empirical puck line table not found at {TABLE_PATH}. "
            "Run scripts/build_nhl_puck_line_table.py first."
        )
    with open(TABLE_PATH, encoding="utf-8") as f:
        return json.load(f)
