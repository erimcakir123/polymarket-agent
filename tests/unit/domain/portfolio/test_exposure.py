"""exposure.py için birim testler."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.portfolio.exposure import exceeds_exposure_limit, fill_ratio


@dataclass
class _FakePos:
    size_usdc: float


def test_exposure_under_limit() -> None:
    positions = {"a": _FakePos(100), "b": _FakePos(100)}
    # total_portfolio = 1000 (cash 800 + invested 200); (200+50)/1000 = 25%; cap 50% → OK
    assert exceeds_exposure_limit(positions, candidate_size=50,
                                  total_portfolio_value=1000, max_exposure_pct=0.50) is False


def test_exposure_over_limit() -> None:
    positions = {"a": _FakePos(300), "b": _FakePos(200)}
    # (500+100)/1000 = 60% > 50% → BLOCK
    assert exceeds_exposure_limit(positions, candidate_size=100,
                                  total_portfolio_value=1000, max_exposure_pct=0.50) is True


def test_exposure_exactly_at_limit() -> None:
    positions = {"a": _FakePos(500)}
    # (500+0)/1000 = 50% at limit; > fails → OK
    assert exceeds_exposure_limit(positions, candidate_size=0,
                                  total_portfolio_value=1000, max_exposure_pct=0.50) is False


def test_zero_portfolio_blocks() -> None:
    assert exceeds_exposure_limit({}, candidate_size=10,
                                  total_portfolio_value=0, max_exposure_pct=0.50) is True


def test_exposure_real_scenario_regression() -> None:
    """Regression: kullanıcının 2026-04-15 bug raporu.

    Bot $1000 bankroll ile 7 pozisyon ($340 invested) açmışken 8. pozisyon
    ($50) denendi. Önceki bug'lı formül (cash payda) 59% verip BLOCK ediyordu;
    doğru formül (toplam portföy payda) 39% verip izin verir.
    """
    positions = {f"p{i}": _FakePos(50) for i in range(7)}
    # 7 × 50 = 350 (kullanıcının $340 scenariosuna yakın)
    # total_portfolio_value = 1000 (bankroll+invested); (350+50)/1000 = 40% < 50% → OK
    assert exceeds_exposure_limit(positions, candidate_size=50,
                                  total_portfolio_value=1000, max_exposure_pct=0.50) is False


def test_fill_ratio_empty() -> None:
    assert fill_ratio({}, total_portfolio_value=1000) == 0.0


def test_fill_ratio_half() -> None:
    positions = {"a": _FakePos(250), "b": _FakePos(250)}
    assert fill_ratio(positions, total_portfolio_value=1000) == 0.5


def test_fill_ratio_zero_portfolio() -> None:
    assert fill_ratio({"a": _FakePos(100)}, total_portfolio_value=0) == 0.0
