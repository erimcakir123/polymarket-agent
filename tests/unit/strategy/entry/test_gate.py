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
    # yp=0.65: anchor=0.60 → BUY_YES, win_prob=0.60 >= 0.55, price=0.65 in [0.60, 0.85] ✓
    gate = _make_gate()
    results = gate.run([_market(yp=0.65)])
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
    # yp=0.65: anchor=0.60 → BUY_YES, win_prob=0.60 >= 0.55 ✓, price in range ✓
    p = PortfolioManager(initial_bankroll=1000.0)
    gate = _make_gate(portfolio=p, manip=lambda question, liquidity: _medium_manip())
    results = gate.run([_market(yp=0.65)])
    assert results[0].signal is not None
    # B sizing: 1000 * 0.04 * win_prob(0.60) = 24; medium × 0.5 = 12 (SPEC-016)
    assert results[0].signal.size_usdc == 12.0


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


def test_below_fav_prob_skips() -> None:
    # anchor=0.52, win_prob=0.52 < min_favorite_probability=0.55 → below_fav_prob
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.52, conf="B")))
    results = gate.run([_market(yp=0.65)])
    assert results[0].signal is None
    assert results[0].skipped_reason == "below_fav_prob"


def test_price_out_of_range_skips() -> None:
    # anchor=0.60, win_prob=0.60 >= 0.55 ✓, but yes_price=0.50 < min_entry_price=0.60 → price_out_of_range
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.60, conf="B")))
    results = gate.run([_market(yp=0.50)])
    assert results[0].signal is None
    assert results[0].skipped_reason == "price_out_of_range"


def test_circuit_breaker_halts_all() -> None:
    cb = CircuitBreaker()
    cb.record_exit(pnl_usd=-100)  # -$100 → portfolio $1000'de -%10 daily → halt
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
                             confidence_bet_pct={"A": 0.05, "B": 0.04}, max_bet_pct=0.05)
    results = gate.run([_market(cid="new", event="enew")])
    assert results[0].signal is None
    assert results[0].skipped_reason == "max_positions_reached"


def test_size_below_min_skips() -> None:
    # yp=0.65: passes directional; Bankroll $100 → B sizing ≈ $2.4 < $5 min
    p = PortfolioManager(initial_bankroll=100.0)
    gate = _make_gate(portfolio=p)
    results = gate.run([_market(yp=0.65)])
    assert results[0].signal is None
    assert "size_below_min" in results[0].skipped_reason


def test_price_out_of_range_blocks_high_price() -> None:
    # anchor=0.92, win_prob=0.92 >= 0.55 ✓, yes_price=0.90 > max_entry_price=0.85 → price_out_of_range
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.92, conf="A")))
    results = gate.run([_market(yp=0.90)])
    assert results[0].signal is None
    assert results[0].skipped_reason == "price_out_of_range"


def test_directional_allows_price_within_range() -> None:
    # anchor=0.93, win_prob=0.93 >= 0.55 ✓, yes_price=0.80 in [0.60, 0.85] ✓ → enters
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.93, conf="A")))
    results = gate.run([_market(yp=0.80)])
    assert results[0].signal is not None


# ── Cricket entry skip (SPEC-011) ──

def _cricket_market(cid: str = "cc1", event: str = "ec1", yp: float = 0.50) -> MarketData:
    return MarketData(
        condition_id=cid,
        question="Will KKR beat RR?",
        slug="cricket-ipl-kkr-rr-2026",
        yes_token_id="y", no_token_id="n",
        yes_price=yp, no_price=1 - yp,
        liquidity=50_000, volume_24h=10_000, tags=[],
        end_date_iso="2026-04-19T00:00:00Z",
        sport_tag="cricket_ipl",
        event_id=event,
    )


def test_cricket_entry_skipped_when_cricapi_quota_exhausted() -> None:
    """CricAPI quota dolu → cricket entry cricapi_unavailable ile skip edilir (SPEC-011)."""
    cricket_client = MagicMock()
    cricket_client.quota.exhausted = True
    cricket_client.quota.used_today = 100
    cricket_client.quota.daily_limit = 100

    gate = EntryGate(
        config=GateConfig(),
        portfolio=PortfolioManager(initial_bankroll=1000.0),
        circuit_breaker=CircuitBreaker(),
        cooldown=CooldownTracker(),
        blacklist=Blacklist(),
        odds_enricher=lambda m: _enrich(),
        manipulation_checker=lambda question, liquidity: _safe_manip(),
        cricket_client=cricket_client,
    )
    results = gate.run([_cricket_market()])
    assert results[0].signal is None
    assert results[0].skipped_reason == "cricapi_unavailable"


def test_cricket_entry_proceeds_when_quota_available() -> None:
    """CricAPI quota dolmamış → cricket entry normal devam eder (SPEC-011)."""
    cricket_client = MagicMock()
    cricket_client.quota.exhausted = False
    cricket_client.quota.used_today = 50
    cricket_client.quota.daily_limit = 100

    gate = EntryGate(
        config=GateConfig(),
        portfolio=PortfolioManager(initial_bankroll=1000.0),
        circuit_breaker=CircuitBreaker(),
        cooldown=CooldownTracker(),
        blacklist=Blacklist(),
        odds_enricher=lambda m: _enrich(),
        manipulation_checker=lambda question, liquidity: _safe_manip(),
        cricket_client=cricket_client,
    )
    # yp=0.65: passes directional price range check [0.60, 0.85]
    results = gate.run([_cricket_market(yp=0.65)])
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
    results = gate.run([_market(cid="new", event="enew", yp=0.65)])
    assert results[0].signal is not None
    assert abs(results[0].signal.size_usdc - 30.0) < 0.5


def test_approved_signal_carries_bookmaker_metadata() -> None:
    """Onaylanan signal'da num_bookmakers ve has_sharp patch'lenen değerleri taşır."""
    bm = _bm(prob=0.65, conf="A")  # has_sharp=True (conf=="A"), num_bookmakers=10.0
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    results = gate.run([_market(yp=0.65)])
    sig = results[0].signal
    assert sig is not None
    assert sig.num_bookmakers == bm.num_bookmakers
    assert sig.has_sharp == bm.has_sharp


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
    results = gate.run([_market(cid="new", event="enew", yp=0.65)])
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
    results = gate.run([_market(cid="new", event="enew", yp=0.65)])
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


def test_evaluate_one_below_fav_prob_sets_skip_detail_values() -> None:
    """below_fav_prob → skip_detail contains win_prob/min/bm values."""
    # anchor=0.52, win_prob=0.52 < min_favorite_probability=0.55 → below_fav_prob
    bm = _bm(prob=0.52, conf="B")
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(_market(yp=0.65))
    assert result.skipped_reason == "below_fav_prob"
    assert "win_prob=" in result.skip_detail
    assert "min=" in result.skip_detail
    assert "bm=0.52" in result.skip_detail


def test_evaluate_one_price_out_of_range_sets_skip_detail_values() -> None:
    """price_out_of_range → skip_detail contains price/min/max values."""
    # anchor=0.60, win_prob=0.60 >= 0.55 ✓, yes_price=0.50 < min_entry_price=0.60 → price_out_of_range
    bm = _bm(prob=0.60, conf="B")
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(_market(yp=0.50))
    assert result.skipped_reason == "price_out_of_range"
    assert "price=" in result.skip_detail
    assert "min=" in result.skip_detail
    assert "max=" in result.skip_detail


def test_evaluate_one_price_out_of_range_high_price_sets_skip_detail() -> None:
    """price_out_of_range (high) → skip_detail contains price/min/max values."""
    # anchor=0.92, win_prob >= 0.55 ✓, yes_price=0.90 > max_entry_price=0.85 → price_out_of_range
    bm = _bm(prob=0.92, conf="A")
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(_market(yp=0.90))
    assert result.skipped_reason == "price_out_of_range"
    assert "price=0.900" in result.skip_detail
    assert "max=0.85" in result.skip_detail


def test_evaluate_one_size_below_min_raw_sets_skip_detail_size_min() -> None:
    """size_below_min (raw adjusted_size < min) → normalized reason + detail."""
    # yp=0.65: passes directional; Bankroll $100 → B sizing ≈ $2.4 < $5 POLYMARKET_MIN
    p = PortfolioManager(initial_bankroll=100.0)
    gate = _make_gate(portfolio=p)
    result = gate._evaluate_one(_market(yp=0.65))
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
        result = gate._evaluate_one(_market(yp=0.65))

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
    result = gate._evaluate_one(_market(cid="new", event="enew", yp=0.65))
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
                             confidence_bet_pct={"A": 0.05, "B": 0.04}, max_bet_pct=0.05)
    results = gate.run([_market(cid="new", event="enew")])
    r = results[0]
    assert r.skipped_reason == "max_positions_reached"
    assert r.skip_detail == "count=5/5"


# --- Gamma startTime korunur, Odds API commence_time override etmez ---


def test_gate_preserves_gamma_start_time_ignoring_odds_commence() -> None:
    """Gamma startTime korunur, Odds API commence_time override etmez."""
    m = _market()
    gamma_time = "2026-04-17T19:00:00Z"  # Gamma doğru maç saati
    m.match_start_iso = gamma_time
    odds_time = "2026-04-17T22:00:00Z"  # Odds API kart saati (yanlış)
    enricher = lambda market: EnrichResult(
        probability=_bm(), fail_reason=None,
        odds_commence_time=odds_time,
    )
    gate = _make_gate(enricher=enricher)
    gate.run([m])
    assert m.match_start_iso == gamma_time


def test_gate_keeps_match_start_iso_when_no_commence_time() -> None:
    """odds_commence_time boşsa mevcut match_start_iso korunmalı."""
    m = _market()
    original = "2026-04-17T08:00:00Z"
    m.match_start_iso = original
    enricher = lambda market: EnrichResult(
        probability=_bm(), fail_reason=None,
        odds_commence_time="",
    )
    gate = _make_gate(enricher=enricher)
    gate.run([m])
    assert m.match_start_iso == original


# --- SPEC-016: win_prob wiring ---


def test_gate_passes_win_prob_when_flag_enabled() -> None:
    """BUY_YES, anchor=0.70, flag=on → stake = 1000 × 0.05 × 0.70 = $35 (A-grade)."""
    # yp=0.65: anchor=0.70 → BUY_YES, win_prob=0.70 >= 0.55 ✓, price=0.65 in [0.60, 0.85] ✓
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.70, conf="A")))
    gate.config = GateConfig(
        probability_weighted=True,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
        max_single_bet_usdc=200.0,  # high cap so win_prob drives the result
        max_bet_pct=0.20,
    )
    results = gate.run([_market(yp=0.65)])
    assert results[0].signal is not None
    # Expected: 1000 × 0.05 × 0.70 = 35.0
    assert abs(results[0].signal.size_usdc - 35.0) < 0.5


def test_gate_skips_win_prob_when_flag_disabled() -> None:
    """Flag=off → win_probability=1.0 → stake = 1000 × 0.05 × 1.0 = $50 (A-grade)."""
    # yp=0.65: anchor=0.70 → BUY_YES, win_prob=0.70 >= 0.55 ✓, price=0.65 in [0.60, 0.85] ✓
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.70, conf="A")))
    gate.config = GateConfig(
        probability_weighted=False,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
        max_single_bet_usdc=200.0,
        max_bet_pct=0.20,
    )
    results = gate.run([_market(yp=0.65)])
    assert results[0].signal is not None
    # Expected: 1000 × 0.05 × 1.0 = 50.0
    assert abs(results[0].signal.size_usdc - 50.0) < 0.5


def test_gate_buy_no_uses_inverse_prob() -> None:
    """BUY_NO, anchor=0.20, flag=on → win_prob=0.80 → stake = 1000 × 0.05 × 0.80 = $40."""
    # anchor=0.20 → BUY_NO; effective_price = 1 - yes_price.
    # yp=0.25 → effective BUY_NO price = 0.75 in [0.60, 0.85] ✓
    # win_prob = effective_win_prob(0.20, "BUY_NO") = 0.80 >= 0.55 ✓
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.20, conf="A")))
    gate.config = GateConfig(
        probability_weighted=True,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
        max_single_bet_usdc=200.0,
        max_bet_pct=0.20,
    )
    results = gate.run([_market(yp=0.25)])
    assert results[0].signal is not None
    assert results[0].signal.direction == "BUY_NO"
    # win_prob = effective_win_prob(0.20, "BUY_NO") = 0.80
    # stake = 1000 × 0.05 × 0.80 = 40.0
    assert abs(results[0].signal.size_usdc - 40.0) < 0.5


# --- SPEC-017: directional gate tests ---


def test_gate_directional_enters_when_favorite_and_price_in_range() -> None:
    """anchor=0.65, win_prob=0.65 >= 0.55 ✓, yes_price=0.70 in [0.60, 0.85] ✓ → signal."""
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.65, conf="B")))
    results = gate.run([_market(yp=0.70)])
    assert results[0].signal is not None
    assert results[0].signal.direction == "BUY_YES"


def test_gate_directional_skips_with_below_fav_prob_when_anchor_too_low() -> None:
    """anchor=0.52, win_prob=0.52 < min_fav_prob=0.55 → below_fav_prob skip."""
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.52, conf="B")))
    results = gate.run([_market(yp=0.70)])
    assert results[0].signal is None
    assert results[0].skipped_reason == "below_fav_prob"


def test_gate_directional_skips_with_price_out_of_range_when_effective_price_above_max() -> None:
    """anchor=0.70, win_prob=0.70 >= 0.55 ✓, yes_price=0.88 > max_entry_price=0.85 → price_out_of_range."""
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.70, conf="B")))
    results = gate.run([_market(yp=0.88)])
    assert results[0].signal is None
    assert results[0].skipped_reason == "price_out_of_range"
