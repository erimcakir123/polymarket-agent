"""Tennis tournament tier + surface resolver tests."""
from __future__ import annotations

import pytest

from src.domain.matching.tennis_tournament_resolver import (
    TournamentInfo,
    resolve_tournament,
)


_TOURNAMENTS = {
    "grand_slam": {
        "australian_open": "hard",
        "french_open": "clay",
        "wimbledon": "grass",
        "us_open": "hard",
    },
    "masters_1000": {
        "madrid_open": "clay",
        "miami_open": "hard",
    },
    "atp_500": {},
    "atp_250": {},
}
_EXCLUDED = ["itf", "challenger", "futures"]


def test_resolve_grand_slam_clay() -> None:
    info = resolve_tournament("atp-french-open-2026-06-01", _TOURNAMENTS, _EXCLUDED)
    assert info == TournamentInfo(tier="grand_slam", surface="clay", format="BO5")


def test_resolve_masters_1000_madrid() -> None:
    info = resolve_tournament("atp-madrid-open-2026-04-28", _TOURNAMENTS, _EXCLUDED)
    assert info == TournamentInfo(tier="masters_1000", surface="clay", format="BO3")


def test_resolve_wta_french_open_bo3() -> None:
    info = resolve_tournament("wta-french-open-2026-06-01", _TOURNAMENTS, _EXCLUDED)
    # WTA Grand Slam still BO3
    assert info == TournamentInfo(tier="grand_slam", surface="clay", format="BO3")


def test_resolve_excluded_tier_returns_none() -> None:
    info = resolve_tournament("atp-challenger-cary-2026-04-28", _TOURNAMENTS, _EXCLUDED)
    assert info is None


def test_resolve_unknown_tournament_returns_none() -> None:
    info = resolve_tournament("atp-unknown-tournament-2026-04-28", _TOURNAMENTS, _EXCLUDED)
    assert info is None


def test_resolve_invalid_slug_returns_none() -> None:
    info = resolve_tournament("not-a-tennis-slug", _TOURNAMENTS, _EXCLUDED)
    assert info is None


def test_resolve_from_question_madrid_open() -> None:
    """Real Polymarket H2H slug with tournament in question text."""
    info = resolve_tournament(
        slug="atp-fils-lehecka-2026-04-29",
        tournaments=_TOURNAMENTS,
        excluded_tiers=_EXCLUDED,
        question="Madrid Open: Arthur Fils vs Jiri Lehecka",
    )
    assert info == TournamentInfo(tier="masters_1000", surface="clay", format="BO3")


def test_resolve_from_question_french_open_atp_bo5() -> None:
    """Grand Slam ATP -> BO5."""
    info = resolve_tournament(
        slug="atp-medvedev-cobolli-2026-06-01",
        tournaments=_TOURNAMENTS,
        excluded_tiers=_EXCLUDED,
        question="French Open: Daniil Medvedev vs Flavio Cobolli",
    )
    assert info == TournamentInfo(tier="grand_slam", surface="clay", format="BO5")


def test_resolve_from_question_french_open_wta_bo3() -> None:
    """Grand Slam WTA -> BO3."""
    info = resolve_tournament(
        slug="wta-swiatek-gauff-2026-06-01",
        tournaments=_TOURNAMENTS,
        excluded_tiers=_EXCLUDED,
        question="French Open: Iga Swiatek vs Coco Gauff",
    )
    assert info == TournamentInfo(tier="grand_slam", surface="clay", format="BO3")


def test_resolve_question_takes_precedence_over_slug() -> None:
    """If both slug and question contain tournament info, both should agree (use either)."""
    info = resolve_tournament(
        slug="atp-madrid-open-fils-lehecka-2026-04-29",
        tournaments=_TOURNAMENTS,
        excluded_tiers=_EXCLUDED,
        question="Madrid Open: Arthur Fils vs Jiri Lehecka",
    )
    assert info == TournamentInfo(tier="masters_1000", surface="clay", format="BO3")


def test_resolve_question_none_returns_none_when_slug_lacks_tournament() -> None:
    """Sub-market with no tournament info anywhere -> None."""
    info = resolve_tournament(
        slug="atp-fils-lehecka-2026-04-29-set-handicap-home-1pt5",
        tournaments=_TOURNAMENTS,
        excluded_tiers=_EXCLUDED,
        question="Set Handicap: Fils (-1.5) vs Lehecka (+1.5)",
    )
    assert info is None
