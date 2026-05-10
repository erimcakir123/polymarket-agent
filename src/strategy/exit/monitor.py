"""Exit orchestrator — tüm exit guard'larını koordine eder.

Öncelik zinciri (ilk tetiklenen kazanır):
  1. Near-resolve profit (eff ≥ 94¢)        — en yüksek öncelik, kâr lock
  2. Scale-out tier (25%→40%, 50%→50%)      — kısmi exit
  3. Flat stop-loss (7-katman)               — temel SL, her zaman aktif
  4. A-conf hold gate:
     - Eğer A-conf hold → sadece market_flip (elapsed≥85%)
     - Değilse → graduated SL + never-in-profit + hold-revocation + ultra-low
  5. FAV promote/demote — sadece state güncellemesi, exit değil

Pure: pos + elapsed_pct + score_info dışarıdan verilir.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.config.settings import BasketballExitConfig
from src.config.sport_rules import BASKETBALL_TAGS, get_match_duration_hours
from src.models.enums import ExitReason, SportsMarketType
from src.models.position import Position
from src.strategy.exit import a_conf_hold, favored, graduated_sl, near_resolve, scale_out, stop_loss
from src.strategy.exit._nba_dispatch import check_nba_exit


@dataclass
class ExitSignal:
    reason: ExitReason
    partial: bool = False      # True = scale-out (kısmi), False = full exit
    sell_pct: float = 1.0
    tier: int | None = None
    detail: str = ""


@dataclass
class FavoredTransition:
    promote: bool = False
    demote: bool = False


@dataclass
class MonitorResult:
    exit_signal: ExitSignal | None
    fav_transition: FavoredTransition
    elapsed_pct: float


def compute_elapsed_pct(pos: Position, score_info: dict | None = None) -> float:
    """match_start_iso → match_duration → elapsed %.

    Eğer match_start parse edilemezse veya yoksa, score_info varsa sport+period'dan
    estimate edilir (SPEC-B Task 6 / audit#4 — ParseError guard bypass fix).

    -1.0 → hesaplanamadı (her ikisi de yok).
    """
    if pos.match_start_iso:
        try:
            start = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
            duration_hours = get_match_duration_hours(pos.sport_tag)
            if duration_hours > 0:
                elapsed_min = (datetime.now(timezone.utc) - start).total_seconds() / 60.0
                duration_min = duration_hours * 60.0
                if duration_min > 0:
                    pct = elapsed_min / duration_min
                    if pct >= 0:
                        return min(pct, 1.0)
        except (ValueError, TypeError):
            pass

    # Fallback: score_info varsa period/inning'den estimate
    if score_info and score_info.get("available"):
        return _estimate_elapsed_from_score(pos.sport_tag, score_info)

    return -1.0


def _estimate_elapsed_from_score(sport_tag: str, score_info: dict) -> float:
    """Sport bazlı period/inning'den elapsed estimate — SPEC-B Task 6 fallback."""
    sport = (sport_tag or "").lower()
    period_str = (score_info.get("period") or "").lower()

    # Hockey: 3 periyot
    if (
        "nhl" in sport or "ahl" in sport or "liiga" in sport or "shl" in sport
        or "mestis" in sport or "allsvenskan" in sport
    ):
        if "ot" in period_str or "final" in period_str:
            return 1.0
        if "3" in period_str:
            return 0.8
        if "2" in period_str:
            return 0.55
        if "1" in period_str:
            return 0.25
        return -1.0

    # Baseball: 9 inning
    if "mlb" in sport or "baseball" in sport or "kbo" in sport or "npb" in sport or "milb" in sport:
        if "final" in period_str:
            return 1.0
        for n in range(9, 0, -1):
            if str(n) in period_str:
                return min(n / 9.0, 1.0)
        return -1.0

    # Basketball: 4 quarter (NBA/WNBA/NCAAB)
    if (
        "nba" in sport or "wnba" in sport or "ncaab" in sport or "cbb" in sport
        or "wncaab" in sport or "euroleague" in sport or "nbl" in sport
    ):
        if "final" in period_str:
            return 1.0
        if "4" in period_str:
            return 0.85
        if "3" in period_str:
            return 0.6
        if "2" in period_str:
            return 0.4
        if "1" in period_str:
            return 0.15
        return -1.0

    return -1.0


def _never_in_profit_exit(
    pos: Position,
    elapsed_pct: float,
    score_info: dict,
) -> bool:
    """Never-in-profit guard (TDD §6.10). pos hiç kâra geçmedi + maç ≥ %70 + fiyat çok düştü."""
    if pos.ever_in_profit or pos.peak_pnl_pct > 0.01:
        return False
    if elapsed_pct < 0.70:
        return False
    eff_entry = pos.entry_price
    eff_current = pos.current_price
    score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
    if score_ahead:
        return False
    if eff_current >= eff_entry * 0.90:
        return False
    if eff_current < eff_entry * 0.75:
        return True
    return False  # 0.75-0.90 aralığı graduated SL'ye bırakılır


def _ultra_low_guard_exit(pos: Position, elapsed_pct: float) -> bool:
    """Ultra-low guard (TDD §6.12). eff_entry<9¢ + elapsed≥%75 + eff_current<5¢."""
    eff_entry = pos.entry_price
    eff_current = pos.current_price
    return eff_entry < 0.09 and elapsed_pct >= 0.75 and eff_current < 0.05


def _hold_revocation_exit(
    pos: Position,
    elapsed_pct: float,
    score_info: dict,
) -> bool:
    """Hold-to-resolve pozisyon için revocation + exit (TDD §6.14).

    Sadece hold-candidate pozisyonlar için (favored veya anchor_prob ≥ 0.65 + A/B).
    """
    is_hold_candidate = pos.favored or (
        pos.anchor_probability >= 0.65 and pos.confidence in ("A", "B")
    )
    if not is_hold_candidate:
        return False

    eff_entry = pos.entry_price
    eff_current = pos.current_price
    score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
    dip_is_temporary = pos.consecutive_down_cycles < 3 or pos.cumulative_drop < 0.05

    if pos.ever_in_profit and eff_current < eff_entry * 0.70 and elapsed_pct > 0.60:
        if not score_ahead and not dip_is_temporary:
            return True  # revoke only; caller kararı vermeli (burada exit değil)

    if not pos.ever_in_profit and eff_current < eff_entry * 0.75 and elapsed_pct > 0.70:
        if not score_ahead and not dip_is_temporary:
            return True  # revoke + exit

    return False


def evaluate(
    pos: Position,
    score_info: dict | None = None,
    near_resolve_threshold_cents: int = 94,
    near_resolve_guard_min: int = 10,
    min_scale_out_realized_usdc: float = 0.0,
    basketball_exit_cfg: BasketballExitConfig | None = None,
) -> MonitorResult:
    """Pozisyonu tüm exit kontrollerinden geçir. İlk tetiklenen exit kazanır.

    FAV transition ayrı (exit değil, pos.favored state update).
    """
    score_info = score_info or {}
    elapsed_pct = compute_elapsed_pct(pos, score_info=score_info)

    # 1. Near-resolve — en yüksek öncelik
    if near_resolve.check(pos, near_resolve_threshold_cents, near_resolve_guard_min):
        return MonitorResult(
            exit_signal=ExitSignal(reason=ExitReason.NEAR_RESOLVE, detail="eff >= threshold"),
            fav_transition=_fav_transition(pos),
            elapsed_pct=elapsed_pct,
        )

    # 2. Scale-out (partial exit)
    so = scale_out.check_scale_out(
        scale_out_tier=pos.scale_out_tier,
        unrealized_pnl_pct=pos.unrealized_pnl_pct,
        unrealized_pnl_usdc=pos.unrealized_pnl_usdc,
        min_realized_usdc=min_scale_out_realized_usdc,
    )
    if so is not None:
        return MonitorResult(
            exit_signal=ExitSignal(
                reason=ExitReason.SCALE_OUT, partial=True,
                sell_pct=so.sell_pct, tier=so.tier, detail=so.reason,
            ),
            fav_transition=_fav_transition(pos),
            elapsed_pct=elapsed_pct,
        )

    # 2.5 Basketball spread/totals dispatch (SPEC-J)
    sport_tag_lc = (pos.sport_tag or "").lower()
    if (
        sport_tag_lc in BASKETBALL_TAGS
        and pos.sports_market_type in (SportsMarketType.SPREADS, SportsMarketType.TOTALS)
    ):
        nba_result = check_nba_exit(
            pos=pos,
            score_info=score_info,
            _elapsed_pct=elapsed_pct,
            basketball_exit_cfg=basketball_exit_cfg,
        )
        if nba_result is not None:
            return MonitorResult(
                exit_signal=ExitSignal(
                    reason=nba_result.reason,
                    partial=nba_result.partial,
                    sell_pct=nba_result.sell_pct,
                    detail=nba_result.detail,
                ),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )

    # 3. A-conf hold dalı — flat SL + graduated SL'den MUAF (TDD §6.9)
    # Sadece near-resolve (yukarıda) + scale-out (yukarıda) + market-flip aktif.
    a_hold = a_conf_hold.is_a_conf_hold(pos) or pos.favored
    if a_hold:
        if elapsed_pct >= 0 and a_conf_hold.market_flip_exit(pos, elapsed_pct):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.MARKET_FLIP, detail="eff < 0.50 at elapsed >= 0.85"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
    else:
        # 4. Non-A-hold flat stop-loss
        if stop_loss.check(pos):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.STOP_LOSS, detail="flat SL hit"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
        # 5. Non-A-hold: graduated SL + never-in-profit + hold-revocation + ultra-low
        if elapsed_pct >= 0:
            if _ultra_low_guard_exit(pos, elapsed_pct):
                return MonitorResult(
                    exit_signal=ExitSignal(reason=ExitReason.ULTRA_LOW_GUARD, detail="ultra-low dead"),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )
            # entry_price zaten token-native (owned side).
            exit_grad, max_loss = graduated_sl.check(pos, elapsed_pct, pos.entry_price, score_info)
            if exit_grad:
                return MonitorResult(
                    exit_signal=ExitSignal(
                        reason=ExitReason.GRADUATED_SL,
                        detail=f"pnl < -{max_loss:.1%} (elapsed {elapsed_pct:.0%})",
                    ),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )
            if _never_in_profit_exit(pos, elapsed_pct, score_info):
                return MonitorResult(
                    exit_signal=ExitSignal(reason=ExitReason.NEVER_IN_PROFIT, detail="never profited + late + dropped"),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )
            if _hold_revocation_exit(pos, elapsed_pct, score_info):
                return MonitorResult(
                    exit_signal=ExitSignal(reason=ExitReason.HOLD_REVOKED, detail="hold revoked + exit"),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )

    # 5. Exit yok — sadece favored transition dön
    return MonitorResult(exit_signal=None, fav_transition=_fav_transition(pos), elapsed_pct=elapsed_pct)


def _fav_transition(pos: Position) -> FavoredTransition:
    return FavoredTransition(
        promote=favored.should_promote(pos),
        demote=favored.should_demote(pos),
    )
