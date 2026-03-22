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
        self._path.write_text(json.dumps(data, indent=2))

    def load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                self._entries = {
                    cid: BlacklistEntry(**vals) for cid, vals in data.items()
                }
            except Exception:
                logger.warning("Failed to load blacklist, starting fresh")
                self._entries = {}
