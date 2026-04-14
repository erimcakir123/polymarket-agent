"""src/main.py için sanity testler."""
from __future__ import annotations

import pathlib


def test_main_module_imports_without_side_effects() -> None:
    import src.main
    assert hasattr(src.main, "main")
    assert callable(src.main.main)


def test_main_max_50_lines() -> None:
    lines = pathlib.Path("src/main.py").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 50, f"main.py is {len(lines)} lines — max 50 (ARCH Kural 5)"
