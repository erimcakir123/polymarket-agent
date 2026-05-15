"""entry_processor totals/moneyline Position field wiring.

SPEC-K spread/totals enrichment 2026-05-15 rollback (Faz 4/10) ile silindi.
NBA totals exit (SPEC-J) için total_line/total_side hala question'dan parse edilir.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.models.enums import TotalSide
from src.models.market import MarketData
from src.models.signal import Signal
from src.orchestration.entry_processor import EntryProcessor
from src.strategy.entry.gate import GateResult


def _make_market(sports_market_type: str, question: str, slug: str):
    return MarketData(
        condition_id="0xabc",
        slug=slug,
        question=question,
        sport_tag="basketball/nba",
        yes_token_id="y", no_token_id="n",
        yes_price=0.55, no_price=0.45,
        liquidity=50000, volume_24h=10000,
        tags=[],
        end_date_iso="2026-04-14T00:00:00Z",
        event_id="e123",
        match_start_iso="2026-04-14T00:00:00Z",
        sports_market_type=sports_market_type,
    )


def _make_signal():
    return Signal(
        condition_id="0xabc",
        direction="BUY_YES",
        market_price=0.55,
        anchor_probability=0.65,
        edge=0.10,
        bookmaker_prob=0.65,
        num_bookmakers=4.0,
        has_sharp=True,
        confidence="A",
        entry_reason="normal",
        size_usdc=20.0,
    )


def _make_deps(captured_positions: list):
    """Deps that capture Position passed to portfolio.add_position."""
    portfolio = MagicMock()
    portfolio.bankroll = 1000.0
    portfolio.realized_pnl = 0.0
    portfolio.positions = {}
    portfolio.count.return_value = 0
    portfolio.total_invested.return_value = 0.0

    def _capture_add(pos):
        captured_positions.append(pos)
        return True
    portfolio.add_position.side_effect = _capture_add

    gate_config = SimpleNamespace(
        max_positions=50,
        max_exposure_pct=0.5,
        hard_cap_overflow_pct=0.02,
        min_entry_size_pct=0.015,
    )
    deps = SimpleNamespace(
        state=SimpleNamespace(
            config=SimpleNamespace(mode=SimpleNamespace(value="dry_run")),
            portfolio=portfolio,
        ),
        scanner=MagicMock(),
        stock=MagicMock(),
        gate=MagicMock(),
        skipped_logger=MagicMock(),
        bot_status_writer=MagicMock(),
        equity_logger=MagicMock(),
        executor=MagicMock(),
        trade_logger=MagicMock(),
        price_feed=None,
    )
    deps.gate.config = gate_config
    deps.executor.place_order.return_value = {"status": "simulated", "price": 0.55}
    return deps


def test_totals_market_position_has_total_line_and_side() -> None:
    """Totals market'ten Position oluşunca total_line + total_side OVER olmalı."""
    market = _make_market(
        sports_market_type="totals",
        question="Lakers vs Celtics o/u 215.5",
        slug="nba-lal-bos-total-over-215pt5",
    )
    signal = _make_signal()
    captured: list = []
    deps = _make_deps(captured)
    deps.gate.run.return_value = [GateResult("0xabc", signal, "", "")]

    EntryProcessor(deps).process_markets([market])

    assert len(captured) == 1
    pos = captured[0]
    assert pos.total_line == 215.5
    assert pos.total_side == TotalSide.OVER
    assert pos.sports_market_type.value == "totals"


def test_moneyline_market_position_has_no_totals_fields() -> None:
    """Moneyline Position'da totals alanları None kalmalı (regression)."""
    market = _make_market(
        sports_market_type="moneyline",
        question="Will Lakers beat Celtics?",
        slug="nba-lal-bos-2026-04-13",
    )
    signal = _make_signal()
    captured: list = []
    deps = _make_deps(captured)
    deps.gate.run.return_value = [GateResult("0xabc", signal, "", "")]

    EntryProcessor(deps).process_markets([market])

    assert len(captured) == 1
    pos = captured[0]
    assert pos.total_line is None
    assert pos.total_side is None
    assert pos.sports_market_type.value == "moneyline"
