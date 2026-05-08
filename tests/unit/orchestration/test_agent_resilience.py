"""Cycle hata sınıflandırma + 2-strike stop politikası testleri."""
from __future__ import annotations

from src.orchestration._agent_resilience import (
    CycleResilience,
    is_programmatic_error,
)


def test_programmatic_errors_classified_correctly() -> None:
    assert is_programmatic_error(TypeError("x"))
    assert is_programmatic_error(AttributeError("x"))
    assert is_programmatic_error(ValueError("x"))
    assert is_programmatic_error(KeyError("x"))
    assert is_programmatic_error(AssertionError("x"))


def test_network_errors_not_programmatic() -> None:
    assert not is_programmatic_error(TimeoutError("x"))
    assert not is_programmatic_error(ConnectionError("x"))
    assert not is_programmatic_error(OSError("x"))


def test_first_programmatic_error_does_not_trigger_stop() -> None:
    r = CycleResilience(max_consecutive=2)
    r.record_error(TypeError("first"))
    assert r.should_stop() is False


def test_two_consecutive_same_type_triggers_stop() -> None:
    r = CycleResilience(max_consecutive=2)
    r.record_error(TypeError("first"))
    r.record_error(TypeError("second"))
    assert r.should_stop() is True


def test_success_resets_counter() -> None:
    r = CycleResilience(max_consecutive=2)
    r.record_error(TypeError("first"))
    r.record_success()
    r.record_error(TypeError("third"))
    assert r.should_stop() is False  # Counter resetlendi


def test_different_error_types_each_get_own_count() -> None:
    r = CycleResilience(max_consecutive=2)
    r.record_error(TypeError("a"))
    r.record_error(AttributeError("b"))  # Farklı tip
    assert r.should_stop() is False
    r.record_error(AttributeError("c"))  # AttrErr 2 ardışık
    assert r.should_stop() is True


def test_consecutive_count_property_exposes_internal_count() -> None:
    r = CycleResilience(max_consecutive=2)
    assert r.consecutive_count == 0
    r.record_error(TypeError("x"))
    assert r.consecutive_count == 1
    r.record_error(TypeError("y"))
    assert r.consecutive_count == 2
    r.record_success()
    assert r.consecutive_count == 0


from unittest.mock import MagicMock


def _build_minimal_deps() -> MagicMock:
    """Cycle test için mock'lu minimal deps (plain MagicMock — spec yok)."""
    deps = MagicMock()
    deps.cycle_manager.tick.return_value = MagicMock(
        run_heavy=True, run_light=False, reason="heavy"
    )
    deps.cycle_manager.sleep_seconds.return_value = 0.0
    deps.state.portfolio.count.return_value = 0
    deps.state.config.mode.value = "paper"
    deps.state.config.agent.cycle_max_consecutive_errors = 2
    deps.price_feed = None
    deps.command_poller = None
    return deps


def test_two_consecutive_typeerror_stops_agent() -> None:
    from src.orchestration.agent import Agent

    deps = _build_minimal_deps()
    agent = Agent(deps)  # type: ignore[arg-type]
    # Mock entry'yi 2 kez TypeError fırlatacak şekilde
    agent._entry = MagicMock()
    agent._entry.run_heavy = MagicMock(side_effect=TypeError("test bug"))
    agent._exit = MagicMock()

    # 5 tick izin ver — 2 ardışık hata sonrası stop bekleniyor
    agent.run(max_ticks=5)

    # 3. tick'e gelmeden stop_requested olmalı
    assert agent._stop_requested is True
    # entry.run_heavy 2 kez çağrılmış olmalı (3. tick'e gelmeden stop)
    assert agent._entry.run_heavy.call_count == 2
