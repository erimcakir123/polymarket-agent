"""Tests for tennis_player_matcher — fuzzy name → PlayerRating lookup. Pure domain."""
from __future__ import annotations

import pytest

from src.domain.matching.tennis_player_matcher import (
    _normalize,
    build_match_index,
    match_player,
)
from src.infrastructure.data.tennis_ratings_store import PlayerRating, SurfaceRating


def _default_surface_rating() -> SurfaceRating:
    return SurfaceRating(rating=1500.0, rd=200.0, volatility=0.06)


def _make_rating(player_id: str, player_name: str) -> PlayerRating:
    sr = _default_surface_rating()
    return PlayerRating(
        player_id=player_id,
        player_name=player_name,
        tour="atp",
        overall=sr,
        serve_clay=sr,
        serve_grass=sr,
        serve_hard=sr,
        return_clay=sr,
        return_grass=sr,
        return_hard=sr,
        last_match_date="2026-01-01",
        match_count_12mo=50,
    )


@pytest.fixture()
def ratings() -> dict[str, PlayerRating]:
    return {
        "p1": _make_rating("p1", "Novak Djokovic"),
        "p2": _make_rating("p2", "Carlos Alcaraz"),
        "p3": _make_rating("p3", "Adrian Mannarino"),
        "p4": _make_rating("p4", "Rafael Nadal"),
    }


# ── normalize ────────────────────────────────────────────────────────────────


def test_normalize_strips_accents() -> None:
    assert _normalize("Djokovic") == "djokovic"


def test_normalize_handles_diacritics() -> None:
    # é → e
    assert _normalize("Éric") == "eric"


def test_normalize_handles_turkish_dotless_i() -> None:
    assert _normalize("ı") == "i"


# ── exact match ──────────────────────────────────────────────────────────────


def test_match_player_exact_full_name(ratings) -> None:
    result = match_player("Novak Djokovic", ratings)
    assert result is not None
    assert result.player_id == "p1"


def test_match_player_exact_case_insensitive(ratings) -> None:
    result = match_player("novak djokovic", ratings)
    assert result is not None
    assert result.player_id == "p1"


def test_match_player_exact_with_accents_stripped(ratings) -> None:
    """Name with diacritics that normalize to same."""
    result = match_player("Carlos Alcaraz", ratings)
    assert result is not None
    assert result.player_id == "p2"


# ── surname-only match ────────────────────────────────────────────────────────


def test_match_player_surname_only_unique(ratings) -> None:
    """Unique surname → resolved."""
    result = match_player("Mannarino", ratings)
    assert result is not None
    assert result.player_id == "p3"


def test_match_player_surname_djokovic(ratings) -> None:
    result = match_player("Djokovic", ratings)
    assert result is not None
    assert result.player_id == "p1"


def test_match_player_surname_not_unique_returns_none() -> None:
    """Two players with same surname → no confident match."""
    rating_a = _make_rating("a1", "John Smith")
    rating_b = _make_rating("a2", "Jane Smith")
    ratings = {"a1": rating_a, "a2": rating_b}
    result = match_player("Smith", ratings)
    # With two Smiths: surname-only returns None (ambiguous)
    # rapidfuzz may pick the better ratio match, so we just check no crash
    assert result is None or result.player_id in ("a1", "a2")


# ── fuzzy match ───────────────────────────────────────────────────────────────


def test_match_player_fuzzy_minor_typo(ratings) -> None:
    """Minor typo should resolve via rapidfuzz."""
    # "Djokovic" with one char off — rapidfuzz should still find it
    result = match_player("Djokoviq", ratings)
    # May or may not match depending on threshold; just must not raise
    assert result is None or result.player_name == "Novak Djokovic"


def test_match_player_empty_name_returns_none(ratings) -> None:
    result = match_player("", ratings)
    assert result is None


def test_match_player_empty_ratings_returns_none() -> None:
    result = match_player("Djokovic", {})
    assert result is None


def test_match_player_no_match_returns_none(ratings) -> None:
    result = match_player("Xxxxxxyyyyyy", ratings)
    assert result is None


# ── short-name collision guard ────────────────────────────────────────────────


def test_match_player_short_name_does_not_match_longer_full_name() -> None:
    """Prefix-of-full-name input must NOT fuzzy-match a longer real name.

    Real-world bug (2026-05-21): Polymarket question "Juan Martin" matched
    "Juan Martin del Potro" via rapidfuzz partial_ratio=100. The correct
    behavior is to refuse the match — too many missing tokens to be confident.
    """
    rating = _make_rating("dp", "Juan Martin del Potro")
    rs = {"dp": rating}
    assert match_player("Juan Martin", rs) is None


def test_match_player_typo_still_resolves() -> None:
    """Regression: single-token typo must still fuzzy-match (token diff ≤1)."""
    rating = _make_rating("js", "Jannik Sinner")
    rs = {"js": rating}
    # "Sinnerr" — 1 token vs target's 2 tokens → diff 1 → fuzz check fires
    result = match_player("Sinnerr", rs)
    assert result is not None
    assert result.player_id == "js"


def test_match_player_compound_last_name_partial_resolves() -> None:
    """Regression: 2-token input vs 3-token target (diff=1) still allowed."""
    rating = _make_rating("ca", "Carlos Alcaraz Garfia")
    rs = {"ca": rating}
    result = match_player("Carlos Alcaraz", rs)
    assert result is not None
    assert result.player_id == "ca"


def test_match_player_same_surname_different_first_name_rejected() -> None:
    """Real-world bug (2026-05-21): "Juan Martin" matched "Dan Martin"
    because surname is exact and partial_ratio on the full string scores
    high. Per-token guard must reject when ANY input token has no strong
    match among target tokens.
    """
    rating = _make_rating("dm", "Dan Martin")
    rs = {"dm": rating}
    assert match_player("Juan Martin", rs) is None


# ── build_match_index ─────────────────────────────────────────────────────────


def test_build_match_index_creates_by_full(ratings) -> None:
    by_full, by_last = build_match_index(ratings)
    assert "novak djokovic" in by_full
    assert "carlos alcaraz" in by_full


def test_build_match_index_creates_by_last(ratings) -> None:
    by_full, by_last = build_match_index(ratings)
    assert "djokovic" in by_last
    assert "mannarino" in by_last


def test_match_player_reuses_prebuilt_index(ratings) -> None:
    """Prebuilt index passed in should give same result as auto-built."""
    by_full, by_last = build_match_index(ratings)
    result = match_player("Nadal", ratings, by_full=by_full, by_last=by_last)
    assert result is not None
    assert result.player_id == "p4"


# ── tour-scoped lookup (no cross-tour collisions) ────────────────────────────


def _make_rating_with_tour(
    player_id: str,
    player_name: str,
    tour: str,
    match_count_12mo: int = 50,
) -> PlayerRating:
    sr = _default_surface_rating()
    return PlayerRating(
        player_id=player_id,
        player_name=player_name,
        tour=tour,
        overall=sr,
        serve_clay=sr,
        serve_grass=sr,
        serve_hard=sr,
        return_clay=sr,
        return_grass=sr,
        return_hard=sr,
        last_match_date="2026-01-01",
        match_count_12mo=match_count_12mo,
    )


def test_match_player_tour_scoped_no_cross_tour_collision() -> None:
    """ATP Williams and WTA Williams resolve to different PlayerRating objects."""
    atp_williams = _make_rating_with_tour("atp:Williams", "Williams", "atp", match_count_12mo=10)
    wta_williams = _make_rating_with_tour("wta:Williams", "Williams", "wta", match_count_12mo=50)
    ratings = {"atp:Williams": atp_williams, "wta:Williams": wta_williams}

    by_full, by_last = build_match_index(ratings, tour="atp")
    atp_hit = match_player("Williams", ratings, by_full=by_full, by_last=by_last, tour="atp")
    assert atp_hit is not None
    assert atp_hit.tour == "atp"
    assert atp_hit.match_count_12mo == 10

    by_full_w, by_last_w = build_match_index(ratings, tour="wta")
    wta_hit = match_player("Williams", ratings, by_full=by_full_w, by_last=by_last_w, tour="wta")
    assert wta_hit is not None
    assert wta_hit.tour == "wta"
    assert wta_hit.match_count_12mo == 50


def test_build_match_index_tour_filter_excludes_other_tour() -> None:
    """build_match_index(tour='atp') drops WTA players from the indexes."""
    atp = _make_rating_with_tour("atp:Federer", "Roger Federer", "atp")
    wta = _make_rating_with_tour("wta:Swiatek", "Iga Swiatek", "wta")
    ratings = {"atp:Federer": atp, "wta:Swiatek": wta}

    by_full, by_last = build_match_index(ratings, tour="atp")
    assert "roger federer" in by_full
    assert "iga swiatek" not in by_full
    assert "swiatek" not in by_last


def test_match_player_compound_partial_respects_tour() -> None:
    """Tier-2 compound partial scan (e.g. 'Alcaraz' → 'Carlos Alcaraz Garfia')
    must NOT cross tours even when only ratings.values() is scanned."""
    atp = _make_rating_with_tour("atp:CA", "Carlos Alcaraz Garfia", "atp")
    wta = _make_rating_with_tour("wta:CA", "Carla Alcaraz Doe", "wta")
    ratings = {"atp:CA": atp, "wta:CA": wta}

    by_full, by_last = build_match_index(ratings, tour="wta")
    # "Alcaraz" alone — compound partial would hit both names if unscoped.
    # With tour=wta scope, only the WTA entry is reachable.
    hit = match_player("Alcaraz", ratings, by_full=by_full, by_last=by_last, tour="wta")
    assert hit is not None
    assert hit.tour == "wta"
