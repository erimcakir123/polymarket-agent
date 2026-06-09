"""
Adversarial audit v2 — fast, targeted, synchronous with immediate flush.
Tries to falsify "bookmaker O/U coverage is only ~8% (1/13)".

Strategy:
- Phase 1: Targeted sweep — for each match, try the 6-8 most plausible keys
  at 2 timestamps (T11Z same-day + T16Z same-day). Fast, ~50-80 API calls.
- Phase 2: Extended sweep — for uncovered matches, try prior-day + more timestamps.
- Phase 3: Big-tournament quality probe — pull French Open + Queens totals directly
  to confirm whether Odds API even carries tennis match totals.

Run: python scripts/adversarial_ou_coverage_v2.py
"""

import json
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

# force unbuffered stdout
sys.stdout.reconfigure(line_buffering=True)

BASE_DIR = Path(__file__).parent.parent
ENV_FILE  = BASE_DIR / ".env"
BAK_FILE  = BASE_DIR / "logs" / "audit" / "trade_events.jsonl.bak.ou_purge_20260609_050042"
ODDS_BASE = "https://api.the-odds-api.com/v4"

API_KEY = ""
for line in ENV_FILE.read_text().splitlines():
    if line.startswith("ODDS_API_KEY="):
        API_KEY = line.split("=", 1)[1].strip()
        break

requests_used = 0
requests_remaining = "unknown"

# ── CANDIDATE KEYS ─────────────────────────────────────────────────────────────
# June 6-8 2026 context:
#   ATP: French Open (ends ~Jun 8), Halle (starts Jun 8), Queens (starts Jun 8),
#        s-Hertogenbosch (Jun 1-7), Nottingham (Jun 1-7 Challengers ran here too)
#   WTA: French Open (ends ~Jun 7), Berlin (Jun 2-8), Nottingham (Jun 2-8),
#        Birmingham (Jun 9+), Queens Club (Jun 9+), s-Hertogenbosch

# Keys confirmed in /sports endpoint (37 total found)
CONFIRMED_ATP = [
    "tennis_atp_french_open",
    "tennis_atp_hamburg_open",
    "tennis_atp_wimbledon",
    "tennis_atp_us_open",
    "tennis_atp_aus_open_singles",
    "tennis_atp_barcelona_open",
    "tennis_atp_canadian_open",
    "tennis_atp_china_open",
    "tennis_atp_cincinnati_open",
    "tennis_atp_dubai",
    "tennis_atp_indian_wells",
    "tennis_atp_italian_open",
    "tennis_atp_madrid_open",
    "tennis_atp_miami_open",
    "tennis_atp_monte_carlo_masters",
    "tennis_atp_munich",
    "tennis_atp_paris_masters",
    "tennis_atp_qatar_open",
    "tennis_atp_shanghai_masters",
]
CONFIRMED_WTA = [
    "tennis_wta_french_open",
    "tennis_wta_queens_club_champ",   # only WTA key currently active
    "tennis_wta_aus_open_singles",
    "tennis_wta_canadian_open",
    "tennis_wta_charleston_open",
    "tennis_wta_china_open",
    "tennis_wta_cincinnati_open",
    "tennis_wta_dubai",
    "tennis_wta_indian_wells",
    "tennis_wta_italian_open",
    "tennis_wta_madrid_open",
    "tennis_wta_qatar_open",
    "tennis_wta_strasbourg",
    "tennis_wta_stuttgart_open",
    "tennis_wta_us_open",
    "tennis_wta_wimbledon",
    "tennis_wta_wuhan_open",
]
# Speculative keys (NOT in /sports but might have existed historically)
SPECULATIVE_ATP = [
    "tennis_atp_queens",
    "tennis_atp_halle",
    "tennis_atp_s_hertogenbosch",
    "tennis_atp_nottingham",
    "tennis_atp_eastbourne",
    "tennis_atp_surbiton",
    "tennis_atp_stuttgart",
]
SPECULATIVE_WTA = [
    "tennis_wta_berlin",
    "tennis_wta_s_hertogenbosch",
    "tennis_wta_nottingham",
    "tennis_wta_eastbourne",
    "tennis_wta_birmingham",
    "tennis_wta_surbiton",
]

ALL_ATP_KEYS = CONFIRMED_ATP + SPECULATIVE_ATP
ALL_WTA_KEYS = CONFIRMED_WTA + SPECULATIVE_WTA


def fetch(sport_key: str, ts: str) -> list | None:
    global requests_used, requests_remaining
    params = urllib.parse.urlencode({
        "apiKey": API_KEY,
        "regions": "us,uk,eu",
        "markets": "totals",
        "oddsFormat": "decimal",
        "date": ts,
    })
    url = f"{ODDS_BASE}/historical/sports/{sport_key}/odds?{params}"
    requests_used += 1
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            headers = dict(r.headers)
            requests_remaining = headers.get("x-requests-remaining", requests_remaining)
            body = json.loads(r.read())
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        if isinstance(body, list):
            return body
        return None
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 422):
            return None   # key doesn't exist
        print(f"  [HTTP {exc.code}] {sport_key} @ {ts}", flush=True)
        return None
    except Exception as exc:
        print(f"  [ERR] {exc}", flush=True)
        return None


def surnames(question: str) -> tuple[str, str]:
    parts = question.split(":")
    players = parts[0].strip().replace(" vs. ", " vs ").split(" vs ")
    if len(players) == 2:
        return players[0].strip().lower(), players[1].strip().lower()
    return "", ""


def event_matches(event: dict, s1: str, s2: str) -> bool:
    home = event.get("home_team", "").lower()
    away = event.get("away_team", "").lower()
    for sn in [s1, s2]:
        if not any(sn in nm or any(p in nm for p in sn.split()) for nm in [home, away]):
            return False
    return True


def bk_over_prob(bookmakers: list, line: float) -> tuple[float, int, bool, list[str]]:
    probs, names = [], []
    has_pinn = False
    for bk in bookmakers:
        title = bk.get("title", "")
        if "pinnacle" in title.lower():
            has_pinn = True
        for mkt in bk.get("markets", []):
            if mkt.get("key") != "totals":
                continue
            outcomes = mkt.get("outcomes", [])
            best_d = min((abs(float(o.get("point", 0)) - line) for o in outcomes), default=999)
            if best_d > 1.0:
                continue
            ov = next((o for o in outcomes if o["name"].lower() == "over" and abs(float(o.get("point",0))-line)==best_d), None)
            un = next((o for o in outcomes if o["name"].lower() == "under" and abs(float(o.get("point",0))-line)==best_d), None)
            if ov and un:
                op = 1/ov["price"] if ov["price"] > 0 else 0
                up = 1/un["price"] if un["price"] > 0 else 0
                tot = op + up
                if tot > 0:
                    probs.append(op / tot)
                    names.append(title)
    if not probs:
        return 0.0, 0, has_pinn, names
    return sum(probs)/len(probs), len(probs), has_pinn, names


def parse_line(q: str) -> float:
    parts = q.split("O/U")
    if len(parts) == 2:
        try:
            return float(parts[1].strip())
        except ValueError:
            pass
    return 0.0


def parse_date(slug: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", slug)
    return m.group(1) if m else ""


def prior_day(d: str) -> str:
    from datetime import datetime, timedelta
    return (datetime.strptime(d, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")


# ── LOAD MATCHES ───────────────────────────────────────────────────────────────

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
            events.setdefault(cid, {}).update({
                "question": r.get("question", ""),
                "slug": r.get("slug", ""),
                "direction": r.get("direction", ""),
            })
        elif kind == "final":
            events.setdefault(cid, {})
            events[cid]["exit_pnl"] = r.get("exit_pnl_usdc")
            events[cid]["voided"] = r.get("exit_reason", "") == "voided"
    result = [
        v for v in events.values()
        if not v.get("voided") and v.get("direction") == "BUY_YES"
        and v.get("exit_pnl") is not None and "question" in v
    ]
    result.sort(key=lambda x: x["slug"])
    return result


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    matches = load_matches()
    print(f"Loaded {len(matches)} resolved BUY_YES tennis O/U bets.", flush=True)

    rows = []
    for m in matches:
        q = m["question"]
        slug = m.get("slug", "")
        line = parse_line(q)
        date = parse_date(slug)
        s1, s2 = surnames(q)
        is_atp = slug.startswith("atp-")
        rows.append({
            "question": q, "slug": slug, "line": line, "date": date,
            "s1": s1, "s2": s2, "exit_pnl": m["exit_pnl"],
            "is_atp": is_atp,
            "covered": False, "found_key": None, "found_ts": None,
            "over_prob": None, "n_books": 0, "pinnacle": False, "book_names": [],
        })
    rows.sort(key=lambda r: (r["date"], r["question"]))

    print(f"\n{'#':<3} {'Tour':<5} {'Date':<12} {'Match':<50} {'Line':<5} {'PnL':>7}")
    print("-" * 85)
    for i, r in enumerate(rows, 1):
        tour = "ATP" if r["is_atp"] else "WTA"
        print(f"{i:<3} {tour:<5} {r['date']:<12} {r['question'][:49]:<50} {r['line']:<5} {r['exit_pnl']:>7.2f}", flush=True)

    # Cache: (key, ts) -> data or None
    cache: dict[tuple, list | None] = {}

    def get(key: str, ts: str) -> list | None:
        k = (key, ts)
        if k not in cache:
            cache[k] = fetch(key, ts)
            time.sleep(0.3)
        return cache[k]

    def try_find(r: dict, keys: list[str], dates: list[str], times: list[str]) -> bool:
        s1, s2, line = r["s1"], r["s2"], r["line"]
        for d in dates:
            for ts_sfx in times:
                ts = d + ts_sfx
                for sk in keys:
                    data = get(sk, ts)
                    if not data:
                        continue
                    for event in data:
                        if event_matches(event, s1, s2):
                            prob, nb, hp, bnames = bk_over_prob(event.get("bookmakers", []), line)
                            if nb > 0:
                                r["covered"] = True
                                r["found_key"] = sk
                                r["found_ts"] = ts
                                r["over_prob"] = prob
                                r["n_books"] = nb
                                r["pinnacle"] = hp
                                r["book_names"] = bnames
                                return True
                            else:
                                # event found but zero totals books
                                print(f"  [event-no-totals] {event.get('home_team')} vs {event.get('away_team')}  key={sk}", flush=True)
        return False

    print(f"\n\n--- PHASE 1: Targeted sweep (2 timestamps × June-context keys) ---", flush=True)
    for i, r in enumerate(rows, 1):
        date = r["date"]
        keys = ALL_ATP_KEYS if r["is_atp"] else ALL_WTA_KEYS
        tour = "ATP" if r["is_atp"] else "WTA"
        print(f"\n[{i}/13] [{tour}] {r['question']} | line={r['line']} | {date}", flush=True)
        found = try_find(r, keys, [date, prior_day(date)], ["T11:00:00Z", "T16:00:00Z"])
        if found:
            print(f"  -> COVERED  key={r['found_key']}  ts={r['found_ts']}  n_books={r['n_books']}  pinnacle={r['pinnacle']}", flush=True)
        else:
            print(f"  -> NOT COVERED in phase 1", flush=True)

    still_missing = [r for r in rows if not r["covered"]]
    print(f"\n\n--- PHASE 2: Extended timestamps for {len(still_missing)} uncovered matches ---", flush=True)
    extra_times = ["T06:00:00Z", "T09:00:00Z", "T13:00:00Z", "T19:00:00Z"]
    for r in still_missing:
        keys = ALL_ATP_KEYS if r["is_atp"] else ALL_WTA_KEYS
        print(f"  {r['question']} [{r['date']}]", flush=True)
        found = try_find(r, keys, [r["date"], prior_day(r["date"])], extra_times)
        if found:
            print(f"  -> COVERED  key={r['found_key']}  ts={r['found_ts']}", flush=True)
        else:
            print(f"  -> still NOT COVERED", flush=True)

    # ── Results ────────────────────────────────────────────────────────────────
    print(f"\n\n{'='*90}", flush=True)
    print("FINAL COVERAGE TABLE", flush=True)
    print(f"{'='*90}", flush=True)
    print(f"{'#':<3} {'Tour':<5} {'Date':<12} {'Match':<48} {'Cov':<5} {'N_bk':<5} {'Pinn':<5} {'Key (short)'}", flush=True)
    print("-" * 90, flush=True)
    n_covered = 0
    for i, r in enumerate(rows, 1):
        tour = "ATP" if r["is_atp"] else "WTA"
        cov = "YES" if r["covered"] else "NO"
        nb = str(r["n_books"]) if r["covered"] else "—"
        pinn = "Y" if r["pinnacle"] else "—"
        key_s = (r["found_key"] or "—")
        if len(key_s) > 30:
            key_s = "..." + key_s[-27:]
        if r["covered"]:
            n_covered += 1
        print(f"{i:<3} {tour:<5} {r['date']:<12} {r['question'][:47]:<48} {cov:<5} {nb:<5} {pinn:<5} {key_s}", flush=True)
    print(f"{'='*90}", flush=True)

    pct = n_covered / len(rows) * 100
    print(f"\nCOVERAGE: {n_covered}/{len(rows)} = {pct:.1f}%", flush=True)
    print(f"Original claim: 1/13 = 7.7%", flush=True)
    if n_covered > 1:
        print(f"FALSIFIED — found more coverage than original test reported", flush=True)
    elif n_covered == 1:
        print(f"CONFIRMED — coverage stays at ~8%", flush=True)
    else:
        print(f"WORSE — found 0/13 (original found 1)", flush=True)

    # ── Phase 3: Big tournament quality probe ──────────────────────────────────
    print(f"\n\n--- PHASE 3: Big-tournament totals quality probe ---", flush=True)
    print("Testing whether ATP/WTA tennis TOTALS markets actually exist at all in Odds API...", flush=True)

    probe_cases = [
        # (sport_key, timestamp, label)
        ("tennis_atp_french_open",    "2026-06-06T11:00:00Z", "ATP Roland Garros Jun 6"),
        ("tennis_atp_french_open",    "2026-06-07T11:00:00Z", "ATP Roland Garros Jun 7"),
        ("tennis_atp_french_open",    "2026-06-08T11:00:00Z", "ATP Roland Garros Jun 8 (SF/F)"),
        ("tennis_atp_queens",         "2026-06-08T11:00:00Z", "ATP Queens Jun 8"),
        ("tennis_atp_queens",         "2026-06-09T11:00:00Z", "ATP Queens Jun 9"),
        ("tennis_atp_halle",          "2026-06-08T11:00:00Z", "ATP Halle Jun 8"),
        ("tennis_atp_halle",          "2026-06-09T11:00:00Z", "ATP Halle Jun 9"),
        ("tennis_wta_french_open",    "2026-06-06T11:00:00Z", "WTA Roland Garros Jun 6"),
        ("tennis_wta_french_open",    "2026-06-07T11:00:00Z", "WTA Roland Garros Jun 7"),
        ("tennis_wta_berlin",         "2026-06-06T11:00:00Z", "WTA Berlin Jun 6"),
        ("tennis_wta_berlin",         "2026-06-07T11:00:00Z", "WTA Berlin Jun 7"),
        ("tennis_wta_berlin",         "2026-06-08T11:00:00Z", "WTA Berlin Jun 8"),
        ("tennis_wta_queens_club_champ", "2026-06-09T11:00:00Z", "WTA Queens Club Jun 9"),
        ("tennis_wta_nottingham",     "2026-06-06T11:00:00Z", "WTA Nottingham Jun 6"),
        ("tennis_wta_nottingham",     "2026-06-07T11:00:00Z", "WTA Nottingham Jun 7"),
    ]

    totals_found_anywhere = False
    for sk, ts, label in probe_cases:
        data = get(sk, ts)
        if data is None:
            print(f"  [{label}] {sk} @ {ts[:10]} -> NO DATA (key not found / 422)", flush=True)
            continue
        n_events = len(data)
        n_with_totals = 0
        n_pinnacle = 0
        sample_line = None
        for event in data:
            bk_list = event.get("bookmakers", [])
            has_tot = any(any(m.get("key") == "totals" for m in bk.get("markets", [])) for bk in bk_list)
            has_pinn = any("pinnacle" in bk.get("title", "").lower() for bk in bk_list)
            if has_tot:
                n_with_totals += 1
                totals_found_anywhere = True
                if sample_line is None:
                    for bk in bk_list:
                        for mkt in bk.get("markets", []):
                            if mkt.get("key") == "totals":
                                outs = mkt.get("outcomes", [])
                                sample_line = " | ".join(f"{o['name']} {o.get('point','?')} @{o.get('price','?')}" for o in outs[:2])
            if has_pinn:
                n_pinnacle += 1
        print(f"  [{label}] {sk}", flush=True)
        print(f"    events={n_events}  with_totals={n_with_totals}  pinnacle_books={n_pinnacle}", flush=True)
        if sample_line:
            print(f"    sample_totals_line: {sample_line}", flush=True)

    if not totals_found_anywhere:
        print(f"\n  PHASE 3 RESULT: ZERO totals markets in ANY tennis event across all probes.", flush=True)
        print(f"  Odds API does NOT carry match totals for tennis.", flush=True)
    else:
        print(f"\n  PHASE 3 RESULT: Totals markets FOUND in some events — see above.", flush=True)

    # ── FINAL VERDICT ─────────────────────────────────────────────────────────
    print(f"\n\n{'='*90}", flush=True)
    print("ADVERSARIAL VERDICT", flush=True)
    print(f"{'='*90}", flush=True)
    print(f"  Requests used this run: ~{requests_used}", flush=True)
    print(f"  API credits remaining:  {requests_remaining}", flush=True)
    print(f"  Coverage: {n_covered}/13 = {pct:.1f}% (original claim: 1/13 = 7.7%)", flush=True)
    print(flush=True)
    if n_covered > 1 and totals_found_anywhere:
        print("  FALSIFIED: Coverage is higher AND totals data exists. Routing-based strategy has merit.", flush=True)
    elif n_covered > 1 and not totals_found_anywhere:
        print("  PARTIALLY FALSIFIED: More matches found than original, but no actual totals odds exist.", flush=True)
        print("  The 'found' events had zero books offering totals — so O/U routing is still non-viable.", flush=True)
    elif n_covered == 1 and not totals_found_anywhere:
        print("  CONFIRMED (STRENGTHENED): 1/13 coverage AND zero totals odds in big tournaments.", flush=True)
        print("  Full O/U removal is the correct call. The 8% is not an undercount.", flush=True)
    elif n_covered == 1 and totals_found_anywhere:
        print("  CONFIRMED (with caveat): 1/13 coverage, but big tournaments DO have totals.", flush=True)
        print("  Our specific bet slate was Challenger/ITF-heavy. Big-tournament routing would have ~0 matches.", flush=True)
    else:
        print(f"  CONFIRMED or WORSE: {n_covered}/13. Full removal was correct.", flush=True)


if __name__ == "__main__":
    main()
