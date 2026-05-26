"""Dashboard HTTP endpoint'leri — thin handlers.

Her handler max ~15 satır. Sadece `readers.*` ve `computed.*` çağırır,
iş mantığı yok. ARCH_GUARD Kural 1: infrastructure/domain/strategy/
orchestration import YOK.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from src.config.settings import AppConfig
from src.presentation.dashboard import computed, readers

logger = logging.getLogger(__name__)


def _attach_replay_simulation(
    events: list[dict[str, Any]], logs_dir: Path,
) -> list[dict[str, Any]]:
    """Enrich exit_events with replay_simulation entries (key: cid+entry_ts)."""
    sim = readers.read_replay_simulation(logs_dir)
    if not sim:
        return events
    for ev in events:
        key = (ev.get("condition_id") or "", ev.get("entry_timestamp") or "")
        if key in sim:
            ev["replay_simulation"] = sim[key]
    return events


def register_routes(app: Flask, config: AppConfig, logs_dir: Path) -> None:
    """Flask app'e tüm endpoint'leri kaydet."""

    @app.route("/")
    def index():
        return render_template(
            "dashboard.html",
            mode=config.mode.value,
            initial_bankroll=config.initial_bankroll,
            max_positions=config.risk.max_positions,
        )

    @app.route("/api/status")
    def api_status():
        status = readers.read_bot_status(logs_dir)
        return jsonify({
            "mode": config.mode.value,
            "bot_alive": readers.bot_is_alive(logs_dir),
            "cycle": status.get("cycle"),
            "stage": status.get("stage"),
            "stage_at": status.get("stage_at"),
            "next_heavy_at": status.get("next_heavy_at"),
            "light_alive": status.get("light_alive", False),
        })

    @app.route("/api/summary")
    def api_summary():
        # Balance/P&L/Peak/Risk → session/equity_history.jsonl + audit trades.
        # realized_pnl widget'ı exit_events tab ile aynı kaynaktan (audit
        # trade_history) hesaplanır — portfolio.realized_pnl drift'ine bağışık.
        # Slot sayısı açık pozisyon listesinden alınır (positions.json).
        session_balance = readers.read_balance_from_session(logs_dir)
        trades = readers.read_trades(logs_dir, n=1000)
        blob = readers.read_positions(logs_dir)
        cb = config.circuit_breaker
        return jsonify({
            "equity": computed.equity_summary_from_session(
                session_balance, config.initial_bankroll, trades=trades,
            ),
            "slots": computed.slots_summary(blob, config.risk.max_positions),
            "loss_protection": computed.loss_protection_from_session(
                session_balance, config.initial_bankroll,
                stop_at_pct=abs(cb.daily_max_loss_pct) * 100.0,
                safe_drawdown_pct=cb.safe_drawdown_pct,
                warn_drawdown_pct=cb.warn_drawdown_pct,
            ),
        })

    @app.route("/api/equity_history")
    def api_equity_history():
        return jsonify(readers.read_equity_history(logs_dir, n=100))

    @app.route("/api/positions")
    def api_positions():
        return jsonify(readers.read_positions(logs_dir).get("positions", {}))

    @app.route("/api/trades")
    def api_trades():
        trades = readers.read_trades(logs_dir, n=100)
        # Exited tab source: full close + partial scale-out event'leri flatten.
        events = computed.exit_events(trades)
        return jsonify(_attach_replay_simulation(events, logs_dir))

    @app.route("/api/skipped")
    def api_skipped():
        return jsonify(readers.read_skipped(logs_dir, n=100))

    @app.route("/api/stock")
    def api_stock():
        return jsonify(readers.read_eligible_queue(logs_dir))

    @app.route("/api/stats")
    def api_stats():
        trades = readers.read_trades(logs_dir, n=1000)
        return jsonify(computed.win_loss(trades))

    @app.route("/api/sport_roi")
    def api_sport_roi():
        trades = readers.read_trades(logs_dir, n=5000)
        return jsonify(computed.sport_roi_treemap(trades))

    @app.route("/api/trades/history")
    def api_trades_history():
        offset = request.args.get("month_offset", 0, type=int)
        raw, label, has_older = readers.read_trades_by_month(logs_dir, offset)
        events = _attach_replay_simulation(computed.exit_events(raw), logs_dir)
        return jsonify({
            "trades": events,
            "month_label": label,
            "month_offset": offset,
            "has_older": has_older,
            "total_in_month": len(events),
        })
