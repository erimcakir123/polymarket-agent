"""Tests for team_lookup — abbreviation ↔ Stats API team_id."""
from src.infrastructure.mlb_data.team_lookup import (
    abbreviation_to_team_id,
    team_id_to_abbreviation,
    TEAM_ABBREVIATIONS,
)


def test_cle_returns_cleveland_id():
    assert abbreviation_to_team_id("cle") == 114


def test_phi_returns_phillies_id():
    assert abbreviation_to_team_id("phi") == 143


def test_uppercase_input_normalized():
    assert abbreviation_to_team_id("CLE") == 114


def test_unknown_returns_none():
    assert abbreviation_to_team_id("zzz") is None


def test_reverse_lookup_phi():
    assert team_id_to_abbreviation(143) == "phi"


def test_reverse_unknown_returns_none():
    assert team_id_to_abbreviation(999) is None


def test_all_30_teams_present():
    assert len(TEAM_ABBREVIATIONS) == 30
