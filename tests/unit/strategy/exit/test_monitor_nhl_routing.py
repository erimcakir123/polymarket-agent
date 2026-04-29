"""Tests for monitor.evaluate() NHL routing — TDD §3C.

Verify that NHL positions route through check_nhl_exit (NHL_* reasons)
and non-NHL positions keep the generic near_resolve / scale_out reasons.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from src.models.enums import ExitReason
from src.models.position import Position
from src.strategy.exit.monitor import evaluate


def _make_pos(sport_tag: str, bid: float, entry: float = 0.45,
              current: float | None = None, scaled_out_50: bool = False) -> Position:
    cp = current if current is not None else bid
    # Live match (1h ago) → pre-match guard'ı geç (near_resolve/scale_out aktif)
    match_start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    return Position(
        condition_id=f"test-{sport_tag}-cid",
        token_id=f"test-{sport_tag}-token",
        direction="BUY_YES",
        match_start_iso=match_start,
        entry_price=entry,
        current_price=cp,
        bid_price=bid,
        size_usdc=10.0,
        shares=20.0,
        anchor_probability=0.60,
        sport_tag=sport_tag,
        scaled_out_50=scaled_out_50,
    )


# ---------------------------------------------------------------------------
# 1. NHL position → NHL_NEAR_RESOLVE (not generic NEAR_RESOLVE)
# ---------------------------------------------------------------------------
def test_nhl_position_returns_nhl_near_resolve_not_generic():
    pos = _make_pos("nhl", bid=0.95, entry=0.45, current=0.95)
    score_info = dict(
        available=True, period=3, clock_seconds=300,
        our_score=2, opp_score=1, is_shootout=False,
    )
    result = evaluate(pos, score_info=score_info, nhl_exit_cfg=None, nhl_wp_table={})
    assert result.exit_signal is not None
    assert result.exit_signal.reason == ExitReason.NHL_NEAR_RESOLVE
    assert result.exit_signal.reason != ExitReason.NEAR_RESOLVE


# ---------------------------------------------------------------------------
# 2. NBA position → generic NEAR_RESOLVE (not NHL routing)
# ---------------------------------------------------------------------------
def test_nba_position_gets_generic_near_resolve():
    pos = _make_pos("nba", bid=0.95, entry=0.45, current=0.95)
    # NBA score_info.available=False → NBA score exit skipped; generic near-resolve fires
    score_info = {"available": False}
    result = evaluate(pos, score_info=score_info)
    assert result.exit_signal is not None
    assert result.exit_signal.reason == ExitReason.NEAR_RESOLVE


# ---------------------------------------------------------------------------
# 3. NHL position → NHL_SCALE_OUT (not generic SCALE_OUT)
# ---------------------------------------------------------------------------
def test_nhl_position_returns_nhl_scale_out_not_generic():
    pos = _make_pos("nhl", bid=0.87, entry=0.45, current=0.87, scaled_out_50=False)
    score_info = dict(
        available=True, period=2, clock_seconds=600,
        our_score=1, opp_score=0, is_shootout=False,
    )
    result = evaluate(pos, score_info=score_info, nhl_exit_cfg=None, nhl_wp_table={})
    assert result.exit_signal is not None
    assert result.exit_signal.reason == ExitReason.NHL_SCALE_OUT
    assert result.exit_signal.reason != ExitReason.SCALE_OUT


# ---------------------------------------------------------------------------
# 4. Pre-match guard: maç başlamamış → near_resolve fire ETMEZ (phantom bid)
# ---------------------------------------------------------------------------
def test_pre_match_phantom_high_bid_does_not_fire_near_resolve():
    """28 Apr 11:57 UTC bug repro: maç başlamadan bid=1.00 phantom geldi.
    Pre-match guard near_resolve'ı atlatmalı."""
    pos = _make_pos("nba", bid=0.99, entry=0.50, current=0.99)
    # Match start FUTURE (8 saat sonra)
    pos.match_start_iso = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
    score_info = {"available": False}
    result = evaluate(pos, score_info=score_info)
    # Pre-match guard → near_resolve fire ETMEZ
    assert result.exit_signal is None or result.exit_signal.reason != ExitReason.NEAR_RESOLVE


def test_pre_match_phantom_high_bid_does_not_fire_scale_out():
    """Maç başlamadan bid=0.87 phantom → scale_out ATLAMALI."""
    pos = _make_pos("nba", bid=0.87, entry=0.50, current=0.87, scaled_out_50=False)
    pos.match_start_iso = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
    score_info = {"available": False}
    result = evaluate(pos, score_info=score_info)
    assert result.exit_signal is None or result.exit_signal.reason != ExitReason.SCALE_OUT


# ---------------------------------------------------------------------------
# 5. Pre-match guard — NHL score-based exits (PREDICTIVE_DEAD phantom repro)
# ---------------------------------------------------------------------------
def test_pre_match_does_not_fire_nhl_puck_line_predictive_dead():
    """28 Apr 19:36 UTC bug repro: Sabres -1.5 spread, ESPN pre-match
    (period='Scheduled', 0-0) score_info.available=True döndürdü → Skellam
    fallback p_cover≈0.13 < bid 0.39 + 0.03 → PREDICTIVE_DEAD anında.
    Pre-match'te NHL score-based dispatch'in tamamı atlanmalı."""
    pos = _make_pos("nhl", bid=0.39, entry=0.39, current=0.39)
    pos.sports_market_type = "spreads"
    pos.match_start_iso = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    score_info = dict(
        available=True, period=1, clock_seconds=1200,
        our_score=0, opp_score=0, is_shootout=False,
    )
    result = evaluate(
        pos, score_info=score_info,
        nhl_puck_line_cfg=None, nhl_puck_line_table={},
    )
    assert result.exit_signal is None


def test_pre_match_does_not_fire_nhl_moneyline_predictive_dead():
    """Pre-match NHL ML için de score-based dispatch atlanmalı (koruma)."""
    pos = _make_pos("nhl", bid=0.55, entry=0.55, current=0.55)
    pos.sports_market_type = "moneyline"
    pos.match_start_iso = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    score_info = dict(
        available=True, period=1, clock_seconds=1200,
        our_score=0, opp_score=0, is_shootout=False,
    )
    result = evaluate(pos, score_info=score_info, nhl_exit_cfg=None, nhl_wp_table={})
    assert result.exit_signal is None


def test_pre_match_does_not_fire_nhl_totals_predictive_dead():
    """Pre-match NHL totals için de score-based dispatch atlanmalı (koruma)."""
    pos = _make_pos("nhl", bid=0.40, entry=0.40, current=0.40)
    pos.sports_market_type = "totals"
    pos.match_start_iso = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    score_info = dict(
        available=True, period=1, clock_seconds=1200,
        our_score=0, opp_score=0, is_shootout=False,
    )
    result = evaluate(
        pos, score_info=score_info,
        nhl_totals_cfg=None, nhl_totals_table={},
    )
    assert result.exit_signal is None


# ---------------------------------------------------------------------------
# 6. ESPN delay phantom: match_start passed but ESPN still pre-match
#    (period="Scheduled", period_number=None) — production bug 28 Apr 23:30 UTC
# ---------------------------------------------------------------------------
def test_espn_scheduled_status_does_not_fire_nhl_puck_line_predictive_dead():
    """28 Apr 23:30 UTC bug repro: match_start UTC zamanı geçmiş ama ESPN
    hâlâ pre-match snapshot döndürüyor — period='Scheduled' (string),
    period_number=None, clock_seconds=0, score=0/0. elapsed_pct≈0 (positive)
    → match_pre_start guard False. Dispatch period_number int kontrolü ile
    atlamalı. Aksi halde Skellam(margin=0, seconds=0) → 0.0 → PREDICTIVE_DEAD."""
    pos = _make_pos("nhl", bid=0.39, entry=0.39, current=0.39)
    pos.sports_market_type = "spreads"
    pos.match_start_iso = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    score_info = dict(
        available=True,
        period="Scheduled",     # ESPN type.description
        period_number=None,     # ESPN status.period (int) yok
        clock_seconds=0,
        our_score=0, opp_score=0,
        is_shootout=False,
    )
    result = evaluate(
        pos, score_info=score_info,
        nhl_puck_line_cfg=None, nhl_puck_line_table={},
    )
    assert result.exit_signal is None


def test_espn_scheduled_status_does_not_fire_nhl_moneyline_predictive_dead():
    """ESPN-delay pre-match (string 'Scheduled' period) NHL ML için de
    dispatch atlamalı."""
    pos = _make_pos("nhl", bid=0.55, entry=0.55, current=0.55)
    pos.sports_market_type = "moneyline"
    pos.match_start_iso = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    score_info = dict(
        available=True,
        period="Scheduled", period_number=None,
        clock_seconds=0,
        our_score=0, opp_score=0,
        is_shootout=False,
    )
    result = evaluate(pos, score_info=score_info, nhl_exit_cfg=None, nhl_wp_table={})
    assert result.exit_signal is None


def test_espn_scheduled_status_does_not_fire_nhl_totals_predictive_dead():
    """ESPN-delay pre-match (string 'Scheduled' period) NHL totals için
    dispatch atlamalı."""
    pos = _make_pos("nhl", bid=0.40, entry=0.40, current=0.40)
    pos.sports_market_type = "totals"
    pos.match_start_iso = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    score_info = dict(
        available=True,
        period="Scheduled", period_number=None,
        clock_seconds=0,
        our_score=0, opp_score=0,
        is_shootout=False,
    )
    result = evaluate(
        pos, score_info=score_info,
        nhl_totals_cfg=None, nhl_totals_table={},
    )
    assert result.exit_signal is None
