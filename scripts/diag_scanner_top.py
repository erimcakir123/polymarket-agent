"""SPEC-K post-mortem: Scanner top-N içinde basketbol spread/totals var mı?"""
from collections import Counter
from pathlib import Path

from src.config.settings import load_config
from src.config.sport_rules import BASKETBALL_TAGS
from src.infrastructure.apis.gamma_client import GammaClient
from src.orchestration.scanner import MarketScanner as Scanner

cfg = load_config(Path("config.yaml"))
print("Running scanner (fetch + filter + sort + top N)...")
scanner = Scanner(cfg.scanner)
top = scanner.scan()
print(f"Scanner top: {len(top)}")
print()

# Categorize top
cats: Counter = Counter()
for m in top:
    smt = m.sports_market_type or "?"
    sport = (m.sport_tag or "?").lower()
    is_basket = sport in BASKETBALL_TAGS
    if is_basket and smt in ("spreads", "totals"):
        cats[f"basketball-{smt}"] += 1
    elif smt == "moneyline":
        cats["moneyline"] += 1
    else:
        cats[f"other-{smt}"] += 1

print(f"Top market_type breakdown: {dict(cats)}")
print()
print("Basketball spread/totals in top:")
for m in top:
    smt = m.sports_market_type or ""
    sport = (m.sport_tag or "").lower()
    if sport in BASKETBALL_TAGS and smt in ("spreads", "totals"):
        print(
            f"  {m.slug[:55]:55s} | {smt:8s} | sport={sport} | "
            f"liq=${m.liquidity:>8.0f} | yes={m.yes_price:.3f}",
        )

print()
print("First 5 moneyline in top:")
n = 0
for m in top:
    if m.sports_market_type == "moneyline":
        print(
            f"  {m.slug[:55]:55s} | sport={(m.sport_tag or '?').lower()} | "
            f"liq=${m.liquidity:>8.0f}",
        )
        n += 1
        if n >= 5:
            break
