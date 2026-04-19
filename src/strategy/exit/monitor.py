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

from src.config.sport_rules import get_match_duration_hours, get_sport_rule, _normalize, is_cricket_sport
from src.models.enums import ExitReason
from src.models.position import Position
from src.strategy.exit import a_conf_hold, baseball_score_exit, catastrophic_watch, cricket_score_exit, favored, graduated_sl, near_resolve, scale_out, hockey_score_exit, stop_loss, tennis_score_exit


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



def compute_elapsed_pct(pos: Position) -> float:
    """match_start_iso → match_duration → elapsed %. -1.0 → hesaplanamadı."""
    if not pos.match_start_iso:
        return -1.0
    try:
        start = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return -1.0
    duration_hours = get_match_duration_hours(pos.sport_tag)
    if duration_hours <= 0:
        return -1.0
    elapsed_min = (datetime.now(timezone.utc) - start).total_seconds() / 60.0
    duration_min = duration_hours * 60.0
    return elapsed_min / duration_min


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
    catastrophic_config: dict | None = None,
    scale_out_tiers: list[dict] | None = None,
) -> MonitorResult:
    """Pozisyonu tüm exit kontrollerinden geçir. İlk tetiklenen exit kazanır.

    FAV transition ayrı (exit değil, pos.favored state update).
    """
    score_info = score_info or {}
    scale_out_tiers = scale_out_tiers or []
    elapsed_pct = compute_elapsed_pct(pos)
    # MMA/combat: card saati ≠ maç saati, elapsed güvenilmez → -1 (devre dışı)
    if get_sport_rule(_normalize(pos.sport_tag), "elapsed_exit_disabled"):
        elapsed_pct = -1.0
    cat_cfg = catastrophic_config or {}
    cat_trigger = cat_cfg.get("trigger", 0.25)
    cat_drop = cat_cfg.get("drop_pct", 0.10)
    cat_cancel = cat_cfg.get("cancel", 0.50)

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
        tiers=scale_out_tiers,
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

    # 2.5 Catastrophic watch — sadece NHL (SPEC-004 K5)
    # Tennis'te set kaybı fiyatı düşürür ama maç dönebilir → false positive.
    if _normalize(pos.sport_tag) == "nhl":
        catastrophic_watch.tick(pos, trigger=cat_trigger, cancel=cat_cancel)
        cat_result = catastrophic_watch.check(pos, trigger=cat_trigger, drop_pct=cat_drop)
        if cat_result is not None:
            return MonitorResult(
                exit_signal=ExitSignal(reason=cat_result.reason, detail=cat_result.detail),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )

    # 3. A-conf hold dalı — flat SL + graduated SL'den MUAF (TDD §6.9)
    # Sadece near-resolve (yukarıda) + scale-out (yukarıda) + market-flip aktif.
    a_hold = a_conf_hold.is_a_conf_hold(pos) or pos.favored
    if a_hold:
        # 3a. Score-based exit — hockey A-conf only (SPEC-004 K1-K4)
        if _normalize(pos.sport_tag) == "nhl" and score_info.get("available"):
            sc_result = hockey_score_exit.check(
                sport_tag=pos.sport_tag,
                confidence=pos.confidence,
                score_info=score_info,
                elapsed_pct=elapsed_pct,
                current_price=pos.current_price,
            )
            if sc_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(reason=sc_result.reason, detail=sc_result.detail),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )

        # 3a-tennis. Score-based exit — tennis (SPEC-006 T1/T2)
        if _normalize(pos.sport_tag) == "tennis" and score_info.get("available"):
            t_result = tennis_score_exit.check(
                score_info=score_info,
                current_price=pos.current_price,
                sport_tag=pos.sport_tag,
            )
            if t_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(reason=t_result.reason, detail=t_result.detail),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )

        # 3a-baseball. Score-based exit — baseball (SPEC-010 M1/M2/M3)
        if _normalize(pos.sport_tag) in ("mlb", "kbo", "npb", "baseball") and score_info.get("available"):
            b_result = baseball_score_exit.check(
                score_info=score_info,
                current_price=pos.current_price,
                sport_tag=pos.sport_tag,
            )
            if b_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(reason=b_result.reason, detail=b_result.detail),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )

        # 3a-cricket. Score-based exit — cricket (SPEC-011 C1/C2/C3)
        if is_cricket_sport(pos.sport_tag) and score_info.get("available"):
            c_result = cricket_score_exit.check(
                score_info=score_info,
                current_price=pos.current_price,
                sport_tag=pos.sport_tag,
            )
            if c_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(reason=c_result.reason, detail=c_result.detail),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )

        # 3b. Market flip — tennis hariç (set kaybı ≠ maç kaybı, dönebilir)
        if _normalize(pos.sport_tag) != "tennis" and elapsed_pct >= 0 and a_conf_hold.market_flip_exit(pos, elapsed_pct):
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
