"""
Throwaway diagnostic: backtest whether bookmaker Match O/U odds predicted
actual outcomes for the 13 resolved tennis O/U bets.

Usage: python scripts/backtest_tennis_ou_bookmaker.py
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.parse

# ── config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / ".env"
AUDIT_FILE = BASE_DIR / "logs" / "audit" / "trade_events.jsonl"
ODDS_BASE = "https://api.the-odds-api.com/v4"

ATP_KEYS = [
    "tennis_atp_french_open",
    "tennis_atp_queens",
    "tennis_atp_s_hertogenbosch",
    "tennis_atp_stuttgart",
    "tennis_atp_halle",
    "tennis_atp_eastbourne",
    "tennis_atp_nottingham",
]
WTA_KEYS = [
    "tennis_wta_french_open",
    "tennis_wta_queens_club_champ",
    "tennis_wta_s_hertogenbosch",
    "tennis_wta_berlin",
    "tennis_wta_nottingham",
    "tennis_wta_eastbourne",
    "tennis_wta_birmingham",
]


# ── helpers ───────────────────────────────────────────────────────────────────

def load_api_key() -> str:
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith("ODDS_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise ValueError("ODDS_API_KEY not found in .env")


def http_get(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        print(f"    [HTTP ERROR] {exc}")
        return None


def fetch_historical(api_key: str, sport_key: str, iso_ts: str) -> list[dict] | None:
    params = urllib.parse.urlencode({
        "apiKey": api_key,
        "regions": "us,uk,eu",
        "markets": "totals",
        "oddsFormat": "decimal",
        "date": iso_ts,
    })
    url = f"{ODDS_BASE}/historical/sports/{sport_key}/odds?{params}"
    result = http_get(url)
    if result is None:
        return None
    if isinstance(result, dict) and "data" in result:
        return result["data"]
    return None


def implied_prob(price: float) -> float:
    return 1.0 / price if price > 0 else 0.0


def bookmaker_over_prob(bookmakers: list[dict], line: float) -> tuple[float, int, bool]:
    """
    Returns (weighted_avg_over_prob, num_books_with_data, has_pinnacle).
    Finds outcome pair at closest line within ±1.0 of target.
    """
    probs = []
    has_pinnacle = False
    for bk in bookmakers:
        bk_title = bk.get("title", "").lower()
        if "pinnacle" in bk_title:
            has_pinnacle = True
        for market in bk.get("markets", []):
            if market.get("key") != "totals":
                continue
            outcomes = market.get("outcomes", [])
            over_out = None
            under_out = None
            best_delta = 999.0
            # find closest pair to target line
            for o in outcomes:
                pt = float(o.get("point", 0))
                delta = abs(pt - line)
                if delta < best_delta:
                    best_delta = delta
            if best_delta > 1.0:
                continue
            for o in outcomes:
                pt = float(o.get("point", 0))
                if abs(pt - line) == best_delta:
                    if o["name"].lower() == "over":
                        over_out = o
                    elif o["name"].lower() == "under":
                        under_out = o
            if over_out and under_out:
                o_raw = implied_prob(over_out["price"])
                u_raw = implied_prob(under_out["price"])
                total = o_raw + u_raw
                if total > 0:
                    probs.append(o_raw / total)
    if not probs:
        return (0.0, 0, has_pinnacle)
    return (sum(probs) / len(probs), len(probs), has_pinnacle)


def surnames_from_question(question: str) -> tuple[str, str]:
    """Extract two player surnames from 'X vs. Y: Match O/U L'"""
    parts = question.split(":")
    matchup = parts[0].strip()
    players = matchup.replace(" vs. ", " vs ").split(" vs ")
    if len(players) == 2:
        return players[0].strip().lower(), players[1].strip().lower()
    return ("", "")


def event_matches(event: dict, s1: str, s2: str) -> bool:
    home = event.get("home_team", "").lower()
    away = event.get("away_team", "").lower()
    # both surnames must appear somewhere in the team names
    for sn in [s1, s2]:
        found = False
        for nm in [home, away]:
            if sn in nm or any(part in nm for part in sn.split()):
                found = True
                break
        if not found:
            return False
    return True


# ── extract 13 O/U matches from audit ────────────────────────────────────────

def extract_ou_matches() -> list[dict]:
    lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    events: dict[str, dict] = {}  # condition_id -> combined info

    for raw in lines:
        row = json.loads(raw)
        cid = row.get("condition_id", "")
        kind = row.get("kind", "")
        sport = row.get("sport_tag", "")
        question = row.get("question", "")

        if sport != "tennis":
            continue
        if "O/U" not in question:
            continue

        if kind == "entry":
            events.setdefault(cid, {})
            events[cid]["question"] = question
            events[cid]["slug"] = row.get("slug", "")
            events[cid]["entry_price"] = row.get("entry_price")
            events[cid]["direction"] = row.get("direction")
            events[cid]["bookmaker_prob"] = row.get("bookmaker_prob")

        elif kind == "final":
            exit_reason = row.get("exit_reason", "")
            if exit_reason == "voided":
                # mark voided so we exclude
                events.setdefault(cid, {})
                events[cid]["voided"] = True
                continue
            events.setdefault(cid, {})
            events[cid]["exit_pnl"] = row.get("exit_pnl_usdc")
            events[cid]["exit_reason"] = exit_reason

    # filter: BUY_YES direction, not voided, has exit_pnl
    result = []
    for cid, info in events.items():
        if info.get("voided"):
            continue
        if info.get("direction") != "BUY_YES":
            continue
        if info.get("exit_pnl") is None:
            continue
        if "question" not in info:
            continue
        result.append({"condition_id": cid, **info})

    return result


# ── parse line from question ───────────────────────────────────────────────────

def parse_line(question: str) -> float:
    # "X vs. Y: Match O/U 22.5"
    parts = question.split("O/U")
    if len(parts) == 2:
        try:
            return float(parts[1].strip())
        except ValueError:
            pass
    return 0.0


def parse_date_from_slug(slug: str) -> str:
    """Extract YYYY-MM-DD from slug like atp-...-2026-06-07-match-..."""
    import re
    m = re.search(r"(\d{4}-\d{2}-\d{2})", slug)
    if m:
        return m.group(1)
    return ""


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    api_key = load_api_key()
    matches = extract_ou_matches()

    print(f"\nFound {len(matches)} resolved non-voided BUY_YES Match O/U bets\n")

    # Build table rows first (ground truth)
    rows = []
    for m in matches:
        q = m["question"]
        slug = m.get("slug", "")
        line = parse_line(q)
        date_str = parse_date_from_slug(slug)
        s1, s2 = surnames_from_question(q)
        actual_over = (m["exit_pnl"] > 0)
        is_atp = slug.startswith("atp-")
        rows.append({
            "question": q,
            "slug": slug,
            "line": line,
            "date": date_str,
            "s1": s1,
            "s2": s2,
            "actual_over": actual_over,
            "exit_pnl": m["exit_pnl"],
            "is_atp": is_atp,
            "bookmaker_prob": m.get("bookmaker_prob"),
            # to be filled
            "bk_over_prob": None,
            "num_books": 0,
            "has_pinnacle": False,
            "coverage": False,
        })

    # Sort by date for cleaner output
    rows.sort(key=lambda r: r["date"])

    print("--- GROUND TRUTH TABLE ---")
    print(f"{'#':<3} {'Match':<42} {'Line':<6} {'Date':<12} {'Actual':<8} {'PnL':>7}")
    print("-" * 82)
    for i, r in enumerate(rows, 1):
        actual_str = "OVER" if r["actual_over"] else "UNDER"
        print(f"{i:<3} {r['question'][:41]:<42} {r['line']:<6} {r['date']:<12} {actual_str:<8} {r['exit_pnl']:>7.2f}")

    # ── fetch bookmaker odds ───────────────────────────────────────────────────
    print("\n\n--- FETCHING BOOKMAKER O/U ODDS ---\n")

    # Cache: (sport_key, date_ts) -> data
    cache: dict[tuple, list | None] = {}

    # timestamps to try per date (T11:00Z, T16:00Z)
    def make_timestamps(date_str: str) -> list[str]:
        return [f"{date_str}T11:00:00Z", f"{date_str}T16:00:00Z"]

    for r in rows:
        date = r["date"]
        line = r["line"]
        s1, s2 = r["s1"], r["s2"]
        candidate_keys = ATP_KEYS if r["is_atp"] else WTA_KEYS

        print(f"  Searching: {r['question'][:50]}  (line={line}, date={date})")
        found = False

        for ts in make_timestamps(date):
            if found:
                break
            for sk in candidate_keys:
                cache_key = (sk, ts)
                if cache_key not in cache:
                    print(f"    Fetching {sk} @ {ts} ...", end=" ")
                    data = fetch_historical(api_key, sk, ts)
                    cache[cache_key] = data
                    if data is not None:
                        print(f"OK ({len(data)} events)")
                    else:
                        print("no data / 404")
                    time.sleep(0.3)  # gentle rate limiting

                data = cache[cache_key]
                if not data:
                    continue

                for event in data:
                    if event_matches(event, s1, s2):
                        bk_prob, nb, hp = bookmaker_over_prob(event.get("bookmakers", []), line)
                        if nb > 0:
                            r["bk_over_prob"] = bk_prob
                            r["num_books"] = nb
                            r["has_pinnacle"] = hp
                            r["coverage"] = True
                            print(f"    FOUND match: {event.get('home_team')} vs {event.get('away_team')}"
                                  f"  bk_over_prob={bk_prob:.3f}  n_books={nb}  pinnacle={hp}")
                            found = True
                            break
                if found:
                    break

        if not found:
            print(f"    NO COVERAGE\n")

    # ── analysis ──────────────────────────────────────────────────────────────
    print("\n\n" + "=" * 100)
    print("FINAL TABLE")
    print("=" * 100)
    header = (
        f"{'#':<3} {'Match':<42} {'Line':<5} {'Actual':<7} "
        f"{'BK_Over%':<10} {'BK_Lean':<9} {'Correct?':<9} "
        f"{'N_bks':<6} {'Pinn':<5}"
    )
    print(header)
    print("-" * 100)

    n_covered = 0
    n_correct = 0
    n_losers = 0          # bets we lost (actual UNDER)
    n_losers_bk_correct = 0  # of those, bookmaker leaned UNDER

    for i, r in enumerate(rows, 1):
        actual_str = "OVER" if r["actual_over"] else "UNDER"
        if r["coverage"] and r["bk_over_prob"] is not None:
            n_covered += 1
            bk_prob = r["bk_over_prob"]
            bk_lean = "OVER" if bk_prob > 0.5 else "UNDER"
            correct = (bk_lean == actual_str)
            if correct:
                n_correct += 1
            if not r["actual_over"]:
                n_losers += 1
                if bk_lean == "UNDER":
                    n_losers_bk_correct += 1
            pinn_str = "YES" if r["has_pinnacle"] else "no"
            correct_str = "YES" if correct else "NO"
            print(
                f"{i:<3} {r['question'][:41]:<42} {r['line']:<5} {actual_str:<7} "
                f"{bk_prob:.3f}     {bk_lean:<9} {correct_str:<9} "
                f"{r['num_books']:<6} {pinn_str:<5}"
            )
        else:
            print(
                f"{i:<3} {r['question'][:41]:<42} {r['line']:<5} {actual_str:<7} "
                f"{'—':<10} {'—':<9} {'—':<9} "
                f"{'—':<6} {'—':<5}  [NO COVERAGE]"
            )

    print("=" * 100)

    n_total = len(rows)
    n_losers_total = sum(1 for r in rows if not r["actual_over"])

    print(f"\n--- SUMMARY ---")
    print(f"Total O/U bets analyzed:        {n_total}")
    print(f"  OVER hit (wins):              {sum(1 for r in rows if r['actual_over'])}")
    print(f"  UNDER hit (losses):           {n_losers_total}")
    print(f"\nBookmaker coverage:             {n_covered}/{n_total}")
    if n_covered > 0:
        print(f"Directional accuracy (covered): {n_correct}/{n_covered} = {n_correct/n_covered*100:.1f}%")
        print(f"\nOn the {n_losers_total} bets where actual=UNDER (our losses):")
        covered_losers = sum(1 for r in rows if not r["actual_over"] and r["coverage"])
        print(f"  Covered losers:               {covered_losers}/{n_losers_total}")
        if covered_losers > 0:
            print(f"  Bookmaker leaned UNDER:       {n_losers_bk_correct}/{covered_losers} = "
                  f"{n_losers_bk_correct/covered_losers*100:.1f}%")
            print(f"  (Would have avoided/flipped these losers)")

        # Calibration loose check
        print("\n--- CALIBRATION (covered only) ---")
        covered = [(r["bk_over_prob"], r["actual_over"]) for r in rows if r["coverage"]]
        high = [(p, a) for p, a in covered if p >= 0.52]
        low  = [(p, a) for p, a in covered if p < 0.48]
        mid  = [(p, a) for p, a in covered if 0.48 <= p < 0.52]
        if high:
            rate = sum(1 for _, a in high if a) / len(high)
            print(f"  BK prob >= 0.52 (lean OVER):  {len(high)} bets, actual OVER rate = {rate:.2f}")
        if low:
            rate = sum(1 for _, a in low if a) / len(low)
            print(f"  BK prob < 0.48 (lean UNDER):  {len(low)} bets, actual OVER rate = {rate:.2f} (should be low)")
        if mid:
            rate = sum(1 for _, a in mid if a) / len(mid)
            print(f"  BK prob 0.48-0.52 (coin flip):{len(mid)} bets, actual OVER rate = {rate:.2f}")

    print("\n--- RECOMMENDATION ---")
    if n_covered == 0:
        print("VERDICT: ZERO bookmaker O/U coverage for tennis sub-markets.")
        print("Full removal is the only rational choice — no signal available.")
    elif n_covered < 5:
        print(f"VERDICT: Very low coverage ({n_covered}/13). Data too thin for reliable conclusions.")
    else:
        acc = n_correct / n_covered
        lc = n_losers_bk_correct / covered_losers if covered_losers > 0 else 0.0
        if acc >= 0.65 and lc >= 0.60:
            print(f"VERDICT: Bookmaker O/U shows decent directional accuracy ({acc:.0%}) and "
                  f"correctly identified {lc:.0%} of our losing Over bets. "
                  f"Routing to bookmaker is SUPPORTED by this small sample.")
        elif acc < 0.50:
            print(f"VERDICT: Bookmaker O/U accuracy ({acc:.0%}) is below coin-flip. "
                  f"Signal is near-random. Full removal is more sensible.")
        else:
            print(f"VERDICT: Mixed result ({acc:.0%} accuracy, {lc:.0%} of losers caught). "
                  f"Sample too small (n={n_covered}) for strong conclusion. "
                  f"Edge case — full removal is safer given uncertainty.")

    print(f"\n(Note: n={n_total} is a small sample. All conclusions should be treated as directional, "
          f"not statistically conclusive.)\n")


if __name__ == "__main__":
    main()
