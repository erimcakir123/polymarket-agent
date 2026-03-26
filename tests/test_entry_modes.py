"""Tests for three-mode entry strategy."""
from unittest.mock import MagicMock, patch
import pytest


def _make_estimate(ai_prob, confidence):
    est = MagicMock()
    est.ai_probability = ai_prob
    est.confidence = confidence
    return est


def _make_market(yes_price, cid="cid-001", slug="test-market", question="Will X win?"):
    m = MagicMock()
    m.condition_id = cid
    m.yes_price = yes_price
    m.slug = slug
    m.question = question
    m.sport_tag = ""
    return m


def _make_gate():
    """Create a minimal EntryGate with mocked dependencies."""
    from src.entry_gate import EntryGate
    cfg = MagicMock()
    cfg.edge.min_edge = 0.06
    cfg.edge.fill_ratio_scaling = False
    cfg.edge.default_spread = 0.0
    cfg.edge.confidence_multipliers = None
    cfg.consensus_entry.enabled = False
    cfg.risk.max_positions = 10
    gate = EntryGate.__new__(EntryGate)
    gate.config = cfg
    gate.portfolio = MagicMock()
    gate.portfolio.active_position_count = 0
    gate.portfolio.count_by_entry_reason = MagicMock(return_value=0)
    gate.odds_api = MagicMock()
    gate.odds_api.available = False
    gate.manip_guard = MagicMock()
    gate.manip_guard.check.return_value = MagicMock(ok=True)
    gate.manip_guard.adjust_position_size = lambda size, _: size
    gate.risk = MagicMock()
    gate.risk.calculate_position_size = MagicMock(return_value=10.0)
    gate.trade_log = MagicMock()
    gate._far_market_ids = set()
    gate._analyzed_market_ids = {}
    return gate


def test_winner_mode_enters_without_edge():
    """AI >= 65% should enter even if market price equals AI probability (no edge)."""
    gate = _make_gate()
    # AI says 80%, market says 80% -> zero edge, but should WINNER-enter
    market = _make_market(yes_price=0.80)
    estimate = _make_estimate(ai_prob=0.80, confidence="B+")
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.80)
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [market], {market.condition_id: estimate},
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 1
    assert candidates[0]["mode"] == "WINNER"
    from src.models import Direction
    assert candidates[0]["direction"] == Direction.BUY_YES


def test_winner_mode_b_minus_rejected():
    """Winner mode should reject B- confidence."""
    gate = _make_gate()
    market = _make_market(yes_price=0.50)
    estimate = _make_estimate(ai_prob=0.80, confidence="B-")
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.80)
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [market], {market.condition_id: estimate},
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 0


def test_underdog_enters_with_edge_a_plus():
    """AI 40%, market 12% -> underdog YES — enters if A/B+ confidence."""
    gate = _make_gate()
    market = _make_market(yes_price=0.12)
    estimate = _make_estimate(ai_prob=0.40, confidence="A")
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.40)
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [market], {market.condition_id: estimate},
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 1
    assert candidates[0]["mode"] == "UNDERDOG"


def test_underdog_rejects_b_minus():
    """Underdog mode must reject B- confidence."""
    gate = _make_gate()
    market = _make_market(yes_price=0.12)
    estimate = _make_estimate(ai_prob=0.40, confidence="B-")
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.40)
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [market], {market.condition_id: estimate},
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 0


def test_deadzone_allows_b_minus():
    """Dead zone (55% AI, 40% market) allows B- confidence."""
    gate = _make_gate()
    market = _make_market(yes_price=0.40)
    estimate = _make_estimate(ai_prob=0.55, confidence="B-")
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.55)
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [market], {market.condition_id: estimate},
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 1
    assert candidates[0]["mode"] == "DEADZONE"


def test_winner_score_higher_than_edge_score():
    """Winner candidate (95% AI, B+) should outrank edge candidate (20% edge, A)."""
    from src.models import Direction
    gate = _make_gate()

    m_winner = _make_market(yes_price=0.70, cid="win-001", slug="winner", question="Team A wins?")
    est_winner = _make_estimate(ai_prob=0.95, confidence="B+")

    m_edge = _make_market(yes_price=0.30, cid="edge-001", slug="edger", question="Team B wins?")
    est_edge = _make_estimate(ai_prob=0.50, confidence="A")  # dead zone, 20% edge

    estimates = {
        "win-001": est_winner,
        "edge-001": est_edge,
    }
    with patch("src.sanity_check.check_bet_sanity") as mock_sanity:
        mock_sanity.return_value = MagicMock(ok=True)
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            def anchor(ai_prob, **kwargs):
                return MagicMock(probability=ai_prob)
            mock_anchor.side_effect = anchor
            with patch("src.probability_engine.get_edge_threshold_adjustment", return_value=0.0):
                candidates = gate._evaluate_candidates(
                    [m_winner, m_edge], estimates,
                    bankroll=1000.0, cycle_count=1, fresh_scan=True,
                )
    assert len(candidates) == 2
    assert candidates[0]["market"].condition_id == "win-001", "Winner should rank first"
