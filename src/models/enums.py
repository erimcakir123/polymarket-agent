"""Domain enumerations (DECISIONS §5.4). Tüm enum'lar str mixin — JSON serializable."""
from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    SKIP = "SKIP"  # Sinyal yok, bu pazarı atla (hold-to-resolve ile karıştırma)


class Confidence(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class EntryReason(str, Enum):
    NORMAL = "normal"
    EARLY = "early"
    CONSENSUS = "consensus"
    TENNIS = "tennis"


class ExitReason(str, Enum):
    STOP_LOSS = "stop_loss"
    SCALE_OUT = "scale_out"
    GRADUATED_SL = "graduated_sl"
    NEVER_IN_PROFIT = "never_in_profit"
    MARKET_FLIP = "market_flip"
    NEAR_RESOLVE = "near_resolve"
    HOLD_REVOKED = "hold_revoked"
    ULTRA_LOW_GUARD = "ultra_low_guard"
    CIRCUIT_BREAKER = "circuit_breaker"
    MANUAL = "manual"
    PREDICTIVE_DEAD = "predictive_dead"
    SCORE_EXIT = "score_exit"
    RESOLVED = "resolved"  # Market resolved (price ≤0.03 lost / ≥0.97 won)
    # Force-close (SPEC-force-close 2026-05-27) — safety net for deep-loss positions
    # whose match has ended but normal exit chain didn't fire.
    FORCE_CLOSE_ESPN = "force_close_espn_event_ended"
    FORCE_CLOSE_TIME = "force_close_time_expired"
    FORCE_CLOSE_NO_BIDS = "force_close_no_bids"


class SportsMarketType(str, Enum):
    MONEYLINE = "moneyline"
    SPREADS = "spreads"
    TOTALS = "totals"
    # Tennis sub-markets — Polymarket raw strings (sandbox/tennis-lab only)
    TENNIS_FIRST_SET_WINNER = "tennis_first_set_winner"
    TENNIS_SET_HANDICAP = "tennis_set_handicap"
    TENNIS_SET_TOTALS = "tennis_set_totals"


class TotalSide(str, Enum):
    OVER = "over"
    UNDER = "under"
