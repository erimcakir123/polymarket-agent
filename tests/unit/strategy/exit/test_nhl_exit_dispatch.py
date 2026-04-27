"""Tests for _nhl_exit_dispatch.check_nhl_exit — TDD §3C."""
from __future__ import annotations

import pytest
from types import SimpleNamespace

from src.models.enums import ExitReason
from src.strategy.exit._nhl_exit_dispatch import check_nhl_exit
from src.strategy.exit.nhl_score_exit import NHLExitConfig


def _pos(**kw):
    defaults = dict(
        entry_price=0.45,
        current_price=0.52,
        bid_price=0.50,
        scaled_out_50=False,
        sport_tag="nhl",
        direction="BUY_YES",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


_CFG = NHLExitConfig()
_EMPTY_TABLE: dict = {}

_BASE_SCORE = dict(
    available=True,
    period=2,
    clock_seconds=600,
    our_score=1,
    opp_score=0,
    is_shootout=False,
)


# ---------------------------------------------------------------------------
# 1. Missing score_info
# ---------------------------------------------------------------------------
def test_returns_none_when_score_info_missing():
    pos = _pos()
    result = check_nhl_exit(pos, {}, 0.5, _CFG, _EMPTY_TABLE)
    assert result is None


# ---------------------------------------------------------------------------
# 2. Missing clock_seconds
# ---------------------------------------------------------------------------
def test_returns_none_when_clock_seconds_missing():
    pos = _pos()
    score_info = dict(
        available=True, period=3, our_score=2, opp_score=1, clock_seconds=None, is_shootout=False,
    )
    result = check_nhl_exit(pos, score_info, 0.5, _CFG, _EMPTY_TABLE)
    assert result is None


# ---------------------------------------------------------------------------
# 3. NEAR_RESOLVE fires when bid high
# ---------------------------------------------------------------------------
def test_near_resolve_fires_when_bid_high():
    pos = _pos(bid_price=0.95)
    score_info = dict(
        available=True, period=3, clock_seconds=300, our_score=2, opp_score=1, is_shootout=False,
    )
    result = check_nhl_exit(pos, score_info, 0.8, _CFG, _EMPTY_TABLE)
    assert result is not None
    assert result.reason == ExitReason.NHL_NEAR_RESOLVE


# ---------------------------------------------------------------------------
# 4. HOLD returns None (no table → KeyError → p_win=None → predictive skip)
# ---------------------------------------------------------------------------
def test_hold_returns_none():
    # bid=0.50: below near_resolve(0.94), below scale_out(0.85), not shootout
    # table empty → wp_fn raises KeyError → PREDICTIVE_DEAD skipped
    # structural_damage: current_price(0.52)/entry_price(0.45)=1.15 > 0.30 → no SD
    pos = _pos(bid_price=0.50, current_price=0.52, entry_price=0.45)
    score_info = dict(
        available=True, period=2, clock_seconds=600, our_score=1, opp_score=0, is_shootout=False,
    )
    result = check_nhl_exit(pos, score_info, 0.5, _CFG, _EMPTY_TABLE)
    assert result is None


# ---------------------------------------------------------------------------
# 5. SHOOTOUT fires when is_shootout=True
# ---------------------------------------------------------------------------
def test_shootout_fires_when_is_shootout_true():
    pos = _pos(bid_price=0.55, current_price=0.55, entry_price=0.45)
    score_info = dict(
        available=True, period=3, clock_seconds=60,
        our_score=2, opp_score=2, is_shootout=True,
    )
    result = check_nhl_exit(pos, score_info, 0.9, _CFG, _EMPTY_TABLE)
    assert result is not None
    assert result.reason == ExitReason.NHL_SHOOTOUT_PROFIT


# ---------------------------------------------------------------------------
# 6. SCALE_OUT fires → partial=True, sell_pct=0.50
# ---------------------------------------------------------------------------
def test_sell_50_when_scale_out_fires():
    pos = _pos(bid_price=0.87, current_price=0.87, entry_price=0.45, scaled_out_50=False)
    score_info = dict(
        available=True, period=2, clock_seconds=600, our_score=1, opp_score=0, is_shootout=False,
    )
    result = check_nhl_exit(pos, score_info, 0.5, _CFG, _EMPTY_TABLE)
    assert result is not None
    assert result.reason == ExitReason.NHL_SCALE_OUT
    assert result.partial is True
    assert result.sell_pct == pytest.approx(0.50)


# ---------------------------------------------------------------------------
# 7. Leading fn called when ahead (monkeypatch)
# ---------------------------------------------------------------------------
def test_uses_leading_fn_when_ahead(monkeypatch):
    calls = []

    def _fake_leading(period, lead, seconds, *, table):
        calls.append(("leading", period, lead, seconds))
        return (0.80, "fake")

    monkeypatch.setattr(
        "src.strategy.exit._nhl_exit_dispatch.leading_team_win_probability",
        _fake_leading,
    )

    pos = _pos(bid_price=0.50, current_price=0.52, entry_price=0.45)
    score_info = dict(
        available=True, period=2, clock_seconds=600, our_score=3, opp_score=0, is_shootout=False,
    )
    check_nhl_exit(pos, score_info, 0.5, _CFG, _EMPTY_TABLE)
    assert any(c[0] == "leading" for c in calls)


# ---------------------------------------------------------------------------
# 8. Trailing fn called when behind (monkeypatch)
# ---------------------------------------------------------------------------
def test_uses_trailing_fn_when_behind(monkeypatch):
    calls = []

    def _fake_trailing(period, deficit, seconds, *, table):
        calls.append(("trailing", period, deficit, seconds))
        return (0.20, "fake")

    monkeypatch.setattr(
        "src.strategy.exit._nhl_exit_dispatch.trailing_team_win_probability",
        _fake_trailing,
    )

    pos = _pos(bid_price=0.50, current_price=0.52, entry_price=0.45)
    score_info = dict(
        available=True, period=2, clock_seconds=600, our_score=0, opp_score=3, is_shootout=False,
    )
    check_nhl_exit(pos, score_info, 0.5, _CFG, _EMPTY_TABLE)
    assert any(c[0] == "trailing" for c in calls)
