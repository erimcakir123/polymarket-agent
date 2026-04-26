"""NBA end-to-end integration test suite — mock data, no real API calls."""
from __future__ import annotations

from unittest.mock import MagicMock
from datetime import datetime, timezone

import pytest

from tests.integration.fixtures.nba_mock_data import (
    make_gate, make_market, make_position, make_score_info, make_enricher_result,
)
from src.orchestration.edge_enricher import EdgeContext
from src.strategy.exit import near_resolve, scale_out
from src.strategy.exit import nba_score_exit, nba_spread_exit, nba_totals_exit


# ═══════════════════════════════════════════════
# 1. ENTRY SCENARIOS
# ═══════════════════════════════════════════════

def test_entry_moneyline_passes_gate_with_sufficient_gap() -> None:
    """Gap 13% + sharp book → entry signal, confidence A."""
    gate, enricher_fn = make_gate()
    enrich = make_enricher_result(prob=0.58, has_sharp=True, num_bookmakers=7.0)
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45)  # gap = 0.58 - 0.45 = 0.13
    results = gate.run([market])

    assert len(results) == 1
    assert results[0].signal is not None
    assert results[0].signal.confidence == "A"
    assert results[0].signal.size_usdc > 0


def test_entry_skipped_low_gap() -> None:
    """Gap 5% < threshold 8% → skip."""
    gate, enricher_fn = make_gate()
    enrich = make_enricher_result(prob=0.50)  # gap = 0.50 - 0.45 = 0.05
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45)
    results = gate.run([market])

    assert results[0].signal is None
    assert results[0].skipped_reason == "GAP_TOO_LOW"


def test_entry_skipped_low_volume() -> None:
    """Gap 13% ama volume $3K < min $5K → skip."""
    gate, enricher_fn = make_gate()
    enrich = make_enricher_result(prob=0.58)
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45, volume_24h=3_000.0)
    results = gate.run([market])

    assert results[0].signal is None
    assert results[0].skipped_reason == "VOLUME_TOO_LOW"


def test_entry_skipped_extreme_price() -> None:
    """Polymarket price 0.09 < min_polymarket_price 0.10 → skip."""
    gate, enricher_fn = make_gate()
    enrich = make_enricher_result(prob=0.22)  # gap = 0.22 - 0.09 = 0.13
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.09)
    results = gate.run([market])

    assert results[0].signal is None
    assert results[0].skipped_reason == "PRICE_OUT_OF_RANGE"


def test_entry_spread_passes_gate() -> None:
    """Spread market Lakers -5.5, price 0.52, gap 13% → entry."""
    gate, enricher_fn = make_gate()
    enrich = make_enricher_result(prob=0.65)  # gap = 0.65 - 0.52 = 0.13
    enricher_fn.return_value = enrich

    market = make_market(
        question="Spread: Los Angeles Lakers (-5.5)",
        yes_price=0.52,
        sports_market_type="spreads",
    )
    results = gate.run([market])

    assert results[0].signal is not None
    assert results[0].signal.sports_market_type == "spreads"


def test_entry_totals_passes_gate() -> None:
    """Totals market O/U 220.5, price 0.52, gap 13% → entry."""
    gate, enricher_fn = make_gate()
    enrich = make_enricher_result(prob=0.65)
    enricher_fn.return_value = enrich

    market = make_market(
        question="Los Angeles Lakers vs Boston Celtics: O/U 220.5",
        yes_price=0.52,
        sports_market_type="totals",
    )
    results = gate.run([market])

    assert results[0].signal is not None
    assert results[0].signal.sports_market_type == "totals"


# ═══════════════════════════════════════════════
# 2. INJURY EDGE SCENARIOS
# ═══════════════════════════════════════════════

def _make_edge_enricher_mock(ctx: EdgeContext):
    mock = MagicMock()
    mock.enrich.return_value = ctx
    return mock


def test_entry_injury_opponent_team_lowers_threshold() -> None:
    """Celtics injury (opp team) → threshold -2% → 7% gap passes 6% threshold."""
    ctx = EdgeContext(has_recent_injury=True, is_own_team_injury=False)
    gate, enricher_fn = make_gate(min_gap_threshold=0.08, edge_enricher=_make_edge_enricher_mock(ctx))
    # prob=0.52, yes_price=0.45 → gap=0.07 (below 0.08, but above 0.06 after injury adj)
    enrich = make_enricher_result(prob=0.52)
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45)
    results = gate.run([market])

    assert results[0].signal is not None, "Opponent injury should lower threshold, allowing 7% gap"


def test_entry_injury_own_team_raises_threshold() -> None:
    """Lakers injury (own team) → threshold +5% → 10% gap fails 13% threshold."""
    ctx = EdgeContext(has_recent_injury=True, is_own_team_injury=True)
    gate, enricher_fn = make_gate(min_gap_threshold=0.08, edge_enricher=_make_edge_enricher_mock(ctx))
    # prob=0.55, yes_price=0.45 → gap=0.10 (above 0.08 normally, but fails 0.13 with +5% bonus)
    enrich = make_enricher_result(prob=0.55)
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45)
    results = gate.run([market])

    assert results[0].signal is None, "Own team injury raises threshold, 10% gap should fail"
    assert results[0].skipped_reason == "GAP_TOO_LOW"


def test_entry_injury_not_recent_no_effect() -> None:
    """No recent injury → EdgeContext has_recent_injury=False → normal threshold."""
    ctx = EdgeContext(has_recent_injury=False)
    gate, enricher_fn = make_gate(min_gap_threshold=0.08, edge_enricher=_make_edge_enricher_mock(ctx))
    enrich = make_enricher_result(prob=0.58)  # gap=0.13 → passes normally
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45)
    results = gate.run([market])

    assert results[0].signal is not None, "No injury modifier → normal gap passes"


def test_entry_injury_questionable_has_no_effect() -> None:
    """Questionable status → _find_injury returns None → no modifier (documents actual behavior)."""
    # EdgeEnricher._find_injury() only returns Out/Doubtful — Questionable is ignored.
    ctx = EdgeContext(has_recent_injury=False)  # Questionable → no injury context
    gate, enricher_fn = make_gate(min_gap_threshold=0.08, edge_enricher=_make_edge_enricher_mock(ctx))
    enrich = make_enricher_result(prob=0.58)
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45)
    results = gate.run([market])

    assert results[0].signal is not None, "Questionable not treated as Out — normal flow"


# ═══════════════════════════════════════════════
# 3. BACK-TO-BACK SCENARIOS
# ═══════════════════════════════════════════════

def test_entry_b2b_opponent_raises_threshold() -> None:
    """Opponent B2B → threshold +3% → 9% gap fails 11% threshold."""
    ctx = EdgeContext(is_opponent_back_to_back=True)
    gate, enricher_fn = make_gate(min_gap_threshold=0.08, edge_enricher=_make_edge_enricher_mock(ctx))
    enrich = make_enricher_result(prob=0.54)  # gap=0.54-0.45=0.09 (passes 0.08, fails 0.11)
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45)
    results = gate.run([market])

    assert results[0].signal is None
    assert results[0].skipped_reason == "GAP_TOO_LOW"


def test_entry_b2b_self_raises_threshold_more() -> None:
    """Own team B2B → threshold +5% → 12% gap fails 13% threshold."""
    ctx = EdgeContext(is_our_back_to_back=True)
    gate, enricher_fn = make_gate(min_gap_threshold=0.08, edge_enricher=_make_edge_enricher_mock(ctx))
    enrich = make_enricher_result(prob=0.57)  # gap=0.57-0.45=0.12 (passes 0.08, fails 0.13)
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45)
    results = gate.run([market])

    assert results[0].signal is None
    assert results[0].skipped_reason == "GAP_TOO_LOW"


# ═══════════════════════════════════════════════
# 4. EXIT SCENARIOS — MONEYLINE (pure function tests)
# ═══════════════════════════════════════════════

def test_exit_q3_hold() -> None:
    score = make_score_info(period_number=3, clock_seconds=300, our_score=70, opp_score=85)
    result = nba_score_exit.check(score_info=score, elapsed_pct=0.75, sport_tag="basketball_nba")
    assert result is None


def test_exit_q4_math_dead() -> None:
    """0.861 × √240 ≈ 13.3; deficit=17 ≥ 13.3 → MATH_DEAD."""
    score = make_score_info(period_number=4, clock_seconds=240, our_score=83, opp_score=100)
    result = nba_score_exit.check(score_info=score, elapsed_pct=0.95, sport_tag="basketball_nba")
    assert result is not None
    assert "MATH_DEAD" in result.detail


def test_exit_q4_empirical_blowout() -> None:
    """clock=720 (Q4 başı), deficit=20 → empirical dead (predictive devre dışı — izole test)."""
    score = make_score_info(period_number=4, clock_seconds=720, our_score=80, opp_score=100)
    result = nba_score_exit.check(
        score_info=score, elapsed_pct=0.75, sport_tag="basketball_nba",
        predictive_enabled=False,
    )
    assert result is not None
    assert "EMPIRICAL_DEAD" in result.detail


def test_exit_q4_endgame_6_point() -> None:
    """clock=60, deficit=6 → empirical dead (son 1 dakika)."""
    score = make_score_info(period_number=4, clock_seconds=60, our_score=94, opp_score=100)
    result = nba_score_exit.check(score_info=score, elapsed_pct=0.99, sport_tag="basketball_nba")
    assert result is not None


def test_exit_overtime_dead() -> None:
    """OT, clock=60, deficit=8 → OT_DEAD."""
    score = make_score_info(period_number=5, clock_seconds=60, our_score=110, opp_score=118)
    result = nba_score_exit.check(score_info=score, elapsed_pct=1.05, sport_tag="basketball_nba")
    assert result is not None
    assert "OT_DEAD" in result.detail


def test_exit_take_profit_94() -> None:
    """bid_price=0.95 ≥ 0.94 → near_resolve fires, sell_pct=1.0."""
    result = near_resolve.check(bid_price=0.95, threshold=0.94)
    assert result is not None
    assert result.sell_pct == 1.0


def test_exit_scale_out_85() -> None:
    """bid_price=0.86, not scaled → scale_out fires, sell_pct=0.50."""
    result = scale_out.check(bid_price=0.86, already_scaled=False, threshold=0.85)
    assert result is not None
    assert result.sell_pct == 0.50


def test_exit_scale_out_already_done() -> None:
    """bid_price=0.87, already_scaled=True → None (HOLD)."""
    result = scale_out.check(bid_price=0.87, already_scaled=True, threshold=0.85)
    assert result is None


# ═══════════════════════════════════════════════
# 5. EXIT SCENARIOS — SPREAD (pure function tests)
# ═══════════════════════════════════════════════

def test_spread_exit_q3_hold() -> None:
    score = make_score_info(period_number=3, clock_seconds=300, our_score=70, opp_score=78)
    result = nba_spread_exit.check(score_info=score, spread_line=5.5, direction="BUY_YES")
    assert result is None


def test_spread_exit_math_dead() -> None:
    """Q4 clock=60, BUY_YES, spread_line=5.5, our=95, opp=100 → margin_to_cover=10.5 > 6.67 → DEAD."""
    score = make_score_info(period_number=4, clock_seconds=60, our_score=95, opp_score=100)
    result = nba_spread_exit.check(score_info=score, spread_line=5.5, direction="BUY_YES")
    assert result is not None
    assert "SPREAD_MATH_DEAD" in result.detail or "EMPIRICAL_DEAD" in result.detail


def test_spread_exit_key_number_3() -> None:
    """Q4 endgame, margin=3 ≥ endgame_margin(3) → exit."""
    # BUY_YES, spread_line=3.0, our=97, opp=100 → actual_diff=-3, margin=3.0-(-3)=6.0 ≥ 3
    score = make_score_info(period_number=4, clock_seconds=60, our_score=97, opp_score=100)
    result = nba_spread_exit.check(score_info=score, spread_line=3.0, direction="BUY_YES")
    assert result is not None


def test_spread_exit_key_number_7() -> None:
    """Q4 late 360s, margin=7 ≥ late_margin(7) → exit."""
    # BUY_YES, spread_line=7.0, our=93, opp=100 → actual_diff=-7, margin=7.0-(-7)=14.0 ≥ 7
    score = make_score_info(period_number=4, clock_seconds=360, our_score=93, opp_score=100)
    result = nba_spread_exit.check(score_info=score, spread_line=7.0, direction="BUY_YES")
    assert result is not None


def test_spread_exit_already_covering() -> None:
    """Already covering spread → margin_to_cover ≤ 0 → HOLD."""
    # BUY_YES, spread_line=5.5, our=110, opp=100 → actual_diff=10, margin=5.5-10=-4.5 ≤ 0
    score = make_score_info(period_number=4, clock_seconds=30, our_score=110, opp_score=100)
    result = nba_spread_exit.check(score_info=score, spread_line=5.5, direction="BUY_YES")
    assert result is None


# ═══════════════════════════════════════════════
# 6. EXIT SCENARIOS — TOTALS (pure function tests)
# ═══════════════════════════════════════════════

def test_totals_over_math_dead() -> None:
    """1.218 × √60 ≈ 9.44; points_needed=20 ≥ 9.44 → TOTALS_MATH_DEAD."""
    # current_total=200, target=220, side=over, points_needed=20
    score = make_score_info(period_number=4, clock_seconds=60, our_score=100, opp_score=100)
    result = nba_totals_exit.check(
        score_info=score, target_total=220.0, side="over",
    )
    assert result is not None
    assert "TOTALS_MATH_DEAD" in result.detail or "EMPIRICAL_DEAD" in result.detail


def test_totals_under_math_dead() -> None:
    """current=245, target=220, side=under → excess=25 > threshold ≈ 9.44 → dead."""
    score = make_score_info(period_number=4, clock_seconds=60, our_score=123, opp_score=122)
    result = nba_totals_exit.check(
        score_info=score, target_total=220.0, side="under",
    )
    assert result is not None


def test_totals_ot_over_windfall() -> None:
    """OT, side=over → OT_OVER_WINDFALL, sell_pct=0.75, partial=True."""
    score = make_score_info(period_number=5, clock_seconds=120, our_score=110, opp_score=110)
    result = nba_totals_exit.check(
        score_info=score, target_total=220.0, side="over",
    )
    assert result is not None
    assert result.sell_pct == 0.75
    assert result.partial is True
    assert "OT_OVER_WINDFALL" in result.detail


def test_totals_ot_under_immediate() -> None:
    """OT, side=under → OT_UNDER_DEAD, sell_pct=1.0."""
    score = make_score_info(period_number=5, clock_seconds=120, our_score=110, opp_score=110)
    result = nba_totals_exit.check(
        score_info=score, target_total=220.0, side="under",
    )
    assert result is not None
    assert result.sell_pct == 1.0


def test_totals_q3_hold() -> None:
    """Q3, current=80, target=220, side=over → HOLD."""
    score = make_score_info(period_number=3, clock_seconds=300, our_score=40, opp_score=40)
    result = nba_totals_exit.check(
        score_info=score, target_total=220.0, side="over",
    )
    assert result is None


# ═══════════════════════════════════════════════
# 7. INTEGRATION — END-TO-END FLOWS
# ═══════════════════════════════════════════════

def test_full_flow_entry_to_exit() -> None:
    """Gate entry → NBA Q4 score exit chain (no real API)."""
    # Step 1: Entry
    gate, enricher_fn = make_gate()
    enrich = make_enricher_result(prob=0.58)
    enricher_fn.return_value = enrich
    market = make_market(yes_price=0.45)
    results = gate.run([market])
    assert results[0].signal is not None

    # Step 2: Score exit check (Q4 blowout)
    score = make_score_info(period_number=4, clock_seconds=240, our_score=83, opp_score=100)
    exit_result = nba_score_exit.check(score_info=score, elapsed_pct=0.95, sport_tag="basketball_nba")
    assert exit_result is not None
    assert "MATH_DEAD" in exit_result.detail


def test_full_flow_entry_with_injury_edge() -> None:
    """Opponent injury lowers threshold → borderline 7% gap enters → larger sizing."""
    ctx = EdgeContext(has_recent_injury=True, is_own_team_injury=False)
    gate, enricher_fn = make_gate(edge_enricher=_make_edge_enricher_mock(ctx))
    # gap=0.07 normally fails 0.08 threshold, but passes 0.06 with injury adj
    enrich = make_enricher_result(prob=0.52, has_sharp=True, num_bookmakers=7.0)
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45)
    results = gate.run([market])

    assert results[0].signal is not None
    assert results[0].signal.size_usdc > 0


def test_full_flow_b2b_self_team() -> None:
    """Own team B2B → threshold +5% → 12% gap blocked."""
    ctx = EdgeContext(is_our_back_to_back=True)
    gate, enricher_fn = make_gate(edge_enricher=_make_edge_enricher_mock(ctx))
    # gap=0.12 normally passes 0.08, but fails 0.13 with +5% B2B adj
    enrich = make_enricher_result(prob=0.57)
    enricher_fn.return_value = enrich

    market = make_market(yes_price=0.45)
    results = gate.run([market])

    assert results[0].signal is None
    assert results[0].skipped_reason == "GAP_TOO_LOW"


# ═══════════════════════════════════════════════
# 8. EVENT GUARD SCENARIOS
# ═══════════════════════════════════════════════

def _make_open_position(event_id: str, market_type: str, direction: str = "BUY_YES"):
    pos = MagicMock()
    pos.event_id = event_id
    pos.sports_market_type = market_type
    pos.direction = direction
    return pos


def test_event_guard_same_event_same_type_blocks() -> None:
    """ML + ML same event → blocked (same market type)."""
    open_pos = _make_open_position("evt_001", "moneyline", "BUY_YES")
    gate, enricher_fn = make_gate(positions={"pos1": open_pos})
    enrich = make_enricher_result(prob=0.58)
    enricher_fn.return_value = enrich

    market = make_market(condition_id="cid_new", event_id="evt_001", sports_market_type="")
    results = gate.run([market])

    assert results[0].signal is None
    assert results[0].skipped_reason == "EVENT_GUARD_SAME_MARKET_TYPE"


def test_event_guard_same_event_ml_totals_allows() -> None:
    """ML position open + Totals new entry same event → ALLOW."""
    open_pos = _make_open_position("evt_001", "moneyline", "BUY_YES")
    gate, enricher_fn = make_gate(positions={"pos1": open_pos})
    enrich = make_enricher_result(prob=0.65)
    enricher_fn.return_value = enrich

    market = make_market(
        condition_id="cid_totals",
        event_id="evt_001",
        sports_market_type="totals",
        question="Los Angeles Lakers vs Boston Celtics: O/U 220.5",
        yes_price=0.52,
    )
    results = gate.run([market])

    assert results[0].signal is not None, "ML + Totals same event should be allowed"


def test_event_guard_max_2_per_event_blocks_third() -> None:
    """2 open positions same event → 3rd blocked (hard cap)."""
    pos1 = _make_open_position("evt_001", "moneyline")
    pos2 = _make_open_position("evt_001", "totals")
    gate, enricher_fn = make_gate(positions={"p1": pos1, "p2": pos2})
    enrich = make_enricher_result(prob=0.65)
    enricher_fn.return_value = enrich

    market = make_market(
        condition_id="cid_spread",
        event_id="evt_001",
        sports_market_type="spreads",
        question="Spread: Los Angeles Lakers (-5.5)",
        yes_price=0.52,
    )
    results = gate.run([market])

    assert results[0].signal is None
    assert results[0].skipped_reason == "EVENT_GUARD_MAX_POSITIONS"
