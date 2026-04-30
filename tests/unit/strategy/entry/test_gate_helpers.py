"""Unit tests for extracted gate helpers (_gate_helpers.py)."""
from __future__ import annotations

import pytest
from src.strategy.entry._gate_helpers import (
    _classify_confidence,
    _gap_multiplier,
    _passes_filters,
    _compute_stake,
    _check_event_guard,
)
from src.strategy.entry.gate import GateConfig
from src.models.enums import Direction


def _make_cfg(**overrides) -> GateConfig:
    base = dict(
        min_favorite_probability=0.60,
        max_entry_price=0.80,
        max_positions=20,
        max_exposure_pct=0.50,
        confidence_bet_pct={"A": 0.05, "B": 0.03},
        max_single_bet_usdc=75.0,
        max_bet_pct=0.05,
        probability_weighted=True,
        min_bookmakers=15,
        min_sharps=3,
    )
    base.update(overrides)
    return GateConfig(**base)


# ── _classify_confidence ─────────────────────────────────────────

def test_classify_confidence_a_when_sharp_and_weight_above_threshold():
    """has_sharp=True + bm_weight >= 5.0 → A."""
    assert _classify_confidence(has_sharp=True, bm_weight=5.0) == "A"


def test_classify_confidence_a_high_weight():
    """has_sharp=True + bm_weight well above threshold → A."""
    assert _classify_confidence(has_sharp=True, bm_weight=10.0) == "A"


def test_classify_confidence_b_when_no_sharp_but_weight_sufficient():
    """has_sharp=False + bm_weight >= 5.0 → B."""
    assert _classify_confidence(has_sharp=False, bm_weight=5.0) == "B"


def test_classify_confidence_c_when_weight_below_threshold():
    """bm_weight < 5.0 → C regardless of has_sharp."""
    assert _classify_confidence(has_sharp=True, bm_weight=4.9) == "C"


def test_classify_confidence_c_when_weight_zero():
    """bm_weight=0 → C."""
    assert _classify_confidence(has_sharp=False, bm_weight=0.0) == "C"


# ── _gap_multiplier ──────────────────────────────────────────────

def test_gap_multiplier_normal_zone_returns_one():
    """gap below high zone → 1.0."""
    cfg = _make_cfg()
    assert _gap_multiplier(0.10, cfg) == 1.0


def test_gap_multiplier_high_zone():
    """gap >= gap_high_zone (0.15) but < gap_extreme_zone (0.25) → high_gap_multiplier (1.2)."""
    cfg = _make_cfg()
    assert _gap_multiplier(0.20, cfg) == 1.2


def test_gap_multiplier_extreme_zone():
    """gap >= gap_extreme_zone (0.25) → extreme_gap_multiplier (1.3)."""
    cfg = _make_cfg()
    assert _gap_multiplier(0.30, cfg) == 1.3


def test_gap_multiplier_exact_extreme_boundary():
    """gap == gap_extreme_zone → extreme multiplier (boundary inclusive)."""
    cfg = _make_cfg()
    assert _gap_multiplier(cfg.gap_extreme_zone, cfg) == cfg.extreme_gap_multiplier


# ── _passes_filters ──────────────────────────────────────────────

def test_passes_filters_nominal_pass():
    """All values nominal → None (passes)."""
    cfg = _make_cfg()
    assert _passes_filters(
        gap=0.10, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
    ) is None


def test_passes_filters_gap_too_low_returns_reason():
    """gap < min_gap_threshold → GAP_TOO_LOW."""
    cfg = _make_cfg()
    assert _passes_filters(
        gap=0.03, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
    ) == "GAP_TOO_LOW"


def test_passes_filters_price_out_of_range_too_low():
    """moneyline price below min → PRICE_OUT_OF_RANGE."""
    cfg = _make_cfg()
    assert _passes_filters(
        gap=0.10, polymarket_price=0.10, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
    ) == "PRICE_OUT_OF_RANGE"


def test_passes_filters_bookmaker_prob_too_low():
    """bookmaker_prob < min_favorite_probability → BOOKMAKER_PROB_TOO_LOW."""
    cfg = _make_cfg()
    assert _passes_filters(
        gap=0.10, polymarket_price=0.45, bookmaker_prob=0.50,
        volume=10_000.0, cfg=cfg,
    ) == "BOOKMAKER_PROB_TOO_LOW"


def test_passes_filters_volume_too_low():
    """volume < min_market_volume → VOLUME_TOO_LOW."""
    cfg = _make_cfg()
    assert _passes_filters(
        gap=0.10, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=1_000.0, cfg=cfg,
    ) == "VOLUME_TOO_LOW"


def test_passes_filters_gap_threshold_adj_negative_lowers_bar():
    """Negative gap_threshold_adj → effective threshold drops, borderline gap passes."""
    cfg = _make_cfg()
    # gap=0.07 < default 0.08, but adj=-0.02 → effective=max(0, 0.06) → passes
    assert _passes_filters(
        gap=0.07, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg, gap_threshold_adj=-0.02,
    ) is None


def test_passes_filters_gap_threshold_adj_positive_raises_bar():
    """Positive gap_threshold_adj raises effective threshold → borderline gap blocked."""
    cfg = _make_cfg()
    # gap=0.09 > default 0.08, but adj=+0.05 → effective=0.13 → fails
    assert _passes_filters(
        gap=0.09, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg, gap_threshold_adj=0.05,
    ) == "GAP_TOO_LOW"


# ── _compute_stake ───────────────────────────────────────────────

def test_compute_stake_confidence_a_no_gap_multiplier():
    """A confidence, gap in normal zone → bankroll * 0.05 * 1.0 * win_prob."""
    cfg = _make_cfg()
    stake = _compute_stake(bankroll=1000.0, confidence="A", gap=0.10, win_prob=0.65, cfg=cfg)
    assert abs(stake - 1000.0 * 0.05 * 0.65) < 0.01


def test_compute_stake_confidence_b_lower_than_a():
    """B confidence → base_pct=confidence_b_pct < confidence_a_pct → smaller stake."""
    cfg = _make_cfg()
    stake_a = _compute_stake(bankroll=1000.0, confidence="A", gap=0.10, win_prob=0.65, cfg=cfg)
    stake_b = _compute_stake(bankroll=1000.0, confidence="B", gap=0.10, win_prob=0.65, cfg=cfg)
    assert stake_b < stake_a


def test_compute_stake_hard_cap_max_single_bet():
    """Very large bankroll → capped at max_single_bet_usdc."""
    cfg = _make_cfg()
    stake = _compute_stake(bankroll=100_000.0, confidence="A", gap=0.30, win_prob=0.90, cfg=cfg)
    assert stake <= cfg.max_single_bet_usdc


def test_compute_stake_high_gap_applies_multiplier():
    """gap in high zone → stake includes high_gap_multiplier (1.2)."""
    cfg = _make_cfg()
    stake_normal = _compute_stake(bankroll=1000.0, confidence="A", gap=0.10, win_prob=0.65, cfg=cfg)
    stake_high = _compute_stake(bankroll=1000.0, confidence="A", gap=0.20, win_prob=0.65, cfg=cfg)
    assert abs(stake_high - stake_normal * 1.2) < 0.01


# ── _check_event_guard ───────────────────────────────────────────

def test_check_event_guard_no_event_id_passes():
    """event_id=None → always None (passes)."""
    assert _check_event_guard(None, "moneyline", Direction.BUY_YES, {}) is None


def test_check_event_guard_empty_positions_passes():
    """No existing positions for event → passes."""
    assert _check_event_guard("evt1", "moneyline", Direction.BUY_YES, {}) is None


def test_check_event_guard_same_market_type_blocked():
    """Same event, same market_type → EVENT_GUARD_SAME_MARKET_TYPE."""
    from unittest.mock import MagicMock
    pos = MagicMock()
    pos.event_id = "evt1"
    pos.direction = Direction.BUY_YES
    pos.sports_market_type = "moneyline"
    result = _check_event_guard("evt1", "moneyline", Direction.BUY_YES, {"cid1": pos})
    assert result == "EVENT_GUARD_SAME_MARKET_TYPE"


def test_check_event_guard_max_positions_blocked():
    """3 existing positions on same event → EVENT_GUARD_MAX_POSITIONS."""
    from unittest.mock import MagicMock
    positions = {}
    for i in range(3):
        pos = MagicMock()
        pos.event_id = "evt1"
        pos.direction = Direction.BUY_YES
        pos.sports_market_type = f"type_{i}"
        positions[f"cid_{i}"] = pos
    result = _check_event_guard("evt1", "moneyline", Direction.BUY_YES, positions)
    assert result == "EVENT_GUARD_MAX_POSITIONS"


def test_check_event_guard_different_event_passes():
    """Existing position on different event → not blocked."""
    from unittest.mock import MagicMock
    pos = MagicMock()
    pos.event_id = "evt_other"
    pos.direction = Direction.BUY_YES
    pos.sports_market_type = "moneyline"
    result = _check_event_guard("evt1", "moneyline", Direction.BUY_YES, {"cid1": pos})
    assert result is None
