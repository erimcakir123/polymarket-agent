"""Replay logged paper trade matches and compute accuracy metrics.

Usage: python -m scripts.diag_tennis_paper_replay [--log-path PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-path", default="logs/audit/tennis_paper_trade.jsonl")
    args = parser.parse_args()

    log_path = Path(args.log_path)
    if not log_path.exists():
        print(f"No paper log found: {log_path}")
        sys.exit(1)

    records = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    finished = [r for r in records if r.get("actual_outcome") is not None]

    if not finished:
        print(f"Loaded {len(records)} records, 0 finished. Cannot compute accuracy.")
        return

    print(f"=== Paper Trade Stats ({len(finished)} finished matches) ===")

    correct = 0
    high_conf_correct = 0
    high_conf_total = 0
    edge_outcomes = []

    for r in finished:
        pre = r["pre_match"]
        actual = r["actual_outcome"]["winner"]
        predicted = "a" if pre["model_p_win_a"] >= 0.5 else "b"
        is_correct = predicted == actual
        if is_correct:
            correct += 1

        # High-confidence calls (model > 0.55)
        if pre["model_p_win_a"] >= 0.55 or pre["model_p_win_a"] <= 0.45:
            high_conf_total += 1
            if is_correct:
                high_conf_correct += 1

        edge_outcomes.append({"edge": pre["edge"], "won": is_correct})

    print(f"Overall accuracy: {correct}/{len(finished)} = {correct/len(finished)*100:.1f}%")
    if high_conf_total > 0:
        print(f"High-confidence (model >= 0.55): {high_conf_correct}/{high_conf_total} = {high_conf_correct/high_conf_total*100:.1f}%")
        print(f"GATE for Phase 1: {'PASS' if high_conf_correct/high_conf_total >= 0.65 else 'FAIL (need >= 65%)'}")
    avg_edge = sum(e["edge"] for e in edge_outcomes) / len(edge_outcomes)
    print(f"Average edge claimed: {avg_edge*100:.2f}%")


if __name__ == "__main__":
    main()
