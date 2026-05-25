"""Distance-based scale-out: tier fires when (current-entry)/(1-entry) >= threshold."""
from src.strategy.exit.scale_out import check_scale_out
from src.config.settings import ScaleOutTier


def _tiers() -> list[ScaleOutTier]:
    return [
        ScaleOutTier(threshold=0.40, sell_pct=0.40),
        ScaleOutTier(threshold=0.70, sell_pct=0.50),
    ]


def test_tier1_fires_when_progress_hits_40pct() -> None:
    # entry=0.20, current=0.52 -> progress = (0.52-0.20)/(1-0.20) = 0.40 exact
    d = check_scale_out(scale_out_tier=0, entry_price=0.20, current_price=0.52, tiers=_tiers())
    assert d is not None
    assert d.tier == 1
    assert d.sell_pct == 0.40


def test_tier1_does_not_fire_below_threshold() -> None:
    # entry=0.20, current=0.50 -> progress = 0.375
    d = check_scale_out(scale_out_tier=0, entry_price=0.20, current_price=0.50, tiers=_tiers())
    assert d is None


def test_tier2_fires_when_progress_hits_70pct() -> None:
    # entry=0.20, current=0.76 -> progress = (0.76-0.20)/0.80 = 0.70
    d = check_scale_out(scale_out_tier=1, entry_price=0.20, current_price=0.76, tiers=_tiers())
    assert d is not None
    assert d.tier == 2
    assert d.sell_pct == 0.50


def test_tier2_does_not_fire_when_only_tier1_passed() -> None:
    # progress=0.50 > tier1 but tier2 needs 0.70
    d = check_scale_out(scale_out_tier=1, entry_price=0.20, current_price=0.60, tiers=_tiers())
    assert d is None


def test_no_decision_when_all_tiers_fired() -> None:
    d = check_scale_out(scale_out_tier=2, entry_price=0.20, current_price=0.95, tiers=_tiers())
    assert d is None


def test_high_entry_tier1_fires_at_appropriate_price() -> None:
    # entry=0.80, threshold 0.40 -> trigger = 0.80 + 0.20*0.40 = 0.88
    d = check_scale_out(scale_out_tier=0, entry_price=0.80, current_price=0.88, tiers=_tiers())
    assert d is not None
    assert d.tier == 1


def test_low_entry_tier1_fires_at_appropriate_price() -> None:
    # entry=0.19, threshold 0.40 -> trigger = 0.19 + 0.81*0.40 = 0.514
    d = check_scale_out(scale_out_tier=0, entry_price=0.19, current_price=0.515, tiers=_tiers())
    assert d is not None
    assert d.tier == 1


def test_zero_distance_edge_case_entry_at_one() -> None:
    # Defensive divide-by-zero guard
    d = check_scale_out(scale_out_tier=0, entry_price=1.0, current_price=1.0, tiers=_tiers())
    assert d is None
