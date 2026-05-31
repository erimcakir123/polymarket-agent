"""2026-05-31 fix: exclude_combos check kod seviyesinde uygulanmıyordu.

Config'de tanımlı (tennis_set_totals + tennis_first_set_winner negatif EV
kanıtı: -$63 ve -$162) AMA hiçbir kod kullanmıyordu. Bot bu tipleri yine
alıyordu. Implementation entry_processor'a eklendi.
"""
from unittest.mock import MagicMock

from src.models.market import MarketData
from src.orchestration.entry_processor import EntryProcessor


def _mk_market(slug: str, market_type: str) -> MarketData:
    return MarketData(
        condition_id="0xnew", event_id="evt_new", slug=slug,
        question="Test", yes_token_id="ty", no_token_id="tn",
        yes_price=0.5, no_price=0.5,
        liquidity=5000, volume_24h=1000,
        end_date_iso="2026-06-01T00:00:00Z",
        match_start_iso="2026-06-01T00:00:00Z",
        sport_tag="tennis",
        sports_market_type=market_type,
    )


def _mk_deps(exclude_combos: list) -> MagicMock:
    deps = MagicMock()
    deps.state.portfolio.positions = {}
    deps.state.config.edge.exclude_combos = exclude_combos
    deps.executor.place_order.return_value = {"status": "error", "reason": "test"}
    return deps


def test_atp_set_totals_A_blocked_by_exclude_combos():
    """ATP + tennis_set_totals + confidence A → SKIP, place_order çağrılmamalı."""
    deps = _mk_deps([
        {"tour": "atp", "market_type": "tennis_set_totals", "confidence": "A"},
    ])
    ep = EntryProcessor.__new__(EntryProcessor)
    ep.deps = deps

    market = _mk_market("atp-jong-zverev-2026-05-31-set-totals-3pt5", "tennis_set_totals")
    signal = MagicMock()
    signal.direction.value = "BUY_YES"
    signal.confidence = "A"
    signal.size_usdc = 15.0

    ep._execute_entry(market, signal)

    deps.executor.place_order.assert_not_called()


def test_wta_first_set_winner_B_blocked():
    """WTA + tennis_first_set_winner + confidence B → SKIP."""
    deps = _mk_deps([
        {"tour": "wta", "market_type": "tennis_first_set_winner", "confidence": "B"},
    ])
    ep = EntryProcessor.__new__(EntryProcessor)
    ep.deps = deps

    market = _mk_market("wta-andreev-teichma-2026-05-31-first-set-winner", "tennis_first_set_winner")
    signal = MagicMock()
    signal.direction.value = "BUY_NO"
    signal.confidence = "B"
    signal.size_usdc = 10.0

    ep._execute_entry(market, signal)

    deps.executor.place_order.assert_not_called()


def test_atp_set_handicap_NOT_blocked():
    """ATP + tennis_set_handicap → exclude'da YOK → place_order ÇAĞRILMALI."""
    deps = _mk_deps([
        {"tour": "atp", "market_type": "tennis_set_totals", "confidence": "A"},
        {"tour": "atp", "market_type": "tennis_first_set_winner", "confidence": "A"},
    ])
    ep = EntryProcessor.__new__(EntryProcessor)
    ep.deps = deps

    market = _mk_market("atp-cobolli-svajda-2026-05-31-set-handicap-home-2pt5", "tennis_set_handicap")
    signal = MagicMock()
    signal.direction.value = "BUY_YES"
    signal.confidence = "A"
    signal.size_usdc = 15.0

    ep._execute_entry(market, signal)

    deps.executor.place_order.assert_called_once()


def test_atp_moneyline_NOT_blocked():
    """ATP moneyline → exclude'da YOK → place_order ÇAĞRILMALI."""
    deps = _mk_deps([
        {"tour": "atp", "market_type": "tennis_set_totals", "confidence": "A"},
    ])
    ep = EntryProcessor.__new__(EntryProcessor)
    ep.deps = deps

    market = _mk_market("atp-jodar-busta-2026-05-31", "moneyline")
    signal = MagicMock()
    signal.direction.value = "BUY_YES"
    signal.confidence = "A"
    signal.size_usdc = 50.0

    ep._execute_entry(market, signal)

    deps.executor.place_order.assert_called_once()


def test_wta_set_totals_atp_only_exclude_passes():
    """ATP-only exclude → WTA pazara izin verilmeli (tour ayrımı doğru)."""
    deps = _mk_deps([
        {"tour": "atp", "market_type": "tennis_set_totals", "confidence": "A"},
    ])
    ep = EntryProcessor.__new__(EntryProcessor)
    ep.deps = deps

    market = _mk_market("wta-bouzkov-oliynyk-2026-05-31-set-totals-2pt5", "tennis_set_totals")
    signal = MagicMock()
    signal.direction.value = "BUY_YES"
    signal.confidence = "A"
    signal.size_usdc = 15.0

    ep._execute_entry(market, signal)

    deps.executor.place_order.assert_called_once()
