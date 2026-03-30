"""Tests for chronological scout-driven selection in EntryGate."""
from unittest.mock import MagicMock
import pytest

from src.entry_gate import EntryGate, _THIN_DATA_THRESHOLDS


def _make_market(cid, hours=3.0, sport_tag=""):
    m = MagicMock()
    m.condition_id = cid
    m.slug = f"slug-{cid}"
    m.question = f"Will {cid} win?"
    m.yes_price = 0.60
    m.sport_tag = sport_tag
    m.tags = []
    m.match_start_iso = ""
    m.end_date_iso = ""
    return m


class TestVolumeSortedSelectionExists:
    """Verify the static method exists and is callable."""

    def test_volume_sorted_selection_exists(self):
        assert hasattr(EntryGate, "_volume_sorted_selection")
        assert callable(EntryGate._volume_sorted_selection)

    def test_volume_sorted_selection_is_static(self):
        # Should be callable without an instance
        result = EntryGate._volume_sorted_selection([], 10)
        assert result == []

    def test_volume_sorted_returns_up_to_scan_size(self):
        markets = [_make_market(f"m{i}") for i in range(20)]
        result = EntryGate._volume_sorted_selection(markets, 5)
        assert len(result) <= 5


class TestSeenMarketIdsThresholdUsesSportAware:
    """Verify _THIN_DATA_THRESHOLDS values match expected sport-aware thresholds."""

    def test_tennis_threshold(self):
        assert _THIN_DATA_THRESHOLDS["tennis"] == 2

    def test_mma_threshold(self):
        assert _THIN_DATA_THRESHOLDS["mma"] == 2

    def test_golf_threshold(self):
        assert _THIN_DATA_THRESHOLDS["golf"] == 1

    def test_racing_threshold(self):
        assert _THIN_DATA_THRESHOLDS["racing"] == 1

    def test_cricket_threshold(self):
        assert _THIN_DATA_THRESHOLDS["cricket"] == 3

    def test_default_threshold(self):
        assert _THIN_DATA_THRESHOLDS["default"] == 3

    def test_all_thresholds_are_positive_ints(self):
        for sport, threshold in _THIN_DATA_THRESHOLDS.items():
            assert isinstance(threshold, int), f"{sport} threshold is not int"
            assert threshold > 0, f"{sport} threshold must be positive"
