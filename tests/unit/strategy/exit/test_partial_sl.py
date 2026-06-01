"""Partial SL — loss-side tiered exit (scale-out simetriği)."""
from __future__ import annotations

from src.config.settings import PartialSlConfig, PartialSlTier
from src.strategy.exit.partial_sl import check_partial_sl


def _default_tiers() -> list[PartialSlTier]:
    return PartialSlConfig().tiers


def test_no_fire_when_in_profit():
    """+%5 kârda — partial SL tetik yok."""
    d = check_partial_sl(
        partial_sl_tier=0, unrealized_pnl_pct=0.05, tiers=_default_tiers(),
    )
    assert d is None


def test_no_fire_when_loss_below_tier1():
    """-%15 — tier 1 eşiği (-%20) altında, tetik yok."""
    d = check_partial_sl(
        partial_sl_tier=0, unrealized_pnl_pct=-0.15, tiers=_default_tiers(),
    )
    assert d is None


def test_tier1_fires_at_20pct_loss():
    """-%20 → tier 1 (%30 sat)."""
    d = check_partial_sl(
        partial_sl_tier=0, unrealized_pnl_pct=-0.20, tiers=_default_tiers(),
    )
    assert d is not None
    assert d.tier == 1
    assert d.sell_pct == 0.30


def test_tier1_fires_past_threshold():
    """-%25 (eşiği aşmış) → tier 1 hâlâ doğru."""
    d = check_partial_sl(
        partial_sl_tier=0, unrealized_pnl_pct=-0.25, tiers=_default_tiers(),
    )
    assert d is not None
    assert d.tier == 1


def test_tier2_fires_at_35pct_loss():
    """-%35 + tier1 zaten fire → tier 2 (%50 of remaining)."""
    d = check_partial_sl(
        partial_sl_tier=1, unrealized_pnl_pct=-0.35, tiers=_default_tiers(),
    )
    assert d is not None
    assert d.tier == 2
    assert d.sell_pct == 0.50


def test_tier2_not_fire_before_threshold():
    """-%30 + tier1 fired → tier 2 eşiği -%35, henüz değil."""
    d = check_partial_sl(
        partial_sl_tier=1, unrealized_pnl_pct=-0.30, tiers=_default_tiers(),
    )
    assert d is None


def test_tier3_fires_at_50pct_loss():
    """-%50 + tier1+2 fired → tier 3 (kalanı tamamen sat)."""
    d = check_partial_sl(
        partial_sl_tier=2, unrealized_pnl_pct=-0.50, tiers=_default_tiers(),
    )
    assert d is not None
    assert d.tier == 3
    assert d.sell_pct == 1.00


def test_all_tiers_fired_no_more():
    """3 tier hepsi fire ettiyse artık tetik yok (pozisyon kapanmış)."""
    d = check_partial_sl(
        partial_sl_tier=3, unrealized_pnl_pct=-0.80, tiers=_default_tiers(),
    )
    assert d is None


def test_custom_tiers_respected():
    """Config'den geçirilen özel tier'lar default'u override eder."""
    custom = [
        PartialSlTier(loss_threshold=0.10, sell_pct=0.20),
        PartialSlTier(loss_threshold=0.25, sell_pct=1.00),
    ]
    d = check_partial_sl(partial_sl_tier=0, unrealized_pnl_pct=-0.12, tiers=custom)
    assert d is not None
    assert d.tier == 1
    assert d.sell_pct == 0.20


def test_default_config_has_3_tiers():
    """Regression: default config 3 tier (20/35/50)."""
    cfg = PartialSlConfig()
    assert cfg.enabled is True
    assert len(cfg.tiers) == 3
    assert cfg.tiers[0].loss_threshold == 0.20
    assert cfg.tiers[1].loss_threshold == 0.35
    assert cfg.tiers[2].loss_threshold == 0.50
    assert cfg.tiers[2].sell_pct == 1.00
