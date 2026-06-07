"""consensus.py için birim testler (DECISIONS §6.4)."""
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
    # SPEC-Z13: pozitif model edge gerekli — book 0.78 > market 0.75 → edge +%3
    sig = consensus.evaluate(_market(yes=0.75), _bm(prob=0.78, conf="A"))
    assert sig is not None
    assert sig.confidence == "A"
    assert sig.bookmaker_prob == 0.78
    assert sig.sport_tag == "nba"
    assert sig.event_id == "evt_1"


# SPEC-Z13 (2026-06-03): min_model_edge guard.
# SPEC-Z14 (2026-06-04 revize): favorite_band — direction-adjusted MODEL OLASILIĞI
# üzerinden (price değil, prob_for_side). Z13 saf semantik için Z14 band'ı testlerde
# boş range ile kapatıyoruz.

_BAND_DISABLED: dict[str, float] = {
    "favorite_band_min_prob": 0.99,
    "favorite_band_max_prob": 0.99,
}


def test_buy_yes_negative_model_edge_rejected_out_of_band() -> None:
    """BUY_YES + negatif model edge + band dışı → Z13 guard reddeder (Azkara)."""
    # market 0.67 YES + book 0.62 YES → model_edge = -0.05.
    # Band kapalı (boş range) → Z13 guard tek başına aktif → None.
    sig = consensus.evaluate(
        _market(yes=0.67), _bm(prob=0.62),
        min_price=0.65, min_model_edge=0.0, **_BAND_DISABLED,
    )
    assert sig is None


def test_buy_yes_negative_model_edge_accepted_in_favorite_band() -> None:
    """SPEC-Z14: prob_for_side favorite_band içinde → negatif edge consensus kabul."""
    # BUY_YES → prob_for_side = bm.prob = 0.62 ∈ [0.60, 0.80) → band aktif → kabul.
    sig = consensus.evaluate(
        _market(yes=0.67), _bm(prob=0.62),
        min_price=0.65, min_model_edge=0.0,
        favorite_band_min_prob=0.60, favorite_band_max_prob=0.80,
    )
    assert sig is not None
    assert sig.direction == Direction.BUY_YES


def test_buy_yes_positive_model_edge_accepted() -> None:
    """BUY_YES + pozitif model edge → Z14 band'ından bağımsız geçer."""
    # market 0.65 YES + book 0.70 YES → model_edge = +0.05 → pozitif.
    sig = consensus.evaluate(
        _market(yes=0.65), _bm(prob=0.70), min_price=0.65, min_model_edge=0.0,
    )
    assert sig is not None
    assert sig.direction == Direction.BUY_YES


def test_buy_no_negative_model_edge_rejected_out_of_band() -> None:
    """BUY_NO + negatif model edge + band dışı → Z13 guard reddeder."""
    # market 0.30 YES (NO favori), book 0.35 YES → BUY_NO, prob_for_side = 1-0.35 = 0.65.
    # 0.65 normalde band içinde — fakat _BAND_DISABLED ile boş range → Z13 aktif.
    # model_edge (BUY_NO) = 0.30 - 0.35 = -0.05 → reject.
    sig = consensus.evaluate(
        _market(yes=0.30), _bm(prob=0.35),
        min_price=0.65, min_model_edge=0.0, **_BAND_DISABLED,
    )
    assert sig is None


def test_buy_no_negative_model_edge_accepted_in_favorite_band() -> None:
    """SPEC-Z14: BUY_NO prob_for_side favorite_band içinde → negatif edge kabul (Zhang)."""
    # BUY_NO, prob_for_side = 1 - 0.35 = 0.65 ∈ [0.60, 0.80) → band aktif → kabul.
    sig = consensus.evaluate(
        _market(yes=0.30), _bm(prob=0.35),
        min_price=0.65, min_model_edge=0.0,
        favorite_band_min_prob=0.60, favorite_band_max_prob=0.80,
    )
    assert sig is not None
    assert sig.direction == Direction.BUY_NO


def test_buy_no_positive_model_edge_accepted() -> None:
    """BUY_NO + pozitif model edge → band'dan bağımsız geçer."""
    # market 0.30 YES (NO 0.70 favori), book 0.20 YES → NO favorisi her iki yanda.
    # model_edge = market.yes - bm_prob = 0.30 - 0.20 = +0.10 → pozitif.
    sig = consensus.evaluate(
        _market(yes=0.30), _bm(prob=0.20), min_price=0.65, min_model_edge=0.0,
    )
    assert sig is not None
    assert sig.direction == Direction.BUY_NO


def test_custom_min_model_edge_threshold_out_of_band() -> None:
    """min_model_edge=0.10 + band kapalı → küçük pozitif edge'ler reddedilir."""
    # market 0.65 YES + book 0.70 YES → model_edge = +0.05.
    # Default 0.0 + band kapalı → geçer.
    # Strict 0.10 + band kapalı → reddedilir.
    sig_default = consensus.evaluate(
        _market(yes=0.65), _bm(prob=0.70),
        min_price=0.65, min_model_edge=0.0, **_BAND_DISABLED,
    )
    sig_strict = consensus.evaluate(
        _market(yes=0.65), _bm(prob=0.70),
        min_price=0.65, min_model_edge=0.10, **_BAND_DISABLED,
    )
    assert sig_default is not None
    assert sig_strict is None


def test_favorite_band_upper_bound_exclusive() -> None:
    """SPEC-Z14: prob_for_side == favorite_band_max_prob → band dışı (yarı-açık aralık)."""
    # BUY_YES, prob_for_side = bm.prob = 0.80 == max → band dışı → Z13 aktif.
    # market 0.85 YES + book 0.80 YES → model_edge = -0.05 → reject.
    sig = consensus.evaluate(
        _market(yes=0.85), _bm(prob=0.80),
        min_price=0.65, min_model_edge=0.0,
        favorite_band_min_prob=0.60, favorite_band_max_prob=0.80,
    )
    assert sig is None


def test_favorite_band_lower_bound_inclusive() -> None:
    """SPEC-Z14: prob_for_side == favorite_band_min_prob → band içi (yarı-açık aralık)."""
    # BUY_YES, prob_for_side = bm.prob = 0.65 == min → band içi → kabul.
    # market 0.70 YES + book 0.65 YES → model_edge = -0.05 → band bypass → kabul.
    sig = consensus.evaluate(
        _market(yes=0.70), _bm(prob=0.65),
        min_price=0.65, min_model_edge=0.0,
        favorite_band_min_prob=0.65, favorite_band_max_prob=0.80,
    )
    assert sig is not None
