"""Alias + ESPN mapping bütünlük testleri.

_ALIASES hedefleri, SPORT_RULES entry'leri ve ESPN path tutarlılığını doğrular.
"""
from __future__ import annotations

import pytest

from src.config.sport_rules import SPORT_RULES, _ALIASES, _normalize, get_sport_rule


# ── Meta-test: alias chain yasak ────────────────────────────────────────────

def test_all_alias_targets_exist_in_sport_rules() -> None:
    """Hiçbir alias zinciri yok — tüm _ALIASES değerleri SPORT_RULES'da olmalı."""
    broken = [
        f"_ALIASES['{k}'] → '{v}' — SPORT_RULES'da yok"
        for k, v in _ALIASES.items()
        if v not in SPORT_RULES
    ]
    assert not broken, "\n".join(broken)


# ── Ice Hockey ───────────────────────────────────────────────────────────────

def test_icehockey_ahl_normalizes_to_ahl() -> None:
    assert _normalize("icehockey_ahl") == "ahl"


def test_ahl_espn_league_is_ahl_not_nhl() -> None:
    assert get_sport_rule("icehockey_ahl", "espn_league") == "ahl"


def test_icehockey_liiga_normalizes_to_liiga() -> None:
    assert _normalize("icehockey_liiga") == "liiga"


def test_liiga_espn_league_is_empty() -> None:
    # hockey/liiga → ESPN 400; espn_league="" prevents attempt
    assert get_sport_rule("icehockey_liiga", "espn_league") == ""


def test_icehockey_shl_normalizes_to_shl() -> None:
    assert _normalize("icehockey_sweden_hockey_league") == "shl"


def test_shl_espn_league_is_empty() -> None:
    assert get_sport_rule("icehockey_sweden_hockey_league", "espn_league") == ""


def test_icehockey_allsvenskan_normalizes_to_allsvenskan() -> None:
    assert _normalize("icehockey_sweden_allsvenskan") == "allsvenskan"


def test_icehockey_mestis_normalizes_to_mestis() -> None:
    assert _normalize("icehockey_mestis") == "mestis"


# ── Basketball ───────────────────────────────────────────────────────────────

def test_basketball_wnba_normalizes_to_wnba() -> None:
    assert _normalize("basketball_wnba") == "wnba"


def test_wnba_espn_league_is_wnba() -> None:
    # basketball/wnba → ESPN 200 confirmed
    assert get_sport_rule("basketball_wnba", "espn_league") == "wnba"
    assert get_sport_rule("basketball_wnba", "espn_sport") == "basketball"


def test_basketball_euroleague_normalizes_to_euroleague() -> None:
    assert _normalize("basketball_euroleague") == "euroleague"


def test_euroleague_espn_league_is_empty() -> None:
    # basketball/euroleague → ESPN 400; no valid path
    assert get_sport_rule("basketball_euroleague", "espn_league") == ""


def test_basketball_ncaab_normalizes_to_ncaab() -> None:
    assert _normalize("basketball_ncaab") == "ncaab"


def test_ncaab_espn_league_is_correct_path() -> None:
    # basketball/mens-college-basketball → ESPN 200 confirmed
    assert get_sport_rule("basketball_ncaab", "espn_league") == "mens-college-basketball"


def test_basketball_nbl_normalizes_to_nbl() -> None:
    assert _normalize("basketball_nbl") == "nbl"


def test_nbl_espn_league_is_nbl() -> None:
    # basketball/nbl → ESPN 200 confirmed (Australian NBL)
    assert get_sport_rule("basketball_nbl", "espn_league") == "nbl"


# ── Baseball ─────────────────────────────────────────────────────────────────

def test_baseball_kbo_normalizes_to_kbo() -> None:
    assert _normalize("baseball_kbo") == "kbo"


def test_kbo_espn_league_is_empty() -> None:
    # baseball/kbo → ESPN 400 confirmed; no valid path
    assert get_sport_rule("baseball_kbo", "espn_league") == ""


def test_baseball_npb_normalizes_to_npb() -> None:
    assert _normalize("baseball_npb") == "npb"


def test_npb_espn_league_is_empty() -> None:
    # baseball/npb → ESPN 400 confirmed; no valid path
    assert get_sport_rule("baseball_npb", "espn_league") == ""


# ── Tennis ───────────────────────────────────────────────────────────────────

def test_tennis_wta_normalizes_correctly() -> None:
    # tennis_wta is in SPORT_RULES → _normalize returns "tennis_wta" directly
    assert _normalize("tennis_wta") == "tennis_wta"


def test_tennis_wta_espn_league_is_wta_not_atp() -> None:
    # tennis/wta → ESPN 200 confirmed; must NOT use tennis/atp path
    assert get_sport_rule("tennis_wta", "espn_league") == "wta"
    assert get_sport_rule("tennis_wta", "espn_sport") == "tennis"


def test_tennis_atp_espn_league_is_atp() -> None:
    assert get_sport_rule("tennis_atp", "espn_league") == "atp"


# ── MMA / Golf ───────────────────────────────────────────────────────────────

def test_mma_ufc_normalizes_to_mma() -> None:
    assert _normalize("mma_ufc") == "mma"


def test_golf_lpga_normalizes_to_golf() -> None:
    assert _normalize("golf_lpga_tour") == "golf"


def test_mma_and_golf_have_no_espn() -> None:
    assert get_sport_rule("mma", "espn_sport") == ""
    assert get_sport_rule("golf", "espn_sport") == ""


# ── Regression: previously correct mappings unchanged ────────────────────────

def test_nhl_alias_still_correct() -> None:
    assert _normalize("icehockey_nhl") == "nhl"
    assert get_sport_rule("icehockey_nhl", "espn_league") == "nhl"


def test_mlb_alias_unchanged() -> None:
    assert _normalize("baseball_mlb") == "mlb"
    assert get_sport_rule("baseball_mlb", "espn_league") == "mlb"


def test_nba_alias_unchanged() -> None:
    assert _normalize("basketball_nba") == "nba"
    assert get_sport_rule("basketball_nba", "espn_league") == "nba"
