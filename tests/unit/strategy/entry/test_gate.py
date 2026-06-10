"""entry/gate.py için birim testler."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

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
    config = kwargs.get("config") or GateConfig()
    return EntryGate(
        config=config,
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


def test_event_guard_blocks_third_position_per_event() -> None:
    """SPEC-J/K + 2026-05-22: max_positions_per_event=3. İlk 3 kabul, 4. blok."""
    p = PortfolioManager(initial_bankroll=1000.0)
    for cid in ("prev_c1", "prev_c2", "prev_c3"):
        p.add_position(Position(
            condition_id=cid, token_id=f"t_{cid}", direction="BUY_YES",
            entry_price=0.4, size_usdc=40, shares=100, current_price=0.4,
            anchor_probability=0.55, event_id="e1",
        ))
    gate = _make_gate(portfolio=p)
    # Aynı event_id=e1 DÖRDÜNCÜ giriş → bloklanır (cap=3)
    results = gate.run([_market(cid="c4", event="e1")])
    assert results[0].signal is None
    assert "event_already_held" in results[0].skipped_reason
    assert "3/3" in results[0].skip_detail


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
    # SPEC-U: market default moneyline (sports_market_type="") → non-bimodal B=$30; medium × 0.5 = $15
    assert results[0].signal.size_usdc == 15.0


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


@pytest.mark.skip(reason="CB removed 2026-05-23 SPEC-T")
def test_circuit_breaker_halts_all() -> None:
    cb = CircuitBreaker()
    cb.record_exit(pnl_usd=-100, portfolio_value=1000)
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
    gate.config = GateConfig(max_positions=5, max_exposure_pct=0.50)
    results = gate.run([_market(cid="new", event="enew")])
    assert results[0].signal is None
    assert results[0].skipped_reason == "max_positions_reached"


def test_size_below_min_skips_when_manipulation_halves_C_tier_floor() -> None:
    # SPEC-P: sabit-tier ($30 B, $50 A) zaten Polymarket min $5 üstünde.
    # Sadece fixed_bet_usdc dict'i $5 altı tutarsa skip oluşur (edge case).
    p = PortfolioManager(initial_bankroll=1000.0)
    gate = _make_gate(portfolio=p)
    # Override: B tier $4 → < $5 polymarket min → skip
    gate.config = GateConfig(
        max_exposure_pct=0.50,
        fixed_bet_usdc={"A": 15.0, "B": 4.0},
    )
    results = gate.run([_market()])
    assert results[0].signal is None
    assert "size_below_min" in results[0].skipped_reason


def test_entry_price_cap_blocks_high_favorite() -> None:
    # Consensus 0.90'da sinyal uretir (min_price 0.60) ama gate 0.88 cap ile reddeder.
    # SPEC-Z13 (2026-06-03): anchor >= market gerekli (model_edge >= 0) yoksa
    # consensus iptal. anchor 0.92, market yes 0.90 → model_edge=+0.02 → consensus
    # gecer, sonra 0.88 cap reddeder.
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.92, conf="A")))
    results = gate.run([_market(yp=0.90)])
    assert results[0].signal is None
    assert results[0].skipped_reason == "entry_price_cap"


def test_entry_price_cap_allows_under_threshold() -> None:
    # 2026-06-07 (SPEC-Z23): cap 0.80 → 0.75 + 0.01 buffer → effective cap 0.74.
    # 0.70 < 0.74 → geçer.
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.80, conf="A")))
    results = gate.run([_market(yp=0.70)])
    assert results[0].signal is not None


# --- PLAN-001: Anti-edge guard (2026-06-01) ---

def test_anti_edge_high_price_skips_cobolli_like_trade() -> None:
    """PLAN-001 Rule A: paid >= 0.80 VE anti_edge > 0 → SKIP.

    Cobolli senaryosu: market 0.86, model 0.63 → BUY_YES, anti_edge 0.23 > 0.
    entry_price_cap'i geçici olarak gevşetip Rule A'yı izole test ediyoruz.

    SPEC-Z13 (2026-06-03): consensus min_model_edge=0.0 default → anchor<market
    olunca consensus None doner, anti_edge guard ulasilamaz. Defense-in-depth
    olarak anti_edge guard hala kodda; test consensus_min_model_edge=-1.0 ile
    Z13 bypass eder ki Rule A yolu test edilebilsin.
    """
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.63, conf="A")))
    gate.config = GateConfig(max_entry_price=0.95, consensus_min_model_edge=-1.0)
    results = gate.run([_market(yp=0.86)])
    assert results[0].signal is None
    assert results[0].skipped_reason == "anti_edge_high_price"
    assert "anti_edge=+0.230" in results[0].skip_detail


def test_anti_edge_absolute_skips_alkaya_like_trade() -> None:
    """PLAN-001 Rule B: anti_edge > 0.15 → SKIP (fiyat fark etmez).

    Alkaya senaryosu: market 0.72, model 0.54 → BUY_YES, anti_edge 0.18 > 0.15.
    paid 0.72 < 0.74 (SPEC-Z23 efektif cap) → Rule A/cap tetiklenmez; Rule B yakalar.

    SPEC-Z13 (2026-06-03): consensus_min_model_edge=-1.0 ile Z13 bypass —
    yoksa consensus None doner ve Normal stratejisi BUY_NO uretir (0.54 vs
    0.72 → NO ucuz). Defense-in-depth: anti_edge guard hala kod icinde,
    test'i Z13'i atlatarak Rule B yolunu izole eder.
    """
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.54, conf="A")))
    gate.config = GateConfig(consensus_min_model_edge=-1.0)
    results = gate.run([_market(yp=0.72)])
    assert results[0].signal is None
    assert results[0].skipped_reason == "anti_edge_absolute"
    assert "anti_edge=+0.180" in results[0].skip_detail


def test_anti_edge_does_not_block_when_model_agrees_or_supports() -> None:
    """PLAN-001: anti_edge <= 0 (model 'ucuz aldık' diyor) → giriş geçer.

    Market 0.65, model 0.85 → BUY_YES, anti_edge = -0.20. Hem A hem B kuralı
    tetiklenmez. Consensus stratejisi sinyali üretir (her iki taraf YES favori,
    paid >= consensus.min_price 0.65).
    """
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.85, conf="A")))
    results = gate.run([_market(yp=0.65)])
    assert results[0].signal is not None
    assert results[0].signal.size_usdc > 0


def test_gate_allows_full_size_when_below_cap_even_if_crosses() -> None:
    """SPEC-P: yumuşak cap — exposure < cap iken tam sabit-tier trade alınır.

    initial=$2000, invested=$990 → exposure 49.5% < 50% cap.
    A trade tam $50 girer (default moneyline non-bimodal, SPEC-U).
    """
    p = PortfolioManager(initial_bankroll=2000.0)
    p.add_position(Position(
        condition_id="prev", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=990.0, shares=2475.0, current_price=0.4,
        anchor_probability=0.55, event_id="eprev",
    ))
    gate = _make_gate(portfolio=p, enricher=lambda m: _enrich(_bm(prob=0.60, conf="A")))
    results = gate.run([_market(cid="new", event="enew")])
    assert results[0].signal is not None
    assert results[0].signal.size_usdc == 50.0


def test_gate_skips_when_exposure_at_cap() -> None:
    """SPEC-P: exposure ≥ cap → blok (hangi yüzdeyle geçtiği fark etmez)."""
    p = PortfolioManager(initial_bankroll=2000.0)
    p.add_position(Position(
        condition_id="prev", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=1000.0, shares=2500.0, current_price=0.4,
        anchor_probability=0.55, event_id="eprev",
    ))
    gate = _make_gate(portfolio=p)
    results = gate.run([_market(cid="new", event="enew")])
    assert results[0].signal is None
    assert results[0].skipped_reason == "exposure_cap_reached"


def test_gate_skips_when_exposure_over_cap_after_prior_crossing() -> None:
    """SPEC-P: önceki trade cap'i geçmiş; sonraki trade artık reddedilir."""
    p = PortfolioManager(initial_bankroll=2000.0)
    p.add_position(Position(
        condition_id="prev", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=1050.0, shares=2625.0, current_price=0.4,
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
    """event_already_held → skip_detail event_id + count/cap içerir (SPEC-J/K).
    Cap=3 olduğu için 3 pozisyon eklenir, 4.'sü reddedilir (2026-05-22 cap artırımı)."""
    from src.models.position import Position

    p = PortfolioManager(initial_bankroll=1000.0)
    for cid in ("prev_c1", "prev_c2", "prev_c3"):
        p.add_position(Position(
            condition_id=cid, token_id=f"t_{cid}", direction="BUY_YES",
            entry_price=0.4, size_usdc=40, shares=100, current_price=0.4,
            anchor_probability=0.55, event_id="378836",
        ))
    gate = _make_gate(portfolio=p)
    result = gate._evaluate_one(_market(cid="c4", event="378836"))
    assert result.skipped_reason == "event_already_held"
    assert "event_id=378836" in result.skip_detail
    assert "count=3/3" in result.skip_detail


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
    # bm=0.63, yes=0.60 → raw_edge=0.03 < 0.05 → no signal
    bm = _bm(prob=0.63, conf="B")
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(_market(yp=0.60))
    assert result.skipped_reason == "no_edge"
    assert "edge=0.030" in result.skip_detail
    assert "min=0.05" in result.skip_detail
    assert "bm=0.63" in result.skip_detail
    assert "yes=0.60" in result.skip_detail


def test_evaluate_one_entry_price_cap_sets_skip_detail_price_cap() -> None:
    """entry_price_cap → skip_detail='price=X.XXX, cap=X.XX, buffer=X.XX'.

    SPEC-Z13 (2026-06-03): anchor>=market gerekli → anchor 0.92 vs market 0.90
    → consensus gecer, sonra cap (SPEC-Z23: 0.75-0.01) reddeder.
    """
    bm = _bm(prob=0.92, conf="A")
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(_market(yp=0.90))
    assert result.skipped_reason == "entry_price_cap"
    assert "price=0.900" in result.skip_detail
    assert "cap=0.75" in result.skip_detail
    assert "buffer=0.01" in result.skip_detail


def test_evaluate_one_size_below_min_raw_sets_skip_detail_size_min() -> None:
    """size_below_min (raw adjusted_size < $5 Polymarket min) → normalized reason + detail.

    SPEC-P: sabit-tier dict $5 altı tutarsa skip oluşur (edge case).
    """
    p = PortfolioManager(initial_bankroll=1000.0)
    gate = _make_gate(portfolio=p)
    gate.config = GateConfig(
        max_exposure_pct=0.50,
        fixed_bet_usdc={"A": 15.0, "B": 4.0},  # B < $5
    )
    result = gate._evaluate_one(_market())
    assert result.skipped_reason == "size_below_min"
    assert "size=" in result.skip_detail
    assert "min=" in result.skip_detail
    assert "(" not in result.skipped_reason


def test_evaluate_one_exposure_cap_sets_skip_detail_invested_cap() -> None:
    """SPEC-P: exposure_cap_reached → skip_detail='invested=X.XX, cap=X.XX'."""
    from src.models.position import Position

    p = PortfolioManager(initial_bankroll=2000.0)
    p.add_position(Position(
        condition_id="prev", token_id="t", direction="BUY_YES",
        entry_price=0.4, size_usdc=1000.0, shares=2500.0, current_price=0.4,
        anchor_probability=0.55, event_id="eprev",
    ))
    gate = _make_gate(portfolio=p)
    result = gate._evaluate_one(_market(cid="new", event="enew"))
    assert result.skipped_reason == "exposure_cap_reached"
    assert "invested=" in result.skip_detail
    assert "cap=" in result.skip_detail


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
    gate.config = GateConfig(max_positions=5, max_exposure_pct=0.50)
    results = gate.run([_market(cid="new", event="enew")])
    r = results[0]
    assert r.skipped_reason == "max_positions_reached"
    assert r.skip_detail == "count=5/5"


# ============================================================================
# SPEC-X (2026-05-24): Bimodal entry kapısı testleri — Faz 2A (min floor)
# ============================================================================


def _bimodal_market(
    cid: str = "c_bimodal",
    event: str = "e_bimodal",
    yp: float = 0.04,
    slug: str = "mlb-wsh-atl-2026-05-23-spread-home-3pt5",
    sport_tag: str = "baseball",
    sports_market_type: str = "spreads",
    event_live: bool = False,
) -> MarketData:
    """Bimodal-aday market helper: SPEC-X test'leri için.

    Task 6 (2026-05-24): event_live parametresi LIVE entry yasağı testleri için
    eklendi. Default False — pre-match davranışını korur.
    """
    return MarketData(
        condition_id=cid,
        question="Will home cover the spread?",
        slug=slug,
        yes_token_id="y", no_token_id="n",
        yes_price=yp, no_price=1 - yp,
        liquidity=50_000, volume_24h=10_000, tags=[],
        end_date_iso="2026-05-24T00:00:00Z",
        sport_tag=sport_tag,
        sports_market_type=sports_market_type,
        event_id=event,
        event_live=event_live,
    )


def test_gate_bimodal_market_entry_below_floor_skipped() -> None:
    """Bimodal market'e 0.10 entry (floor 0.20) → bloklanır.

    Consensus disabled (test isolation). Normal BUY_YES @ 0.10, < 0.20 → SKIP.
    """
    market = _bimodal_market(
        slug="mlb-wsh-atl-2026-05-23-spread-home-3pt5",
        yp=0.10,
        sport_tag="baseball",
        sports_market_type="spreads",
    )
    bm = BookmakerProbability(
        probability=0.18, confidence="A",
        bookmaker_prob=0.18, num_bookmakers=29.0, has_sharp=True,
    )
    cfg = GateConfig(consensus_enabled=False)
    gate = _make_gate(enricher=lambda m: _enrich(bm), config=cfg)
    result = gate._evaluate_one(market)
    assert result.signal is None
    assert result.skipped_reason == "bimodal_entry_below_floor"


def test_gate_bimodal_market_entry_at_floor_not_blocked_by_floor() -> None:
    """Sınır: entry_price = 0.20 → floor blokuna takılmaz (strict less-than).

    NOT: Bu test sadece floor kuralının çalışmadığını gösterir — başka kurallar
    signal'i reddedebilir. Burada doğruladığımız tek şey: skipped_reason
    'bimodal_entry_below_floor' DEĞİL.
    """
    market = _bimodal_market(
        slug="mlb-cle-phi-2026-05-23-spread-home-1pt5",
        yp=0.20,
        sport_tag="baseball",
        sports_market_type="spreads",
    )
    bm = BookmakerProbability(
        probability=0.30, confidence="A",
        bookmaker_prob=0.30, num_bookmakers=29.0, has_sharp=True,
    )
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(market)
    assert result.skipped_reason != "bimodal_entry_below_floor"


def test_gate_moneyline_market_low_entry_not_blocked_by_bimodal_floor() -> None:
    """Moneyline 4¢ entry → bimodal floor TETİKLENMEZ (sadece bimodal market'ler için)."""
    market = _bimodal_market(
        cid="c_ml",
        event="e_ml",
        slug="mlb-cle-phi-2026-05-23",  # moneyline (suffix yok)
        yp=0.04,
        sport_tag="baseball",
        sports_market_type="moneyline",
    )
    bm = BookmakerProbability(
        probability=0.59, confidence="A",
        bookmaker_prob=0.59, num_bookmakers=29.0, has_sharp=True,
    )
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(market)
    assert result.skipped_reason != "bimodal_entry_below_floor"


# ============================================================================
# SPEC-X (2026-05-24): Bimodal LIVE entry yasağı testleri — Faz 2B
# ============================================================================


def test_gate_bimodal_market_live_entry_blocked() -> None:
    """Bimodal market LIVE (event_live=True) → bimodal_entry_live."""
    market = _bimodal_market(
        slug="mlb-lad-mil-2026-05-23-spread-away-1pt5",
        yp=0.42,
        sport_tag="baseball",
        sports_market_type="spreads",
        event_live=True,
    )
    bm = BookmakerProbability(
        probability=0.52, confidence="A",
        bookmaker_prob=0.52, num_bookmakers=54.0, has_sharp=True,
    )
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(market)
    assert result.signal is None
    assert result.skipped_reason == "bimodal_entry_live"


def test_gate_bimodal_market_not_live_entry_allowed_by_live_rule() -> None:
    """Bimodal market pre-match (event_live=False) → bimodal_entry_live TETİKLENMEZ."""
    market = _bimodal_market(
        slug="mlb-cle-phi-2026-05-23-spread-home-1pt5",
        yp=0.42,
        sport_tag="baseball",
        sports_market_type="spreads",
        event_live=False,
    )
    bm = BookmakerProbability(
        probability=0.52, confidence="A",
        bookmaker_prob=0.52, num_bookmakers=54.0, has_sharp=True,
    )
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(market)
    assert result.skipped_reason != "bimodal_entry_live"


def test_gate_moneyline_market_live_entry_not_blocked_by_bimodal_live_rule() -> None:
    """Moneyline LIVE → bimodal_entry_live TETİKLENMEZ (sadece bimodal market'ler için)."""
    market = _bimodal_market(
        slug="wnba-por-tor-2026-05-23",
        yp=0.65,
        sport_tag="wnba",
        sports_market_type="moneyline",
        event_live=True,
    )
    bm = BookmakerProbability(
        probability=0.75, confidence="A",
        bookmaker_prob=0.75, num_bookmakers=10.0, has_sharp=True,
    )
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(market)
    assert result.skipped_reason != "bimodal_entry_live"


def test_gate_bimodal_market_event_live_default_treated_as_not_live() -> None:
    """Sınır: event_live default/None → 'canlı değil' kabul, blok yok."""
    market = _bimodal_market(
        slug="mlb-cle-phi-2026-05-23-spread-home-1pt5",
        yp=0.42,
        sport_tag="baseball",
        sports_market_type="spreads",
        # event_live omitted → default False
    )
    bm = BookmakerProbability(
        probability=0.52, confidence="A",
        bookmaker_prob=0.52, num_bookmakers=54.0, has_sharp=True,
    )
    gate = _make_gate(enricher=lambda m: _enrich(bm))
    result = gate._evaluate_one(market)
    assert result.skipped_reason != "bimodal_entry_live"
