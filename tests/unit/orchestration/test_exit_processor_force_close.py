"""Force-close integration testleri (SPEC-force-close 2026-05-27).

ExitProcessor.run_light force-close path:
  1. Normal exit chain None döndü.
  2. Pozisyon -%50+ zararda (deep-loss gate).
  3. Time-based timeout doldu (ESPN None → time-based fallback).
  4. Bid book walk full slippage bypass → realize.

Senaryolar:
  T1: bid var → realize @ bid price (FORCE_CLOSE_TIME)
  T2: bid yok → realize @ 0 (FORCE_CLOSE_NO_BIDS, tam kayıp)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.config.settings import AppConfig
from src.models.position import Position
from src.orchestration.exit_processor import ExitProcessor


def _make_deps_and_pos(orderbook_bids: list[dict]):
    """Common setup: deps mock + 1 deep-loss position 250min old + ESPN None.

    Pozisyon: nba_match_winner, 250 dk önce başlamış → elapsed > 180dk timeout.
    Entry $0.50 × 100 share = $50, current $0.005 → -%99 pnl (deep-loss gate aşılır).
    Time-based path tetiklenir (ESPN None).
    """
    deps = MagicMock()

    cfg = AppConfig()
    # market_type "moneyline" için 60dk timeout — pozisyon 250dk önce başlamış,
    # time-based path kesin tetiklenir.
    cfg.risk.force_close_timeouts = {"moneyline": 60, "default": 300}
    deps.state.config = cfg

    # Position: 250 dakika önce başlamış (timeout=60'tan büyük).
    start = (datetime.now(timezone.utc) - timedelta(minutes=250)).isoformat()
    pos = Position(
        condition_id="cid_fc1",
        token_id="tok_fc1",
        direction="BUY_YES",
        entry_price=0.50,
        size_usdc=50.0,
        shares=100.0,
        current_price=0.005,  # -%99 (deep-loss gate aşıldı: -%50)
        anchor_probability=0.55,
        event_id="espn_evt_1",
        slug="test-nba-game-force-close",
        sport_tag="nba",
        question="Team A vs Team B",
        match_start_iso=start,
    )
    # SportsMarketType ayarla — moneyline default zaten ama açıkça set edelim.
    from src.models.enums import SportsMarketType
    pos.sports_market_type = SportsMarketType.MONEYLINE

    deps.state.portfolio.positions = {"cid_fc1": pos}
    deps.state.portfolio.bankroll = 1000.0

    # Executor: book fetch full bypass için _fetch_book mock.
    deps.executor._fetch_book = MagicMock(
        return_value={"asks": [], "bids": orderbook_bids},
    )

    # ESPN None → time-based path zorlanır.
    deps.espn_client = MagicMock()
    deps.espn_client.get_match_status = MagicMock(return_value=None)

    # price_feed unsubscribe çağrılır — None bırakırsak _finalize_full_exit
    # `if self.deps.price_feed is not None` guard ile atlar (test path basit).
    deps.price_feed = None

    # portfolio.remove_position realized_pnl yakalamak için.
    captured = {"realized": None, "exit_reason": None, "exit_price": None}

    def fake_remove(_cid, realized_pnl_usdc):
        captured["realized"] = realized_pnl_usdc
        # Pozisyonu portfolio'dan da düşür (run_light loop için).
        deps.state.portfolio.positions.pop(_cid, None)

    deps.state.portfolio.remove_position = MagicMock(side_effect=fake_remove)

    def fake_update_on_exit(_cid, payload):
        captured["exit_reason"] = payload.get("exit_reason")
        captured["exit_price"] = payload.get("exit_price")
        return True

    deps.trade_logger.update_on_exit = MagicMock(side_effect=fake_update_on_exit)

    return deps, pos, captured


def _stub_monitor_none(monkeypatch):
    """Normal exit chain'i nötralize et — force-close path izole test edilsin.

    Force-close zaten "normal exit None döndü" varsayımı altında çalışır; bu
    stub o varsayımı testte garantiler.
    """
    import src.strategy.exit.monitor as monitor_mod
    from src.strategy.exit.monitor import FavoredTransition, MonitorResult

    def fake_eval(*_args, **_kw):
        return MonitorResult(
            exit_signal=None,
            fav_transition=FavoredTransition(),
            elapsed_pct=0.86,
        )
    monkeypatch.setattr(monitor_mod, "evaluate", fake_eval)


def test_force_close_with_bids_realizes_at_bid_price(monkeypatch):
    """T1: Bid var → realize @ bid avg_price, exit_reason=force_close_time_expired."""
    _stub_monitor_none(monkeypatch)
    bids = [{"price": 0.01, "size": 200}]
    deps, pos, captured = _make_deps_and_pos(orderbook_bids=bids)

    ep = ExitProcessor(deps)
    ep.run_light()

    # Pozisyon portfolio'dan kaldırıldı.
    assert "cid_fc1" not in deps.state.portfolio.positions
    # Exit reason force-close time-expired.
    assert captured["exit_reason"] == "force_close_time_expired"
    # Realized = filled(100) * 0.01 - size(50) = 1 - 50 = -49.
    assert captured["realized"] == pytest.approx(-49.0, abs=0.5)
    assert captured["exit_price"] == pytest.approx(0.01, abs=0.001)


def test_force_close_without_bids_holds_position(monkeypatch):
    """T2 (2026-06-01 revize): Bid yok → pozisyon HOLD (0'a sıfırlamaz).

    Kullanıcı kararı: fiyat 0'a gitmediyse 0'a satmak aptal.
    Bid yoksa Polymarket resolve detector eninde sonunda devreye girer.
    """
    _stub_monitor_none(monkeypatch)
    deps, pos, captured = _make_deps_and_pos(orderbook_bids=[])

    ep = ExitProcessor(deps)
    ep.run_light()

    # Pozisyon AÇIK kalır, finalize çağrılmaz (captured None'larla başlar, dolmaz).
    assert "cid_fc1" in deps.state.portfolio.positions
    assert captured["exit_reason"] is None
    assert captured["realized"] is None
