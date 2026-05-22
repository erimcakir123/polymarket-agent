"""Tennis enricher canli dogrulama — Polymarket tennis market'leri icin ESPN
match-start override gercekten calisiyor mu, manuel olarak gor.

Cagri: python scripts/verify_tennis_enricher.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Project root sys.path'e eklenir — script root disindan calistirilinca da import calissin.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.infrastructure.apis.espn_client import ESPNClient
from src.models.market import MarketData
from src.orchestration.tennis_start_enricher import TennisStartEnricher


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    stock_path = project_root / "data" / "stock_queue.json"
    with stock_path.open(encoding="utf-8") as f:
        rows = json.load(f)
    tennis_markets: list[MarketData] = []
    for r in rows:
        m = r.get("market") or {}
        if "tennis" not in (m.get("sport_tag") or "").lower():
            continue
        try:
            tennis_markets.append(MarketData(**m))
        except Exception as e:
            print(f"[skip] {m.get('slug', '?')}: {e}")

    if not tennis_markets:
        print("Stock queue'da tennis market yok — script bitti.")
        return

    print(f"{len(tennis_markets)} tennis market bulundu:\n")
    for m in tennis_markets:
        print(f"  POLY  {m.slug!r:60} start={m.match_start_iso}")

    print("\nESPN sorgu yapiliyor (3-asamali fetch + athlete cache)...\n")
    enricher = TennisStartEnricher(espn_client=ESPNClient(), cache_ttl_sec=300)
    out = enricher.enrich(tennis_markets)

    print("\nSonuc:\n")
    for orig, new in zip(tennis_markets, out):
        flag = "ESPN override" if orig.match_start_iso != new.match_start_iso else "Polymarket kaldi"
        print(f"  {new.slug!r:60}")
        print(f"    poly  = {orig.match_start_iso}")
        print(f"    final = {new.match_start_iso}   [{flag}]")


if __name__ == "__main__":
    main()
