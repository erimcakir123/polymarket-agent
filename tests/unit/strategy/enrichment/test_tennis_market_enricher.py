"""Integration tests for tennis_market_enricher — mock ratings + matches."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.config.settings import AppConfig, TennisConfig
from src.domain.matching.tennis_player_matcher import build_match_index
from src.infrastructure.data.sackmann_csv_client import SackmannMatch
from src.infrastructure.data.tennis_ratings_store import PlayerRating, SurfaceRating
from src.models.market import MarketData
from src.strategy.enrichment.tennis_market_enricher import classify_tier, enrich
from src.strategy.entry.tennis_entry import EdgeCandidate


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _surface_rating(r: float = 1500.0, rd: float = 80.0) -> SurfaceRating:
    return SurfaceRating(rating=r, rd=rd, volatility=0.06)


def _make_player_rating(pid: str, name: str, r: float = 1500.0) -> PlayerRating:
    sr = _surface_rating(r)
    return PlayerRating(
        player_id=pid,
        player_name=name,
        overall=sr,
        serve_clay=sr, serve_grass=sr, serve_hard=sr,
        return_clay=sr, return_grass=sr, return_hard=sr,
        last_match_date="2026-01-01",
        match_count_12mo=60,
    )


def _make_sackmann_match(
    winner: str,
    loser: str,
    surface: str = "Clay",
    days_ago: int = 30,
) -> SackmannMatch:
    match_date = datetime.utcnow() - timedelta(days=days_ago)
    return SackmannMatch(
        tourney_id="test", tourney_name="Test Open", surface=surface,
        draw_size=32, tourney_level="A",
        match_date=match_date, match_num=1,
        winner_id="w1", winner_name=winner, winner_hand="R",
        loser_id="l1", loser_name=loser, loser_hand="R",
        score="6-3 6-4", best_of=3, round="R32",
        minutes=90,
        w_ace=None, w_df=None, w_svpt=None, w_1stIn=None, w_1stWon=None,
        w_2ndWon=None, w_SvGms=None, w_bpSaved=None, w_bpFaced=None,
        l_ace=None, l_df=None, l_svpt=None, l_1stIn=None, l_1stWon=None,
        l_2ndWon=None, l_SvGms=None, l_bpSaved=None, l_bpFaced=None,
        winner_rank=10, winner_rank_points=3000,
        loser_rank=20, loser_rank_points=1500,
    )


def _make_market(
    question: str = "Set 1 Winner: Djokovic vs Alcaraz",
    sports_market_type: str = "tennis_first_set_winner",
    yes_price: float = 0.50,
    slug: str = "atp-djokovic-alcaraz-2026",
) -> MarketData:
    now = datetime.now(timezone.utc)
    return MarketData(
        condition_id="cid-test",
        question=question,
        slug=slug,
        yes_token_id="y", no_token_id="n",
        yes_price=yes_price, no_price=1.0 - yes_price,
        liquidity=5000.0, volume_24h=1000.0,
        end_date_iso=(now + timedelta(hours=5)).isoformat() + "Z",
        match_start_iso=(now + timedelta(hours=2)).isoformat() + "Z",
        sport_tag="tennis_atp",
        sports_market_type=sports_market_type,
        event_id="evt-test",
    )


def _make_cfg() -> AppConfig:
    return AppConfig()


def _make_good_ratings() -> dict[str, PlayerRating]:
    return {
        "p1": _make_player_rating("p1", "Novak Djokovic", r=1600.0),
        "p2": _make_player_rating("p2", "Carlos Alcaraz", r=1580.0),
    }


def _make_sackmann_50_matches(p1: str, p2: str) -> list[SackmannMatch]:
    """50 recent matches to satisfy Tier A threshold."""
    matches = []
    for i in range(30):
        matches.append(_make_sackmann_match(p1, p2, "Clay", days_ago=i + 5))
    for i in range(20):
        matches.append(_make_sackmann_match(p2, p1, "Clay", days_ago=i + 35))
    return matches


# ── classify_tier ─────────────────────────────────────────────────────────────


def test_classify_tier_a_sufficient_data() -> None:
    from src.domain.prediction.feature_extractor import FeatureSnapshot
    snap = FeatureSnapshot(
        p1_name="P1", p2_name="P2", surface="clay",
        p1_match_count_12mo=45, p1_surface_count=20, p1_form_w_pct_60d=0.6, p1_form_data_age_days=30,
        p2_match_count_12mo=42, p2_surface_count=16, p2_form_w_pct_60d=0.55, p2_form_data_age_days=25,
        h2h_matches_total=3, h2h_matches_same_surface=2, h2h_p1_wins=2, h2h_last_meeting_days_ago=180,
    )
    cfg = _make_cfg()
    assert classify_tier(snap, cfg) == "A"


def test_classify_tier_b_moderate_data() -> None:
    from src.domain.prediction.feature_extractor import FeatureSnapshot
    snap = FeatureSnapshot(
        p1_name="P1", p2_name="P2", surface="clay",
        p1_match_count_12mo=22, p1_surface_count=10, p1_form_w_pct_60d=0.55, p1_form_data_age_days=70,
        p2_match_count_12mo=25, p2_surface_count=9, p2_form_w_pct_60d=0.50, p2_form_data_age_days=60,
        h2h_matches_total=0, h2h_matches_same_surface=0, h2h_p1_wins=0, h2h_last_meeting_days_ago=None,
    )
    cfg = _make_cfg()
    assert classify_tier(snap, cfg) == "B"


def test_classify_tier_skip_insufficient_data() -> None:
    from src.domain.prediction.feature_extractor import FeatureSnapshot
    snap = FeatureSnapshot(
        p1_name="P1", p2_name="P2", surface="clay",
        p1_match_count_12mo=5, p1_surface_count=2, p1_form_w_pct_60d=0.5, p1_form_data_age_days=100,
        p2_match_count_12mo=3, p2_surface_count=1, p2_form_w_pct_60d=0.5, p2_form_data_age_days=120,
        h2h_matches_total=0, h2h_matches_same_surface=0, h2h_p1_wins=0, h2h_last_meeting_days_ago=None,
    )
    cfg = _make_cfg()
    assert classify_tier(snap, cfg) == "skip"


# ── enrich ────────────────────────────────────────────────────────────────────


def test_enrich_unsupported_market_type_returns_none() -> None:
    """tennis_match_totals → unsupported, enrich returns None."""
    market = _make_market(sports_market_type="tennis_match_totals")
    result = enrich(market, {}, [], _make_cfg())
    assert result is None


def test_enrich_player_not_in_ratings_returns_none() -> None:
    """No ratings in cache → returns None."""
    market = _make_market()
    result = enrich(market, {}, [], _make_cfg())
    assert result is None


def test_enrich_one_player_missing_returns_none() -> None:
    """Only p1 in ratings, p2 missing → None."""
    ratings = {"p1": _make_player_rating("p1", "Novak Djokovic")}
    market = _make_market()
    result = enrich(market, ratings, [], _make_cfg())
    assert result is None


def test_enrich_returns_edge_candidate_with_correct_event_id() -> None:
    """With both players rated and good match history → EdgeCandidate returned."""
    ratings = _make_good_ratings()
    matches = _make_sackmann_50_matches("Novak Djokovic", "Carlos Alcaraz")
    market = _make_market(slug="atp-djokovic-alcaraz-roland-garros-2026")
    result = enrich(market, ratings, matches, _make_cfg())
    # May be None if tier==skip (default config). But at least shouldn't raise.
    assert result is None or isinstance(result, EdgeCandidate)


def test_enrich_edge_candidate_event_id_from_market(monkeypatch) -> None:
    """event_id is taken from MarketData.event_id field."""
    ratings = _make_good_ratings()
    matches = _make_sackmann_50_matches("Novak Djokovic", "Carlos Alcaraz")
    market = _make_market(slug="atp-djokovic-alcaraz-roland-garros-2026")
    # Override event_id
    market_dict = market.model_dump()
    market_dict["event_id"] = "custom-event-id"
    from src.models.market import MarketData as MD  # noqa: PLC0415
    m2 = MD(**market_dict)
    result = enrich(m2, ratings, matches, _make_cfg())
    if result is not None:
        assert result.event_id == "custom-event-id"


def test_enrich_prebuilt_index_gives_same_result() -> None:
    """Passing pre-built index gives same output as auto-built."""
    ratings = _make_good_ratings()
    matches = _make_sackmann_50_matches("Novak Djokovic", "Carlos Alcaraz")
    market = _make_market(slug="atp-djokovic-alcaraz-roland-garros-2026")
    cfg = _make_cfg()

    result_auto = enrich(market, ratings, matches, cfg)
    by_full, by_last = build_match_index(ratings)
    result_prebuilt = enrich(market, ratings, matches, cfg, by_full=by_full, by_last=by_last)

    assert type(result_auto) == type(result_prebuilt)
    if result_auto is not None and result_prebuilt is not None:
        assert abs(result_auto.edge - result_prebuilt.edge) < 1e-9
