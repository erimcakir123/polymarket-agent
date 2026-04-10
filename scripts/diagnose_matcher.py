"""Matcher diagnostic: why are scout-queue entries not finding Polymarket markets?

Reads the current scout queue and live Polymarket markets (filtered to the 2h
window used by entry_gate), runs the real matcher, and writes a report
enumerating every Polymarket market that failed to match with a classification
of the likely reason.

Usage:
    python scripts/diagnose_matcher.py

Output: logs/matcher-diagnostic.md
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.matching import match_markets  # noqa: E402
from src.market_scanner import MarketScanner  # noqa: E402
from src.config import load_config  # noqa: E402

SCOUT_QUEUE = PROJECT_ROOT / "logs" / "scout_queue.json"
REPORT = PROJECT_ROOT / "logs" / "matcher-diagnostic.md"

# Window used by entry_gate._analyze_batch scout chrono selection
WINDOW_START_HOURS = -2.0
WINDOW_END_HOURS = 2.0


def load_scout_in_window(now: datetime) -> dict:
    raw = json.loads(SCOUT_QUEUE.read_text(encoding="utf-8"))
    in_window: dict = {}
    for key, entry in raw.items():
        mt = entry.get("match_time", "")
        if not mt:
            continue
        try:
            dt = datetime.fromisoformat(mt.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        hours = (dt - now).total_seconds() / 3600
        if WINDOW_START_HOURS <= hours <= WINDOW_END_HOURS:
            in_window[key] = entry
    return in_window


def load_polymarket_in_window(now: datetime):
    cfg = load_config()
    scanner = MarketScanner(cfg.scanner)
    all_markets = scanner.fetch()
    in_window = []
    for m in all_markets:
        mt = getattr(m, "match_start_iso", "") or ""
        if not mt:
            continue
        try:
            dt = datetime.fromisoformat(mt.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        hours = (dt - now).total_seconds() / 3600
        if WINDOW_START_HOURS <= hours <= WINDOW_END_HOURS:
            in_window.append(m)
    return in_window


def classify_failure(market) -> str:
    """Return a short label explaining why this market likely did not match."""
    slug = (getattr(market, "slug", "") or "").lower()
    question = (getattr(market, "question", "") or "").lower()

    # Prop markets: first-set, exact-score, player props — no head-to-head scout entry
    prop_tokens = ("first-set", "exact-score", "total-", "-over-", "-under-",
                   "to-score", "anytime", "margin", "handicap")
    if any(tok in slug for tok in prop_tokens):
        return "prop_market_no_h2h_scout"

    # Outright / long-term (year-level, playoff, season)
    if any(tok in slug or tok in question for tok in
           ("season", "playoff", "champion", "finish", "top-scorer", "mvp")):
        return "outright_not_h2h"

    # Sport not in scout coverage
    if slug.startswith(("f1-", "ufc-", "mma-", "boxing-")):
        return "sport_not_scouted"

    # Default: likely fuzzy-name failure (both teams should exist but matcher missed)
    return "fuzzy_name_mismatch_candidate"


def main() -> int:
    now = datetime.now(timezone.utc)
    print(f"Running matcher diagnostic at {now.isoformat()}")

    scout = load_scout_in_window(now)
    markets = load_polymarket_in_window(now)
    print(f"Scout entries in 2h window:     {len(scout)}")
    print(f"Polymarket markets in 2h window: {len(markets)}")

    matched = match_markets(markets, scout)
    matched_cids = {mm["market"].condition_id for mm in matched}
    unmatched = [m for m in markets if m.condition_id not in matched_cids]
    print(f"Matched:   {len(matched)}")
    print(f"Unmatched: {len(unmatched)}")

    # Classify unmatched
    classes: Counter = Counter()
    per_class_samples: dict[str, list] = {}
    for m in unmatched:
        label = classify_failure(m)
        classes[label] += 1
        per_class_samples.setdefault(label, [])
        if len(per_class_samples[label]) < 5:
            per_class_samples[label].append(
                f"{(m.slug or '')[:50]:50} | {(getattr(m, 'question', '') or '')[:60]}"
            )

    # Write report
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append(f"# Matcher Diagnostic — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Scout entries in 2h window: **{len(scout)}**")
    lines.append(f"- Polymarket markets in 2h window: **{len(markets)}**")
    lines.append(f"- Matched: **{len(matched)}**")
    lines.append(f"- Unmatched: **{len(unmatched)}**")
    lines.append(f"- Match rate: **{len(matched) / max(len(markets), 1) * 100:.1f}%**")
    lines.append("")
    lines.append("## Unmatched by category")
    lines.append("")
    lines.append("| Category | Count | Description |")
    lines.append("|---|---|---|")
    descriptions = {
        "prop_market_no_h2h_scout":
            "Prop market (first-set, exact-score, totals, player props). "
            "Scout only stores head-to-head matches, so these will never match. "
            "Expected — not a matcher bug.",
        "outright_not_h2h":
            "Outright / season-long (champion, top scorer, finish 2nd). "
            "Not a head-to-head match. Expected.",
        "sport_not_scouted":
            "F1, UFC, boxing — not covered by the scout sources. Expected.",
        "fuzzy_name_mismatch_candidate":
            "Both teams exist as a head-to-head market; matcher *should* have "
            "found a scout entry but didn't. **Likely fuzzy-matching gap.**",
    }
    for cat, count in classes.most_common():
        lines.append(f"| `{cat}` | {count} | {descriptions.get(cat, '—')} |")
    lines.append("")
    lines.append("## Samples per category")
    lines.append("")
    for cat, count in classes.most_common():
        lines.append(f"### `{cat}` ({count} cases)")
        lines.append("")
        for s in per_class_samples.get(cat, []):
            lines.append(f"- `{s}`")
        lines.append("")

    # Reverse angle: scout entries that had no Polymarket market at all
    matched_scout_keys = {mm["scout_key"] for mm in matched}
    scout_unused = [k for k in scout if k not in matched_scout_keys]
    lines.append("## Scout entries without a Polymarket match")
    lines.append("")
    lines.append(f"Out of {len(scout)} scout entries in the 2h window, "
                 f"**{len(scout_unused)}** have no Polymarket counterpart. "
                 "These are either niche leagues Polymarket doesn't list, or "
                 "matcher-side fuzzy failures (if Polymarket DID list the match).")
    lines.append("")
    for k in scout_unused[:20]:
        e = scout[k]
        ta = e.get("team_a", "?")
        tb = e.get("team_b", "?")
        sport = e.get("sport") or "?"
        mt = e.get("match_time", "")[:16]
        lines.append(f"- `[{sport}]` {ta} vs {tb} @ {mt}")
    if len(scout_unused) > 20:
        lines.append(f"- ... and {len(scout_unused) - 20} more")
    lines.append("")

    lines.append("## Conclusion")
    lines.append("")
    fuzzy_count = classes.get("fuzzy_name_mismatch_candidate", 0)
    if fuzzy_count == 0:
        lines.append(
            "No fuzzy-match gaps detected. All unmatched markets fall into "
            "categories the matcher is **not expected** to handle (props, "
            "outrights, non-scouted sports). Match rate is limited by "
            "Polymarket's non-H2H inventory, not matcher quality."
        )
    else:
        lines.append(
            f"**{fuzzy_count}** markets are candidates for a matcher patch. "
            "These are head-to-head markets where Polymarket and the scout "
            "both *should* know the teams but fuzzy matching failed. Review "
            "the `fuzzy_name_mismatch_candidate` samples above and open a "
            "follow-up matcher patch plan."
        )
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written: {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
