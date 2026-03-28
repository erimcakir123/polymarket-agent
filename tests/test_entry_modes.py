"""Tests for entry strategy (WINNER / SKIP — deadzone disabled)."""
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
    m.tags = []
    m.yes_token_id = "tok_yes"
    m.no_token_id = "tok_no"
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
    gate.manip_guard.check_market = MagicMock(return_value=MagicMock(ok=True))
    gate.manip_guard.adjust_position_size = lambda size, _: size
    gate.risk = MagicMock()
    risk_decision = MagicMock()
    risk_decision.size_usdc = 10.0
    gate.risk.evaluate = MagicMock(return_value=risk_decision)
    gate.trade_log = MagicMock()
    gate._far_market_ids = set()
    gate._analyzed_market_ids = {}
    return gate


class TestCaseA_Consensus:
    """When AI and market agree on the same favorite, enter that side."""

    def test_consensus_winner_high_prob(self):
        """AI=80% YES, market=70% YES -> both favor YES -> WINNER mode, BUY_YES."""
        gate = _make_gate()
        market = _make_market(yes_price=0.70)
        estimate = _make_estimate(ai_prob=0.80, confidence="B+")
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.80, method="shrunk_no_bookmaker")
            candidates = gate._evaluate_candidates(
                [market], {market.condition_id: estimate},
                bankroll=1000.0, cycle_count=1, fresh_scan=True,
            )
        assert len(candidates) == 1
        assert candidates[0]["mode"] == "WINNER"
        from src.models import Direction
        assert candidates[0]["direction"] == Direction.BUY_YES
        assert abs(candidates[0]["edge"] - 0.29) < 0.02

    def test_consensus_deadzone_now_skips(self):
        """AI=58% YES, market=55% YES -> agree on YES -> SKIP (deadzone disabled)."""
        gate = _make_gate()
        market = _make_market(yes_price=0.55)
        estimate = _make_estimate(ai_prob=0.58, confidence="B+")
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.58, method="shrunk_no_bookmaker")
            candidates = gate._evaluate_candidates(
                [market], {market.condition_id: estimate},
                bankroll=1000.0, cycle_count=1, fresh_scan=True,
            )
        assert len(candidates) == 0  # Deadzone disabled — no entry

    def test_consensus_skip_too_uncertain(self):
        """AI=52% YES, market=55% YES -> agree but AI < 55% -> SKIP (no entry)."""
        gate = _make_gate()
        market = _make_market(yes_price=0.55)
        estimate = _make_estimate(ai_prob=0.52, confidence="B+")
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.52, method="shrunk_no_bookmaker")
            candidates = gate._evaluate_candidates(
                [market], {market.condition_id: estimate},
                bankroll=1000.0, cycle_count=1, fresh_scan=True,
            )
        assert len(candidates) == 0

    def test_consensus_no_side(self):
        """AI=30% YES (=70% NO), market=25% YES (=75% NO) -> agree on NO -> BUY_NO."""
        gate = _make_gate()
        market = _make_market(yes_price=0.25)
        estimate = _make_estimate(ai_prob=0.30, confidence="A")
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.30, method="shrunk_no_bookmaker")
            candidates = gate._evaluate_candidates(
                [market], {market.condition_id: estimate},
                bankroll=1000.0, cycle_count=1, fresh_scan=True,
            )
        assert len(candidates) == 1
        from src.models import Direction
        assert candidates[0]["direction"] == Direction.BUY_NO
        assert candidates[0]["mode"] == "WINNER"


class TestCaseB_Disagree:
    """When AI and market disagree on the favorite, use standard shrinkage+edge."""

    def test_disagree_ai_no_market_yes_deadzone_skips(self):
        """AI=42% YES (NO fav), market=70% YES -> disagree -> 57.2% in deadzone -> SKIP."""
        gate = _make_gate()
        market = _make_market(yes_price=0.70)
        estimate = _make_estimate(ai_prob=0.42, confidence="A")
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.428, method="shrunk_no_bookmaker")
            candidates = gate._evaluate_candidates(
                [market], {market.condition_id: estimate},
                bankroll=1000.0, cycle_count=1, fresh_scan=True,
            )
        assert len(candidates) == 0  # 57.2% is in deadzone -> SKIP

    def test_disagree_high_prob_enters_winner(self):
        """AI=30% YES (NO fav=70%), market=70% YES -> disagree -> anchored 70% >= 65% -> WINNER."""
        gate = _make_gate()
        market = _make_market(yes_price=0.70)
        estimate = _make_estimate(ai_prob=0.30, confidence="A")
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.35, method="shrunk_no_bookmaker")
            candidates = gate._evaluate_candidates(
                [market], {market.condition_id: estimate},
                bankroll=1000.0, cycle_count=1, fresh_scan=True,
            )
        assert len(candidates) == 1
        assert candidates[0]["mode"] == "WINNER"
        from src.models import Direction
        assert candidates[0]["direction"] == Direction.BUY_NO


class TestBoundaries:
    """Test exact boundary values for mode classification."""

    def test_boundary_55_skips_deadzone(self):
        """Exactly 55% now SKIPs (deadzone disabled)."""
        gate = _make_gate()
        market = _make_market(yes_price=0.60)
        estimate = _make_estimate(ai_prob=0.55, confidence="B+")
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.55, method="shrunk_no_bookmaker")
            candidates = gate._evaluate_candidates(
                [market], {market.condition_id: estimate},
                bankroll=1000.0, cycle_count=1, fresh_scan=True,
            )
        assert len(candidates) == 0  # Deadzone disabled

    def test_boundary_54_skips(self):
        """54% should SKIP (below 55% threshold)."""
        gate = _make_gate()
        market = _make_market(yes_price=0.60)
        estimate = _make_estimate(ai_prob=0.54, confidence="A")
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.54, method="shrunk_no_bookmaker")
            candidates = gate._evaluate_candidates(
                [market], {market.condition_id: estimate},
                bankroll=1000.0, cycle_count=1, fresh_scan=True,
            )
        assert len(candidates) == 0

    def test_boundary_65_enters_winner(self):
        """Exactly 65% should enter WINNER mode."""
        gate = _make_gate()
        market = _make_market(yes_price=0.70)
        estimate = _make_estimate(ai_prob=0.65, confidence="B+")
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            mock_anchor.return_value = MagicMock(probability=0.65, method="shrunk_no_bookmaker")
            candidates = gate._evaluate_candidates(
                [market], {market.condition_id: estimate},
                bankroll=1000.0, cycle_count=1, fresh_scan=True,
            )
        assert len(candidates) == 1
        assert candidates[0]["mode"] == "WINNER"

    def test_ranking_only_winners(self):
        """Only WINNER candidates survive — deadzone is filtered out."""
        gate = _make_gate()
        m1 = _make_market(yes_price=0.70, cid="win-1", slug="winner")
        est1 = _make_estimate(ai_prob=0.95, confidence="B+")
        m2 = _make_market(yes_price=0.55, cid="dz-1", slug="deadzone")
        est2 = _make_estimate(ai_prob=0.58, confidence="B+")
        estimates = {"win-1": est1, "dz-1": est2}
        with patch("src.probability_engine.calculate_anchored_probability") as mock_anchor:
            def anchor(ai_prob, **kw):
                return MagicMock(probability=ai_prob, method="shrunk_no_bookmaker")
            mock_anchor.side_effect = anchor
            candidates = gate._evaluate_candidates(
                [m1, m2], estimates,
                bankroll=1000.0, cycle_count=1, fresh_scan=True,
            )
        assert len(candidates) == 1  # Only winner survives
        assert candidates[0]["market"].condition_id == "win-1"
