"""Resolved exit rule — Polymarket maç sonu fiyat yapışması (≤3¢ / ≥97¢).

Eski davranış: maç bitince fiyat 0.00/1.00'a giderdi → graduated_sl tetiklenir,
exit_reason="graduated_sl" yanıltıcı kayıt. Resolved rule ayrı reason ile bunu
düzeltir + monitor dispatch'inde tüm diğer kurallardan ÖNCE çalışır.

2026-05-26 zakharo-muchova bug: WS thin-book transient current_price=0.01 tek
tick'te resolved tetikledi → $19.29 yanlış exit (market closed=False, prices_YES=0.49).
Fix: extreme fiyatın resolved sayılması için EITHER match_ended=True OR
consecutive_down_cycles ≥ MIN_SUSTAINED_TICKS.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.models.enums import ExitReason
from src.models.position import Position
from src.strategy.exit import resolved
from src.strategy.exit.monitor import evaluate


def _pos(**over) -> Position:
    base = dict(
        condition_id="c", token_id="t", direction="BUY_YES",
        entry_price=0.40, size_usdc=40, shares=100,
        current_price=0.40, anchor_probability=0.55,
        confidence="B", sport_tag="tennis_atp",
    )
    base.update(over)
    return Position(**base)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── zakharo regression: transient extreme MUST NOT fire ────────────────────────


def test_resolved_does_not_fire_on_transient_low_price_without_ended_flag() -> None:
    """zakharo bug: current_price=0.01 transient, match_ended=False, tek tick → resolved YANGINDAN OLMAZ."""
    p = _pos(
        current_price=0.01,
        match_ended=False,
        consecutive_down_cycles=1,  # tek tick (transient)
        previous_cycle_price=0.28,
    )
    sig = resolved.check(p)
    assert sig is None, "resolved transient single-tick extreme'de ateşlenmemeli"


def test_resolved_does_not_fire_on_transient_high_price_without_ended_flag() -> None:
    """Won-tarafta single-tick spike (0.99) + previous_cycle 0.50 → resolved fire ETMEZ."""
    p = _pos(
        current_price=0.99,
        match_ended=False,
        consecutive_down_cycles=0,
        previous_cycle_price=0.50,
    )
    sig = resolved.check(p)
    assert sig is None, "won-tarafta tek tick spike resolved sayılmamalı"


# ── legitimate fire paths ─────────────────────────────────────────────────────


def test_resolved_fires_when_match_ended_and_price_extreme_low() -> None:
    """match_ended=True + price=0.005 → resolved lost (short-circuit)."""
    p = _pos(
        current_price=0.005,
        match_ended=True,
        consecutive_down_cycles=0,  # flag varken sustained gerek yok
    )
    sig = resolved.check(p)
    assert sig is not None
    assert sig.sell_pct == 1.0
    assert "lost" in sig.detail
    assert "match_ended" in sig.detail


def test_resolved_fires_when_match_ended_and_price_extreme_high() -> None:
    """match_ended=True + price=0.98 → resolved won (short-circuit)."""
    p = _pos(current_price=0.98, match_ended=True)
    sig = resolved.check(p)
    assert sig is not None
    assert "won" in sig.detail
    assert "match_ended" in sig.detail


def test_resolved_fires_after_sustained_low_price() -> None:
    """match_ended=False ama consecutive_down_cycles=3 + price=0.01 → resolved lost."""
    p = _pos(
        current_price=0.01,
        match_ended=False,
        consecutive_down_cycles=3,  # sustained
    )
    sig = resolved.check(p)
    assert sig is not None
    assert "lost" in sig.detail
    assert "sustained" in sig.detail


def test_resolved_fires_at_3_cents_when_sustained() -> None:
    """current_price=0.03 boundary + sustained → resolved lost."""
    p = _pos(current_price=0.03, consecutive_down_cycles=3)
    sig = resolved.check(p)
    assert sig is not None
    assert "lost" in sig.detail


def test_resolved_fires_when_won_side_previous_cycle_also_high() -> None:
    """Won-tarafta previous_cycle_price ≥ WON_THRESHOLD → resolved won (proxy for sustained)."""
    p = _pos(
        current_price=0.98,
        match_ended=False,
        previous_cycle_price=0.97,  # geçen tick de extreme high
    )
    sig = resolved.check(p)
    assert sig is not None
    assert "won" in sig.detail


# ── normal range stays None ───────────────────────────────────────────────────


def test_resolved_returns_none_in_normal_range() -> None:
    """0.03 < price < 0.97 → None (normal trading range)."""
    for price in [0.04, 0.20, 0.50, 0.80, 0.96]:
        p = _pos(current_price=price, consecutive_down_cycles=10, match_ended=True)
        assert resolved.check(p) is None, f"expected None at price={price}"


def test_resolved_returns_none_below_threshold_until_sustained() -> None:
    """price=0.01 sustained_ticks 0/1/2 → None; ticks 3 → fire."""
    for ticks in [0, 1, 2]:
        p = _pos(current_price=0.01, consecutive_down_cycles=ticks)
        assert resolved.check(p) is None, f"resolved tick={ticks}'de ateşlenmemeli"


# ── monitor integration: resolved beats all other rules ──────────────────────


def test_monitor_prefers_resolved_over_graduated_sl_when_sustained() -> None:
    """Lost-resolved (0.01) + sustained ticks → exit_reason=RESOLVED, NOT GRADUATED_SL."""
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    p = _pos(
        current_price=0.01, entry_price=0.40, match_start_iso=_iso(start),
        consecutive_down_cycles=3,
    )
    r = evaluate(p)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.RESOLVED
    assert "lost" in r.exit_signal.detail


def test_monitor_prefers_resolved_over_near_resolve_when_match_ended() -> None:
    """Won-resolved (0.98) + match_ended → exit_reason=RESOLVED, NOT NEAR_RESOLVE."""
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    p = _pos(
        current_price=0.98, entry_price=0.40, match_start_iso=_iso(start),
        match_ended=True,
    )
    r = evaluate(p)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.RESOLVED
    assert "won" in r.exit_signal.detail


def test_monitor_does_not_resolve_on_transient_then_falls_to_other_rule() -> None:
    """zakharo regression at monitor level: tek tick 0.01 → RESOLVED ateşlenmemeli."""
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    p = _pos(
        current_price=0.01, entry_price=0.28, match_start_iso=_iso(start),
        match_ended=False,
        consecutive_down_cycles=1,  # transient
        previous_cycle_price=0.28,
    )
    r = evaluate(p)
    # Burada başka bir kural (graduated_sl/stop_loss) tetikleyebilir ama
    # ASLA RESOLVED olmamalı — bu testin asıl iddiası.
    if r.exit_signal is not None:
        assert r.exit_signal.reason != ExitReason.RESOLVED, (
            "transient single-tick extreme RESOLVED tetiklememeli (zakharo regression)"
        )
