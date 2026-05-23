"""Tests for tennis_question_parser — question text → structured fields. Pure strategy."""
from __future__ import annotations

import pytest

from src.strategy.enrichment.tennis_question_parser import (
    _detect_surface,
    _extract_player_names,
    map_market_type,
    parse_tennis_question,
)


# ── map_market_type ───────────────────────────────────────────────────────────


def test_map_market_type_first_set_winner() -> None:
    assert map_market_type("tennis_first_set_winner") == "first_set_winner"


def test_map_market_type_set_handicap() -> None:
    assert map_market_type("tennis_set_handicap") == "set_handicap_minus_1_5"


def test_map_market_type_set_totals() -> None:
    assert map_market_type("tennis_set_totals") == "total_sets_under_2_5"


def test_map_market_type_unsupported_returns_none() -> None:
    assert map_market_type("tennis_completed_match") is None


def test_map_market_type_completed_match_returns_none() -> None:
    assert map_market_type("tennis_completed_match") is None


def test_map_market_type_empty_returns_none() -> None:
    assert map_market_type("") is None


# ── surface detection ─────────────────────────────────────────────────────────


def test_detect_surface_slug_contains_roland_garros() -> None:
    assert _detect_surface("atp-djokovic-alcaraz-roland-garros-2026", "") == "clay"


def test_detect_surface_question_contains_geneva() -> None:
    assert _detect_surface("", "Geneva Open: Adrian Mannarino vs Raphael Collignon") == "clay"


def test_detect_surface_slug_wimbledon() -> None:
    assert _detect_surface("atp-djokovic-alcaraz-wimbledon-2026", "") == "grass"


def test_detect_surface_queens() -> None:
    assert _detect_surface("", "Queen's Club: Player1 vs Player2") == "grass"


def test_detect_surface_us_open() -> None:
    assert _detect_surface("atp-player1-player2-us-open-2026", "") == "hard"


def test_detect_surface_australian_open() -> None:
    assert _detect_surface("", "Australian Open: Player1 vs Player2") == "hard"


def test_detect_surface_default_hard() -> None:
    """No tournament keyword → default hard."""
    assert _detect_surface("atp-djokovic-alcaraz-2026", "") == "hard"


def test_detect_surface_madrid() -> None:
    assert _detect_surface("", "Madrid Open: Alcaraz vs Sinner") == "clay"


def test_detect_surface_halle() -> None:
    assert _detect_surface("atp-djokovic-haller-halle-2026", "") == "grass"


# ── player name extraction ────────────────────────────────────────────────────


def test_extract_player_names_simple_vs() -> None:
    p1, p2 = _extract_player_names("Adrian Mannarino vs Raphael Collignon")
    assert p1 == "Adrian Mannarino"
    assert p2 == "Raphael Collignon"


def test_extract_player_names_set_prefix() -> None:
    """'Set 1 Winner: P1 vs P2' — prefix stripped."""
    p1, p2 = _extract_player_names("Set 1 Winner: Siegemund vs Samsonova")
    assert p1 is not None
    assert "Siegemund" in p1
    assert p2 is not None
    assert "Samsonova" in p2


def test_extract_player_names_tournament_prefix() -> None:
    """'Geneva Open: P1 vs P2' — tournament prefix stripped."""
    p1, p2 = _extract_player_names("Geneva Open: Adrian Mannarino vs Raphael Collignon")
    assert p1 is not None
    assert "Mannarino" in p1
    assert p2 is not None
    assert "Collignon" in p2


def test_extract_player_names_handicap_format() -> None:
    """'Set Handicap: P1 (-1.5) vs P2 (+1.5)' — handicap suffix stripped."""
    p1, p2 = _extract_player_names("Set Handicap: Samsonova (-1.5) vs Siegemund (+1.5)")
    assert p1 == "Samsonova"
    assert p2 == "Siegemund"


def test_extract_player_names_ou_suffix() -> None:
    """'P1 vs. P2: Set 1 Games O/U 8.5' — suffix stripped from p2."""
    p1, p2 = _extract_player_names("Siegemund vs. Samsonova: Set 1 Games O/U 8.5")
    assert p1 is not None
    assert "Siegemund" in p1
    assert p2 is not None
    assert "Samsonova" in p2


def test_extract_player_names_empty_returns_none() -> None:
    p1, p2 = _extract_player_names("")
    assert p1 is None
    assert p2 is None


def test_extract_player_names_no_vs_returns_none() -> None:
    p1, p2 = _extract_player_names("Will Djokovic win Wimbledon?")
    assert p1 is None or p2 is None  # no opponent


# ── parse_tennis_question ─────────────────────────────────────────────────────


def test_parse_tennis_question_first_set_winner() -> None:
    result = parse_tennis_question(
        question="Set 1 Winner: Djokovic vs Alcaraz",
        sports_market_type="tennis_first_set_winner",
        slug="atp-djokovic-alcaraz-roland-garros-2026",
    )
    assert result is not None
    assert result["market_type"] == "first_set_winner"
    assert "Djokovic" in result["p1_name"]
    assert "Alcaraz" in result["p2_name"]
    assert result["surface"] == "clay"


def test_parse_tennis_question_set_handicap() -> None:
    result = parse_tennis_question(
        question="Set Handicap: Tsitsipas (-1.5) vs Tien (+1.5)",
        sports_market_type="tennis_set_handicap",
        slug="atp-tsitsipas-tien-2026",
    )
    assert result is not None
    assert result["market_type"] == "set_handicap_minus_1_5"
    assert result["p1_name"] == "Tsitsipas"
    assert result["p2_name"] == "Tien"


def test_parse_tennis_question_set_totals() -> None:
    result = parse_tennis_question(
        question="Tsitsipas vs. Tien: Total Sets O/U 2.5",
        sports_market_type="tennis_set_totals",
        slug="atp-tsitsipas-tien-2026",
    )
    assert result is not None
    assert result["market_type"] == "total_sets_under_2_5"


def test_parse_tennis_question_unsupported_type_returns_none() -> None:
    result = parse_tennis_question(
        question="Will the match be completed?",
        sports_market_type="tennis_completed_match",
        slug="atp-djokovic-alcaraz-2026",
    )
    assert result is None


def test_parse_tennis_question_unresolvable_question_returns_none() -> None:
    result = parse_tennis_question(
        question="Random nonsense with no player names",
        sports_market_type="tennis_first_set_winner",
        slug="atp-xxx-yyy-2026",
    )
    assert result is None


# ── moneyline (match winner) ──────────────────────────────────────────────────


def test_map_market_type_moneyline() -> None:
    assert map_market_type("moneyline") == "match_winner"


def test_parse_tennis_question_moneyline_simple_vs() -> None:
    """ATP moneyline: plain 'P1 vs P2' question should parse to match_winner."""
    result = parse_tennis_question(
        question="Carlos Alcaraz vs Novak Djokovic",
        sports_market_type="moneyline",
        slug="atp-alcaraz-djokovic-2026-06-01",
    )
    assert result is not None
    assert result["market_type"] == "match_winner"
    assert "Alcaraz" in result["p1_name"]
    assert "Djokovic" in result["p2_name"]


def test_parse_tennis_question_moneyline_tournament_prefix() -> None:
    """Moneyline with tournament prefix: 'Roland Garros: P1 vs P2'."""
    result = parse_tennis_question(
        question="Roland Garros: Djokovic vs Sinner",
        sports_market_type="moneyline",
        slug="atp-djokovic-sinner-roland-garros-2026",
    )
    assert result is not None
    assert result["market_type"] == "match_winner"
    assert result["surface"] == "clay"


def test_parse_tennis_question_moneyline_wta_slug_parses_with_tour_wta() -> None:
    """WTA moneyline slug parses successfully and reports tour='wta'."""
    result = parse_tennis_question(
        question="Swiatek vs Sabalenka",
        sports_market_type="moneyline",
        slug="wta-swiatek-sabalenka-2026-06-01",
    )
    assert result is not None
    assert result["market_type"] == "match_winner"
    assert result["tour"] == "wta"


def test_parse_tennis_question_completed_match_returns_none() -> None:
    """'will match be completed?' is not predictable — must return None."""
    result = parse_tennis_question(
        question="Will the match be completed?",
        sports_market_type="tennis_completed_match",
        slug="atp-alcaraz-djokovic-2026-06-01-completed",
    )
    assert result is None


# ── tennis_match_totals ───────────────────────────────────────────────────────


def test_map_market_type_tennis_match_totals() -> None:
    assert map_market_type("tennis_match_totals") == "match_totals_over_under"


def test_parse_tennis_question_match_totals() -> None:
    """match_totals O/U question: player names extracted, market_type correct."""
    result = parse_tennis_question(
        question="Djokovic vs Alcaraz: Match Games O/U 21.5",
        sports_market_type="tennis_match_totals",
        slug="atp-djokovic-alcaraz-2026",
    )
    assert result is not None
    assert result["market_type"] == "match_totals_over_under"
    assert "Djokovic" in result["p1_name"]
    assert "Alcaraz" in result["p2_name"]


def test_parse_tennis_question_match_totals_wta_parses_with_tour_wta() -> None:
    """WTA match_totals parses successfully and reports tour='wta'."""
    result = parse_tennis_question(
        question="Swiatek vs Sabalenka: Match Games O/U 20.5",
        sports_market_type="tennis_match_totals",
        slug="wta-swiatek-sabalenka-2026",
    )
    assert result is not None
    assert result["market_type"] == "match_totals_over_under"
    assert result["tour"] == "wta"


# ── tour detection ────────────────────────────────────────────────────────────


def test_parse_atp_slug_returns_tour_atp() -> None:
    parsed = parse_tennis_question(
        question="Set 1 Winner: Djokovic vs Alcaraz",
        sports_market_type="tennis_first_set_winner",
        slug="atp-djokovic-alcaraz-roland-garros-2026",
    )
    assert parsed is not None
    assert parsed["tour"] == "atp"


def test_parse_wta_slug_returns_tour_wta() -> None:
    parsed = parse_tennis_question(
        question="Set 1 Winner: Swiatek vs Gauff",
        sports_market_type="tennis_first_set_winner",
        slug="wta-swiatek-gauff-roland-garros-2026",
    )
    assert parsed is not None
    assert parsed["tour"] == "wta"


def test_parse_unknown_prefix_defaults_to_atp() -> None:
    """Slugs without atp-/wta- prefix default to atp (back-compat for malformed slugs)."""
    parsed = parse_tennis_question(
        question="Set 1 Winner: A vs B",
        sports_market_type="tennis_first_set_winner",
        slug="someother-prefix-a-b-2026",
    )
    assert parsed is not None
    assert parsed["tour"] == "atp"
