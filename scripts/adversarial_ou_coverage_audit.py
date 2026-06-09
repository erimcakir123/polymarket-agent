"""
Adversarial audit: try to FALSIFY the claim that bookmaker O/U coverage
for our 13 tennis Match O/U bets is only ~8% (1/13).

Attack vectors:
1. Expand sport_key search to ALL tennis keys returned by /sports (not just the
   7 ATP + 7 WTA used in the original backtest).
2. Try additional keys not in the /sports list (e.g. queens, halle, s_hertogenbosch,
   nottingham, berlin, stuttgart for both ATP+WTA, plus challenger keys).
3. Try a wider time-window (T06, T09, T11, T13, T16, T19 UTC) — maybe prior-day
   data would show open totals.
4. Also probe the PRIOR DAY for each match (markets open day-before).
5. Check if big-tournament O/U (French Open, Queens) has real Pinnacle data
   even when our specific matches weren't found.

Usage: python scripts/adversarial_ou_coverage_audit.py
"""

import json
import os
import re
import sys
import time
from pathlib import Path
import urllib.request
import urllib.parse

# ── paths / config ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / ".env"
BAK_FILE = BASE_DIR / "logs" / "audit" / "trade_events.jsonl.bak.ou_purge_20260609_050042"
ODDS_BASE = "https://api.the-odds-api.com/v4"

API_KEY = ""
REQUESTS_USED = 0
REQUESTS_REMAINING = "?"


def load_api_key() -> str:
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith("ODDS_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise ValueError("ODDS_API_KEY not found")


# ── ALL candidate sport keys to probe ─────────────────────────────────────────
# Original backtest used 7 ATP + 7 WTA.
# We expand to every key in /sports PLUS speculative keys for grass-court weeks.
KNOWN_TENNIS_KEYS = [
    # ATP Grand Slams
    "tennis_atp_french_open",
    "tennis_atp_wimbledon",
    "tennis_atp_us_open",
    "tennis_atp_aus_open_singles",
    # ATP 500s
    "tennis_atp_queens",            # Queens Club ATP 500 (not in /sports list!)
    "tennis_atp_halle",             # Halle ATP 500 (not in /sports list!)
    "tennis_atp_hamburg_open",
    # ATP 250s
    "tennis_atp_s_hertogenbosch",   # Libema Open
    "tennis_atp_nottingham",
    "tennis_atp_stuttgart",
    "tennis_atp_eastbourne",
    "tennis_atp_surbiton",
    # ATP other
    "tennis_atp_barcelona_open",
    "tennis_atp_monte_carlo_masters",
    "tennis_atp_italian_open",
    "tennis_atp_madrid_open",
    "tennis_atp_munich",
    "tennis_atp_canadian_open",
    "tennis_atp_cincinnati_open",
    "tennis_atp_china_open",
    "tennis_atp_shanghai_masters",
    "tennis_atp_paris_masters",
    "tennis_atp_indian_wells",
    "tennis_atp_dubai",
    "tennis_atp_qatar_open",
    "tennis_atp_miami_open",
    # WTA Grand Slams
    "tennis_wta_french_open",
    "tennis_wta_wimbledon",
    "tennis_wta_us_open",
    "tennis_wta_aus_open_singles",
    # WTA events
    "tennis_wta_queens_club_champ",
    "tennis_wta_s_hertogenbosch",
    "tennis_wta_berlin",
    "tennis_wta_nottingham",
    "tennis_wta_eastbourne",
    "tennis_wta_birmingham",
    "tennis_wta_surbiton",
    "tennis_wta_strasbourg",
    "tennis_wta_stuttgart_open",
    "tennis_wta_italian_open",
    "tennis_wta_madrid_open",
    "tennis_wta_canadian_open",
    "tennis_wta_cincinnati_open",
    "tennis_wta_china_open",
    "tennis_wta_indian_wells",
    "tennis_wta_dubai",
    "tennis_wta_charleston_open",
    "tennis_wta_miami_open",
    "tennis_wta_qatar_open",
    "tennis_wta_wuhan_open",
]

# Speculative keys that MIGHT exist but aren't in the /sports list
SPECULATIVE_KEYS = [
    "tennis_atp_queens",
    "tennis_atp_halle",
    "tennis_atp_eastbourne",
    "tennis_atp_surbiton",
    "tennis_atp_nottingham",
    "tennis_wta_s_hertogenbosch",
    "tennis_wta_berlin",
    "tennis_wta_nottingham",
    "tennis_wta_eastbourne",
    "tennis_wta_birmingham",
    "tennis_wta_surbiton",
]

# Time-of-day probes — try 6 different UTC hours per date
TIME_PROBES = ["T06:00:00Z", "T09:00:00Z", "T11:00:00Z", "T13:00:00Z", "T16:00:00Z", "T19:00:00Z"]


def http_get(url: str) -> tuple[dict | list | None, dict]:
    global REQUESTS_REMAINING
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            headers = dict(resp.headers)
            REQUESTS_REMAINING = headers.get("x-requests-remaining", REQUESTS_REMAINING)
            return json.loads(resp.read()), headers
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            return None, {}  # key doesn't exist / no data for date
        print(f"    [HTTP {exc.code}] {url[-80:]}")
        return None, {}
    except Exception as exc:
        print(f"    [ERROR] {exc}")
        return None, {}


def fetch_historical(sport_key: str, iso_ts: str) -> list[dict] | None:
    global REQUESTS_USED
    params = urllib.parse.urlencode({
        "apiKey": API_KEY,
        "regions": "us,uk,eu",
        "markets": "totals",
        "oddsFormat": "decimal",
        "date": iso_ts,
    })
    url = f"{ODDS_BASE}/historical/sports/{sport_key}/odds?{params}"
    REQUESTS_USED += 1
    result, _ = http_get(url)
    if result is None:
        return None
    if isinstance(result, dict) and "data" in result:
        return result["data"]
    if isinstance(result, list):
        return result
    return None


def implied_prob(price: float) -> float:
    return 1.0 / price if price > 0 else 0.0


def bookmaker_over_prob(bookmakers: list[dict], line: float) -> tuple[float, int, bool, list[str]]:
    probs = []
    has_pinnacle = False
    book_names = []
    for bk in bookmakers:
        bk_title = bk.get("title", "")
        if "pinnacle" in bk_title.lower():
            has_pinnacle = True
        for market in bk.get("markets", []):
            if market.get("key") != "totals":
                continue
            outcomes = market.get("outcomes", [])
            best_delta = 999.0
            for o in outcomes:
                pt = float(o.get("point", 0))
                delta = abs(pt - line)
                if delta < best_delta:
                    best_delta = delta
            if best_delta > 1.0:
                continue
            over_out = under_out = None
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
                    book_names.append(bk_title)
    if not probs:
        return 0.0, 0, has_pinnacle, book_names
    return sum(probs) / len(probs), len(probs), has_pinnacle, book_names


def surnames_from_question(question: str) -> tuple[str, str]:
    parts = question.split(":")
    matchup = parts[0].strip()
    players = matchup.replace(" vs. ", " vs ").split(" vs ")
    if len(players) == 2:
        return players[0].strip().lower(), players[1].strip().lower()
    return "", ""


def event_matches(event: dict, s1: str, s2: str) -> bool:
    home = event.get("home_team", "").lower()
    away = event.get("away_team", "").lower()
    for sn in [s1, s2]:
        found = any(sn in nm or any(p in nm for p in sn.split()) for nm in [home, away])
        if not found:
            return False
    return True


def parse_line(question: str) -> float:
    parts = question.split("O/U")
    if len(parts) == 2:
        try:
            return float(parts[1].strip())
        except ValueError:
            pass
    return 0.0


def parse_date_from_slug(slug: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", slug)
    return m.group(1) if m else ""


def prior_day(date_str: str) -> str:
    from datetime import datetime, timedelta
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return (d - timedelta(days=1)).strftime("%Y-%m-%d")


# ── load the 13 matches ────────────────────────────────────────────────────────

def load_matches() -> list[dict]:
    lines = BAK_FILE.read_text(encoding="utf-8").splitlines()
    events: dict[str, dict] = {}
    for raw in lines:
        r = json.loads(raw)
        if r.get("sport_tag") != "tennis" or "O/U" not in r.get("question", ""):
            continue
        cid = r.get("condition_id", "")
        kind = r.get("kind", "")
        if kind == "entry":
            events.setdefault(cid, {})
            events[cid].update({
                "question": r.get("question", ""),
                "slug": r.get("slug", ""),
                "direction": r.get("direction", ""),
            })
        elif kind == "final":
            events.setdefault(cid, {})
            events[cid]["exit_pnl"] = r.get("exit_pnl_usdc")
            events[cid]["exit_reason"] = r.get("exit_reason", "")
            events[cid]["voided"] = r.get("exit_reason", "") == "voided"

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
        result.append(info)
    result.sort(key=lambda r: r["slug"])
    return result


# ── determine which keys to try per match ─────────────────────────────────────

def candidate_keys_for_match(slug: str, question: str) -> list[str]:
    """
    Heuristic: based on player names + date, guess which tournament(s) likely apply.
    Also return ALL keys so we exhaustively sweep.
    """
    is_atp = slug.startswith("atp-")
    q_lower = question.lower()
    date_str = parse_date_from_slug(slug)
    s1, s2 = surnames_from_question(question)

    # Big-name player heuristics
    big_atp = {"cilic", "shapovalov", "borges"}    # Borges ~50 ATP, could be Queens/Halle
    big_wta = {"badosa", "samsonova", "dart", "kvitova", "pegula", "semenistaja", "snigur"}

    primary_keys = []
    # June 6-8 context
    if is_atp:
        primary_keys += [
            "tennis_atp_queens",
            "tennis_atp_halle",
            "tennis_atp_french_open",
            "tennis_atp_s_hertogenbosch",
            "tennis_atp_nottingham",
            "tennis_atp_stuttgart",
            "tennis_atp_eastbourne",
        ]
        if any(p in {s1, s2} for p in big_atp):
            # Cilic+Shapovalov: French Open ended ~Jun 8, Halle starts Jun 8, Queens starts Jun 8
            primary_keys = ["tennis_atp_french_open", "tennis_atp_queens", "tennis_atp_halle"] + primary_keys
    else:
        primary_keys += [
            "tennis_wta_french_open",
            "tennis_wta_queens_club_champ",
            "tennis_wta_berlin",
            "tennis_wta_s_hertogenbosch",
            "tennis_wta_nottingham",
            "tennis_wta_eastbourne",
            "tennis_wta_birmingham",
        ]
        if any(p in {s1, s2} for p in big_wta):
            primary_keys = ["tennis_wta_french_open", "tennis_wta_berlin", "tennis_wta_queens_club_champ"] + primary_keys

    # Deduplicate preserving order
    seen = set()
    deduped = []
    for k in primary_keys + KNOWN_TENNIS_KEYS:
        if k not in seen:
            seen.add(k)
            deduped.append(k)
    return deduped


# ── probe: big-tournament quality test ────────────────────────────────────────

def probe_big_tournament_quality() -> None:
    """
    Pull totals data for Queens (ATP 500, June 8) and Roland Garros (June 6-8)
    to assess: do bookmakers actually offer match totals? Does Pinnacle appear?
    """
    print("\n" + "=" * 90)
    print("PROBE: Big-tournament O/U quality (Queens ATP / French Open / Berlin WTA)")
    print("=" * 90)

    probes = [
        ("tennis_atp_french_open", "2026-06-06T11:00:00Z", "ATP French Open June 6"),
        ("tennis_atp_french_open", "2026-06-08T11:00:00Z", "ATP French Open June 8 (final days)"),
        ("tennis_atp_queens",      "2026-06-08T11:00:00Z", "ATP Queens June 8 (R1)"),
        ("tennis_atp_queens",      "2026-06-08T16:00:00Z", "ATP Queens June 8 (R1, later)"),
        ("tennis_atp_halle",       "2026-06-08T11:00:00Z", "ATP Halle June 8 (R1)"),
        ("tennis_wta_french_open", "2026-06-06T11:00:00Z", "WTA French Open June 6"),
        ("tennis_wta_berlin",      "2026-06-08T11:00:00Z", "WTA Berlin June 8"),
        ("tennis_wta_berlin",      "2026-06-08T16:00:00Z", "WTA Berlin June 8 (later)"),
        ("tennis_wta_queens_club_champ", "2026-06-08T11:00:00Z", "WTA Queens Club June 8"),
        ("tennis_wta_nottingham",  "2026-06-06T11:00:00Z", "WTA Nottingham June 6"),
        ("tennis_wta_nottingham",  "2026-06-08T11:00:00Z", "WTA Nottingham June 8"),
    ]

    found_totals_any = False
    for sport_key, ts, label in probes:
        print(f"\n  [{label}] -> {sport_key} @ {ts}")
        data = fetch_historical(sport_key, ts)
        time.sleep(0.4)
        if not data:
            print(f"    NO DATA (key doesn't exist or no events at this timestamp)")
            continue
        print(f"    {len(data)} events found")
        totals_events = 0
        pinnacle_events = 0
        sample_shown = 0
        for event in data:
            bookmakers = event.get("bookmakers", [])
            has_totals = any(
                any(m.get("key") == "totals" for m in bk.get("markets", []))
                for bk in bookmakers
            )
            has_pinnacle = any("pinnacle" in bk.get("title", "").lower() for bk in bookmakers)
            if has_totals:
                totals_events += 1
                found_totals_any = True
            if has_pinnacle:
                pinnacle_events += 1
            if has_totals and sample_shown < 3:
                book_list = [bk["title"] for bk in bookmakers if any(m.get("key") == "totals" for m in bk.get("markets", []))]
                # Show line + odds for first bookmaker
                for bk in bookmakers[:1]:
                    for mkt in bk.get("markets", []):
                        if mkt.get("key") == "totals":
                            outcomes = mkt.get("outcomes", [])
                            line_str = " | ".join(f"{o['name']} {o.get('point','?')} @ {o.get('price','?')}" for o in outcomes[:2])
                print(f"    TOTALS: {event.get('home_team','?')} vs {event.get('away_team','?')}")
                print(f"      books_with_totals: {book_list}")
                print(f"      sample line: {line_str}")
                sample_shown += 1

        print(f"    -> events_with_totals: {totals_events}/{len(data)}  pinnacle_events: {pinnacle_events}/{len(data)}")

    if not found_totals_any:
        print("\n  RESULT: ZERO totals markets found across all big-tournament probes.")
    else:
        print("\n  RESULT: Totals markets found — see detail above.")


# ── main exhaustive sweep ──────────────────────────────────────────────────────

def main() -> None:
    global API_KEY
    API_KEY = load_api_key()

    matches = load_matches()
    print(f"\nLoaded {len(matches)} resolved BUY_YES Match O/U bets from backup.\n")

    # Annotate
    rows = []
    for m in matches:
        q = m["question"]
        slug = m.get("slug", "")
        line = parse_line(q)
        date_str = parse_date_from_slug(slug)
        s1, s2 = surnames_from_question(q)
        is_atp = slug.startswith("atp-")
        rows.append({
            "question": q,
            "slug": slug,
            "line": line,
            "date": date_str,
            "s1": s1,
            "s2": s2,
            "exit_pnl": m["exit_pnl"],
            "is_atp": is_atp,
            "coverage": False,
            "found_in_key": None,
            "found_at_ts": None,
            "bk_over_prob": None,
            "num_books": 0,
            "has_pinnacle": False,
            "book_names": [],
        })
    rows.sort(key=lambda r: r["date"])

    # Print match list
    print("--- 13 MATCHES TO TEST ---")
    print(f"{'#':<3} {'Tour':<5} {'Date':<12} {'Match':<52} {'Line':<6} {'PnL':>7}")
    print("-" * 90)
    for i, r in enumerate(rows, 1):
        tour = "ATP" if r["is_atp"] else "WTA"
        print(f"{i:<3} {tour:<5} {r['date']:<12} {r['question'][:51]:<52} {r['line']:<6} {r['exit_pnl']:>7.2f}")

    # Cache: (sport_key, timestamp) -> data
    cache: dict[tuple, list | None] = {}

    def get_cached(sport_key: str, ts: str) -> list | None:
        k = (sport_key, ts)
        if k not in cache:
            data = fetch_historical(sport_key, ts)
            cache[k] = data
            status = f"OK ({len(data)} events)" if data else "no data"
            # Only print if data found (reduce noise)
            if data:
                print(f"      [FETCH] {sport_key} @ {ts} -> {status}")
            time.sleep(0.35)
        return cache[k]

    print("\n\n--- EXHAUSTIVE COVERAGE SWEEP ---")
    print("(Testing ALL tennis keys × ALL timestamps × same-day + prior-day)\n")

    for r in rows:
        date = r["date"]
        prev = prior_day(date)
        line = r["line"]
        s1, s2 = r["s1"], r["s2"]
        tour = "ATP" if r["is_atp"] else "WTA"

        print(f"\n[{tour}] {r['question']} (line={line}, date={date})")

        cand_keys = candidate_keys_for_match(r["slug"], r["question"])
        # dates to try: prior day + match day
        dates_to_try = [prev, date]

        found = False
        for d in dates_to_try:
            if found:
                break
            for ts_suffix in TIME_PROBES:
                if found:
                    break
                ts = d + ts_suffix
                for sk in cand_keys:
                    if found:
                        break
                    data = get_cached(sk, ts)
                    if not data:
                        continue
                    for event in data:
                        if event_matches(event, s1, s2):
                            bk_prob, nb, hp, bnames = bookmaker_over_prob(
                                event.get("bookmakers", []), line
                            )
                            if nb > 0:
                                r["coverage"] = True
                                r["found_in_key"] = sk
                                r["found_at_ts"] = ts
                                r["bk_over_prob"] = bk_prob
                                r["num_books"] = nb
                                r["has_pinnacle"] = hp
                                r["book_names"] = bnames
                                print(f"  *** COVERED *** key={sk}  ts={ts}")
                                print(f"      event: {event.get('home_team')} vs {event.get('away_team')}")
                                print(f"      bk_over_prob={bk_prob:.3f}  n_books={nb}  pinnacle={hp}")
                                print(f"      books: {bnames[:5]}")
                                found = True
                                break
                            else:
                                # Event found but NO totals odds
                                print(f"  [event found, but NO totals odds] key={sk}  {event.get('home_team')} vs {event.get('away_team')}")

        if not found:
            print(f"  -> NO COVERAGE across all {len(cand_keys)} keys × {len(dates_to_try)*len(TIME_PROBES)} timestamps")

    # ── Results ──────────────────────────────────────────────────────────────
    print("\n\n" + "=" * 90)
    print("FINAL COVERAGE TABLE (Adversarial Audit)")
    print("=" * 90)
    print(f"{'#':<3} {'Tour':<5} {'Date':<12} {'Match':<45} {'Covered':<8} {'Key':<35} {'N_bks':<6} {'Pinn'}")
    print("-" * 90)

    n_covered = 0
    for i, r in enumerate(rows, 1):
        tour = "ATP" if r["is_atp"] else "WTA"
        cov = "YES" if r["coverage"] else "NO"
        key_short = (r["found_in_key"] or "—")[-35:]
        pinn = "YES" if r["has_pinnacle"] else "—"
        nb = str(r["num_books"]) if r["coverage"] else "—"
        if r["coverage"]:
            n_covered += 1
        print(f"{i:<3} {tour:<5} {r['date']:<12} {r['question'][:44]:<45} {cov:<8} {key_short:<35} {nb:<6} {pinn}")

    n_total = len(rows)
    pct = n_covered / n_total * 100 if n_total > 0 else 0

    print("=" * 90)
    print(f"\n--- COVERAGE SUMMARY ---")
    print(f"Matches tested:       {n_total}")
    print(f"Covered:              {n_covered}")
    print(f"Coverage rate:        {n_covered}/{n_total} = {pct:.1f}%")
    print(f"\nNew vs original (1/13 = 7.7%):")
    if n_covered > 1:
        print(f"  FALSIFIED — coverage is higher than 8% (found {n_covered}/13 = {pct:.1f}%)")
    elif n_covered == 1:
        print(f"  CONFIRMED — coverage remains at ~8% (1/13)")
    else:
        print(f"  CONFIRMED (or worse) — coverage is 0/13 = 0%")

    print(f"\nRequests used this run: ~{REQUESTS_USED}")
    print(f"API credits remaining:  {REQUESTS_REMAINING}")

    # Detail for covered matches
    if n_covered > 0:
        print("\n--- COVERED MATCHES DETAIL ---")
        for r in rows:
            if r["coverage"]:
                actual_str = "OVER" if r["exit_pnl"] > 0 else "UNDER"
                bk_lean = "OVER" if r["bk_over_prob"] > 0.5 else "UNDER"
                correct = (bk_lean == actual_str)
                print(f"  {r['question']}")
                print(f"    key={r['found_in_key']}, ts={r['found_at_ts']}")
                print(f"    bk_over_prob={r['bk_over_prob']:.3f}, books={r['num_books']}, pinnacle={r['has_pinnacle']}")
                print(f"    actual={actual_str}, bk_lean={bk_lean}, correct={correct}")
                print(f"    books: {r['book_names']}")

    # ── Big tournament quality probe ──────────────────────────────────────────
    probe_big_tournament_quality()

    print(f"\n--- TOTAL API REQUESTS USED ---")
    print(f"  ~{REQUESTS_USED} (each historical fetch = 1 credit)")
    print(f"  Remaining: {REQUESTS_REMAINING}")

    # ── ADVERSARIAL VERDICT ────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("ADVERSARIAL VERDICT")
    print("=" * 90)

    print(f"\nCoverage after exhaustive search: {n_covered}/{n_total} = {pct:.1f}%")

    # Classify each match
    print("\nPer-match classification:")
    for i, r in enumerate(rows, 1):
        tour = "ATP" if r["is_atp"] else "WTA"
        s1, s2 = r["s1"], r["s2"]
        # Heuristic classification
        big_players = {"cilic", "shapovalov", "borges", "badosa", "samsonova", "dart"}
        is_big = any(p in {s1, s2} for p in big_players)
        tier = "MAIN_TOUR?" if is_big else "CHALLENGER/ITF?"
        cov = "COVERED" if r["coverage"] else "NOT_COVERED"
        print(f"  {i:2}. [{tour}] {r['question'][:48]:<50} {tier:<16} {cov}")

    if n_covered <= 1:
        print("\nCONCLUSION: The ~8% (1/13) coverage claim is ROBUST.")
        print("  Exhaustive search across all known tennis sport keys + all timestamps")
        print("  + prior-day probing does NOT reveal hidden coverage.")
        print("  Most matches are Challenger/ITF level where bookmakers don't offer totals.")
        print("  Full O/U removal is NOT an over-correction.")
    elif n_covered <= 3:
        print(f"\nCONCLUSION: Coverage is LOW ({n_covered}/13 = {pct:.1f}%) but slightly")
        print("  higher than the original 8%. Still too thin for a reliable routing strategy.")
        print("  Routing 'big tournament only' would miss ~{100-pct:.0f}% of our actual bet slate.")
    else:
        print(f"\nCONCLUSION: Coverage is materially higher ({n_covered}/13 = {pct:.1f}%).")
        print("  The 8% claim was UNDERCOUNTED — possibly wrong sport keys in original test.")
        print("  A big-tournament routing strategy deserves further analysis.")


if __name__ == "__main__":
    main()
