"""Tennis exit dispatch — Phase 1 v1 set-bazlı sabit tablo (BO3 only).

Spec: docs/superpowers/specs/2026-04-29-tennis-magnus-live-system-design.md §6
DECISIONS.md tennis section.

Pure: pos + score_info dışarıdan verilir. I/O yok.
Strategy katmanı; cfg dataclass injected (no magic numbers).

Direction handling (BUY_YES = bet on player A/home; BUY_NO = bet on B/away):
- Internal logic always works in "us vs opponent" frame; caller maps via
  `our_is_home` boolean to pick which side of home_*/away_* fields counts as us.

Decision priority (first hit wins):
  1. NEAR_RESOLVE      — current_bid >= near_resolve_threshold
  2. STRUCTURAL_DAMAGE — current_price/entry_price <= structural_damage_ratio
  3. MATEMATICAL_DEATH — sets_lost == sets_to_win (BO3=2, BO5=3)
  4. SET_LOSS_BAGEL    — last completed set lost 0-6
  5. SET_LOSS_DECISIVE — last completed set lost {1,2,3}-6 (BO3 only Phase 1)
  6. PROFIT_LOCK       — current_bid >= profit_lock_threshold
  7. HOLD              — default
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.models.enums import ExitReason as DomainExitReason
from src.models.position import Position


class ExitAction(str, Enum):
    HOLD = "HOLD"
    SELL_50 = "SELL_50"
    SELL_75 = "SELL_75"
    SELL_ALL = "SELL_ALL"


class ExitReason(str, Enum):
    NEAR_RESOLVE = "NEAR_RESOLVE"
    PROFIT_LOCK = "PROFIT_LOCK"
    SET_LOSS_DECISIVE = "SET_LOSS_DECISIVE"
    SET_LOSS_BAGEL = "SET_LOSS_BAGEL"
    MATEMATICAL_DEATH = "MATEMATICAL_DEATH"
    STRUCTURAL_DAMAGE = "STRUCTURAL_DAMAGE"
    HOLD = "HOLD"


@dataclass(frozen=True)
class TennisExitConfig:
    """Phase 1 v1 thresholds — match config.yaml `tennis.exit.*`."""

    near_resolve_threshold: float = 0.95
    profit_lock_threshold: float = 0.80
    structural_damage_ratio: float = 0.30
    # BO3-only Phase 1: thresholds defining "decisive" / "bagel"
    bagel_games_lost: int = 6           # opponent games to qualify as bagel
    bagel_games_won_max: int = 0        # our games <= this in lost set → bagel
    decisive_games_won_max: int = 3     # our games <= this (and >0) → decisive
    bo3_sets_to_win: int = 2
    bo5_sets_to_win: int = 3


@dataclass(frozen=True)
class TennisExitDecision:
    action: ExitAction
    reason: ExitReason
    note: str


@dataclass(frozen=True)
class TennisExitSignal:
    """Adapter shape returned by check() — consumed by monitor.py.

    Mirrors NHLSignal so monitor branch can build ExitSignal uniformly.
    """

    reason: DomainExitReason
    partial: bool
    sell_pct: float
    detail: str


_DOMAIN_REASON_MAP: dict[ExitReason, DomainExitReason] = {
    ExitReason.NEAR_RESOLVE: DomainExitReason.TENNIS_NEAR_RESOLVE,
    ExitReason.PROFIT_LOCK: DomainExitReason.TENNIS_PROFIT_LOCK,
    ExitReason.SET_LOSS_DECISIVE: DomainExitReason.TENNIS_SET_LOSS_DECISIVE,
    ExitReason.SET_LOSS_BAGEL: DomainExitReason.TENNIS_SET_LOSS_BAGEL,
    ExitReason.MATEMATICAL_DEATH: DomainExitReason.TENNIS_MATEMATICAL_DEATH,
    ExitReason.STRUCTURAL_DAMAGE: DomainExitReason.TENNIS_STRUCTURAL_DAMAGE,
}

_ACTION_TO_SELL_PCT: dict[ExitAction, float] = {
    ExitAction.SELL_50: 0.50,
    ExitAction.SELL_75: 0.75,
    ExitAction.SELL_ALL: 1.00,
}


def decide_tennis_exit(
    *,
    cfg: TennisExitConfig,
    entry_price: float,
    current_bid: float,
    current_price: float,
    sets_won_home: int,
    sets_won_away: int,
    games_home: int,
    games_away: int,
    current_set: int,
    is_bo5: bool,
    direction: str,
    last_completed_set_home: int | None = None,
    last_completed_set_away: int | None = None,
) -> TennisExitDecision:
    """Tennis exit decision — pure function (Phase 1 v1, BO3 primary path).

    All score fields use ESPN home/away convention. `direction` flips
    perspective: BUY_YES = home is "us", BUY_NO = away is "us".

    BO5 safe fallback: SET_LOSS_DECISIVE / SET_LOSS_BAGEL are NOT fired in
    BO5 (deferred to Phase 2 — Bayesian model needed). MATEMATICAL_DEATH still
    fires at 0-3 sets and NEAR_RESOLVE / PROFIT_LOCK / STRUCTURAL_DAMAGE work
    normally for both formats.
    """
    # ── 1. NEAR_RESOLVE (highest priority — overrides all set-state logic) ──
    if current_bid >= cfg.near_resolve_threshold:
        return TennisExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.NEAR_RESOLVE,
            note=f"bid={current_bid:.3f}",
        )

    # ── 2. STRUCTURAL_DAMAGE ──
    if entry_price > 0 and (current_price / entry_price) <= cfg.structural_damage_ratio:
        ratio = current_price / entry_price
        return TennisExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.STRUCTURAL_DAMAGE,
            note=f"ratio={ratio:.2f}",
        )

    # ── Determine "us" vs "opponent" from direction ──
    if direction == "BUY_YES":
        our_sets, opp_sets = sets_won_home, sets_won_away
        our_last_set = last_completed_set_home
        opp_last_set = last_completed_set_away
    else:  # BUY_NO
        our_sets, opp_sets = sets_won_away, sets_won_home
        our_last_set = last_completed_set_away
        opp_last_set = last_completed_set_home

    # ── 3. MATEMATICAL_DEATH ──
    sets_to_win = cfg.bo5_sets_to_win if is_bo5 else cfg.bo3_sets_to_win
    if opp_sets >= sets_to_win and our_sets < sets_to_win:
        return TennisExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.MATEMATICAL_DEATH,
            note=f"sets {our_sets}-{opp_sets} bo{'5' if is_bo5 else '3'}",
        )

    # ── 4 & 5. Set loss table (BO3 only — Phase 1 v1) ──
    # Only fire if opponent just won a set AND we have linescore for it.
    # BO5 deferred to Phase 2 (needs Bayesian context).
    if (
        not is_bo5
        and our_last_set is not None
        and opp_last_set is not None
        and opp_last_set >= cfg.bagel_games_lost
        and our_last_set < opp_last_set
    ):
        # Bagel: 0-6
        if our_last_set <= cfg.bagel_games_won_max:
            return TennisExitDecision(
                action=ExitAction.SELL_75,
                reason=ExitReason.SET_LOSS_BAGEL,
                note=f"set {our_last_set}-{opp_last_set}",
            )
        # Decisive: {1,2,3}-6
        if our_last_set <= cfg.decisive_games_won_max:
            return TennisExitDecision(
                action=ExitAction.SELL_50,
                reason=ExitReason.SET_LOSS_DECISIVE,
                note=f"set {our_last_set}-{opp_last_set}",
            )
        # Close set loss (4-6, 5-7, 6-7) → fall through to HOLD layer

    # ── 6. PROFIT_LOCK ──
    if current_bid >= cfg.profit_lock_threshold:
        return TennisExitDecision(
            action=ExitAction.SELL_50,
            reason=ExitReason.PROFIT_LOCK,
            note=f"bid={current_bid:.3f}",
        )

    # ── 7. HOLD (default) ──
    return TennisExitDecision(
        action=ExitAction.HOLD,
        reason=ExitReason.HOLD,
        note="",
    )


def _extract_last_completed_set(
    linescores: list,
    sets_won_home: int,
    sets_won_away: int,
    current_set: int,
) -> tuple[int | None, int | None]:
    """Extract last COMPLETED set scoreline from ESPN linescores.

    ESPN linescores are [[home_games, away_games], ...] per set in order.
    Last completed = the latest set where one side reached >= 6 games and
    is no longer the in-progress set.

    Returns (None, None) when no completed set or malformed input.
    """
    if not linescores:
        return None, None
    total_sets_done = sets_won_home + sets_won_away
    if total_sets_done == 0:
        return None, None
    # Take the most recent completed set; ESPN appends current set last
    # when current_set > total_sets_done. If current_set == total_sets_done,
    # all linescores are completed and last entry is the most recent.
    idx = total_sets_done - 1
    # Guard index range
    if idx < 0 or idx >= len(linescores):
        return None, None
    pair = linescores[idx]
    if not isinstance(pair, (list, tuple)) or len(pair) < 2:
        return None, None
    try:
        return int(pair[0]), int(pair[1])
    except (TypeError, ValueError):
        return None, None


def check_tennis_exit(
    *,
    pos: Position,
    score_info: dict,
    cfg: TennisExitConfig,
) -> TennisExitSignal | None:
    """Adapt position + score_info → TennisExitSignal | None (HOLD = None).

    Wires score_info dict into pure decide_tennis_exit() and maps the result
    into the shape monitor.py consumes.
    """
    if not score_info.get("available"):
        return None

    sets_won_home = score_info.get("sets_won_home")
    sets_won_away = score_info.get("sets_won_away")
    if sets_won_home is None or sets_won_away is None:
        # ESPN sometimes lacks tennis-specific fields → safe HOLD
        sets_won_home = 0
        sets_won_away = 0

    games_home = score_info.get("games_home", 0) or 0
    games_away = score_info.get("games_away", 0) or 0
    current_set = score_info.get("current_set", 1) or 1
    linescores = score_info.get("linescores", []) or []

    last_h, last_a = _extract_last_completed_set(
        linescores, sets_won_home, sets_won_away, current_set,
    )

    # Format: BO3 default; BO5 indicated externally (Grand Slam ATP men).
    # Phase 1 v1: rely on score_info["is_bo5"] hint when present.
    is_bo5 = bool(score_info.get("is_bo5", False))

    decision = decide_tennis_exit(
        cfg=cfg,
        entry_price=pos.entry_price,
        current_bid=pos.bid_price,
        current_price=pos.current_price,
        sets_won_home=sets_won_home,
        sets_won_away=sets_won_away,
        games_home=games_home,
        games_away=games_away,
        current_set=current_set,
        is_bo5=is_bo5,
        direction=pos.direction,
        last_completed_set_home=last_h,
        last_completed_set_away=last_a,
    )

    if decision.action == ExitAction.HOLD:
        return None

    domain_reason = _DOMAIN_REASON_MAP.get(decision.reason, DomainExitReason.SCORE_EXIT)
    sell_pct = _ACTION_TO_SELL_PCT.get(decision.action, 1.0)
    partial = decision.action in (ExitAction.SELL_50, ExitAction.SELL_75)
    return TennisExitSignal(
        reason=domain_reason,
        partial=partial,
        sell_pct=sell_pct,
        detail=decision.note,
    )
