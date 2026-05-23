from unittest.mock import MagicMock

from src.models.enums import Direction, EntryReason
from src.models.signal import Signal


def _mk_market(cid: str, sport: str, mtype: str) -> MagicMock:
    m = MagicMock()
    m.condition_id = cid
    m.sport_tag = sport
    m.sports_market_type = mtype
    return m


def _mk_signal(cid: str) -> Signal:
    return Signal(
        condition_id=cid, direction=Direction.BUY_YES, anchor_probability=0.6,
        market_price=0.5, edge=0.08, confidence="A", size_usdc=0.0,
        entry_reason=EntryReason.MLB_SUBMARKET, bookmaker_prob=0.0,
        num_bookmakers=0, has_sharp=False, sport_tag="baseball_mlb", event_id="evt-x",
    )


def test_scanner_routes_mlb_totals_to_model() -> None:
    from src.orchestration.scanner import classify_anchor_path
    mlb_totals = _mk_market("c1", "baseball_mlb", "totals")
    assert classify_anchor_path(mlb_totals) == "model"


def test_scanner_routes_mlb_moneyline_to_model() -> None:
    from src.orchestration.scanner import classify_anchor_path
    mlb_ml = _mk_market("c2", "baseball_mlb", "moneyline")
    assert classify_anchor_path(mlb_ml) == "model"


def test_scanner_routes_nba_totals_to_bookmaker() -> None:
    from src.orchestration.scanner import classify_anchor_path
    nba_totals = _mk_market("c3", "basketball_nba", "totals")
    assert classify_anchor_path(nba_totals) == "bookmaker"


def test_scanner_collects_model_signals_when_engine_present() -> None:
    from src.orchestration.scanner import collect_model_signals
    mlb_totals = _mk_market("cid-x", "baseball_mlb", "totals")
    mlb_ml = _mk_market("cid-y", "baseball_mlb", "moneyline")
    engine = MagicMock()
    # SPEC-S C4: MLB moneyline now uses model anchor → both markets sent to engine
    engine.process.side_effect = [_mk_signal("cid-x"), _mk_signal("cid-y")]
    markets, signals = collect_model_signals(
        candidates=[mlb_totals, mlb_ml], engine=engine,
    )
    assert len(markets) == 2
    assert markets[0].condition_id == "cid-x"
    assert markets[1].condition_id == "cid-y"
    assert signals[0].condition_id == "cid-x"
    assert signals[1].condition_id == "cid-y"
    assert engine.process.call_count == 2


def test_scanner_skips_when_engine_none() -> None:
    from src.orchestration.scanner import collect_model_signals
    mlb_totals = _mk_market("cid-x", "baseball_mlb", "totals")
    markets, signals = collect_model_signals(candidates=[mlb_totals], engine=None)
    assert markets == []
    assert signals == []


def test_scanner_skips_when_engine_returns_none() -> None:
    from src.orchestration.scanner import collect_model_signals
    mlb_totals = _mk_market("cid-x", "baseball_mlb", "totals")
    engine = MagicMock()
    engine.process.return_value = None
    markets, signals = collect_model_signals(candidates=[mlb_totals], engine=engine)
    assert markets == []
    assert signals == []
