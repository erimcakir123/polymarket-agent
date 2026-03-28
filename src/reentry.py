# src/reentry.py
"""Re-entry eligibility, tiered blacklist, and dynamic re-entry parameters.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #6, #8, #10
"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

# --- Dynamic elapsed thresholds by game type ---
RE_ENTRY_MAX_ELAPSED = {
    "cs2_bo1": 0.55, "cs2_bo3": 0.70, "cs2_bo5": 0.75,
    "val_bo1": 0.55, "val_bo3": 0.70, "val_bo5": 0.75,
    "lol_bo1": 0.40, "lol_bo3": 0.55, "lol_bo5": 0.65,
    "dota2_bo1": 0.40, "dota2_bo3": 0.55, "dota2_bo5": 0.65,
    "football": 0.70, "basketball": 0.75, "default": 0.65,
}


def get_reentry_max_elapsed(slug: str, number_of_games: int) -> float:
    slug_lower = slug.lower()
    for prefix in ("cs2", "val", "lol", "dota2"):
        if slug_lower.startswith(f"{prefix}-"):
            bo = number_of_games if number_of_games > 0 else 3
            key = f"{prefix}_bo{bo}"
            return RE_ENTRY_MAX_ELAPSED.get(key, RE_ENTRY_MAX_ELAPSED["default"])
    for sport in ("epl", "laliga", "ucl", "seriea", "bundesliga", "ligue1"):
        if slug_lower.startswith(f"{sport}-"):
            return RE_ENTRY_MAX_ELAPSED["football"]
    for sport in ("nba", "cbb"):
        if slug_lower.startswith(f"{sport}-"):
            return RE_ENTRY_MAX_ELAPSED["basketball"]
    return RE_ENTRY_MAX_ELAPSED["default"]


def get_min_reentry_drop(effective_exit_price: float) -> float:
    if effective_exit_price < 0.25:
        return 0.15
    elif effective_exit_price < 0.50:
        return 0.10
    elif effective_exit_price < 0.75:
        return 0.08
    else:
        return 0.05


def get_reentry_size_multiplier(
    ai_prob: float, direction: str, score_info: dict, original_pnl_pct: float
) -> float:
    # ai_prob is ALWAYS P(YES wins). Flip here for BUY_NO usage only.
    effective_ai = ai_prob if direction == "BUY_YES" else (1 - ai_prob)
    base = 0.50
    if effective_ai >= 0.75:
        base += 0.25
    elif effective_ai >= 0.65:
        base += 0.15
    if score_info.get("available") and score_info.get("map_diff", 0) > 0:
        base += 0.15
    if original_pnl_pct > 0.30:
        base += 0.10
    return min(1.0, base)


def can_reenter(
    exit_reason: str,
    exit_price: float,
    current_price: float,
    ai_prob: float,
    direction: str,
    score_info: dict,
    elapsed_pct: float,
    slug: str,
    number_of_games: int,
    minutes_since_exit: float,
    daily_reentry_count: int,
    market_reentry_count: int,
) -> tuple[bool, str]:
    # ai_prob is ALWAYS P(YES wins). Flip here for BUY_NO usage only.
    effective_ai = ai_prob if direction == "BUY_YES" else (1 - ai_prob)
    effective_exit = exit_price if direction == "BUY_YES" else (1 - exit_price)
    effective_current = current_price if direction == "BUY_YES" else (1 - current_price)

    if exit_reason not in ("take_profit", "trailing_stop", "edge_tp", "spike_exit", "scale_out_final"):
        return False, "Non-profit exit"

    max_elapsed = get_reentry_max_elapsed(slug, number_of_games)
    if elapsed_pct > max_elapsed:
        return False, f"Too late: {elapsed_pct:.0%} > {max_elapsed:.0%}"

    min_drop = get_min_reentry_drop(effective_exit)
    actual_drop = (effective_exit - effective_current) / effective_exit if effective_exit > 0 else 0
    if actual_drop < min_drop:
        return False, f"Drop {actual_drop:.0%} < required {min_drop:.0%}"

    if effective_ai < 0.60:
        return False, f"AI prob {effective_ai:.0%} < 60%"

    if score_info.get("available") and score_info.get("map_diff", 0) < 0:
        return False, "Score behind"

    if minutes_since_exit < 5:
        return False, f"Cooldown: {minutes_since_exit:.0f}min < 5min"

    if daily_reentry_count >= 5:
        return False, "Daily re-entry limit (5) reached"
    if market_reentry_count >= 2:
        return False, "Market re-entry limit (2) reached"

    return True, "OK"


# --- Snowball Ban (#11) ---
SNOWBALL_GAMES = {"lol", "dota2"}


def is_snowball_banned(
    slug: str, elapsed_pct: float, score_info: dict
) -> tuple[bool, str]:
    slug_lower = slug.lower()
    is_moba = any(slug_lower.startswith(f"{g}-") for g in SNOWBALL_GAMES)
    if not is_moba:
        return False, ""
    if elapsed_pct > 0.30 and score_info.get("available") and score_info.get("map_diff", 0) < 0:
        return True, f"MOBA snowball ban: {elapsed_pct:.0%} elapsed, score behind"
    return False, ""


# --- Layer 3 Grace Period (#9) ---
REENTRY_GRACE_CYCLES = 5
REENTRY_GRACE_MAX_DROP = 0.03  # 3 cents


def is_grace_period_active(data: dict) -> bool:
    """Re-entry positions get limited immunity from Layer 3 (never-in-profit guard)."""
    entry_reason = data.get("entry_reason", "")
    if not entry_reason.startswith("re_entry") and entry_reason != "scale_in":
        return False
    cycles_held = data.get("cycles_held", 999)
    if cycles_held > REENTRY_GRACE_CYCLES:
        return False
    entry_p = data.get("entry_price", 0)
    current_p = data.get("current_price", 0)
    direction = data.get("direction", "BUY_YES")
    if direction == "BUY_NO":
        drop_since_entry = current_p - entry_p  # YES price rising = bad for BUY_NO
    else:
        drop_since_entry = entry_p - current_p
    if drop_since_entry > REENTRY_GRACE_MAX_DROP:
        return False
    return True


# --- Tiered Blacklist ---

BLACKLIST_RULES = {
    "catastrophic_floor": ("permanent", None),
    "hold_revoked": ("permanent", None),
    "score_terminal_loss": ("permanent", None),
    "graduated_sl": ("timed", None),
    "never_in_profit": ("timed", 20),
    "stop_loss": ("timed", 25),
    "ultra_low_guard": ("timed", 15),
    "take_profit": ("reentry", 5),
    "trailing_stop": ("reentry", 5),
    "edge_tp": ("reentry", 5),
    "spike_exit": ("reentry", 3),
    "scale_out_final": ("reentry", 5),
    "score_terminal_win": ("none", 0),
    "re_entry_resolve_win": ("reentry", 3),
    "re_entry_resolve_loss": ("timed", 15),
    "vs_take_profit": ("reentry", 5),
    "vs_mandatory_exit": ("timed", 15),
    "resolved_win": ("none", 0),
    "resolved_loss": ("timed", 20),
    "election_reeval": ("timed", 30),
    "far_penny": ("none", 0),
    "slot_upgrade": ("timed", 10),
}


def get_graduated_sl_cooldown(elapsed_pct: float) -> int:
    if elapsed_pct < 0.40:
        return 10
    elif elapsed_pct < 0.65:
        return 15
    elif elapsed_pct < 0.85:
        return 20
    else:
        return 30


def get_blacklist_rule(exit_reason: str, elapsed_pct: float = 0.0) -> tuple[str, int | None]:
    rule = BLACKLIST_RULES.get(exit_reason, ("timed", 15))
    btype, duration = rule
    if exit_reason == "graduated_sl":
        duration = get_graduated_sl_cooldown(elapsed_pct)
    return btype, duration


@dataclass
class BlacklistEntry:
    condition_id: str
    exit_reason: str
    blacklist_type: str
    expires_at_cycle: int | None
    exit_data: dict


# --- Score Reversal Blacklist Exception (#13) ---


def qualifies_for_score_reversal_reentry(
    blacklist_entry: BlacklistEntry,
    score_info: dict,
    elapsed_pct: float,
    current_cycle: int,
) -> tuple[bool, str]:
    """Override blacklist if score dramatically reversed. Very narrow conditions."""
    if not score_info.get("available"):
        return False, "No score data"
    map_diff = score_info.get("map_diff", 0)
    if map_diff < 2:
        return False, f"map_diff {map_diff} < 2 (need convincing lead)"
    if elapsed_pct > 0.70:
        return False, f"Too late: {elapsed_pct:.0%} > 70%"
    if blacklist_entry.blacklist_type == "permanent":
        return False, "Cannot override permanent blacklist"
    if blacklist_entry.blacklist_type == "timed":
        remaining = (blacklist_entry.expires_at_cycle or 0) - current_cycle
        if remaining <= 10:
            return False, f"Only {remaining} cycles left, let it expire naturally"
    return True, f"Score reversal: map_diff={map_diff}, elapsed={elapsed_pct:.0%}"


def passes_confidence_momentum(
    saved_ai_prob: float,
    current_ai_prob: float,
    direction: str,
    threshold: float = 1.05,
) -> tuple[bool, str]:
    """Check if AI confidence is rising (for re-entry qualification).
    Compares saved effective prob at exit with current effective prob."""
    saved_eff = saved_ai_prob if direction == "BUY_YES" else (1 - saved_ai_prob)
    current_eff = current_ai_prob if direction == "BUY_YES" else (1 - current_ai_prob)
    if saved_eff < 0.10:
        return True, "Saved effective prob too low"
    ratio = current_eff / saved_eff
    if ratio >= threshold:
        return True, f"Confidence rising: {saved_eff:.0%} -> {current_eff:.0%}"
    return False, f"Confidence not rising: ratio {ratio:.2f} < {threshold}"


class Blacklist:
    def __init__(self, path: str = "logs/blacklist.json"):
        self._path = Path(path)
        self._entries: dict[str, BlacklistEntry] = {}
        self.load()

    def add(self, condition_id: str, exit_reason: str, blacklist_type: str,
            expires_at_cycle: int | None, exit_data: dict | None = None) -> None:
        self._entries[condition_id] = BlacklistEntry(
            condition_id=condition_id, exit_reason=exit_reason,
            blacklist_type=blacklist_type, expires_at_cycle=expires_at_cycle,
            exit_data=exit_data or {},
        )
        self.save()

    def is_blocked(self, condition_id: str, current_cycle: int) -> bool:
        entry = self._entries.get(condition_id)
        if entry is None:
            return False
        if entry.blacklist_type == "permanent":
            return True
        if entry.blacklist_type == "none":
            return False
        if entry.expires_at_cycle is not None and current_cycle >= entry.expires_at_cycle:
            return False
        return True

    def get_entry(self, condition_id: str) -> BlacklistEntry | None:
        return self._entries.get(condition_id)

    def cleanup(self, current_cycle: int) -> None:
        expired = [
            cid for cid, e in self._entries.items()
            if e.blacklist_type != "permanent"
            and e.expires_at_cycle is not None
            and current_cycle >= e.expires_at_cycle
        ]
        for cid in expired:
            del self._entries[cid]
        if expired:
            self.save()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {cid: asdict(e) for cid, e in self._entries.items()}
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._entries = {
                    cid: BlacklistEntry(**vals) for cid, vals in data.items()
                }
            except Exception:
                logger.warning("Failed to load blacklist, starting fresh")
                self._entries = {}
