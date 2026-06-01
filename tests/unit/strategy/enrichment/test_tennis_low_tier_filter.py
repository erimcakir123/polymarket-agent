"""Tennis low-tier slug filtresi — ITF/Challenger/Futures SKIP."""
from __future__ import annotations

from src.strategy.enrichment.tennis_dispatch import _is_low_tier_tennis


def test_itf_slug_prefix_blocked():
    assert _is_low_tier_tennis("itf-beraldo-luque-2026-06-01", "") is True


def test_challenger_slug_prefix_blocked():
    assert _is_low_tier_tennis("challenger-perugia-cecchin-simakin", "") is True


def test_atp_main_tour_passes():
    assert _is_low_tier_tennis("atp-tiafoe-arnaldi-2026-06-01", "") is False


def test_question_with_itf_keyword_blocked():
    """Slug 'wta-' olsa bile question'da ITF varsa block."""
    assert _is_low_tier_tennis(
        "wta-pier-bosio-2026-06-01",
        "Foggia ITF: Pieri vs Bosio",
    ) is True


def test_question_with_m15_keyword_blocked():
    assert _is_low_tier_tennis("atp-x-y", "M15 Heraklion: X vs Y") is True


def test_grand_slam_question_passes():
    assert _is_low_tier_tennis(
        "atp-djokovic-alcaraz", "Wimbledon: Djokovic vs Alcaraz",
    ) is False


def test_empty_inputs_pass():
    assert _is_low_tier_tennis("", "") is False


def test_custom_prefixes_override_defaults():
    """Config'den geçirilen prefix listesi default'ı override eder."""
    assert _is_low_tier_tennis(
        "uta-x-y-2026", "", slug_prefixes=("uta-",),
    ) is True
    # Default itf- artık yok, geçer
    assert _is_low_tier_tennis(
        "itf-a-b", "", slug_prefixes=("uta-",),
    ) is False


def test_custom_keywords_block_prostejov_challenger():
    """Config'den ek keyword: Prostejov (ATP Challenger, Krumich case)."""
    assert _is_low_tier_tennis(
        "atp-olivier-krumich-2026-06-01",
        "Prostejov: Olivier vs Krumich",
        question_keywords=("Prostejov",),
    ) is True


def test_default_prefixes_unchanged():
    """Regression: default prefix listesi değişmedi (geri uyumluluk)."""
    from src.strategy.enrichment.tennis_dispatch import (
        _DEFAULT_LOW_TIER_SLUG_PREFIXES,
        _DEFAULT_LOW_TIER_QUESTION_KEYWORDS,
    )
    assert "itf-" in _DEFAULT_LOW_TIER_SLUG_PREFIXES
    assert "challenger-" in _DEFAULT_LOW_TIER_SLUG_PREFIXES
    assert "futures-" in _DEFAULT_LOW_TIER_SLUG_PREFIXES
    assert "ITF" in _DEFAULT_LOW_TIER_QUESTION_KEYWORDS
    assert "Challenger" in _DEFAULT_LOW_TIER_QUESTION_KEYWORDS
