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


class SportsMarketType(str, Enum):
    MONEYLINE = "moneyline"
    SPREADS = "spreads"
    TOTALS = "totals"


class TotalSide(str, Enum):
    OVER = "over"
    UNDER = "under"
