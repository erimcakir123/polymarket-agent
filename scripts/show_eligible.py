import sys, io, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from src.market_scanner import MarketScanner
from src.config import load_config
from datetime import datetime, timezone
from collections import defaultdict

cfg = load_config()
scanner = MarketScanner(cfg.scanner)
markets = scanner.fetch()
now = datetime.now(timezone.utc)

sports = defaultdict(list)
for m in markets:
    sports[m.sport_tag].append(m)

for tag in sorted(sports.keys(), key=lambda t: -len(sports[t])):
    ms = sports[tag]
    print(f"\n=== {tag.upper()} ({len(ms)} markets) ===")
    seen = set()
    for m in sorted(ms, key=lambda x: x.match_start_iso or x.end_date_iso or ""):
        t = m.match_start_iso or m.end_date_iso
        hours = 0
        if t:
            try:
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                hours = max(0, (dt - now).total_seconds() / 3600)
            except Exception:
                pass
        q = m.question[:65]
        slug_base = m.slug.split("-total")[0].split("-spread")[0].split("-game")[0].split("-map-")[0]
        if slug_base in seen:
            continue
        seen.add(slug_base)
        vol = f"${m.volume_24h/1000:.0f}K" if m.volume_24h >= 1000 else f"${m.volume_24h:.0f}"
        liq = f"${m.liquidity/1000:.0f}K" if m.liquidity >= 1000 else f"${m.liquidity:.0f}"
        price = f"{m.yes_price*100:.0f}c"
        print(f"  {hours:5.1f}h | {price:>4s} | vol={vol:>6s} liq={liq:>6s} | {q}")
