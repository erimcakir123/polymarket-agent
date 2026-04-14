"""volatility_swing.py için birim testler."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.domain.analysis.probability import BookmakerProbability
from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.strategy.entry import volatility_swing as vs


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _market(yes: float = 0.30, hours_ahead: float = 6.0) -> MarketData:
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


def test_vs_buy_yes_when_yes_underdog_priced() -> None:
    # YES 0.30 — underdog aralığında (0.10-0.50)
    sig = vs.evaluate(_market(yes=0.30, hours_ahead=6))
    assert sig is not None
    assert sig.direction == Direction.BUY_YES
    assert sig.entry_reason == EntryReason.VOLATILITY_SWING


def test_vs_buy_no_when_no_underdog_priced() -> None:
    # YES 0.75 → NO 0.25 (underdog) → BUY_NO
    sig = vs.evaluate(_market(yes=0.75, hours_ahead=6))
    assert sig is not None
    assert sig.direction == Direction.BUY_NO


def test_vs_takes_no_when_yes_above_50() -> None:
    # YES 0.55 → NO 0.45 — NO underdog aralığında, BUY_NO alır.
    # Her zaman bir taraf <0.50 olduğundan VS genelde her market'te tetiklenebilir;
    # dışlanma sadece her iki tarafın da [0.10, 0.50] dışında olduğu durumda.
    sig = vs.evaluate(_market(yes=0.55, hours_ahead=6))
    assert sig is not None
    assert sig.direction == Direction.BUY_NO


def test_vs_skip_when_too_cheap() -> None:
    # YES 0.05 → NO 0.95; ikisi de aralık dışı
    assert vs.evaluate(_market(yes=0.05, hours_ahead=6)) is None


def test_vs_skip_post_match() -> None:
    # match_start geçmişte
    assert vs.evaluate(_market(yes=0.30, hours_ahead=-1)) is None


def test_vs_skip_too_far_from_start() -> None:
    # 30h > 24h max
    assert vs.evaluate(_market(yes=0.30, hours_ahead=30)) is None


def test_vs_no_match_start_returns_none() -> None:
    m = _market(yes=0.30)
    m = m.model_copy(update={"match_start_iso": ""})
    assert vs.evaluate(m) is None


def test_vs_uses_bookmaker_metadata_when_provided() -> None:
    bm = BookmakerProbability(probability=0.30, confidence="A",
                              bookmaker_prob=0.30, num_bookmakers=10.0, has_sharp=True)
    sig = vs.evaluate(_market(yes=0.30, hours_ahead=6), bm_prob_for_logging=bm)
    assert sig is not None
    assert sig.confidence == "A"
    assert sig.bookmaker_prob == 0.30


def test_vs_no_bookmaker_default_confidence_b() -> None:
    sig = vs.evaluate(_market(yes=0.30, hours_ahead=6))
    assert sig is not None
    assert sig.confidence == "B"
