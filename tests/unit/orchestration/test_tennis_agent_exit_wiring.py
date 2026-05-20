"""tennis_agent.run_light_cycle + run_forever exit wiring (Stage 5 PLAN-TENNIS-001).

Verifies that:
  - run_light_cycle delegates to deps.exit_processor.run_light(score_map=None)
  - run_light_cycle persists state after exit evaluation
  - run_light_cycle writes bot_status.json with stage="light"
  - run_forever schedules heavy + light cycles on independent intervals

All processors are mocked — we test the wiring + scheduling, not the
exit guards themselves.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config.settings import AppConfig
from src.orchestration.tennis_agent import run_forever, run_light_cycle
from src.orchestration.tennis_factory import TennisDeps


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_deps(tmp_path: Path) -> TennisDeps:
    """Minimal TennisDeps with mocked entry/exit processors and a real state.

    state.config.mode.value is consumed by _write_status; rest of state is unused
    by run_light_cycle directly (exit_processor mock owns position iteration).
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

    config = AppConfig()
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
    return TennisDeps(
        config=config,
        ratings_store=TennisRatingsStore(path=tmp_path / "ratings.json"),
        sackmann_client=SackmannCsvClient(cache_dir=tmp_path),
        diagnostic_logger=TennisDiagnosticLogger(log_dir=tmp_path / "logs"),
        state=state,
        entry_processor=MagicMock(),
        exit_processor=MagicMock(),
        equity_logger=MagicMock(),
    )


# ── run_light_cycle tests ─────────────────────────────────────────────────────


def test_run_light_cycle_calls_exit_processor(tmp_path: Path) -> None:
    """run_light_cycle → exit_processor.run_light(score_map=None) called once."""
    deps = _make_deps(tmp_path)
    run_light_cycle(deps, data_dir=tmp_path)
    deps.exit_processor.run_light.assert_called_once_with(score_map=None)


def test_run_light_cycle_calls_persist(tmp_path: Path) -> None:
    """run_light_cycle → persist(state) called (positions.json reflects exits)."""
    deps = _make_deps(tmp_path)
    with patch("src.orchestration.tennis_agent.persist") as mock_persist:
        run_light_cycle(deps, data_dir=tmp_path)
    mock_persist.assert_called_once_with(deps.state)


def test_run_light_cycle_updates_bot_status_to_light(tmp_path: Path) -> None:
    """run_light_cycle → bot_status.json yazılır, stage='light'."""
    deps = _make_deps(tmp_path)
    status_file = tmp_path / "bot_status.json"
    assert not status_file.exists()
    run_light_cycle(deps, data_dir=tmp_path)
    assert status_file.exists()
    payload = json.loads(status_file.read_text(encoding="utf-8"))
    assert payload["stage"] == "light"
    assert payload["cycle"] == "light"
    assert payload["mode"] == deps.config.mode.value


def test_light_cycle_logs_periodically(tmp_path: Path, caplog) -> None:
    """FIX 4: her 10. tick'te 'Light cycle tick #N' INFO log atılır.

    10 çağrı → tam 1 log message; counter modulo'su 10. tick'te tetikler.
    State module-level olduğu için testler arasında sıfırlanır.
    """
    import logging
    from src.orchestration import tennis_agent
    tennis_agent._light_tick_state["count"] = 0  # test izolasyonu
    deps = _make_deps(tmp_path)
    with caplog.at_level(logging.INFO, logger="src.orchestration.tennis_agent"):
        for _ in range(10):
            run_light_cycle(deps, data_dir=tmp_path)
    tick_logs = [r for r in caplog.records if "Light cycle tick" in r.message]
    assert len(tick_logs) == 1, f"expected 1 throttled tick log after 10 calls, got {len(tick_logs)}"
    assert "tick #10" in tick_logs[0].message


# ── run_forever scheduling test ───────────────────────────────────────────────


def test_heavy_and_light_intervals_independent(tmp_path: Path) -> None:
    """run_forever heavy + light cycles bağımsız interval'larda tetiklenir.

    Simulated clock: 305 sn akış, heavy=300, light=60 → heavy ≈ 2 kez
    (t=0 ve t=300), light ≈ 6 kez (t=0, 60, 120, 180, 240, 300).
    StopIteration time.sleep'i durdurarak loop'tan çıkar.
    """
    deps = _make_deps(tmp_path)
    # Time akışı: monotonic() çağrılarına artan değerler döner.
    # Heavy interval=300, light=60 → toplam ~305 sn boyunca her sn bir tick.
    clock = [0.0]
    SIM_END = 305.0

    def fake_monotonic() -> float:
        return clock[0]

    def fake_sleep(sec: float) -> None:
        clock[0] += sec
        if clock[0] > SIM_END:
            raise StopIteration("simulation end")

    with patch("src.orchestration.tennis_agent.time.monotonic", side_effect=fake_monotonic), \
         patch("src.orchestration.tennis_agent.time.sleep", side_effect=fake_sleep), \
         patch("src.orchestration.tennis_agent.run_one_cycle", return_value=0) as mock_heavy, \
         patch("src.orchestration.tennis_agent._write_pid"):
        try:
            run_forever(
                deps,
                interval_sec=300,
                logs_dir=tmp_path,
                data_dir=tmp_path,
                light_interval_sec=60,
            )
        except StopIteration:
            pass

    # Heavy: t=0 (initial) + t=300 → 2 çağrı.
    assert mock_heavy.call_count == 2, f"expected 2 heavy, got {mock_heavy.call_count}"
    # Light: t=0, 60, 120, 180, 240, 300 → 6 çağrı.
    assert deps.exit_processor.run_light.call_count == 6, (
        f"expected 6 light, got {deps.exit_processor.run_light.call_count}"
    )
