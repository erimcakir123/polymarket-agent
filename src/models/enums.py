"""Domain enumerations (TDD §5.4). Tüm enum'lar str mixin — JSON serializable."""
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
    DIRECTIONAL = "directional"  # SPEC-017: edge-free directional entry


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
    SCORE_EXIT = "score_exit"
    CATASTROPHIC_BOUNCE = "catastrophic_bounce"
    MANUAL = "manual"
