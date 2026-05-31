"""2026-05-31 fix: aynı maça + aynı tipe + aynı yöne max 1 pozisyon.

Spurs örneği: 3 ayrı totals (211.5/210.5/207.5) hepsi over → maç düşük sayılı
bitti → 3'ü de kaybetti = -$60 zincir kayıp. Profesyonel literatür: positively
correlated bets aynı yöne riski 3× yapar, edge'i değil. Çözüm: aynı event_id +
aynı sports_market_type + aynı direction varsa yeni entry skip.

Farklı yön (over vs under) veya farklı market_type (moneyline vs totals)
EKLENMESİNE izin verilir — bağımsız bahis (max_positions_per_event=3 bütünde).
"""
from unittest.mock import MagicMock

from src.models.market import MarketData
from src.models.position import Position
from src.orchestration.entry_processor import EntryProcessor


def _mk_market(cid: str, market_type: str = "totals") -> MarketData:
    return MarketData(
        condition_id=cid,
        event_id="spurs-okc-evt1",
        slug="nba-sas-okc-2026-05-30-total-211pt5",
        question="Spurs vs Thunder: O/U 211.5",
        yes_token_id="ty", no_token_id="tn",
        yes_price=0.50, no_price=0.50,
        liquidity=5000, volume_24h=1000,
        end_date_iso="2026-05-31T00:00:00Z",
        match_start_iso="2026-05-31T00:00:00Z",
        sport_tag="nba",
        sports_market_type=market_type,
    )


def _mk_position(cid: str, market_type: str = "totals", direction: str = "BUY_NO") -> Position:
    return Position(
        condition_id=cid, token_id="ty", direction=direction,
        entry_price=0.49, size_usdc=50.0, shares=102.0, current_price=0.40,
        anchor_probability=0.5, entry_reason="consensus", confidence="A",
        sport_tag="nba", event_id="spurs-okc-evt1",
        slug="nba-sas-okc-2026-05-30-total-211pt5",
        entry_timestamp="2026-05-30T20:00:00Z",
        sports_market_type=market_type,
    )


def test_same_event_same_type_same_direction_blocked():
    """KRİTİK: aynı (event_id, market_type, direction) varsa yeni entry SKIP."""
    deps = MagicMock()
    existing = _mk_position("0xfirst", market_type="totals", direction="BUY_NO")
    deps.state.portfolio.positions = {"0xfirst": existing}

    ep = EntryProcessor.__new__(EntryProcessor)
    ep.deps = deps

    # Yeni totals over bahsi (FARKLI condition_id ama aynı event+type+dir)
    market = _mk_market("0xsecond", market_type="totals")
    signal = MagicMock()
    signal.direction.value = "BUY_NO"
    signal.size_usdc = 50.0

    ep._execute_entry(market, signal)

    # place_order ÇAĞRILMAMALI (korelasyon riski)
    deps.executor.place_order.assert_not_called()


def test_same_event_different_market_type_allowed():
    """Aynı maça farklı market_type (moneyline + totals) İZİN VERİLİR."""
    deps = MagicMock()
    existing = _mk_position("0xml", market_type="moneyline", direction="BUY_YES")
    deps.state.portfolio.positions = {"0xml": existing}
    deps.executor.place_order.return_value = {"status": "error", "reason": "test_stop"}

    ep = EntryProcessor.__new__(EntryProcessor)
    ep.deps = deps

    market = _mk_market("0xtot", market_type="totals")  # Farklı tip
    signal = MagicMock()
    signal.direction.value = "BUY_NO"
    signal.size_usdc = 50.0

    ep._execute_entry(market, signal)

    # place_order ÇAĞRILMALI (farklı market_type bağımsız)
    deps.executor.place_order.assert_called_once()


def test_same_event_same_type_different_direction_allowed():
    """Aynı maça aynı tip ama TERS yön (over vs under) İZİN VERİLİR.

    Hedge stratejisi olabilir; korelasyon riski yok (zıt yönlerden hedge).
    """
    deps = MagicMock()
    existing = _mk_position("0xover", market_type="totals", direction="BUY_YES")
    deps.state.portfolio.positions = {"0xover": existing}
    deps.executor.place_order.return_value = {"status": "error", "reason": "test_stop"}

    ep = EntryProcessor.__new__(EntryProcessor)
    ep.deps = deps

    market = _mk_market("0xunder", market_type="totals")
    signal = MagicMock()
    signal.direction.value = "BUY_NO"  # Ters yön
    signal.size_usdc = 50.0

    ep._execute_entry(market, signal)

    deps.executor.place_order.assert_called_once()
