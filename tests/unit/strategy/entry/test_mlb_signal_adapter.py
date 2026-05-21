"""Tests for mlb_signal_adapter — EdgeCandidate → Signal (SPEC-R Plan 4 T1)."""
import pytest
from unittest.mock import MagicMock

from src.domain.mlb_submarket.edge_candidate import EdgeCandidate
from src.models.enums import Direction, EntryReason
from src.strategy.entry.mlb_signal_adapter import mlb_candidate_to_signal


def _market(cid: str = "cid-mlb", event_id: str = "evt-mlb"):
    m = MagicMock()
    m.condition_id = cid
    m.event_id = event_id
    return m


def _fixed_bet() -> dict[str, float]:
    return {"A": 50.0, "B": 30.0}


def test_positive_edge_buy_yes() -> None:
    ec = EdgeCandidate(model_p=0.62, market_p=0.55, edge=0.07,
                       market_type="totals", line=8.5)
    sig = mlb_candidate_to_signal(ec, _market(), tier="A", fixed_bet_usdc=_fixed_bet())
    assert sig.direction == Direction.BUY_YES


def test_negative_edge_buy_no() -> None:
    ec = EdgeCandidate(model_p=0.40, market_p=0.55, edge=-0.15,
                       market_type="totals", line=8.5)
    sig = mlb_candidate_to_signal(ec, _market(), tier="A", fixed_bet_usdc=_fixed_bet())
    assert sig.direction == Direction.BUY_NO


def test_anchor_probability_is_model_p_unchanged() -> None:
    ec = EdgeCandidate(model_p=0.62, market_p=0.55, edge=0.07,
                       market_type="totals", line=8.5)
    sig = mlb_candidate_to_signal(ec, _market(), tier="A", fixed_bet_usdc=_fixed_bet())
    assert sig.anchor_probability == 0.62  # P(YES) preserved


def test_entry_reason_is_mlb_submarket() -> None:
    ec = EdgeCandidate(model_p=0.55, market_p=0.50, edge=0.05,
                       market_type="totals", line=8.5)
    sig = mlb_candidate_to_signal(ec, _market(), tier="B", fixed_bet_usdc=_fixed_bet())
    assert sig.entry_reason == EntryReason.MLB_SUBMARKET


def test_bookmaker_fields_zeroed() -> None:
    ec = EdgeCandidate(model_p=0.55, market_p=0.50, edge=0.05,
                       market_type="totals", line=8.5)
    sig = mlb_candidate_to_signal(ec, _market(), tier="A", fixed_bet_usdc=_fixed_bet())
    assert sig.bookmaker_prob == 0.0
    assert sig.num_bookmakers == 0
    assert sig.has_sharp is False


def test_sport_tag_baseball_mlb() -> None:
    ec = EdgeCandidate(model_p=0.55, market_p=0.50, edge=0.05,
                       market_type="totals", line=8.5)
    sig = mlb_candidate_to_signal(ec, _market(), tier="A", fixed_bet_usdc=_fixed_bet())
    assert sig.sport_tag == "baseball_mlb"


def test_size_a_tier_50() -> None:
    ec = EdgeCandidate(model_p=0.55, market_p=0.50, edge=0.05,
                       market_type="totals", line=8.5)
    sig = mlb_candidate_to_signal(ec, _market(), tier="A", fixed_bet_usdc=_fixed_bet())
    assert sig.size_usdc == 50.0


def test_size_b_tier_30() -> None:
    ec = EdgeCandidate(model_p=0.55, market_p=0.50, edge=0.05,
                       market_type="totals", line=8.5)
    sig = mlb_candidate_to_signal(ec, _market(), tier="B", fixed_bet_usdc=_fixed_bet())
    assert sig.size_usdc == 30.0
