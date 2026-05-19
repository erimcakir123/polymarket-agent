"""Tennis trade diagnostic tool.

Analyze tennis trade outcomes — group by surface, tier, feature.

Run:
    python scripts/diagnose.py --period 7d --group-by surface
    python scripts/diagnose.py --period 30d --group-by tier
    python scripts/diagnose.py --period 30d --group-by feature
    python scripts/diagnose.py --trade <uuid>  # single trade detail

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §8.2
Plan: Task 15
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticRecord:
    trade_id: str
    surface: str
    tournament_tier: str
    market_type: str
    confidence_tier: str
    model_prob: float
    edge: float
    features: dict
    outcome: Optional[str]  # "WIN" / "LOSS" / None
    realized_pnl: float


def load_diagnostic_records(log_dir: Path, days: int) -> list[DiagnosticRecord]:
    """Load + merge prediction + outcome records across JSONL log files.

    Each JSONL file is named YYYY-MM-DD.jsonl.
    Prediction rows have 'match'/'market'/'prediction'/'features' keys.
    Outcome rows have 'outcome' key but no 'match' key.
    Merges by trade_id.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    preds: dict[str, dict] = {}
    outcomes: dict[str, dict] = {}

    for log_file in sorted(Path(log_dir).glob("*.jsonl")):
        try:
            file_date = datetime.strptime(log_file.stem, "%Y-%m-%d")
            if file_date < cutoff:
                continue
        except ValueError:
            continue

        with open(log_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed JSON line in %s", log_file.name)
                    continue
                tid = r.get("trade_id")
                if not tid:
                    continue
                if r.get("outcome") is not None and "match" not in r:
                    outcomes[tid] = r
                else:
                    preds[tid] = r

    records: list[DiagnosticRecord] = []
    for tid, pred in preds.items():
        outcome_data = outcomes.get(tid, {})
        match = pred.get("match", {})
        market = pred.get("market", {})
        prediction = pred.get("prediction", {})
        records.append(DiagnosticRecord(
            trade_id=tid,
            surface=match.get("surface", "unknown"),
            tournament_tier=match.get("tournament_tier", "unknown"),
            market_type=market.get("type", "unknown"),
            confidence_tier=prediction.get("confidence_tier", "unknown"),
            model_prob=float(prediction.get("model_prob", 0.0)),
            edge=float(prediction.get("edge", 0.0)),
            features=pred.get("features", {}),
            outcome=outcome_data.get("outcome"),
            realized_pnl=float(outcome_data.get("realized_pnl_usdc", 0.0)),
        ))
    return records


def _empty_bucket() -> dict:
    return {"wins": 0, "losses": 0, "net_pnl": 0.0, "count": 0}


def _tally(bucket: dict, r: DiagnosticRecord) -> None:
    bucket["count"] += 1
    bucket["net_pnl"] += r.realized_pnl
    if r.outcome == "WIN":
        bucket["wins"] += 1
    elif r.outcome == "LOSS":
        bucket["losses"] += 1


def group_by_surface(records: list[DiagnosticRecord]) -> dict[str, dict]:
    """Group records by tennis surface (clay/hard/grass)."""
    groups: dict[str, dict] = defaultdict(_empty_bucket)
    for r in records:
        _tally(groups[r.surface], r)
    return dict(groups)


def group_by_tier(records: list[DiagnosticRecord]) -> dict[str, dict]:
    """Group records by prediction confidence tier (A/B/C)."""
    groups: dict[str, dict] = defaultdict(_empty_bucket)
    for r in records:
        _tally(groups[r.confidence_tier], r)
    return dict(groups)


def group_by_feature(records: list[DiagnosticRecord]) -> dict[str, dict]:
    """Group by feature bands: h2h_matches_total and form_data_age."""
    groups: dict[str, dict] = defaultdict(_empty_bucket)
    for r in records:
        h2h = r.features.get("h2h_matches_total", 0)
        if h2h == 0:
            _tally(groups["h2h_matches_total=0"], r)
        elif h2h <= 2:
            _tally(groups["h2h_matches_total=1-2"], r)
        else:
            _tally(groups["h2h_matches_total>=3"], r)

        age = r.features.get("p1_form_data_age_days", 0)
        if age > 90:
            _tally(groups["form_data_age>90d"], r)
        elif age > 60:
            _tally(groups["form_data_age=60-90d"], r)
        else:
            _tally(groups["form_data_age<60d"], r)
    return dict(groups)


def _print_groups(title: str, groups: dict[str, dict]) -> None:
    print(f"\n=== {title} ===")
    print(f"{'Group':40s} {'W':>4s} {'L':>4s} {'W%':>6s} {'NetPnL':>10s}")
    print("-" * 70)
    for k, b in sorted(groups.items(), key=lambda kv: kv[1]["net_pnl"]):
        total = b["wins"] + b["losses"]
        w_pct = (b["wins"] / total * 100) if total > 0 else 0.0
        print(
            f"{k:40s} {b['wins']:>4d} {b['losses']:>4d} "
            f"{w_pct:>5.1f}% ${b['net_pnl']:>+8.2f}"
        )


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description="Tennis trade diagnostic")
    parser.add_argument("--period", default="30d", help="Time period (Nd, e.g. 7d, 30d)")
    parser.add_argument(
        "--group-by",
        default="surface",
        choices=["surface", "tier", "feature"],
        help="Grouping dimension",
    )
    parser.add_argument("--trade", default=None, help="Single trade detail by UUID")
    args = parser.parse_args()

    log_dir = Path("logs/tennis_diagnostics")
    days = int(args.period.rstrip("d"))
    records = load_diagnostic_records(log_dir, days=days)
    print(f"Loaded {len(records)} trade records from last {days} days")

    if args.trade:
        for r in records:
            if r.trade_id == args.trade:
                print(f"\nTRADE {r.trade_id}")
                print(f"  Surface: {r.surface}, Tier: {r.confidence_tier}")
                print(f"  Market: {r.market_type}, model_p={r.model_prob:.3f}, edge={r.edge:+.3f}")
                print(f"  Outcome: {r.outcome}, PnL: ${r.realized_pnl:+.2f}")
                print(f"  Features: {json.dumps(r.features, indent=2)}")
                return
        print(f"Trade {args.trade} not found")
        return

    if args.group_by == "surface":
        _print_groups("Surface Performance", group_by_surface(records))
    elif args.group_by == "tier":
        _print_groups("Confidence Tier Performance", group_by_tier(records))
    elif args.group_by == "feature":
        _print_groups("Feature Pattern Analysis", group_by_feature(records))


if __name__ == "__main__":
    main()
