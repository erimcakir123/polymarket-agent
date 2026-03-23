"""Research: Price movement across sport categories (basketball, esports, football, MMA, etc.)."""
import requests
import json
import time
from datetime import datetime, timezone
from collections import defaultdict

def classify_sport(slug: str) -> str:
    """Classify market slug into sport category."""
    slug_lower = slug.lower()
    if any(k in slug_lower for k in ["nba", "basketball", "ncaa", "march-madness", "celtics", "lakers", "bucks", "cavaliers"]):
        return "Basketball"
    if any(k in slug_lower for k in ["epl", "premier-league", "la-liga", "serie-a", "bundesliga", "ucl", "champions-league", "soccer", "football", "fc-", "manchester", "liverpool", "arsenal", "real-madrid", "barcelona"]):
        return "Football/Soccer"
    if any(k in slug_lower for k in ["lol", "csgo", "cs2", "dota", "valorant", "esport", "g2", "fnatic", "t1-", "gen-g", "cloud9", "lec", "lck", "lpl"]):
        return "Esports"
    if any(k in slug_lower for k in ["ufc", "mma", "bellator", "fight", "bout"]):
        return "MMA/UFC"
    if any(k in slug_lower for k in ["nhl", "hockey", "ice-"]):
        return "Hockey"
    if any(k in slug_lower for k in ["mlb", "baseball"]):
        return "Baseball"
    if any(k in slug_lower for k in ["nfl", "touchdown", "super-bowl"]):
        return "NFL"
    if any(k in slug_lower for k in ["tennis", "atp", "wta", "grand-slam"]):
        return "Tennis"
    return "Other Sports"

def analyze_market(m):
    """Analyze price movement for a single market. Returns dict or None."""
    slug = m.get("slug", "")
    tokens = json.loads(m.get("clobTokenIds", '["",""]'))
    end_date = m.get("endDate", "")
    token_yes = tokens[0] if tokens else ""

    if not token_yes or not end_date:
        return None

    try:
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None

    try:
        r = requests.get("https://clob.polymarket.com/prices-history", params={
            "market": token_yes,
            "interval": "all",
            "fidelity": "60",
        }, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        hist = data.get("history", [])
        if not hist or len(hist) < 5:
            return None
    except Exception:
        return None

    # Parse timestamps and prices
    points = []
    for h in hist:
        ts = h.get("t", 0)
        price = float(h.get("p", 0))
        if ts and price:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            hours_before = (end_dt - dt).total_seconds() / 3600
            if hours_before > 0:  # Only pre-end data
                points.append((hours_before, price))

    if len(points) < 3:
        return None

    points.sort(key=lambda x: x[0], reverse=True)  # earliest first

    # Find prices at key time horizons
    horizons = {72: None, 48: None, 24: None, 12: None, 6: None, 3: None, 1: None}
    for hours_before, price in points:
        for h in horizons:
            if horizons[h] is None and hours_before <= h + 2:
                horizons[h] = price

    # Calculate movements between horizons
    sorted_h = sorted([h for h in horizons if horizons[h] is not None], reverse=True)
    movements = {}
    for i in range(len(sorted_h) - 1):
        h_from = sorted_h[i]
        h_to = sorted_h[i + 1]
        movements[f"{h_from}h->{h_to}h"] = abs(horizons[h_from] - horizons[h_to])

    # Ranges
    prices = [p for _, p in points]
    all_range = max(prices) - min(prices)

    last_6h = [p for hb, p in points if 0 < hb <= 6]
    before_6h = [p for hb, p in points if hb > 6]
    last_3h = [p for hb, p in points if 0 < hb <= 3]

    result = {
        "slug": slug,
        "sport": classify_sport(slug),
        "data_points": len(points),
        "horizons": horizons,
        "movements": movements,
        "total_range": all_range,
        "last_6h_range": (max(last_6h) - min(last_6h)) if len(last_6h) >= 2 else 0,
        "last_3h_range": (max(last_3h) - min(last_3h)) if len(last_3h) >= 2 else 0,
        "before_6h_range": (max(before_6h) - min(before_6h)) if len(before_6h) >= 2 else 0,
    }
    return result


# === Main ===
print("=" * 70)
print("PRICE MOVEMENT RESEARCH — Multi-Sport Analysis")
print("=" * 70)

# Fetch resolved sports markets — larger batch
all_markets = []
for offset in [0, 50]:
    resp = requests.get("https://gamma-api.polymarket.com/markets", params={
        "closed": "true",
        "tag": "Sports",
        "limit": 50,
        "offset": offset,
        "order": "volume24hr",
        "ascending": "false",
    }, timeout=15)
    if resp.status_code == 200:
        all_markets.extend(resp.json())
    time.sleep(0.3)

print(f"\nFetched {len(all_markets)} resolved sports markets")

# Classify and show distribution
sport_counts = defaultdict(int)
for m in all_markets:
    sport_counts[classify_sport(m.get("slug", ""))] += 1
print("\nCategory distribution:")
for sport, count in sorted(sport_counts.items(), key=lambda x: -x[1]):
    print(f"  {sport}: {count}")

# Analyze up to 30 markets across categories
results = []
analyzed = 0
for m in all_markets:
    if analyzed >= 30:
        break
    result = analyze_market(m)
    if result:
        results.append(result)
        analyzed += 1
        print(f"  [{analyzed}/30] {result['sport']:15s} | {result['slug'][:45]}")
    time.sleep(0.4)  # Rate limit

print(f"\n\nSuccessfully analyzed {len(results)} markets")

# === Aggregate by sport category ===
by_sport = defaultdict(list)
for r in results:
    by_sport[r["sport"]].append(r)

print("\n" + "=" * 70)
print("RESULTS BY SPORT CATEGORY")
print("=" * 70)

for sport in sorted(by_sport.keys()):
    markets = by_sport[sport]
    print(f"\n{'='*50}")
    print(f"  {sport} ({len(markets)} markets)")
    print(f"{'='*50}")

    # Per-market details
    for r in markets:
        print(f"\n  {r['slug'][:55]}")
        print(f"    Data points: {r['data_points']}")
        h = r["horizons"]
        prev = None
        for t in [72, 48, 24, 12, 6, 3, 1]:
            if h.get(t) is not None:
                delta = ""
                if prev is not None:
                    diff = abs(h[t] - prev) * 100
                    delta = f" (delta {diff:.1f}%)"
                print(f"    {t:3d}h before: {h[t]*100:.1f}%{delta}")
                prev = h[t]
        print(f"    Total range: {r['total_range']*100:.1f}%")
        print(f"    Before 6h range: {r['before_6h_range']*100:.1f}% | Last 6h range: {r['last_6h_range']*100:.1f}% | Last 3h range: {r['last_3h_range']*100:.1f}%")

    # Averages for this sport
    avg_total = sum(r["total_range"] for r in markets) / len(markets) * 100
    avg_before_6h = sum(r["before_6h_range"] for r in markets) / len(markets) * 100
    avg_last_6h = sum(r["last_6h_range"] for r in markets) / len(markets) * 100
    avg_last_3h = sum(r["last_3h_range"] for r in markets) / len(markets) * 100

    print(f"\n  --- {sport} AVERAGES ---")
    print(f"  Avg total range:     {avg_total:.1f}%")
    print(f"  Avg before-6h range: {avg_before_6h:.1f}%")
    print(f"  Avg last-6h range:   {avg_last_6h:.1f}%")
    print(f"  Avg last-3h range:   {avg_last_3h:.1f}%")
    print(f"  Late volatility ratio (last6h / total): {(avg_last_6h / avg_total * 100) if avg_total > 0 else 0:.0f}%")

# === Cross-sport summary ===
print("\n" + "=" * 70)
print("CROSS-SPORT SUMMARY")
print("=" * 70)
print(f"{'Sport':<20} {'N':>3} {'Avg Range':>10} {'Before 6h':>10} {'Last 6h':>10} {'Last 3h':>10} {'Late%':>6}")
print("-" * 70)
for sport in sorted(by_sport.keys()):
    markets = by_sport[sport]
    n = len(markets)
    avg_total = sum(r["total_range"] for r in markets) / n * 100
    avg_b6 = sum(r["before_6h_range"] for r in markets) / n * 100
    avg_l6 = sum(r["last_6h_range"] for r in markets) / n * 100
    avg_l3 = sum(r["last_3h_range"] for r in markets) / n * 100
    late_pct = (avg_l6 / avg_total * 100) if avg_total > 0 else 0
    print(f"{sport:<20} {n:>3} {avg_total:>9.1f}% {avg_b6:>9.1f}% {avg_l6:>9.1f}% {avg_l3:>9.1f}% {late_pct:>5.0f}%")

print("\n\nKey: Late% = what fraction of total price movement happens in the last 6 hours")
print("Higher Late% = more late volatility = better for near-match strategy")
print("Lower Late% = price moves earlier = far-slot strategy could work")
