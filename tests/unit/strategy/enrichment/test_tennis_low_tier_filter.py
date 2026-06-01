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
