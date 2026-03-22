"""Match-aware exit system — 4-layer exit logic using match timing, score, and profit history.

Spec: docs/superpowers/specs/2026-03-22-match-aware-exit-system-design.md
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def parse_match_score(
    score_str: str | None,
    number_of_games: int,
    direction: str,
) -> dict:
    """Parse match_score into structured data, direction-aware.

    Args:
        score_str: Raw score string from Gamma API (e.g. "2-1|Bo3", "1-0")
        number_of_games: BO format (1, 3, 5). 0 = unknown, treated as BO3.
        direction: "BUY_YES" or "BUY_NO" — determines which side is "ours"

    Returns:
        dict with keys: available, our_maps, opp_maps, map_diff,
                        is_already_lost, is_already_won
    """
    empty = {"available": False}

    if not score_str or not isinstance(score_str, str):
        return empty

    try:
        # Split format suffix: "2-1|Bo3" → "2-1", "Bo3"
        parts = score_str.split("|")
        scores = parts[0].strip().split("-")
        if len(scores) != 2:
            return empty

        first_score = int(scores[0].strip())
        second_score = int(scores[1].strip())
    except (ValueError, IndexError):
        return empty

    # Direction-aware: BUY_YES = we want first team to win
    #                  BUY_NO  = we want first team to lose (second team wins)
    if direction == "BUY_NO":
        our_maps = second_score
        opp_maps = first_score
    else:
        our_maps = first_score
        opp_maps = second_score

    bo = number_of_games if number_of_games > 0 else 3
    wins_needed = (bo // 2) + 1

    return {
        "available": True,
        "our_maps": our_maps,
        "opp_maps": opp_maps,
        "map_diff": our_maps - opp_maps,
        "is_already_lost": opp_maps >= wins_needed,
        "is_already_won": our_maps >= wins_needed,
    }


# Game-specific duration estimates (minutes)
# Key: (game_prefix, number_of_games) → duration in minutes
_DURATION_TABLE: dict[tuple[str, int], int] = {
    ("cs2", 1): 40,   ("cs2", 3): 130,  ("cs2", 5): 200,
    ("val", 1): 50,    ("val", 3): 140,  ("val", 5): 220,
    ("lol", 1): 35,    ("lol", 3): 100,  ("lol", 5): 160,
    ("dota2", 1): 45,  ("dota2", 3): 130, ("dota2", 5): 210,
}

# Sport detection from slug prefix
_SPORT_DURATION: dict[str, int] = {
    "epl": 95, "laliga": 95, "ucl": 95, "seriea": 95, "bundesliga": 95, "ligue1": 95,
    "nba": 150,
    "cbb": 120,
    "mlb": 180,
    "nhl": 150,
}

# Generic esports fallback (when game is unknown but BO format exists)
_GENERIC_ESPORTS: dict[int, int] = {1: 40, 3: 120, 5: 180}


def get_game_duration(slug: str, number_of_games: int) -> int:
    """Return estimated match duration in minutes.

    Uses game-specific lookup from slug prefix + BO format.
    Falls back to sport-specific, then generic esports, then 90 min default.
    """
    slug_lower = slug.lower()

    # Try game-specific esports lookup
    for prefix in ("cs2", "val", "lol", "dota2"):
        if slug_lower.startswith(f"{prefix}-"):
            bo = number_of_games if number_of_games > 0 else 3
            return _DURATION_TABLE.get((prefix, bo), _DURATION_TABLE.get((prefix, 3), 120))

    # Try sport-specific lookup
    for prefix, duration in _SPORT_DURATION.items():
        if slug_lower.startswith(f"{prefix}-"):
            return duration

    # If BO format is specified, assume generic esports
    if number_of_games in (1, 3, 5):
        return _GENERIC_ESPORTS[number_of_games]

    # Absolute fallback
    return 90


def get_entry_price_multiplier(entry_price: float) -> float:
    """Return stop loss width multiplier based on entry price.

    Low entry (underdog) → wider tolerance (1.50)
    High entry (favorite) → tighter tolerance (0.70)
    """
    if entry_price < 0.20:
        return 1.50
    elif entry_price < 0.35:
        return 1.25
    elif entry_price <= 0.50:
        return 1.00
    elif entry_price < 0.70:
        return 0.85
    else:
        return 0.70


# Base tiers: (elapsed_pct_threshold, max_loss)
# The tier that matches the HIGHEST threshold <= elapsed_pct is used.
_BASE_TIERS = [
    (1.00, 0.05),   # Overtime
    (0.85, 0.15),   # Final phase
    (0.65, 0.20),   # Late match
    (0.40, 0.30),   # Mid match
    (0.00, 0.40),   # Early match
]


def get_graduated_max_loss(
    elapsed_pct: float,
    entry_price: float,
    score_info: dict,
) -> float:
    """Calculate max allowed loss: base_tier × price_mult × score_adj.

    Returns a float in [0.05, 0.70] representing the max loss fraction.
    E.g. 0.30 means position is exited if unrealized_pnl_pct < -0.30.
    """
    # Pre-match: use base -40%
    if elapsed_pct < 0:
        base = 0.40
    else:
        # Find matching tier (sorted descending, first match wins)
        base = 0.40  # default
        for threshold, loss in _BASE_TIERS:
            if elapsed_pct >= threshold:
                base = loss
                break

    # Entry price multiplier
    price_mult = get_entry_price_multiplier(entry_price)

    # Score adjustment
    score_adj = 1.0
    if score_info.get("available"):
        md = score_info.get("map_diff", 0)
        if md > 0:
            score_adj = 1.25  # ahead: loosen
        elif md < 0:
            score_adj = 0.75  # behind: tighten

    result = base * price_mult * score_adj

    # Clamp to [0.05, 0.70]
    return max(0.05, min(0.70, result))


def check_match_exit(data: dict) -> dict:
    """Run 4-layer match-aware exit check on a position.

    Args:
        data: Dict with position fields (see _make_pos_data in tests for schema)

    Returns:
        dict with keys:
            exit: bool — should this position be exited?
            layer: str — which layer triggered (if exit=True)
            reason: str — human-readable reason
            revoke_hold: bool — should hold-to-resolve be revoked?
            restore_hold: bool — should hold-to-resolve be restored?
            momentum_tighten: bool — should graduated SL be tightened next cycle?
    """
    result = {"exit": False, "layer": "", "reason": "",
              "revoke_hold": False, "restore_hold": False, "momentum_tighten": False}

    entry_price = data["entry_price"]
    current_price = data["current_price"]
    direction = data.get("direction", "BUY_YES")
    number_of_games = data.get("number_of_games", 0)
    slug = data.get("slug", "")
    match_score = data.get("match_score", "")
    match_start_iso = data.get("match_start_iso", "")
    ever_in_profit = data.get("ever_in_profit", False)
    peak_pnl_pct = data.get("peak_pnl_pct", 0.0)
    scouted = data.get("scouted", False)
    confidence = data.get("confidence", "medium")
    ai_probability = data.get("ai_probability", 0.5)
    consecutive_down = data.get("consecutive_down_cycles", 0)
    cumulative_drop = data.get("cumulative_drop", 0.0)
    hold_revoked_at = data.get("hold_revoked_at")
    hold_was_original = data.get("hold_was_original", False)
    volatility_swing = data.get("volatility_swing", False)
    pnl_pct = data.get("unrealized_pnl_pct", 0.0)

    # VS positions use their own exit system
    if volatility_swing:
        return result

    # --- Step 0: Parse score ---
    score_info = parse_match_score(match_score, number_of_games, direction)

    # --- Step 0a: Score terminal checks ---
    if score_info.get("is_already_lost"):
        return {"exit": True, "layer": "score_terminal",
                "reason": f"Match already lost (score: {match_score})",
                "revoke_hold": False, "restore_hold": False, "momentum_tighten": False}
    if score_info.get("is_already_won"):
        return {"exit": False, "layer": "score_terminal",
                "reason": f"Match already won — hold to resolve (score: {match_score})",
                "revoke_hold": False, "restore_hold": False, "momentum_tighten": False}

    # --- Step 1: Catastrophic Floor (Layer 1) ---
    if entry_price >= 0.25 and current_price < entry_price * 0.50:
        return {"exit": True, "layer": "catastrophic_floor",
                "reason": f"Price {current_price:.3f} < entry*50% ({entry_price*0.50:.3f})",
                "revoke_hold": False, "restore_hold": False, "momentum_tighten": False}

    # --- Step 2: Calculate elapsed_pct ---
    elapsed_pct = -1.0
    if match_start_iso:
        try:
            start_dt = datetime.fromisoformat(match_start_iso.replace("Z", "+00:00"))
            elapsed_min = (datetime.now(timezone.utc) - start_dt).total_seconds() / 60
            duration = get_game_duration(slug, number_of_games)
            elapsed_pct = elapsed_min / duration if duration > 0 else 0
        except (ValueError, TypeError):
            pass

    if elapsed_pct < 0:
        # No match timing -> can't do graduated/never-in-profit checks
        # Return no exit, let existing flat stop loss handle
        return result

    # Ultra-low entry (<9¢) guard: normally exempt from stop loss, but
    # if match is >90% done and price <5¢, exit (position is dead)
    if entry_price < 0.09 and elapsed_pct >= 0.90 and current_price < 0.05:
        return {**result, "exit": True, "layer": "ultra_low_guard",
                "reason": f"Ultra-low {entry_price:.0f}¢ at {elapsed_pct:.0%} done, price {current_price:.0f}¢ < 5¢"}

    # --- Step 3: Graduated Stop Loss (Layer 2) ---
    max_loss = get_graduated_max_loss(elapsed_pct, entry_price, score_info)

    # Momentum tightening: if 3+ consecutive down cycles with 5c+ drop, tighten one tier
    if consecutive_down >= 3 and cumulative_drop >= 0.05:
        result["momentum_tighten"] = True
        # Tighten by reducing tolerance by 25%
        max_loss = max(0.05, max_loss * 0.75)

    if pnl_pct < -max_loss:
        return {**result, "exit": True, "layer": "graduated_sl",
                "reason": f"PnL {pnl_pct:.1%} < -{max_loss:.1%} (elapsed {elapsed_pct:.0%})"}

    # --- Step 4: Never-in-Profit Guard (Layer 3) ---
    if not ever_in_profit and peak_pnl_pct <= 0.01 and elapsed_pct >= 0.70:
        # Score ahead -> STAY regardless
        if score_info.get("available") and score_info.get("map_diff", 0) > 0:
            pass  # Stay — winning despite no profit
        elif current_price >= entry_price * 0.90:
            pass  # Stay — close to entry, right side
        elif current_price < entry_price * 0.75:
            return {**result, "exit": True, "layer": "never_in_profit",
                    "reason": f"Never profited + 70%+ done + price {current_price:.3f} < entry*75% ({entry_price*0.75:.3f})"}
        # Between 0.75 and 0.90: Layer 2 handles via graduated SL

        # Force exit at 80%+ if price < entry*0.75 and score not ahead
        if elapsed_pct >= 0.80 and current_price < entry_price * 0.75:
            score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
            if not score_ahead:
                return {**result, "exit": True, "layer": "never_in_profit",
                        "reason": f"Force exit at 80%+ — never profited, price {current_price:.3f}"}

    # --- Step 5: Hold-to-Resolve Check (Layer 4) ---
    is_hold_candidate = scouted or (
        ai_probability >= 0.65 and confidence in ("high", "medium_high")
    )

    if is_hold_candidate:
        # Check revocation
        # Momentum guard: dips shorter than 3 cycles or smaller than 5c are temporary -> keep hold
        dip_is_temporary = (consecutive_down < 3 or cumulative_drop < 0.05)

        if ever_in_profit and current_price < entry_price * 0.70 and elapsed_pct > 0.60:
            score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
            if not score_ahead and not dip_is_temporary:
                result["revoke_hold"] = True
                result["reason"] = f"Hold revoked: saw profit but now at {current_price:.3f} < entry*70%"

        if not ever_in_profit and current_price < entry_price * 0.75 and elapsed_pct > 0.70:
            score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
            if not score_ahead and not dip_is_temporary:
                result["revoke_hold"] = True
                result["exit"] = True
                result["layer"] = "hold_revoked"
                result["reason"] = f"Hold revoked + exit: never profited, {current_price:.3f} < entry*75% at {elapsed_pct:.0%}"

    # Check restore (if previously revoked)
    if hold_was_original and not scouted and hold_revoked_at:
        try:
            revoked_dt = hold_revoked_at if isinstance(hold_revoked_at, datetime) else \
                datetime.fromisoformat(str(hold_revoked_at).replace("Z", "+00:00"))
            minutes_since = (datetime.now(timezone.utc) - revoked_dt).total_seconds() / 60
            if minutes_since >= 10 and current_price > entry_price * 0.85:
                score_behind = score_info.get("available") and score_info.get("map_diff", 0) < 0
                if not score_behind:
                    result["restore_hold"] = True
                    result["reason"] = f"Hold restored: price recovered to {current_price:.3f} > entry*85%"
        except (ValueError, TypeError):
            pass

    return result
