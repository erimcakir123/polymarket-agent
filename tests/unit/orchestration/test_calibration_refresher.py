"""Calibration refresher — haftalık stale check + fit."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from src.orchestration.calibration_refresher import (
    REFRESH_INTERVAL_DAYS,
    is_calibration_stale,
    refresh_calibration_if_stale,
)


def test_missing_file_is_stale(tmp_path: Path):
    assert is_calibration_stale(tmp_path / "missing.json") is True


def test_recent_file_not_stale(tmp_path: Path):
    p = tmp_path / "cal.json"
    p.write_text("{}", encoding="utf-8")
    assert is_calibration_stale(p) is False


def test_old_file_is_stale(tmp_path: Path):
    p = tmp_path / "cal.json"
    p.write_text("{}", encoding="utf-8")
    old_ts = time.time() - (REFRESH_INTERVAL_DAYS + 1) * 86400
    os.utime(p, (old_ts, old_ts))
    assert is_calibration_stale(p) is True


def test_refresh_skips_when_fresh(tmp_path: Path):
    cal = tmp_path / "cal.json"
    cal.write_text("{}", encoding="utf-8")
    trades = tmp_path / "trades.jsonl"
    assert refresh_calibration_if_stale(cal, trades) is False


def test_refresh_empty_trades_returns_false(tmp_path: Path):
    cal = tmp_path / "cal.json"   # missing → stale
    trades = tmp_path / "trades.jsonl"  # missing
    assert refresh_calibration_if_stale(cal, trades) is False


def test_refresh_fits_curves_from_trades(tmp_path: Path):
    cal = tmp_path / "cal.json"
    trades_path = tmp_path / "trades.jsonl"
    # 30+ trade nba:moneyline (min threshold)
    rows = [
        {
            "sport_tag": "nba",
            "market_type": "moneyline",
            "anchor_probability": 0.7,
            "resolved_outcome": 1 if i % 3 != 0 else 0,
        }
        for i in range(40)
    ]
    with trades_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    assert refresh_calibration_if_stale(cal, trades_path) is True
    assert cal.exists()
    payload = json.loads(cal.read_text(encoding="utf-8"))
    assert "nba:moneyline" in payload


def test_refresh_skips_buckets_below_min_threshold(tmp_path: Path):
    cal = tmp_path / "cal.json"
    trades_path = tmp_path / "trades.jsonl"
    rows = [
        {
            "sport_tag": "nba", "market_type": "moneyline",
            "anchor_probability": 0.7, "resolved_outcome": 1,
        }
        for _ in range(10)  # below 30 threshold
    ]
    with trades_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    assert refresh_calibration_if_stale(cal, trades_path) is False
