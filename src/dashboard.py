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
REENTRY_POOL_FILE = Path("logs/reentry_pool.json")


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
        # Read all trades so EXIT entries are never buried under HOLDs
        return jsonify(trade_log.read_all())

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
        live_dip_count = 0
        far_count = 0
        reentry_count = 0
        normal_count = 0
        pending_count = 0

        for pos in (positions.values() if isinstance(positions, dict) else []):
            if pos.get("pending_resolution"):
                pending_count += 1
                continue
            entry_reason = pos.get("entry_reason", "")
            if pos.get("volatility_swing"):
                vs_count += 1
            elif entry_reason.startswith("re_entry"):
                reentry_count += 1
            elif entry_reason == "fav_time_gate":
                fav_count += 1
            elif entry_reason == "live_dip":
                live_dip_count += 1
            elif entry_reason == "far":
                far_count += 1
            else:
                normal_count += 1

        # Count waiting reentry pool candidates
        reentry_pool_waiting = 0
        if REENTRY_POOL_FILE.exists():
            try:
                pool_data = json.loads(REENTRY_POOL_FILE.read_text(encoding="utf-8"))
                # Only count candidates NOT already in active positions
                for cid in pool_data:
                    if cid not in positions:
                        reentry_pool_waiting += 1
            except (json.JSONDecodeError, OSError):
                pass

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
            "fav": {"current": fav_count, "max": 5},
            "live_dip": {"current": live_dip_count, "max": 2},
            "far": {"current": far_count, "max": far_max},
            "reentry": {"current": reentry_count, "max": 3, "waiting": reentry_pool_waiting},
            "pending": pending_count,
            "total": normal_count + vs_count + fav_count + live_dip_count + far_count + reentry_count,
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

    @app.route("/api/api-usage")
    def api_api_usage():
        """Return API usage stats for dashboard."""
        from src.api_usage import get_usage
        return jsonify(get_usage())

    @app.route("/api/calibration")
    def api_calibration():
        """Return AI vs Bookmaker calibration data from match_outcomes.jsonl."""
        outcomes_file = Path("logs/match_outcomes.jsonl")
        if not outcomes_file.exists():
            return jsonify([])
        records = []
        for line in outcomes_file.read_text(encoding="utf-8").strip().split("\n"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                # Only include resolved outcomes that have both AI and bookmaker probs
                if not r.get("resolved"):
                    continue
                ai_prob = r.get("ai_probability", 0)
                book_prob = r.get("bookmaker_prob", 0)
                yes_won = r.get("yes_won")
                if yes_won is None:
                    continue
                records.append({
                    "ts": r.get("timestamp", ""),
                    "slug": r.get("slug", "")[:40],
                    "ai_prob": round(ai_prob, 4),
                    "book_prob": round(book_prob, 4) if book_prob > 0 else None,
                    "yes_won": yes_won,
                    "sport": r.get("sport_tag", ""),
                    "confidence": r.get("confidence", ""),
                    "pnl": r.get("pnl", 0),
                    "ai_correct": r.get("ai_correct"),
                })
            except json.JSONDecodeError:
                continue
        return jsonify(records)

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
