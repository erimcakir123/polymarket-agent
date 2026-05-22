"""TennisStartEnricher: tennis market'lerin match_start_iso'sunu ESPN ile override eder."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.models.market import MarketData
from src.orchestration.tennis_start_enricher import TennisStartEnricher


def _mkt(slug: str, sport_tag: str = "tennis", start: str = "") -> MarketData:
    return MarketData(
        condition_id=f"cid-{slug}",
        question="",
        slug=slug,
        yes_token_id="t1",
        no_token_id="t2",
        yes_price=0.5,
        no_price=0.5,
        liquidity=1000.0,
        volume_24h=100.0,
        tags=[],
        end_date_iso="2026-05-30T00:00:00Z",
        match_start_iso=start,
        sport_tag=sport_tag,
    )


def _espn(home: str, away: str, date_iso: str) -> ESPNMatchScore:
    return ESPNMatchScore(
        event_id=f"{home}-{away}",
        home_name=home,
        away_name=away,
        commence_time=date_iso,
    )


def test_enrich_overrides_match_start_when_espn_match_found():
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = [
        _espn("Alex de Minaur", "Tommy Paul", "2026-05-22T16:00:00Z"),
    ]
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    markets = [_mkt("atp-minaur-paul-2026-05-22", start="2026-05-22T15:30:00Z")]
    out = enricher.enrich(markets)
    assert out[0].match_start_iso == "2026-05-22T16:00:00Z"


def test_enrich_keeps_polymarket_start_when_no_espn_match():
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = []
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    markets = [_mkt("atp-minaur-paul-2026-05-22", start="2026-05-22T15:30:00Z")]
    out = enricher.enrich(markets)
    assert out[0].match_start_iso == "2026-05-22T15:30:00Z"


def test_enrich_skips_non_tennis_markets():
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = [_espn("a", "b", "2026-05-22T20:00:00Z")]
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    markets = [_mkt("mlb-yankees-redsox", sport_tag="mlb", start="2026-05-22T19:05:00Z")]
    out = enricher.enrich(markets)
    assert out[0].match_start_iso == "2026-05-22T19:05:00Z"
    espn_client.fetch_tennis_matches_today.assert_not_called()


def test_enrich_no_tennis_markets_skips_espn_call():
    espn_client = MagicMock()
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    enricher.enrich([_mkt("mlb-yankees-redsox", sport_tag="mlb")])
    espn_client.fetch_tennis_matches_today.assert_not_called()


def test_enrich_espn_fail_returns_markets_unchanged():
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.side_effect = Exception("ESPN down")
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    markets = [_mkt("atp-minaur-paul-2026-05-22", start="2026-05-22T15:30:00Z")]
    out = enricher.enrich(markets)
    assert out[0].match_start_iso == "2026-05-22T15:30:00Z"


def test_enrich_caches_espn_response_within_ttl():
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = []
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    # match_start_iso bos oldugu icin sadece bugun fetch'lenir (market'lerden tarih
    # gelmeyince today fallback). 2 league x 1 day (bugun) x 1 fetch (cached) = 2 call.
    enricher.enrich([_mkt("atp-x-y-2026-05-22")])
    enricher.enrich([_mkt("atp-a-b-2026-05-22")])
    assert espn_client.fetch_tennis_matches_today.call_count == 2


def test_enrich_atp_slug_matches_atp_only_event():
    """Slug 'atp-...' ile baslayan market sadece atp league'inden eslesmeli."""
    espn_client = MagicMock()

    def fetch(league, date):
        if league == "atp":
            return [_espn("Alex de Minaur", "Tommy Paul", "2026-05-22T16:00:00Z")]
        return []

    espn_client.fetch_tennis_matches_today.side_effect = fetch
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    # market start'i dolu olmali: same-day guard ESPN tarihi ile market tarihini eslesir.
    out = enricher.enrich([_mkt("atp-minaur-paul-2026-05-22", start="2026-05-22T15:00:00Z")])
    assert out[0].match_start_iso == "2026-05-22T16:00:00Z"


def test_enrich_doubles_slug_parses_surnames_correctly():
    espn_client = MagicMock()
    espn_client.fetch_tennis_matches_today.return_value = [
        ESPNMatchScore(
            event_id="d1",
            home_name="John Fortrom",
            away_name="Mike Gadatu",
            commence_time="2026-05-23T15:00:00Z",
        ),
    ]
    enricher = TennisStartEnricher(espn_client=espn_client, cache_ttl_sec=300)
    out = enricher.enrich([_mkt("atp-doubles-fortrom-gadatu-2026-05-23",
                                  sport_tag="tennis", start="2026-05-23T14:00:00Z")])
    assert out[0].match_start_iso == "2026-05-23T15:00:00Z"


def test_slug_surnames_skips_doubles_token():
    from src.orchestration.tennis_start_enricher import _slug_surnames
    assert _slug_surnames("atp-minaur-paul-2026-05-22") == ("minaur", "paul")
    assert _slug_surnames("atp-doubles-fortrom-gadatu-2026-05-22") == ("fortrom", "gadatu")
    assert _slug_surnames("wta-doubles-smith-jones-2026-05-22") == ("smith", "jones")
    assert _slug_surnames("xyz-foo-bar-2026") is None
