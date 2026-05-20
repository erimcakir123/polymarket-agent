"""sport_rules.py için tennis entry + alias birim testleri.

2026-05-20 (tennis-lab Faz tennis): Tennis paper bot canlandı; graduated_sl
elapsed_pct ve near_resolve guard'ları sport-spesifik değerler okumalı.
"""
from __future__ import annotations

from src.config.sport_rules import (
    SPORT_RULES,
    get_match_duration_hours,
    get_sport_rule,
    get_stop_loss,
)


def test_tennis_sport_rules_present() -> None:
    """SPORT_RULES dict'inde 'tennis' anahtarı bulunur."""
    assert "tennis" in SPORT_RULES


def test_tennis_alias_atp_normalizes_to_tennis() -> None:
    """Polymarket sport_tag 'tennis_atp' → tennis kuralına çözümlenir."""
    assert get_stop_loss("tennis_atp") == SPORT_RULES["tennis"]["stop_loss_pct"]


def test_tennis_alias_wta_normalizes_to_tennis() -> None:
    """Polymarket sport_tag 'tennis_wta' → tennis kuralına çözümlenir."""
    assert get_stop_loss("tennis_wta") == SPORT_RULES["tennis"]["stop_loss_pct"]


def test_tennis_alias_atp_finals_normalizes_to_tennis() -> None:
    """ATP Finals slug etiketi de tennis kuralına çözümlenir."""
    assert get_stop_loss("tennis_atp_finals") == SPORT_RULES["tennis"]["stop_loss_pct"]


def test_tennis_alias_wta_finals_normalizes_to_tennis() -> None:
    """WTA Finals slug etiketi de tennis kuralına çözümlenir."""
    assert get_stop_loss("tennis_wta_finals") == SPORT_RULES["tennis"]["stop_loss_pct"]


def test_tennis_match_duration_is_1_75h() -> None:
    """ATP/WTA BO3 ortalama maç süresi = 1.75 saat (graduated_sl elapsed_pct için)."""
    assert SPORT_RULES["tennis"]["match_duration_hours"] == 1.75


def test_get_match_duration_hours_returns_tennis_value_for_atp_tag() -> None:
    """Public helper'ı 'tennis_atp' tag'i için 1.75 döner (alias resolution)."""
    assert get_match_duration_hours("tennis_atp") == 1.75


def test_tennis_near_resolve_threshold_94c() -> None:
    """near_resolve_threshold_cents = 94 (price ≥ 94¢ → near-resolve guard)."""
    assert get_sport_rule("tennis", "near_resolve_threshold_cents") == 94


def test_tennis_stop_loss_pct_030() -> None:
    """Tennis stop_loss = 30% (BO3 volatilitesi)."""
    assert SPORT_RULES["tennis"]["stop_loss_pct"] == 0.30


def test_tennis_score_source_espn() -> None:
    """Score source = ESPN (tennis/atp)."""
    assert get_sport_rule("tennis_atp", "score_source") == "espn"
    assert get_sport_rule("tennis_atp", "espn_sport") == "tennis"
    assert get_sport_rule("tennis_atp", "espn_league") == "atp"
