"""tennis_agent.run_one_cycle entry wiring (Stage 4 PLAN-TENNIS-001).

Verifies that run_one_cycle:
  - calls entry_processor.process_signals when a qualifying A/B-tier candidate exists
  - skips entry for tier="skip" candidates
  - calls persist(state) after a successful entry pass

Uses heavy mocking of the enricher / classifier / feature extractor — we're
testing the wiring, not the prediction pipeline.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config.settings import AppConfig
from src.domain.prediction.feature_extractor import FeatureSnapshot
from src.infrastructure.data.tennis_ratings_store import PlayerRating, SurfaceRating
from src.models.market import MarketData
from src.orchestration.tennis_agent import run_one_cycle
from src.orchestration.tennis_factory import TennisDeps
from src.strategy.entry.tennis_entry import EdgeCandidate


# ── Helpers ───────────────────────────────────────────────────────────────────


def _surface_rating() -> SurfaceRating:
    return SurfaceRating(rating=1500.0, rd=80.0, volatility=0.06)


def _player(pid: str, name: str) -> PlayerRating:
    sr = _surface_rating()
    return PlayerRating(
        player_id=pid, player_name=name, overall=sr,
        serve_clay=sr, serve_grass=sr, serve_hard=sr,
        return_clay=sr, return_grass=sr, return_hard=sr,
        last_match_date="2026-01-01", match_count_12mo=60,
    )


def _market(cid: str = "0xTENNIS", yes_price: float = 0.45) -> MarketData:
    now = datetime.now(timezone.utc)
    return MarketData(
        condition_id=cid,
        question="Set 1 Winner: Player One vs Player Two",
        slug="atp-test-2026",
        yes_token_id="y", no_token_id="n",
        yes_price=yes_price, no_price=1.0 - yes_price,
        liquidity=20_000.0, volume_24h=5_000.0,
        end_date_iso=(now + timedelta(hours=5)).isoformat() + "Z",
        match_start_iso=(now + timedelta(hours=2)).isoformat() + "Z",
        sport_tag="tennis_atp",
        sports_market_type="tennis_first_set_winner",
        event_id="evt-tennis",
    )


def _features() -> FeatureSnapshot:
    return FeatureSnapshot(
        p1_name="Player One", p2_name="Player Two", surface="clay",
        p1_match_count_12mo=50, p1_surface_count=20,
        p1_form_w_pct_60d=0.6, p1_form_data_age_days=20,
        p2_match_count_12mo=45, p2_surface_count=18,
        p2_form_w_pct_60d=0.55, p2_form_data_age_days=15,
        h2h_matches_total=2, h2h_matches_same_surface=1,
        h2h_p1_wins=1, h2h_last_meeting_days_ago=200,
    )


def _candidate(edge: float = 0.20) -> EdgeCandidate:
    return EdgeCandidate(
        event_id="evt-tennis",
        market_type="first_set_winner",
        model_p=0.60,
        market_p=0.40,
        edge=edge,
    )


def _make_deps(tmp_path: Path, cfg: AppConfig | None = None) -> TennisDeps:
    """Build TennisDeps with a real-ish state/portfolio and a mocked entry_processor.

    We assert against entry_processor.process_signals call args.
    """
    from src.domain.guards.blacklist import Blacklist  # noqa: PLC0415
    from src.domain.portfolio.manager import PortfolioManager  # noqa: PLC0415
    from src.domain.risk.circuit_breaker import (  # noqa: PLC0415
        CircuitBreaker, CircuitBreakerConfig,
    )
    from src.infrastructure.data.sackmann_csv_client import SackmannCsvClient  # noqa: PLC0415
    from src.infrastructure.data.tennis_ratings_store import TennisRatingsStore  # noqa: PLC0415
    from src.infrastructure.persistence.json_store import JsonStore  # noqa: PLC0415
    from src.orchestration.startup import RuntimeState  # noqa: PLC0415
    from src.orchestration.tennis_diagnostic_logger import TennisDiagnosticLogger  # noqa: PLC0415

    config = cfg or AppConfig()
    portfolio = PortfolioManager(initial_bankroll=config.initial_bankroll)
    breaker = CircuitBreaker(config=CircuitBreakerConfig(enabled=False))
    blacklist = Blacklist()
    state = RuntimeState(
        config=config,
        portfolio=portfolio,
        circuit_breaker=breaker,
        blacklist=blacklist,
        positions_store=JsonStore(tmp_path / "positions.json"),
        breaker_store=JsonStore(tmp_path / "circuit_breaker_state.json"),
        blacklist_store=JsonStore(tmp_path / "blacklist.json"),
    )
    entry_processor = MagicMock()
    return TennisDeps(
        config=config,
        ratings_store=TennisRatingsStore(path=tmp_path / "ratings.json"),
        sackmann_client=SackmannCsvClient(cache_dir=tmp_path),
        diagnostic_logger=TennisDiagnosticLogger(log_dir=tmp_path / "logs"),
        state=state,
        entry_processor=entry_processor,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_tennis_cycle_submits_signal_for_qualified_a_tier(tmp_path: Path) -> None:
    """A-tier candidate above min_edge → entry_processor.process_signals called once."""
    deps = _make_deps(tmp_path)
    ratings = {"p1": _player("p1", "Player One"), "p2": _player("p2", "Player Two")}

    parsed_info = {
        "p1_name": "Player One", "p2_name": "Player Two",
        "market_type": "first_set_winner", "surface": "clay",
    }

    with patch("src.orchestration.tennis_agent.MarketScanner") as MockScanner, \
         patch("src.orchestration.tennis_agent.enrich", return_value=_candidate(edge=0.20)), \
         patch("src.orchestration.tennis_agent.classify_tier", return_value="A"), \
         patch("src.orchestration.tennis_agent.extract_features", return_value=_features()), \
         patch("src.orchestration.tennis_agent.match_player", return_value=ratings["p1"]), \
         patch("src.orchestration.tennis_agent.parse_tennis_question", return_value=parsed_info):
        MockScanner.return_value.scan.return_value = [_market()]
        run_one_cycle(deps, ratings=ratings, sackmann_matches=[])

    deps.entry_processor.process_signals.assert_called_once()
    markets_arg, signals_arg = deps.entry_processor.process_signals.call_args[0]
    assert len(markets_arg) == 1
    assert len(signals_arg) == 1
    signal = signals_arg[0]
    assert signal.entry_reason.value == "tennis"
    assert signal.confidence == "A"
    assert signal.size_usdc > 0


def test_tennis_cycle_skips_unqualified_tier(tmp_path: Path) -> None:
    """tier='skip' candidates → entry_processor.process_signals NOT called."""
    deps = _make_deps(tmp_path)
    ratings = {"p1": _player("p1", "Player One"), "p2": _player("p2", "Player Two")}

    parsed_info = {
        "p1_name": "Player One", "p2_name": "Player Two",
        "market_type": "first_set_winner", "surface": "clay",
    }

    with patch("src.orchestration.tennis_agent.MarketScanner") as MockScanner, \
         patch("src.orchestration.tennis_agent.enrich", return_value=_candidate(edge=0.20)), \
         patch("src.orchestration.tennis_agent.classify_tier", return_value="skip"), \
         patch("src.orchestration.tennis_agent.extract_features", return_value=_features()), \
         patch("src.orchestration.tennis_agent.match_player", return_value=ratings["p1"]), \
         patch("src.orchestration.tennis_agent.parse_tennis_question", return_value=parsed_info):
        MockScanner.return_value.scan.return_value = [_market()]
        run_one_cycle(deps, ratings=ratings, sackmann_matches=[])

    deps.entry_processor.process_signals.assert_not_called()


def test_tennis_cycle_calls_persist_after_entries(tmp_path: Path) -> None:
    """Successful entry pass → persist(state) called (positions.json written)."""
    deps = _make_deps(tmp_path)
    ratings = {"p1": _player("p1", "Player One"), "p2": _player("p2", "Player Two")}

    parsed_info = {
        "p1_name": "Player One", "p2_name": "Player Two",
        "market_type": "first_set_winner", "surface": "clay",
    }

    # Confirm positions.json doesn't exist yet
    assert not (tmp_path / "positions.json").exists()

    with patch("src.orchestration.tennis_agent.MarketScanner") as MockScanner, \
         patch("src.orchestration.tennis_agent.enrich", return_value=_candidate(edge=0.20)), \
         patch("src.orchestration.tennis_agent.classify_tier", return_value="A"), \
         patch("src.orchestration.tennis_agent.extract_features", return_value=_features()), \
         patch("src.orchestration.tennis_agent.match_player", return_value=ratings["p1"]), \
         patch("src.orchestration.tennis_agent.parse_tennis_question", return_value=parsed_info), \
         patch("src.orchestration.tennis_agent.persist") as mock_persist:
        MockScanner.return_value.scan.return_value = [_market()]
        run_one_cycle(deps, ratings=ratings, sackmann_matches=[])

    mock_persist.assert_called_once_with(deps.state)
