"""NHL empirical totals over/under probability table loader.

Build: python scripts/build_nhl_totals_table.py
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

TABLE_PATH: Path = Path("data/nhl_empirical_totals_table.json")


@lru_cache(maxsize=1)
def load_table() -> dict:
    if not TABLE_PATH.exists():
        raise FileNotFoundError(
            f"Empirical totals table not found at {TABLE_PATH}. "
            "Run scripts/build_nhl_totals_table.py first."
        )
    with open(TABLE_PATH, encoding="utf-8") as f:
        return json.load(f)
