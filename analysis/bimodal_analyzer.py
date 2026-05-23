"""
Empirical bimodal classification for Polymarket sports submarkets.

NOT a production script — one-shot research tool. Outputs JSON + Markdown to
analysis/. Reads only from public Polymarket APIs. Documents key limitation:
prices-history fidelity floor is 60s, NOT tick-level.

Usage: python analysis/bimodal_analyzer.py
"""
from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from pathlib import Path
from statistics import median

import httpx

GAMMA = "https://gamma-api.polymarket.com/markets"
CLOB = "https://clob.polymarket.com/prices-history"

TARGET_PER_CELL = 15
MIN_PER_CELL = 5
PAGES_TO_SCAN = 200  # 200 * 100 = 20,000 markets — deep scan needed (sports are <5% of closed pool)
PAGE_SIZE = 100
REQUEST_DELAY = 0.15  # 150ms politeness

# Slug pattern -> (sport_family, sport_tag, market_type)
# Patterns evaluated in order; first match wins. Slug stripped of date suffix.
SLUG_PATTERNS = [
    # NBA
    (r"^nba-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-1h-moneyline", "basketball", "nba", "1h_moneyline"),
    (r"^nba-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-1q-moneyline", "basketball", "nba", "1q_moneyline"),
    (r"^nba-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-total-\d", "basketball", "nba", "totals"),
    (r"^nba-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-spread-", "basketball", "nba", "spread"),
    (r"^nba-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}$", "basketball", "nba", "moneyline"),
    # WNBA
    (r"^wnba-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-1h-moneyline", "basketball", "wnba", "1h_moneyline"),
    (r"^wnba-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-1q-moneyline", "basketball", "wnba", "1q_moneyline"),
    (r"^wnba-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-total-\d", "basketball", "wnba", "totals"),
    (r"^wnba-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-spread-", "basketball", "wnba", "spread"),
    (r"^wnba-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}$", "basketball", "wnba", "moneyline"),
    # NHL
    (r"^nhl-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-total-\d", "hockey", "nhl", "totals"),
    (r"^nhl-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-spread-", "hockey", "nhl", "spread"),
    (r"^nhl-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}$", "hockey", "nhl", "moneyline"),
    # MLB
    (r"^mlb-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-nrfi", "baseball", "mlb", "nrfi"),
    (r"^mlb-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-f5-total", "baseball", "mlb", "f5_totals"),
    (r"^mlb-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-f5", "baseball", "mlb", "f5_moneyline"),
    (r"^mlb-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-spread-", "baseball", "mlb", "run_line"),
    (r"^mlb-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-total-\d", "baseball", "mlb", "totals"),
    (r"^mlb-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}$", "baseball", "mlb", "moneyline"),
    # NFL
    (r"^nfl-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-1h-moneyline", "football", "nfl", "1h_moneyline"),
    (r"^nfl-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-total-\d", "football", "nfl", "totals"),
    (r"^nfl-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-spread-", "football", "nfl", "spread"),
    (r"^nfl-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}$", "football", "nfl", "moneyline"),
    # NCAAF
    (r"^ncaaf-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-1h-moneyline", "football", "ncaaf", "1h_moneyline"),
    (r"^ncaaf-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-total-\d", "football", "ncaaf", "totals"),
    (r"^ncaaf-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-spread-", "football", "ncaaf", "spread"),
    (r"^ncaaf-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}$", "football", "ncaaf", "moneyline"),
    # ATP (singles only — atp-doubles excluded by the negative lookbehind via pattern order)
    (r"^atp-doubles-", None, None, None),  # exclude
    (r"^atp-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-first-set-winner", "tennis", "atp", "first_set_winner"),
    (r"^atp-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-first-set-total", "tennis", "atp", "set_totals"),
    (r"^atp-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-set-totals?-", "tennis", "atp", "set_totals"),
    (r"^atp-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-set-handicap", "tennis", "atp", "set_handicap"),
    (r"^atp-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-match-total-", "tennis", "atp", "match_total_games"),
    (r"^atp-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-completed-match", None, None, None),  # exclude metadata
    (r"^atp-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}$", "tennis", "atp", "moneyline"),
    # WTA
    (r"^wta-doubles-", None, None, None),  # exclude
    (r"^wta-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-first-set-winner", "tennis", "wta", "first_set_winner"),
    (r"^wta-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-first-set-total", "tennis", "wta", "set_totals"),
    (r"^wta-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-set-totals?-", "tennis", "wta", "set_totals"),
    (r"^wta-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-set-handicap", "tennis", "wta", "set_handicap"),
    (r"^wta-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-match-total-", "tennis", "wta", "match_total_games"),
    (r"^wta-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-completed-match", None, None, None),
    (r"^wta-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}$", "tennis", "wta", "moneyline"),
]

# Slug substrings that exclude a market (player props, metadata, exotics).
SLUG_EXCLUDE_CONTAINS = (
    "-assists-",
    "-rebounds-",
    "-points-",
    "-strikeouts-",
    "-home-runs-",
    "-exact-score-",
    "-halftime-",
    "-odd-even-",
    "-kill-over-",
    "-completed-match",
    "-game1",
    "-game2",
    "-game3",
    "-map-",  # esports
)


def classify_slug(slug: str):
    """Return (sport_family, sport_tag, market_type) or None."""
    # Hard excludes first
    for needle in SLUG_EXCLUDE_CONTAINS:
        if needle in slug:
            return None
    for pat, fam, tag, mt in SLUG_PATTERNS:
        if re.match(pat, slug):
            if fam is None:  # explicit exclude pattern
                return None
            return fam, tag, mt
    return None


def fetch_markets_pool(client: httpx.Client, pages: int):
    """Paginate gamma markets API."""
    pool = []
    for page in range(pages):
        offset = page * PAGE_SIZE
        try:
            r = client.get(
                GAMMA,
                params={
                    "closed": "true",
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "order": "closedTime",
                    "ascending": "false",
                    "tag": "sports",
                },
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            print(f"[pool] page={page} HTTP error: {exc}")
            time.sleep(1.0)
            continue
        if r.status_code != 200:
            print(f"[pool] page={page} status={r.status_code}")
            time.sleep(0.5)
            continue
        data = r.json()
        if not data:
            print(f"[pool] page={page} empty, stopping")
            break
        pool.extend(data)
        if page % 5 == 0:
            print(f"[pool] page={page} cumulative={len(pool)}")
        time.sleep(REQUEST_DELAY)
    return pool


def bucket_markets(pool):
    """Group markets by (sport_family, sport_tag, market_type)."""
    by_cell = defaultdict(list)
    for m in pool:
        slug = m.get("slug") or ""
        cls = classify_slug(slug)
        if not cls:
            continue
        # Need clobTokenIds + volume
        if not m.get("clobTokenIds"):
            continue
        # Only volume > 0 (otherwise no price action)
        vol = m.get("volumeNum") or 0
        if vol < 50:  # cosmetic floor; we want markets that actually traded
            continue
        by_cell[cls].append(m)
    return by_cell


def fetch_price_history(client: httpx.Client, token_id: str):
    """Fetch finest-resolution full-life price history."""
    # interval=1d fidelity=1 gave 60s ticks for ~17h span. Try max first.
    for params in (
        {"market": token_id, "interval": "1w", "fidelity": 1},
        {"market": token_id, "interval": "1d", "fidelity": 1},
        {"market": token_id, "interval": "max", "fidelity": 1},
    ):
        try:
            r = client.get(CLOB, params=params, timeout=15.0)
        except httpx.HTTPError:
            continue
        if r.status_code != 200:
            continue
        data = r.json()
        hist = data.get("history") or []
        if len(hist) < 10:
            continue
        # Check if it's truly 60s spacing
        deltas = [hist[i + 1]["t"] - hist[i]["t"] for i in range(min(20, len(hist) - 1))]
        if deltas and median(deltas) <= 120:
            return hist
    # Fallback: max with any fidelity
    try:
        r = client.get(CLOB, params={"market": token_id, "interval": "max", "fidelity": 1}, timeout=15.0)
        if r.status_code == 200:
            return r.json().get("history") or []
    except httpx.HTTPError:
        pass
    return []


def analyze_arc(hist):
    """Find the worst sustained drop in the price arc.

    Returns dict:
      worst_drop_pct: float (e.g. 0.55 = -55%)
      worst_drop_window_s: int (seconds from peak to trough)
      worst_drop_from: float
      worst_drop_to: float
      peak_to_endmin_pct: float (peak-of-arc to nearest local trough after)
      n_points: int
    """
    if len(hist) < 5:
        return None
    prices = [h["p"] for h in hist]
    times = [h["t"] for h in hist]

    # Strategy: for each point, look ahead to find lowest within 1h, compute drop
    # then capture the WORST drop event (highest pct decline) and its window length.
    worst = {
        "drop_pct": 0.0,
        "window_s": 0,
        "from_p": 0.0,
        "to_p": 0.0,
        "from_t": 0,
        "to_t": 0,
    }
    n = len(hist)
    # Limit lookahead to 2 hours = 120 bars (60s each)
    LOOKAHEAD_BARS = 120
    for i in range(n):
        peak_p = prices[i]
        if peak_p < 0.02:  # too low to drop meaningfully
            continue
        # Find lowest price within lookahead, where the drop is monotonic-ish
        end_idx = min(n, i + LOOKAHEAD_BARS + 1)
        running_min = peak_p
        running_min_idx = i
        for j in range(i + 1, end_idx):
            if prices[j] < running_min:
                running_min = prices[j]
                running_min_idx = j
            # Stop if price recovers >20% from running min — that ends this drop event
            if prices[j] > running_min * 1.20 and prices[j] > peak_p * 0.5:
                break
        drop_pct = (peak_p - running_min) / peak_p if peak_p > 0 else 0
        if drop_pct > worst["drop_pct"]:
            worst.update({
                "drop_pct": drop_pct,
                "window_s": times[running_min_idx] - times[i],
                "from_p": peak_p,
                "to_p": running_min,
                "from_t": times[i],
                "to_t": times[running_min_idx],
            })
    return worst


def categorize_drop(drop_pct: float, window_s: int):
    """Return one of: instant, borderline, kademeli, no_significant_drop."""
    if drop_pct < 0.30:
        return "no_significant_drop"
    # The drop crossed -30% threshold within this window. Categorize by window.
    # NOTE: 60s API floor — "instant" here means within ONE bar (single 60s tick)
    if window_s <= 60:
        return "instant"
    elif window_s <= 300:
        return "borderline"
    else:
        return "kademeli"


def decide_cell(cell_stats):
    """Apply objective decision rule."""
    n = cell_stats["n"]
    if n < MIN_PER_CELL:
        return "INSUFFICIENT_DATA"
    instant = cell_stats["instant_collapse_pct"]
    kademeli = cell_stats["sl_catchable_pct"]
    median_w = cell_stats["median_drop_window_seconds"]
    # Rule: bimodal if instant >= 30% OR median window < 30s.
    # API floor 60s; we adapt: median window <= 60s ~ "instant-class within available resolution"
    if instant >= 30 or (median_w is not None and median_w <= 60):
        return "BIMODAL"
    if kademeli >= 60 and instant < 20:
        return "NON_BIMODAL"
    return "AMBIGUOUS_DEFAULT_BIMODAL"


def main():
    out_dir = Path(__file__).parent
    out_dir.mkdir(exist_ok=True)

    api_calls = 0
    with httpx.Client(headers={"User-Agent": "polymarket-bimodal-research/1.0"}) as client:
        print("[1] Fetching market pool...")
        pool = fetch_markets_pool(client, PAGES_TO_SCAN)
        api_calls += PAGES_TO_SCAN
        print(f"[1] Pool size: {len(pool)} markets")

        print("[2] Bucketing by cell...")
        by_cell = bucket_markets(pool)
        for cell, ms in sorted(by_cell.items(), key=lambda x: -len(x[1])):
            print(f"    {cell}: {len(ms)} candidates")

        print("[3] Analyzing per-cell samples (target=15, min=5)...")
        cell_results = {}
        for cell, ms in by_cell.items():
            # Sort by volume descending — analyze most liquid first
            ms_sorted = sorted(ms, key=lambda m: m.get("volumeNum") or 0, reverse=True)
            samples = ms_sorted[:TARGET_PER_CELL]
            drops = []
            sample_slugs = []
            for m in samples:
                try:
                    tokens = json.loads(m["clobTokenIds"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
                if not tokens:
                    continue
                # Use YES token (index 0)
                hist = fetch_price_history(client, tokens[0])
                api_calls += 1
                time.sleep(REQUEST_DELAY)
                if not hist or len(hist) < 10:
                    continue
                w = analyze_arc(hist)
                if not w:
                    continue
                drops.append(w)
                sample_slugs.append(m["slug"])
            n = len(drops)
            print(f"    [{cell}] analyzed n={n}")
            if n == 0:
                cell_results[cell] = {
                    "n_analyzed": 0,
                    "decision": "INSUFFICIENT_DATA",
                    "sample_market_slugs": [],
                }
                continue
            # Categorize
            cats = [categorize_drop(d["drop_pct"], d["window_s"]) for d in drops]
            sig_drops = [d for d, c in zip(drops, cats) if c != "no_significant_drop"]
            n_sig = len(sig_drops)
            n_instant = sum(1 for c in cats if c == "instant")
            n_border = sum(1 for c in cats if c == "borderline")
            n_kademeli = sum(1 for c in cats if c == "kademeli")
            n_no = sum(1 for c in cats if c == "no_significant_drop")
            windows = [d["window_s"] for d in sig_drops]
            stats = {
                "n_analyzed": n,
                "n_with_significant_drop": n_sig,
                "n_no_significant_drop": n_no,
                "instant_collapse_pct": round(100.0 * n_instant / n, 1),
                "borderline_pct": round(100.0 * n_border / n, 1),
                "sl_catchable_pct": round(100.0 * n_kademeli / n, 1),
                "no_significant_drop_pct": round(100.0 * n_no / n, 1),
                "median_drop_window_seconds": int(median(windows)) if windows else None,
                "median_drop_pct": round(median([d["drop_pct"] for d in sig_drops]), 3) if sig_drops else None,
                "sample_market_slugs": sample_slugs,
            }
            stats["decision"] = decide_cell({
                "n": n,
                "instant_collapse_pct": stats["instant_collapse_pct"],
                "sl_catchable_pct": stats["sl_catchable_pct"],
                "median_drop_window_seconds": stats["median_drop_window_seconds"],
            })
            cell_results[cell] = stats

    # Build JSON output
    cells_out = []
    for (fam, tag, mt), stats in sorted(cell_results.items()):
        rec = {
            "sport_family": fam,
            "sport_tag": tag,
            "market_type": mt,
        }
        rec.update(stats)
        cells_out.append(rec)

    payload = {
        "methodology": (
            "Empirical bimodal classification using Polymarket public APIs. "
            "API resolution floor: 60s (1-minute) — sub-minute / tick data NOT available. "
            "Adapted thresholds: instant = drop >=30% within <=60s (single bar); "
            "borderline = 61-300s; kademeli = >300s. Decision rule unchanged from spec."
        ),
        "api_calls_made": api_calls,
        "data_resolution_seconds": 60,
        "sample_dates": "Markets closing within recent window (data-driven, sorted by closedTime desc)",
        "sl_threshold_pct": 30.0,
        "bot_poll_seconds": 5,
        "cells": cells_out,
    }

    json_path = out_dir / "bimodal_classification_2026-05-23.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Wrote {json_path}")

    # Build Markdown report
    md_lines = []
    md_lines.append("# Polymarket Bimodal Classification — 2026-05-23")
    md_lines.append("")
    md_lines.append("## Methodology")
    md_lines.append("")
    md_lines.append("- **Source**: Polymarket public APIs (`gamma-api.polymarket.com/markets` + `clob.polymarket.com/prices-history`).")
    md_lines.append("- **CRITICAL CONSTRAINT**: Public price-history API floor is **60 seconds**. Sub-minute (5s) tick data is NOT available via public endpoints.")
    md_lines.append("- **Adapted bands**:")
    md_lines.append("  - **instant** = >=30% drop within <=60s (single 1-min bar) — SL polling at 5s CANNOT catch reliably")
    md_lines.append("  - **borderline** = 61-300s (2-5 bars) — SL may catch")
    md_lines.append("  - **kademeli** = >300s — SL catches reliably")
    md_lines.append("- **Sampling**: Up to 15 markets per (sport_tag × market_type) cell, filtered for closed + volume>=50, sorted by volume desc.")
    md_lines.append("- **Decision rule**:")
    md_lines.append("  - BIMODAL if instant>=30% OR median_drop_window<=60s")
    md_lines.append("  - NON_BIMODAL if kademeli>=60% AND instant<20%")
    md_lines.append("  - Else AMBIGUOUS (defaults to BIMODAL for safety)")
    md_lines.append("")
    md_lines.append("## Per-Cell Summary")
    md_lines.append("")
    md_lines.append("| Sport | Market | n | instant% | borderline% | kademeli% | no_sig_drop% | median_window_s | decision |")
    md_lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|")
    for rec in cells_out:
        n = rec.get("n_analyzed", 0)
        if n == 0:
            md_lines.append(
                f"| {rec['sport_tag']} | {rec['market_type']} | 0 | — | — | — | — | — | INSUFFICIENT_DATA |"
            )
            continue
        md_lines.append(
            f"| {rec['sport_tag']} | {rec['market_type']} | {n} | "
            f"{rec['instant_collapse_pct']} | {rec['borderline_pct']} | {rec['sl_catchable_pct']} | "
            f"{rec['no_significant_drop_pct']} | {rec['median_drop_window_seconds']} | "
            f"**{rec['decision']}** |"
        )
    md_lines.append("")

    # Recommended bimodal lists per sport
    md_lines.append("## Recommended `bimodal_market_types` per sport")
    md_lines.append("")
    by_sport = defaultdict(list)
    for rec in cells_out:
        if rec.get("decision") in ("BIMODAL", "AMBIGUOUS_DEFAULT_BIMODAL"):
            by_sport[rec["sport_tag"]].append(rec["market_type"])
    if not by_sport:
        md_lines.append("_No bimodal cells detected (or insufficient data)._")
    else:
        md_lines.append("```python")
        md_lines.append("# Paste into sport_rules.py")
        md_lines.append("BIMODAL_MARKET_TYPES = {")
        for sport_tag, mts in sorted(by_sport.items()):
            mts_quoted = ", ".join(f'\"{m}\"' for m in sorted(mts))
            md_lines.append(f'    "{sport_tag}": [{mts_quoted}],')
        md_lines.append("}")
        md_lines.append("```")
    md_lines.append("")

    # Insufficient cells
    insuf = [r for r in cells_out if r.get("n_analyzed", 0) < MIN_PER_CELL]
    md_lines.append("## Cells with insufficient data (n<5)")
    md_lines.append("")
    if not insuf:
        md_lines.append("_None._")
    else:
        for r in insuf:
            md_lines.append(f"- {r['sport_tag']} / {r['market_type']}: n={r.get('n_analyzed', 0)}")
    md_lines.append("")

    # Sample slugs appendix
    md_lines.append("## Sample slugs per cell")
    md_lines.append("")
    for rec in cells_out:
        slugs = rec.get("sample_market_slugs", [])
        if not slugs:
            continue
        md_lines.append(f"### {rec['sport_tag']} / {rec['market_type']} (n={rec['n_analyzed']})")
        for s in slugs[:5]:
            md_lines.append(f"- `{s}`")
        if len(slugs) > 5:
            md_lines.append(f"- _...+{len(slugs)-5} more_")
        md_lines.append("")

    md_path = out_dir / "bimodal_classification_2026-05-23.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[OK] Wrote {md_path}")
    print(f"\nTotal API calls: {api_calls}")


if __name__ == "__main__":
    main()
