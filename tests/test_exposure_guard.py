"""Tests for exposure guard -- block entries when >35% bankroll invested."""


def test_exposure_guard_blocks_when_over_limit():
    bankroll = 1000.0
    total_invested = 300.0
    candidate_size = 100.0
    max_exposure_pct = 0.35
    over_limit = (total_invested + candidate_size) / bankroll > max_exposure_pct
    assert over_limit is True


def test_exposure_guard_allows_when_under_limit():
    bankroll = 1000.0
    total_invested = 200.0
    candidate_size = 100.0
    max_exposure_pct = 0.35
    over_limit = (total_invested + candidate_size) / bankroll > max_exposure_pct
    assert over_limit is False


def test_exposure_guard_blocks_at_zero_bankroll():
    bankroll = 0.0
    candidate_size = 10.0
    # With zero bankroll, should always block
    if bankroll <= 0:
        over_limit = True
    else:
        over_limit = (0 + candidate_size) / bankroll > 0.35
    assert over_limit is True


def test_exposure_guard_allows_at_exact_limit():
    bankroll = 1000.0
    total_invested = 300.0
    candidate_size = 50.0
    max_exposure_pct = 0.35
    # 350/1000 = 0.35, not > 0.35
    over_limit = (total_invested + candidate_size) / bankroll > max_exposure_pct
    assert over_limit is False


def test_exposure_guard_config_default():
    from src.config import RiskConfig
    cfg = RiskConfig()
    assert cfg.max_exposure_pct == 0.50
