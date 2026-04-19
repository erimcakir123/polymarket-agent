"""early_entry.py için birim testler."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.domain.analysis.probability import BookmakerProbability
from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.strategy.entry import early_entry


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _market(yes: float = 0.50, hours_ahead: float = 12.0) -> MarketData:
    start = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    return MarketData(
        condition_id="c", question="Q?", slug="nba-x-y-2026",
        yes_token_id="y", no_token_id="n",
        yes_price=yes, no_price=1 - yes,
        liquidity=50_000, volume_24h=10_000, tags=[],
        end_date_iso=_iso(start + timedelta(hours=3)),
        match_start_iso=_iso(start),
        sport_tag="nba", event_id="evt_1",
    )


def _bm(prob: float = 0.65, conf: str = "B") -> BookmakerProbability:
    return BookmakerProbability(
        probability=prob, confidence=conf,
        bookmaker_prob=prob, num_bookmakers=10.0, has_sharp=(conf == "A"),
    )


def test_early_signal_generated() -> None:
    # 12h ahead, B conf, anchor 0.65, market 0.50 → raw=0.15 > 0.10 → BUY_YES
    sig = early_entry.evaluate(_market(yes=0.50, hours_ahead=12), _bm(prob=0.65, conf="B"))
    assert sig is not None
    assert sig.direction == Direction.BUY_YES
    assert sig.entry_reason == EntryReason.EARLY


def test_too_close_to_match_returns_none() -> None:
    # 3 saat kalmış → < 6h min → None
    assert early_entry.evaluate(_market(yes=0.50, hours_ahead=3), _bm(prob=0.65)) is None


def test_too_far_from_match_returns_none() -> None:
    # 25 saat → > 24h max → None (fırsatı erken yakalama penceresi dışında)
    assert early_entry.evaluate(_market(yes=0.50, hours_ahead=25), _bm(prob=0.65)) is None


def test_low_favorite_prob_returns_none() -> None:
    # BUY_YES: bm 0.50 < min_favorite_probability 0.55 → atla (SPEC-013)
    assert early_entry.evaluate(_market(yes=0.40, hours_ahead=12), _bm(prob=0.50)) is None


def test_high_market_price_returns_none() -> None:
    # market 0.75 > 0.70 max_entry_price → atla
    assert early_entry.evaluate(_market(yes=0.75, hours_ahead=12), _bm(prob=0.85)) is None


def test_low_edge_returns_none() -> None:
    # raw 0.05 < min_edge 0.10 → atla
    assert early_entry.evaluate(_market(yes=0.60, hours_ahead=12), _bm(prob=0.65)) is None


def test_c_confidence_returns_none() -> None:
    assert early_entry.evaluate(_market(yes=0.50, hours_ahead=12), _bm(conf="C")) is None


def test_no_match_start_returns_none() -> None:
    m = _market(yes=0.50)
    m = m.model_copy(update={"match_start_iso": ""})
    assert early_entry.evaluate(m, _bm(prob=0.65)) is None


def test_a_conf_higher_threshold_still_works() -> None:
    # A conf threshold = 0.10 × 1.25 = 0.125; raw 0.15 > 0.125 → OK
    sig = early_entry.evaluate(_market(yes=0.50, hours_ahead=12), _bm(prob=0.65, conf="A"))
    assert sig is not None
    assert sig.confidence == "A"
