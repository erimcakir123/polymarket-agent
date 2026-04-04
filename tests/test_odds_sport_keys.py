"""Tests for Polymarket -> Odds API sport key mapping."""


def test_slug_prefix_to_odds_key_soccer():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("epl") == "soccer_epl"
    assert slug_to_odds_key("lal") == "soccer_spain_la_liga"
    assert slug_to_odds_key("bun") == "soccer_germany_bundesliga"
    assert slug_to_odds_key("sea") == "soccer_italy_serie_a"
    assert slug_to_odds_key("fl1") == "soccer_france_ligue_one"
    assert slug_to_odds_key("ere") == "soccer_netherlands_eredivisie"
    assert slug_to_odds_key("mls") == "soccer_usa_mls"
    assert slug_to_odds_key("ucl") == "soccer_uefa_champs_league"
    assert slug_to_odds_key("spl") == "soccer_saudi_arabia_pro_league"
    assert slug_to_odds_key("arg") == "soccer_argentina_primera_division"


def test_slug_prefix_to_odds_key_american():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("mlb") == "baseball_mlb"
    assert slug_to_odds_key("nba") == "basketball_nba"
    assert slug_to_odds_key("nhl") == "icehockey_nhl"
    assert slug_to_odds_key("nfl") == "americanfootball_nfl"


def test_slug_prefix_to_odds_key_mma():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("ufc") == "mma_mixed_martial_arts"


def test_slug_prefix_unknown_returns_none():
    from src.matching.odds_sport_keys import slug_to_odds_key
    assert slug_to_odds_key("xyz999") is None
    assert slug_to_odds_key("") is None
    assert slug_to_odds_key(None) is None


def test_tag_to_odds_key_soccer():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("premier-league") == "soccer_epl"
    assert tag_to_odds_key("la-liga") == "soccer_spain_la_liga"
    assert tag_to_odds_key("serie-a") == "soccer_italy_serie_a"
    assert tag_to_odds_key("bundesliga") == "soccer_germany_bundesliga"
    assert tag_to_odds_key("ligue-1") == "soccer_france_ligue_one"
    assert tag_to_odds_key("eredivisie") == "soccer_netherlands_eredivisie"
    assert tag_to_odds_key("champions-league") == "soccer_uefa_champs_league"
    assert tag_to_odds_key("saudi-professional-league") == "soccer_saudi_arabia_pro_league"


def test_tag_to_odds_key_strips_year_suffix():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("serie-a-2025") == "soccer_italy_serie_a"
    assert tag_to_odds_key("la-liga-2025") == "soccer_spain_la_liga"
    assert tag_to_odds_key("ligue-1-2025") == "soccer_france_ligue_one"


def test_tag_unknown_returns_none():
    from src.matching.odds_sport_keys import tag_to_odds_key
    assert tag_to_odds_key("unknown-league-xyz") is None
    assert tag_to_odds_key("") is None
    assert tag_to_odds_key(None) is None


def test_resolve_odds_key_prefers_slug():
    from src.matching.odds_sport_keys import resolve_odds_key
    result = resolve_odds_key(slug="epl-ars-che-2026-04-04", tags=["premier-league"])
    assert result == "soccer_epl"


def test_resolve_odds_key_falls_back_to_tags():
    from src.matching.odds_sport_keys import resolve_odds_key
    result = resolve_odds_key(slug="xxx-ars-che-2026-04-04", tags=["premier-league"])
    assert result == "soccer_epl"


def test_resolve_odds_key_no_match():
    from src.matching.odds_sport_keys import resolve_odds_key
    result = resolve_odds_key(slug="xxx-yyy", tags=["unknown-tag"])
    assert result is None


def test_is_soccer_key_true():
    from src.matching.odds_sport_keys import is_soccer_key
    assert is_soccer_key("soccer_epl") is True
    assert is_soccer_key("soccer_italy_serie_a") is True
    assert is_soccer_key("soccer_uefa_champs_league") is True


def test_is_soccer_key_false():
    from src.matching.odds_sport_keys import is_soccer_key
    assert is_soccer_key("baseball_mlb") is False
    assert is_soccer_key("basketball_nba") is False
    assert is_soccer_key("tennis_atp_miami_open") is False
    assert is_soccer_key("mma_mixed_martial_arts") is False


def test_is_soccer_key_empty_or_none():
    from src.matching.odds_sport_keys import is_soccer_key
    assert is_soccer_key("") is False
    assert is_soccer_key(None) is False
