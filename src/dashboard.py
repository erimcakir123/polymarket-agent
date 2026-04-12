"""Flask web dashboard -- read-only portfolio monitoring."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory

from src.config import AppConfig, load_config
from src.trade_logger import TradeLogger

DASHBOARD_HTML = Path(__file__).parent.parent / "templates" / "dashboard.html"
IMAGE_DIR = Path(__file__).parent.parent / "İmage"
BUDGET_FILE = Path("logs/ai_budget.json")
POSITIONS_FILE = Path("logs/positions.json")
STATUS_FILE = Path("logs/bot_status.json")
STOCK_FILE = Path("logs/candidate_stock.json")
REENTRY_POOL_FILE = Path("logs/reentry_pool.json")
EQUITY_SNAPSHOT_FILE = Path("logs/equity.json")


def create_app(
    trades_file: str = "logs/trades.jsonl",
    portfolio_file: str = "logs/portfolio.jsonl",
    performance_file: str = "logs/performance.jsonl",
    config: Optional[AppConfig] = None,
) -> Flask:
    if config is None:
        config = load_config()
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
        limit = request.args.get("limit", 500, type=int)
        offset = request.args.get("offset", 0, type=int)
        limit = min(limit, 2000)  # Cap to prevent abuse
        return jsonify(trade_log.read_recent_page(limit=limit, offset=offset))

    @app.route("/api/portfolio")
    def api_portfolio():
        return jsonify(portfolio_log.read_recent(100))

    @app.route("/api/equity")
    def api_equity():
        """Single source of truth for dashboard equity display.

        Reads the snapshot written by Portfolio.save_prices_to_disk() each
        cycle. Contains: initial, realized, unrealized, active_cost, cash,
        total_equity, hwm, positions, wins, losses, ts.

        Falls back to empty structure if snapshot missing (bot not started
        yet). Dashboard has its own client-side fallback as well.
        """
        if EQUITY_SNAPSHOT_FILE.exists():
            try:
                return jsonify(json.loads(EQUITY_SNAPSHOT_FILE.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return jsonify({})

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

        # Count by category -- unified pipeline (Normal + VS)
        vs_count = 0
        reentry_count = 0
        normal_count = 0
        pending_count = 0
        # Track entry_reason breakdown for info (not enforced)
        reason_breakdown: dict[str, int] = {}

        for pos in (positions.values() if isinstance(positions, dict) else []):
            if pos.get("pending_resolution"):
                pending_count += 1
                continue
            entry_reason = pos.get("entry_reason", "normal")
            if pos.get("volatility_swing"):
                vs_count += 1
            elif entry_reason.startswith("re_entry"):
                reentry_count += 1
            else:
                normal_count += 1
            # Track all entry reasons for breakdown display
            reason_breakdown[entry_reason] = reason_breakdown.get(entry_reason, 0) + 1

        # Count waiting reentry pool candidates
        reentry_pool_waiting = 0
        if REENTRY_POOL_FILE.exists():
            try:
                pool_data = json.loads(REENTRY_POOL_FILE.read_text(encoding="utf-8"))
                for cid in pool_data:
                    if cid not in positions:
                        reentry_pool_waiting += 1
            except (json.JSONDecodeError, OSError):
                pass

        # Unified pipeline: Normal + VS slots
        _cfg = config
        max_positions = _cfg.risk.max_positions
        vs_reserved = _cfg.volatility_swing.reserved_slots
        normal_max = max_positions - vs_reserved
        active_count = normal_count + vs_count + reentry_count

        return jsonify({
            "normal": {"current": normal_count, "max": normal_max},
            "vs": {"current": vs_count, "max": vs_reserved},
            "reentry": {"current": reentry_count, "max": 3, "waiting": reentry_pool_waiting},
            "pending": pending_count,
            "total": active_count,
            "max_total": max_positions,
            "entry_reasons": reason_breakdown,
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
                ai_prob = r.get("anchor_probability", r.get("ai_probability", 0))
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
        # Check if bot process is actually running
        pid_file = Path("logs/agent.pid")
        bot_alive = False
        if pid_file.exists():
            try:
                import subprocess
                pid = int(pid_file.read_text().strip())
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, timeout=5
                )
                bot_alive = str(pid) in result.stdout
            except (ValueError, Exception):
                pass

        if bot_alive and STATUS_FILE.exists():
            try:
                data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
                return jsonify(data)
            except (json.JSONDecodeError, OSError):
                pass
        return jsonify({"state": "offline", "step": ""})

    @app.route("/api/realized")
    def api_realized():
        rpath = Path("logs/realized_pnl.json")
        if not rpath.exists():
            return jsonify({"total": 0, "wins": 0, "losses": 0, "hwm": 0})
        try:
            return jsonify(json.loads(rpath.read_text(encoding="utf-8")))
        except Exception:
            return jsonify({"total": 0, "wins": 0, "losses": 0, "hwm": 0})

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="127.0.0.1", port=5050, debug=False)
