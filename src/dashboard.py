"""Flask web dashboard — read-only portfolio monitoring."""
from __future__ import annotations
import json
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from src.trade_logger import TradeLogger

DASHBOARD_HTML = Path(__file__).parent.parent / "templates" / "dashboard.html"
IMAGE_DIR = Path(__file__).parent.parent / "İmage"
BUDGET_FILE = Path("logs/ai_budget.json")
POSITIONS_FILE = Path("logs/positions.json")
STATUS_FILE = Path("logs/bot_status.json")
STOCK_FILE = Path("logs/candidate_stock.json")


def create_app(
    trades_file: str = "logs/trades.jsonl",
    portfolio_file: str = "logs/portfolio.jsonl",
    performance_file: str = "logs/performance.jsonl",
) -> Flask:
    app = Flask(__name__)
    trade_log = TradeLogger(trades_file)
    portfolio_log = TradeLogger(portfolio_file)
    perf_log = TradeLogger(performance_file)

    @app.route("/")
    def index():
        if DASHBOARD_HTML.exists():
            return DASHBOARD_HTML.read_text(encoding="utf-8")
        return "<h1>Polymarket Agent Dashboard</h1><p>Template not found.</p>"

    @app.route("/images/<path:filename>")
    def serve_image(filename):
        return send_from_directory(str(IMAGE_DIR.resolve()), filename)

    @app.route("/api/trades")
    def api_trades():
        return jsonify(trade_log.read_recent(100))

    @app.route("/api/portfolio")
    def api_portfolio():
        return jsonify(portfolio_log.read_recent(100))

    @app.route("/api/performance")
    def api_performance():
        return jsonify(perf_log.read_recent(100))

    @app.route("/api/positions")
    def api_positions():
        if POSITIONS_FILE.exists():
            try:
                data = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
                return jsonify(data)
            except (json.JSONDecodeError, OSError):
                pass
        return jsonify({})

    @app.route("/api/budget")
    def api_budget():
        if BUDGET_FILE.exists():
            try:
                data = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
                return jsonify(data)
            except (json.JSONDecodeError, OSError):
                pass
        return jsonify({"spent": 0.0, "limit": 0.0, "remaining": 0.0})

    @app.route("/api/slots")
    def api_slots():
        """Slot allocation breakdown for dashboard widget."""
        positions = {}
        if POSITIONS_FILE.exists():
            try:
                positions = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        # Count by category
        vs_count = 0
        fav_count = 0
        esports_count = 0
        live_dip_count = 0
        far_count = 0
        normal_count = 0
        pending_count = 0

        for pos in (positions.values() if isinstance(positions, dict) else []):
            if pos.get("pending_resolution"):
                pending_count += 1
                continue
            if pos.get("volatility_swing"):
                vs_count += 1
            elif pos.get("entry_reason") == "fav_time_gate":
                fav_count += 1
            elif pos.get("entry_reason") == "esports_early":
                esports_count += 1
            elif pos.get("entry_reason") == "live_dip":
                live_dip_count += 1
            elif pos.get("entry_reason") == "far":
                far_count += 1
            else:
                normal_count += 1

        # Load config for max values
        import yaml
        config_path = Path("config.yaml")
        max_positions = 15
        vs_reserved = 3
        far_max = 2
        try:
            if config_path.exists():
                cfg = yaml.safe_load(config_path.read_text()) or {}
                max_positions = cfg.get("risk", {}).get("max_positions", 15)
                vs_reserved = cfg.get("volatility_swing", {}).get("reserved_slots", 3)
                far_max = cfg.get("far", {}).get("max_slots", 2)
        except Exception:
            pass

        normal_max = max_positions - vs_reserved

        return jsonify({
            "normal": {"current": normal_count, "max": normal_max},
            "vs": {"current": vs_count, "max": vs_reserved},
            "fav": {"current": fav_count, "max": 3},
            "esports": {"current": esports_count, "max": 3},
            "live_dip": {"current": live_dip_count, "max": 2},
            "far": {"current": far_count, "max": far_max},
            "pending": pending_count,
            "total": normal_count + vs_count + fav_count + esports_count + live_dip_count + far_count,
        })

    @app.route("/api/stock")
    def api_stock():
        """Return candidate stock pipeline for dashboard."""
        if STOCK_FILE.exists():
            try:
                data = json.loads(STOCK_FILE.read_text(encoding="utf-8"))
                return jsonify(data)
            except (json.JSONDecodeError, OSError):
                pass
        return jsonify([])

    @app.route("/api/status")
    def api_status():
        if STATUS_FILE.exists():
            try:
                data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
                return jsonify(data)
            except (json.JSONDecodeError, OSError):
                pass
        return jsonify({"state": "offline", "step": ""})

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="127.0.0.1", port=5050, debug=False)
