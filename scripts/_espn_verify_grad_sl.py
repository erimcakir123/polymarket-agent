"""ESPN'den top N graduated_sl trade'in gercek sonuclarini cek."""
import json
import re
import httpx
from pathlib import Path
from datetime import datetime

files = []
for root in ["_archive", "logs"]:
    files.extend(Path(root).rglob("trade_history*.jsonl*"))
seen = set()
trades = []
for f in files:
    try:
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                key = (r.get("condition_id", ""), r.get("entry_timestamp", ""))
                if key in seen:
                    continue
                seen.add(key)
                trades.append(r)
    except Exception:
        pass

grad = [t for t in trades
        if t.get("exit_reason") == "graduated_sl" and t.get("exit_pnl_usdc") is not None]
grad.sort(key=lambda t: abs(t["exit_pnl_usdc"]), reverse=True)

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"


def date_from_slug_or_iso(t):
    slug = t.get("slug", "")
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", slug)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    iso = t.get("match_start_iso", "") or t.get("entry_timestamp", "")
    if iso:
        try:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return dt.strftime("%Y%m%d")
        except Exception:
            pass
    return None


def sport_league_from_slug(slug, sport_tag):
    s = slug.lower()
    st = (sport_tag or "").lower()
    if s.startswith("atp-") or st == "atp":
        return "tennis", "atp"
    if s.startswith("wta-") or st == "wta":
        return "tennis", "wta"
    if s.startswith("nba-") or st == "nba":
        return "basketball", "nba"
    if s.startswith("wnba-") or st == "wnba":
        return "basketball", "wnba"
    if s.startswith("mlb-") or st == "mlb":
        return "baseball", "mlb"
    if s.startswith("nhl-") or st == "nhl":
        return "hockey", "nhl"
    if s.startswith("nfl-") or st == "nfl":
        return "football", "nfl"
    return None, None


_CACHE = {}


def fetch_espn(sport, league, date):
    k = (sport, league, date)
    if k in _CACHE:
        return _CACHE[k]
    url = f"{ESPN_BASE}/{sport}/{league}/scoreboard?dates={date}"
    try:
        r = httpx.get(url, timeout=10)
        if r.status_code != 200:
            _CACHE[k] = None
            return None
        data = r.json()
        _CACHE[k] = data
        return data
    except Exception:
        _CACHE[k] = None
        return None


def extract_names_from_slug(slug):
    s = slug.lower()
    s = re.sub(r"-\d{4}-\d{2}-\d{2}.*$", "", s)
    s = re.sub(r"^(atp|wta|nba|wnba|mlb|nhl|nfl)-", "", s)
    parts = s.split("-")
    return [p for p in parts if p]


def match_event(events, slug_parts, question):
    q_lower = (question or "").lower()
    q_words = [w for w in re.split(r"[^a-z]+", q_lower) if len(w) >= 4]
    for ev in events:
        name = ev.get("name", "").lower()
        short = ev.get("shortName", "").lower()
        for part in slug_parts:
            if len(part) >= 4 and (part in name or part in short):
                return ev
        for word in q_words:
            if word in name or word in short:
                return ev
    return None


TOP_N = 50
print(f"=== Top {TOP_N} graduated_sl trade'i ESPN'den dogrulama ===\n")

verified = []
unmatched = []

for t in grad[:TOP_N]:
    slug = t.get("slug", "")
    sport, league = sport_league_from_slug(slug, t.get("sport_tag"))
    date = date_from_slug_or_iso(t)
    if not sport or not date:
        unmatched.append((t, "SPORT_OR_DATE_FAIL"))
        continue
    data = fetch_espn(sport, league, date)
    if not data:
        unmatched.append((t, f"ESPN_FETCH_FAIL ({league}/{date})"))
        continue
    events = data.get("events", [])
    parts = extract_names_from_slug(slug)
    ev = match_event(events, parts, t.get("question", ""))
    if not ev:
        unmatched.append((t, f"NO_MATCH ({league}/{date}, {len(events)} events)"))
        continue
    comps = ev.get("competitions", [])
    if not comps:
        unmatched.append((t, "NO_COMP"))
        continue
    competitors = comps[0].get("competitors", [])
    if len(competitors) < 2:
        unmatched.append((t, "FEWER_THAN_2_TEAMS"))
        continue
    status = ev.get("status", {}).get("type", {}).get("description", "")
    if status != "Final":
        unmatched.append((t, f"NOT_FINAL ({status})"))
        continue
    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
    try:
        home_score = int(home.get("score", "0") or 0)
        away_score = int(away.get("score", "0") or 0)
    except Exception:
        home_score = away_score = 0
    home_name = home.get("team", {}).get("displayName", "?")
    away_name = away.get("team", {}).get("displayName", "?")
    home_winner = bool(home.get("winner", home_score > away_score))
    verified.append((t, {
        "name": ev.get("name"),
        "short": ev.get("shortName"),
        "home_name": home_name, "home_score": home_score, "home_winner": home_winner,
        "away_name": away_name, "away_score": away_score,
    }))

print(f"ESPN'den dogrulanan: {len(verified)}/{TOP_N}\n")

# ----------------- HELD ANALYSIS -----------------
# For each verified trade, determine actual outcome of held position.
# Logic:
#   moneyline: Position direction is BUY_YES (we bet home=YES) or BUY_NO (away).
#              Position WINS if (direction_implied_home_won) match outcome aligns.
#   For totals: YES=over, NO=under, total = home+away
#   For set_handicap, spread: too complex to extract from slug, mark uncertain
#
# Slug parts: ["jones","vukic"]. If slug parts in [home_name.lower(), away_name.lower()]:
#   First slug part is usually 'home' in question (e.g., "Jones vs Vukic") but Polymarket
#   convention is YES=first-mentioned. We'll heuristic-map.

def position_held_outcome(t, info):
    """Returns ('WIN', held_pnl) or ('LOSE', held_pnl) or ('UNKNOWN', 0).
    Held pnl = (shares × 1.0) − size if win, else −size if lose.
    """
    direction = t.get("direction", "")
    shares = t.get("shares", 0)
    size = t.get("size_usdc", 0)
    slug = t.get("slug", "").lower()
    question = t.get("question", "").lower()
    market_type = (t.get("sports_market_type") or "").lower()
    if not market_type:
        # Slug'tan tahmin et
        if "-total-" in slug or "-totals-" in slug:
            market_type = "totals"
        elif "-spread-" in slug:
            market_type = "spreads"
        elif "-handicap-" in slug:
            market_type = "spreads"
        else:
            market_type = "moneyline"
    home_w = info["home_winner"]
    home_score = info["home_score"]
    away_score = info["away_score"]

    # Try map slug to home/away via name matching
    home_first = (info["home_name"].lower().split()[0] if info["home_name"] else "")
    away_first = (info["away_name"].lower().split()[0] if info["away_name"] else "")
    slug_parts = extract_names_from_slug(slug)
    # First slug part = YES side typically
    yes_side = slug_parts[0] if slug_parts else ""

    if market_type == "moneyline":
        # YES side is "yes_side". Did yes_side win?
        if yes_side and yes_side in home_first.lower():
            yes_won = home_w
        elif yes_side and yes_side in away_first.lower():
            yes_won = not home_w
        else:
            # Cannot map. Try question.
            qw_match_home = home_first in question
            qw_match_away = away_first in question
            if qw_match_home and not qw_match_away:
                yes_won = home_w  # uncertain
            else:
                return ("UNKNOWN", 0)
        if direction == "BUY_YES":
            won = yes_won
        else:
            won = not yes_won
        return ("WIN" if won else "LOSE", (shares * 1.0 - size) if won else -size)

    if market_type == "totals":
        # YES = over, NO = under
        total = home_score + away_score
        # Get line from slug, e.g., "-total-167pt5" -> 167.5
        m = re.search(r"-total-(\d+)pt(\d+)", slug)
        if m:
            line = float(m.group(1)) + float(f"0.{m.group(2)}")
        else:
            m = re.search(r"-total-(\d+)", slug)
            if not m:
                return ("UNKNOWN", 0)
            line = float(m.group(1))
        over_won = total > line
        if direction == "BUY_YES":
            won = over_won
        else:
            won = not over_won
        return ("WIN" if won else "LOSE", (shares * 1.0 - size) if won else -size)

    return ("UNKNOWN", 0)


# Display
print(f"{'Slug':50} {'Actual':>9} {'Held':>9} {'Diff':>9}  Detail")
print("-" * 130)
total_actual = 0.0
total_held = 0.0
known_cnt = 0
saved_cnt = 0  # graduated_sl SAVED us
hurt_cnt = 0  # graduated_sl HURT us
unknown_cnt = 0

for t, info in verified:
    slug = t.get("slug", "?")[:50]
    actual = t["exit_pnl_usdc"]
    outcome, held_pnl = position_held_outcome(t, info)
    detail = f"{info['away_name']}({info['away_score']})@{info['home_name']}({info['home_score']}) {outcome}"
    if outcome == "UNKNOWN":
        unknown_cnt += 1
        print(f"{slug:50} ${actual:+8.2f}        ?         ?  {detail}")
        continue
    diff = held_pnl - actual
    if held_pnl > actual:
        # held would have been better → graduated_sl HURT
        hurt_cnt += 1
        marker = "HURT"
    else:
        saved_cnt += 1
        marker = "SAVED"
    total_actual += actual
    total_held += held_pnl
    known_cnt += 1
    print(f"{slug:50} ${actual:+8.2f} ${held_pnl:+8.2f} ${diff:+8.2f}  {detail} {marker}")

print()
print(f"=== SONUC ({known_cnt} dogrulanmis trade icin) ===")
print(f"  graduated_sl KURTARDIGI: {saved_cnt} trade")
print(f"  graduated_sl ZARAR ETTIRDIGI: {hurt_cnt} trade")
print(f"  Cikarilamayan: {unknown_cnt}")
print(f"  Toplam actual (graduated_sl ile): ${total_actual:+.2f}")
print(f"  Toplam held (tutsaydık): ${total_held:+.2f}")
print(f"  NET FARK: ${total_held - total_actual:+.2f}  (pozitif = graduated_sl ZARAR ETTI)")

print()
print(f"=== ESLESEMEYENLER ({len(unmatched)}) ===")
for t, why in unmatched[:15]:
    print(f"  {t.get('slug','?')[:60]:60} -> {why}")
