"""Dashboard HTTP endpoint'leri — thin handlers.

Her handler max ~15 satır. Sadece `readers.*` ve `computed.*` çağırır,
iş mantığı yok. ARCH_GUARD Kural 1: infrastructure/domain/strategy/
orchestration import YOK.
"""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from src.config.settings import AppConfig
from src.presentation.dashboard import computed, computed_sport_health, readers

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
            session_start_iso=readers.read_session_start(logs_dir),
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
        # Balance/P&L/Peak/Risk → tek kaynak: audit/equity_history.jsonl (SPEC-Z18).
        # positions.json'a BAKILMAZ — reboot dosyayı arşive taşıyınca sıfır döner.
        # Slot sayısı açık pozisyon listesinden alınır (positions.json).
        session_balance = readers.read_balance_from_session(logs_dir)
        blob = readers.read_positions(logs_dir)
        # realized_pnl widget'ı exited tab ile aynı kaynaktan (trade_history.jsonl)
        # hesaplanır — reboot-scoped tutarlılık.
        trades = readers.read_trades(logs_dir, n=1000)
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
        positions = readers.read_positions(logs_dir).get("positions", {})
        alerted = readers.read_force_close_alerts(logs_dir)
        realistic = readers.read_realistic_exit_estimates(logs_dir)
        for cid, pos in positions.items():
            if isinstance(pos, dict):
                pos["force_close_alert"] = cid in alerted
                if cid in realistic:
                    pos["realistic_exit"] = realistic[cid]
        return jsonify(positions)

    @app.route("/api/trades")
    def api_trades():
        # Feed exited tab + per-trade PnL chart source: full close + partial
        # scale-out event'leri flatten (her exit ayri event). ?n=5000.
        n = request.args.get("n", 100, type=int)
        trades = readers.read_trades(logs_dir, n=n)
        return jsonify(computed.exit_events(trades))

    @app.route("/api/trades/positions")
    def api_trades_positions():
        # Log modal source: pozisyon-bazli (her bahis = 1 kayit). partial/final
        # ic ice (partial_exits) kalir — exit_events gibi flatten ETMEZ. Boylece
        # modal her maci/market'i tek baslik, scale-out'lari alt-event gosterir.
        n = request.args.get("n", 100, type=int)
        trades = readers.read_trades(logs_dir, n=n)
        closed = [
            t for t in trades
            if t.get("exit_price") is not None or (t.get("partial_exits") or [])
        ]
        closed.sort(
            key=lambda t: t.get("exit_timestamp") or t.get("entry_timestamp") or "",
            reverse=True,
        )
        return jsonify(closed)

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
        # Plan 1.D Task 4: branş kartına isabet alt-satırı için model_health
        # JSON'unu ekle. Dosya yoksa sport_health boş dict olur (graceful).
        health_blob = readers.read_model_health(logs_dir)
        payload = computed.sport_roi_treemap(trades)
        payload["sport_health"] = computed_sport_health.compute_sport_health_for_dashboard(health_blob)
        return jsonify(payload)

    @app.route("/api/calibration")
    def api_calibration():
        """Model dogruluk karnesi: bin basina (anchor, gercek win-rate, n).

        4 sezgisel kova:
          underdog (0.30-0.45) | hafif favori (0.45-0.65)
          net favori (0.65-0.80) | ezici favori (0.80-1.00)
        Yetersiz veri (< 10 trade) bin'leri "henuz veri yok" doner.
        """
        from src.presentation.dashboard import computed_calibration
        sport = request.args.get("sport", "all")
        trades = readers.read_trades(logs_dir, n=5000)
        return jsonify(computed_calibration.calibration_report(trades, sport))

    @app.route("/api/trades/history")
    def api_trades_history():
        offset = request.args.get("week_offset", 0, type=int)
        raw, label, has_older = readers.read_trades_by_week(logs_dir, offset)
        events = computed.exit_events(raw)
        return jsonify({
            "trades": events,
            "week_label": label,
            "week_offset": offset,
            "has_older": has_older,
            "total_in_week": len(events),
        })
