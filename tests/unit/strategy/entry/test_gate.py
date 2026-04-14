"""entry/gate.py için birim testler."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.domain.analysis.probability import BookmakerProbability
from src.domain.guards.blacklist import Blacklist
from src.domain.guards.manipulation import ManipulationCheck
from src.domain.portfolio.manager import PortfolioManager
from src.domain.risk.circuit_breaker import CircuitBreaker
from src.domain.risk.cooldown import CooldownTracker
from src.models.market import MarketData
from src.models.position import Position
from src.strategy.entry.gate import EntryGate, GateConfig, GateResult


def _market(cid: str = "c1", event: str = "e1", yp: float = 0.50) -> MarketData:
    return MarketData(
        condition_id=cid,
        question="Will Lakers beat Celtics?",
        slug="nba-lal-bos-2026",
        yes_token_id="y", no_token_id="n",
        yes_price=yp, no_price=1 - yp,
        liquidity=50_000, volume_24h=10_000, tags=[],
        end_date_iso="2026-04-14T00:00:00Z",
        sport_tag="basketball_nba",
        event_id=event,
    )


def _bm(prob: float = 0.60, conf: str = "B") -> BookmakerProbability:
    return BookmakerProbability(
        probability=prob, confidence=conf,
        bookmaker_prob=prob, num_bookmakers=10.0, has_sharp=(conf == "A"),
    )


def _safe_manip() -> ManipulationCheck:
    return ManipulationCheck(safe=True, risk_level="low", flags=[], recommendation="")


def _high_manip() -> ManipulationCheck:
    return ManipulationCheck(safe=False, risk_level="high", flags=["X"], recommendation="")


def _medium_manip() -> ManipulationCheck:
    return ManipulationCheck(safe=True, risk_level="medium", flags=["Y"], recommendation="")


def _make_gate(**kwargs) -> EntryGate:
    portfolio = kwargs.get("portfolio") or PortfolioManager(initial_bankroll=1000.0)
    cb = kwargs.get("cb") or CircuitBreaker()
    cd = kwargs.get("cd") or CooldownTracker()
    bl = kwargs.get("bl") or Blacklist()
    enricher = kwargs.get("enricher") or (lambda m: _bm())
    manip = kwargs.get("manip") or (lambda question, liquidity: _safe_manip())
    return EntryGate(
        config=GateConfig(),
        portfolio=portfolio, circuit_breaker=cb, cooldown=cd, blacklist=bl,
        odds_enricher=enricher, manipulation_checker=manip,
    )


def test_happy_path_produces_signal() -> None:
    gate = _make_gate()
    results = gate.run([_market()])
    assert len(results) == 1
    r = results[0]
    assert r.signal is not None
    assert r.signal.size_usdc > 0


def test_event_guard_blocks_second_position() -> None:
    p = PortfolioManager(initial_bankroll=1000.0)
    p.add_position(Position(
        condition_id="prev_c", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=40, shares=100, current_price=0.4,
        anchor_probability=0.55, event_id="e1",
    ))
    gate = _make_gate(portfolio=p)
    # Aynı event_id=e1 ikinci giriş → bloklanır
    results = gate.run([_market(cid="c2", event="e1")])
    assert results[0].signal is None
    assert "event_already_held" in results[0].skipped_reason


def test_blacklist_blocks() -> None:
    bl = Blacklist()
    bl.add_condition("c1")
    gate = _make_gate(bl=bl)
    results = gate.run([_market(cid="c1")])
    assert results[0].signal is None
    assert results[0].skipped_reason == "blacklisted"


def test_manipulation_high_blocks() -> None:
    gate = _make_gate(manip=lambda question, liquidity: _high_manip())
    results = gate.run([_market()])
    assert results[0].signal is None
    assert "manipulation" in results[0].skipped_reason


def test_manipulation_medium_halves_size() -> None:
    p = PortfolioManager(initial_bankroll=1000.0)
    gate = _make_gate(portfolio=p, manip=lambda question, liquidity: _medium_manip())
    results = gate.run([_market()])
    assert results[0].signal is not None
    # B sizing: 1000 * 0.04 = 40; medium × 0.5 = 20
    assert results[0].signal.size_usdc == 20.0


def test_no_bookmaker_data_skips() -> None:
    gate = _make_gate(enricher=lambda m: None)
    results = gate.run([_market()])
    assert results[0].signal is None
    assert results[0].skipped_reason == "no_bookmaker_data"


def test_c_confidence_skips() -> None:
    gate = _make_gate(enricher=lambda m: _bm(conf="C"))
    results = gate.run([_market()])
    assert results[0].signal is None
    assert results[0].skipped_reason == "confidence_C"


def test_no_edge_skips() -> None:
    # anchor=0.52, market=0.50 → raw=0.02 < threshold 0.06 → HOLD
    gate = _make_gate(enricher=lambda m: _bm(prob=0.52, conf="B"))
    results = gate.run([_market()])
    assert results[0].signal is None
    assert results[0].skipped_reason == "no_edge"


def test_circuit_breaker_halts_all() -> None:
    cb = CircuitBreaker()
    cb.record_exit(pnl_usd=-100, portfolio_value=1000)  # -10% daily → halt
    gate = _make_gate(cb=cb)
    results = gate.run([_market(), _market(cid="c2", event="e2")])
    assert all(r.signal is None for r in results)
    assert all("breaker" in r.skipped_reason for r in results)


def test_cooldown_halts_all() -> None:
    cd = CooldownTracker(trigger_threshold=1, cooldown_cycles=2)
    cd.record_outcome(win=False)  # 1 kayıp → cooldown tetiklenir
    gate = _make_gate(cd=cd)
    results = gate.run([_market()])
    assert results[0].signal is None
    assert results[0].skipped_reason == "cooldown_active"


def test_max_positions_halts() -> None:
    p = PortfolioManager(initial_bankroll=10_000.0)
    # max_positions=50 default; teste özel 5 set edip 5 pozisyon ekle
    for i in range(5):
        p.add_position(Position(
            condition_id=f"c{i}", token_id=f"t{i}", direction="BUY_YES",
            entry_price=0.4, size_usdc=40, shares=100, current_price=0.4,
            anchor_probability=0.55, event_id=f"e{i}",
        ))
    gate = _make_gate(portfolio=p)
    gate.config = GateConfig(max_positions=5, max_exposure_pct=0.50,
                             max_single_bet_usdc=75.0, max_bet_pct=0.05)
    results = gate.run([_market(cid="new", event="enew")])
    assert results[0].signal is None
    assert results[0].skipped_reason == "max_positions_reached"


def test_exposure_cap_blocks() -> None:
    p = PortfolioManager(initial_bankroll=1000.0)
    # %48 yatırılmış → 40 daha eklenirse %52 > %50 cap
    p.add_position(Position(
        condition_id="prev", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=480, shares=1200, current_price=0.4,
        anchor_probability=0.55, event_id="eprev",
    ))
    gate = _make_gate(portfolio=p)
    results = gate.run([_market(cid="new", event="enew")])
    assert results[0].signal is None
    assert results[0].skipped_reason == "exposure_cap_reached"


def test_size_below_min_skips() -> None:
    # Bankroll $100 → B sizing $4 < $5 min
    p = PortfolioManager(initial_bankroll=100.0)
    gate = _make_gate(portfolio=p)
    results = gate.run([_market()])
    assert results[0].signal is None
    assert "size_below_min" in results[0].skipped_reason
