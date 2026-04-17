"""Catastrophic watch (K5) testleri (SPEC-004 Adım 3)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.models.position import Position
from src.strategy.exit.catastrophic_watch import check, tick


_TRIGGER = 0.25
_DROP_PCT = 0.10
_CANCEL = 0.50


def _make(price: float = 0.60, sport: str = "nhl") -> Position:
    return Position(
        condition_id="c", token_id="t", direction="BUY_YES",
        entry_price=0.60, size_usdc=50, shares=80,
        current_price=price, anchor_probability=0.55,
        confidence="A", sport_tag=sport,
    )


# ── tick: watch tetikleme ──

def test_catastrophic_watch_trigger_below_025() -> None:
    pos = _make(price=0.22)
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)
    assert pos.catastrophic_watch is True
    assert pos.catastrophic_recovery_peak == 0.22


def test_catastrophic_watch_not_triggered_above_025() -> None:
    pos = _make(price=0.30)
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)
    assert pos.catastrophic_watch is False


# ── tick: recovery peak tracking ──

def test_catastrophic_watch_tracks_recovery_peak() -> None:
    pos = _make(price=0.22)
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)  # watch aktif
    pos.current_price = 0.30
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)  # peak = 0.30
    assert pos.catastrophic_recovery_peak == 0.30
    pos.current_price = 0.35
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)  # peak = 0.35
    assert pos.catastrophic_recovery_peak == 0.35


# ── tick: comeback iptal ──

def test_catastrophic_watch_genuine_comeback_cancel() -> None:
    pos = _make(price=0.22)
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)
    assert pos.catastrophic_watch is True
    pos.current_price = 0.55
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)
    assert pos.catastrophic_watch is False
    assert pos.catastrophic_recovery_peak == 0.0


# ── check: bounce + drop = exit ──

def test_catastrophic_watch_bounce_then_drop_exit() -> None:
    pos = _make(price=0.22)
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)  # watch on
    pos.current_price = 0.35
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)  # peak = 0.35
    pos.current_price = 0.30  # drop = 14% > 10%
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)
    sig = check(pos, trigger=_TRIGGER, drop_pct=_DROP_PCT)
    assert sig is not None
    assert sig.reason == ExitReason.CATASTROPHIC_BOUNCE
    assert "K5" in sig.detail


def test_catastrophic_watch_no_bounce_no_exit() -> None:
    pos = _make(price=0.22)
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)
    # Peak henüz trigger'ın altında — bounce olmadı
    sig = check(pos, trigger=_TRIGGER, drop_pct=_DROP_PCT)
    assert sig is None


# ── Tüm sporlar ──

def test_catastrophic_watch_all_sports() -> None:
    pos = _make(price=0.22, sport="mlb")
    tick(pos, trigger=_TRIGGER, cancel=_CANCEL)
    assert pos.catastrophic_watch is True  # mlb'de de çalışır
