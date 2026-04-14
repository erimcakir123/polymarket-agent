"""Dashboard HTTP endpoint'leri — thin handlers.

Her handler max ~15 satır. Sadece `readers.*` ve `computed.*` çağırır,
iş mantığı yok. ARCH_GUARD Kural 1: infrastructure/domain/strategy/
orchestration import YOK.
"""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, render_template

from src.config.settings import AppConfig
from src.presentation.dashboard import computed, readers

logger = logging.getLogger(__name__)


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
            "last_cycle": status.get("last_cycle"),
            "last_cycle_at": status.get("last_cycle_at"),
            "reason": status.get("reason"),
        })

    @app.route("/api/summary")
    def api_summary():
        # Tek dosya okuma 3 computation'a paylaşılır → 3 ayrı endpoint'in
        # 5sn'de 3 kez positions.json'ı okuması yerine 1 kez.
        blob = readers.read_positions(logs_dir)
        history = readers.read_equity_history(logs_dir, n=500)
        cb = config.circuit_breaker
        return jsonify({
            "equity": computed.equity_summary(blob, config.initial_bankroll, history),
            "slots": computed.slots_summary(blob, config.risk.max_positions),
            "loss_protection": computed.loss_protection(
                blob, config.initial_bankroll,
                stop_at_pct=abs(cb.daily_max_loss_pct) * 100.0,
                safe_drawdown_pct=cb.safe_drawdown_pct,
                warn_drawdown_pct=cb.warn_drawdown_pct,
                equity_history=history,
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
        return jsonify(computed.closed_trades(trades))

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
