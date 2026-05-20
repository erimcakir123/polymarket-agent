"""Tennis heavy + light cycle ORDER integration testleri (Stage 8 PLAN-TENNIS-001).

Stages 4-7 her bir parçanın bağlandığını ayrı ayrı doğruladı (entry wiring,
exit wiring, equity snapshot). Stage 8 bunların tamamının end-to-end DOĞRU
SIRADA çalıştığını assert eder — özellikle:

HEAVY (run_one_cycle):
  1. MarketScanner.scan()      — markets list
  2. enrich (her market için)  — EdgeCandidate'lar
  3. (select_best_2 + min_edge filtresi: domain, doğrudan mock'lanmıyor)
  4. EntryProcessor.process_signals(markets, signals)   [skip if 0 qualified]
  5. persist(state)                                      [skip if 0 qualified]
  6. operational_writers.log_equity_snapshot(...)        [heartbeat, her zaman]

LIGHT (run_light_cycle):
  1. ExitProcessor.run_light(score_map=None)
  2. persist(state)
  3. operational_writers.log_equity_snapshot(...)
  4. bot_status.json yazılır (stage="light")

Mock'lar `Mock.mock_calls` üzerinden zaman damgalı sıraya sahip — sıralama
indeks kıyaslamasıyla doğrulanır.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config.settings import AppConfig
from src.domain.guards.blacklist import Blacklist
from src.domain.portfolio.manager import PortfolioManager
from src.domain.prediction.feature_extractor import FeatureSnapshot
from src.domain.risk.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from src.infrastructure.data.sackmann_csv_client import SackmannCsvClient
from src.infrastructure.data.tennis_ratings_store import (
    PlayerRating,
    SurfaceRating,
    TennisRatingsStore,
)
from src.infrastructure.persistence.json_store import JsonStore
from src.models.market import MarketData
from src.orchestration.startup import RuntimeState
from src.orchestration.tennis_agent import run_light_cycle, run_one_cycle
from src.orchestration.tennis_diagnostic_logger import TennisDiagnosticLogger
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


def _parsed() -> dict:
    return {
        "p1_name": "Player One", "p2_name": "Player Two",
        "market_type": "first_set_winner", "surface": "clay",
    }


def _make_deps(tmp_path: Path) -> TennisDeps:
    """TennisDeps with real state + JsonStore + mocked processors/equity_logger.

    Mocking entry_processor / exit_processor / equity_logger lets us inspect
    call order on a single shared `recorder` MagicMock (see _wire_recorder).
    """
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


def _attach_recorder(*mocks: MagicMock) -> MagicMock:
    """Bütün mock çağrılarını tek bir 'recorder' altında zaman sıralı topla.

    Mock.mock_calls çağrılma sırasını korur; aynı mock parent altında attach
    edilen child mock'ların çağrıları parent.mock_calls içinde gözükür.
    """
    recorder = MagicMock(name="cycle_recorder")
    for i, m in enumerate(mocks):
        recorder.attach_mock(m, f"step_{i}")
    return recorder


def _names_in_order(recorder: MagicMock) -> list[str]:
    """Recorder'a kayıtlı çağrıları sıralı şekilde 'step_X.metod' isim listesine çevir."""
    return [c[0] for c in recorder.mock_calls]


# ── HEAVY cycle order ────────────────────────────────────────────────────────


def test_heavy_cycle_call_order(tmp_path: Path) -> None:
    """Heavy cycle: scanner → enrich → entry_processor → persist → equity_logger.

    Mock.attach_mock ile tüm bağımlı çağrılar tek recorder altında toplanır;
    sıralama indeks kıyaslamasıyla doğrulanır (eşitsizlik chain).
    """
    deps = _make_deps(tmp_path)
    ratings = {"p1": _player("p1", "Player One"), "p2": _player("p2", "Player Two")}

    scanner_instance = MagicMock(name="scanner_inst")
    scanner_instance.scan.return_value = [_market()]
    scanner_cls = MagicMock(return_value=scanner_instance)

    enrich_mock = MagicMock(return_value=_candidate(edge=0.20))
    persist_mock = MagicMock()
    snapshot_mock = MagicMock()

    recorder = _attach_recorder(
        scanner_cls,                         # step_0  → MarketScanner(...)
        scanner_instance,                    # step_1  → .scan()
        enrich_mock,                         # step_2  → enrich(...)
        deps.entry_processor,                # step_3  → .process_signals(...)
        persist_mock,                        # step_4  → persist(state)
        snapshot_mock,                       # step_5  → log_equity_snapshot(...)
    )

    with patch("src.orchestration.tennis_agent.MarketScanner", scanner_cls), \
         patch("src.orchestration.tennis_agent.enrich", enrich_mock), \
         patch("src.orchestration.tennis_agent.classify_tier", return_value="A"), \
         patch("src.orchestration.tennis_agent.extract_features", return_value=_features()), \
         patch("src.orchestration.tennis_agent.match_player", return_value=ratings["p1"]), \
         patch("src.orchestration.tennis_agent.parse_tennis_question", return_value=_parsed()), \
         patch("src.orchestration.tennis_agent.persist", persist_mock), \
         patch(
             "src.orchestration.tennis_agent.operational_writers.log_equity_snapshot",
             snapshot_mock,
         ):
        run_one_cycle(deps, ratings=ratings, sackmann_matches=[])

    names = _names_in_order(recorder)

    # Her zorunlu adım tetiklenmiş olmalı.
    def first_index(prefix: str) -> int:
        for i, n in enumerate(names):
            if n.startswith(prefix):
                return i
        raise AssertionError(f"step '{prefix}' kaydedilmedi; çağrı dizisi: {names}")

    idx_scanner_ctor = first_index("step_0")           # MarketScanner(...)
    idx_scan         = first_index("step_1.scan")      # scanner.scan()
    idx_enrich       = first_index("step_2")           # enrich(...)
    idx_entry        = first_index("step_3.process_signals")
    idx_persist      = first_index("step_4")
    idx_snapshot     = first_index("step_5")

    # 1 → 2 → 3 → 4 → 5 → 6 sıralaması
    assert idx_scanner_ctor < idx_scan < idx_enrich < idx_entry < idx_persist < idx_snapshot, (
        f"Heavy cycle adım sırası bozuk: {names}"
    )


def test_heavy_cycle_skip_entry_when_no_qualified(tmp_path: Path) -> None:
    """0 qualified candidate → process_signals + persist çağrılmaz; equity HEARTBEAT yazılır."""
    deps = _make_deps(tmp_path)
    ratings = {"p1": _player("p1", "Player One"), "p2": _player("p2", "Player Two")}

    scanner_instance = MagicMock()
    scanner_instance.scan.return_value = [_market()]
    scanner_cls = MagicMock(return_value=scanner_instance)

    persist_mock = MagicMock()
    snapshot_mock = MagicMock()

    with patch("src.orchestration.tennis_agent.MarketScanner", scanner_cls), \
         patch("src.orchestration.tennis_agent.enrich", return_value=_candidate(edge=0.20)), \
         patch("src.orchestration.tennis_agent.classify_tier", return_value="skip"), \
         patch("src.orchestration.tennis_agent.extract_features", return_value=_features()), \
         patch("src.orchestration.tennis_agent.match_player", return_value=ratings["p1"]), \
         patch("src.orchestration.tennis_agent.parse_tennis_question", return_value=_parsed()), \
         patch("src.orchestration.tennis_agent.persist", persist_mock), \
         patch(
             "src.orchestration.tennis_agent.operational_writers.log_equity_snapshot",
             snapshot_mock,
         ):
        run_one_cycle(deps, ratings=ratings, sackmann_matches=[])

    # tier="skip" → entry akışı atlanır
    deps.entry_processor.process_signals.assert_not_called()
    persist_mock.assert_not_called()
    # Heartbeat: snapshot HER ZAMAN yazılır (dashboard Total Equity chart sürekliliği)
    snapshot_mock.assert_called_once()


# ── LIGHT cycle order ────────────────────────────────────────────────────────


def test_light_cycle_call_order(tmp_path: Path) -> None:
    """Light cycle: exit_processor → persist → equity_logger → bot_status."""
    deps = _make_deps(tmp_path)

    persist_mock = MagicMock()
    snapshot_mock = MagicMock()
    status_mock = MagicMock()

    recorder = _attach_recorder(
        deps.exit_processor,   # step_0 → .run_light(score_map=None)
        persist_mock,          # step_1 → persist(state)
        snapshot_mock,         # step_2 → log_equity_snapshot(...)
        status_mock,           # step_3 → _write_status(...)
    )

    with patch("src.orchestration.tennis_agent.persist", persist_mock), \
         patch(
             "src.orchestration.tennis_agent.operational_writers.log_equity_snapshot",
             snapshot_mock,
         ), \
         patch("src.orchestration.tennis_agent._write_status", status_mock):
        run_light_cycle(deps, data_dir=tmp_path)

    names = _names_in_order(recorder)

    def first_index(prefix: str) -> int:
        for i, n in enumerate(names):
            if n.startswith(prefix):
                return i
        raise AssertionError(f"step '{prefix}' kaydedilmedi; çağrı dizisi: {names}")

    idx_exit     = first_index("step_0.run_light")
    idx_persist  = first_index("step_1")
    idx_snapshot = first_index("step_2")
    idx_status   = first_index("step_3")

    assert idx_exit < idx_persist < idx_snapshot < idx_status, (
        f"Light cycle adım sırası bozuk: {names}"
    )

    # bot_status'ın stage="light" parametresiyle çağrıldığını da bir kez doğrula
    assert status_mock.call_args.kwargs.get("stage") == "light"


def test_light_cycle_persist_called_when_no_exits(tmp_path: Path) -> None:
    """0 exit → persist + equity_logger yine de çağrılır (tick heartbeat).

    exit_processor.run_light hiçbir pozisyon kapatmasa bile light cycle:
      - persist: tick alanları (current_price, peak, consecutive_down_cycles) diske yazılmalı
      - equity_logger: dashboard chart 60sn'de bir ilerlemeli
    """
    deps = _make_deps(tmp_path)
    # exit_processor mock — default return_value = MagicMock() (no exits)

    with patch("src.orchestration.tennis_agent.persist") as persist_mock, \
         patch(
             "src.orchestration.tennis_agent.operational_writers.log_equity_snapshot",
         ) as snapshot_mock:
        run_light_cycle(deps, data_dir=tmp_path)

    deps.exit_processor.run_light.assert_called_once_with(score_map=None)
    persist_mock.assert_called_once_with(deps.state)
    snapshot_mock.assert_called_once()

    # bot_status.json gerçekten diske yazıldı mı?
    status_file = tmp_path / "bot_status.json"
    assert status_file.exists()
    payload = json.loads(status_file.read_text(encoding="utf-8"))
    assert payload["stage"] == "light"
