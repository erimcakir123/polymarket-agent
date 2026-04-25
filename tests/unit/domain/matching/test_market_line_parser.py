"""Market line parser — gerçek Polymarket format'larına karşı test."""
from __future__ import annotations

import pytest
from src.domain.matching.market_line_parser import parse_spread_line, parse_total_line


# ── parse_spread_line ─────────────────────────────────────────────
def test_spread_standard_format():
    """'Spread: Lakers (-5.5)' → 5.5"""
    assert parse_spread_line("Spread: Lakers (-5.5)") == 5.5


def test_spread_integer_line():
    """'Spread: Celtics (-6)' → 6.0"""
    assert parse_spread_line("Spread: Celtics (-6)") == 6.0


def test_spread_large_line():
    """'Spread: Warriors (-13.5)' → 13.5"""
    assert parse_spread_line("Spread: Warriors (-13.5)") == 13.5


def test_spread_underdog_plus():
    """'Spread: Rockets (+5.5)' → 5.5 (absolute value)"""
    assert parse_spread_line("Spread: Rockets (+5.5)") == 5.5


def test_spread_group_item_title():
    """groupItemTitle format: 'Lakers (-5.5)' → 5.5"""
    assert parse_spread_line("Lakers (-5.5)") == 5.5


def test_spread_no_match_returns_none():
    """Tanımlanamayan format → None"""
    assert parse_spread_line("Lakers vs Rockets moneyline") is None


def test_spread_empty_returns_none():
    assert parse_spread_line("") is None


# ── parse_total_line ──────────────────────────────────────────────
def test_total_standard_format():
    """'Lakers vs Rockets: O/U 220.5' → (220.5, 'over')"""
    result = parse_total_line("Lakers vs Rockets: O/U 220.5")
    assert result == (220.5, "over")


def test_total_games_total_format():
    """Esports: 'Games Total: O/U 2.5' → (2.5, 'over')"""
    result = parse_total_line("Games Total: O/U 2.5")
    assert result == (2.5, "over")


def test_total_group_item_title():
    """groupItemTitle: 'O/U 215.5' → (215.5, 'over')"""
    result = parse_total_line("O/U 215.5")
    assert result == (215.5, "over")


def test_total_case_insensitive():
    """'o/u 220.5' (küçük harf) → (220.5, 'over')"""
    result = parse_total_line("o/u 220.5")
    assert result == (220.5, "over")


def test_total_integer_line():
    """'O/U 220' → (220.0, 'over')"""
    result = parse_total_line("O/U 220")
    assert result == (220.0, "over")


def test_total_no_match_returns_none():
    """Tanımlanamayan format → None"""
    assert parse_total_line("Lakers vs Rockets moneyline") is None


def test_total_empty_returns_none():
    assert parse_total_line("") is None
