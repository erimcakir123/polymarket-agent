"""Tests for Polymarket slug parsing."""
from src.matching.slug_parser import parse_slug, extract_slug_tokens


class TestParseSlug:
    def test_standard_format(self):
        r = parse_slug("nba-lal-bos-2026-04-05")
        assert r.sport == "nba"
        assert r.team_tokens == ["lal", "bos"]

    def test_esports_format(self):
        r = parse_slug("cs2-hero-nip-2026-04-03")
        assert r.sport == "cs2"
        assert r.team_tokens == ["hero", "nip"]

    def test_three_word_team(self):
        r = parse_slug("nba-okc-gsw-2026-04-05")
        assert r.sport == "nba"
        assert r.team_tokens == ["okc", "gsw"]

    def test_soccer_format(self):
        r = parse_slug("epl-liv-mci-2026-04-03")
        assert r.sport == "epl"
        assert r.team_tokens == ["liv", "mci"]

    def test_no_date(self):
        r = parse_slug("nba-lal-bos")
        assert r.sport == "nba"
        assert r.team_tokens == ["lal", "bos"]

    def test_unknown_sport(self):
        r = parse_slug("will-lakers-beat-celtics")
        assert r.sport is None
        assert "lakers" in r.team_tokens or len(r.team_tokens) > 0

    def test_empty_slug(self):
        r = parse_slug("")
        assert r.sport is None
        assert r.team_tokens == []

    def test_cricket_ipl(self):
        r = parse_slug("ipl-csk-mi-2026-04-05")
        assert r.sport == "ipl"
        assert r.team_tokens == ["csk", "mi"]


class TestExtractSlugTokens:
    def test_basic(self):
        tokens = extract_slug_tokens("nba-lal-bos-2026-04-05")
        assert "nba" in tokens
        assert "lal" in tokens
        assert "bos" in tokens
        assert "2026" not in tokens

    def test_single_char_excluded(self):
        tokens = extract_slug_tokens("a-bb-ccc")
        assert "a" not in tokens
        assert "bb" in tokens
        assert "ccc" in tokens
