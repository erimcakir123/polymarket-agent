"""Polymarket auto-resolution detector integration testleri (2026-05-28).

ExitProcessor light cycle her N tick'te bir gamma'ya pozisyon condition_id ile
sorgu atar; closed + uma resolved ise owned-side payout ile exit eder.

Senaryolar:
  - resolved market → exit @ payout, reason=resolved
  - unresolved market → exit yok
  - throttling: gamma her tick degil, her N tick'te bir
  - gamma exception → graceful skip (crash yok)
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.config.settings import AppConfig
from src.models.position import Position
from src.orchestration.exit_processor import ExitProcessor


def _make_deps_and_pos(every_n_ticks: int = 60):
    """Common setup: normal exit chain None, force-close None → izole resolution path."""
    deps = MagicMock()
    cfg = AppConfig()
    cfg.risk.polymarket_resolution_check_every_n_ticks = every_n_ticks
    cfg.risk.force_close_timeouts = {}  # force-close devre disi
    deps.state.config = cfg

    pos = Position(
        condition_id="cid_res1",
        token_id="tok_res1",
        direction="BUY_YES",
        entry_price=0.30,
        size_usdc=30.0,
        shares=100.0,
        current_price=0.05,
        anchor_probability=0.55,
        event_id="evt_1",
        slug="wnba-test-resolution",
        sport_tag="wnba",
        question="Team A vs Team B",
    )
    deps.state.portfolio.positions = {"cid_res1": pos}
    deps.state.portfolio.bankroll = 1000.0

    deps.price_feed = None
    deps.gamma_client = MagicMock()

    captured = {"realized": None, "exit_reason": None, "exit_price": None}

    def fake_remove(_cid, realized_pnl_usdc):
        captured["realized"] = realized_pnl_usdc
        deps.state.portfolio.positions.pop(_cid, None)

    deps.state.portfolio.remove_position = MagicMock(side_effect=fake_remove)

    def fake_update_on_exit(_cid, payload):
        captured["exit_reason"] = payload.get("exit_reason")
        captured["exit_price"] = payload.get("exit_price")
        return True

    deps.trade_logger.update_on_exit = MagicMock(side_effect=fake_update_on_exit)

    return deps, pos, captured


def _stub_monitor_none(monkeypatch):
    """Normal exit chain'i nötralize et — resolution path izole test edilsin."""
    import src.strategy.exit.monitor as monitor_mod
    from src.strategy.exit.monitor import FavoredTransition, MonitorResult

    def fake_eval(*_args, **_kw):
        return MonitorResult(
            exit_signal=None,
            fav_transition=FavoredTransition(),
            elapsed_pct=0.50,
        )
    monkeypatch.setattr(monitor_mod, "evaluate", fake_eval)


def test_resolved_market_fires_exit(monkeypatch) -> None:
    """Gamma closed+resolved döndü → exit @ payout, reason=resolved."""
    _stub_monitor_none(monkeypatch)
    deps, pos, captured = _make_deps_and_pos(every_n_ticks=1)
    # BUY_YES, prices=['1','0'] → YES won → exit_price = 1.0
    deps.gamma_client.fetch_closed_market_by_condition = MagicMock(return_value={
        "closed": True,
        "umaResolutionStatus": "resolved",
        "outcomePrices": '["1", "0"]',
    })

    ep = ExitProcessor(deps)
    ep.run_light()

    assert "cid_res1" not in deps.state.portfolio.positions
    assert captured["exit_reason"] == "resolved"
    assert captured["exit_price"] == pytest.approx(1.0, abs=0.001)
    # Realized = shares*payout - size = 100*1.0 - 30 = 70
    assert captured["realized"] == pytest.approx(70.0, abs=0.5)


def test_unresolved_market_no_exit(monkeypatch) -> None:
    """Gamma None / closed=false → exit yok, pozisyon korunur."""
    _stub_monitor_none(monkeypatch)
    deps, pos, captured = _make_deps_and_pos(every_n_ticks=1)
    deps.gamma_client.fetch_closed_market_by_condition = MagicMock(return_value=None)

    ep = ExitProcessor(deps)
    ep.run_light()

    assert "cid_res1" in deps.state.portfolio.positions
    assert captured["exit_reason"] is None


def test_check_throttled_to_every_n_ticks(monkeypatch) -> None:
    """N=3 → gamma sadece 1, 4, 7. cycle'lar'da çağrılır (tick 1 trigger, tick 2-3 skip)."""
    _stub_monitor_none(monkeypatch)
    deps, pos, captured = _make_deps_and_pos(every_n_ticks=3)
    deps.gamma_client.fetch_closed_market_by_condition = MagicMock(return_value=None)

    ep = ExitProcessor(deps)
    # 6 light tick — gamma 2 kez çağrılmalı (tick 1 ve tick 4).
    for _ in range(6):
        ep.run_light()

    assert deps.gamma_client.fetch_closed_market_by_condition.call_count == 2


def test_gamma_failure_does_not_crash(monkeypatch) -> None:
    """Gamma exception (gamma_client method exception fırlattı) → graceful skip."""
    _stub_monitor_none(monkeypatch)
    deps, pos, captured = _make_deps_and_pos(every_n_ticks=1)
    deps.gamma_client.fetch_closed_market_by_condition = MagicMock(
        side_effect=RuntimeError("network down"),
    )

    ep = ExitProcessor(deps)
    ep.run_light()  # crash etmemeli

    # Pozisyon hala acik
    assert "cid_res1" in deps.state.portfolio.positions
    assert captured["exit_reason"] is None


def test_feature_disabled_when_ticks_zero(monkeypatch) -> None:
    """polymarket_resolution_check_every_n_ticks=0 → gamma asla çağrılmaz."""
    _stub_monitor_none(monkeypatch)
    deps, pos, captured = _make_deps_and_pos(every_n_ticks=0)
    deps.gamma_client.fetch_closed_market_by_condition = MagicMock()

    ep = ExitProcessor(deps)
    for _ in range(10):
        ep.run_light()

    assert deps.gamma_client.fetch_closed_market_by_condition.call_count == 0


def test_no_gamma_client_does_not_crash(monkeypatch) -> None:
    """deps.gamma_client None → feature devre disi, crash yok (backwards-compat)."""
    _stub_monitor_none(monkeypatch)
    deps, pos, captured = _make_deps_and_pos(every_n_ticks=1)
    deps.gamma_client = None

    ep = ExitProcessor(deps)
    ep.run_light()  # crash etmemeli

    assert "cid_res1" in deps.state.portfolio.positions


def test_buy_no_won_resolution(monkeypatch) -> None:
    """BUY_NO + prices=['0','1'] → NO won → exit @ 1.0."""
    _stub_monitor_none(monkeypatch)
    deps, pos, captured = _make_deps_and_pos(every_n_ticks=1)
    pos.direction = "BUY_NO"
    pos.entry_price = 0.40
    pos.size_usdc = 40.0
    deps.gamma_client.fetch_closed_market_by_condition = MagicMock(return_value={
        "closed": True,
        "umaResolutionStatus": "resolved",
        "outcomePrices": '["0", "1"]',
    })

    ep = ExitProcessor(deps)
    ep.run_light()

    assert "cid_res1" not in deps.state.portfolio.positions
    assert captured["exit_reason"] == "resolved"
    assert captured["exit_price"] == pytest.approx(1.0, abs=0.001)
    # Realized = shares*payout - size = 100*1.0 - 40 = 60
    assert captured["realized"] == pytest.approx(60.0, abs=0.5)
