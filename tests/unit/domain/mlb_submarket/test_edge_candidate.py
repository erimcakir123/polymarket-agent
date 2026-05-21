import pytest
from src.domain.mlb_submarket.edge_candidate import EdgeCandidate


def test_edge_candidate_basic() -> None:
    ec = EdgeCandidate(model_p=0.62, market_p=0.55, edge=0.07, market_type="totals", line=8.5)
    assert ec.edge == 0.07


def test_edge_candidate_invalid_model_p() -> None:
    with pytest.raises(ValueError):
        EdgeCandidate(model_p=1.2, market_p=0.5, edge=0.1, market_type="totals", line=8.5)


def test_edge_candidate_invalid_market_type() -> None:
    with pytest.raises(ValueError):
        EdgeCandidate(model_p=0.5, market_p=0.5, edge=0.0, market_type="invalid", line=8.5)


def test_edge_candidate_frozen() -> None:
    ec = EdgeCandidate(model_p=0.6, market_p=0.5, edge=0.1, market_type="run_line", line=1.5)
    with pytest.raises(Exception):  # FrozenInstanceError
        ec.edge = 0.2  # type: ignore
