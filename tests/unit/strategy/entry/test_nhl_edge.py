"""Tests for src/strategy/entry/_nhl_edge.py — standalone, no gate.run() pipeline."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.strategy.entry._nhl_edge import apply_nhl_edge_modifiers


# ── helpers ──────────────────────────────────────────────────────


def _cfg(**overrides):
    base = dict(
        nhl_b2b_opponent_gap_bonus=0.02,
        nhl_b2b_opponent_size_mult=1.10,
        nhl_b2b_self_gap_bonus=0.02,
        nhl_require_goalie_confirmation=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _market(question="Bruins vs. Sabres"):
    return SimpleNamespace(question=question, sport_tag="nhl")


def _ctx(opp_b2b=False, our_b2b=False):
    return SimpleNamespace(
        is_opponent_back_to_back=opp_b2b,
        is_our_back_to_back=our_b2b,
    )


# ── tests ─────────────────────────────────────────────────────────


class TestApplyNhlEdgeModifiers:
    def test_no_enricher_returns_neutral(self):
        gap, size = apply_nhl_edge_modifiers(_market(), None, _cfg())
        assert gap == 0.0
        assert size == 1.0

    def test_unparseable_question_returns_neutral(self):
        enricher = MagicMock()
        gap, size = apply_nhl_edge_modifiers(
            _market(question="random text no teams"),
            enricher,
            _cfg(),
        )
        assert gap == 0.0
        assert size == 1.0
        enricher.enrich.assert_not_called()

    def test_unknown_team_returns_neutral(self):
        enricher = MagicMock()
        gap, size = apply_nhl_edge_modifiers(
            _market(question="ZZZ vs YYY"),
            enricher,
            _cfg(),
        )
        assert gap == 0.0
        assert size == 1.0

    def test_enricher_exception_returns_neutral(self):
        enricher = MagicMock()
        enricher.enrich.side_effect = RuntimeError("API down")
        gap, size = apply_nhl_edge_modifiers(_market(), enricher, _cfg())
        assert gap == 0.0
        assert size == 1.0

    def test_opponent_b2b_lowers_gap_and_raises_size(self):
        enricher = MagicMock()
        enricher.enrich.return_value = _ctx(opp_b2b=True)
        gap, size = apply_nhl_edge_modifiers(_market(), enricher, _cfg())
        assert gap == -0.02
        assert size == 1.10

    def test_our_b2b_raises_gap(self):
        enricher = MagicMock()
        enricher.enrich.return_value = _ctx(our_b2b=True)
        gap, size = apply_nhl_edge_modifiers(_market(), enricher, _cfg())
        assert gap == 0.02
        assert size == 1.0

    def test_both_b2b_combine(self):
        enricher = MagicMock()
        enricher.enrich.return_value = _ctx(opp_b2b=True, our_b2b=True)
        gap, size = apply_nhl_edge_modifiers(_market(), enricher, _cfg())
        assert gap == 0.0        # opp -0.02 + self +0.02 = net 0
        assert size == 1.10      # size only from opp

    def test_no_b2b_neutral(self):
        enricher = MagicMock()
        enricher.enrich.return_value = _ctx()
        gap, size = apply_nhl_edge_modifiers(_market(), enricher, _cfg())
        assert gap == 0.0
        assert size == 1.0

    def test_enricher_called_with_correct_args(self):
        enricher = MagicMock()
        enricher.enrich.return_value = _ctx()
        apply_nhl_edge_modifiers(
            _market(question="Bruins vs. Sabres"),
            enricher,
            _cfg(),
        )
        call = enricher.enrich.call_args
        assert call.kwargs["our_team_id"] == "1"    # BOS
        assert call.kwargs["opp_team_id"] == "2"    # BUF
        assert call.kwargs["probables_home"] is None
        assert call.kwargs["probables_away"] is None
        assert call.kwargs["we_are_home"] is True
