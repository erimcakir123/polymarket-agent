"""Tennis EdgeCandidate -> Signal adapter — unit tests (Stage 2 PLAN-TENNIS-001)."""
from __future__ import annotations

import pytest

from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.signal import Signal
from src.strategy.entry.tennis_entry import EdgeCandidate
from src.strategy.entry.tennis_signal_adapter import tennis_candidate_to_signal


def _market(
    *,
    condition_id: str = "0xCID",
    yes_price: float = 0.50,
    event_id: str | None = "evt-123",
    sport_tag: str = "tennis",
) -> MarketData:
    return MarketData(
        condition_id=condition_id,
        question="Will Sinner win the first set vs Alcaraz?",
        slug="sinner-alcaraz-first-set",
        yes_token_id="yes-tok",
        no_token_id="no-tok",
        yes_price=yes_price,
        no_price=round(1.0 - yes_price, 4),
        liquidity=10_000.0,
        volume_24h=5_000.0,
        end_date_iso="2026-05-20T18:00:00Z",
        event_id=event_id,
        sport_tag=sport_tag,
    )


def _candidate(*, edge: float = 0.08, model_p: float = 0.58, market_p: float = 0.50) -> EdgeCandidate:
    return EdgeCandidate(
        event_id="evt-123",
        market_type="first_set_winner",
        model_p=model_p,
        market_p=market_p,
        edge=edge,
    )


def test_adapter_buy_yes_when_edge_positive() -> None:
    sig = tennis_candidate_to_signal(_candidate(edge=0.08), _market(), tier="A")
    assert sig.direction == Direction.BUY_YES


def test_adapter_buy_no_when_edge_negative() -> None:
    cand = _candidate(edge=-0.07, model_p=0.43, market_p=0.50)
    sig = tennis_candidate_to_signal(cand, _market(), tier="B")
    assert sig.direction == Direction.BUY_NO


def test_adapter_preserves_anchor_probability() -> None:
    """anchor_probability == candidate.model_p (NOT remapped to direction)."""
    cand = _candidate(edge=-0.10, model_p=0.40, market_p=0.50)
    sig = tennis_candidate_to_signal(cand, _market(), tier="A")
    assert sig.anchor_probability == 0.40  # P(YES), not 1 - 0.40


def test_adapter_sets_tennis_entry_reason() -> None:
    sig = tennis_candidate_to_signal(_candidate(), _market(), tier="A")
    assert sig.entry_reason == EntryReason.TENNIS


def test_adapter_zeroes_bookmaker_fields() -> None:
    sig = tennis_candidate_to_signal(_candidate(), _market(), tier="A")
    assert sig.bookmaker_prob == 0.0
    assert sig.num_bookmakers == 0
    assert sig.has_sharp is False


def test_adapter_sets_sport_tag_to_tennis_atp() -> None:
    """FIX 3 (2026-05-20): sport_tag hardcoded 'tennis_atp' (WTA filter upstream).

    Dashboard Sport ROI treemap '<category>_<league>' formatına göre grup yapıyor;
    boş veya 'tennis' tag dashboard'da görünmez/karışır. WTA parser'da reject
    edildiği için tüm tenis sinyalleri ATP — hardcode güvenli."""
    # market.sport_tag farklı değerlerde gelse de adapter hep tennis_atp döner
    for market_tag in ["tennis", "tennis_atp", "", "wta_atp", None]:
        market = _market(sport_tag=market_tag or "")
        sig = tennis_candidate_to_signal(_candidate(), market, tier="A")
        assert sig.sport_tag == "tennis_atp", f"market_tag={market_tag!r} produced {sig.sport_tag!r}"


@pytest.mark.parametrize("tier", ["A", "B"])
def test_adapter_confidence_tier_passed_through(tier: str) -> None:
    sig = tennis_candidate_to_signal(_candidate(), _market(), tier=tier)
    assert sig.confidence == tier


def test_adapter_maps_condition_id_market_price_edge_event_id() -> None:
    """Sanity: remaining mapping fields wired through correctly."""
    market = _market(condition_id="0xABC", yes_price=0.50, event_id="evt-XYZ")
    cand = _candidate(edge=0.08, model_p=0.58, market_p=0.50)
    sig = tennis_candidate_to_signal(cand, market, tier="A")
    assert sig.condition_id == "0xABC"
    assert sig.market_price == 0.50
    assert sig.edge == 0.08
    assert sig.event_id == "evt-XYZ"
    assert sig.size_usdc == 0.0


def test_adapter_event_id_empty_when_market_event_id_none() -> None:
    market = _market(event_id=None)
    sig = tennis_candidate_to_signal(_candidate(), market, tier="A")
    assert sig.event_id == ""
