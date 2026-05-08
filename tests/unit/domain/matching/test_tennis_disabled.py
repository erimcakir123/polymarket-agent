"""Tennis kapatıldı 2026-05-05 — resolver erken None döner (CPU/token israfı yok)."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.strategy.enrichment.sport_key_resolver import resolve_sport_key


def test_atp_slug_prefix_returns_none_no_odds_call() -> None:
    """Slug prefix 'atp' → None döner, odds_client.get_sports HİÇ çağrılmamalı."""
    odds = MagicMock()
    result = resolve_sport_key(
        question="Will Djokovic beat Federer?",
        slug="atp-djoko-feder-2026-05-15",
        tags=[],
        odds_client=odds,
    )
    assert result is None
    odds.get_sports.assert_not_called()


def test_wta_slug_prefix_returns_none_no_odds_call() -> None:
    """Slug prefix 'wta' → None döner, odds_client çağrılmaz."""
    odds = MagicMock()
    result = resolve_sport_key(
        question="Match prediction",
        slug="wta-swiatek-sabalenka-2026-05-15",
        tags=[],
        odds_client=odds,
    )
    assert result is None
    odds.get_sports.assert_not_called()


def test_tennis_question_text_returns_none() -> None:
    """Question'da 'tennis'/'atp'/'wta'/'women' → None, odds çağrılmaz."""
    odds = MagicMock()
    for q in ["ATP final", "WTA semifinal", "tennis match", "Women's draw"]:
        result = resolve_sport_key(
            question=q,
            slug="some-other-slug-2026-05-15",
            tags=[],
            odds_client=odds,
        )
        assert result is None, f"q={q!r} did not return None"
    odds.get_sports.assert_not_called()
