"""Tennis sandbox scanner extension tests (Task 12).

Spec §11.3: allowed_sports_market_types opt-in allow-list + doubles slug skip.
Fallback: if allowed_sports_market_types not set → legacy moneyline/spreads/totals.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.config.settings import ScannerConfig
from src.models.market import MarketData
from src.orchestration.scanner import MarketScanner


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _tennis_market(
    slug: str = "tennis-djokovic-alcaraz-2026-ro16",
    sport_tag: str = "tennis_atp",
    sports_market_type: str = "tennis_first_set_winner",
    match_start_offset_h: float = 2.0,
    end_offset_h: float = 5.0,
) -> MarketData:
    now = datetime.now(timezone.utc)
    return MarketData(
        condition_id="test-cid",
        question="Will Djokovic win the first set?",
        slug=slug,
        yes_token_id="y1",
        no_token_id="n1",
        yes_price=0.55,
        no_price=0.45,
        liquidity=5000.0,
        volume_24h=1000.0,
        tags=[],
        end_date_iso=_iso(now + timedelta(hours=end_offset_h)),
        match_start_iso=_iso(now + timedelta(hours=match_start_offset_h)),
        sport_tag=sport_tag,
        sports_market_type=sports_market_type,
        closed=False,
        resolved=False,
        accepting_orders=True,
    )


def _mock_gamma(markets: list[MarketData]) -> MagicMock:
    g = MagicMock()
    g.fetch_events.return_value = markets
    return g


def _tennis_scanner_config(allowed_types: list[str] | None = None) -> ScannerConfig:
    """ScannerConfig with tennis sandbox settings.

    allowed_sports_market_types is optional — absent (None) → legacy fallback.
    """
    return ScannerConfig(
        min_liquidity=1000,
        max_markets_per_cycle=300,
        max_duration_days=14,
        allowed_sport_tags=["tennis_atp", "tennis_wta"],
        allowed_sports_market_types=allowed_types,
    )


# ── Test 1: Accepts tennis_first_set_winner when in allow-list ────────────────

def test_scanner_tennis_accepts_allowed_market_type() -> None:
    """tennis_first_set_winner in allowed_sports_market_types → kabul edilir."""
    m = _tennis_market(sports_market_type="tennis_first_set_winner")
    cfg = _tennis_scanner_config(allowed_types=["tennis_first_set_winner", "tennis_match_winner"])
    sc = MarketScanner(cfg, gamma_client=_mock_gamma([m]))
    result = sc.scan()
    assert len(result) == 1, (
        f"tennis_first_set_winner izin listesindeyken kabul edilmeli, "
        f"ama {len(result)} market döndü"
    )


# ── Test 2: Rejects unlisted tennis market type ───────────────────────────────

def test_scanner_tennis_rejects_unlisted_market_type() -> None:
    """tennis_tie_break izin listesinde değil → reddedilir."""
    m = _tennis_market(sports_market_type="tennis_tie_break")
    cfg = _tennis_scanner_config(allowed_types=["tennis_first_set_winner", "tennis_match_winner"])
    sc = MarketScanner(cfg, gamma_client=_mock_gamma([m]))
    result = sc.scan()
    assert len(result) == 0, (
        f"tennis_tie_break izin listesinde değilken reddedilmeli, "
        f"ama {len(result)} market döndü"
    )


# ── Test 3: Skips doubles slugs ───────────────────────────────────────────────

def test_scanner_tennis_skips_doubles_slug() -> None:
    """Slug 'doubles' içeriyorsa → reddedilir (çiftler analiz kapsamı dışı)."""
    m = _tennis_market(
        slug="tennis-doubles-djokovic-partner-vs-opponents-2026",
        sports_market_type="tennis_match_winner",
    )
    cfg = _tennis_scanner_config(allowed_types=["tennis_match_winner"])
    sc = MarketScanner(cfg, gamma_client=_mock_gamma([m]))
    result = sc.scan()
    assert len(result) == 0, (
        f"'doubles' içeren slug reddedilmeli, ama {len(result)} market döndü"
    )
