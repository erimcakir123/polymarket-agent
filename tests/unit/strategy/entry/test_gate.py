"""entry/gate.py için birim testler."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
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


def _enrich(bm: BookmakerProbability | None = None, *, prob: float = 0.60, conf: str = "B") -> EnrichResult:
    """Başarılı bir EnrichResult döner (probability dolu)."""
    return EnrichResult(probability=bm or _bm(prob=prob, conf=conf), fail_reason=None)


def _enrich_fail(reason: EnrichFailReason = EnrichFailReason.SPORT_KEY_UNRESOLVED) -> EnrichResult:
    """Başarısız bir EnrichResult döner (probability=None)."""
    return EnrichResult(probability=None, fail_reason=reason)


def _make_gate(**kwargs) -> EntryGate:
    portfolio = kwargs.get("portfolio") or PortfolioManager(initial_bankroll=1000.0)
    cb = kwargs.get("cb") or CircuitBreaker()
    cd = kwargs.get("cd") or CooldownTracker()
    bl = kwargs.get("bl") or Blacklist()
    enricher = kwargs.get("enricher") or (lambda m: _enrich())
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
    gate = _make_gate(enricher=lambda m: _enrich_fail())
    results = gate.run([_market()])
    assert results[0].signal is None
    assert results[0].skipped_reason == "no_bookmaker_data"


def test_c_confidence_skips() -> None:
    gate = _make_gate(enricher=lambda m: _enrich(_bm(conf="C")))
    results = gate.run([_market()])
    assert results[0].signal is None
    assert results[0].skipped_reason == "confidence_C"


def test_no_edge_skips() -> None:
    # anchor=0.52, market=0.50 → raw=0.02 < threshold 0.06 → HOLD
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.52, conf="B")))
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


def test_size_below_min_skips() -> None:
    # Bankroll $100 → B sizing $4 < $5 min
    p = PortfolioManager(initial_bankroll=100.0)
    gate = _make_gate(portfolio=p)
    results = gate.run([_market()])
    assert results[0].signal is None
    assert "size_below_min" in results[0].skipped_reason


def test_entry_price_cap_blocks_high_favorite() -> None:
    # Consensus 0.90'da sinyal üretir (min_price 0.60) ama gate 0.88 cap ile reddeder.
    # anchor 0.85, market yes 0.90 → is_consensus True (ikisi de YES favori), entry=0.90
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.85, conf="A")))
    results = gate.run([_market(yp=0.90)])
    assert results[0].signal is None
    assert results[0].skipped_reason == "entry_price_cap"


def test_entry_price_cap_allows_under_threshold() -> None:
    # 0.87 eşiğin altında → geçer
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.80, conf="A")))
    results = gate.run([_market(yp=0.87)])
    assert results[0].signal is not None


def test_gate_clips_signal_size_when_partial_space_in_hard_cap() -> None:
    # initial=$2000, invested=$1010 → bankroll_kalan=$990, total=$2000.
    # hard=$2000×0.52=$1040, available=$1040-$1010=$30.
    # A sizing = $990×0.05 = $49.5; min(49.5, 30) = $30 (clip).
    p = PortfolioManager(initial_bankroll=2000.0)
    p.add_position(Position(
        condition_id="prev", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=1010.0, shares=2525.0, current_price=0.4,
        anchor_probability=0.55, event_id="eprev",
    ))
    gate = _make_gate(portfolio=p, enricher=lambda m: _enrich(_bm(prob=0.60, conf="A")))
    results = gate.run([_market(cid="new", event="enew")])
    assert results[0].signal is not None
    assert abs(results[0].signal.size_usdc - 30.0) < 0.5


def test_gate_skips_when_available_below_min_entry_size() -> None:
    # initial=$2000, invested=$1035 → bankroll_kalan=$965, total=$2000.
    # hard=$1040, available=$5. min_entry = $965×0.015 ≈ $14.48. $5 < $14.48 → skip.
    p = PortfolioManager(initial_bankroll=2000.0)
    p.add_position(Position(
        condition_id="prev", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=1035.0, shares=2587.5, current_price=0.4,
        anchor_probability=0.55, event_id="eprev",
    ))
    gate = _make_gate(portfolio=p)
    results = gate.run([_market(cid="new", event="enew")])
    assert results[0].signal is None
    assert results[0].skipped_reason == "exposure_cap_reached"


def test_gate_skips_when_hard_cap_fully_used() -> None:
    # initial=$2000, invested=$1040 → bankroll_kalan=$960, total=$2000.
    # hard=$1040, available=0. min_entry ≈ $14.40 > 0 → skip.
    p = PortfolioManager(initial_bankroll=2000.0)
    p.add_position(Position(
        condition_id="prev", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=1040.0, shares=2600.0, current_price=0.4,
        anchor_probability=0.55, event_id="eprev",
    ))
    gate = _make_gate(portfolio=p)
    results = gate.run([_market(cid="new", event="enew")])
    assert results[0].signal is None
    assert results[0].skipped_reason == "exposure_cap_reached"


# --- SPEC-001: skip_detail for no_bookmaker_data ---

def test_evaluate_one_no_bookmaker_data_sets_skip_detail_fail_reason() -> None:
    # Enricher fail_reason=SPORT_KEY_UNRESOLVED döner → skip_detail bu değeri taşımalı
    gate = _make_gate(
        enricher=lambda m: EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.SPORT_KEY_UNRESOLVED,
        )
    )
    result = gate._evaluate_one(_market())
    assert result.skipped_reason == "no_bookmaker_data"
    assert result.skip_detail == "sport_key_unresolved"


# --- SPEC-001: skip_detail for the remaining 11 reasons + 2 reason normalizations ---


def test_evaluate_one_event_already_held_sets_skip_detail_event_id() -> None:
    """event_already_held → skip_detail='event_id=<event_id>'."""
    from src.models.position import Position

    p = PortfolioManager(initial_bankroll=1000.0)
    p.add_position(Position(
        condition_id="prev_c", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=40, shares=100, current_price=0.4,
        anchor_probability=0.55, event_id="378836",
    ))
    gate = _make_gate(portfolio=p)
    result = gate._evaluate_one(_market(cid="c2", event="378836"))
    assert result.skipped_reason == "event_already_held"
    assert result.skip_detail == "event_id=378836"


def test_evaluate_one_blacklisted_condition_id_sets_skip_detail_match_condition_id() -> None:
    """blacklist condition_id hit → skip_detail='match=condition_id'."""
    bl = Blacklist()
    bl.add_condition("c1")
    gate = _make_gate(bl=bl)
    result = gate._evaluate_one(_market(cid="c1"))
    assert result.skipped_reason == "blacklisted"
    assert result.skip_detail == "match=condition_id"


def test_evaluate_one_blacklisted_event_id_sets_skip_detail_match_event_id() -> None:
    """blacklist event_id hit (condition_id clean) → skip_detail='match=event_id'."""
    bl = MagicMock(spec=Blacklist)
    # condition_id check → False; event_id check → True
    bl.is_blacklisted.side_effect = lambda **kwargs: bool(kwargs.get("event_id"))
    gate = _make_gate(bl=bl)
    result = gate._evaluate_one(_market(cid="c_clean", event="e_blocked"))
    assert result.skipped_reason == "blacklisted"
    assert result.skip_detail == "match=event_id"


def test_evaluate_one_manipulation_high_risk_sets_skip_detail_reason() -> None:
    """manipulation_high_risk → skip_detail=flags joined (or 'unknown')."""
    manip = ManipulationCheck(safe=False, risk_level="high", flags=["viral_keyword"], recommendation="")
    gate = _make_gate(manip=lambda question, liquidity: manip)
    result = gate._evaluate_one(_market())
    assert result.skipped_reason == "manipulation_high_risk"
    assert result.skip_detail == "viral_keyword"


def test_evaluate_one_confidence_c_sets_skip_detail_num_bookmakers() -> None:
    """confidence_C → skip_detail='num_bookmakers=X.X'."""
    bm = BookmakerProbability(
        probability=0.55, confidence="C",
        bookmaker_prob=0.55, num_bookmakers=1.5, has_sharp=False,
    )
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(_market())
    assert result.skipped_reason == "confidence_C"
    assert result.skip_detail == "num_bookmakers=1.5"


def test_evaluate_one_no_edge_sets_skip_detail_edge_values() -> None:
    """no_edge → skip_detail contains edge/min/bm/yes values."""
    # bm=0.63, yes=0.60 → raw_edge=0.03 < 0.06 → no signal
    bm = _bm(prob=0.63, conf="B")
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(_market(yp=0.60))
    assert result.skipped_reason == "no_edge"
    assert "edge=0.030" in result.skip_detail
    assert "min=0.06" in result.skip_detail
    assert "bm=0.63" in result.skip_detail
    assert "yes=0.60" in result.skip_detail


def test_evaluate_one_entry_price_cap_sets_skip_detail_price_cap() -> None:
    """entry_price_cap → skip_detail='price=X.XXX, cap=X.XX'."""
    # anchor=0.85(A) + market=0.90 → consensus signal at 0.90 > 0.88 cap
    bm = _bm(prob=0.85, conf="A")
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(_market(yp=0.90))
    assert result.skipped_reason == "entry_price_cap"
    assert "price=0.900" in result.skip_detail
    assert "cap=0.88" in result.skip_detail


def test_evaluate_one_size_below_min_raw_sets_skip_detail_size_min() -> None:
    """size_below_min (raw adjusted_size < min) → normalized reason + detail."""
    # Bankroll $100 → B sizing ≈ $4 < $5 POLYMARKET_MIN
    p = PortfolioManager(initial_bankroll=100.0)
    gate = _make_gate(portfolio=p)
    result = gate._evaluate_one(_market())
    assert result.skipped_reason == "size_below_min"
    assert "size=" in result.skip_detail
    assert "min=" in result.skip_detail
    # reason must NOT embed numbers (normalized form)
    assert "(" not in result.skipped_reason


def test_evaluate_one_size_below_min_final_sets_skip_detail_size_min() -> None:
    """size_below_min (final clipped size < min after exposure cap clip) → normalized reason."""
    # We need: raw_size >= min but available < min after clip.
    # Use bankroll=$5000 (A sizing = $250 raw), but cap available to just $3 by investing heavily.
    # invested=$2535 → total=$5000, hard_cap=5000*0.52=$2600, available=$65.
    # Actually easier: use a very small available so final_size < POLYMARKET_MIN_ORDER_USDC
    # but available >= min_entry_size_pct*bankroll.
    # POLYMARKET_MIN_ORDER_USDC = $5.
    # min_entry_size_pct=0.015 → with bankroll=$300, min_size=$4.5.
    # A sizing → 300*0.05=$15 raw, available < $5 but >= $4.5 → final=available < $5 → size_below_min
    # hard_cap = total * 0.52; total = bankroll + invested
    # If invested=$152 → total=$452, hard_cap=$235, available=$235-$152=$83 — too big.
    # Use max_exposure_pct=0.10 to shrink. But GateConfig default=0.50.
    # Simplest: mock available_under_cap via MagicMock on portfolio.
    # Strategy: patch portfolio so available = $4 (< POLYMARKET_MIN_ORDER_USDC=$5)
    #           but available ($4) >= min_size (bankroll*0.015)
    #           → exposure_cap_reached NOT triggered, final_size = min(raw, $4) = $4 < $5 → size_below_min
    p = MagicMock(spec=PortfolioManager)
    p.count.return_value = 0
    p.has_event.return_value = False
    p.bankroll = 100.0
    p.total_invested.return_value = 0.0
    p.positions = []

    import unittest.mock as _mock

    with _mock.patch(
        "src.strategy.entry.gate.available_under_cap",
        return_value=4.0,  # < POLYMARKET_MIN_ORDER_USDC ($5) but >= min_size (100*0.015=$1.5)
    ):
        gate = _make_gate(portfolio=p, enricher=lambda m: _enrich(_bm(prob=0.65, conf="A")))
        result = gate._evaluate_one(_market())

    assert result.skipped_reason == "size_below_min"
    assert "size=" in result.skip_detail
    assert "min=" in result.skip_detail
    assert "(" not in result.skipped_reason


def test_evaluate_one_exposure_cap_sets_skip_detail_available_min() -> None:
    """exposure_cap_reached → skip_detail='available=X.XX, min=X.XX'."""
    # initial=$2000, invested=$1035 → available=$5 < min_entry=$14.48 → exposure_cap_reached
    from src.models.position import Position

    p = PortfolioManager(initial_bankroll=2000.0)
    p.add_position(Position(
        condition_id="prev", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=1035.0, shares=2587.5, current_price=0.4,
        anchor_probability=0.55, event_id="eprev",
    ))
    gate = _make_gate(portfolio=p)
    result = gate._evaluate_one(_market(cid="new", event="enew"))
    assert result.skipped_reason == "exposure_cap_reached"
    assert "available=" in result.skip_detail
    assert "min=" in result.skip_detail


def test_run_circuit_breaker_sets_skip_detail_breaker_reason_normalized() -> None:
    """circuit_breaker (normalized) → reason='circuit_breaker', detail=raw breaker message."""
    cb = MagicMock(spec=CircuitBreaker)
    cb.should_halt_entries.return_value = (True, "Daily loss -3.1% exceeded soft limit -3%")
    gate = _make_gate(cb=cb)
    results = gate.run([_market()])
    r = results[0]
    assert r.skipped_reason == "circuit_breaker"
    assert r.skip_detail == "Daily loss -3.1% exceeded soft limit -3%"


def test_run_cooldown_sets_skip_detail_cycles_remaining() -> None:
    """cooldown_active → skip_detail='cycles_remaining=N'."""
    cd = CooldownTracker(trigger_threshold=1, cooldown_cycles=2)
    cd.record_outcome(win=False)  # triggers cooldown: remaining=2
    gate = _make_gate(cd=cd)
    results = gate.run([_market()])
    r = results[0]
    assert r.skipped_reason == "cooldown_active"
    # remaining starts at 2; is_active() decrements to 1, returns True (1>0)
    # We capture before calling is_active(), so detail should show 2
    assert r.skip_detail == "cycles_remaining=2"


def test_run_max_positions_sets_skip_detail_count_slash_limit() -> None:
    """max_positions_reached → skip_detail='count=N/N'."""
    from src.models.position import Position

    p = PortfolioManager(initial_bankroll=10_000.0)
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
    r = results[0]
    assert r.skipped_reason == "max_positions_reached"
    assert r.skip_detail == "count=5/5"
