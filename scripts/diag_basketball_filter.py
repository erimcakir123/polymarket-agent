"""SPEC-J post-mortem: Scanner basketbol spread/totals neden açmadı?"""
from collections import Counter
from pathlib import Path

from src.config.settings import load_config
from src.config.sport_rules import BASKETBALL_TAGS
from src.infrastructure.apis.gamma_client import GammaClient

cfg = load_config(Path("config.yaml"))
print(f"BASKETBALL_TAGS: {sorted(BASKETBALL_TAGS)}")
print(f"allowed_sport_tags: {cfg.scanner.allowed_sport_tags}")
print(f"min_liquidity: {cfg.scanner.min_liquidity}")
print()

client = GammaClient()
print("Fetching events from gamma...")
markets = client.fetch_events()
print(f"Total raw markets: {len(markets)}")
print()

# Filter by basketbol + spreads/totals
basketball_st = [
    m for m in markets
    if m.sports_market_type in ("spreads", "totals")
    and (m.sport_tag or "").lower() in BASKETBALL_TAGS
]
print(f"Basketbol spread/totals (raw): {len(basketball_st)}")

# Adım adım filter takibi
filter_drops: Counter = Counter()
passed: list = []
for m in basketball_st:
    if m.closed or m.resolved or not m.accepting_orders:
        filter_drops["closed_resolved_or_not_accepting"] += 1
        continue
    th = cfg.scanner.resolved_price_threshold
    if m.yes_price >= th or m.yes_price <= (1.0 - th):
        filter_drops["price_resolved"] += 1
        continue
    if m.liquidity < cfg.scanner.min_liquidity:
        filter_drops["min_liquidity"] += 1
        continue
    if not m.match_start_iso:
        filter_drops["no_match_start"] += 1
        continue
    passed.append(m)

print(f"\nFilter drops: {dict(filter_drops)}")
print(f"Passed basic filters: {len(passed)}")
print()
print("First 10 PASSED basketbol spread/totals:")
for m in passed[:10]:
    print(
        f"  {m.slug[:55]:55s} | smt={m.sports_market_type:8s} | "
        f"liq=${m.liquidity:>8.0f} | yes={m.yes_price:.3f} | start={m.match_start_iso[:16]}",
    )
