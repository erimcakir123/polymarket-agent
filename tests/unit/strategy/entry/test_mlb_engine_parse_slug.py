"""Unit tests for MlbSubmarketEngine._parse_slug_static (Task A3).

Verifies that the static parser returns (date_str, market_type, line, away, home)
for valid MLB slugs, and None for unrecognised slugs.
"""
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def test_parse_totals_slug_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-total-8pt5"
    )
    assert result == ("2026-05-22", "totals", 8.5, "cle", "phi")


def test_parse_run_line_neg_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-spread-neg1pt5"
    )
    assert result == ("2026-05-22", "run_line", -1.5, "cle", "phi")


def test_parse_run_line_pos_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-spread-pos1pt5"
    )
    assert result == ("2026-05-22", "run_line", 1.5, "cle", "phi")


def test_parse_unknown_returns_none():
    assert MlbSubmarketEngine._parse_slug_static("nba-okc-sas-2026-05-22") is None
