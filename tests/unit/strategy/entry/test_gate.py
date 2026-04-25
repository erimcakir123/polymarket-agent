"""EntryGate + GateConfig testleri — gap-based entry logic."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.strategy.entry.gate import (
    GateConfig,
    EntryGate,
    _classify_confidence,
    _gap_multiplier,
    _compute_stake,
    _passes_filters,
)


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


# ── GateConfig defaults ──────────────────────────────────────────
def test_gate_config_defaults_hard_cap_overflow():
    assert _make_cfg().hard_cap_overflow_pct == 0.02


def test_gate_config_defaults_min_entry_size_pct():
    assert _make_cfg().min_entry_size_pct == 0.015


def test_gate_config_defaults_min_gap_threshold():
    assert _make_cfg().min_gap_threshold == 0.08


# ── _classify_confidence ─────────────────────────────────────────
def test_confidence_a_with_sharp():
    assert _classify_confidence(has_sharp=True, bm_weight=6.0) == "A"


def test_confidence_b_no_sharp():
    assert _classify_confidence(has_sharp=False, bm_weight=6.0) == "B"


def test_confidence_c_low_weight():
    assert _classify_confidence(has_sharp=True, bm_weight=3.0) == "C"


# ── _gap_multiplier ──────────────────────────────────────────────
def test_gap_multiplier_normal():
    cfg = _make_cfg()
    assert _gap_multiplier(gap=0.10, cfg=cfg) == 1.0


def test_gap_multiplier_high_zone():
    cfg = _make_cfg()
    assert _gap_multiplier(gap=0.20, cfg=cfg) == 1.2


def test_gap_multiplier_extreme_zone():
    cfg = _make_cfg()
    assert _gap_multiplier(gap=0.26, cfg=cfg) == 1.3


# ── _passes_filters ──────────────────────────────────────────────
def test_filters_pass_nominal():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
    )
    assert reason is None


def test_filters_gap_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.05, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
    )
    assert reason == "GAP_TOO_LOW"


def test_filters_price_out_of_range_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.10, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
    )
    assert reason == "PRICE_OUT_OF_RANGE"


def test_filters_volume_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=3_000.0, cfg=cfg,
    )
    assert reason == "VOLUME_TOO_LOW"


def test_filters_bookmaker_prob_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.45, bookmaker_prob=0.55,
        volume=10_000.0, cfg=cfg,
    )
    assert reason == "BOOKMAKER_PROB_TOO_LOW"


# ── _compute_stake ───────────────────────────────────────────────
def test_compute_stake_confidence_a_no_gap_mult():
    cfg = _make_cfg()
    stake = _compute_stake(
        bankroll=1000.0, confidence="A", gap=0.10,
        win_prob=0.65, cfg=cfg,
    )
    assert abs(stake - 1000 * 0.05 * 0.65) < 0.01


def test_compute_stake_high_gap_multiplier():
    cfg = _make_cfg()
    stake = _compute_stake(
        bankroll=1000.0, confidence="A", gap=0.20,
        win_prob=0.65, cfg=cfg,
    )
    assert abs(stake - 1000 * 0.05 * 0.65 * 1.2) < 0.01


def test_compute_stake_hard_cap():
    cfg = _make_cfg()
    stake = _compute_stake(
        bankroll=10_000.0, confidence="A", gap=0.30,
        win_prob=0.90, cfg=cfg,
    )
    assert stake <= 10_000 * 0.05


# ── EntryGate.run() ──────────────────────────────────────────────
def test_gate_run_empty_markets_returns_empty():
    cfg = _make_cfg()
    gate = EntryGate(
        config=cfg, portfolio=None, circuit_breaker=None,
        cooldown=None, blacklist=None,
        odds_enricher=None, manipulation_checker=None,
    )
    assert gate.run([]) == []


def test_gate_run_inactive_sport_skipped():
    """active_sports boşsa tüm marketler atlanır."""
    cfg = _make_cfg(active_sports=[])
    gate = EntryGate(
        config=cfg, portfolio=None, circuit_breaker=None,
        cooldown=None, blacklist=None,
        odds_enricher=MagicMock(), manipulation_checker=None,
    )
    market = MagicMock()
    market.sport_tag = "basketball_nba"
    result = gate.run([market])
    assert len(result) == 1
    assert result[0].signal is None
    assert result[0].skipped_reason == "INACTIVE_SPORT"


def test_gate_run_same_event_same_direction_blocked():
    """Aynı event_id + aynı yön → BLOCKED."""
    from src.models.enums import Direction

    cfg = _make_cfg(active_sports=["basketball_nba"])

    mock_prob = MagicMock()
    mock_prob.prob = 0.70
    mock_prob.has_sharp = True
    mock_prob.num_bookmakers = 7.0

    mock_enrich = MagicMock()
    mock_enrich.probability = mock_prob
    mock_enrich.fail_reason = None

    existing_pos = MagicMock()
    existing_pos.event_id = "evt_001"
    existing_pos.direction = Direction.BUY_YES

    mock_portfolio = MagicMock()
    mock_portfolio.positions = {"some_cid": existing_pos}
    mock_portfolio.bankroll.return_value = 1000.0

    gate = EntryGate(
        config=cfg, portfolio=mock_portfolio, circuit_breaker=None,
        cooldown=None, blacklist=None,
        odds_enricher=lambda m: mock_enrich,
        manipulation_checker=None,
    )

    market = MagicMock()
    market.condition_id = "new_cid"
    market.sport_tag = "basketball_nba"
    market.yes_price = 0.45
    market.volume_24h = 10_000.0
    market.liquidity = 5_000.0
    market.event_id = "evt_001"

    result = gate.run([market])
    assert len(result) == 1
    assert result[0].skipped_reason == "EVENT_GUARD_SAME_DIRECTION"


# ── Spread filter tests ──────────────────────────────────────────
def test_filters_spread_price_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.15, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="spreads",
    )
    assert reason == "PRICE_OUT_OF_RANGE"


def test_filters_spread_price_in_range():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.50, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="spreads",
    )
    assert reason is None


def test_filters_spread_large_spread_needs_gap_bonus():
    """spread_line >= 10 → efektif gap_threshold 0.08+0.02=0.10 olur."""
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.09, polymarket_price=0.50, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="spreads",
        spread_line=10.5,
    )
    assert reason == "GAP_TOO_LOW"


def test_filters_spread_small_spread_normal_gap():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.09, polymarket_price=0.50, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="spreads",
        spread_line=5.5,
    )
    assert reason is None


# ── Totals filter tests ──────────────────────────────────────────
def test_filters_totals_price_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.15, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="totals",
    )
    assert reason == "PRICE_OUT_OF_RANGE"


def test_filters_totals_target_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.50, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="totals",
        total_line=150.0,
    )
    assert reason == "TOTAL_TOO_LOW"


def test_filters_totals_pass():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.50, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="totals",
        total_line=220.5,
    )
    assert reason is None
