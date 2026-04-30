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
    SCALE_OUT = "scale_out"
    NEVER_IN_PROFIT = "never_in_profit"
    MARKET_FLIP = "market_flip"
    NEAR_RESOLVE = "near_resolve"
    HOLD_REVOKED = "hold_revoked"
    ULTRA_LOW_GUARD = "ultra_low_guard"
    SCORE_EXIT = "score_exit"
    STOP_LOSS = "stop_loss"            # PLAN-014: dolar-bazlı cap (price<0.50 + loss>$10)
    BLIND_SL = "blind_sl"              # Skor gelmeyen maçlar için devreye giren SL
    PREDICTIVE_DEAD = "predictive_dead"
    NHL_PREDICTIVE_DEAD = "nhl_predictive_dead"
    NHL_STRUCTURAL_DAMAGE = "nhl_structural_damage"
    NHL_SHOOTOUT_PROFIT = "nhl_shootout_profit"
    NHL_NEAR_RESOLVE = "nhl_near_resolve"
    NHL_SCALE_OUT = "nhl_scale_out"
    NHL_PUCK_LINE_NEAR_RESOLVE = "nhl_puck_line_near_resolve"
    NHL_PUCK_LINE_SCALE_OUT = "nhl_puck_line_scale_out"
    NHL_PUCK_LINE_PREDICTIVE_DEAD = "nhl_puck_line_predictive_dead"
    NHL_PUCK_LINE_STRUCTURAL_DAMAGE = "nhl_puck_line_structural_damage"
    NHL_PUCK_LINE_HOLD = "nhl_puck_line_hold"
    NHL_TOTALS_NEAR_RESOLVE = "nhl_totals_near_resolve"
    NHL_TOTALS_SCALE_OUT = "nhl_totals_scale_out"
    NHL_TOTALS_PREDICTIVE_DEAD = "nhl_totals_predictive_dead"
    NHL_TOTALS_STRUCTURAL_DAMAGE = "nhl_totals_structural_damage"
    NHL_TOTALS_HOLD = "nhl_totals_hold"
    # MLB Moneyline exits
    MLB_NEAR_RESOLVE = "mlb_near_resolve"
    MLB_SCALE_OUT = "mlb_scale_out"
    MLB_M1_SEVENTH_DEFICIT_5 = "mlb_m1_seventh_deficit_5"
    MLB_M2_EIGHTH_DEFICIT_3 = "mlb_m2_eighth_deficit_3"
    MLB_M3_NINTH_DEFICIT_1 = "mlb_m3_ninth_deficit_1"
    MLB_PREDICTIVE_DEAD = "mlb_predictive_dead"
    MLB_STRUCTURAL_DAMAGE = "mlb_structural_damage"
    # MLB Run Line exits
    MLB_RUN_LINE_NEAR_RESOLVE = "mlb_run_line_near_resolve"
    MLB_RUN_LINE_SCALE_OUT = "mlb_run_line_scale_out"
    MLB_RUN_LINE_PREDICTIVE_DEAD = "mlb_run_line_predictive_dead"
    MLB_RUN_LINE_STRUCTURAL_DAMAGE = "mlb_run_line_structural_damage"
    # MLB Totals exits
    MLB_TOTALS_NEAR_RESOLVE = "mlb_totals_near_resolve"
    MLB_TOTALS_SCALE_OUT = "mlb_totals_scale_out"
    MLB_TOTALS_PREDICTIVE_DEAD = "mlb_totals_predictive_dead"
    MLB_TOTALS_STRUCTURAL_DAMAGE = "mlb_totals_structural_damage"
    # Tennis Phase 1 v1 set-bazlı exits
    TENNIS_NEAR_RESOLVE = "tennis_near_resolve"
    TENNIS_PROFIT_LOCK = "tennis_profit_lock"
    TENNIS_SET_LOSS_DECISIVE = "tennis_set_loss_decisive"
    TENNIS_SET_LOSS_BAGEL = "tennis_set_loss_bagel"
    TENNIS_MATHEMATICAL_DEATH = "tennis_mathematical_death"
    TENNIS_STRUCTURAL_DAMAGE = "tennis_structural_damage"
