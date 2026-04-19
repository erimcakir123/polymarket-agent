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
    # book 0.75 YES + market 0.70 YES → consensus, BUY_YES (EV guard: 0.75 >= 0.70 ✓)
    sig = consensus.evaluate(_market(yes=0.70), _bm(prob=0.75))
    assert sig is not None
    assert sig.direction == Direction.BUY_YES
    assert sig.entry_reason == EntryReason.CONSENSUS
    assert abs(sig.edge - (0.99 - 0.70)) < 1e-9


def test_consensus_buy_no_when_both_favor_no() -> None:
    # book 0.25 (NO favori %75) + market 0.30 (NO favori %70) → consensus BUY_NO
    # entry=0.70 (no_price), our_side_prob=1-0.25=0.75 >= 0.70 ✓
    sig = consensus.evaluate(_market(yes=0.30), _bm(prob=0.25))
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


def test_above_max_price_returns_none() -> None:
    # consensus var, min_price geçti, ama 76¢ > 75¢ max → atla (R/R dar)
    assert consensus.evaluate(_market(yes=0.76), _bm(prob=0.80), max_price=0.75) is None


def test_at_max_price_boundary_enters() -> None:
    # entry_price == max_price sınırda geçerli (> 0.75 red, == 0.75 kabul)
    sig = consensus.evaluate(_market(yes=0.75), _bm(prob=0.80), max_price=0.75)
    assert sig is not None
    assert sig.direction == Direction.BUY_YES


def test_ev_guard_negative_ev_rejected_buy_yes() -> None:
    """Bookmaker %70, PM yes 74¢ → biz 74¢ ödüyoruz bookmaker %70 veriyor → NEGATIF EV."""
    # direction=BUY_YES, entry=0.74, bm_prob=0.70 → our_side_prob (0.70) < entry (0.74) → None
    assert consensus.evaluate(_market(yes=0.74), _bm(prob=0.70)) is None


def test_ev_guard_negative_ev_rejected_buy_no() -> None:
    """Spurs 84¢ bug senaryosu: BUY_NO entry 0.74 (no_price), bm %20 (YES) → bizim NO %80.
    Ama bizim testte entry 0.74 NO_price, our_side_prob = 1-0.20 = 0.80 > 0.74 → ENTER.
    Sikici senaryo: PM no=0.74, book YES prob=0.28 → our NO prob = 0.72 < 0.74 → SKIP (NEG EV).
    """
    # yes=0.26 -> no_price=0.74. book YES=0.28 -> NO=0.72. NO is favored on market AND book.
    # our_side_prob (NO) = 0.72 < entry_price 0.74 → negatif EV → None
    assert consensus.evaluate(_market(yes=0.26), _bm(prob=0.28)) is None


def test_ev_guard_positive_ev_accepted() -> None:
    """Bookmaker %80, PM 70¢ → pozitif EV (our_side_prob 0.80 >= 0.70)."""
    sig = consensus.evaluate(_market(yes=0.70), _bm(prob=0.80))
    assert sig is not None
    assert sig.direction == Direction.BUY_YES


def test_c_confidence_returns_none() -> None:
    assert consensus.evaluate(_market(yes=0.70), _bm(conf="C")) is None


def test_at_50_50_boundary() -> None:
    # book 0.50 == 0.50 → favors_yes True. market 0.50 == 0.50 → True. Consensus var.
    # Ama 0.50 < 0.65 min_price → None
    assert consensus.evaluate(_market(yes=0.50), _bm(prob=0.50), min_price=0.65) is None


def test_signal_has_correct_metadata() -> None:
    # EV guard: bm_prob (0.80) >= entry (0.75) ✓
    sig = consensus.evaluate(_market(yes=0.75), _bm(prob=0.80, conf="A"))
    assert sig is not None
    assert sig.confidence == "A"
    assert sig.bookmaker_prob == 0.80
    assert sig.sport_tag == "nba"
    assert sig.event_id == "evt_1"
