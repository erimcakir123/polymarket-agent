"""SPEC-K post-mortem: enrich_market bir basketbol spread/totals için ne döndürüyor?"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
from src.config.settings import load_config
from src.config.sport_rules import BASKETBALL_TAGS
from src.infrastructure.apis.gamma_client import GammaClient
from src.infrastructure.apis.odds_client import OddsAPIClient as OddsClient
from src.orchestration.scanner import MarketScanner
from src.strategy.enrichment.odds_enricher import enrich_market

cfg = load_config(Path("config.yaml"))
api_key = os.getenv("ODDS_API_KEY", "")
if not api_key:
    print("ERROR: ODDS_API_KEY env var not set")
    raise SystemExit(1)

scanner = MarketScanner(cfg.scanner)
top = scanner.scan()
basketball = [
    m for m in top
    if (m.sport_tag or "").lower() in BASKETBALL_TAGS
    and m.sports_market_type in ("spreads", "totals")
]
print(f"Top içinde basketbol spread/totals: {len(basketball)}")
print()

odds_client = OddsClient(api_key=api_key)
tolerance = cfg.odds_api.spread_totals_line_tolerance
print(f"line_tolerance from config: {tolerance}")
print()

for i, m in enumerate(basketball[:3], 1):
    print(f"--- Market {i}: {m.slug[:60]} ---")
    print(f"  sport_tag={m.sport_tag} | sports_market_type={m.sports_market_type}")
    print(f"  question: {m.question[:100]}")
    try:
        result = enrich_market(m, odds_client, line_tolerance=tolerance)
        print(f"  ->fail_reason={result.fail_reason}")
        print(f"  ->probability={result.probability}")
        print(f"  ->spread_line={result.spread_line}")
        print(f"  ->total_line={result.total_line}")
        print(f"  ->total_side={result.total_side}")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")
    print()
