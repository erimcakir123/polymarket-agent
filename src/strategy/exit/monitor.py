"""Exit orchestrator — tüm exit guard'larını koordine eder (A3 sadeleşmiş).

Öncelik zinciri (ilk tetiklenen kazanır):
  1. Near-resolve profit (eff ≥ 94¢)        — en yüksek öncelik, kâr lock
  2. Scale-out (tek tier: entry→0.99 yolun %50'si, %40 sat) — kısmi exit
  3. Sport-specific score exit (hockey/tennis/baseball/cricket/soccer/nba/nfl)
  4. Market flip (tennis hariç, elapsed ≥85% + eff<50¢)
  5. Fiyat-tabanlı geç guard'lar (ultra_low / never_in_profit / hold_revoked)
  6. FAV promote/demote — sadece state güncellemesi, exit değil

Pure: pos + elapsed_pct + score_info dışarıdan verilir.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.config.settings import BasketballExitConfig, ExitMonitorConfig
from src.config.sport_rules import get_match_duration_hours, get_sport_rule, _normalize, is_cricket_sport
from src.models.enums import ExitReason
from src.models.position import Position
from src.strategy.exit import market_flip, baseball_score_exit, favored, nba_score_exit, nba_spread_exit, nba_totals_exit, near_resolve, nfl_score_exit, price_cap, scale_out, hockey_score_exit, soccer_score_exit, tennis_score_exit
from src.strategy.exit.price_cap import SLParams
from src.strategy.exit.hockey_score_exit import _is_hockey_family

_DEFAULT_MONITOR_CFG = ExitMonitorConfig()

_SOCCER_SPORT_TAGS = frozenset({"soccer", "rugby", "afl", "handball"})


def _is_soccer_sport(sport_tag: str) -> bool:
    tag = _normalize(sport_tag)
    return tag in _SOCCER_SPORT_TAGS or any(tag.startswith(s) for s in _SOCCER_SPORT_TAGS)


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
    cfg: ExitMonitorConfig = _DEFAULT_MONITOR_CFG,
) -> bool:
    """Never-in-profit guard (TDD §6.10). pos hiç kâra geçmedi + maç ≥ elapsed_gate + fiyat çok düştü."""
    if pos.ever_in_profit or pos.peak_pnl_pct > 0.01:
        return False
    if elapsed_pct < cfg.never_in_profit_elapsed_gate:
        return False
    eff_entry = pos.entry_price
    eff_current = pos.bid_price
    score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
    if score_ahead:
        return False
    if eff_current >= eff_entry * cfg.never_in_profit_recovery_ratio:
        return False
    if eff_current < eff_entry * cfg.never_in_profit_drop_ratio:
        return True
    return False  # recovery_ratio ~ drop_ratio aralığı: bekle


def _ultra_low_guard_exit(
    pos: Position,
    elapsed_pct: float,
    cfg: ExitMonitorConfig = _DEFAULT_MONITOR_CFG,
) -> bool:
    """Ultra-low guard (TDD §6.12). eff_entry<entry_cap + elapsed≥elapsed_gate + eff_current<current_cap."""
    eff_entry = pos.entry_price
    eff_current = pos.bid_price
    return (
        eff_entry < cfg.ultra_low_entry_cap
        and elapsed_pct >= cfg.ultra_low_elapsed_gate
        and eff_current < cfg.ultra_low_current_cap
    )


def _hold_revocation_should_revoke(
    pos: Position,
    elapsed_pct: float,
    score_info: dict,
    cfg: ExitMonitorConfig = _DEFAULT_MONITOR_CFG,
) -> bool:
    """Hold-to-resolve pozisyon için revocation kontrolü (PLAN-019: state-only).

    True dönerse caller `pos.favored = False` set etmeli, EXIT VERMEMELİ.
    Normal exit kuralları (özellikle SL — price_cap) sonra karar verir.

    Sadece hold-candidate pozisyonlar için (favored veya anchor_prob ≥ hold_anchor_prob_gate + A/B).
    """
    is_hold_candidate = pos.favored or (
        pos.anchor_probability >= cfg.hold_anchor_prob_gate and pos.confidence in ("A", "B")
    )
    if not is_hold_candidate:
        return False

    eff_entry = pos.entry_price
    eff_current = pos.bid_price
    score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
    dip_is_temporary = (
        pos.consecutive_down_cycles < cfg.hold_dip_min_cycles
        or pos.cumulative_drop < cfg.hold_dip_min_drop
    )

    if (
        pos.ever_in_profit
        and eff_current < eff_entry * cfg.hold_ever_profit_price_ratio
        and elapsed_pct > cfg.hold_ever_profit_elapsed_gate
    ):
        if not score_ahead and not dip_is_temporary:
            return True  # revoke only; caller kararı vermeli (burada exit değil)

    if (
        not pos.ever_in_profit
        and eff_current < eff_entry * cfg.hold_no_profit_price_ratio
        and elapsed_pct > cfg.hold_no_profit_elapsed_gate
    ):
        if not score_ahead and not dip_is_temporary:
            return True  # revoke + exit

    return False


def evaluate(
    pos: Position,
    score_info: dict | None = None,
    near_resolve_threshold_cents: int = 94,
    near_resolve_guard_min: int = 10,
    scale_out_tiers: list[dict] | None = None,
    monitor_cfg: ExitMonitorConfig | None = None,
    sl_params: SLParams | None = None,         # PLAN-014
    scale_out_min_realized_usd: float = 0.0,   # PLAN-014b
    basketball_exit_cfg: BasketballExitConfig | None = None,
    scale_out_threshold: float = 0.85,
) -> MonitorResult:
    """Pozisyonu tüm exit kontrollerinden geçir (A3 score-only, tek-dal akış).

    A-hold ayrımı kaldırıldı: tüm pozisyonlar aynı flow'dan geçer.
    FAV transition ayrı (exit değil, pos.favored state update).
    """
    score_info = score_info or {}
    scale_out_tiers = scale_out_tiers or []
    cfg = monitor_cfg if monitor_cfg is not None else _DEFAULT_MONITOR_CFG
    elapsed_pct = compute_elapsed_pct(pos)
    # MMA/combat: card saati ≠ maç saati, elapsed güvenilmez → -1 (devre dışı)
    if get_sport_rule(_normalize(pos.sport_tag), "elapsed_exit_disabled"):
        elapsed_pct = -1.0

    # 1. Near-resolve — en yüksek öncelik
    _nr = near_resolve.check(pos.bid_price, near_resolve_threshold_cents / 100.0)
    if _nr is not None:
        return MonitorResult(
            exit_signal=ExitSignal(reason=ExitReason.NEAR_RESOLVE, sell_pct=_nr.sell_pct, detail=_nr.reason),
            fav_transition=_fav_transition(pos),
            elapsed_pct=elapsed_pct,
        )

    # 2. Scale-out (partial exit)
    _so = scale_out.check(pos.bid_price, pos.scaled_out_50, scale_out_threshold)
    if _so is not None:
        return MonitorResult(
            exit_signal=ExitSignal(
                reason=ExitReason.SCALE_OUT, partial=True,
                sell_pct=_so.sell_pct, tier=_so.tier, detail=_so.reason,
            ),
            fav_transition=_fav_transition(pos),
            elapsed_pct=elapsed_pct,
        )

    # PLAN-019: Hold revoke (state-only, EXIT YAPMAZ)
    # Tetiklenirse pos.favored=False; SL ve diğer kurallar normal akışla karar verir.
    if elapsed_pct >= 0 and _hold_revocation_should_revoke(pos, elapsed_pct, score_info, cfg):
        pos.favored = False

    # PLAN-014: Dolar-bazlı SL (sport-agnostic, skor bağımsız, ESPN-down dayanıklı)
    if sl_params is not None and price_cap.check(pos, sl_params, elapsed_pct):
        detail = (
            f"price={pos.current_price:.3f}<{sl_params.price_below}, "
            f"loss={pos.shares * (pos.entry_price - pos.current_price):.2f}"
            f">{sl_params.max_loss_usd}"
        )
        return MonitorResult(
            exit_signal=ExitSignal(reason=ExitReason.STOP_LOSS, detail=detail),
            fav_transition=_fav_transition(pos),
            elapsed_pct=elapsed_pct,
        )

    # 3. Sport-specific score-based exit (tüm pozisyonlar — A-hold gate yok)
    if _is_hockey_family(pos.sport_tag) and score_info.get("available"):
        sc_result = hockey_score_exit.check(
            sport_tag=pos.sport_tag,
            confidence=pos.confidence,
            score_info=score_info,
            elapsed_pct=elapsed_pct,
            current_price=pos.bid_price,
        )
        if sc_result is not None:
            return _simple_mr(sc_result, pos, elapsed_pct)

    if _normalize(pos.sport_tag) == "tennis" and score_info.get("available"):
        t_result = tennis_score_exit.check(
            score_info=score_info,
            current_price=pos.bid_price,
            sport_tag=pos.sport_tag,
        )
        if t_result is not None:
            return _simple_mr(t_result, pos, elapsed_pct)

    if _normalize(pos.sport_tag) in ("mlb", "kbo", "npb", "baseball") and score_info.get("available"):
        b_result = baseball_score_exit.check(
            score_info=score_info,
            current_price=pos.bid_price,
            sport_tag=pos.sport_tag,
        )
        if b_result is not None:
            return _simple_mr(b_result, pos, elapsed_pct)

    if _is_soccer_sport(pos.sport_tag) and score_info.get("available"):
        s_result = soccer_score_exit.check(score_info=score_info, sport_tag=pos.sport_tag)
        if s_result is not None:
            return _simple_mr(s_result, pos, elapsed_pct)

    if _normalize(pos.sport_tag) == "nba" and score_info.get("available"):
        nba_mr = _check_nba_exit(pos, score_info, elapsed_pct, basketball_exit_cfg)
        if nba_mr is not None:
            return nba_mr

    if _normalize(pos.sport_tag) == "nfl" and score_info.get("available"):
        nfl_result = nfl_score_exit.check(
            score_info=score_info,
            elapsed_pct=elapsed_pct,
            sport_tag=pos.sport_tag,
        )
        if nfl_result is not None:
            return _simple_mr(nfl_result, pos, elapsed_pct)

    # 4. Market flip — tennis hariç (set kaybı ≠ maç kaybı, dönebilir)
    if _normalize(pos.sport_tag) != "tennis" and elapsed_pct >= 0 and market_flip.market_flip_exit(pos, elapsed_pct):
        return MonitorResult(
            exit_signal=ExitSignal(reason=ExitReason.MARKET_FLIP, detail="eff < 0.50 at elapsed >= 0.85"),
            fav_transition=_fav_transition(pos),
            elapsed_pct=elapsed_pct,
        )

    # 5. Fiyat-tabanlı geç guard'lar (ultra-low, never-in-profit, hold-revocation)
    if elapsed_pct >= 0:
        if _ultra_low_guard_exit(pos, elapsed_pct, cfg):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.ULTRA_LOW_GUARD, detail="ultra-low dead"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
        if _never_in_profit_exit(pos, elapsed_pct, score_info, cfg):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.NEVER_IN_PROFIT, detail="never profited + late + dropped"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
        # PLAN-019: hold_revocation EXIT dispatch silindi.
        # Revoke şimdi state-only (yukarıda scale-out sonrası).
        # Yeni mantık: revoke → pos.favored=False → SL (price_cap) karar verir.

    # 6. Exit yok — sadece favored transition dön
    return MonitorResult(exit_signal=None, fav_transition=_fav_transition(pos), elapsed_pct=elapsed_pct)


def _simple_mr(r, pos: Position, elapsed_pct: float) -> MonitorResult:
    return MonitorResult(exit_signal=ExitSignal(reason=r.reason, detail=r.detail), fav_transition=_fav_transition(pos), elapsed_pct=elapsed_pct)


def _nba_mr(r, pos: Position, elapsed_pct: float) -> MonitorResult:
    return MonitorResult(exit_signal=ExitSignal(reason=r.reason, detail=r.detail, partial=r.partial, sell_pct=r.sell_pct), fav_transition=_fav_transition(pos), elapsed_pct=elapsed_pct)


def _check_nba_exit(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,
    basketball_exit_cfg: BasketballExitConfig | None,
) -> MonitorResult | None:
    """NBA market-type dispatch: spreads → nba_spread_exit, totals → nba_totals_exit, else → nba_score_exit."""
    _bk = basketball_exit_cfg or BasketballExitConfig()
    mtype = pos.sports_market_type or "moneyline"
    _predictive = dict(
        predictive_enabled=_bk.predictive_exit.enabled,
        predictive_safety_margin=_bk.predictive_exit.safety_margin,
        predictive_hold_threshold=_bk.predictive_exit.hold_threshold,
    )

    if mtype == "spreads" and pos.spread_line is not None:
        sp_result = nba_spread_exit.check(
            score_info=score_info,
            spread_line=pos.spread_line,
            direction=pos.direction,
            bid_price=pos.bid_price,
            entry_price=pos.entry_price,
            bill_james_multiplier=_bk.bill_james_multiplier,
            structural_damage_ratio=_bk.structural_damage_ratio,
            ot_seconds=_bk.overtime.seconds,
            ot_margin=_bk.overtime.deficit,
            q4_late_seconds=_bk.spread_empirical.q4_late_seconds,
            q4_late_margin=_bk.spread_empirical.q4_late_margin,
            q4_final_seconds=_bk.spread_empirical.q4_final_seconds,
            q4_final_margin=_bk.spread_empirical.q4_final_margin,
            q4_endgame_seconds=_bk.spread_empirical.q4_endgame_seconds,
            q4_endgame_margin=_bk.spread_empirical.q4_endgame_margin,
            **_predictive,
        )
        if sp_result is not None:
            return _nba_mr(sp_result, pos, elapsed_pct)

    elif mtype == "totals" and pos.total_line is not None:
        effective_side = pos.total_side or "over"
        tot_result = nba_totals_exit.check(
            score_info=score_info,
            target_total=pos.total_line,
            side=effective_side,
            bid_price=pos.bid_price,
            entry_price=pos.entry_price,
            totals_multiplier=_bk.totals_multiplier,
            structural_damage_ratio=_bk.structural_damage_ratio,
            ot_over_scale_pct=_bk.totals_empirical.ot_over_scale_pct,
            q4_late_seconds=_bk.totals_empirical.q4_late_seconds,
            q4_late_gap=_bk.totals_empirical.q4_late_gap,
            q4_final_seconds=_bk.totals_empirical.q4_final_seconds,
            q4_final_gap=_bk.totals_empirical.q4_final_gap,
            q4_endgame_seconds=_bk.totals_empirical.q4_endgame_seconds,
            q4_endgame_gap=_bk.totals_empirical.q4_endgame_gap,
            **_predictive,
        )
        if tot_result is not None:
            return _nba_mr(tot_result, pos, elapsed_pct)

    else:  # moneyline (or spread_line/total_line missing — disabled)
        nba_result = nba_score_exit.check(
            score_info=score_info,
            elapsed_pct=elapsed_pct,
            sport_tag=pos.sport_tag,
            bid_price=pos.bid_price,
            entry_price=pos.entry_price,
            bill_james_multiplier=_bk.bill_james_multiplier,
            structural_damage_ratio=_bk.structural_damage_ratio,
            ot_seconds=_bk.overtime.seconds,
            ot_deficit=_bk.overtime.deficit,
            q4_blowout_seconds=_bk.empirical.q4_blowout_seconds,
            q4_blowout_deficit=_bk.empirical.q4_blowout_deficit,
            q4_late_seconds=_bk.empirical.q4_late_seconds,
            q4_late_deficit=_bk.empirical.q4_late_deficit,
            q4_final_seconds=_bk.empirical.q4_final_seconds,
            q4_final_deficit=_bk.empirical.q4_final_deficit,
            q4_endgame_seconds=_bk.empirical.q4_endgame_seconds,
            q4_endgame_deficit=_bk.empirical.q4_endgame_deficit,
            **_predictive,
        )
        if nba_result is not None:
            return _nba_mr(nba_result, pos, elapsed_pct)

    return None


def _fav_transition(pos: Position) -> FavoredTransition:
    return FavoredTransition(
        promote=favored.should_promote(pos),
        demote=favored.should_demote(pos),
    )
