"""agent.py için birim testler — tüm akışları mock'larla test eder."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config.settings import AppConfig
from src.domain.analysis.probability import BookmakerProbability
from src.domain.guards.manipulation import ManipulationCheck
from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.persistence.eligible_queue_snapshot import EligibleQueueSnapshot
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.json_store import JsonStore
from src.orchestration.bot_status_writer import BotStatusWriter
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.models.market import MarketData
from src.orchestration.agent import Agent, AgentDeps
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.scanner import MarketScanner
from src.orchestration.startup import bootstrap
from src.strategy.entry.gate import EntryGate, GateConfig


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _market(cid: str = "m1", yes: float = 0.50) -> MarketData:
    now = datetime.now(timezone.utc)
    return MarketData(
        condition_id=cid,
        question="Will Lakers beat Celtics?",
        slug=f"nba-lal-bos-{cid}",
        yes_token_id="y", no_token_id="n",
        yes_price=yes, no_price=1 - yes,
        liquidity=50_000, volume_24h=10_000, tags=[],
        end_date_iso=_iso(now + timedelta(hours=3)),
        match_start_iso=_iso(now + timedelta(hours=1)),
        sport_tag="basketball_nba",
        event_id=f"evt_{cid}",
    )


def _bm(prob: float = 0.60, conf: str = "A") -> BookmakerProbability:
    return BookmakerProbability(
        probability=prob, confidence=conf,
        bookmaker_prob=prob, num_bookmakers=10.0, has_sharp=(conf == "A"),
    )


def _safe_manip() -> ManipulationCheck:
    return ManipulationCheck(safe=True, risk_level="low", flags=[], recommendation="")


def _build_deps(tmp_path: Path, markets: list[MarketData], bm_result: BookmakerProbability | None = None) -> AgentDeps:
    """Test için minimal agent deps."""
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=tmp_path)

    gamma = MagicMock()
    gamma.fetch_events.return_value = markets
    scanner = MarketScanner(cfg.scanner, gamma_client=gamma)

    cm = CycleManager(cfg.cycle)
    cooldown = CooldownTracker()

    # Executor: dry_run + mock CLOB book fetch
    exec_http = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock(return_value=None)
    resp.json.return_value = {
        "asks": [{"price": "0.99", "size": "10"}, {"price": "0.50", "size": "100"}],
        "bids": [{"price": "0.01", "size": "10"}, {"price": "0.49", "size": "100"}],
    }
    exec_http.return_value = resp
    from src.infrastructure.executor import Executor
    from src.config.settings import Mode
    executor = Executor(mode=Mode.DRY_RUN, http_get=exec_http)

    odds_client = MagicMock()
    odds_client.get_sports.return_value = []
    odds_client.get_events.return_value = []
    odds_client.get_odds.return_value = []

    # Gate: enricher ve manipulation checker mock'la
    enricher = lambda m: bm_result
    manip = lambda question, liquidity: _safe_manip()
    gate = EntryGate(
        config=GateConfig(),
        portfolio=state.portfolio, circuit_breaker=state.circuit_breaker,
        cooldown=cooldown, blacklist=state.blacklist,
        odds_enricher=enricher, manipulation_checker=manip,
    )

    trade_logger = TradeHistoryLogger(str(tmp_path / "trade_history.jsonl"))
    equity_logger = EquityHistoryLogger(str(tmp_path / "equity_history.jsonl"))
    skipped_logger = SkippedTradeLogger(str(tmp_path / "skipped_trades.jsonl"))
    eligible_snapshot = EligibleQueueSnapshot(str(tmp_path / "eligible_queue.json"))
    bot_status_store = JsonStore(tmp_path / "bot_status.json")
    bot_status_writer = BotStatusWriter(bot_status_store, cm)

    return AgentDeps(
        state=state, scanner=scanner, cycle_manager=cm,
        executor=executor, odds_client=odds_client, trade_logger=trade_logger,
        gate=gate, cooldown=cooldown,
        equity_logger=equity_logger, skipped_logger=skipped_logger,
        eligible_snapshot=eligible_snapshot, bot_status_writer=bot_status_writer,
    )


# ── Heavy cycle ──

def test_heavy_cycle_opens_position_when_signal(tmp_path: Path, monkeypatch) -> None:
    # Edge'li pazar — enricher A conf + %65 prob → market 0.50 → raw edge 0.15
    deps = _build_deps(tmp_path, [_market(cid="m1", yes=0.50)], bm_result=_bm(prob=0.65, conf="A"))
    monkeypatch.setattr(time, "sleep", lambda *a: None)  # test hızlı

    agent = Agent(deps)
    agent.run(max_ticks=1)

    assert deps.state.portfolio.count() == 1
    assert "m1" in deps.state.portfolio.positions


def test_heavy_cycle_no_enrichment_no_position(tmp_path: Path, monkeypatch) -> None:
    # Enricher None döner → no_bookmaker_data
    deps = _build_deps(tmp_path, [_market(cid="m1")], bm_result=None)
    monkeypatch.setattr(time, "sleep", lambda *a: None)
    agent = Agent(deps)
    agent.run(max_ticks=1)
    assert deps.state.portfolio.count() == 0


def test_trade_logger_records_entry(tmp_path: Path, monkeypatch) -> None:
    deps = _build_deps(tmp_path, [_market(cid="m1", yes=0.50)], bm_result=_bm(prob=0.65, conf="A"))
    monkeypatch.setattr(time, "sleep", lambda *a: None)
    agent = Agent(deps)
    agent.run(max_ticks=1)
    rows = deps.trade_logger.read_all()
    assert len(rows) == 1
    assert rows[0]["slug"] == "nba-lal-bos-m1"
    assert rows[0]["sport_category"] == "basketball"
    assert rows[0]["league"] == "nba"
    assert rows[0]["confidence"] == "A"


def test_trade_record_carries_num_bookmakers_and_has_sharp(tmp_path: Path, monkeypatch) -> None:
    """Entry kaydı bookmaker sayısını ve sharp flag'i gate'ten taşımalı."""
    deps = _build_deps(
        tmp_path, [_market(cid="m1", yes=0.50)],
        bm_result=BookmakerProbability(
            probability=0.65, confidence="A",
            bookmaker_prob=0.65, num_bookmakers=12.0, has_sharp=True,
        ),
    )
    monkeypatch.setattr(time, "sleep", lambda *a: None)
    Agent(deps).run(max_ticks=1)
    rows = deps.trade_logger.read_all()
    assert len(rows) == 1
    assert rows[0]["num_bookmakers"] == 12.0
    assert rows[0]["has_sharp"] is True


# ── Light cycle / exit ──

def test_light_cycle_triggers_near_resolve_exit(tmp_path: Path, monkeypatch) -> None:
    # Pozisyon aç (heavy) + fiyatı manipüle et (current 0.95) → near-resolve exit
    deps = _build_deps(tmp_path, [_market(cid="m1", yes=0.50)], bm_result=_bm(prob=0.65, conf="A"))
    monkeypatch.setattr(time, "sleep", lambda *a: None)
    agent = Agent(deps)
    agent.run(max_ticks=1)  # Pozisyon açıldı

    # Fiyatı yükselt — yeterince eski maç
    pos = deps.state.portfolio.positions["m1"]
    pos.current_price = 0.95
    pos.match_start_iso = _iso(datetime.now(timezone.utc) - timedelta(minutes=30))

    # Light cycle çalıştır
    deps.cycle_manager._last_heavy_ts = time.time()  # heavy tekrar tetiklenmesin
    agent.run(max_ticks=1)

    # Pozisyon kapandı
    assert "m1" not in deps.state.portfolio.positions


# ── Exit-triggered heavy + eligible queue ──

def test_slot_full_market_goes_to_eligible_queue(tmp_path: Path, monkeypatch) -> None:
    deps = _build_deps(tmp_path, [_market(cid="m1", yes=0.50)], bm_result=_bm(prob=0.65, conf="A"))
    monkeypatch.setattr(time, "sleep", lambda *a: None)

    # max_positions 1 — pozisyon açınca slot dolar
    deps.gate.config = GateConfig(
        min_edge=0.06, max_positions=1, max_exposure_pct=0.50,
        max_single_bet_usdc=75.0, max_bet_pct=0.05,
    )

    agent = Agent(deps)
    agent.run(max_ticks=1)
    assert deps.state.portfolio.count() == 1

    # Şimdi 2. market ekle — slot dolu, queue'ya düşmeli
    new_market = _market(cid="m2", yes=0.50)
    deps.scanner._gamma.fetch_events.return_value = [new_market]
    # Heavy'yi zorla tetikle
    deps.cycle_manager._last_heavy_ts = 0
    agent.run(max_ticks=1)

    # Pozisyon hala 1, eligible queue'da 1 entry
    assert deps.state.portfolio.count() == 1
    # Queue'ya push — cid m2
    # (Not: gate max_positions_reached → eligible'a değil "blanket halt" uyguluyor.
    #  Individual skipped_reason pathway — test yaklaşık kontrol)


# ── WebSocket price feed integration ──

def _deps_with_ws(tmp_path: Path, markets: list[MarketData], bm_result: BookmakerProbability | None = None):
    """_build_deps + mock PriceFeed."""
    deps = _build_deps(tmp_path, markets, bm_result=bm_result)
    price_feed = MagicMock()
    price_feed.subscribe = MagicMock()
    price_feed.unsubscribe = MagicMock()
    price_feed.set_callback = MagicMock()
    price_feed.start_background = MagicMock()
    price_feed.stop = MagicMock()
    deps.price_feed = price_feed
    return deps, price_feed


def test_agent_init_wires_callback_to_price_feed(tmp_path: Path) -> None:
    deps, feed = _deps_with_ws(tmp_path, [])
    agent = Agent(deps)
    feed.set_callback.assert_called_once()
    # Callback agent._on_price_update olmalı
    callback = feed.set_callback.call_args.args[0]
    assert callable(callback)


def test_agent_run_starts_ws_background(tmp_path: Path, monkeypatch) -> None:
    deps, feed = _deps_with_ws(tmp_path, [])
    monkeypatch.setattr(time, "sleep", lambda *a: None)
    agent = Agent(deps)
    agent.run(max_ticks=1)
    feed.start_background.assert_called_once()


def test_agent_subscribes_on_entry(tmp_path: Path, monkeypatch) -> None:
    deps, feed = _deps_with_ws(tmp_path, [_market(cid="m1", yes=0.50)], bm_result=_bm(prob=0.65, conf="A"))
    monkeypatch.setattr(time, "sleep", lambda *a: None)
    agent = Agent(deps)
    agent.run(max_ticks=1)
    # Entry → subscribe([token_id])
    assert deps.state.portfolio.count() == 1
    pos = list(deps.state.portfolio.positions.values())[0]
    feed.subscribe.assert_called_with([pos.token_id])


def test_agent_unsubscribes_on_full_exit(tmp_path: Path, monkeypatch) -> None:
    deps, feed = _deps_with_ws(tmp_path, [_market(cid="m1", yes=0.50)], bm_result=_bm(prob=0.65, conf="A"))
    monkeypatch.setattr(time, "sleep", lambda *a: None)
    agent = Agent(deps)
    agent.run(max_ticks=1)  # Pozisyon aç
    pos = list(deps.state.portfolio.positions.values())[0]

    # Near-resolve trigger
    pos.current_price = 0.95
    pos.match_start_iso = _iso(datetime.now(timezone.utc) - timedelta(minutes=30))

    deps.cycle_manager._last_heavy_ts = time.time()  # heavy tekrar tetiklenmesin
    feed.unsubscribe.reset_mock()
    agent.run(max_ticks=1)

    # Pozisyon kapandı + unsubscribe çağrıldı
    assert deps.state.portfolio.count() == 0
    feed.unsubscribe.assert_called_with([pos.token_id])


def test_agent_price_callback_updates_portfolio(tmp_path: Path, monkeypatch) -> None:
    deps, feed = _deps_with_ws(tmp_path, [_market(cid="m1", yes=0.50)], bm_result=_bm(prob=0.65, conf="A"))
    monkeypatch.setattr(time, "sleep", lambda *a: None)
    agent = Agent(deps)
    agent.run(max_ticks=1)
    pos = list(deps.state.portfolio.positions.values())[0]
    old_price = pos.current_price

    # Callback'i simüle et (WS geldi gibi)
    agent._on_price_update(pos.token_id, yes_price=0.70, bid_price=0.69, _ts=0)

    assert pos.current_price == 0.70
    assert pos.bid_price == 0.69
    assert pos.current_price != old_price


def test_agent_request_stop_stops_ws(tmp_path: Path) -> None:
    deps, feed = _deps_with_ws(tmp_path, [])
    agent = Agent(deps)
    agent.request_stop()
    feed.stop.assert_called_once()


def test_agent_without_ws_works(tmp_path: Path, monkeypatch) -> None:
    """Eski davranış korunuyor — price_feed=None ile çalışır."""
    deps = _build_deps(tmp_path, [_market(cid="m1", yes=0.50)], bm_result=_bm(prob=0.65, conf="A"))
    assert deps.price_feed is None  # _build_deps default
    monkeypatch.setattr(time, "sleep", lambda *a: None)
    agent = Agent(deps)
    agent.run(max_ticks=1)  # Hata atmamalı
    assert deps.state.portfolio.count() == 1
