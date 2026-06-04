"""SPEC-Z17: entry processor event log'a entry event yazar."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.orchestration.entry_processor import EntryProcessor


def _trade_record(**over):
    base = dict(
        slug="s", condition_id="c1", event_id="e", token_id="t",
        question="q", sport_tag="tennis", sport_category="tennis",
        league="", direction="BUY_YES", entry_price=0.45,
        size_usdc=50.0, shares=100.0, confidence="A",
        bookmaker_prob=0.5, anchor_probability=0.5,
        num_bookmakers=5.0, has_sharp=True,
        entry_reason="normal", entry_timestamp="t0",
        source="model",
    )
    base.update(over)
    from src.infrastructure.persistence.trade_logger import TradeRecord
    return TradeRecord(**base)


def test_entry_event_logged_alongside_trade_record():
    """SPEC-Z17: pozisyon eklenince trade_event_log.append_entry çağrılır."""
    portfolio = MagicMock()
    portfolio.add_position.return_value = True
    deps = SimpleNamespace(
        state=SimpleNamespace(portfolio=portfolio),
        trade_logger=MagicMock(),
        trade_event_log=MagicMock(),
        notifier=None,
    )
    proc = EntryProcessor.__new__(EntryProcessor)
    proc.deps = deps
    pos = MagicMock()
    pos.slug = "s"
    pos.condition_id = "c1"
    pos.event_id = "e"
    rec = _trade_record()
    ok = proc._persist_filled_position(pos, rec)
    assert ok is True
    deps.trade_event_log.append_entry.assert_called_once()
    kwargs = deps.trade_event_log.append_entry.call_args.kwargs
    assert kwargs["condition_id"] == "c1"
    assert kwargs["entry_price"] == 0.45
    assert kwargs["sport_tag"] == "tennis"
