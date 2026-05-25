"""EntryProcessor.process_signals — sport-agnostic portfolio guard tests.

Stage 4 PLAN-TENNIS-001: tennis paper entry pipeline'ı için yazılan public
API. Bookmaker enricher ÇALIŞMAZ; yalnızca 8 portfolio guard'ı:
  1. circuit_breaker.halt_active
  2. cooldown.active
  3. max_positions reached
  4. event_count_per_event_cap
  5. blacklisted
  6. manipulation_high_risk
  7. entry_price_cap
  8. exposure_cap_reached

Tests use real PortfolioManager + Blacklist + CooldownTracker + CircuitBreaker
so state transitions are exercised end-to-end. Executor + loggers are mocked.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.domain.guards.blacklist import Blacklist
from src.domain.guards.manipulation import ManipulationCheck
from src.domain.portfolio.manager import PortfolioManager
from src.domain.risk.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from src.domain.risk.cooldown import CooldownTracker
from src.models.market import MarketData
from src.models.signal import Signal
from src.orchestration.entry_processor import EntryProcessor
from src.strategy.entry.gate import EntryGate, GateConfig


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_market(
    *,
    cid: str = "0xCID",
    event_id: str | None = "evt-1",
    yes_price: float = 0.50,
    slug: str = "tennis-sinner-alcaraz-set1",
) -> MarketData:
    return MarketData(
        condition_id=cid,
        slug=slug,
        question="Set 1 Winner: Sinner vs Alcaraz",
        yes_token_id="y-tok",
        no_token_id="n-tok",
        yes_price=yes_price,
        no_price=round(1.0 - yes_price, 4),
        liquidity=20_000.0,
        volume_24h=5_000.0,
        end_date_iso="2026-05-20T22:00:00Z",
        match_start_iso="2026-05-20T18:00:00Z",
        event_id=event_id,
        sport_tag="tennis",
        sports_market_type="tennis_first_set_winner",
    )


def _make_signal(
    *,
    cid: str = "0xCID",
    direction: str = "BUY_YES",
    market_price: float = 0.50,
    size_usdc: float = 25.0,
    event_id: str = "evt-1",
    anchor_probability: float = 0.60,
) -> Signal:
    return Signal(
        condition_id=cid,
        direction=direction,
        market_price=market_price,
        anchor_probability=anchor_probability,
        edge=0.10,
        bookmaker_prob=0.0,
        num_bookmakers=0,
        has_sharp=False,
        confidence="A",
        entry_reason="tennis",
        size_usdc=size_usdc,
        sport_tag="tennis",
        event_id=event_id,
    )


def _safe_manip(question: str, liquidity: float) -> ManipulationCheck:
    return ManipulationCheck(safe=True, risk_level="low", flags=[], recommendation="")


def _build_deps(
    *,
    portfolio: PortfolioManager | None = None,
    blacklist: Blacklist | None = None,
    cooldown: CooldownTracker | None = None,
    breaker: CircuitBreaker | None = None,
    manip_checker=None,
    max_positions: int = 50,
    max_positions_per_event: int = 2,
    max_exposure_pct: float = 0.60,
    hard_cap_overflow_pct: float = 0.02,
    min_entry_size_pct: float = 0.02,
    max_entry_price: float = 0.88,
):
    """Build a deps SimpleNamespace matching what EntryProcessor expects.

    Uses real PortfolioManager/Blacklist/Cooldown/CircuitBreaker so state
    transitions are exercised. Executor/loggers/bot_status_writer mocked.
    """
    portfolio = portfolio or PortfolioManager(initial_bankroll=1000.0)
    blacklist = blacklist or Blacklist()
    cooldown = cooldown or CooldownTracker(trigger_threshold=999)  # never trip by default
    breaker = breaker or CircuitBreaker(config=CircuitBreakerConfig(enabled=False))
    manip = manip_checker or _safe_manip

    gate_cfg = GateConfig(
        max_positions=max_positions,
        max_positions_per_event=max_positions_per_event,
        max_exposure_pct=max_exposure_pct,
        hard_cap_overflow_pct=hard_cap_overflow_pct,
        min_entry_size_pct=min_entry_size_pct,
        max_entry_price=max_entry_price,
    )
    gate = EntryGate(
        config=gate_cfg,
        portfolio=portfolio,
        circuit_breaker=breaker,
        cooldown=cooldown,
        blacklist=blacklist,
        odds_enricher=lambda m: None,
        manipulation_checker=manip,
    )

    executor = MagicMock()
    executor.place_order.return_value = {"status": "simulated", "price": 0.50}

    return SimpleNamespace(
        state=SimpleNamespace(
            config=SimpleNamespace(mode=SimpleNamespace(value="paper")),
            portfolio=portfolio,
        ),
        gate=gate,
        executor=executor,
        trade_logger=MagicMock(),
        equity_logger=MagicMock(),
        skipped_logger=MagicMock(),
        bot_status_writer=MagicMock(),
        price_feed=None,
        # Unused by process_signals but referenced elsewhere — leave as None
        scanner=None,
        stock=None,
        cooldown=cooldown,
        odds_client=None,
    )


# ── Tests: happy path ────────────────────────────────────────────────────────


def test_process_signals_creates_position_for_approved_signal() -> None:
    """One market + one sized signal → one position in portfolio + trade logged."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    deps = _build_deps(portfolio=portfolio)

    processor = EntryProcessor(deps)
    processor.process_signals([_make_market()], [_make_signal()])

    assert portfolio.count() == 1
    assert "0xCID" in portfolio.positions
    pos = portfolio.positions["0xCID"]
    assert pos.entry_reason == "tennis"
    assert pos.confidence == "A"
    assert pos.size_usdc == pytest.approx(25.0, abs=0.01)
    deps.trade_logger.log.assert_called_once()
    record = deps.trade_logger.log.call_args[0][0]
    assert record.entry_reason == "tennis"


# ── Tests: global guards (batch-level) ────────────────────────────────────────


def test_process_signals_skips_when_circuit_breaker_active() -> None:
    """Active circuit breaker → no positions opened, all markets skip-logged."""
    breaker = CircuitBreaker(
        config=CircuitBreakerConfig(enabled=True, daily_max_loss_pct=-0.01),
    )
    # Force breaker to trigger via accumulated daily loss
    breaker.state.daily_realized_pnl_pct = -0.50

    portfolio = PortfolioManager(initial_bankroll=1000.0)
    deps = _build_deps(portfolio=portfolio, breaker=breaker)

    EntryProcessor(deps).process_signals([_make_market()], [_make_signal()])

    assert portfolio.count() == 0
    deps.executor.place_order.assert_not_called()
    # circuit_breaker skip logged
    calls = deps.skipped_logger.log.call_args_list
    assert any(c[0][0].skip_reason == "circuit_breaker" for c in calls)


def test_process_signals_skips_when_cooldown_active() -> None:
    """Active cooldown → no positions opened, all markets skip-logged."""
    cooldown = CooldownTracker(trigger_threshold=1, cooldown_cycles=3)
    cooldown.record_outcome(win=False)  # triggers cooldown_remaining=3
    assert cooldown.state.cooldown_remaining > 0

    portfolio = PortfolioManager(initial_bankroll=1000.0)
    deps = _build_deps(portfolio=portfolio, cooldown=cooldown)

    EntryProcessor(deps).process_signals([_make_market()], [_make_signal()])

    assert portfolio.count() == 0
    deps.executor.place_order.assert_not_called()
    calls = deps.skipped_logger.log.call_args_list
    assert any(c[0][0].skip_reason == "cooldown_active" for c in calls)


def test_process_signals_respects_max_positions_cap() -> None:
    """If portfolio.count >= max_positions → batch-level skip."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    # Pre-fill portfolio so count() == max_positions
    from src.models.position import Position
    for i in range(2):
        portfolio.add_position(Position(
            condition_id=f"existing-{i}",
            token_id=f"t-{i}", direction="BUY_YES",
            entry_price=0.5, size_usdc=10.0, shares=20.0,
            current_price=0.5, anchor_probability=0.5,
        ))

    deps = _build_deps(portfolio=portfolio, max_positions=2)
    pre_count = portfolio.count()

    EntryProcessor(deps).process_signals([_make_market()], [_make_signal()])

    assert portfolio.count() == pre_count
    deps.executor.place_order.assert_not_called()
    calls = deps.skipped_logger.log.call_args_list
    assert any(c[0][0].skip_reason == "max_positions_reached" for c in calls)


# ── Tests: per-signal guards ──────────────────────────────────────────────────


def test_process_signals_respects_max_positions_per_event_cap() -> None:
    """Two same-event signals with cap=1 → only 1 opens."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    deps = _build_deps(portfolio=portfolio, max_positions_per_event=1)

    m1 = _make_market(cid="0xA", event_id="evt-shared")
    m2 = _make_market(cid="0xB", event_id="evt-shared")
    s1 = _make_signal(cid="0xA", event_id="evt-shared")
    s2 = _make_signal(cid="0xB", event_id="evt-shared")

    EntryProcessor(deps).process_signals([m1, m2], [s1, s2])

    assert portfolio.count_event("evt-shared") == 1
    calls = deps.skipped_logger.log.call_args_list
    assert any(c[0][0].skip_reason == "event_count_per_event_cap" for c in calls)


def test_b_confidence_blocks_same_market_type_per_event() -> None:
    """B-only same_market_type guard: 2nd B signal for same (event, market_type) skipped.

    aguilar-shelton case (2026-05-26): bot opened set_totals 3.5 AND 4.5 on the
    same match (both B confidence). Model wrong -> BOTH lost (-$31 chain).
    B (26% win rate) compounds chain losses on correlated multi-line bets.
    A (77% win rate) compounds wins -> guard MUST NOT apply to A.
    """
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    # Pre-fill: 1 open B set_totals position on event "evt-shared"
    from src.models.position import Position
    portfolio.add_position(Position(
        condition_id="0xEXISTING_B",
        token_id="t-existing", direction="BUY_YES",
        entry_price=0.50, size_usdc=10.0, shares=20.0,
        current_price=0.50, anchor_probability=0.55,
        event_id="evt-shared",
        sports_market_type="tennis_set_totals",
        confidence="B",
    ))

    deps = _build_deps(portfolio=portfolio, max_positions_per_event=10)

    # Try to add a second B set_totals signal on the SAME event/market_type -> SKIPPED
    m_b = _make_market(cid="0xNEW_B", event_id="evt-shared", slug="atp-x-set-totals-4pt5")
    m_b.sports_market_type = "tennis_set_totals"
    s_b = _make_signal(cid="0xNEW_B", event_id="evt-shared")
    s_b = s_b.model_copy(update={"confidence": "B"})

    EntryProcessor(deps).process_signals([m_b], [s_b])

    # Second B was blocked
    assert "0xNEW_B" not in portfolio.positions
    calls = deps.skipped_logger.log.call_args_list
    assert any(
        c[0][0].skip_reason == "same_market_type_per_event_b" for c in calls
    ), f"expected same_market_type_per_event_b skip; got {[c[0][0].skip_reason for c in calls]}"

    # Now: an A signal for the SAME event/market_type -> ALLOWED (A unrestricted)
    portfolio_a = PortfolioManager(initial_bankroll=1000.0)
    portfolio_a.add_position(Position(
        condition_id="0xEXISTING_A",
        token_id="t-existing-a", direction="BUY_YES",
        entry_price=0.50, size_usdc=15.0, shares=30.0,
        current_price=0.50, anchor_probability=0.60,
        event_id="evt-A-shared",
        sports_market_type="tennis_set_totals",
        confidence="A",
    ))
    deps_a = _build_deps(portfolio=portfolio_a, max_positions_per_event=10)

    m_a = _make_market(cid="0xNEW_A", event_id="evt-A-shared", slug="atp-x-set-totals-4pt5")
    m_a.sports_market_type = "tennis_set_totals"
    s_a = _make_signal(cid="0xNEW_A", event_id="evt-A-shared")  # confidence="A" by default

    EntryProcessor(deps_a).process_signals([m_a], [s_a])

    # A was opened (no guard for A)
    assert "0xNEW_A" in portfolio_a.positions
    a_skips = [c[0][0].skip_reason for c in deps_a.skipped_logger.log.call_args_list]
    assert "same_market_type_per_event_b" not in a_skips, (
        f"A must not be blocked by B-only guard; skips: {a_skips}"
    )


def test_process_signals_skips_blacklisted_market() -> None:
    """Blacklisted condition_id → signal skipped, others go through."""
    blacklist = Blacklist()
    blacklist.add_condition("0xBLACK")

    portfolio = PortfolioManager(initial_bankroll=1000.0)
    deps = _build_deps(portfolio=portfolio, blacklist=blacklist)

    m_ok = _make_market(cid="0xOK", event_id="evt-1")
    m_black = _make_market(cid="0xBLACK", event_id="evt-2")
    s_ok = _make_signal(cid="0xOK", event_id="evt-1")
    s_black = _make_signal(cid="0xBLACK", event_id="evt-2")

    EntryProcessor(deps).process_signals([m_ok, m_black], [s_ok, s_black])

    assert "0xOK" in portfolio.positions
    assert "0xBLACK" not in portfolio.positions
    calls = deps.skipped_logger.log.call_args_list
    assert any(c[0][0].skip_reason == "blacklisted" for c in calls)


def test_process_signals_skips_when_entry_price_above_cap() -> None:
    """Signal market_price → effective_price >= max_entry_price → skip."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    deps = _build_deps(portfolio=portfolio, max_entry_price=0.70)

    # market_price=0.85, BUY_YES → effective_price=0.85 >= 0.70 → skip
    market = _make_market(yes_price=0.85)
    signal = _make_signal(market_price=0.85)

    EntryProcessor(deps).process_signals([market], [signal])

    assert portfolio.count() == 0
    deps.executor.place_order.assert_not_called()
    calls = deps.skipped_logger.log.call_args_list
    assert any(c[0][0].skip_reason == "entry_price_cap" for c in calls)


def test_process_signals_skips_when_exposure_cap_exceeded() -> None:
    """Pre-filled portfolio at exposure cap → next signal exposure_cap_reached."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    # Pre-fill: invest $500 of $1000 bankroll. Total portfolio = 500 + 500 = 1000.
    # max_exposure_pct=0.40 + overflow=0 → hard_cap = $400; invested $500 > $400.
    from src.models.position import Position
    portfolio.add_position(Position(
        condition_id="existing",
        token_id="t-x", direction="BUY_YES",
        entry_price=0.5, size_usdc=500.0, shares=1000.0,
        current_price=0.5, anchor_probability=0.5,
    ))
    deps = _build_deps(
        portfolio=portfolio,
        max_exposure_pct=0.40, hard_cap_overflow_pct=0.0,
        min_entry_size_pct=0.05,
    )

    EntryProcessor(deps).process_signals([_make_market()], [_make_signal()])

    # No new position opened (still just the pre-filled one)
    assert portfolio.count() == 1
    assert "0xCID" not in portfolio.positions
    calls = deps.skipped_logger.log.call_args_list
    assert any(c[0][0].skip_reason == "exposure_cap_reached" for c in calls)


def test_process_signals_skips_manipulation_high_risk() -> None:
    """High-risk manipulation check → signal skipped."""
    def high_risk(question: str, liquidity: float) -> ManipulationCheck:
        return ManipulationCheck(
            safe=False, risk_level="high",
            flags=["LOW_LIQUIDITY"], recommendation="SKIP",
        )

    portfolio = PortfolioManager(initial_bankroll=1000.0)
    deps = _build_deps(portfolio=portfolio, manip_checker=high_risk)

    EntryProcessor(deps).process_signals([_make_market()], [_make_signal()])

    assert portfolio.count() == 0
    calls = deps.skipped_logger.log.call_args_list
    assert any(c[0][0].skip_reason == "manipulation_high_risk" for c in calls)


# ── Misc ──────────────────────────────────────────────────────────────────────


def test_process_signals_empty_list_is_noop() -> None:
    """Empty inputs → no errors, no calls."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    deps = _build_deps(portfolio=portfolio)

    EntryProcessor(deps).process_signals([], [])

    assert portfolio.count() == 0
    deps.executor.place_order.assert_not_called()
    deps.skipped_logger.log.assert_not_called()


def test_process_signals_mismatched_lengths_raises() -> None:
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    deps = _build_deps(portfolio=portfolio)

    with pytest.raises(ValueError, match="length mismatch"):
        EntryProcessor(deps).process_signals(
            [_make_market(cid="a"), _make_market(cid="b")],
            [_make_signal(cid="a")],
        )


def test_run_heavy_behavior_unchanged_after_refactor() -> None:
    """Sanity: run_heavy / process_markets path still works (gate-based flow).

    Builds a minimal deps with a gate that returns no signals → expect no
    positions opened. We're confirming the new process_signals didn't break
    the existing main-bot flow.
    """
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    deps = _build_deps(portfolio=portfolio)

    # Build minimal scanner + stock for run_heavy path
    deps.scanner = MagicMock()
    deps.scanner.scan.return_value = []
    deps.stock = MagicMock()
    deps.stock.config = SimpleNamespace(jit_batch_multiplier=3)
    deps.stock.refresh_from_scan = MagicMock()
    deps.stock.evict_expired = MagicMock()
    deps.stock.save = MagicMock()
    deps.stock.top_n_by_match_start = MagicMock(return_value=[])
    deps.stock.has = MagicMock(return_value=False)

    EntryProcessor(deps).run_heavy()

    assert portfolio.count() == 0
    deps.executor.place_order.assert_not_called()
