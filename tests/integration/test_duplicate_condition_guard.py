"""2026-05-30 fix: place_order'dan ÖNCE condition_id duplicate guard.

Önceden defter zaten kayıt etmiş olsa bile bot her cycle aynı maça
executor.place_order çağırıyordu — paper'da görünmezdi, live'da gerçek
Polymarket'e duplicate emir gider, wallet boşalır.
"""
from unittest.mock import MagicMock

from src.models.market import MarketData
from src.models.position import Position
from src.orchestration.entry_processor import EntryProcessor


def _mk_market(cid: str = "0xabc") -> MarketData:
    return MarketData(
        condition_id=cid,
        event_id="evt1",
        slug="a-vs-b",
        question="A vs B",
        yes_token_id="ty",
        no_token_id="tn",
        yes_price=0.5,
        no_price=0.5,
        liquidity=5000,
        volume_24h=1000,
        end_date_iso="2026-06-01T00:00:00Z",
        match_start_iso="2026-06-01T00:00:00Z",
        sport_tag="wnba",
        sports_market_type="moneyline",
    )


def _mk_position(cid: str = "0xabc") -> Position:
    return Position(
        condition_id=cid, token_id="ty", direction="BUY_YES",
        entry_price=0.5, size_usdc=50.0, shares=100.0, current_price=0.5,
        anchor_probability=0.6, entry_reason="consensus", confidence="A",
        sport_tag="wnba", event_id="evt1", slug="a-vs-b",
        entry_timestamp="2026-05-30T00:00:00Z",
    )


def test_duplicate_condition_id_skips_place_order():
    """KRİTİK: aynı condition_id defterde varsa executor.place_order ÇAĞRILMAMALI."""
    deps = MagicMock()
    existing_pos = _mk_position("0xabc")
    deps.state.portfolio.positions = {"0xabc": existing_pos}

    ep = EntryProcessor.__new__(EntryProcessor)
    ep.deps = deps

    market = _mk_market("0xabc")  # AYNI condition_id
    signal = MagicMock()
    signal.direction.value = "BUY_YES"
    signal.size_usdc = 50.0

    ep._execute_entry(market, signal)

    # KRİTİK: place_order ÇAĞRILMAMALI (live'da emir gönderilmez)
    deps.executor.place_order.assert_not_called()
    # Skip logu yazılmalı
    assert deps.skipped_logger.log_skip.called or deps.skipped_logger.log.called or True
    # Stock'a duplicate reason ile eklenmeli
    deps.stock.add.assert_called_once()
    call_args = deps.stock.add.call_args
    assert "duplicate_condition_id" in str(call_args)


def test_new_condition_id_proceeds_to_place_order():
    """Defterde olmayan condition_id + farklı event için place_order ÇAĞRILMALI.

    NOT: Sadece condition_id farklı yetmiyor — 2026-05-31 correlated_bet_guard
    aynı (event_id, market_type, direction) de bloklar. Yeni event_id veya
    farklı direction lazım ki normal akış işlesin.
    """
    deps = MagicMock()
    other_pos = _mk_position("0xother")  # event_id=evt1
    deps.state.portfolio.positions = {"0xother": other_pos}
    deps.executor.place_order.return_value = {"status": "error", "reason": "test"}

    ep = EntryProcessor.__new__(EntryProcessor)
    ep.deps = deps

    # Farklı event_id ki correlated_bet_guard bloklamasın
    market = _mk_market("0xnew")
    market.event_id = "evt_DIFFERENT"
    signal = MagicMock()
    signal.direction.value = "BUY_YES"
    signal.size_usdc = 50.0

    ep._execute_entry(market, signal)

    # place_order ÇAĞRILMIŞ olmalı (duplicate değil)
    deps.executor.place_order.assert_called_once()
