"""Tests for sackmann_refresher — cache freshness check + download orchestration.

Pure unit tests with injected http_get (no real network calls).
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.infrastructure.data.sackmann_refresher import (
    is_cache_stale,
    refresh_cache,
    refresh_if_stale,
)


# ── is_cache_stale ───────────────────────────────────────────────────────────


def test_is_cache_stale_when_dir_empty(tmp_path: Path) -> None:
    """Empty cache directory → stale (current-year file missing)."""
    assert is_cache_stale(tmp_path, max_age_days=3) is True


def test_is_cache_stale_when_current_year_file_fresh(tmp_path: Path) -> None:
    """Current-year file mtime within max_age_days → not stale."""
    from datetime import datetime
    current = datetime.utcnow().year
    f = tmp_path / f"atp_matches_{current}.csv"
    f.write_text("header\n", encoding="utf-8")
    # mtime is now → 0 days old → fresh
    assert is_cache_stale(tmp_path, max_age_days=3) is False


def test_is_cache_stale_when_current_year_file_old(tmp_path: Path) -> None:
    """Current-year file older than max_age_days → stale."""
    from datetime import datetime
    current = datetime.utcnow().year
    f = tmp_path / f"atp_matches_{current}.csv"
    f.write_text("header\n", encoding="utf-8")
    # Force mtime to 5 days ago
    old_ts = time.time() - 5 * 86400
    import os
    os.utime(f, (old_ts, old_ts))
    assert is_cache_stale(tmp_path, max_age_days=3) is True


# ── refresh_cache ────────────────────────────────────────────────────────────


def _mock_http(status: int = 200, body: str = "tourney_id,a,b\nx,1,2\n") -> MagicMock:
    """Build a MagicMock that mimics requests.get returning a Response-ish."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = body
    return MagicMock(return_value=resp)


def test_refresh_cache_downloads_all_five_categories(tmp_path: Path) -> None:
    """refresh_cache(years=[2026]) downloads 5 file categories per year."""
    http = _mock_http()
    counts = refresh_cache(tmp_path, years=[2026], http_get=http)
    # 5 categories × 1 year = 5 calls
    assert http.call_count == 5
    assert sum(counts.values()) == 5
    # File names use cache convention (atp_futures, wta_futures — not URL paths)
    assert (tmp_path / "atp_matches_2026.csv").exists()
    assert (tmp_path / "atp_matches_qual_chall_2026.csv").exists()
    assert (tmp_path / "atp_futures_2026.csv").exists()
    assert (tmp_path / "wta_matches_2026.csv").exists()
    assert (tmp_path / "wta_futures_2026.csv").exists()


def test_refresh_cache_atomic_write_skips_partial_on_error(tmp_path: Path) -> None:
    """A non-200 response leaves no partial file (atomic tmp rename)."""
    http = _mock_http(status=404, body="")
    counts = refresh_cache(tmp_path, years=[2026], http_get=http)
    assert sum(counts.values()) == 0
    # No CSV created (all 5 returned 404)
    assert list(tmp_path.glob("*.csv")) == []


def test_refresh_cache_multiple_years(tmp_path: Path) -> None:
    """5 categories × 2 years = 10 calls."""
    http = _mock_http()
    refresh_cache(tmp_path, years=[2025, 2026], http_get=http)
    assert http.call_count == 10


def test_refresh_cache_continues_on_partial_failure(tmp_path: Path) -> None:
    """One category 404, others 200 → other files written, total < max."""
    # Cycle: first call 404, rest 200
    seq = []
    for i in range(5):
        r = MagicMock()
        r.status_code = 404 if i == 0 else 200
        r.text = "header\n"
        seq.append(r)
    http = MagicMock(side_effect=seq)
    counts = refresh_cache(tmp_path, years=[2026], http_get=http)
    assert sum(counts.values()) == 4
    # 4 of 5 files written
    assert len(list(tmp_path.glob("*.csv"))) == 4


# ── refresh_if_stale ─────────────────────────────────────────────────────────


def test_refresh_if_stale_skips_when_fresh(tmp_path: Path) -> None:
    """Fresh cache → no downloads, returns False."""
    from datetime import datetime
    current = datetime.utcnow().year
    (tmp_path / f"atp_matches_{current}.csv").write_text("h\n", encoding="utf-8")
    http = _mock_http()
    refreshed = refresh_if_stale(tmp_path, max_age_days=3, http_get=http)
    assert refreshed is False
    assert http.call_count == 0


def test_refresh_if_stale_downloads_when_stale(tmp_path: Path) -> None:
    """Empty cache → triggers download of recent years (5 categories × 2 = 10)."""
    http = _mock_http()
    refreshed = refresh_if_stale(tmp_path, max_age_days=3, http_get=http)
    assert refreshed is True
    # Default: last 2 years
    assert http.call_count == 10


def test_refresh_if_stale_custom_years(tmp_path: Path) -> None:
    """Override years parameter — refreshes specified years only."""
    http = _mock_http()
    refresh_if_stale(tmp_path, max_age_days=3, years=[2026], http_get=http)
    assert http.call_count == 5  # 1 year × 5 categories
