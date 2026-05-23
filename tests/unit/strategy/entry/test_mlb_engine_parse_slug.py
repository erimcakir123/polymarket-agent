"""Unit tests for MlbSubmarketEngine._parse_slug_static.

SPEC-X (2026-05-24): slug parser gerçek Polymarket formatına çekildi.
Eski `spread-(pos|neg)1pt5` formatı artık desteklenmez.
Yeni format: `spread-(home|away)-{N}pt5` — değişken N.
"""
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def test_parse_totals_slug_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-total-8pt5"
    )
    assert result == ("2026-05-22", "totals", 8.5, "cle", "phi")


def test_parse_totals_slug_variable_line_10pt5():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-23-total-10pt5"
    )
    assert result == ("2026-05-23", "totals", 10.5, "cle", "phi")


def test_parse_run_line_home_1pt5_returns_negative_home_line():
    # spread-home-1pt5 = home team -1.5 covers (yes_token)
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-23-spread-home-1pt5"
    )
    assert result == ("2026-05-23", "run_line", -1.5, "cle", "phi")


def test_parse_run_line_away_1pt5_returns_positive_home_line():
    # spread-away-1pt5 = away team -1.5 covers → home team gets +1.5
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-lad-mil-2026-05-23-spread-away-1pt5"
    )
    assert result == ("2026-05-23", "run_line", 1.5, "lad", "mil")


def test_parse_run_line_home_3pt5_returns_negative_3pt5():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-wsh-atl-2026-05-23-spread-home-3pt5"
    )
    assert result == ("2026-05-23", "run_line", -3.5, "wsh", "atl")


def test_parse_run_line_home_2pt5_variable_line_supported():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cws-sf-2026-05-23-spread-home-2pt5"
    )
    assert result == ("2026-05-23", "run_line", -2.5, "cws", "sf")


def test_parse_run_line_old_pos_format_returns_none():
    # SPEC-X: eski format artık desteklenmez — backward-incompatible (kasıtlı)
    assert MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-spread-pos1pt5"
    ) is None


def test_parse_run_line_old_neg_format_returns_none():
    assert MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-spread-neg1pt5"
    ) is None


def test_parse_unknown_returns_none():
    assert MlbSubmarketEngine._parse_slug_static("nba-okc-sas-2026-05-22") is None


def test_parse_moneyline_slug_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22"
    )
    assert result == ("2026-05-22", "moneyline", 0.0, "cle", "phi")


def test_parse_moneyline_with_unknown_suffix_rejected():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-foo"
    )
    assert result is None
