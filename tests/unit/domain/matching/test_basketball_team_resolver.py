"""Basketball team resolver — Polymarket slug ↔ NBA team abbreviation."""
from __future__ import annotations

from src.domain.matching.basketball_team_resolver import resolve_team_pair


def test_resolve_nba_standard_slug():
    res = resolve_team_pair("nba-lal-gsw-2024-11-01", league="nba")
    assert res.home == "LAL"
    assert res.away == "GSW"
    assert res.ok is True


def test_resolve_handles_full_team_names():
    """Bazı Polymarket slug'larda "lakers-warriors" pattern var."""
    res = resolve_team_pair("nba-lakers-vs-warriors-2024-11-01", league="nba")
    assert res.home == "LAL"
    assert res.away == "GSW"


def test_resolve_wnba_abbreviation():
    res = resolve_team_pair("wnba-lva-nyl-2024-08-15", league="wnba")
    assert res.home == "LVA"
    assert res.away == "NYL"


def test_resolve_unknown_team_returns_not_ok():
    res = resolve_team_pair("nba-xxx-yyy-2024-11-01", league="nba")
    assert res.ok is False
    assert res.fail_reason is not None


def test_resolve_ncaab_top_program_full_name():
    """NCAAB popüler okullar — full name slug."""
    res = resolve_team_pair("ncaab-duke-unc-2024-12-01", league="ncaab")
    assert res.home == "DUKE"
    assert res.away == "UNC"


def test_resolve_ncaab_abbreviation_or_nickname():
    res = resolve_team_pair("ncaab-jayhawks-zags-2024-12-01", league="ncaab")
    assert res.home == "KU"
    assert res.away == "GONZ"


def test_resolve_wncaab_top_programs():
    res = resolve_team_pair("wncaab-southcarolina-iowa-2024-12-01", league="wncaab")
    assert res.home == "SC"
    assert res.away == "IOWA"


def test_resolve_ncaab_unknown_returns_not_ok():
    res = resolve_team_pair("ncaab-podunku-tinytown-2024-12-01", league="ncaab")
    assert res.ok is False


def test_resolve_euroleague_top_teams():
    """Euroleague slug — Türkçe + İngilizce varyasyonları."""
    res = resolve_team_pair("euroleague-realmadrid-barcelona-2024-10-15", league="euroleague")
    assert res.home == "RM"
    assert res.away == "FCB"


def test_resolve_euroleague_turkish_teams():
    res = resolve_team_pair("euroleague-fenerbahce-efes-2024-11-01", league="euroleague")
    assert res.home == "FB"
    assert res.away == "EFES"
