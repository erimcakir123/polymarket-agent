"""Self-improvement engine -- autoresearch-style experiment loop for betting strategy.

Reads calibration data, analyzes performance, proposes ONE parameter change,
tracks experiments in logs/experiments.tsv. Designed to be called by Claude Code
skill (uses Claude Code tokens, not API budget).

Inspired by: github.com/karpathy/autoresearch
"""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
CALIBRATION_FILE = Path("logs/calibration.jsonl")
PREDICTIONS_FILE = Path("logs/predictions.jsonl")
TRADES_FILE = Path("logs/trades.jsonl")
PORTFOLIO_FILE = Path("logs/portfolio.jsonl")
CONFIG_FILE = Path("config.yaml")
EXPERIMENTS_FILE = Path("logs/experiments.tsv")
REPORT_FILE = Path("logs/self_improve_report.md")

# Minimum resolved predictions before running analysis
MIN_RESOLVED = 15


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class CalibrationEntry:
    condition_id: str
    question: str
    ai_probability: float
    market_price_at_trade: float
    direction: str
    resolved_yes: bool
    ai_correct: bool
    prediction_error: float
    category: str
    confidence: str = ""
    resolved_at: str = ""


@dataclass
class AnalysisReport:
    """Complete performance analysis output."""
    total_predictions: int = 0
    resolved_predictions: int = 0
    win_rate: float = 0.0
    brier_score: float = 0.0
    avg_edge: float = 0.0
    avg_prediction_error: float = 0.0

    # Breakdowns
    by_category: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_confidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_edge_range: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Weaknesses identified
    weaknesses: list[str] = field(default_factory=list)

    # Proposed experiment
    proposed_param: str = ""
    proposed_old_value: Any = None
    proposed_new_value: Any = None
    proposed_reason: str = ""


# ---------------------------------------------------------------------------
# Core analysis functions
# ---------------------------------------------------------------------------
def load_calibration() -> list[CalibrationEntry]:
    """Load all resolved calibration entries."""
    entries = []
    if not CALIBRATION_FILE.exists():
        return entries
    for line in CALIBRATION_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            entries.append(CalibrationEntry(
                condition_id=d.get("condition_id", ""),
                question=d.get("question", ""),
                ai_probability=d.get("ai_probability", 0.5),
                market_price_at_trade=d.get("market_price_at_trade", 0.5),
                direction=d.get("direction", ""),
                resolved_yes=d.get("resolved_yes", False),
                ai_correct=d.get("ai_correct", False),
                prediction_error=d.get("prediction_error", 0.0),
                category=d.get("category", "unknown"),
                confidence=d.get("confidence", ""),
                resolved_at=d.get("resolved_at", ""),
            ))
        except (json.JSONDecodeError, KeyError):
            continue
    return entries


def load_trades() -> list[dict]:
    """Load trade log entries."""
    trades = []
    if not TRADES_FILE.exists():
        return trades
    for line in TRADES_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            trades.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return trades


def load_config() -> dict:
    """Load current config.yaml as dict."""
    import yaml
    if not CONFIG_FILE.exists():
        return {}
    return yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}


def brier_score(entries: list[CalibrationEntry]) -> float:
    """Calculate Brier score (lower = better calibration)."""
    if not entries:
        return 1.0
    total = 0.0
    for e in entries:
        outcome = 1.0 if e.resolved_yes else 0.0
        total += (e.ai_probability - outcome) ** 2
    return total / len(entries)


def win_rate(entries: list[CalibrationEntry]) -> float:
    """Percentage of correct predictions."""
    if not entries:
        return 0.0
    return sum(1 for e in entries if e.ai_correct) / len(entries)


def analyze_by_group(entries: list[CalibrationEntry], key_fn) -> dict[str, dict[str, Any]]:
    """Group entries by a key function and compute stats per group."""
    groups: dict[str, list[CalibrationEntry]] = {}
    for e in entries:
        k = key_fn(e)
        groups.setdefault(k, []).append(e)

    result = {}
    for k, group in sorted(groups.items()):
        result[k] = {
            "count": len(group),
            "win_rate": win_rate(group),
            "brier_score": brier_score(group),
            "avg_error": statistics.mean(e.prediction_error for e in group),
        }
    return result


def edge_range_key(e: CalibrationEntry) -> str:
    """Bucket edge into ranges."""
    edge = abs(e.ai_probability - e.market_price_at_trade)
    if edge < 0.05:
        return "0-5%"
    elif edge < 0.10:
        return "5-10%"
    elif edge < 0.15:
        return "10-15%"
    else:
        return "15%+"


# ---------------------------------------------------------------------------
# Experiment proposal engine
# ---------------------------------------------------------------------------

# Parameter search space -- each entry: (config_path, current_key, candidates, description)
PARAM_SPACE = [
    ("edge.min_edge", [0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.12, 0.15],
     "Minimum edge threshold to place a bet"),
    ("risk.stop_loss_pct", [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50],
     "Stop-loss percentage trigger"),
    ("scanner.max_duration_days", [3, 5, 7, 10, 14, 21],
     "Maximum days until market resolution"),
    ("scanner.min_liquidity", [2000, 3000, 5000, 8000, 10000, 15000],
     "Minimum market liquidity filter"),
    ("cycle.default_interval_min", [15, 20, 25, 30, 45],
     "Minutes between scan cycles"),
]


def get_nested(d: dict, path: str) -> Any:
    """Get nested dict value by dot path: 'edge.min_edge' -> d['edge']['min_edge']."""
    keys = path.split(".")
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def set_nested(d: dict, path: str, value: Any) -> None:
    """Set nested dict value by dot path."""
    keys = path.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def load_experiment_history() -> list[dict]:
    """Load past experiments from TSV."""
    experiments = []
    if not EXPERIMENTS_FILE.exists():
        return experiments
    lines = EXPERIMENTS_FILE.read_text(encoding="utf-8").strip().split("\n")
    if len(lines) <= 1:  # Header only
        return experiments
    header = lines[0].split("\t")
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) >= len(header):
            experiments.append(dict(zip(header, parts)))
    return experiments


def propose_experiment(report: AnalysisReport, config: dict) -> AnalysisReport:
    """Based on analysis, propose ONE parameter change."""
    history = load_experiment_history()
    tried_params = {e.get("parameter", ""): e.get("status", "") for e in history}

    # Priority 1: If win rate < 55%, focus on min_edge (filtering bad bets)
    if report.win_rate < 0.55 and report.resolved_predictions >= MIN_RESOLVED:
        current = get_nested(config, "edge.min_edge")
        if current is not None:
            # Try raising min_edge to filter out low-quality bets
            candidates = [v for v in PARAM_SPACE[0][1] if v > current]
            if candidates:
                new_val = candidates[0]  # Next higher value
                report.proposed_param = "edge.min_edge"
                report.proposed_old_value = current
                report.proposed_new_value = new_val
                report.proposed_reason = (
                    f"Win rate {report.win_rate:.0%} < 55%. "
                    f"Raising min_edge from {current} to {new_val} to filter weak bets."
                )
                return report


    # Priority 3: Check edge ranges -- if small-edge bets have low win rate
    small_edge = report.by_edge_range.get("0-5%", {})
    if small_edge and small_edge.get("count", 0) >= 3 and small_edge.get("win_rate", 1.0) < 0.50:
        current = get_nested(config, "edge.min_edge")
        if current is not None and current < 0.06:
            report.proposed_param = "edge.min_edge"
            report.proposed_old_value = current
            report.proposed_new_value = 0.06
            report.proposed_reason = (
                f"Small-edge bets (0-5%) win only {small_edge['win_rate']:.0%}. "
                f"Raising min_edge to 0.06 to cut unprofitable low-edge bets."
            )
            return report

    # Priority 4: Category-based -- if a category is consistently bad
    for cat, stats in report.by_category.items():
        if stats["count"] >= 5 and stats["win_rate"] < 0.40:
            report.proposed_param = f"CATEGORY_FILTER:{cat}"
            report.proposed_old_value = "included"
            report.proposed_new_value = "excluded"
            report.proposed_reason = (
                f"Category '{cat}' win rate is {stats['win_rate']:.0%} "
                f"over {stats['count']} predictions. Consider excluding."
            )
            return report

    # Priority 5: If doing well, try reducing min_edge to capture more bets
    if report.win_rate >= 0.60 and report.resolved_predictions >= 20:
        current = get_nested(config, "edge.min_edge")
        if current is not None and current > 0.04:
            new_val = round(current - 0.01, 2)
            key = f"edge.min_edge={new_val}"
            if key not in tried_params:
                report.proposed_param = "edge.min_edge"
                report.proposed_old_value = current
                report.proposed_new_value = new_val
                report.proposed_reason = (
                    f"Win rate {report.win_rate:.0%} is strong. "
                    f"Lowering min_edge from {current} to {new_val} to capture more opportunities."
                )
                return report

    # Priority 6: Cycle through untried parameters
    for param_path, candidates, desc in PARAM_SPACE:
        current = get_nested(config, param_path)
        if current is None:
            continue
        for candidate in candidates:
            key = f"{param_path}={candidate}"
            if candidate != current and key not in tried_params:
                report.proposed_param = param_path
                report.proposed_old_value = current
                report.proposed_new_value = candidate
                report.proposed_reason = f"Exploring: {desc}. Trying {candidate} (was {current})."
                return report

    report.proposed_reason = "No untried experiments remaining. All parameter combinations explored."
    return report


# ---------------------------------------------------------------------------
# Main analysis pipeline
# ---------------------------------------------------------------------------
def run_analysis() -> AnalysisReport:
    """Run complete analysis and return report with proposed experiment."""
    entries = load_calibration()
    trades = load_trades()
    config = load_config()

    report = AnalysisReport()
    report.total_predictions = len(
        PREDICTIONS_FILE.read_text(encoding="utf-8").strip().split("\n")
    ) if PREDICTIONS_FILE.exists() else 0
    report.resolved_predictions = len(entries)

    if not entries:
        report.weaknesses.append("No resolved predictions yet. Need more data.")
        return report

    # Core metrics
    report.win_rate = win_rate(entries)
    report.brier_score = brier_score(entries)
    report.avg_prediction_error = statistics.mean(e.prediction_error for e in entries)

    # Edge from trades
    buy_trades = [t for t in trades if t.get("action") in ("BUY_YES", "BUY_NO") and "edge" in t]
    if buy_trades:
        report.avg_edge = statistics.mean(t["edge"] for t in buy_trades)

    # Breakdowns
    report.by_category = analyze_by_group(entries, lambda e: e.category or "unknown")
    report.by_confidence = analyze_by_group(entries, lambda e: e.confidence or "unknown")
    report.by_edge_range = analyze_by_group(entries, edge_range_key)

    # Identify weaknesses
    if report.win_rate < 0.50:
        report.weaknesses.append(f"Win rate critically low: {report.win_rate:.0%}")
    elif report.win_rate < 0.55:
        report.weaknesses.append(f"Win rate below target: {report.win_rate:.0%} (target: 57%+)")

    if report.brier_score > 0.30:
        report.weaknesses.append(f"Brier score high (poor calibration): {report.brier_score:.3f}")
    elif report.brier_score > 0.25:
        report.weaknesses.append(f"Brier score moderate: {report.brier_score:.3f}")

    for cat, stats in report.by_category.items():
        if stats["count"] >= 3 and stats["win_rate"] < 0.40:
            report.weaknesses.append(
                f"Category '{cat}' underperforming: {stats['win_rate']:.0%} "
                f"win rate ({stats['count']} predictions)"
            )

    for conf, stats in report.by_confidence.items():
        if stats["count"] >= 3 and stats["win_rate"] < 0.45:
            report.weaknesses.append(
                f"'{conf}' confidence predictions weak: {stats['win_rate']:.0%} "
                f"({stats['count']} predictions)"
            )

    # Propose next experiment
    report = propose_experiment(report, config)

    return report


def generate_report_markdown(report: AnalysisReport) -> str:
    """Generate human-readable markdown report."""
    lines = [
        f"# Self-Improvement Report",
        f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n",
        f"## Core Metrics",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total predictions | {report.total_predictions} |",
        f"| Resolved | {report.resolved_predictions} |",
        f"| Win rate | {report.win_rate:.1%} |",
        f"| Brier score | {report.brier_score:.4f} |",
        f"| Avg prediction error | {report.avg_prediction_error:.3f} |",
        f"| Avg edge (trades) | {report.avg_edge:.3f} |",
        "",
    ]

    if report.by_category:
        lines.append("## By Category")
        lines.append("| Category | Count | Win Rate | Brier | Avg Error |")
        lines.append("|----------|-------|----------|-------|-----------|")
        for cat, s in report.by_category.items():
            lines.append(
                f"| {cat} | {s['count']} | {s['win_rate']:.0%} | "
                f"{s['brier_score']:.3f} | {s['avg_error']:.3f} |"
            )
        lines.append("")

    if report.by_confidence:
        lines.append("## By Confidence")
        lines.append("| Confidence | Count | Win Rate | Brier | Avg Error |")
        lines.append("|------------|-------|----------|-------|-----------|")
        for conf, s in report.by_confidence.items():
            lines.append(
                f"| {conf} | {s['count']} | {s['win_rate']:.0%} | "
                f"{s['brier_score']:.3f} | {s['avg_error']:.3f} |"
            )
        lines.append("")

    if report.by_edge_range:
        lines.append("## By Edge Range")
        lines.append("| Range | Count | Win Rate | Brier | Avg Error |")
        lines.append("|-------|-------|----------|-------|-----------|")
        for rng, s in report.by_edge_range.items():
            lines.append(
                f"| {rng} | {s['count']} | {s['win_rate']:.0%} | "
                f"{s['brier_score']:.3f} | {s['avg_error']:.3f} |"
            )
        lines.append("")

    if report.weaknesses:
        lines.append("## Weaknesses Identified")
        for w in report.weaknesses:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## Proposed Experiment")
    if report.proposed_param:
        lines.append(f"- **Parameter:** `{report.proposed_param}`")
        lines.append(f"- **Current:** `{report.proposed_old_value}`")
        lines.append(f"- **Proposed:** `{report.proposed_new_value}`")
        lines.append(f"- **Reason:** {report.proposed_reason}")
    else:
        lines.append(f"- {report.proposed_reason}")

    return "\n".join(lines) + "\n"


def log_experiment(param: str, old_val: Any, new_val: Any, status: str, description: str) -> None:
    """Append experiment result to experiments.tsv."""
    EXPERIMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not EXPERIMENTS_FILE.exists():
        EXPERIMENTS_FILE.write_text(
            "timestamp\tparameter\told_value\tnew_value\tstatus\twin_rate\tbrier\tdescription\n",
            encoding="utf-8",
        )
    with open(EXPERIMENTS_FILE, "a", encoding="utf-8") as f:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        f.write(f"{ts}\t{param}\t{old_val}\t{new_val}\t{status}\t\t\t{description}\n")


# ---------------------------------------------------------------------------
# Auto-calibration (triggered every N resolved exits from the bot loop)
# ---------------------------------------------------------------------------
MATCH_OUTCOMES_FILE = Path("logs/match_outcomes.jsonl")
CALIBRATION_EVENTS_FILE = Path("logs/calibration_events.jsonl")
AUTO_CAL_STATE_FILE = Path("logs/auto_cal_state.json")

# How many resolved outcomes between auto-calibration runs.
# Lowered from 50 -> 15: bot resolves ~10-30 trades/day, so 15 gives one or
# two reports per day instead of one per week. Reports are read-only so cost
# is just one Telegram message per run.
AUTO_CAL_INTERVAL = 15


def _load_match_outcomes() -> list[dict]:
    """Load all records from match_outcomes.jsonl."""
    records: list[dict] = []
    if not MATCH_OUTCOMES_FILE.exists():
        return records
    for line in MATCH_OUTCOMES_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _load_auto_cal_state() -> dict:
    """Load auto-calibration state (last_resolved_count, last_run timestamp)."""
    if not AUTO_CAL_STATE_FILE.exists():
        return {"last_resolved_count": 0, "last_run": ""}
    try:
        return json.loads(AUTO_CAL_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"last_resolved_count": 0, "last_run": ""}


def _save_auto_cal_state(state: dict) -> None:
    AUTO_CAL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTO_CAL_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def auto_calibrate(logger: Any = None) -> dict | None:
    """Run auto-calibration if enough new resolved outcomes have accumulated.

    Called from the bot's main loop after each resolution batch.
    Returns calibration report dict if triggered, None otherwise.
    """
    import logging
    log = logger or logging.getLogger(__name__)

    outcomes = _load_match_outcomes()
    resolved = [r for r in outcomes if r.get("resolved")]
    resolved_count = len(resolved)

    state = _load_auto_cal_state()
    last_count = state.get("last_resolved_count", 0)

    # Not enough new resolutions since last calibration
    if resolved_count - last_count < AUTO_CAL_INTERVAL:
        return None

    if resolved_count < MIN_RESOLVED:
        return None

    log.info("Auto-calibration triggered: %d resolved (last run at %d)", resolved_count, last_count)

    # --- Compute metrics from resolved match outcomes ---
    total_correct = 0
    total_brier = 0.0
    by_confidence: dict[str, dict] = {}
    by_sport: dict[str, dict] = {}
    by_entry_reason: dict[str, dict] = {}
    book_vs_ai: list[dict] = []  # entries where bookmaker_prob is available

    # Hold-vs-exit analytics (post_exit_* records only)
    by_exit_reason: dict[str, dict] = {}        # per-exit-reason: count, exit_correct_n, total_left_on_table
    total_left_on_table = 0.0                    # sum of pnl_left_on_table across all post_exit records
    post_exit_count = 0                           # count of post_exit records (subset of resolved)
    exit_correct_count = 0                        # exits that were the right call
    held_better_count = 0                         # holds that would have done better than our exit
    held_better_total_diff = 0.0                  # sum of (hypothetical - actual) for held_better cases

    for r in resolved:
        ai_prob = r.get("ai_probability", 0.5)
        yes_won = r.get("yes_won")
        ai_correct = r.get("ai_correct")
        conf = r.get("confidence", "unknown")
        sport = r.get("sport_tag", "unknown") or "unknown"
        entry_reason = r.get("entry_reason", "unknown") or "unknown"
        book_prob = r.get("bookmaker_prob", 0.0)

        outcome_val = 1.0 if yes_won else 0.0
        brier_err = (ai_prob - outcome_val) ** 2
        total_brier += brier_err
        if ai_correct:
            total_correct += 1

        # Per-confidence breakdown
        _acc(by_confidence, conf, ai_correct, brier_err)
        # Per-sport breakdown
        _acc(by_sport, sport, ai_correct, brier_err)
        # Per-entry-reason breakdown
        _acc(by_entry_reason, entry_reason, ai_correct, brier_err)

        # Bookmaker comparison
        if book_prob > 0:
            book_brier = (book_prob - outcome_val) ** 2
            book_vs_ai.append({
                "ai_brier": round(brier_err, 4),
                "book_brier": round(book_brier, 4),
                "ai_better": brier_err < book_brier,
            })

        # Hold-vs-exit analytics: only for post_exit_* records that carry the
        # outcome_tracker analytics (actual_pnl, hypothetical_pnl, etc).
        exit_reason_str = r.get("exit_reason", "") or ""
        actual_pnl = r.get("actual_pnl")
        hypothetical_pnl = r.get("hypothetical_pnl")
        left_on_table = r.get("pnl_left_on_table")
        exit_was_correct = r.get("exit_was_correct")

        if exit_reason_str.startswith("post_exit_") and actual_pnl is not None:
            post_exit_count += 1
            # Strip the prefix so the breakdown key is the underlying exit reason.
            base_reason = exit_reason_str[len("post_exit_"):]
            stats = by_exit_reason.setdefault(base_reason, {
                "count": 0,
                "exit_correct_n": 0,
                "total_left_on_table": 0.0,
                "total_actual_pnl": 0.0,
                "total_hypothetical_pnl": 0.0,
                "held_better_n": 0,  # cases where holding beat our exit
            })
            stats["count"] += 1
            stats["total_actual_pnl"] += actual_pnl
            if hypothetical_pnl is not None:
                stats["total_hypothetical_pnl"] += hypothetical_pnl
            if left_on_table is not None:
                stats["total_left_on_table"] += left_on_table
                total_left_on_table += left_on_table
            if exit_was_correct is True:
                stats["exit_correct_n"] += 1
                exit_correct_count += 1
            # "Held would have been better" = positive money left on table
            if left_on_table is not None and left_on_table > 0:
                stats["held_better_n"] += 1
                held_better_count += 1
                held_better_total_diff += left_on_table

    n = len(resolved)
    overall_win_rate = total_correct / n if n else 0.0
    overall_brier = total_brier / n if n else 1.0

    # AI vs bookmaker comparison
    ai_better_count = sum(1 for x in book_vs_ai if x["ai_better"])
    book_compared = len(book_vs_ai)
    ai_vs_book_pct = ai_better_count / book_compared if book_compared else 0.0
    avg_ai_brier = statistics.mean(x["ai_brier"] for x in book_vs_ai) if book_vs_ai else 0.0
    avg_book_brier = statistics.mean(x["book_brier"] for x in book_vs_ai) if book_vs_ai else 0.0

    # Identify weaknesses
    weaknesses: list[str] = []
    if overall_win_rate < 0.55:
        weaknesses.append(f"Win rate {overall_win_rate:.0%} below 55% target")
    if overall_brier > 0.25:
        weaknesses.append(f"Brier score {overall_brier:.3f} indicates poor calibration")

    for group_name, breakdown in [("confidence", by_confidence), ("sport", by_sport), ("entry", by_entry_reason)]:
        for key, stats in breakdown.items():
            if stats["count"] >= 5 and stats["win_rate"] < 0.40:
                weaknesses.append(f"{group_name}={key}: {stats['win_rate']:.0%} win rate ({stats['count']} trades)")

    if book_compared >= 10 and ai_vs_book_pct < 0.45:
        weaknesses.append(
            f"AI underperforms bookmakers: AI better only {ai_vs_book_pct:.0%} of time "
            f"(AI Brier={avg_ai_brier:.3f} vs Book={avg_book_brier:.3f})"
        )

    # Hold-vs-exit weakness checks (only meaningful with enough post_exit samples)
    exit_reason_summary: dict[str, dict] = {}
    if post_exit_count >= 3:
        avg_left_on_table = total_left_on_table / post_exit_count
        exit_correct_pct = exit_correct_count / post_exit_count
        held_better_pct = held_better_count / post_exit_count
        avg_held_better_diff = (held_better_total_diff / held_better_count) if held_better_count > 0 else 0.0

        if avg_left_on_table > 2.0:  # >$2 per trade left on table on average
            weaknesses.append(
                f"Avg ${avg_left_on_table:.2f} left on table per exit "
                f"(across {post_exit_count} post-exits) -- exits may be premature"
            )
        if exit_correct_pct < 0.55 and post_exit_count >= 10:
            weaknesses.append(
                f"Exit timing only {exit_correct_pct:.0%} correct over {post_exit_count} samples"
            )
        if held_better_pct >= 0.60 and post_exit_count >= 10:
            weaknesses.append(
                f"Holding would have beaten {held_better_pct:.0%} of exits "
                f"(avg ${avg_held_better_diff:.2f} extra) -- consider raising exit thresholds"
            )

        # Per-exit-reason summary (rounded for JSON output)
        for reason, stats in by_exit_reason.items():
            n = stats["count"]
            exit_reason_summary[reason] = {
                "count": n,
                "exit_correct_rate": round(stats["exit_correct_n"] / n, 4) if n else 0.0,
                "avg_actual_pnl": round(stats["total_actual_pnl"] / n, 2) if n else 0.0,
                "avg_hypothetical_pnl": round(stats["total_hypothetical_pnl"] / n, 2) if n else 0.0,
                "avg_left_on_table": round(stats["total_left_on_table"] / n, 2) if n else 0.0,
                "held_better_n": stats["held_better_n"],
                "held_better_pct": round(stats["held_better_n"] / n, 4) if n else 0.0,
            }
            # Per-reason weakness: enough samples + holding consistently better
            if n >= 5 and stats["held_better_n"] / n >= 0.60:
                avg_diff_for_reason = (
                    stats["total_left_on_table"] / stats["held_better_n"]
                    if stats["held_better_n"] > 0 else 0.0
                )
                weaknesses.append(
                    f"exit_reason={reason}: holding beats exit {stats['held_better_n']}/{n} times "
                    f"(avg ${avg_diff_for_reason:.2f} extra)"
                )

    # Build calibration event
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resolved_count": resolved_count,
        "overall_win_rate": round(overall_win_rate, 4),
        "overall_brier": round(overall_brier, 4),
        "by_confidence": {k: _round_stats(v) for k, v in by_confidence.items()},
        "by_sport": {k: _round_stats(v) for k, v in by_sport.items()},
        "by_entry_reason": {k: _round_stats(v) for k, v in by_entry_reason.items()},
        "ai_vs_bookmaker": {
            "compared": book_compared,
            "ai_better_pct": round(ai_vs_book_pct, 4),
            "avg_ai_brier": round(avg_ai_brier, 4),
            "avg_book_brier": round(avg_book_brier, 4),
        },
        "hold_vs_exit": {
            "post_exit_samples": post_exit_count,
            "total_left_on_table": round(total_left_on_table, 2),
            "avg_left_on_table_per_exit": round(total_left_on_table / post_exit_count, 2) if post_exit_count else 0.0,
            "exit_correct_rate": round(exit_correct_count / post_exit_count, 4) if post_exit_count else 0.0,
            "held_better_count": held_better_count,
            "held_better_pct": round(held_better_count / post_exit_count, 4) if post_exit_count else 0.0,
            "by_exit_reason": exit_reason_summary,
        },
        "weaknesses": weaknesses,
    }

    # Persist
    CALIBRATION_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CALIBRATION_EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    # Update state
    _save_auto_cal_state({
        "last_resolved_count": resolved_count,
        "last_run": datetime.now(timezone.utc).isoformat(),
    })

    log.info(
        "Auto-calibration complete: win_rate=%.0f%% brier=%.3f weaknesses=%d ai_vs_book=%.0f%%",
        overall_win_rate * 100, overall_brier, len(weaknesses), ai_vs_book_pct * 100,
    )

    return event


def _acc(breakdown: dict, key: str, ai_correct: bool | None, brier_err: float) -> None:
    """Accumulate stats into a breakdown dict."""
    if key not in breakdown:
        breakdown[key] = {"count": 0, "correct": 0, "total_brier": 0.0}
    breakdown[key]["count"] += 1
    if ai_correct:
        breakdown[key]["correct"] += 1
    breakdown[key]["total_brier"] += brier_err
    n = breakdown[key]["count"]
    breakdown[key]["win_rate"] = breakdown[key]["correct"] / n
    breakdown[key]["brier"] = breakdown[key]["total_brier"] / n


def _round_stats(stats: dict) -> dict:
    """Round stats for JSON output."""
    return {
        "count": stats["count"],
        "win_rate": round(stats["win_rate"], 4),
        "brier": round(stats["brier"], 4),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Run analysis and print report. Called by Claude Code skill."""
    report = run_analysis()
    md = generate_report_markdown(report)

    # Save report
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(md, encoding="utf-8")

    print(md)
    return report


if __name__ == "__main__":
    main()
