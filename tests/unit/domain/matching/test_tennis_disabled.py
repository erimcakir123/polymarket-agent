"""Tennis YENİDEN AKTİF 2026-05-29 (Phase 3 follow-up) — resolver _match_tennis_key çağırır.

Eski dosya tennis dormant durumundayken erken-None testleri içeriyordu;
tennis ana bota geri alındığı için güncel davranışla değiştirildi.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.strategy.enrichment.sport_key_resolver import resolve_sport_key


def _odds_with_active_tennis_keys(*keys: str) -> MagicMock:
    odds = MagicMock()
    odds.get_sports.return_value = [
        {"key": k, "active": True} for k in keys
    ]
    return odds


def test_atp_slug_prefix_invokes_tennis_resolver() -> None:
    odds = _odds_with_active_tennis_keys("tennis_atp_french_open", "tennis_atp_munich")
    result = resolve_sport_key(
        question="Djokovic vs Federer at French Open",
        slug="atp-djoko-feder-2026-05-15",
        tags=[],
        odds_client=odds,
    )
    assert result == "tennis_atp_french_open"
    odds.get_sports.assert_called()


def test_wta_slug_prefix_invokes_tennis_resolver() -> None:
    odds = _odds_with_active_tennis_keys("tennis_wta_madrid", "tennis_wta_roland_garros")
    result = resolve_sport_key(
        question="Swiatek vs Sabalenka madrid open",
        slug="wta-swiatek-sabalenka-2026-05-15",
        tags=[],
        odds_client=odds,
    )
    assert result == "tennis_wta_madrid"


def test_tennis_question_text_invokes_resolver_when_no_active_tournaments() -> None:
    """Tennis kelimesi var ama aktif tennis key yoksa None (graceful)."""
    odds = MagicMock()
    odds.get_sports.return_value = []
    result = resolve_sport_key(
        question="ATP final",
        slug="some-other-slug-2026-05-15",
        tags=[],
        odds_client=odds,
    )
    assert result is None
    odds.get_sports.assert_called()
