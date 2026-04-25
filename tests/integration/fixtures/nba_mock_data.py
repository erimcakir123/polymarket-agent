"""NBA integration test için mock data factory'leri."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.models.market import MarketData
from src.models.position import Position
from src.strategy.entry.gate import EntryGate, GateConfig
from src.orchestration.edge_enricher import EdgeContext


def make_market(
    condition_id: str = "cid_test",
    question: str = "Will the Los Angeles Lakers beat the Boston Celtics?",
    yes_price: float = 0.45,
    no_price: float = 0.55,
    volume_24h: float = 10_000.0,
    sport_tag: str = "basketball_nba",
    sports_market_type: str = "",
    event_id: str | None = "evt_lal_bos",
    match_start_iso: str = "",
) -> MarketData:
    if not match_start_iso:
        match_start_iso = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    return MarketData(
        condition_id=condition_id,
        question=question,
        slug=f"slug-{condition_id}",
        yes_token_id=f"tok_yes_{condition_id}",
        no_token_id=f"tok_no_{condition_id}",
        yes_price=yes_price,
        no_price=no_price,
        liquidity=5_000.0,
        volume_24h=volume_24h,
        end_date_iso="2026-06-01T00:00:00Z",
        match_start_iso=match_start_iso,
        event_id=event_id,
        sport_tag=sport_tag,
        sports_market_type=sports_market_type,
    )


def make_gate(
    bankroll: float = 1000.0,
    active_sports: list[str] | None = None,
    min_gap_threshold: float = 0.08,
    positions: dict | None = None,
    edge_enricher=None,
) -> tuple[EntryGate, MagicMock]:
    """Returns (gate, mock_odds_enricher_callable)."""
    if active_sports is None:
        active_sports = ["basketball_nba"]

    cfg = GateConfig(
        min_favorite_probability=0.50,
        max_entry_price=0.80,
        max_positions=10,
        max_exposure_pct=0.50,
        hard_cap_overflow_pct=0.02,
        min_entry_size_pct=0.015,
        confidence_bet_pct={"A": 0.05, "B": 0.03},
        max_single_bet_usdc=100.0,
        max_bet_pct=0.05,
        probability_weighted=True,
        min_bookmakers=1,
        min_sharps=0,
        active_sports=active_sports,
        min_gap_threshold=min_gap_threshold,
        min_market_volume=5_000.0,
        min_polymarket_price=0.10,
    )

    mock_portfolio = MagicMock()
    mock_portfolio.positions = positions or {}
    mock_portfolio.bankroll.return_value = bankroll

    # Default odds enricher returns high-quality data
    mock_prob = MagicMock()
    mock_prob.prob = 0.58
    mock_prob.has_sharp = True
    mock_prob.num_bookmakers = 7.0

    mock_enrich_result = MagicMock()
    mock_enrich_result.probability = mock_prob
    mock_enrich_result.fail_reason = None

    mock_enricher_fn = MagicMock(return_value=mock_enrich_result)

    gate = EntryGate(
        config=cfg,
        portfolio=mock_portfolio,
        circuit_breaker=None,
        cooldown=None,
        blacklist=None,
        odds_enricher=mock_enricher_fn,
        manipulation_checker=None,
        edge_enricher=edge_enricher,
    )
    return gate, mock_enricher_fn


def make_enricher_result(prob: float = 0.58, has_sharp: bool = True, num_bookmakers: float = 7.0):
    """Return a mock odds enricher result callable."""
    mock_prob = MagicMock()
    mock_prob.prob = prob
    mock_prob.has_sharp = has_sharp
    mock_prob.num_bookmakers = num_bookmakers

    mock_result = MagicMock()
    mock_result.probability = mock_prob
    mock_result.fail_reason = None
    return mock_result


def make_position(
    condition_id: str = "cid_test",
    direction: str = "BUY_YES",
    entry_price: float = 0.60,
    size_usdc: float = 30.0,
    bid_price: float = 0.60,
    sport_tag: str = "basketball_nba",
    sports_market_type: str = "",
    spread_line: float | None = None,
    total_line: float | None = None,
    total_side=None,
    event_id: str = "evt_lal_bos",
    scaled_out_50: bool = False,
    match_start_iso: str = "",
) -> Position:
    shares = size_usdc / entry_price if entry_price > 0 else 0.0
    if not match_start_iso:
        # 3 hours ago — gives elapsed_pct > 1.0 for NBA (2.5h duration)
        match_start_iso = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    return Position(
        condition_id=condition_id,
        token_id=f"tok_{condition_id}",
        direction=direction,
        entry_price=entry_price,
        size_usdc=size_usdc,
        shares=shares,
        current_price=bid_price,
        bid_price=bid_price,
        anchor_probability=0.65,
        sport_tag=sport_tag,
        sports_market_type=sports_market_type,
        spread_line=spread_line,
        total_line=total_line,
        total_side=total_side,
        event_id=event_id,
        match_start_iso=match_start_iso,
        slug=f"slug-{condition_id}",
        scaled_out_50=scaled_out_50,
    )


def make_score_info(
    available: bool = True,
    period_number: int = 4,
    clock_seconds: int = 120,
    our_score: int = 85,
    opp_score: int = 100,
    period: str = "4th Quarter",
    is_live: bool = True,
) -> dict:
    deficit = opp_score - our_score
    return {
        "available": available,
        "period_number": period_number,
        "clock_seconds": clock_seconds,
        "our_score": our_score,
        "opp_score": opp_score,
        "deficit": deficit,
        "period": period,
        "is_live": is_live,
        "map_diff": -deficit,
        "linescores": [],
        "our_is_home": True,
        "minute": None,
        "regulation_state": "",
        "our_outcome": None,
        "knockout": False,
        "inning": None,
        "espn_start": "",
        "home_team_id": "13",
        "away_team_id": "2",
    }
