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
    """Aynı event_id + aynı market_type → BLOCKED (same market type guard)."""
    from src.models.enums import Direction

    cfg = _make_cfg(active_sports=["basketball_nba"])

    mock_prob = MagicMock()
    mock_prob.probability = 0.70
    mock_prob.has_sharp = True
    mock_prob.num_bookmakers = 7.0

    mock_enrich = MagicMock()
    mock_enrich.probability = mock_prob
    mock_enrich.fail_reason = None

    existing_pos = MagicMock()
    existing_pos.event_id = "evt_001"
    existing_pos.direction = Direction.BUY_YES
    existing_pos.sports_market_type = "moneyline"

    mock_portfolio = MagicMock()
    mock_portfolio.positions = {"some_cid": existing_pos}
    mock_portfolio.bankroll = 1000.0

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
    market.sports_market_type = "moneyline"

    result = gate.run([market])
    assert len(result) == 1
    assert result[0].skipped_reason == "EVENT_GUARD_SAME_MARKET_TYPE"


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


# ── EdgeContext gap adjustments (_passes_filters direct) ─────────

def test_passes_filters_injury_opp_gap_reduction_allows_entry():
    """Opponent injury reduces gap threshold → borderline gap now passes."""
    cfg = _make_cfg()
    # gap=0.07 is below default threshold 0.08, but adj=-0.02 → effective=0.06 → passes
    reason = _passes_filters(
        gap=0.07, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        gap_threshold_adj=-0.02,
    )
    assert reason is None


def test_passes_filters_own_injury_gap_increase_blocks_entry():
    """Own team injury raises gap threshold → borderline gap now blocked."""
    cfg = _make_cfg()
    # gap=0.09 passes default 0.08, but adj=+0.05 → effective=0.13 → fails
    reason = _passes_filters(
        gap=0.09, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        gap_threshold_adj=0.05,
    )
    assert reason == "GAP_TOO_LOW"


def test_passes_filters_b2b_opponent_gap_increase_blocks_entry():
    """Opponent B2B adds 0.03 → borderline gap blocked."""
    cfg = _make_cfg()
    # gap=0.09 passes default 0.08, but adj=+0.03 → effective=0.11 → fails
    reason = _passes_filters(
        gap=0.09, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        gap_threshold_adj=0.03,
    )
    assert reason == "GAP_TOO_LOW"


def test_passes_filters_no_adjustment_unchanged():
    """gap_threshold_adj=0.0 → same behaviour as before (no regression)."""
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        gap_threshold_adj=0.0,
    )
    assert reason is None


def test_passes_filters_negative_adj_clamps_to_zero_threshold():
    """Negative adjustment never makes threshold go below zero."""
    cfg = _make_cfg(min_gap_threshold=0.02)
    # adj=-0.10 would make threshold -0.08 without clamp
    # With clamp → max(0, 0.02 + (-0.10)) = 0.0 → any positive gap passes
    reason = _passes_filters(
        gap=0.001, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        gap_threshold_adj=-0.10,
    )
    assert reason is None  # gap > 0.0 threshold → passes


# ── EntryGate integration — EdgeEnricher wiring ──────────────────

def test_gate_run_no_edge_enricher_still_works():
    """Gate without edge_enricher processes markets normally (no regression)."""
    cfg = _make_cfg(active_sports=["basketball_nba"])

    mock_prob = MagicMock()
    mock_prob.probability = 0.75
    mock_prob.has_sharp = True
    mock_prob.num_bookmakers = 7.0

    mock_enrich = MagicMock()
    mock_enrich.probability = mock_prob
    mock_enrich.fail_reason = None

    mock_portfolio = MagicMock()
    mock_portfolio.positions = {}
    mock_portfolio.bankroll = 1000.0

    gate = EntryGate(
        config=cfg, portfolio=mock_portfolio, circuit_breaker=None,
        cooldown=None, blacklist=None,
        odds_enricher=lambda m: mock_enrich, manipulation_checker=None,
        edge_enricher=None,
    )

    market = MagicMock()
    market.condition_id = "cid1"
    market.sport_tag = "basketball_nba"
    market.yes_price = 0.50
    market.volume_24h = 10_000.0
    market.event_id = "evt1"
    market.sports_market_type = "moneyline"
    market.question = "Lakers vs Celtics"

    result = gate.run([market])
    assert len(result) == 1
    assert result[0].signal is not None


def test_gate_run_edge_enricher_opponent_injury_increases_stake():
    """Opponent injury (is_own_team_injury=False) → size_multiplier applied to stake."""
    from src.orchestration.edge_enricher import EdgeContext

    cfg = _make_cfg(active_sports=["basketball_nba"])

    mock_prob = MagicMock()
    mock_prob.probability = 0.75
    mock_prob.has_sharp = True
    mock_prob.num_bookmakers = 7.0

    mock_enrich = MagicMock()
    mock_enrich.probability = mock_prob
    mock_enrich.fail_reason = None

    mock_portfolio = MagicMock()
    mock_portfolio.positions = {}
    mock_portfolio.bankroll = 1000.0

    # Edge context: opponent has injury → size multiplier 1.3, gap threshold -0.02
    opp_injury_ctx = EdgeContext(
        has_recent_injury=True,
        is_own_team_injury=False,
        is_opponent_back_to_back=False,
        is_our_back_to_back=False,
    )
    mock_edge = MagicMock()
    mock_edge.enrich.return_value = opp_injury_ctx

    gate = EntryGate(
        config=cfg, portfolio=mock_portfolio, circuit_breaker=None,
        cooldown=None, blacklist=None,
        odds_enricher=lambda m: mock_enrich, manipulation_checker=None,
        edge_enricher=mock_edge,
    )

    market = MagicMock()
    market.condition_id = "cid2"
    market.sport_tag = "basketball_nba"
    market.yes_price = 0.50
    market.volume_24h = 10_000.0
    market.event_id = "evt2"
    market.sports_market_type = "moneyline"
    market.question = "Lakers vs Celtics"

    result = gate.run([market])
    assert len(result) == 1
    sig = result[0].signal
    assert sig is not None
    # gap=0.25 → extreme_gap_multiplier=1.3, then injury_size_multiplier=1.3, then capped
    # _compute_stake: 1000 * 0.05 * 1.3 (gap_mult) * 0.75 (win_prob) = 48.75
    # after injury multiplier: 48.75 * 1.3 = 63.375, capped at max_single_bet_usdc=75
    expected = min(1000.0 * 0.05 * 1.3 * 0.75 * 1.3, cfg.max_single_bet_usdc)
    assert abs(sig.size_usdc - expected) < 0.01


def test_gate_run_edge_enricher_own_injury_blocks_borderline_gap():
    """Own team injury raises threshold → market that would pass without edge ctx is skipped."""
    from src.orchestration.edge_enricher import EdgeContext

    cfg = _make_cfg(active_sports=["basketball_nba"])

    mock_prob = MagicMock()
    mock_prob.probability = 0.585   # gap = 0.585 - 0.50 = 0.085 (just above default 0.08)
    mock_prob.has_sharp = True
    mock_prob.num_bookmakers = 7.0

    mock_enrich = MagicMock()
    mock_enrich.probability = mock_prob
    mock_enrich.fail_reason = None

    mock_portfolio = MagicMock()
    mock_portfolio.positions = {}
    mock_portfolio.bankroll = 1000.0

    # Own team injury → star_out_self_gap_bonus=0.05 added → effective threshold=0.13 → gap=0.085 fails
    own_injury_ctx = EdgeContext(
        has_recent_injury=True,
        is_own_team_injury=True,
        is_opponent_back_to_back=False,
        is_our_back_to_back=False,
    )
    mock_edge = MagicMock()
    mock_edge.enrich.return_value = own_injury_ctx

    gate = EntryGate(
        config=cfg, portfolio=mock_portfolio, circuit_breaker=None,
        cooldown=None, blacklist=None,
        odds_enricher=lambda m: mock_enrich, manipulation_checker=None,
        edge_enricher=mock_edge,
    )

    market = MagicMock()
    market.condition_id = "cid3"
    market.sport_tag = "basketball_nba"
    market.yes_price = 0.50
    market.volume_24h = 10_000.0
    market.event_id = "evt3"
    market.sports_market_type = "moneyline"
    market.question = "Lakers vs Celtics"

    result = gate.run([market])
    assert len(result) == 1
    assert result[0].skipped_reason == "GAP_TOO_LOW"


# ── Team ID resolution via edge enricher ────────────────────────

def _make_market_mock(
    condition_id: str,
    question: str,
    yes_price: float = 0.45,
    volume: float = 10_000.0,
    sport_tag: str = "basketball_nba",
    event_id: str = "evt_x",
) -> MagicMock:
    """Shared MagicMock factory for gate.run() market fixtures."""
    m = MagicMock()
    m.condition_id = condition_id
    m.sport_tag = sport_tag
    m.yes_price = yes_price
    m.volume_24h = volume
    m.event_id = event_id
    m.sports_market_type = "moneyline"
    m.question = question
    return m


def _make_gate_with_edge(mock_edge: MagicMock) -> EntryGate:
    """Gate with a passing odds mock + portfolio + given edge enricher."""
    cfg = _make_cfg(active_sports=["basketball_nba"])

    mock_prob = MagicMock()
    mock_prob.probability = 0.75
    mock_prob.has_sharp = True
    mock_prob.num_bookmakers = 7.0

    mock_enrich = MagicMock()
    mock_enrich.probability = mock_prob
    mock_enrich.fail_reason = None

    mock_portfolio = MagicMock()
    mock_portfolio.positions = {}
    mock_portfolio.bankroll = 1000.0

    return EntryGate(
        config=cfg,
        portfolio=mock_portfolio,
        circuit_breaker=None,
        cooldown=None,
        blacklist=None,
        odds_enricher=lambda m: mock_enrich,
        manipulation_checker=None,
        edge_enricher=mock_edge,
    )


def test_gate_run_passes_team_ids_to_edge_enricher() -> None:
    """extract_teams → resolve_nba_espn_id → edge_enricher.enrich() receives correct IDs."""
    mock_edge = MagicMock()
    mock_edge.enrich.return_value = None  # no edge context

    gate = _make_gate_with_edge(mock_edge)
    market = _make_market_mock(
        condition_id="cid_lal_bos",
        question="Will the Los Angeles Lakers beat the Boston Celtics?",
    )

    gate.run([market])

    mock_edge.enrich.assert_called_once()
    call_kwargs = mock_edge.enrich.call_args
    assert call_kwargs.kwargs.get("our_team_id") == "13"
    assert call_kwargs.kwargs.get("opp_team_id") == "2"


def test_gate_run_graceful_fallback_on_unparseable_question() -> None:
    """Empty question → extract_teams returns (None, None) → edge_enricher gets empty strings."""
    mock_edge = MagicMock()
    mock_edge.enrich.return_value = None

    gate = _make_gate_with_edge(mock_edge)
    market = _make_market_mock(
        condition_id="cid_empty_q",
        question="",  # empty → extract_teams returns (None, None)
    )

    gate.run([market])

    call_kwargs = mock_edge.enrich.call_args
    assert call_kwargs.kwargs.get("our_team_id") == ""
    assert call_kwargs.kwargs.get("opp_team_id") == ""
