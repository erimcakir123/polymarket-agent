"""
NHL match clock parser for ESPN scoreboard responses.

Converts ESPN status payload into structured (period, seconds_remaining_in_regulation,
is_overtime, is_shootout, is_final) tuple for use in exit logic.

Design:
- Regulation periods: 1, 2, 3 each 1200 seconds (20 min)
- OT period: 4 (300s in regular season, 1200s in playoffs — exit logic
  treats both via Skellam OT lambda)
- SO: period 5, sudden-death by shootout, no clock
- Total regulation: 3600s

Maps ESPN status.period + status.displayClock to game clock semantics.

Probe-derived state mapping (status.type.detail):
- "1st Period", "P1, ..." -> period 1, live
- "2nd Period", "P2, ..." -> period 2, live
- "3rd Period", "P3, ..." -> period 3, live
- "OT", "Overtime"        -> period 4, live, is_overtime=True
- "Shootout"              -> period 5, live, is_shootout=True
- "Final"                 -> period 3 ended, is_final=True
- "Final/OT"              -> period 4 ended, is_final=True, ended_in_ot=True
- "Final/SO"              -> period 5 ended, is_final=True, ended_in_so=True

References:
- data/probes/nhl/SUMMARY.md (probe analysis)
"""
from __future__ import annotations

from dataclasses import dataclass


REGULATION_PERIOD_SECONDS: int = 1200
REGULATION_TOTAL_SECONDS: int = 3600
OT_REGULAR_SEASON_SECONDS: int = 300


@dataclass(frozen=True)
class NHLClock:
    """Parsed NHL game clock state from ESPN scoreboard."""
    period: int                           # 1, 2, 3, 4 (OT), 5 (SO), 0 if pre
    seconds_remaining_in_period: int      # countdown within current period
    seconds_remaining_in_regulation: int  # 0 if past regulation
    is_pre: bool
    is_live: bool
    is_overtime: bool
    is_shootout: bool
    is_final: bool
    ended_in_ot: bool
    ended_in_so: bool
    raw_state: str    # ESPN status.type.state
    raw_detail: str   # ESPN status.type.detail (preserved for debugging)


def period_clock_to_regulation_seconds(period: int, period_clock_seconds: int) -> int:
    """Convert ESPN period-bound clock to NHL regulation-total seconds remaining.

    Empirical puck line / totals tables and Skellam λ are calibrated against
    regulation-total clock (max 3600s = 3×1200s). ESPN displayClock is
    period-bound (0–1200s within the current period). Dispatch needs the
    match-bound value to look up empirical buckets and feed Skellam.

    period <= 0 (pre) or period > 3 (OT/SO) → 0 (no regulation time left).
    """
    if period <= 0 or period > 3:
        return 0
    period_clock_seconds = max(0, period_clock_seconds)
    return (3 - period) * REGULATION_PERIOD_SECONDS + period_clock_seconds


def _parse_display_clock(display_clock: str) -> int:
    """
    Parse ESPN displayClock (e.g. "10:35", "0:00", "20:00") to seconds.
    Returns 0 on parse failure.
    """
    if not display_clock or not isinstance(display_clock, str):
        return 0
    try:
        parts = display_clock.strip().split(":")
        if len(parts) != 2:
            return 0
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, AttributeError):
        return 0


def parse_nhl_status(status: dict) -> NHLClock:
    """
    Parse ESPN status payload into NHLClock.

    Args:
        status: dict from event["status"], typically containing
                {"period": int, "displayClock": str, "clock": float,
                 "type": {"state": str, "detail": str, ...}}

    Returns:
        NHLClock dataclass
    """
    if not isinstance(status, dict):
        return NHLClock(
            period=0,
            seconds_remaining_in_period=0,
            seconds_remaining_in_regulation=REGULATION_TOTAL_SECONDS,
            is_pre=True, is_live=False, is_overtime=False, is_shootout=False,
            is_final=False, ended_in_ot=False, ended_in_so=False,
            raw_state="unknown", raw_detail="",
        )

    period: int = int(status.get("period", 0) or 0)
    display_clock: str = status.get("displayClock", "0:00") or "0:00"
    type_obj: dict = status.get("type") or {}
    state: str = (type_obj.get("state") or "").lower()
    detail: str = (type_obj.get("detail") or "").strip()
    detail_lower: str = detail.lower()

    is_post: bool = (state == "post")
    is_in: bool = (state == "in")
    is_pre: bool = not is_in and not is_post  # "pre", "" (unknown), or any unrecognized state

    # Post-game outcome detection (probe-derived)
    is_final: bool = is_post
    ended_in_ot: bool = is_post and (
        "/ot" in detail_lower
        or ("ot" in detail_lower and "final" in detail_lower)
    )
    ended_in_so: bool = is_post and (
        "/so" in detail_lower or "shootout" in detail_lower
    )

    # Live OT/SO detection
    is_overtime_live: bool = is_in and (
        "overtime" in detail_lower
        or detail_lower.startswith("ot")
        or period == 4
    )
    is_shootout_live: bool = is_in and (
        "shootout" in detail_lower or period == 5
    )

    # Promote period when ESPN reports period=3 with Final/OT or Final/SO
    if is_post and ended_in_ot and period < 4:
        period = 4
    if is_post and ended_in_so and period < 5:
        period = 5

    is_overtime: bool = is_overtime_live or ended_in_ot
    is_shootout: bool = is_shootout_live or ended_in_so

    seconds_remaining_in_period: int = _parse_display_clock(display_clock)

    # Compute regulation seconds remaining
    if is_pre or (not status):
        seconds_remaining_in_regulation = REGULATION_TOTAL_SECONDS
    elif period <= 3 and is_in:
        elapsed_full_periods = (period - 1) * REGULATION_PERIOD_SECONDS
        elapsed_in_current = REGULATION_PERIOD_SECONDS - seconds_remaining_in_period
        elapsed_total = elapsed_full_periods + elapsed_in_current
        seconds_remaining_in_regulation = max(0, REGULATION_TOTAL_SECONDS - elapsed_total)
    else:
        seconds_remaining_in_regulation = 0

    return NHLClock(
        period=period,
        seconds_remaining_in_period=seconds_remaining_in_period,
        seconds_remaining_in_regulation=seconds_remaining_in_regulation,
        is_pre=is_pre,
        is_live=is_in,
        is_overtime=is_overtime,
        is_shootout=is_shootout,
        is_final=is_final,
        ended_in_ot=ended_in_ot,
        ended_in_so=ended_in_so,
        raw_state=state,
        raw_detail=detail,
    )
