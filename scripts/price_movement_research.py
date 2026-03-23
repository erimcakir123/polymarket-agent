"""Research: How much do sports market prices move before match time?"""
import requests
import json
from datetime import datetime, timezone

# 1. Fetch resolved sports markets
print("=== Fetching resolved sports markets ===")
resp = requests.get("https://gamma-api.polymarket.com/markets", params={
    "closed": "true",
    "tag": "Sports",
    "limit": 15,
    "order": "volume24hr",
    "ascending": "false",
}, timeout=15)
markets = resp.json()

for m in markets[:5]:
    slug = m.get("slug", "")
    vol = float(m.get("volume24hr", 0) or 0)
    end = m.get("endDate", "")
    prices = m.get("outcomePrices", "")
    cid = m.get("conditionId", "")
    tokens = json.loads(m.get("clobTokenIds", '["",""]'))
    print(f"\n{slug[:60]}")
    print(f"  vol=${vol:,.0f} | end={end[:16]} | prices={prices}")
    print(f"  conditionId={cid[:30]}...")
    print(f"  token_yes={tokens[0][:30]}...")

# 2. Try CLOB price history endpoint
print("\n\n=== Testing price history endpoints ===")
test_token = json.loads(markets[0].get("clobTokenIds", '["",""]'))[0]
test_cid = markets[0].get("conditionId", "")

# Try different endpoints
endpoints = [
    f"https://clob.polymarket.com/prices-history?market={test_cid}&interval=all&fidelity=60",
    f"https://clob.polymarket.com/prices-history?market={test_cid}",
    f"https://strapi-matic.poly.market/markets/{test_cid}",
    f"https://gamma-api.polymarket.com/markets/{test_cid}/prices",
]

for url in endpoints:
    try:
        r = requests.get(url, timeout=10)
        print(f"\n{url[:80]}...")
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"  Got {len(data)} data points")
                print(f"  First: {json.dumps(data[0])[:150]}")
                print(f"  Last:  {json.dumps(data[-1])[:150]}")
            elif isinstance(data, dict):
                print(f"  Keys: {list(data.keys())[:10]}")
                # Check for history in nested fields
                for k, v in data.items():
                    if isinstance(v, list) and len(v) > 2:
                        print(f"  {k}: {len(v)} items")
                        break
        else:
            print(f"  Body: {r.text[:100]}")
    except Exception as e:
        print(f"  Error: {e}")

# 3. Try CLOB timeseries
print("\n\n=== CLOB Timeseries ===")
ts_urls = [
    f"https://clob.polymarket.com/prices-history?market={test_cid}&interval=1w&fidelity=60",
    f"https://clob.polymarket.com/prices-history?market={test_cid}&interval=1d&fidelity=5",
]
for url in ts_urls:
    try:
        r = requests.get(url, timeout=10)
        print(f"\n{url[:80]}...")
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "history" in data:
                hist = data["history"]
                print(f"  History points: {len(hist)}")
                if hist:
                    print(f"  First: {hist[0]}")
                    print(f"  Last:  {hist[-1]}")
            elif isinstance(data, list):
                print(f"  Points: {len(data)}")
                if data:
                    print(f"  Sample: {data[0]}")
            else:
                print(f"  Keys: {list(data.keys())[:10]}")
                print(f"  Sample: {json.dumps(data)[:200]}")
    except Exception as e:
        print(f"  Error: {e}")
