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
