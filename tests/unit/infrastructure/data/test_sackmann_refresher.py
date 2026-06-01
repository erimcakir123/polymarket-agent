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
    """All expected files present + canary mtime within max_age_days → not stale."""
    from datetime import datetime, timezone
    from src.infrastructure.data.sackmann_refresher import _SOURCES
    current = datetime.now(timezone.utc).year
    # Tüm beklenen dosyaları yarat (canary + diğerleri — missing-file fix sonrası gerek).
    for spec in _SOURCES.values():
        f = tmp_path / spec["file"].format(year=current)
        f.write_text("header\n", encoding="utf-8")
    assert is_cache_stale(tmp_path, max_age_days=3) is False


def test_is_cache_stale_when_current_year_file_old(tmp_path: Path) -> None:
    """Current-year file older than max_age_days → stale."""
    from datetime import datetime, timezone
    current = datetime.now(timezone.utc).year
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


def test_refresh_cache_downloads_all_categories(tmp_path: Path) -> None:
    """refresh_cache(years=[2026]) downloads every category in _SOURCES per year."""
    from src.infrastructure.data.sackmann_refresher import _SOURCES
    expected_count = len(_SOURCES)
    http = _mock_http()
    counts = refresh_cache(tmp_path, years=[2026], http_get=http)
    assert http.call_count == expected_count
    assert sum(counts.values()) == expected_count
    # Core categories must be present (atomic write convention).
    assert (tmp_path / "atp_matches_2026.csv").exists()
    assert (tmp_path / "atp_matches_qual_chall_2026.csv").exists()
    assert (tmp_path / "atp_futures_2026.csv").exists()
    assert (tmp_path / "wta_matches_2026.csv").exists()
    assert (tmp_path / "wta_futures_2026.csv").exists()


def test_sackmann_doubles_disabled_2020_suspended():
    """2026-06-01: Sackmann doubles güncellemesi 2020 sonrası DURMUŞ.

    Doubles source _SOURCES'tan kaldırıldı. Doubles pricer + dispatch wiring
    kod olarak korunur (alternatif kaynak bulunduğunda aktive edilir).
    """
    from src.infrastructure.data.sackmann_refresher import _SOURCES
    assert "atp_doubles" not in _SOURCES
    assert "wta_doubles" not in _SOURCES


def test_is_cache_stale_when_expected_file_missing(tmp_path: Path) -> None:
    """Missing-file detection: bir source dosyası yoksa stale dön."""
    from datetime import datetime, timezone
    from src.infrastructure.data.sackmann_refresher import _SOURCES
    current = datetime.now(timezone.utc).year
    # Sadece canary yarat (atp_main), diğerleri YOK → stale
    (tmp_path / f"atp_matches_{current}.csv").write_text("h\n", encoding="utf-8")
    # Diğer source'lar mevcut olmalı (en az 3 var)
    assert len(_SOURCES) >= 3
    from src.infrastructure.data.sackmann_refresher import is_cache_stale
    assert is_cache_stale(tmp_path, max_age_days=3) is True


def test_refresh_cache_atomic_write_skips_partial_on_error(tmp_path: Path) -> None:
    """A non-200 response leaves no partial file (atomic tmp rename)."""
    http = _mock_http(status=404, body="")
    counts = refresh_cache(tmp_path, years=[2026], http_get=http)
    assert sum(counts.values()) == 0
    # No CSV created (all 5 returned 404)
    assert list(tmp_path.glob("*.csv")) == []


def test_refresh_cache_multiple_years(tmp_path: Path) -> None:
    """All categories × 2 years = 2 × len(_SOURCES) calls."""
    from src.infrastructure.data.sackmann_refresher import _SOURCES
    http = _mock_http()
    refresh_cache(tmp_path, years=[2025, 2026], http_get=http)
    assert http.call_count == 2 * len(_SOURCES)


def test_refresh_cache_continues_on_partial_failure(tmp_path: Path) -> None:
    """One category 404, others 200 → other files written, total < max."""
    from src.infrastructure.data.sackmann_refresher import _SOURCES
    n = len(_SOURCES)
    seq = []
    for i in range(n):
        r = MagicMock()
        r.status_code = 404 if i == 0 else 200
        r.text = "header\n"
        seq.append(r)
    http = MagicMock(side_effect=seq)
    counts = refresh_cache(tmp_path, years=[2026], http_get=http)
    assert sum(counts.values()) == n - 1
    assert len(list(tmp_path.glob("*.csv"))) == n - 1


# ── refresh_if_stale ─────────────────────────────────────────────────────────


def test_refresh_if_stale_skips_when_fresh(tmp_path: Path) -> None:
    """All expected files present + fresh canary → no downloads."""
    from datetime import datetime, timezone
    from src.infrastructure.data.sackmann_refresher import _SOURCES
    current = datetime.now(timezone.utc).year
    for spec in _SOURCES.values():
        (tmp_path / spec["file"].format(year=current)).write_text("h\n", encoding="utf-8")
    http = _mock_http()
    refreshed = refresh_if_stale(tmp_path, max_age_days=3, http_get=http)
    assert refreshed is False
    assert http.call_count == 0


def test_refresh_if_stale_downloads_when_stale(tmp_path: Path) -> None:
    """Empty cache → triggers download of recent years (categories × 2 years)."""
    from src.infrastructure.data.sackmann_refresher import _SOURCES
    http = _mock_http()
    refreshed = refresh_if_stale(tmp_path, max_age_days=3, http_get=http)
    assert refreshed is True
    assert http.call_count == 2 * len(_SOURCES)


def test_refresh_if_stale_custom_years(tmp_path: Path) -> None:
    """Override years parameter — refreshes specified years only."""
    from src.infrastructure.data.sackmann_refresher import _SOURCES
    http = _mock_http()
    refresh_if_stale(tmp_path, max_age_days=3, years=[2026], http_get=http)
    assert http.call_count == len(_SOURCES)
