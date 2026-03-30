"""Tests for chronological scout-driven selection in EntryGate."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest

from src.entry_gate import EntryGate, _THIN_DATA_THRESHOLDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_market(cid: str, hours_from_now: float = 3.0, sport_tag: str = "") -> MagicMock:
    """Create a mock MarketData with a realistic match_start_iso."""
    m = MagicMock()
    m.condition_id = cid
    m.slug = f"slug-{cid}"
    m.question = f"Will {cid} win?"
    m.yes_price = 0.60
    m.sport_tag = sport_tag
    m.tags = []
    start = datetime.now(timezone.utc) + timedelta(hours=hours_from_now)
    m.match_start_iso = start.isoformat()
    m.end_date_iso = ""
    return m


def _build_gate(scout=None) -> EntryGate:
    """Create an EntryGate with all dependencies mocked out."""
    cfg = MagicMock()
    cfg.risk.max_positions = 10
    cfg.ai.batch_size = 10
    cfg.early.min_hours_to_start = 6

    portfolio = MagicMock()
    portfolio.active_position_count = 0
    portfolio.positions = {}

    gate = EntryGate(
        config=cfg,
        portfolio=portfolio,
        executor=MagicMock(),
        ai=MagicMock(),
        scanner=MagicMock(),
        risk=MagicMock(),
        odds_api=MagicMock(),
        esports=MagicMock(),
        news_scanner=MagicMock(),
        manip_guard=MagicMock(),
        trade_log=MagicMock(),
        notifier=MagicMock(),
        discovery=None,
        scout=scout,
    )
    # Esports context returns empty so no market passes data filter -> fast return
    gate.esports.get_match_context.return_value = None
    return gate


def _run_selection(gate: EntryGate, markets: list) -> list:
    """Call _analyze_batch and return the market list it produces.

    Since no market will have sports data (esports mock returns None,
    discovery is None), _analyze_batch returns ([], {}).  To capture the
    *prioritized* list before the data filter, we intercept the point where
    it's built by patching the news_scanner to record it.
    """
    # We need to capture `prioritized` after selection but before it's filtered.
    # Patch news_scanner.search_for_markets to capture the prioritized list via
    # the market_keywords dict keys (which == condition_ids of prioritized).
    captured_cids: list[str] = []

    original_search = gate.news_scanner.search_for_markets

    def capture_search(market_keywords: dict) -> dict:
        captured_cids.extend(market_keywords.keys())
        return {}

    gate.news_scanner.search_for_markets = capture_search

    gate._analyze_batch(markets, cycle_count=0)
    return captured_cids


# ---------------------------------------------------------------------------
# Behavioral tests: Chronological selection
# ---------------------------------------------------------------------------

class TestChronologicalSelection:
    """When scout has matched markets, they are selected soonest-first."""

    def test_markets_ordered_by_match_time(self):
        """Scout-matched markets should appear ordered by match_time (soonest first)."""
        scout = MagicMock()

        # 3 markets at 1h, 4h, 2h from now
        m1 = _make_market("early", hours_from_now=1.0)
        m2 = _make_market("late", hours_from_now=4.0)
        m3 = _make_market("mid", hours_from_now=2.0)
        all_markets = [m1, m2, m3]

        t_early = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        t_mid = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        t_late = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()

        # Scout returns all 3 as matched, with match_time set
        scout.match_markets_batch.return_value = [
            {"market": m1, "scout_entry": {"match_time": t_early}, "scout_key": "k_early"},
            {"market": m2, "scout_entry": {"match_time": t_late}, "scout_key": "k_late"},
            {"market": m3, "scout_entry": {"match_time": t_mid}, "scout_key": "k_mid"},
        ]

        # All keys in 2h window (only early and mid qualify), then expand
        # At 2h window: only k_early fits. At 3h: k_early, k_mid. At 5h: all 3.
        # But we need >=5 to stop early — with only 3 markets it will exhaust all windows.
        def get_window(hours):
            cutoff = datetime.now(timezone.utc) + timedelta(hours=hours)
            entries = []
            for key, t in [("k_early", t_early), ("k_mid", t_mid), ("k_late", t_late)]:
                if datetime.fromisoformat(t) <= cutoff:
                    entries.append({"scout_key": key})
            return entries

        scout.get_window.side_effect = get_window

        gate = _build_gate(scout=scout)
        cids = _run_selection(gate, all_markets)

        # All 3 should be present (scout found 3 < 5, so fallback adds volume-sorted too)
        # But scout-matched ones should come first, ordered by match_time
        assert "early" in cids
        assert "mid" in cids
        assert "late" in cids
        # Check ordering: early before mid before late among the first 3
        idx_early = cids.index("early")
        idx_mid = cids.index("mid")
        idx_late = cids.index("late")
        assert idx_early < idx_mid < idx_late


class TestExpandingWindow:
    """Window starts at 2h and expands to 3h, 4h, 5h until >=5 markets found."""

    def test_stops_expanding_when_five_reached(self):
        """If 2h window has >=5 markets, don't expand further."""
        scout = MagicMock()

        markets = [_make_market(f"m{i}", hours_from_now=1.0 + i * 0.1) for i in range(7)]
        t_base = datetime.now(timezone.utc)

        matched = []
        for i, m in enumerate(markets):
            t = (t_base + timedelta(hours=1.0 + i * 0.1)).isoformat()
            matched.append({
                "market": m,
                "scout_entry": {"match_time": t},
                "scout_key": f"k{i}",
            })
        scout.match_markets_batch.return_value = matched

        # 2h window returns all 7 keys
        scout.get_window.return_value = [{"scout_key": f"k{i}"} for i in range(7)]

        gate = _build_gate(scout=scout)
        _run_selection(gate, markets)

        # get_window should be called only once (2h) since it returned >= 5
        scout.get_window.assert_called_once_with(2)

    def test_expands_until_enough_markets(self):
        """If 2h has <5, 3h has <5, 4h has >=5, stop at 4h."""
        scout = MagicMock()

        # 8 markets spaced 0.5h apart starting at 1h: 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5
        markets = [_make_market(f"m{i}", hours_from_now=1.0 + i * 0.5) for i in range(8)]
        t_base = datetime.now(timezone.utc)

        matched = []
        for i, m in enumerate(markets):
            t = (t_base + timedelta(hours=1.0 + i * 0.5)).isoformat()
            matched.append({
                "market": m,
                "scout_entry": {"match_time": t},
                "scout_key": f"k{i}",
            })
        scout.match_markets_batch.return_value = matched

        # get_window returns keys where hour offset < cutoff (strict less-than)
        # 2h -> k0(1h), k1(1.5h) = 2 keys (<5)
        # 3h -> k0, k1, k2(2h), k3(2.5h) = 4 keys (<5)
        # 4h -> k0, k1, k2, k3, k4(3h), k5(3.5h) = 6 keys (>=5, stop)
        def get_window(hours):
            entries = []
            for i in range(8):
                if (1.0 + i * 0.5) < hours:
                    entries.append({"scout_key": f"k{i}"})
            return entries

        scout.get_window.side_effect = get_window

        gate = _build_gate(scout=scout)
        _run_selection(gate, markets)

        # Should have called get_window(2), get_window(3), get_window(4) — stopped at 4
        calls = [c.args[0] for c in scout.get_window.call_args_list]
        assert calls == [2, 3, 4]


class TestVolumeSortedFallback:
    """When scout yields <5 markets, fall back to volume-sorted and deduplicate."""

    def test_fallback_adds_non_scout_markets(self):
        """Scout yields 2 markets; fallback fills from volume-sorted, excluding scout CIDs."""
        scout = MagicMock()

        scout_m1 = _make_market("scout1", hours_from_now=1.0)
        scout_m2 = _make_market("scout2", hours_from_now=1.5)
        vol_m1 = _make_market("vol1", hours_from_now=2.0)
        vol_m2 = _make_market("vol2", hours_from_now=3.0)
        vol_m3 = _make_market("vol3", hours_from_now=4.0)
        all_markets = [scout_m1, scout_m2, vol_m1, vol_m2, vol_m3]

        t_base = datetime.now(timezone.utc)
        scout.match_markets_batch.return_value = [
            {"market": scout_m1, "scout_entry": {"match_time": (t_base + timedelta(hours=1)).isoformat()}, "scout_key": "ks1"},
            {"market": scout_m2, "scout_entry": {"match_time": (t_base + timedelta(hours=1.5)).isoformat()}, "scout_key": "ks2"},
        ]

        # All windows return both keys (still < 5)
        scout.get_window.return_value = [{"scout_key": "ks1"}, {"scout_key": "ks2"}]

        gate = _build_gate(scout=scout)
        cids = _run_selection(gate, all_markets)

        # Scout markets should be first
        assert cids[0] == "scout1"
        assert cids[1] == "scout2"
        # Volume-sorted fallback should add the others
        assert "vol1" in cids
        assert "vol2" in cids
        assert "vol3" in cids

    def test_fallback_deduplicates_scout_cids(self):
        """Volume-sorted fallback must not re-add markets already selected by scout."""
        scout = MagicMock()

        m1 = _make_market("shared", hours_from_now=1.0)
        m2 = _make_market("only_vol", hours_from_now=2.0)
        all_markets = [m1, m2]

        t = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        scout.match_markets_batch.return_value = [
            {"market": m1, "scout_entry": {"match_time": t}, "scout_key": "ks1"},
        ]
        scout.get_window.return_value = [{"scout_key": "ks1"}]

        gate = _build_gate(scout=scout)
        cids = _run_selection(gate, all_markets)

        # "shared" should appear exactly once
        assert cids.count("shared") == 1
        assert "only_vol" in cids


class TestNoScoutFallback:
    """When self.scout is None, fall back entirely to volume-sorted."""

    def test_no_scout_uses_volume_sorted(self):
        """With scout=None, all markets go through volume-sorted selection."""
        markets = [_make_market(f"m{i}", hours_from_now=1.0 + i) for i in range(6)]

        gate = _build_gate(scout=None)
        cids = _run_selection(gate, markets)

        # All markets should be present (volume-sorted picks them all since scan_size is large)
        for i in range(6):
            assert f"m{i}" in cids

    def test_no_scout_no_crash(self):
        """Calling _analyze_batch with scout=None and empty markets should not crash."""
        gate = _build_gate(scout=None)
        result = gate._analyze_batch([], cycle_count=0)
        assert result == ([], {})


# ---------------------------------------------------------------------------
# Threshold value tests (kept from original)
# ---------------------------------------------------------------------------

class TestThinDataThresholds:
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


class TestVolumeSortedSelection:
    """Verify _volume_sorted_selection static method works correctly."""

    def test_returns_empty_for_empty_input(self):
        result = EntryGate._volume_sorted_selection([], 10)
        assert result == []

    def test_returns_up_to_scan_size(self):
        markets = [_make_market(f"m{i}") for i in range(20)]
        result = EntryGate._volume_sorted_selection(markets, 5)
        assert len(result) <= 5
