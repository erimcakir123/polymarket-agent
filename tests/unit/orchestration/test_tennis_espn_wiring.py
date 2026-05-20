"""ESPN ScoreEnricher → tennis_agent wiring (2026-05-20 tennis-lab).

build_tennis_deps `TennisDeps.score_enricher` üzerinde ESPNClient ile sarmalı
bir ScoreEnricher kurar; run_light_cycle bu enricher'ı çağırıp dönen
score_map'i ExitProcessor.run_light'a iletir. ESPN istisna fırlatırsa boş map
fallback olur (None ASLA iletilmez).

Tennis ESPN parser ayrıca:
  - Live competition'tan athlete adları + linescore-based sets won çıkartır
  - Pre-match competition'da 0 set, is_live=False döner
  - Final competition'da is_completed=True, period="Final" döner
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.config.settings import AppConfig
from src.infrastructure.apis.espn_client import ESPNClient
from src.orchestration.score_enricher import ScoreEnricher
from src.orchestration.tennis_agent import _fetch_tennis_score_map, run_light_cycle
from src.orchestration.tennis_factory import TennisDeps, build_tennis_deps


# ── Helpers ──────────────────────────────────────────────────────────────────


def _live_tennis_event(
    *,
    home_name: str = "Sinner",
    away_name: str = "Alcaraz",
    home_sets: int = 1,
    away_sets: int = 0,
    period: int = 2,
) -> dict:
    """ESPN tenis response fragment'i (tournament wrapper + tek live match)."""
    def _linescores(winning_sets: int, total_played: int) -> list[dict]:
        out = []
        for i in range(total_played):
            out.append({"value": 6.0, "winner": i < winning_sets})
        return out

    total = max(period - 1, max(home_sets, away_sets))
    return {
        "id": "T1",
        "date": "2026-05-20T10:00Z",
        "groupings": [
            {
                "competitions": [
                    {
                        "id": "M1",
                        "date": "2026-05-20T12:00Z",
                        "status": {
                            "period": period,
                            "type": {"state": "in", "name": f"Set {period}", "completed": False},
                        },
                        "competitors": [
                            {
                                "homeAway": "home",
                                "athlete": {"id": "p1", "displayName": home_name},
                                "linescores": _linescores(home_sets, total),
                            },
                            {
                                "homeAway": "away",
                                "athlete": {"id": "p2", "displayName": away_name},
                                "linescores": _linescores(away_sets, total),
                            },
                        ],
                    },
                ],
            },
        ],
    }


def _final_tennis_event() -> dict:
    return {
        "id": "T2",
        "date": "2026-05-19T10:00Z",
        "groupings": [
            {
                "competitions": [
                    {
                        "id": "M2",
                        "date": "2026-05-19T11:00Z",
                        "status": {
                            "period": 3,
                            "type": {"state": "post", "name": "STATUS_FINAL", "completed": True},
                        },
                        "competitors": [
                            {
                                "homeAway": "home",
                                "athlete": {"id": "p3", "displayName": "Djokovic"},
                                "linescores": [
                                    {"value": 6.0, "winner": True},
                                    {"value": 4.0, "winner": False},
                                    {"value": 7.0, "winner": True},
                                ],
                            },
                            {
                                "homeAway": "away",
                                "athlete": {"id": "p4", "displayName": "Medvedev"},
                                "linescores": [
                                    {"value": 4.0, "winner": False},
                                    {"value": 6.0, "winner": True},
                                    {"value": 5.0, "winner": False},
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    }


def _pre_match_tennis_event() -> dict:
    return {
        "id": "T3",
        "date": "2026-05-22T10:00Z",
        "groupings": [
            {
                "competitions": [
                    {
                        "id": "M3",
                        "date": "2026-05-22T14:00Z",
                        "status": {
                            "period": 0,
                            "type": {"state": "pre", "name": "STATUS_SCHEDULED", "completed": False},
                        },
                        "competitors": [
                            {"homeAway": "home", "athlete": {"id": "p5", "displayName": "Rune"}, "linescores": []},
                            {"homeAway": "away", "athlete": {"id": "p6", "displayName": "Ruud"}, "linescores": []},
                        ],
                    },
                ],
            },
        ],
    }


def _fake_http(payload: dict):
    """ESPNClient http_get callable mock — payload'ı JSON olarak döndüren response."""
    def _get(_url, params=None, timeout=None):  # noqa: ARG001
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = payload
        return resp
    return _get


def _make_min_deps(tmp_path: Path) -> TennisDeps:
    """Minimal TennisDeps with mocked processors — score_enricher overridden per test."""
    from src.domain.guards.blacklist import Blacklist
    from src.domain.portfolio.manager import PortfolioManager
    from src.domain.risk.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
    from src.infrastructure.data.sackmann_csv_client import SackmannCsvClient
    from src.infrastructure.data.tennis_ratings_store import TennisRatingsStore
    from src.infrastructure.persistence.json_store import JsonStore
    from src.orchestration.startup import RuntimeState
    from src.orchestration.tennis_diagnostic_logger import TennisDiagnosticLogger

    config = AppConfig()
    portfolio = PortfolioManager(initial_bankroll=config.initial_bankroll)
    breaker = CircuitBreaker(config=CircuitBreakerConfig(enabled=False))
    state = RuntimeState(
        config=config, portfolio=portfolio, circuit_breaker=breaker, blacklist=Blacklist(),
        positions_store=JsonStore(tmp_path / "positions.json"),
        breaker_store=JsonStore(tmp_path / "breaker.json"),
        blacklist_store=JsonStore(tmp_path / "bl.json"),
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


# ── ESPN parser: tennis event → match-level ESPNMatchScore ───────────────────


def test_espn_parse_tennis_event_extracts_set_info() -> None:
    payload = {"events": [_live_tennis_event(home_sets=1, away_sets=0, period=2)]}
    espn = ESPNClient(http_get=_fake_http(payload))
    matches = espn.fetch_scoreboard("tennis", "atp")
    assert len(matches) == 1
    m = matches[0]
    assert m.event_id == "M1"
    assert m.home_name == "Sinner"
    assert m.away_name == "Alcaraz"
    assert m.home_score == 1
    assert m.away_score == 0
    assert m.period == "Set 2"
    assert m.period_number == 2
    assert m.is_live is True
    assert m.is_completed is False


def test_espn_parse_tennis_event_handles_pre_match() -> None:
    payload = {"events": [_pre_match_tennis_event()]}
    espn = ESPNClient(http_get=_fake_http(payload))
    matches = espn.fetch_scoreboard("tennis", "atp")
    assert len(matches) == 1
    m = matches[0]
    assert m.is_live is False
    assert m.is_completed is False
    assert m.home_score == 0  # boş linescores → 0 set
    assert m.away_score == 0


def test_espn_parse_tennis_event_handles_final() -> None:
    payload = {"events": [_final_tennis_event()]}
    espn = ESPNClient(http_get=_fake_http(payload))
    matches = espn.fetch_scoreboard("tennis", "atp")
    assert len(matches) == 1
    m = matches[0]
    assert m.is_completed is True
    assert m.is_live is False
    assert m.period == "Final"
    assert m.home_score == 2  # Djokovic: 2 winning sets (1, 3)
    assert m.away_score == 1  # Medvedev: 1 winning set (2)


# ── monitor._estimate_elapsed_from_score: tennis branch ──────────────────────


def test_estimate_elapsed_tennis_set_1_returns_0_3() -> None:
    from src.strategy.exit.monitor import _estimate_elapsed_from_score
    info = {"available": True, "period": "Set 1"}
    assert _estimate_elapsed_from_score("tennis_atp", info) == 0.3


def test_estimate_elapsed_tennis_set_2_returns_0_6() -> None:
    from src.strategy.exit.monitor import _estimate_elapsed_from_score
    info = {"available": True, "period": "Set 2"}
    assert _estimate_elapsed_from_score("tennis", info) == 0.6


def test_estimate_elapsed_tennis_set_3_returns_0_85() -> None:
    from src.strategy.exit.monitor import _estimate_elapsed_from_score
    info = {"available": True, "period": "Set 3"}
    assert _estimate_elapsed_from_score("tennis_wta", info) == 0.85


def test_estimate_elapsed_tennis_final_returns_1_0() -> None:
    from src.strategy.exit.monitor import _estimate_elapsed_from_score
    info = {"available": True, "period": "Final"}
    assert _estimate_elapsed_from_score("tennis", info) == 1.0


# ── tennis_factory wiring: TennisDeps.score_enricher hazır ───────────────────


def test_tennis_factory_builds_score_enricher(tmp_path: Path) -> None:
    """build_tennis_deps `score_enricher`'i wires (None değil, ScoreEnricher instance).

    config_tennis.yaml score.enabled=true → gerçek ESPN-backed enricher kurulur.
    Diğer alanları minimal config'le geçer (yaml var olmasa AppConfig default'ı).
    """
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "mode: dry_run\ninitial_bankroll: 100.0\nscore:\n  enabled: true\n",
        encoding="utf-8",
    )
    deps = build_tennis_deps(cfg_path, data_dir=tmp_path / "d", logs_dir=tmp_path / "l")
    assert deps.score_enricher is not None
    assert isinstance(deps.score_enricher, ScoreEnricher)


# ── run_light_cycle: score_map akışı ──────────────────────────────────────────


def test_run_light_cycle_passes_score_map_to_exit_processor(tmp_path: Path) -> None:
    """score_enricher ESPN map dönerse, run_light_cycle aynı map'i ExitProcessor'a iletir."""
    deps = _make_min_deps(tmp_path)
    expected_map = {"cid1": {"available": True, "our_score": 1, "opp_score": 0, "map_diff": 1, "deficit": 0, "period": "Set 2"}}
    enricher = MagicMock()
    enricher.get_scores_if_due.return_value = expected_map
    deps.score_enricher = enricher

    run_light_cycle(deps, data_dir=tmp_path)

    enricher.get_scores_if_due.assert_called_once_with(deps.state.portfolio.positions)
    deps.exit_processor.run_light.assert_called_once_with(score_map=expected_map)


def test_run_light_cycle_handles_espn_outage_passes_empty_map(tmp_path: Path) -> None:
    """ESPN istisna fırlatırsa run_light_cycle score_map={} ile devam eder, ASLA None geçmez."""
    deps = _make_min_deps(tmp_path)
    enricher = MagicMock()
    enricher.get_scores_if_due.side_effect = RuntimeError("ESPN down")
    deps.score_enricher = enricher

    run_light_cycle(deps, data_dir=tmp_path)

    deps.exit_processor.run_light.assert_called_once_with(score_map={})


def test_fetch_score_map_returns_empty_when_enricher_is_none(tmp_path: Path) -> None:
    """deps.score_enricher=None (test/legacy) → {} (None ASLA döndürülmez)."""
    deps = _make_min_deps(tmp_path)
    deps.score_enricher = None
    assert _fetch_tennis_score_map(deps) == {}
