"""consensus.py için birim testler (TDD §6.4)."""
from __future__ import annotations

from src.domain.analysis.probability import BookmakerProbability
from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.strategy.entry import consensus


def _market(yes: float = 0.70) -> MarketData:
    return MarketData(
        condition_id="c", question="Q?", slug="nba-x-y-2026",
        yes_token_id="y", no_token_id="n",
        yes_price=yes, no_price=1 - yes,
        liquidity=50_000, volume_24h=10_000, tags=[],
        end_date_iso="2026-04-14T00:00:00Z",
        sport_tag="nba", event_id="evt_1",
    )


def _bm(prob: float = 0.70, conf: str = "B") -> BookmakerProbability:
    return BookmakerProbability(
        probability=prob, confidence=conf,
        bookmaker_prob=prob, num_bookmakers=10.0, has_sharp=(conf == "A"),
    )


def test_consensus_buy_yes_above_min_price() -> None:
    # book 0.70 YES + market 0.70 YES → consensus, BUY_YES
    sig = consensus.evaluate(_market(yes=0.70), _bm(prob=0.70))
    assert sig is not None
    assert sig.direction == Direction.BUY_YES
    assert sig.entry_reason == EntryReason.CONSENSUS
    assert abs(sig.edge - (0.99 - 0.70)) < 1e-9


def test_consensus_buy_no_when_both_favor_no() -> None:
    # book 0.30 (NO favori) + market 0.30 (NO favori) → consensus BUY_NO
    sig = consensus.evaluate(_market(yes=0.30), _bm(prob=0.30))
    assert sig is not None
    assert sig.direction == Direction.BUY_NO
    # entry_price = no_price = 0.70; edge = 0.99 - 0.70 = 0.29
    assert abs(sig.edge - 0.29) < 1e-9


def test_disagreement_returns_none() -> None:
    # book 0.70 (YES favori), market 0.40 (NO favori) → consensus yok
    assert consensus.evaluate(_market(yes=0.40), _bm(prob=0.70)) is None


def test_below_min_price_returns_none() -> None:
    # consensus var ama 60¢ < 65¢ min → atla
    assert consensus.evaluate(_market(yes=0.60), _bm(prob=0.60), min_price=0.65) is None


def test_c_confidence_returns_none() -> None:
    assert consensus.evaluate(_market(yes=0.70), _bm(conf="C")) is None


def test_at_50_50_boundary() -> None:
    # book 0.50 == 0.50 → favors_yes True. market 0.50 == 0.50 → True. Consensus var.
    # Ama 0.50 < 0.65 min_price → None
    assert consensus.evaluate(_market(yes=0.50), _bm(prob=0.50), min_price=0.65) is None


def test_signal_has_correct_metadata() -> None:
    sig = consensus.evaluate(_market(yes=0.75), _bm(prob=0.72, conf="A"))
    assert sig is not None
    assert sig.confidence == "A"
    assert sig.bookmaker_prob == 0.72
    assert sig.sport_tag == "nba"
    assert sig.event_id == "evt_1"
