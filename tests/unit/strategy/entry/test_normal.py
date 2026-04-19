"""entry/normal.py için birim testler."""
from __future__ import annotations

from src.domain.analysis.probability import BookmakerProbability
from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.strategy.entry import normal


def _market(yes_price: float = 0.50) -> MarketData:
    return MarketData(
        condition_id="0x1",
        question="Will Lakers beat Celtics?",
        slug="nba-lal-bos-2026",
        yes_token_id="y", no_token_id="n",
        yes_price=yes_price, no_price=1 - yes_price,
        liquidity=50000, volume_24h=10000,
        tags=[],
        end_date_iso="2026-04-14T00:00:00Z",
        sport_tag="basketball_nba",
        event_id="evt_1",
    )


def _bm(prob: float = 0.60, conf: str = "B") -> BookmakerProbability:
    return BookmakerProbability(
        probability=prob, confidence=conf,
        bookmaker_prob=prob, num_bookmakers=10.0, has_sharp=(conf == "A"),
    )


def test_buy_yes_signal_generated() -> None:
    m = _market(yes_price=0.50)
    bm = _bm(prob=0.60, conf="B")
    # Raw=0.10, threshold=0.06 → BUY_YES edge=0.10
    sig = normal.evaluate(m, bm, min_edge=0.06)
    assert sig is not None
    assert sig.direction == Direction.BUY_YES
    assert abs(sig.edge - 0.10) < 1e-9
    assert sig.entry_reason == EntryReason.NORMAL
    assert sig.size_usdc == 0.0  # gate sizing uygular


def test_buy_no_signal_when_anchor_below_market() -> None:
    m = _market(yes_price=0.60)
    bm = _bm(prob=0.40, conf="B")
    sig = normal.evaluate(m, bm)
    assert sig is not None
    assert sig.direction == Direction.BUY_NO


def test_c_confidence_blocks() -> None:
    m = _market(yes_price=0.50)
    bm = _bm(prob=0.60, conf="C")
    assert normal.evaluate(m, bm) is None


def test_no_edge_returns_none() -> None:
    m = _market(yes_price=0.50)
    bm = _bm(prob=0.53, conf="B")  # raw=0.03 < threshold 0.06 → HOLD
    assert normal.evaluate(m, bm) is None


def test_a_confidence_unified_threshold() -> None:
    """SPEC-010 + Bug #2 fix: A=1.00 multiplier → %6 esik (B ile unified)."""
    m = _market(yes_price=0.50)
    # A conf threshold = 0.06 × 1.00 = 0.06
    # raw=0.05 → HOLD (below threshold)
    bm_a = _bm(prob=0.55, conf="A")
    assert normal.evaluate(m, bm_a) is None
    # raw=0.07 → BUY_YES (0.07 > 0.06)
    bm_a2 = _bm(prob=0.57, conf="A")
    sig = normal.evaluate(m, bm_a2)
    assert sig is not None
    assert sig.confidence == "A"


def test_signal_copies_sport_tag_and_event_id() -> None:
    m = _market(yes_price=0.50)
    bm = _bm(prob=0.60, conf="B")
    sig = normal.evaluate(m, bm)
    assert sig.sport_tag == "basketball_nba"
    assert sig.event_id == "evt_1"
    assert sig.bookmaker_prob == 0.60


# --- SPEC-013: min_favorite_probability guard ---

def test_normal_entry_underdog_rejected_by_favorite_filter() -> None:
    """Bookmaker bizim tarafa %44 -> our_side < 0.55 -> favorite filter skip."""
    m = _market(yes_price=0.30)
    bm = _bm(prob=0.44, conf="A")
    sig = normal.evaluate(m, bm, min_edge=0.06, min_favorite_probability=0.55)
    assert sig is None


def test_normal_entry_favorite_accepted_by_filter() -> None:
    """Bookmaker bizim tarafa %60 (BUY_YES) -> our_side >= 0.55 -> girer."""
    m = _market(yes_price=0.50)
    bm = _bm(prob=0.60, conf="A")
    sig = normal.evaluate(m, bm, min_edge=0.06, min_favorite_probability=0.55)
    assert sig is not None
    assert sig.direction == Direction.BUY_YES


def test_normal_entry_buy_no_favorite_side_accepted() -> None:
    """BUY_NO: our_side_prob = 1 - bm_prob; bm YES 0.30 -> NO 0.70 >= 0.55 -> girer."""
    m = _market(yes_price=0.45)
    bm = _bm(prob=0.30, conf="A")
    sig = normal.evaluate(m, bm, min_edge=0.06, min_favorite_probability=0.55)
    assert sig is not None
    assert sig.direction == Direction.BUY_NO


def test_normal_entry_buy_no_underdog_side_rejected() -> None:
    """BUY_NO'da our_side_prob = 1 - 0.48 = 0.52 < 0.55 -> skip."""
    m = _market(yes_price=0.55)
    bm = _bm(prob=0.48, conf="A")
    sig = normal.evaluate(m, bm, min_edge=0.06, min_favorite_probability=0.55)
    assert sig is None
