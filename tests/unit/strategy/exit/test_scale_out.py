"""scale_out.py icin birim testler — midpoint semantigi (SPEC-013)."""
from __future__ import annotations

from src.strategy.exit.scale_out import ScaleOutDecision, check_scale_out


def test_midpoint_fires_at_half_distance_low_entry() -> None:
    """Entry 43c -> midpoint ~71c. 72c'te (> midpoint) trigger.

    Not: (0.71-0.43)/(0.99-0.43) = 0.4999... floating point nedenli 0.5'in altinda kalir.
    0.72 kullanilir: fraction = 0.517 >= 0.50 -> tetiklenir.
    """
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    r = check_scale_out(
        scale_out_tier=0,
        entry_price=0.43,
        current_price=0.72,
        tiers=tiers,
    )
    assert isinstance(r, ScaleOutDecision)
    assert r.tier == 1
    assert r.sell_pct == 0.40


def test_midpoint_not_yet_triggered() -> None:
    """Entry 43c, current 60c -> fraction (60-43)/56 = 0.30 < 0.50 -> None."""
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    r = check_scale_out(
        scale_out_tier=0,
        entry_price=0.43,
        current_price=0.60,
        tiers=tiers,
    )
    assert r is None


def test_higher_entry_midpoint() -> None:
    """Entry 70c -> midpoint = 70 + 0.5*(99-70) = 84.5c."""
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    r = check_scale_out(
        scale_out_tier=0,
        entry_price=0.70,
        current_price=0.845,
        tiers=tiers,
    )
    assert r is not None
    assert r.tier == 1


def test_price_below_entry_returns_none() -> None:
    """Kar yok -> scale-out yok."""
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    r = check_scale_out(
        scale_out_tier=0,
        entry_price=0.50,
        current_price=0.40,
        tiers=tiers,
    )
    assert r is None


def test_entry_equal_current_returns_none() -> None:
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    r = check_scale_out(
        scale_out_tier=0,
        entry_price=0.50,
        current_price=0.50,
        tiers=tiers,
    )
    assert r is None


def test_entry_at_resolution_returns_none() -> None:
    """Entry 0.99+ -> near-resolve zaten, scale-out anlamsiz."""
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    r = check_scale_out(
        scale_out_tier=0,
        entry_price=0.99,
        current_price=0.99,
        tiers=tiers,
    )
    assert r is None


def test_beyond_max_tier_returns_none() -> None:
    """Tier 1 gecildi + tek tier var -> None."""
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    r = check_scale_out(
        scale_out_tier=1,  # zaten gecildi
        entry_price=0.50,
        current_price=0.99,
        tiers=tiers,
    )
    assert r is None


def test_empty_tiers_returns_none() -> None:
    r = check_scale_out(
        scale_out_tier=0,
        entry_price=0.50,
        current_price=0.80,
        tiers=[],
    )
    assert r is None


def test_multi_tier_progression() -> None:
    """Fonksiyon N-tier: caller coklu tier verirse sirayla ilerler."""
    multi = [
        {"threshold": 0.30, "sell_pct": 0.30},
        {"threshold": 0.60, "sell_pct": 0.50},
    ]
    # Entry 0.50, current 0.80 -> fraction = (0.80-0.50)/(0.99-0.50) = 0.612
    r1 = check_scale_out(scale_out_tier=0, entry_price=0.50, current_price=0.80, tiers=multi)
    assert r1 is not None and r1.tier == 1  # tier 1 once tetiklenir

    r2 = check_scale_out(scale_out_tier=1, entry_price=0.50, current_price=0.80, tiers=multi)
    assert r2 is not None and r2.tier == 2


def test_buy_no_direction_works_transparently() -> None:
    """BUY_NO: caller effective prices verir (entry=no_price, current=no_price).
    Fonksiyon direction'a bakmaz, matematik adil."""
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    # BUY_NO entry 0.43 NO, current 0.72 NO -> fraction 0.517 >= 0.50 -> tetik
    r = check_scale_out(
        scale_out_tier=0,
        entry_price=0.43,
        current_price=0.72,
        tiers=tiers,
    )
    assert r is not None
