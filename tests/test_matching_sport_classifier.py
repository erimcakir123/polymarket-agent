"""Tests for sport classification from Polymarket market data."""
from dataclasses import dataclass
from src.matching.sport_classifier import classify_sport


@dataclass
class FakeMarket:
    slug: str = ""
    sport_tag: str = ""
    tags: list = None
    question: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class TestClassifySport:
    def test_slug_prefix_nba(self):
        m = FakeMarket(slug="nba-lal-bos-2026-04-05")
        assert classify_sport(m) == "basketball"

    def test_slug_prefix_cs2(self):
        m = FakeMarket(slug="cs2-hero-nip-2026-04-03")
        assert classify_sport(m) == "esports"

    def test_slug_prefix_epl(self):
        m = FakeMarket(slug="epl-liv-mci-2026-04-03")
        assert classify_sport(m) == "soccer"

    def test_slug_prefix_mlb(self):
        m = FakeMarket(slug="mlb-nyy-bos-2026-04-05")
        assert classify_sport(m) == "baseball"

    def test_slug_prefix_nhl(self):
        m = FakeMarket(slug="nhl-nyr-bos-2026-04-05")
        assert classify_sport(m) == "hockey"

    def test_slug_prefix_val(self):
        m = FakeMarket(slug="val-fnc-tl-2026-04-05")
        assert classify_sport(m) == "esports"

    def test_slug_prefix_lol(self):
        m = FakeMarket(slug="lol-t1-geng-2026-04-05")
        assert classify_sport(m) == "esports"

    def test_slug_prefix_dota2(self):
        m = FakeMarket(slug="dota2-spirit-navi-2026-04-05")
        assert classify_sport(m) == "esports"

    def test_slug_prefix_ufc(self):
        m = FakeMarket(slug="ufc-jones-miocic-2026-04-05")
        assert classify_sport(m) == "mma"

    def test_slug_prefix_atp(self):
        m = FakeMarket(slug="atp-sinner-djokovic-2026-04-05")
        assert classify_sport(m) == "tennis"

    def test_slug_prefix_cricket_ipl(self):
        m = FakeMarket(slug="ipl-csk-mi-2026-04-05")
        assert classify_sport(m) == "cricket"

    def test_slug_prefix_rugby(self):
        m = FakeMarket(slug="ruprem-eng-fra-2026-04-05")
        assert classify_sport(m) == "rugby"

    def test_sport_tag_fallback(self):
        m = FakeMarket(slug="unknown-slug-here", sport_tag="cs2")
        assert classify_sport(m) == "esports"

    def test_question_keyword_fallback(self):
        m = FakeMarket(slug="will-team-win", question="NBA: Will the Lakers beat the Celtics?")
        assert classify_sport(m) == "basketball"

    def test_unknown_returns_none(self):
        m = FakeMarket(slug="some-random-market")
        assert classify_sport(m) is None

    def test_cross_sport_check(self):
        from src.matching.sport_classifier import sports_compatible
        assert sports_compatible("basketball", "basketball") is True
        assert sports_compatible("basketball", "football") is False
        assert sports_compatible("esports", "basketball") is False
        assert sports_compatible(None, "basketball") is True
