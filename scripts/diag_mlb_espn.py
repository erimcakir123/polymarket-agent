"""MLB ESPN API response inceleme — inning hangi field'da?"""
import json
import requests

r = requests.get(
    "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    timeout=15,
)
data = r.json()
events = data.get("events", [])
print(f"Total events: {len(events)}")
for event in events[:3]:
    # Hem dogrudan competitions hem groupings altindaki competitions kontrol
    competitions = event.get("competitions", [])
    if not competitions:
        for g in event.get("groupings", []):
            competitions.extend(g.get("competitions", []))
    for comp in competitions[:1]:
        status = comp.get("status", {})
        print(f"Event: {event.get('name', '')[:60]}")
        print(f"  status.period         : {status.get('period')!r}  (type: {type(status.get('period')).__name__})")
        print(f"  status.type.description: {status.get('type', {}).get('description', '')!r}")
        print(f"  status.type.detail     : {status.get('type', {}).get('detail', '')!r}")
        print(f"  status.type.state      : {status.get('type', {}).get('state', '')!r}")
        print()
