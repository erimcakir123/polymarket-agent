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


def test_a_confidence_no_extra_threshold_penalty() -> None:
    """2026-05-15 rollback (DECISIONS §6.3): A çarpanı 1.25 → 1.00.

    2026-06-10'da fark edildi: domain default'u 1.25'te unutulmuştu — A
    işlemler fiilen %25 şişik eşik görüyordu. A artık B ile aynı eşiği görür.
    """
    m = _market(yes_price=0.50)
    # raw=0.055 > threshold 0.05 × 1.00 → BUY_YES (eski 1.25 ile None olurdu)
    bm_a = _bm(prob=0.555, conf="A")
    sig = normal.evaluate(m, bm_a)
    assert sig is not None
    assert sig.confidence == "A"
    # raw=0.03 < 0.05 → eşik hâlâ çalışıyor
    bm_low = _bm(prob=0.53, conf="A")
    assert normal.evaluate(m, bm_low) is None


def test_signal_copies_sport_tag_and_event_id() -> None:
    m = _market(yes_price=0.50)
    bm = _bm(prob=0.60, conf="B")
    sig = normal.evaluate(m, bm)
    assert sig.sport_tag == "basketball_nba"
    assert sig.event_id == "evt_1"
    assert sig.bookmaker_prob == 0.60
