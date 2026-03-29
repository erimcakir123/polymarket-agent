"""Tests for upset hunter bidirectional (YES + NO) support."""
from src.upset_hunter import UpsetCandidate, pre_filter
from src.models import MarketData


def test_upset_candidate_has_direction_fields():
    """UpsetCandidate should have no_price, no_token_id, direction fields."""
    c = UpsetCandidate(
        condition_id="cid1",
        question="Team A vs Team B",
        slug="team-a-vs-team-b",
        yes_price=0.90,
        yes_token_id="tok_yes",
        no_price=0.10,
        no_token_id="tok_no",
        direction="BUY_NO",
        volume_24h=50000,
        liquidity=10000,
        odds_api_implied=None,
        divergence=None,
        hours_to_match=2.0,
        upset_type="underdog",
        event_id="evt1",
    )
    assert c.direction == "BUY_NO"
    assert c.no_price == 0.10
    assert c.no_token_id == "tok_no"


def test_pre_filter_produces_no_side_candidate():
    """When NO price is in 5-15c zone, pre_filter should produce BUY_NO candidate."""
    markets = [
        MarketData(
            condition_id="cid1",
            question="Will Team A win?",
            slug="team-a-win",
            yes_price=0.92,
            no_price=0.08,
            yes_token_id="tok_yes",
            no_token_id="tok_no",
            volume_24h=50000,
            liquidity=10000,
            event_id="evt1",
        ),
    ]
    candidates = pre_filter(markets, min_price=0.05, max_price=0.15)
    assert any(c.direction == "BUY_NO" for c in candidates)


def test_pre_filter_produces_yes_side_candidate():
    """When YES price is in 5-15c zone, pre_filter should produce BUY_YES candidate."""
    markets = [
        MarketData(
            condition_id="cid2",
            question="Will Team B win?",
            slug="team-b-win",
            yes_price=0.08,
            no_price=0.92,
            yes_token_id="tok_yes",
            no_token_id="tok_no",
            volume_24h=50000,
            liquidity=10000,
            event_id="evt2",
        ),
    ]
    candidates = pre_filter(markets, min_price=0.05, max_price=0.15)
    assert any(c.direction == "BUY_YES" for c in candidates)


def test_pre_filter_produces_both_sides():
    """When both YES and NO prices are in 5-15c zone, produce two candidates."""
    # This is an unusual market but the logic should handle it
    markets = [
        MarketData(
            condition_id="cid3",
            question="Draw market?",
            slug="draw-market",
            yes_price=0.10,
            no_price=0.10,  # Both in zone (unusual but valid)
            yes_token_id="tok_yes",
            no_token_id="tok_no",
            volume_24h=50000,
            liquidity=10000,
            event_id="evt3",
        ),
    ]
    candidates = pre_filter(markets, min_price=0.05, max_price=0.15)
    directions = {c.direction for c in candidates if c.condition_id == "cid3"}
    assert "BUY_YES" in directions
    assert "BUY_NO" in directions


def test_pre_filter_no_candidate_when_price_out_of_range():
    """Neither side qualifies when both prices are outside 5-15c zone."""
    markets = [
        MarketData(
            condition_id="cid4",
            question="Will Team C win?",
            slug="team-c-win",
            yes_price=0.50,
            no_price=0.50,
            yes_token_id="tok_yes",
            no_token_id="tok_no",
            volume_24h=50000,
            liquidity=10000,
            event_id="evt4",
        ),
    ]
    candidates = pre_filter(markets, min_price=0.05, max_price=0.15)
    assert len(candidates) == 0


def test_divergence_direction_aware_yes_side():
    """YES-side divergence = odds_implied - yes_price."""
    markets = [
        MarketData(
            condition_id="cid5",
            question="Will Team D win?",
            slug="team-d-win",
            yes_price=0.10,
            no_price=0.90,
            yes_token_id="tok_yes",
            no_token_id="tok_no",
            volume_24h=50000,
            liquidity=10000,
            event_id="evt5",
            odds_api_implied_prob=0.25,  # bookmaker says 25% YES
        ),
    ]
    candidates = pre_filter(markets, min_price=0.05, max_price=0.15)
    yes_candidates = [c for c in candidates if c.direction == "BUY_YES"]
    assert len(yes_candidates) == 1
    # divergence = 0.25 - 0.10 = 0.15
    assert abs(yes_candidates[0].divergence - 0.15) < 1e-9


def test_divergence_direction_aware_no_side():
    """NO-side divergence = (1 - odds_implied) - no_price."""
    markets = [
        MarketData(
            condition_id="cid6",
            question="Will Team E win?",
            slug="team-e-win",
            yes_price=0.90,
            no_price=0.10,
            yes_token_id="tok_yes",
            no_token_id="tok_no",
            volume_24h=50000,
            liquidity=10000,
            event_id="evt6",
            odds_api_implied_prob=0.75,  # bookmaker says 75% YES → 25% NO
        ),
    ]
    candidates = pre_filter(markets, min_price=0.05, max_price=0.15)
    no_candidates = [c for c in candidates if c.direction == "BUY_NO"]
    assert len(no_candidates) == 1
    # divergence = (1 - 0.75) - 0.10 = 0.15
    assert abs(no_candidates[0].divergence - 0.15) < 1e-9


def test_divergence_filters_per_side_independently():
    """If YES divergence passes but NO divergence fails, only YES candidate emitted."""
    # yes_price=0.10, odds_implied=0.25 → YES div = 0.15 (passes 0.05 threshold)
    # no_price=0.90 (out of zone, won't produce NO candidate anyway)
    # But test with both in zone:
    markets = [
        MarketData(
            condition_id="cid7",
            question="Close match?",
            slug="close-match",
            yes_price=0.10,
            no_price=0.12,
            yes_token_id="tok_yes",
            no_token_id="tok_no",
            volume_24h=50000,
            liquidity=10000,
            event_id="evt7",
            odds_api_implied_prob=0.90,  # YES div = 0.90-0.10 = 0.80, NO div = 0.10-0.12 = -0.02
        ),
    ]
    candidates = pre_filter(markets, min_price=0.05, max_price=0.15, min_odds_divergence=0.05)
    # YES side should pass (div=0.80), NO side should fail (div=-0.02)
    assert any(c.direction == "BUY_YES" for c in candidates)
    assert not any(c.direction == "BUY_NO" for c in candidates)
