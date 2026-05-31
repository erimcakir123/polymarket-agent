"""Kelly criterion sizing — saf math testleri."""
from src.domain.pricing.kelly import bet_size, kelly_fraction


def test_kelly_zero_when_no_edge():
    # p == price → no edge → 0
    assert kelly_fraction(p=0.50, price=0.50) == 0.0


def test_kelly_zero_when_negative_edge():
    assert kelly_fraction(p=0.40, price=0.50) == 0.0


def test_kelly_positive_when_edge():
    # p=0.60, price=0.50 → Kelly = (0.60-0.50)/(1-0.50) = 0.20
    assert abs(kelly_fraction(p=0.60, price=0.50) - 0.20) < 1e-6


def test_kelly_deep_underdog_value():
    # p=0.30, price=0.10 → Kelly = (0.30-0.10)/0.90 = 0.222
    assert abs(kelly_fraction(p=0.30, price=0.10) - 0.20 / 0.90) < 1e-6


def test_bet_size_zero_when_no_edge():
    assert bet_size(p=0.40, price=0.50, bankroll=1000.0,
                    kelly_multiplier=0.25, max_pct=0.05) == 0.0


def test_bet_size_uses_multiplier():
    # Kelly 0.20, multiplier 0.25 → 0.05 fraction of 1000 = 50
    s = bet_size(p=0.60, price=0.50, bankroll=1000.0,
                 kelly_multiplier=0.25, max_pct=0.10)
    assert abs(s - 50.0) < 1e-6


def test_bet_size_caps_at_max_pct():
    # Large edge would prescribe big size but max_pct caps
    s = bet_size(p=0.90, price=0.10, bankroll=1000.0,
                 kelly_multiplier=1.0, max_pct=0.05)
    assert s == 50.0  # 5% cap


def test_bet_size_zero_bankroll():
    assert bet_size(p=0.70, price=0.50, bankroll=0.0,
                    kelly_multiplier=0.25, max_pct=0.05) == 0.0


def test_bet_size_extreme_price():
    # price ~ 1.0 → 1-price ~ 0 → division guard
    s = bet_size(p=0.99, price=0.99, bankroll=1000.0,
                 kelly_multiplier=0.25, max_pct=0.05)
    assert s == 0.0
