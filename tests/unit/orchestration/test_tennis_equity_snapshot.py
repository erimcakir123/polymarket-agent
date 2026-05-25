"""tennis_agent equity snapshot wiring (Stage 6 PLAN-TENNIS-001).

Verifies that:
  - run_one_cycle writes an equity snapshot after every heavy cycle (heartbeat
    for dashboard Total Equity chart continuity), with or without entries.
  - run_light_cycle writes an equity snapshot after every light cycle so the
    chart updates between heavy cycles too.
  - The snapshot JSONL row carries all keys the dashboard reader expects
    (bankroll/realized_pnl/unrealized_pnl/invested/open_positions). The
    peak_bankroll widget value is computed downstream from these rows.
  - tennis_factory wires the equity_logger to logs/session/ (mirror path —
    dashboard's `read_balance_from_session` reads from session/).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config.settings import AppConfig
from src.domain.prediction.feature_extractor import FeatureSnapshot
from src.infrastructure.data.tennis_ratings_store import PlayerRating, SurfaceRating
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.models.market import MarketData
from src.orchestration.tennis_agent import run_light_cycle, run_one_cycle
from src.orchestration.tennis_factory import TennisDeps
from src.strategy.entry.tennis_entry import EdgeCandidate

# Dashboard expects these keys on the last JSONL line (readers.py:read_balance_from_session)
_DASHBOARD_SCHEMA_KEYS = {
    "bankroll", "realized_pnl", "unrealized_pnl", "invested", "open_positions",
}


# ── Helpers (mirror test_tennis_agent_entry_wiring.py shape) ─────────────────


def _surface_rating() -> SurfaceRating:
    return SurfaceRating(rating=1500.0, rd=80.0, volatility=0.06)


def _player(pid: str, name: str) -> PlayerRating:
    sr = _surface_rating()
    return PlayerRating(
        player_id=pid, player_name=name, tour="atp", overall=sr,
        serve_clay=sr, serve_grass=sr, serve_hard=sr,
        return_clay=sr, return_grass=sr, return_hard=sr,
        last_match_date="2026-01-01", singles_main_count_12mo=60,
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


def _make_deps(
    tmp_path: Path,
    equity_path: Path,
    cfg: AppConfig | None = None,
) -> TennisDeps:
    """TennisDeps with a real EquityHistoryLogger writing to a temp file."""
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
    exit_processor = MagicMock()
    # Test'in görebildiği gerçek EquityHistoryLogger — diske yazıyor.
    equity_logger = EquityHistoryLogger(str(equity_path))

    deps = TennisDeps(
        config=config,
        ratings_store=TennisRatingsStore(path=tmp_path / "ratings.json"),
        sackmann_client=SackmannCsvClient(cache_dir=tmp_path),
        diagnostic_logger=TennisDiagnosticLogger(log_dir=tmp_path / "logs"),
        state=state,
        entry_processor=entry_processor,
        exit_processor=exit_processor,
        equity_logger=equity_logger,
    )
    return deps


def _read_last_jsonl_line(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines, f"{path} is empty"
    return json.loads(lines[-1])


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_snapshot_written_after_heavy_cycle_with_entries(tmp_path: Path) -> None:
    """A-tier qualifying candidate → entry submitted + equity snapshot appended."""
    equity_path = tmp_path / "equity_history.jsonl"
    deps = _make_deps(tmp_path, equity_path)
    ratings = {"p1": _player("p1", "Player One"), "p2": _player("p2", "Player Two")}
    parsed_info = {
        "p1_name": "Player One", "p2_name": "Player Two",
        "market_type": "first_set_winner", "surface": "clay", "tour": "atp",
    }

    with patch("src.orchestration.tennis_agent.MarketScanner") as MockScanner, \
         patch("src.orchestration.tennis_agent.enrich", return_value=_candidate(edge=0.20)), \
         patch("src.orchestration.tennis_agent.classify_tier", return_value="A"), \
         patch("src.orchestration.tennis_agent.extract_features", return_value=_features()), \
         patch("src.orchestration.tennis_agent.match_player", return_value=ratings["p1"]), \
         patch("src.orchestration.tennis_agent.parse_tennis_question", return_value=parsed_info):
        MockScanner.return_value.scan.return_value = [_market()]
        run_one_cycle(deps, ratings=ratings, sackmann_matches=[])

    assert equity_path.exists(), "Heavy cycle with entries must write equity snapshot"
    snap = _read_last_jsonl_line(equity_path)
    assert _DASHBOARD_SCHEMA_KEYS.issubset(snap.keys())


def test_snapshot_written_after_heavy_cycle_no_entries(tmp_path: Path) -> None:
    """No qualifying candidate (tier=skip) → still write heartbeat snapshot.

    Dashboard Total Equity chart needs continuous samples so the line keeps
    advancing even on idle cycles (matches main bot's run_heavy behaviour:
    equity snapshot fires regardless of entry count).
    """
    equity_path = tmp_path / "equity_history.jsonl"
    deps = _make_deps(tmp_path, equity_path)
    ratings = {"p1": _player("p1", "Player One"), "p2": _player("p2", "Player Two")}
    parsed_info = {
        "p1_name": "Player One", "p2_name": "Player Two",
        "market_type": "first_set_winner", "surface": "clay", "tour": "atp",
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
    assert equity_path.exists(), "Heavy heartbeat snapshot must be written even with no entries"
    snap = _read_last_jsonl_line(equity_path)
    assert _DASHBOARD_SCHEMA_KEYS.issubset(snap.keys())


def test_snapshot_written_after_light_cycle(tmp_path: Path) -> None:
    """Light cycle persists portfolio state + writes equity snapshot heartbeat.

    Dashboard polls equity_history every few seconds; light cycle (60s) must
    advance the chart between heavy cycles (30min) so unrealized_pnl ticks
    are visible without waiting for the next heavy.
    """
    equity_path = tmp_path / "equity_history.jsonl"
    deps = _make_deps(tmp_path, equity_path)

    # exit_processor.run_light is mocked — light cycle should still write snapshot.
    run_light_cycle(deps, data_dir=tmp_path)

    assert equity_path.exists(), "Light cycle must write equity snapshot"
    snap = _read_last_jsonl_line(equity_path)
    assert _DASHBOARD_SCHEMA_KEYS.issubset(snap.keys())


def test_snapshot_fields_match_dashboard_schema(tmp_path: Path) -> None:
    """Snapshot row has all keys the dashboard balance reader expects.

    readers.read_balance_from_session(logs_dir) iterates the JSONL tail and
    looks up these fields directly. Missing keys would degrade the Balance /
    Open P&L / Realized P&L / Total Equity widgets silently.
    """
    equity_path = tmp_path / "equity_history.jsonl"
    deps = _make_deps(tmp_path, equity_path)

    run_light_cycle(deps, data_dir=tmp_path)

    snap = _read_last_jsonl_line(equity_path)
    for key in _DASHBOARD_SCHEMA_KEYS:
        assert key in snap, f"snapshot missing dashboard-required key: {key}"
    # timestamp also required (chart x-axis)
    assert "timestamp" in snap
    # Types
    assert isinstance(snap["bankroll"], (int, float))
    assert isinstance(snap["realized_pnl"], (int, float))
    assert isinstance(snap["unrealized_pnl"], (int, float))
    assert isinstance(snap["invested"], (int, float))
    assert isinstance(snap["open_positions"], int)


def test_factory_wires_equity_logger_to_session_path(tmp_path: Path) -> None:
    """tennis_factory builds equity_logger writing to logs/session/ mirror.

    Dashboard `read_balance_from_session` reads ONLY from
    `logs/session/equity_history.jsonl`. If the factory writes to a different
    path, the dashboard widgets stay empty even though snapshots are produced.
    """
    from src.orchestration.tennis_factory import build_tennis_deps  # noqa: PLC0415

    config_path = Path(__file__).resolve().parents[3] / "config_tennis.yaml"
    if not config_path.exists():
        # Test environment without config — skip rather than fail.
        import pytest  # noqa: PLC0415
        pytest.skip(f"config_tennis.yaml not at {config_path}")

    logs_dir = tmp_path / "logs"
    data_dir = tmp_path / "data"
    deps = build_tennis_deps(
        config_path=config_path,
        data_dir=data_dir,
        logs_dir=logs_dir,
    )

    # Equity logger primary path must be inside session/ (or mirror to it).
    primary = Path(deps.equity_logger.path)
    mirror = deps.equity_logger.mirror
    session_target = logs_dir / "session" / "equity_history.jsonl"
    assert primary == session_target or mirror == session_target, (
        f"equity_logger writes to {primary} (mirror={mirror}); "
        f"dashboard reads from {session_target}"
    )
