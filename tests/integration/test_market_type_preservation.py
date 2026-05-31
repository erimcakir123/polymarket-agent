"""2026-05-31 fix: tennis_set_handicap → Position'da DOĞRU market_type.

Eski bug: _resolve_market_meta sadece "totals"/"spreads" tanıyordu, geri
kalan her şey MONEYLINE'a fallback ediyordu. Sonuç:
- Polymarket'ten gelen `tennis_set_handicap` → Position'a `moneyline` yazıldı
- Sport_rules bimodal listesi eşleşmedi → $50 cap (olması gereken $15)
- Korelasyon guard yanlış gruplama
- Dashboard yanlış etiket (WIN fallback)
"""
from unittest.mock import MagicMock

from src.models.market import MarketData
from src.models.enums import SportsMarketType
from src.orchestration.entry_processor import _resolve_market_meta


def _mk(market_type: str, slug: str = "x-y-2026-05-31") -> MarketData:
    return MarketData(
        condition_id="0xa", event_id="e1", slug=slug,
        question="Set Handicap: Mensik (+1.5) vs Rublev (-1.5)",
        yes_token_id="ty", no_token_id="tn",
        yes_price=0.5, no_price=0.5,
        liquidity=5000, volume_24h=1000,
        end_date_iso="2026-06-01T00:00:00Z",
        match_start_iso="2026-06-01T00:00:00Z",
        sport_tag="tennis",
        sports_market_type=market_type,
    )


def test_tennis_set_handicap_preserved():
    """tennis_set_handicap → MONEYLINE'a düşmeyip kendisi olarak kayıt."""
    m = _mk("tennis_set_handicap")
    mt, line, side = _resolve_market_meta(m)
    assert mt == SportsMarketType.TENNIS_SET_HANDICAP
    assert line is None
    assert side is None


def test_tennis_set_totals_preserved():
    m = _mk("tennis_set_totals")
    mt, _, _ = _resolve_market_meta(m)
    assert mt == SportsMarketType.TENNIS_SET_TOTALS


def test_tennis_match_totals_preserved():
    m = _mk("tennis_match_totals")
    mt, _, _ = _resolve_market_meta(m)
    assert mt == SportsMarketType.TENNIS_MATCH_TOTALS


def test_tennis_first_set_winner_preserved():
    m = _mk("tennis_first_set_winner")
    mt, _, _ = _resolve_market_meta(m)
    assert mt == SportsMarketType.TENNIS_FIRST_SET_WINNER


def test_moneyline_still_moneyline():
    m = _mk("moneyline")
    mt, _, _ = _resolve_market_meta(m)
    assert mt == SportsMarketType.MONEYLINE


def test_unknown_type_falls_back_to_moneyline():
    """Tanınmayan market_type (yeni Polymarket tipi) → MONEYLINE fallback."""
    m = _mk("tennis_brand_new_unknown_type")
    mt, _, _ = _resolve_market_meta(m)
    assert mt == SportsMarketType.MONEYLINE


def test_totals_still_parses_line():
    m = MarketData(
        condition_id="0xa", event_id="e1",
        slug="nba-sas-okc-2026-05-30-total-211pt5",
        question="Spurs vs Thunder: O/U 211.5",
        yes_token_id="ty", no_token_id="tn",
        yes_price=0.5, no_price=0.5,
        liquidity=5000, volume_24h=1000,
        end_date_iso="2026-05-31T00:00:00Z",
        match_start_iso="2026-05-31T00:00:00Z",
        sport_tag="nba",
        sports_market_type="totals",
    )
    mt, line, side = _resolve_market_meta(m)
    assert mt == SportsMarketType.TOTALS
    assert line == 211.5
