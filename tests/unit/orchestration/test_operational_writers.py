"""operational_writers — 3 free function smoke testleri."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.models.market import MarketData
from src.orchestration import operational_writers


def _make_market(slug="m1", sport="mlb"):
    return MarketData(
        condition_id="c", yes_token_id="y", no_token_id="n",
        question="A vs B", slug=slug, sport_tag=sport,
        yes_price=0.5, no_price=0.5, liquidity=100.0, volume_24h=50.0,
        match_start_iso="2026-04-15T23:00:00Z", end_date_iso="",
        event_id="e", closed=False, resolved=False, accepting_orders=True,
    )


def test_log_skip_calls_logger_with_record():
    skipped_logger = MagicMock()
    market = _make_market()
    operational_writers.log_skip(skipped_logger, market, reason="exposure_cap_reached")
    assert skipped_logger.log.called
    record = skipped_logger.log.call_args.args[0]
    assert record.skip_reason == "exposure_cap_reached"
    assert record.slug == "m1"


def test_log_skip_swallows_oserror():
    skipped_logger = MagicMock()
    skipped_logger.log.side_effect = OSError("disk full")
    operational_writers.log_skip(skipped_logger, _make_market(), reason="x")
    # raise etmemeli


def test_log_equity_snapshot_writes_snapshot():
    portfolio = MagicMock()
    portfolio.positions = {}
    portfolio.bankroll = 1000.0
    portfolio.realized_pnl = 0.0
    equity_logger = MagicMock()
    operational_writers.log_equity_snapshot(portfolio, equity_logger)
    assert equity_logger.log.called
    snap = equity_logger.log.call_args.args[0]
    assert snap.bankroll == 1000.0
    assert snap.invested == 0.0
