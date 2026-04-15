"""Odds API tam kapasite auditi — bizim kullandıklarımız vs kullanabileceklerimiz.

Çalıştır: python scripts/audit_odds_api.py
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

from src.config.settings import load_config  # noqa: E402
from src.domain.matching.odds_sport_keys import _TAG_TO_ODDS  # noqa: E402
from src.infrastructure.apis.odds_client import OddsAPIClient  # noqa: E402


def main() -> None:
    api_key = os.environ.get("ODDS_API_KEY", "")
    if not api_key:
        print("ERROR: ODDS_API_KEY env var not set")
        sys.exit(1)
    client = OddsAPIClient(api_key=api_key)
    cfg = load_config()

    print("=== ODDS API - TÜM AKTİF SPORTS ===\n")
    sports = client.get_sports(include_inactive=False) or []
    by_group: dict[str, list[dict]] = defaultdict(list)
    for s in sports:
        if not isinstance(s, dict):
            continue
        by_group[s.get("group", "?")].append(s)

    for group in sorted(by_group):
        print(f"  {group}:")
        for s in sorted(by_group[group], key=lambda x: x.get("key", "")):
            print(f"    {s.get('key',''):40s}  {s.get('title','')}")
        print()

    # Bizim static mapping'imiz
    print("=== BİZİM STATIC MAP (sport_tag → odds key) ===\n")
    for tag, key in sorted(_TAG_TO_ODDS.items()):
        status = "✓" if any(s.get("key") == key for s in sports) else "✗ inactive/unknown"
        print(f"  {tag:30s} → {key:35s}  {status}")
    print()

    # Config whitelist
    print("=== CONFIG WHITELIST (config.scanner.allowed_sport_tags) ===\n")
    for tag in cfg.scanner.allowed_sport_tags:
        in_map = tag in _TAG_TO_ODDS or any(tag.startswith(prefix) for prefix in ("atp", "wta", "tennis"))
        print(f"  {tag:20s}  {'mapped' if in_map else 'NO MAP — dinamik veya bilinmiyor'}")
    print()

    # Fark analizi
    print("=== GAP ANALİZİ ===\n")
    mapped_keys = set(_TAG_TO_ODDS.values())
    active_keys = {s.get("key") for s in sports if isinstance(s, dict)}
    not_using = active_keys - mapped_keys
    # Filter tennis/futures keys
    interesting_gaps = [k for k in sorted(not_using)
                        if not k.startswith("tennis_")
                        and not k.endswith("_winner")
                        and not k.endswith("_champion")]
    if interesting_gaps:
        print("  Odds API'nin sunduğu ama static map'imizde OLMAYAN sport key'ler:")
        for k in interesting_gaps:
            title = next((s.get("title", "") for s in sports if isinstance(s, dict) and s.get("key") == k), "")
            print(f"    {k:45s}  {title}")
    else:
        print("  Tüm non-tennis active key'ler static map'te.")

    # Dinamik tennis key'leri (bizim _match_tennis_key'in gördüğü havuz)
    tennis_keys = [k for k in sorted(active_keys) if k.startswith("tennis_")]
    print(f"\n=== AKTIF TENNIS KEY'LERI ({len(tennis_keys)} adet) ===")
    for k in tennis_keys:
        title = next((s.get("title", "") for s in sports if isinstance(s, dict) and s.get("key") == k), "")
        print(f"  {k:40s}  {title}")


if __name__ == "__main__":
    main()
