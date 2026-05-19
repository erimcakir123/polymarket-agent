"""Tennis entry strategy — select best 2 edge per match."""
from __future__ import annotations

import pytest

from src.domain.prediction.tennis_predictor import MarketPrediction
from src.strategy.entry.tennis_entry import (
    EdgeCandidate,
    select_best_2_per_event,
)


def test_select_3_predictions_returns_top_2_by_edge():
    candidates = [
        EdgeCandidate(event_id="evt1", market_type="first_set_winner",
                      model_p=0.62, market_p=0.55, edge=0.07),
        EdgeCandidate(event_id="evt1", market_type="set_handicap",
                      model_p=0.40, market_p=0.30, edge=0.10),
        EdgeCandidate(event_id="evt1", market_type="total_sets",
                      model_p=0.50, market_p=0.48, edge=0.02),
    ]
    selected = select_best_2_per_event(candidates)
    assert len(selected) == 2
    # Top 2 by abs(edge): 0.10 + 0.07
    edges = [c.edge for c in selected]
    assert 0.10 in edges
    assert 0.07 in edges
    assert 0.02 not in edges


def test_select_handles_2_predictions_returns_both():
    candidates = [
        EdgeCandidate(event_id="evt1", market_type="first_set_winner",
                      model_p=0.62, market_p=0.55, edge=0.07),
        EdgeCandidate(event_id="evt1", market_type="set_handicap",
                      model_p=0.40, market_p=0.30, edge=0.10),
    ]
    selected = select_best_2_per_event(candidates)
    assert len(selected) == 2


def test_select_handles_multiple_events_independent():
    candidates = [
        EdgeCandidate(event_id="evt1", market_type="m1", model_p=0.6, market_p=0.5, edge=0.10),
        EdgeCandidate(event_id="evt1", market_type="m2", model_p=0.6, market_p=0.5, edge=0.05),
        EdgeCandidate(event_id="evt1", market_type="m3", model_p=0.6, market_p=0.5, edge=0.03),
        EdgeCandidate(event_id="evt2", market_type="m1", model_p=0.6, market_p=0.5, edge=0.20),
    ]
    selected = select_best_2_per_event(candidates)
    # evt1 keeps top 2 (0.10, 0.05); evt2 keeps its 1
    assert len(selected) == 3
    evt1 = [c for c in selected if c.event_id == "evt1"]
    assert len(evt1) == 2
    evt2 = [c for c in selected if c.event_id == "evt2"]
    assert len(evt2) == 1


def test_select_uses_abs_edge_for_negative():
    """Negative edge means BUY_NO direction; still ranked by magnitude."""
    candidates = [
        EdgeCandidate(event_id="evt1", market_type="m1", model_p=0.4, market_p=0.5, edge=-0.10),
        EdgeCandidate(event_id="evt1", market_type="m2", model_p=0.6, market_p=0.55, edge=0.05),
        EdgeCandidate(event_id="evt1", market_type="m3", model_p=0.6, market_p=0.58, edge=0.02),
    ]
    selected = select_best_2_per_event(candidates)
    edges = [c.edge for c in selected]
    assert -0.10 in edges  # biggest magnitude
    assert 0.05 in edges
    assert 0.02 not in edges
