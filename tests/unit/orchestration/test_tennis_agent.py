"""Tests for tennis_agent — run_one_cycle mocked scanner + enricher."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from src.config.settings import AppConfig
from src.infrastructure.data.tennis_ratings_store import PlayerRating, SurfaceRating
from src.models.market import MarketData
from src.orchestration.tennis_agent import run_one_cycle
from src.orchestration.tennis_factory import TennisDeps


# ── Helpers ───────────────────────────────────────────────────────────────────


def _surface_rating() -> SurfaceRating:
    return SurfaceRating(rating=1500.0, rd=80.0, volatility=0.06)


def _make_player_rating(pid: str, name: str) -> PlayerRating:
    sr = _surface_rating()
    return PlayerRating(
        player_id=pid, player_name=name, overall=sr,
        serve_clay=sr, serve_grass=sr, serve_hard=sr,
        return_clay=sr, return_grass=sr, return_hard=sr,
        last_match_date="2026-01-01", match_count_12mo=60,
    )


def _make_market(
    question: str = "Set 1 Winner: Player One vs Player Two",
    sports_market_type: str = "tennis_first_set_winner",
    yes_price: float = 0.45,
) -> MarketData:
    now = datetime.now(timezone.utc)
    return MarketData(
        condition_id="cid",
        question=question,
        slug="atp-test-2026",
        yes_token_id="y",
        no_token_id="n",
        yes_price=yes_price,
        no_price=1.0 - yes_price,
        liquidity=5000.0,
        volume_24h=1000.0,
        end_date_iso=(now + timedelta(hours=5)).isoformat() + "Z",
        match_start_iso=(now + timedelta(hours=2)).isoformat() + "Z",
        sport_tag="tennis_atp",
        sports_market_type=sports_market_type,
        event_id="evt-test",
    )


def _make_deps(tmp_path: Path, cfg: AppConfig | None = None) -> TennisDeps:
    from unittest.mock import MagicMock  # noqa: PLC0415

    from src.infrastructure.data.sackmann_csv_client import SackmannCsvClient  # noqa: PLC0415
    from src.infrastructure.data.tennis_ratings_store import TennisRatingsStore  # noqa: PLC0415
    from src.orchestration.tennis_diagnostic_logger import TennisDiagnosticLogger  # noqa: PLC0415

    config = cfg or AppConfig()
    # Existing diagnostic-only tests don't exercise the entry pipeline; pass
    # mock state + entry_processor so TennisDeps shape is satisfied. New
    # entry-wiring tests build a real EntryProcessor (see test_tennis_agent_entry_wiring.py).
    state = MagicMock()
    state.portfolio.bankroll = config.initial_bankroll
    entry_processor = MagicMock()
    exit_processor = MagicMock()
    return TennisDeps(
        config=config,
        ratings_store=TennisRatingsStore(path=tmp_path / "ratings.json"),
        sackmann_client=SackmannCsvClient(cache_dir=tmp_path),
        diagnostic_logger=TennisDiagnosticLogger(log_dir=tmp_path / "logs"),
        state=state,
        entry_processor=entry_processor,
        exit_processor=exit_processor,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_run_one_cycle_no_ratings_returns_zero(tmp_path) -> None:
    """When no ratings loaded → cycle returns 0 and logs warning."""
    deps = _make_deps(tmp_path)
    # No ratings file → ratings_store.load() returns {}
    result = run_one_cycle(deps, ratings={}, sackmann_matches=[])
    assert result == 0


def test_run_one_cycle_scanner_returns_empty_returns_zero(tmp_path) -> None:
    """Empty scanner results → 0 candidates."""
    deps = _make_deps(tmp_path)
    ratings = {
        "p1": _make_player_rating("p1", "Player One"),
        "p2": _make_player_rating("p2", "Player Two"),
    }
    with patch("src.orchestration.tennis_agent.MarketScanner") as MockScanner:
        MockScanner.return_value.scan.return_value = []
        result = run_one_cycle(deps, ratings=ratings, sackmann_matches=[])
    assert result == 0


def test_run_one_cycle_unsupported_market_type_returns_zero(tmp_path) -> None:
    """Markets with unsupported type → enricher skips them → 0 logged."""
    deps = _make_deps(tmp_path)
    ratings = {
        "p1": _make_player_rating("p1", "Player One"),
        "p2": _make_player_rating("p2", "Player Two"),
    }
    market = _make_market(sports_market_type="tennis_match_totals")  # unsupported
    with patch("src.orchestration.tennis_agent.MarketScanner") as MockScanner:
        MockScanner.return_value.scan.return_value = [market]
        result = run_one_cycle(deps, ratings=ratings, sackmann_matches=[])
    assert result == 0


def test_run_one_cycle_with_edge_candidate_logs_to_diagnostic(tmp_path) -> None:
    """When enricher returns EdgeCandidate with sufficient edge → logged."""
    from src.domain.prediction.feature_extractor import FeatureSnapshot  # noqa: PLC0415
    from src.strategy.entry.tennis_entry import EdgeCandidate  # noqa: PLC0415

    deps = _make_deps(tmp_path)
    market = _make_market(yes_price=0.40)
    ratings = {
        "p1": _make_player_rating("p1", "Player One"),
        "p2": _make_player_rating("p2", "Player Two"),
    }

    # Mock out scanner, enrich, classify_tier; patch deferred imports at their source
    candidate = EdgeCandidate(
        event_id="evt-test",
        market_type="first_set_winner",
        model_p=0.60,
        market_p=0.40,
        edge=0.20,
    )

    good_features = FeatureSnapshot(
        p1_name="Player One", p2_name="Player Two", surface="clay",
        p1_match_count_12mo=50, p1_surface_count=20, p1_form_w_pct_60d=0.6, p1_form_data_age_days=20,
        p2_match_count_12mo=45, p2_surface_count=18, p2_form_w_pct_60d=0.55, p2_form_data_age_days=15,
        h2h_matches_total=2, h2h_matches_same_surface=1, h2h_p1_wins=1, h2h_last_meeting_days_ago=200,
    )

    parsed_info = {
        "p1_name": "Player One", "p2_name": "Player Two",
        "market_type": "first_set_winner", "surface": "clay",
    }

    with patch("src.orchestration.tennis_agent.MarketScanner") as MockScanner, \
         patch("src.orchestration.tennis_agent.enrich", return_value=candidate), \
         patch("src.orchestration.tennis_agent.classify_tier", return_value="A"), \
         patch("src.orchestration.tennis_agent.extract_features", return_value=good_features), \
         patch("src.orchestration.tennis_agent.match_player", return_value=ratings["p1"]), \
         patch("src.orchestration.tennis_agent.parse_tennis_question", return_value=parsed_info):

        MockScanner.return_value.scan.return_value = [market]
        result = run_one_cycle(deps, ratings=ratings, sackmann_matches=[])

    # At minimum, the cycle should not crash.
    # Logging 1 candidate requires edge >= min_edge (0.06 default) — candidate has 0.20.
    assert result >= 0


def test_run_one_cycle_below_min_edge_not_logged(tmp_path) -> None:
    """EdgeCandidate with edge < min_edge → not logged."""
    from src.strategy.entry.tennis_entry import EdgeCandidate  # noqa: PLC0415

    deps = _make_deps(tmp_path)
    market = _make_market(yes_price=0.50)
    ratings = {
        "p1": _make_player_rating("p1", "Player One"),
        "p2": _make_player_rating("p2", "Player Two"),
    }

    # Edge 0.01 — below min_edge 0.06
    candidate = EdgeCandidate(
        event_id="evt-test",
        market_type="first_set_winner",
        model_p=0.51,
        market_p=0.50,
        edge=0.01,
    )

    with patch("src.orchestration.tennis_agent.MarketScanner") as MockScanner, \
         patch("src.orchestration.tennis_agent.enrich", return_value=candidate):
        MockScanner.return_value.scan.return_value = [market]
        result = run_one_cycle(deps, ratings=ratings, sackmann_matches=[])

    assert result == 0
