"""Tests for RateCache — JSONL persistence.

SPEC-R Plan 3 T4.
"""
import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.mlb_data.rate_cache import RateCache


def test_put_and_get_roundtrip(tmp_path: Path) -> None:
    cache = RateCache(tmp_path / "cache.jsonl")
    rates = {"K": 0.22, "BB": 0.08}
    cache.put(12345, 2024, "batter", rates)
    assert cache.get(12345, 2024, "batter") == rates


def test_get_missing_returns_none(tmp_path: Path) -> None:
    cache = RateCache(tmp_path / "cache.jsonl")
    assert cache.get(99999, 2024, "batter") is None


def test_role_separation(tmp_path: Path) -> None:
    cache = RateCache(tmp_path / "cache.jsonl")
    batter_rates = {"K": 0.20}
    pitcher_rates = {"K": 0.30}
    cache.put(12345, 2024, "batter", batter_rates)
    cache.put(12345, 2024, "pitcher", pitcher_rates)
    assert cache.get(12345, 2024, "batter") == batter_rates
    assert cache.get(12345, 2024, "pitcher") == pitcher_rates


def test_latest_entry_wins(tmp_path: Path) -> None:
    cache = RateCache(tmp_path / "cache.jsonl")
    cache.put(12345, 2024, "batter", {"K": 0.20})
    cache.put(12345, 2024, "batter", {"K": 0.25})  # newer overwrite
    assert cache.get(12345, 2024, "batter") == {"K": 0.25}


def test_season_separation(tmp_path: Path) -> None:
    cache = RateCache(tmp_path / "cache.jsonl")
    cache.put(12345, 2023, "batter", {"K": 0.20})
    cache.put(12345, 2024, "batter", {"K": 0.25})
    assert cache.get(12345, 2023, "batter") == {"K": 0.20}
    assert cache.get(12345, 2024, "batter") == {"K": 0.25}


def test_clear_expired_removes_old(tmp_path: Path) -> None:
    cache = RateCache(tmp_path / "cache.jsonl")
    # Manually write old entry
    old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    fresh_ts = datetime.now(timezone.utc).isoformat()
    cache_path = tmp_path / "cache.jsonl"
    cache_path.write_text(
        json.dumps({"mlbam_id": 1, "season": 2024, "role": "batter",
                    "rates": {"K": 0.20}, "ts": old_ts}) + "\n" +
        json.dumps({"mlbam_id": 2, "season": 2024, "role": "batter",
                    "rates": {"K": 0.25}, "ts": fresh_ts}) + "\n",
        encoding="utf-8",
    )
    cache.clear_expired(max_age_days=7)
    assert cache.get(1, 2024, "batter") is None  # cleared
    assert cache.get(2, 2024, "batter") == {"K": 0.25}  # kept


def test_clear_expired_empty_cache_no_error(tmp_path: Path) -> None:
    cache = RateCache(tmp_path / "nonexistent.jsonl")
    cache.clear_expired(max_age_days=7)  # no crash


def test_malformed_line_skipped(tmp_path: Path, caplog) -> None:
    cache_path = tmp_path / "cache.jsonl"
    cache_path.write_text(
        "not json\n" +
        json.dumps({"mlbam_id": 1, "season": 2024, "role": "batter",
                    "rates": {"K": 0.20}, "ts": datetime.now(timezone.utc).isoformat()}) + "\n",
        encoding="utf-8",
    )
    cache = RateCache(cache_path)
    assert cache.get(1, 2024, "batter") == {"K": 0.20}


def test_cache_dir_auto_created(tmp_path: Path) -> None:
    cache_path = tmp_path / "deep" / "nested" / "cache.jsonl"
    cache = RateCache(cache_path)
    cache.put(12345, 2024, "batter", {"K": 0.20})
    assert cache_path.exists()


def test_get_returns_dict_copy_not_reference(tmp_path: Path) -> None:
    cache = RateCache(tmp_path / "cache.jsonl")
    rates_in = {"K": 0.20}
    cache.put(12345, 2024, "batter", rates_in)
    rates_out = cache.get(12345, 2024, "batter")
    assert rates_out == {"K": 0.20}
    # Mutate out — should not affect future reads (file-backed)
    rates_out["K"] = 999
    assert cache.get(12345, 2024, "batter") == {"K": 0.20}
