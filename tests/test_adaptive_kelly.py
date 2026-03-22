import pytest


class TestAdaptiveKelly:
    def test_high_confidence_base(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        frac = get_adaptive_kelly_fraction("high", 0.70, "esports",
                                            config_kelly_by_conf={"high": 0.25, "medium_high": 0.20, "medium_low": 0.12, "low": 0.08})
        # high=0.25 * esports_discount=0.90 = 0.225
        assert 0.20 <= frac <= 0.25

    def test_strong_ai_bonus(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        frac = get_adaptive_kelly_fraction("high", 0.85, "sports",
                                            config_kelly_by_conf={"high": 0.25})
        # 0.25 + 0.05 (AI>0.80) = 0.30
        assert frac == 0.30

    def test_reentry_discount(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        frac = get_adaptive_kelly_fraction("medium_high", 0.70, "esports", is_reentry=True,
                                            config_kelly_by_conf={"medium_high": 0.20})
        # 0.20 * 0.90 (esports) * 0.80 (re-entry) = 0.144
        assert 0.13 <= frac <= 0.16

    def test_low_confidence_floor(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        frac = get_adaptive_kelly_fraction("low", 0.55, "esports", is_reentry=True,
                                            config_kelly_by_conf={"low": 0.08})
        # 0.08 * 0.90 (esports) * 0.80 (re-entry) = 0.0576, above 0.05 floor
        assert abs(frac - 0.058) < 0.005

    def test_missing_confidence_uses_default(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        frac = get_adaptive_kelly_fraction("unknown", 0.65, "sports",
                                            config_kelly_by_conf={"high": 0.25})
        # Fallback 0.15
        assert frac == 0.15
