"""Resolved exit rule — Polymarket maç sonu fiyat yapışması (≤3¢ / ≥97¢).

Eski davranış: maç bitince fiyat 0.00/1.00'a giderdi → graduated_sl tetiklenir,
exit_reason="graduated_sl" yanıltıcı kayıt. Resolved rule ayrı reason ile bunu
düzeltir + monitor dispatch'inde tüm diğer kurallardan ÖNCE çalışır.
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


# ── resolved.check (pure function) ────────────────────────────────────────────


def test_resolved_triggers_at_3_cents_or_below() -> None:
    """current_price ≤ 0.03 → ResolvedSignal lost, full exit."""
    p = _pos(current_price=0.03)
    sig = resolved.check(p)
    assert sig is not None
    assert sig.sell_pct == 1.0
    assert "lost" in sig.detail

    p2 = _pos(current_price=0.01)
    sig2 = resolved.check(p2)
    assert sig2 is not None
    assert "lost" in sig2.detail


def test_resolved_triggers_at_97_cents_or_above() -> None:
    """current_price ≥ 0.97 → ResolvedSignal won, full exit."""
    p = _pos(current_price=0.97)
    sig = resolved.check(p)
    assert sig is not None
    assert sig.sell_pct == 1.0
    assert "won" in sig.detail

    p2 = _pos(current_price=0.99)
    sig2 = resolved.check(p2)
    assert sig2 is not None
    assert "won" in sig2.detail


def test_resolved_returns_none_in_normal_range() -> None:
    """0.03 < price < 0.97 → None (normal trading range)."""
    for price in [0.04, 0.20, 0.50, 0.80, 0.96]:
        p = _pos(current_price=price)
        assert resolved.check(p) is None, f"expected None at price={price}"


# ── monitor integration: resolved beats all other rules ──────────────────────


def test_monitor_prefers_resolved_over_graduated_sl() -> None:
    """Lost-resolved (0.01) + match elapsed > 0 → exit_reason=RESOLVED, NOT GRADUATED_SL."""
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    p = _pos(current_price=0.01, entry_price=0.40, match_start_iso=_iso(start))
    r = evaluate(p)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.RESOLVED
    assert "lost" in r.exit_signal.detail


def test_monitor_prefers_resolved_over_near_resolve() -> None:
    """Won-resolved (0.98) → exit_reason=RESOLVED, NOT NEAR_RESOLVE."""
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    p = _pos(current_price=0.98, entry_price=0.40, match_start_iso=_iso(start))
    r = evaluate(p)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.RESOLVED
    assert "won" in r.exit_signal.detail


def test_monitor_prefers_resolved_over_stop_loss() -> None:
    """Lost-resolved (0.02) + flat SL would also fire → RESOLVED wins (highest priority)."""
    p = _pos(current_price=0.02, entry_price=0.40)  # -95% pnl
    r = evaluate(p)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.RESOLVED
