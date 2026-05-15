"""ExitProcessor score_map injection testi (SPEC-B Task 5)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.config.settings import AppConfig
from src.models.position import Position
from src.orchestration.exit_processor import ExitProcessor


def _make_deps_with_pos():
    deps = MagicMock()
    deps.state.config = AppConfig()
    pos = Position(
        condition_id="cid", token_id="t", direction="BUY_YES",
        entry_price=0.5, size_usdc=50, shares=100, current_price=0.6,
        anchor_probability=0.5, event_id="e1", slug="s",
        sport_tag="nhl", question="A vs B",
    )
    deps.state.portfolio.positions = {"cid": pos}
    return deps, pos


def test_run_light_passes_score_info_to_monitor(monkeypatch) -> None:
    """run_light score_map içindeki score_info'yu monitor.evaluate'a geçirir."""
    deps, pos = _make_deps_with_pos()
    score_map = {
        "cid": {
            "available": True, "our_score": 2, "opp_score": 1,
            "deficit": 0, "map_diff": 1, "period": "In Progress",
        },
    }

    captured = {}

    def fake_eval(p, score_info=None, **_kw):
        captured["score_info"] = score_info
        from src.strategy.exit.monitor import FavoredTransition, MonitorResult
        return MonitorResult(
            exit_signal=None,
            fav_transition=FavoredTransition(),
            elapsed_pct=0.5,
        )

    import src.strategy.exit.monitor as monitor_mod
    monkeypatch.setattr(monitor_mod, "evaluate", fake_eval)

    ep = ExitProcessor(deps)
    ep.run_light(score_map=score_map)
    assert captured["score_info"] == score_map["cid"]


def test_run_light_no_score_map_passes_empty_dict(monkeypatch) -> None:
    """score_map=None → monitor.evaluate score_info={} (mevcut davranış)."""
    deps, pos = _make_deps_with_pos()

    captured = {}

    def fake_eval(p, score_info=None, **_kw):
        captured["score_info"] = score_info
        from src.strategy.exit.monitor import FavoredTransition, MonitorResult
        return MonitorResult(
            exit_signal=None,
            fav_transition=FavoredTransition(),
            elapsed_pct=0.5,
        )

    import src.strategy.exit.monitor as monitor_mod
    monkeypatch.setattr(monitor_mod, "evaluate", fake_eval)

    ep = ExitProcessor(deps)
    ep.run_light(score_map=None)
    assert captured["score_info"] in (None, {})


def test_run_light_passes_basketball_exit_cfg_to_monitor(monkeypatch) -> None:
    """SPEC-J: AppConfig.exit_basketball monitor.evaluate'a iletilir."""
    from src.config.settings import BasketballExitConfig
    deps, pos = _make_deps_with_pos()
    custom_cfg = BasketballExitConfig(totals_multiplier=1.5)
    deps.state.config.exit_basketball = custom_cfg

    captured = {}

    def fake_eval(p, score_info=None, basketball_exit_cfg=None, **_kw):
        captured["basketball_exit_cfg"] = basketball_exit_cfg
        from src.strategy.exit.monitor import FavoredTransition, MonitorResult
        return MonitorResult(
            exit_signal=None,
            fav_transition=FavoredTransition(),
            elapsed_pct=0.5,
        )

    import src.strategy.exit.monitor as monitor_mod
    monkeypatch.setattr(monitor_mod, "evaluate", fake_eval)

    ep = ExitProcessor(deps)
    ep.run_light(score_map=None)
    assert captured["basketball_exit_cfg"] is custom_cfg
