import pytest
from src.domain.mlb_submarket.rate_shrinker import shrink_beta, marcel_weight


def test_shrink_beta_basic() -> None:
    # observed 50/100, prior Beta(10, 10) (weak prior)
    # posterior = (10+50)/(10+10+100) = 60/120 = 0.5
    assert abs(shrink_beta(50, 100, 10, 10) - 0.5) < 1e-9


def test_shrink_beta_zero_observations() -> None:
    # n=0 → prior mean = alpha/(alpha+beta)
    assert abs(shrink_beta(0, 0, 10, 30) - 0.25) < 1e-9


def test_shrink_beta_invalid_x_gt_n() -> None:
    with pytest.raises(ValueError):
        shrink_beta(50, 30, 10, 10)


def test_marcel_weight_three_seasons() -> None:
    # Marcel 5/4/3 weighting
    # weighted = (5*0.10*100 + 4*0.08*80 + 3*0.06*60) / (5*100 + 4*80 + 3*60)
    # numerator = 50 + 25.6 + 10.8 = 86.4
    # denominator = 500 + 320 + 180 = 1000
    # expected = 0.0864
    result = marcel_weight([(0.10, 100), (0.08, 80), (0.06, 60)])
    assert abs(result - 0.0864) < 1e-9


def test_marcel_weight_extends_with_zeros() -> None:
    # Single season uses only first weight (5)
    # weighted = 5*0.10*100 / 5*100 = 0.10
    result = marcel_weight([(0.10, 100)])
    assert abs(result - 0.10) < 1e-9


def test_marcel_weight_too_many_seasons_raises() -> None:
    with pytest.raises(ValueError):
        marcel_weight([(0.1, 100)] * 4, weights=(5, 4, 3))
