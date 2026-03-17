import pytest


def test_buy_yes_when_ai_higher():
    from src.edge_calculator import calculate_edge
    from src.models import Direction
    direction, edge = calculate_edge(0.72, 0.60, min_edge=0.06, confidence="medium")
    assert direction == Direction.BUY_YES
    assert edge == pytest.approx(0.12)


def test_buy_no_when_ai_lower():
    from src.edge_calculator import calculate_edge
    from src.models import Direction
    direction, edge = calculate_edge(0.30, 0.55, min_edge=0.06, confidence="medium")
    assert direction == Direction.BUY_NO
    assert edge == pytest.approx(0.25)


def test_hold_when_no_edge():
    from src.edge_calculator import calculate_edge
    from src.models import Direction
    direction, edge = calculate_edge(0.52, 0.50, min_edge=0.06, confidence="medium")
    assert direction == Direction.HOLD


def test_high_confidence_lower_threshold():
    from src.edge_calculator import calculate_edge
    from src.models import Direction
    direction, _ = calculate_edge(0.55, 0.50, min_edge=0.06, confidence="high")
    assert direction == Direction.BUY_YES


def test_low_confidence_higher_threshold():
    from src.edge_calculator import calculate_edge
    from src.models import Direction
    direction, _ = calculate_edge(0.57, 0.50, min_edge=0.06, confidence="low")
    assert direction == Direction.HOLD


def test_whale_signal_blending():
    from src.edge_calculator import calculate_edge_with_whale
    from src.models import Direction
    direction, edge = calculate_edge_with_whale(
        ai_prob=0.60, market_price=0.50, min_edge=0.06,
        confidence="medium", whale_prob=0.70, whale_weight=0.15
    )
    assert direction == Direction.BUY_YES
    assert edge == pytest.approx(0.115)
