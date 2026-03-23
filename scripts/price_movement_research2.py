"""Research: Price history via CLOB token-based endpoint."""
import requests
import json
import time
from datetime import datetime, timezone, timedelta

# Fetch resolved sports markets
resp = requests.get("https://gamma-api.polymarket.com/markets", params={
    "closed": "true", "tag": "Sports", "limit": 10,
    "order": "volume24hr", "ascending": "false",
}, timeout=15)
markets = resp.json()

for m in markets[:5]:
    slug = m.get("slug", "")
    tokens = json.loads(m.get("clobTokenIds", '["",""]'))
    end_date = m.get("endDate", "")
    token_yes = tokens[0]

    if not token_yes or not end_date:
        continue

    print(f"\n{'='*60}")
    print(f"Market: {slug}")
    print(f"End: {end_date}")

    # Parse end date for time calculations
    try:
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except:
        continue

    # Try token-based price history
    # CLOB prices-history with token_id
    try:
        url = f"https://clob.polymarket.com/prices-history"
        params = {
            "market": token_yes,
            "interval": "all",
            "fidelity": "60",  # 60 min intervals
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            hist = data.get("history", [])
            if hist:
                print(f"  Price history: {len(hist)} data points")

                # Analyze price movement at different time horizons
                for h in hist[:3]:
                    print(f"  Sample: {h}")

                # Parse timestamps and prices
                points = []
                for h in hist:
                    ts = h.get("t", 0)
                    price = float(h.get("p", 0))
                    if ts and price:
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        hours_before = (end_dt - dt).total_seconds() / 3600
                        points.append((hours_before, price, dt))

                if points:
                    points.sort(key=lambda x: x[0], reverse=True)  # earliest first

                    # Find prices at key time horizons
                    horizons = {72: None, 48: None, 24: None, 12: None, 6: None, 3: None, 1: None}
                    for hours_before, price, dt in points:
                        for h in horizons:
                            if horizons[h] is None and hours_before <= h + 2:
                                horizons[h] = price

                    print(f"\n  Price movement timeline (hours before match -> price):")
                    prev_price = None
                    for h in sorted(horizons.keys(), reverse=True):
                        if horizons[h] is not None:
                            change = ""
                            if prev_price is not None:
                                diff = abs(horizons[h] - prev_price) * 100
                                change = f" (delta {diff:.1f}%)"
                            print(f"    {h:3d}h before: {horizons[h]:.3f} ({horizons[h]*100:.1f}%){change}")
                            prev_price = horizons[h]

                    # Calculate total range
                    prices = [p for _, p, _ in points]
                    price_range = max(prices) - min(prices)
                    print(f"\n  Total range: {min(prices):.3f} - {max(prices):.3f} (swing: {price_range*100:.1f}%)")

                    # Last 6 hours vs rest
                    last_6h = [p for hb, p, _ in points if 0 < hb <= 6]
                    before_6h = [p for hb, p, _ in points if hb > 6]
                    if last_6h and before_6h:
                        early_range = max(before_6h) - min(before_6h)
                        late_range = max(last_6h) - min(last_6h)
                        print(f"  Before 6h: range {early_range*100:.1f}%")
                        print(f"  Last 6h:   range {late_range*100:.1f}%")
            else:
                print(f"  No history data")
        else:
            print(f"  Status {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"  Error: {e}")

    time.sleep(0.5)  # Rate limit
