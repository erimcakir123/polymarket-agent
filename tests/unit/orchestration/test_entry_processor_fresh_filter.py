"""EntryProcessor.run_heavy — fresh_only active_sport filtresi (TDD §EP-1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.orchestration.entry_processor import EntryProcessor


# ── Minimal stubs ────────────────────────────────────────────────────────────

@dataclass
class _GateConfig:
    active_sports: list[str] = field(default_factory=lambda: ["basketball_nba"])
    max_positions: int = 50
    max_exposure_pct: float = 0.20
    hard_cap_overflow_pct: float = 0.02
    min_entry_size_pct: float = 0.015


@dataclass
class _StockConfig:
    jit_batch_multiplier: int = 3


def _make_market(condition_id: str, sport_tag: str, match_start_iso: str):
    m = MagicMock()
    m.condition_id = condition_id
    m.sport_tag = sport_tag
    m.match_start_iso = match_start_iso
    m.event_id = None
    return m


def _build_deps(
    scan_markets: list,
    gate_returns: list | None = None,
    active_sports: list[str] | None = None,
    max_positions: int = 50,
) -> MagicMock:
    deps = MagicMock()

    gate_cfg = _GateConfig(
        active_sports=active_sports or ["basketball_nba"],
        max_positions=max_positions,
    )
    deps.gate.config = gate_cfg
    deps.gate.run.return_value = gate_returns or []

    deps.scanner.scan.return_value = scan_markets

    stock_cfg = _StockConfig()
    deps.stock.config = stock_cfg
    deps.stock.has.return_value = False
    deps.stock.top_n_by_match_start.return_value = []

    portfolio = MagicMock()
    portfolio.count.return_value = 0
    portfolio.positions = {}
    portfolio.bankroll = 1000.0
    portfolio.total_invested.return_value = 0.0
    deps.state.portfolio = portfolio
    deps.state.config.mode.value = "dry_run"

    return deps


# ── Tests ────────────────────────────────────────────────────────────────────

def test_fresh_only_excludes_inactive_sports():
    """Soccer (earlier match_start) + NBA: only NBA reaches process_markets."""
    soccer_early = _make_market("soc-1", "soccer", "2026-04-26T12:00:00")
    soccer_mid   = _make_market("soc-2", "soccer", "2026-04-26T14:00:00")
    nba_late     = _make_market("nba-1", "nba",    "2026-04-26T17:30:00")

    deps = _build_deps([soccer_early, soccer_mid, nba_late])
    ep = EntryProcessor(deps)
    ep.process_markets = MagicMock()

    ep.run_heavy()

    # stock_batch boş → process_markets sadece fresh_batch için çağrılır
    assert ep.process_markets.call_count == 1
    called_markets = ep.process_markets.call_args[0][0]
    cids = [m.condition_id for m in called_markets]
    assert "nba-1" in cids, "NBA market fresh_batch'e girmeliydi"
    assert "soc-1" not in cids, "Soccer market fresh_batch'e girmemeli"
    assert "soc-2" not in cids, "Soccer market fresh_batch'e girmemeli"


def test_fresh_only_nba_sorted_by_match_start():
    """Birden fazla NBA market: match_start ASC sıralı gelir."""
    nba_late  = _make_market("nba-late",  "nba", "2026-04-26T22:30:00")
    nba_early = _make_market("nba-early", "nba", "2026-04-26T17:30:00")
    nba_mid   = _make_market("nba-mid",   "nba", "2026-04-26T20:00:00")

    deps = _build_deps([nba_late, nba_early, nba_mid])
    ep = EntryProcessor(deps)
    ep.process_markets = MagicMock()

    ep.run_heavy()

    assert ep.process_markets.call_count == 1
    called_markets = ep.process_markets.call_args[0][0]
    starts = [m.match_start_iso for m in called_markets]
    assert starts == sorted(starts), "NBA marketler match_start ASC sıralı olmalı"


def test_fresh_only_empty_when_no_active_sports_in_scan():
    """Scan sadece inactive sport döndürüyorsa fresh_batch boş → process_markets çağrılmaz."""
    soccer = _make_market("soc-1", "soccer", "2026-04-26T12:00:00")

    deps = _build_deps([soccer])
    ep = EntryProcessor(deps)
    ep.process_markets = MagicMock()

    ep.run_heavy()

    ep.process_markets.assert_not_called()


def test_fresh_only_respects_stock_has():
    """Stock'ta olan NBA market fresh_only'e dahil edilmez."""
    nba_in_stock = _make_market("nba-stock", "nba", "2026-04-26T17:30:00")
    nba_fresh    = _make_market("nba-fresh", "nba", "2026-04-26T20:00:00")

    deps = _build_deps([nba_in_stock, nba_fresh])
    deps.stock.has.side_effect = lambda cid: cid == "nba-stock"
    ep = EntryProcessor(deps)
    ep.process_markets = MagicMock()

    ep.run_heavy()

    assert ep.process_markets.call_count == 1
    called_markets = ep.process_markets.call_args[0][0]
    cids = [m.condition_id for m in called_markets]
    assert "nba-fresh" in cids
    assert "nba-stock" not in cids


def test_fresh_batch_capped_at_still_empty_times_multiplier():
    """fresh_batch max = still_empty × jit_mult (burada 50 × 3 = 150)."""
    # 200 NBA market oluştur — sadece 150 alınmalı
    markets = [
        _make_market(f"nba-{i}", "nba", f"2026-04-26T{17+i//60:02d}:{i%60:02d}:00")
        for i in range(200)
    ]
    deps = _build_deps(markets)
    ep = EntryProcessor(deps)
    ep.process_markets = MagicMock()

    ep.run_heavy()

    assert ep.process_markets.call_count == 1
    called_markets = ep.process_markets.call_args[0][0]
    assert len(called_markets) == 150  # 50 × 3
