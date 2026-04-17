"""Tennis score-based exit — SPEC-006 T1/T2.

BO3 tennis A-conf hold pozisyonlarda set/game skoru ile erken çıkış.
Pure fonksiyon: I/O yok. Eşikler sport_rules.py config'inden.

T1: Straight set kaybı yaklaşıyor (0-1 set + current set deficit ≥ 3)
T2: Decider set kaybı (1-1 set + 3. set deficit ≥ 3)

Tiebreak buffer: 1. set tiebreak kaybı (dar) → T1 deficit eşiği +1.
Blowout: 1. sette our_games < close_set_threshold → buffer yok.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class TennisExitResult:
    """Tennis exit sonucu — monitor.py ExitSignal'a çevirir."""

    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    current_price: float,
    sport_tag: str = "tennis",
) -> TennisExitResult | None:
    """Tennis T1/T2 exit kontrolü.

    Returns:
        TennisExitResult → çık; None → tetiklenmedi.
    """
    if not score_info.get("available"):
        return None

    linescores = score_info.get("linescores", [])
    if not linescores or len(linescores) < 2:
        return None

    our_is_home = score_info.get("our_is_home", True)
    sets = _map_linescores(linescores, our_is_home)

    completed = sets[:-1]
    current = sets[-1]

    sets_won = sum(1 for our, opp in completed if our > opp)
    sets_lost = sum(1 for our, opp in completed if opp > our)

    current_our, current_opp = current
    deficit = current_opp - current_our
    games_total = current_our + current_opp

    if deficit <= 0:
        return None

    exit_deficit = int(get_sport_rule(sport_tag, "set_exit_deficit", 3))
    exit_games_total = int(get_sport_rule(sport_tag, "set_exit_games_total", 7))
    blowout_deficit = int(get_sport_rule(sport_tag, "set_exit_blowout_deficit", 4))
    close_threshold = int(get_sport_rule(sport_tag, "set_exit_close_set_threshold", 5))
    close_buffer = int(get_sport_rule(sport_tag, "set_exit_close_set_buffer", 1))

    # T1 — Straight set loss (0-1 + current set bad)
    if sets_won == 0 and sets_lost == 1:
        effective_deficit = exit_deficit
        if _was_close_set(completed[0], close_threshold):
            effective_deficit += close_buffer

        if _should_exit(deficit, games_total, effective_deficit, exit_games_total, blowout_deficit):
            return TennisExitResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"T1: sets=0-1 game={current_our}-{current_opp} threshold={effective_deficit}",
            )

    # T2 — Decider set loss (1-1 + 3rd set bad)
    if sets_won == 1 and sets_lost == 1:
        if _should_exit(deficit, games_total, exit_deficit, exit_games_total, blowout_deficit):
            return TennisExitResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"T2: sets=1-1 game={current_our}-{current_opp}",
            )

    return None


def _map_linescores(linescores: list[list[int]], our_is_home: bool) -> list[tuple[int, int]]:
    """Raw linescores → (our_games, opp_games) per set."""
    result = []
    for pair in linescores:
        if len(pair) < 2:
            continue
        if our_is_home:
            result.append((pair[0], pair[1]))
        else:
            result.append((pair[1], pair[0]))
    return result


def _was_close_set(set_scores: tuple[int, int], threshold: int) -> bool:
    """Kaybedilen set dar mıydı? our >= threshold → close (6-7, 5-7)."""
    our, opp = set_scores
    if our >= opp:
        return False
    return our >= threshold


def _should_exit(
    deficit: int,
    games_total: int,
    exit_deficit: int,
    exit_games_total: int,
    blowout_deficit: int,
) -> bool:
    """Exit koşulu: (deficit ≥ blowout) OR (deficit ≥ threshold AND total ≥ min)."""
    if deficit >= blowout_deficit:
        return True
    return deficit >= exit_deficit and games_total >= exit_games_total
