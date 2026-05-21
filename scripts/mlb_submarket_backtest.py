"""MLB Submarket Backtest Script.

SPEC-R Plan 4 T4. Evaluates model accuracy on historical markets.

Usage (v1, smoke):
    python scripts/mlb_submarket_backtest.py --picks-jsonl path/to/picks.jsonl

Where picks.jsonl has one record per line:
    {"model_p": 0.62, "market_p": 0.55, "actual_outcome": "over",
     "market_type": "totals"}

Production backtest (v2) will:
- Fetch Statcast historical data for season
- Replay MlbSubmarketEngine on each historical market
- Compare against Polymarket audit archives
- Report calibration plot + edge-weighted accuracy
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

_HIGH_EDGE_THRESHOLD = 0.07


def evaluate_backtest_pick(
    model_p: float,
    market_p: float,
    actual_outcome: str,
    market_type: str,
) -> dict[str, Any]:
    """For one historical market, determine model vs market pick and correctness.

    Args:
        model_p: Model's P(YES / over / home_covers) probability.
        market_p: Market's P(YES / over / home_covers) probability.
        actual_outcome: Ground truth — "over" | "under" | "home_covers" | "away_covers".
        market_type: "totals" | "run_line".

    Returns:
        {model_pick, market_pick, actual, correct: bool, edge}
    """
    if market_type == "totals":
        model_pick = "over" if model_p > 0.5 else "under"
        market_pick = "over" if market_p > 0.5 else "under"
    elif market_type == "run_line":
        model_pick = "home_covers" if model_p > 0.5 else "away_covers"
        market_pick = "home_covers" if market_p > 0.5 else "away_covers"
    else:
        raise ValueError(f"unknown market_type: {market_type!r}")

    edge = model_p - market_p
    return {
        "model_pick": model_pick,
        "market_pick": market_pick,
        "actual": actual_outcome,
        "correct": model_pick == actual_outcome,
        "edge": edge,
    }


def summarize_backtest(picks: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate over many picks into accuracy + edge statistics.

    Args:
        picks: List of dicts, each containing at least {"correct": bool, "edge": float}.

    Returns:
        {n_markets, n_correct, accuracy, mean_edge, median_edge, accuracy_high_edge}
    """
    if not picks:
        return {
            "n_markets": 0,
            "n_correct": 0,
            "accuracy": 0.0,
            "mean_edge": 0.0,
            "median_edge": 0.0,
            "accuracy_high_edge": 0.0,
        }

    n_markets = len(picks)
    n_correct = sum(1 for p in picks if p.get("correct"))
    edges = [p.get("edge", 0.0) for p in picks]
    high_edge_picks = [
        p for p in picks if abs(p.get("edge", 0.0)) >= _HIGH_EDGE_THRESHOLD
    ]
    high_edge_correct = sum(1 for p in high_edge_picks if p.get("correct"))

    return {
        "n_markets": n_markets,
        "n_correct": n_correct,
        "accuracy": n_correct / n_markets,
        "mean_edge": statistics.fmean(edges),
        "median_edge": statistics.median(edges),
        "accuracy_high_edge": (
            high_edge_correct / len(high_edge_picks) if high_edge_picks else 0.0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="MLB Submarket Backtest")
    parser.add_argument(
        "--picks-jsonl",
        type=Path,
        required=True,
        help="Path to JSONL file with historical picks",
    )
    args = parser.parse_args()

    if not args.picks_jsonl.exists():
        print(f"ERROR: {args.picks_jsonl} not found", file=sys.stderr)
        return 1

    raw_picks: list[dict[str, Any]] = []
    for line in args.picks_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            raw_picks.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"WARNING: skipping malformed line: {exc}", file=sys.stderr)

    evaluated = [
        evaluate_backtest_pick(
            model_p=r["model_p"],
            market_p=r["market_p"],
            actual_outcome=r["actual_outcome"],
            market_type=r["market_type"],
        )
        for r in raw_picks
    ]
    summary = summarize_backtest(evaluated)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
