"""Debug: dump all tennis-tagged markets from Polymarket Gamma API.

Usage:
    python scripts/debug_tennis_markets.py

Stage 0 of PLAN-TENNIS-001 — investigates why scanner returns 0 tennis
markets despite polymarket.com/sports/tennis/games showing active matches.

Reuses GammaClient (infrastructure). Prints one line per tennis market:
    slug | sport_tag | sports_market_type | match_start_iso | hours_to_start | yes_price

Then prints a summary: unique sports_market_type values + counts.
"""
from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.infrastructure.apis.gamma_client import GammaClient
from src.models.market import MarketData


def _hours_to_start(m: MarketData) -> float:
    raw = m.match_start_iso or m.end_date_iso
    if not raw:
        return float("inf")
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return float("inf")
    return (dt - datetime.now(timezone.utc)).total_seconds() / 3600.0


def main() -> None:
    print("Fetching events from Gamma API...")
    client = GammaClient()
    all_markets = client.fetch_events()
    print(f"Total markets fetched: {len(all_markets)}\n")

    tennis = [m for m in all_markets if (m.sport_tag or "").lower() == "tennis"]
    print(f"Tennis markets (sport_tag=='tennis'): {len(tennis)}\n")

    if not tennis:
        # Fallback dump: maybe normalization missed; show any tennis-shaped slugs.
        candidates = [
            m for m in all_markets
            if (m.slug or "").lower().startswith(("atp-", "wta-", "tennis-"))
        ]
        print(f"Slug-based tennis candidates: {len(candidates)}\n")
        tennis = candidates

    print("slug | sport_tag | sports_market_type | match_start_iso | hours_to_start | yes_price")
    print("-" * 140)
    for m in tennis:
        hrs = _hours_to_start(m)
        hrs_str = f"{hrs:>7.1f}" if hrs != float("inf") else "    inf"
        print(
            f"{(m.slug or '')[:55]:55s} | "
            f"{(m.sport_tag or ''):8s} | "
            f"{(m.sports_market_type or '<empty>'):28s} | "
            f"{(m.match_start_iso or '<empty>'):25s} | "
            f"{hrs_str} | "
            f"{m.yes_price:.3f}"
        )

    print()
    print("=" * 80)
    print("Summary: unique sports_market_type values among tennis markets")
    print("=" * 80)
    type_counts: Counter = Counter()
    for m in tennis:
        type_counts[m.sports_market_type or "<empty>"] += 1
    for smt, n in type_counts.most_common():
        print(f"  {smt:35s} {n}")

    print()
    print("=" * 80)
    print("Summary: unique sport_tag values among tennis-shaped markets")
    print("=" * 80)
    tag_counts: Counter = Counter()
    for m in tennis:
        tag_counts[m.sport_tag or "<empty>"] += 1
    for tag, n in tag_counts.most_common():
        print(f"  {tag:20s} {n}")

    # Hours-to-start distribution buckets — to see if max_hours_to_start=24h is the gate.
    print()
    print("=" * 80)
    print("Summary: hours_to_start buckets (tennis markets)")
    print("=" * 80)
    buckets = {"<6h": 0, "6-24h": 0, "24-72h": 0, "72-168h": 0, ">168h_or_unknown": 0}
    for m in tennis:
        h = _hours_to_start(m)
        if h == float("inf"):
            buckets[">168h_or_unknown"] += 1
        elif h < 6:
            buckets["<6h"] += 1
        elif h < 24:
            buckets["6-24h"] += 1
        elif h < 72:
            buckets["24-72h"] += 1
        elif h < 168:
            buckets["72-168h"] += 1
        else:
            buckets[">168h_or_unknown"] += 1
    for b, n in buckets.items():
        print(f"  {b:25s} {n}")


if __name__ == "__main__":
    main()
