"""Tek seferlik teşhis — tennis no_bookmaker_data skip'lerinin kök sebebi.

5 başarısız tennis market al, enricher adım adım çalıştır, hangi step fail
ediyor göster. Bu dosya commit edilmez (scripts/ altında, gitignore edilebilir).

Çalıştır: python -m scripts.diag_tennis_enrich
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Proje kökünü import path'e ekle
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

from src.infrastructure.apis.odds_client import OddsAPIClient  # noqa: E402
from src.models.market import MarketData
from src.strategy.enrichment.question_parser import extract_teams
from src.strategy.enrichment.sport_key_resolver import resolve_sport_key
from src.domain.matching.pair_matcher import find_best_event_match
from src.strategy.enrichment.odds_enricher import _odds_query_params


def load_tennis_samples(n: int = 5) -> list[MarketData]:
    """stock_queue.json'dan tennis+no_bookmaker_data+12-24h pencereli ilk N."""
    raw = json.load(open("data/stock_queue.json"))
    now = datetime.now(timezone.utc)
    samples: list[MarketData] = []
    for row in raw:
        if row.get("last_skip_reason") != "no_bookmaker_data":
            continue
        m = row.get("market", {})
        if m.get("sport_tag") != "tennis":
            continue
        iso = m.get("match_start_iso", "")
        try:
            h = (datetime.fromisoformat(iso.replace("Z", "+00:00")) - now).total_seconds() / 3600
        except Exception:
            continue
        if not (0 <= h <= 24):
            continue
        samples.append(MarketData(**{k: m[k] for k in m if k in MarketData.model_fields}))
        if len(samples) >= n:
            break
    return samples


def diag_one(market: MarketData, odds_client: OddsAPIClient) -> dict:
    """Enricher akışını manuel tekrarla, her adımın çıktısını logla."""
    out = {"slug": market.slug, "question": market.question, "steps": []}

    # 1. sport_key resolve
    sport_key = resolve_sport_key(market.question, market.slug, market.tags, odds_client)
    out["steps"].append({"step": "sport_key_resolve", "result": sport_key})
    if not sport_key:
        return out

    # 2. extract_teams
    team_a, team_b = extract_teams(market.question)
    out["steps"].append({"step": "extract_teams", "team_a": team_a, "team_b": team_b})
    if not team_a:
        return out

    # 3. fetch odds
    events = odds_client.get_odds(sport_key, _odds_query_params())
    out["steps"].append({"step": "fetch_odds", "event_count": len(events) if events else 0})
    if not events:
        return out

    # 4. event match
    if team_b:
        match_result = find_best_event_match(team_a, team_b, events)
        if match_result:
            best, score = match_result
            out["steps"].append({
                "step": "event_match", "matched": True, "score": score,
                "home": best.get("home_team"), "away": best.get("away_team"),
                "bookmakers": len(best.get("bookmakers", [])),
            })
        else:
            candidates = [(e.get("home_team"), e.get("away_team"))
                          for e in events[:5]]
            out["steps"].append({
                "step": "event_match", "matched": False,
                "first_5_candidates": candidates,
            })
    return out


def main() -> None:
    api_key = os.environ.get("ODDS_API_KEY", "")
    if not api_key:
        print("ERROR: ODDS_API_KEY env var not set")
        sys.exit(1)
    odds_client = OddsAPIClient(api_key=api_key)

    samples = load_tennis_samples(5)
    print(f"Loaded {len(samples)} tennis samples\n")

    for m in samples:
        result = diag_one(m, odds_client)
        print(f"=== {result['slug']} ===")
        print(f"Q: {result['question'][:90]}")
        for step in result["steps"]:
            print(f"  {step}")
        print()


if __name__ == "__main__":
    main()
