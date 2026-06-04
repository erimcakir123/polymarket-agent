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

    # SPEC-Z17: tek truth = trade_event_log; exit verisini event'ten yakala.
    def fake_append_final(condition_id, exit_price, exit_reason, **_kw):
        captured["exit_reason"] = exit_reason
        captured["exit_price"] = exit_price

    deps.trade_event_log.append_final = MagicMock(side_effect=fake_append_final)

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


def test_force_close_emits_alert_no_automatic_exit_with_bids(monkeypatch, tmp_path):
    """T1 (2026-06-01 revize): Bid var olsa BİLE otomatik exit YOK.

    Kullanıcı kararı: 'Otomatik çık deme. Kırmızı border + bildirim
    gelsin, ben karar veririm. Polymarket bug olsa yanlış exit yapmayalım.'
    """
    _stub_monitor_none(monkeypatch)
    from src.infrastructure.persistence import force_close_alerts
    monkeypatch.setattr(
        force_close_alerts, "_DEFAULT_PATH", tmp_path / "fc_alerts.json",
    )
    bids = [{"price": 0.01, "size": 200}]
    deps, pos, captured = _make_deps_and_pos(orderbook_bids=bids)

    ep = ExitProcessor(deps)
    ep.run_light()

    # Pozisyon AÇIK kalır — bid olsa bile satılmaz.
    assert "cid_fc1" in deps.state.portfolio.positions
    assert captured["exit_reason"] is None
    assert captured["realized"] is None
    # Alert store kaydı oluştu (dashboard kırmızı border için).
    assert ep._fc_alerts.is_alerted("cid_fc1")


def test_force_close_alert_idempotent(monkeypatch, tmp_path):
    """T2: Aynı pozisyon için 2. cycle'da Telegram spam YOK (alert flag set)."""
    _stub_monitor_none(monkeypatch)
    from src.infrastructure.persistence import force_close_alerts
    monkeypatch.setattr(
        force_close_alerts, "_DEFAULT_PATH", tmp_path / "fc_alerts.json",
    )
    deps, pos, _ = _make_deps_and_pos(orderbook_bids=[{"price": 0.05, "size": 200}])

    ep = ExitProcessor(deps)
    ep.run_light()  # 1. cycle — alarm fire
    first_at = ep._fc_alerts._state["cid_fc1"]

    ep.run_light()  # 2. cycle — flag set, idempotent
    second_at = ep._fc_alerts._state["cid_fc1"]
    assert first_at == second_at  # timestamp değişmedi


def test_force_close_without_bids_also_alerts_no_exit(monkeypatch, tmp_path):
    """T3: Bid yokken de davranış aynı — alarm + hold."""
    _stub_monitor_none(monkeypatch)
    from src.infrastructure.persistence import force_close_alerts
    monkeypatch.setattr(
        force_close_alerts, "_DEFAULT_PATH", tmp_path / "fc_alerts.json",
    )
    deps, pos, captured = _make_deps_and_pos(orderbook_bids=[])

    ep = ExitProcessor(deps)
    ep.run_light()

    assert "cid_fc1" in deps.state.portfolio.positions
    assert captured["exit_reason"] is None
    assert ep._fc_alerts.is_alerted("cid_fc1")
