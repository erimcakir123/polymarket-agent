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
    MLB_SUBMARKET = "mlb_submarket"  # SPEC-R: model-anchor MLB totals/run-line entries


class ExitReason(str, Enum):
    STOP_LOSS = "stop_loss"
    SCALE_OUT = "scale_out"
    PARTIAL_SL = "partial_sl"
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
    # Force-close (SPEC-force-close 2026-05-27) — safety net for deep-loss positions
    # whose match has ended but normal exit chain didn't fire.
    FORCE_CLOSE_ESPN = "force_close_espn_event_ended"
    FORCE_CLOSE_TIME = "force_close_time_expired"
    FORCE_CLOSE_NO_BIDS = "force_close_no_bids"
    # Polymarket auto-resolution detected via Gamma (closed=true + umaResolutionStatus=resolved).
    # 2026-05-28: previously bot couldn't detect resolved markets because fetch_events
    # queries closed=false; ExitProcessor now polls gamma per-position periodically.
    RESOLVED = "resolved"
    # SPEC-Z27 (2026-06-09): Polymarket maçı iptal/void → 0.5/0.5 (her hisse 0.50 öder).
    # GERÇEK kâr/zarar (basis iadesi değil) — "İade" sadece açıklayıcı etiket.
    VOIDED = "voided"


class SportsMarketType(str, Enum):
    MONEYLINE = "moneyline"
    SPREADS = "spreads"
    TOTALS = "totals"
    # 2026-05-31: Polymarket tennis market_type'ları. Eski kod sadece
    # moneyline/totals/spreads tanıyıp geri kalanı MONEYLINE'a fallback
    # ediyordu → bimodal sizing yanlış, korelasyon guard yanlış, dashboard
    # yanlış etiket. Kanıt: ATP series'te 6 farklı tennis tipi geliyor.
    TENNIS_SET_HANDICAP = "tennis_set_handicap"
    TENNIS_SET_TOTALS = "tennis_set_totals"
    TENNIS_MATCH_TOTALS = "tennis_match_totals"
    TENNIS_FIRST_SET_WINNER = "tennis_first_set_winner"
    TENNIS_FIRST_SET_TOTALS = "tennis_first_set_totals"
    TENNIS_COMPLETED_MATCH = "tennis_completed_match"


class TotalSide(str, Enum):
    OVER = "over"
    UNDER = "under"
