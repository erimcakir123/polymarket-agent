"""Scanner tennis tier filter — Challenger/ITF eler, Masters/GS geçer.

Bug: tennis Challenger/ITF marketleri scanner'ı geçip gate'e ulaşıyor;
Odds API onları desteklemediği için her market ~3 quota harcıyor (838
EVENT_NO_MATCH skips/gün). Fix: scanner'a opsiyonel tennis tier filter
ekle — TournamentInfo None dönerse market drop. Backward compat: boş
tournaments dict default = filter disabled (mevcut davranış).
"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import ScannerConfig
from src.models.market import MarketData
from src.orchestration.scanner import MarketScanner


def test_scanner_drops_tennis_challenger_when_tier_filter_enabled() -> None:
    """Challenger tournaments (not in tournaments map) → scanner drops."""
    challenger = MarketData(
        condition_id="ch1",
        slug="atp-onclin-giunta-2026-04-29",
        question="Abidjan 2: Gauthier Onclin vs Massimo Giunta",
        sport_tag="tennis",
        sports_market_type="moneyline",
        yes_price=0.55,
        no_price=0.45,
        liquidity=5000.0,
        volume_24h=1000.0,
        match_start_iso="2026-04-29T22:00:00Z",
        end_date_iso="2026-04-30T01:00:00Z",
        closed=False, resolved=False, accepting_orders=True,
        yes_token_id="t1", no_token_id="t2", event_id="e1", tags=[],
    )
    masters = challenger.model_copy(update={
        "slug": "atp-fils-lehecka-2026-04-29",
        "question": "Madrid Open: Arthur Fils vs Jiri Lehecka",
        "condition_id": "m1",
    })
    gamma = MagicMock()
    gamma.fetch_events.return_value = [challenger, masters]

    cfg = ScannerConfig(
        min_liquidity=1000, max_markets_per_cycle=300, max_duration_days=14,
        max_hours_to_start=24.0, resolved_price_threshold=0.98,
        allowed_categories=["sports"], allowed_sport_tags=["tennis", "atp*", "wta*"],
    )
    tournaments = {"masters_1000": {"madrid_open": "clay"}}
    excluded = ["challenger", "itf", "futures"]

    scanner = MarketScanner(
        config=cfg, gamma_client=gamma,
        tennis_tournaments=tournaments, tennis_excluded_tiers=excluded,
    )
    result = scanner.scan()
    slugs = {m.slug for m in result}
    assert "atp-fils-lehecka-2026-04-29" in slugs, "Madrid Open (Masters 1000) MUST pass"
    assert "atp-onclin-giunta-2026-04-29" not in slugs, "Abidjan Challenger MUST be dropped"


def test_scanner_passes_tennis_when_tier_filter_disabled() -> None:
    """Backward compat: empty tennis_tournaments dict = no filter (old behavior)."""
    challenger = MarketData(
        condition_id="ch1", slug="atp-onclin-giunta-2026-04-29",
        question="Abidjan 2: Gauthier Onclin vs Massimo Giunta",
        sport_tag="tennis", sports_market_type="moneyline",
        yes_price=0.55, no_price=0.45, liquidity=5000.0, volume_24h=1000.0,
        match_start_iso="2026-04-29T22:00:00Z", end_date_iso="2026-04-30T01:00:00Z",
        closed=False, resolved=False, accepting_orders=True,
        yes_token_id="t1", no_token_id="t2", event_id="e1", tags=[],
    )
    gamma = MagicMock()
    gamma.fetch_events.return_value = [challenger]

    cfg = ScannerConfig(
        min_liquidity=1000, max_markets_per_cycle=300, max_duration_days=14,
        max_hours_to_start=24.0, resolved_price_threshold=0.98,
        allowed_categories=["sports"], allowed_sport_tags=["tennis", "atp*", "wta*"],
    )

    # No tennis config passed -> filter disabled -> challenger passes (old behavior)
    scanner = MarketScanner(config=cfg, gamma_client=gamma)
    result = scanner.scan()
    assert any(m.slug == "atp-onclin-giunta-2026-04-29" for m in result)
