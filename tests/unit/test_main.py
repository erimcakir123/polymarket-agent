"""src/main.py için sanity testler."""
from __future__ import annotations

import pathlib


def test_main_max_50_lines() -> None:
    lines = pathlib.Path("src/main.py").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 50, f"main.py is {len(lines)} lines — max 50 (ARCH Kural 5)"
