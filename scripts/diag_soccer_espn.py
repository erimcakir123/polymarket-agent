"""ESPN soccer endpoint inceleme — minute, status fields (SPEC-015 Task 1)."""
import json
import requests

LEAGUES = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "uefa.champions"]

for lg in LEAGUES:
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            print(f"[{lg}] HTTP {r.status_code}")
            continue
        data = r.json()
        events = data.get("events", [])
        print(f"\n[{lg}] {len(events)} events")
        for e in events[:3]:
            for comp in e.get("competitions", [{}])[:1]:
                status = comp.get("status", {})
                print(f"  {e.get('name', '')[:60]}")
                print(f"    period: {status.get('period')}")
                print(f"    displayClock: {status.get('displayClock')}")
                print(f"    type.description: {status.get('type', {}).get('description')}")
                print(f"    type.detail: {status.get('type', {}).get('detail')}")
                print(f"    type.state: {status.get('type', {}).get('state')}")
                print(f"    type.completed: {status.get('type', {}).get('completed')}")
    except Exception as e:
        print(f"[{lg}] error: {e}")
