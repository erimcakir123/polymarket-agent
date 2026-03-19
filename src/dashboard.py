"""Flask web dashboard — read-only portfolio monitoring."""
from __future__ import annotations
import json
from pathlib import Path

from flask import Flask, jsonify

from src.trade_logger import TradeLogger

DASHBOARD_HTML = Path(__file__).parent.parent / "templates" / "dashboard.html"
BUDGET_FILE = Path("logs/ai_budget.json")


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

    @app.route("/api/trades")
    def api_trades():
        return jsonify(trade_log.read_recent(100))

    @app.route("/api/portfolio")
    def api_portfolio():
        return jsonify(portfolio_log.read_recent(100))

    @app.route("/api/performance")
    def api_performance():
        return jsonify(perf_log.read_recent(100))

    @app.route("/api/budget")
    def api_budget():
        if BUDGET_FILE.exists():
            try:
                data = json.loads(BUDGET_FILE.read_text())
                return jsonify(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return jsonify({"spent": 0.0, "limit": 0.0, "remaining": 0.0})

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="127.0.0.1", port=5050, debug=False)
