"""Source freshness — cache age check, NO DATA → NO TRADE prensibi."""
from __future__ import annotations

import os
import time
from pathlib import Path

from src.infrastructure.data.source_freshness import (
    MAX_CACHE_AGE_HOURS,
    is_source_fresh,
)


def test_fresh_cache_passes(tmp_path: Path):
    p = tmp_path / "ratings.json"
    p.write_text("{}", encoding="utf-8")
    result = is_source_fresh(p)
    assert result.fresh is True
    assert result.age_hours < 1
    assert result.reason is None


def test_stale_cache_blocks_trade(tmp_path: Path):
    p = tmp_path / "ratings.json"
    p.write_text("{}", encoding="utf-8")
    old = time.time() - (MAX_CACHE_AGE_HOURS + 1) * 3600
    os.utime(p, (old, old))
    result = is_source_fresh(p)
    assert result.fresh is False
    assert result.reason == "cache_too_old"


def test_missing_cache_blocks_trade(tmp_path: Path):
    result = is_source_fresh(tmp_path / "missing.json")
    assert result.fresh is False
    assert result.reason == "cache_missing"


def test_custom_max_age_hours(tmp_path: Path):
    p = tmp_path / "ratings.json"
    p.write_text("{}", encoding="utf-8")
    old = time.time() - 6 * 3600  # 6 saat eski
    os.utime(p, (old, old))
    # 4 saat eşik: stale
    assert is_source_fresh(p, max_age_hours=4.0).fresh is False
    # 8 saat eşik: taze
    assert is_source_fresh(p, max_age_hours=8.0).fresh is True
