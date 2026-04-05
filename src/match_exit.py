"""Match-aware exit system -- 4-layer exit logic using match timing, score, and profit history.

Spec: docs/superpowers/specs/2026-03-22-match-aware-exit-system-design.md
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.models import effective_price
from src.sport_rules import get_sport_rule

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
        direction: "BUY_YES" or "BUY_NO" -- determines which side is "ours"

    Returns:
        dict with keys: available, our_maps, opp_maps, map_diff,
                        is_already_lost, is_already_won
    """
    empty = {"available": False}

    if not score_str or not isinstance(score_str, str):
        return empty

    try:
        # Split format suffix: "2-1|Bo3" -> "2-1", "Bo3"
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
# Key: (game_prefix, number_of_games) -> duration in minutes
_DURATION_TABLE: dict[tuple[str, int], int] = {
    ("cs2", 1): 40,   ("cs2", 3): 130,  ("cs2", 5): 200,
    ("val", 1): 50,    ("val", 3): 140,  ("val", 5): 220,
    ("lol", 1): 35,    ("lol", 3): 100,  ("lol", 5): 160,
    ("dota2", 1): 45,  ("dota2", 3): 130, ("dota2", 5): 210,
}

# Sport detection from slug/seriesSlug prefix -> duration in minutes
_SPORT_DURATION: dict[str, int] = {
    # Football/Soccer (all leagues)
    "epl": 95, "laliga": 95, "ucl": 95, "seriea": 95, "bundesliga": 95, "ligue1": 95,
    "mls": 95, "liga": 95, "soccer": 95, "primera": 95, "serie": 95,
    "la-liga": 95, "premier": 95, "champions": 95, "europa": 95,
    "eredivisie": 95, "superlig": 95, "ligue": 95, "copa": 95,
    "concacaf": 95, "caf": 95, "afc": 95, "fifa": 95,
    # US Sports
    "nba": 150, "nba-": 150,
    "nhl": 150, "nhl-": 150,
    "mlb": 180, "mlb-": 180,
    "nfl": 195, "nfl-": 195,
    "ncaa": 120, "cbb": 120, "cwbb": 120, "ncaab": 120,
    # Combat sports
    "ufc": 75, "mma": 75, "boxing": 120, "zuffa": 75,
    # Tennis
    "atp": 120, "wta": 100,
    # Cricket
    "t20": 180, "odi": 480, "test": 1800, "ipl": 210, "cricket": 210,
    # Hockey (non-NHL)
    "khl": 150, "shl": 150, "ahl": 150, "cehl": 150,
    # Basketball (non-NBA)
    "euroleague": 120, "bk": 120,
    # Rugby
    "rugby": 100,
    # Motorsport
    "f1": 120, "formula": 120,
}

# Generic esports fallback (when game is unknown but BO format exists)
_GENERIC_ESPORTS: dict[int, int] = {1: 40, 3: 120, 5: 180}


def get_game_duration(slug: str, number_of_games: int, sport_tag: str = "") -> int:
    """Return estimated match duration in minutes.

    Uses game-specific lookup from slug prefix + BO format.
    Falls back to sport_tag, then sport-specific, then generic esports, then 90 min default.
    """
    slug_lower = slug.lower()
    tag_lower = sport_tag.lower() if sport_tag else ""

    # Try game-specific esports lookup (slug or sport_tag)
    for prefix in ("cs2", "val", "lol", "dota2"):
        if slug_lower.startswith(f"{prefix}-") or tag_lower.startswith(prefix):
            bo = number_of_games if number_of_games > 0 else 3
            return _DURATION_TABLE.get((prefix, bo), _DURATION_TABLE.get((prefix, 3), 120))

    # Also match seriesSlug-style names (counter-strike, league-of-legends etc.)
    esport_slug_map = {
        "counter-strike": "cs2", "league-of-legends": "lol",
        "dota-2": "dota2", "valorant": "val",
    }
    for slug_prefix, game_key in esport_slug_map.items():
        if tag_lower.startswith(slug_prefix) or slug_lower.startswith(slug_prefix):
            bo = number_of_games if number_of_games > 0 else 3
            return _DURATION_TABLE.get((game_key, bo), _DURATION_TABLE.get((game_key, 3), 120))

    # Try sport-specific lookup (check both slug and sport_tag)
    for prefix, duration in _SPORT_DURATION.items():
        if slug_lower.startswith(f"{prefix}-") or slug_lower.startswith(prefix) or tag_lower.startswith(prefix):
            return duration

    # If BO format is specified, assume generic esports
    if number_of_games in (1, 3, 5):
        return _GENERIC_ESPORTS[number_of_games]

    # Absolute fallback
    return 90


def get_entry_price_multiplier(entry_price: float) -> float:
    """Return stop loss width multiplier based on entry price.

    Low entry (underdog) -> wider tolerance (1.50)
    High entry (favorite) -> tighter tolerance (0.70)
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
        base = _BASE_TIERS[-1][1]  # fallback to widest tier
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
            exit: bool -- should this position be exited?
            layer: str -- which layer triggered (if exit=True)
            reason: str -- human-readable reason
            revoke_hold: bool -- should hold-to-resolve be revoked?
            restore_hold: bool -- should hold-to-resolve be restored?
            momentum_tighten: bool -- should graduated SL be tightened next cycle?
    """
    result = {"exit": False, "layer": "", "reason": "",
              "revoke_hold": False, "restore_hold": False, "momentum_tighten": False,
              "momentum_multiplier": 1.0, "elapsed_pct": -1.0}

    entry_price = data["entry_price"]
    current_price = data["current_price"]
    direction = data.get("direction", "BUY_YES")

    # Direction-aware effective prices: for BUY_NO, effective = 1 - YES price
    effective_entry = effective_price(entry_price, direction)
    effective_current = effective_price(current_price, direction)
    number_of_games = data.get("number_of_games", 0)
    slug = data.get("slug", "")
    match_score = data.get("match_score", "")
    match_start_iso = data.get("match_start_iso", "")
    ever_in_profit = data.get("ever_in_profit", False)
    peak_pnl_pct = data.get("peak_pnl_pct", 0.0)
    scouted = data.get("scouted", False)
    confidence = data.get("confidence", "B-")
    ai_probability = data.get("ai_probability", 0.5)
    consecutive_down = data.get("consecutive_down_cycles", 0)
    cumulative_drop = data.get("cumulative_drop", 0.0)
    hold_revoked_at = data.get("hold_revoked_at")
    hold_was_original = data.get("hold_was_original", False)
    volatility_swing = data.get("volatility_swing", False)
    pnl_pct = data.get("unrealized_pnl_pct", 0.0)
    sport_tag = data.get("sport_tag", "")
    ht_deficit = get_sport_rule(sport_tag, "halftime_exit_deficit", 15)

    # VS positions use their own exit system
    if volatility_swing:
        return result

    # --- Step 0: Parse score ---
    score_info = parse_match_score(match_score, number_of_games, direction)
    category = data.get("category", "")

    # --- Step 0a: Score terminal checks (esports BO series only) ---
    if category == "esports" and score_info.get("is_already_lost"):
        return {**result, "exit": True, "layer": "score_terminal_loss",
                "reason": f"Match already lost (score: {match_score})"}
    if category == "esports" and score_info.get("is_already_won"):
        return {**result, "exit": False, "layer": "score_terminal_win",
                "reason": f"Match already won -- hold to resolve (score: {match_score})"}

    # --- Step 1: Catastrophic Floor (Layer 1) ---
    is_reentry = data.get("entry_reason", "").startswith("re_entry") or data.get("entry_reason") == "scale_in"
    cat_floor_mult = 0.75 if is_reentry else 0.50
    if effective_entry >= 0.20 and effective_current < effective_entry * cat_floor_mult:
        return {**result, "exit": True, "layer": "catastrophic_floor",
                "reason": f"Price eff:{effective_current:.3f} < eff_entry*{cat_floor_mult:.0%} ({effective_entry*cat_floor_mult:.3f})"}

    # --- Step 2: Calculate elapsed_pct ---
    elapsed_pct = -1.0
    if match_start_iso:
        try:
            start_dt = datetime.fromisoformat(match_start_iso.replace("Z", "+00:00"))
            elapsed_min = (datetime.now(timezone.utc) - start_dt).total_seconds() / 60
            duration = get_game_duration(slug, number_of_games, sport_tag)
            elapsed_pct = elapsed_min / duration if duration > 0 else 0
        except (ValueError, TypeError):
            pass

    # --- Upset/Penny: forced exit at 75% of match (3-tier price filter) ---
    # By 75% elapsed, match outcome is usually clear. Exit unless position became favorite.
    entry_reason = data.get("entry_reason", "")
    if entry_reason in ("upset", "penny") and elapsed_pct is not None and elapsed_pct >= 0.75:
        if effective_current >= 0.60:
            pass  # HOLD — became favorite, let it resolve
        elif effective_current >= 0.50:
            return {**result, "exit": True, "layer": "upset_take_profit",
                    "reason": f"{entry_reason}: match {elapsed_pct:.0%} done, price {effective_current:.2f} in risky zone, take profit"}
        else:
            return {**result, "exit": True, "layer": "upset_forced_exit",
                    "reason": f"{entry_reason}: match {elapsed_pct:.0%} done, price {effective_current:.2f} still underdog, forced exit"}

    # --- Upset/Penny: fallback for missing match timing ---
    if entry_reason in ("upset", "penny") and elapsed_pct < 0:
        hold_hours = data.get("hold_hours", 0)
        if hold_hours >= 3.0 and pnl_pct < 0:
            return {**result, "exit": True, "layer": "upset_max_hold",
                    "reason": f"Upset hunter: held {hold_hours:.1f}h with no timing, PnL {pnl_pct:.1%}"}
        # Penny/upset with no timing and positive PnL: exit after 6h to avoid stuck positions
        if hold_hours >= 6.0:
            return {**result, "exit": True, "layer": "upset_max_hold",
                    "reason": f"{entry_reason}: held {hold_hours:.1f}h with no timing data, forced exit"}

    if elapsed_pct < 0:
        # No match timing -> can't do graduated/never-in-profit checks
        # Return no exit, let existing flat stop loss handle
        return result

    # Ultra-low entry (<9¢) guard: normally exempt from stop loss, but
    # if match is >75% done and price <5¢, exit (position is dead)
    if effective_entry < 0.09 and elapsed_pct >= 0.75 and effective_current < 0.05:
        return {**result, "exit": True, "layer": "ultra_low_guard",
                "reason": f"Ultra-low eff:{effective_entry:.0f}¢ at {elapsed_pct:.0%} done, eff_price {effective_current:.0f}¢ < 5¢"}

    # --- Step 3: Graduated Stop Loss (Layer 2) ---
    if entry_reason in ("upset", "penny"):
        pass  # Skip graduated SL — upsets/penny have forced exit at 75% elapsed
    else:
        max_loss = get_graduated_max_loss(elapsed_pct, effective_entry, score_info)

        # Check DEEPER tier first (5+ is subset of 3+, must come first):
        if consecutive_down >= 5 and cumulative_drop >= 0.10:
            result["momentum_tighten"] = True
            result["momentum_multiplier"] = 0.60
            max_loss = max(0.05, max_loss * 0.60)
        elif consecutive_down >= 3 and cumulative_drop >= 0.05:
            result["momentum_tighten"] = True
            result["momentum_multiplier"] = 0.75
            max_loss = max(0.05, max_loss * 0.75)

        # A-confidence hold-to-resolve: loosen graduated SL floor to 50%.
        # Applied AFTER momentum tightening so A-conf positions never exit
        # via graduated SL unless loss exceeds 50%. Catastrophic floor
        # (Layer 1, effective_current < effective_entry × 0.50) still protects
        # against total collapse.
        if confidence == "A":
            max_loss = max(max_loss, 0.50)

        if pnl_pct < -max_loss:
            return {**result, "exit": True, "layer": "graduated_sl",
                    "reason": f"PnL {pnl_pct:.1%} < -{max_loss:.1%} (elapsed {elapsed_pct:.0%})"}

    # PRIORITY CHAIN (higher = wins):
    # 1. Stop-Loss -- ALWAYS fires, never overridden (portfolio.py)
    # 2. Scale-Out -- only at spike (>50% profit) for hold-to-resolve
    # 3. Hold-to-Resolve -- skips normal TP, not SL
    # 4. Never-in-Profit Guard -- can trigger exit, but SL takes precedence

    # --- Step 4: Never-in-Profit Guard (Layer 3) ---
    if entry_reason in ("upset", "penny"):
        pass  # Skip — these are designed to stay out of profit until late
    elif not ever_in_profit and peak_pnl_pct <= 0.01 and elapsed_pct >= 0.70:
        score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
        if score_ahead:
            pass  # Stay -- winning despite no profit
        elif effective_current >= effective_entry * 0.90:
            pass  # Stay -- close to entry, right side
        elif effective_current < effective_entry * 0.75:
            return {**result, "exit": True, "layer": "never_in_profit",
                    "reason": f"Never profited + 70%+ done + eff_price {effective_current:.3f} < eff_entry*75% ({effective_entry*0.75:.3f})"}
        # Between 0.75 and 0.90: Layer 2 handles via graduated SL

    # --- Step 5: Hold-to-Resolve Check (Layer 4) ---
    is_hold_candidate = scouted or (
        ai_probability >= 0.65 and confidence in ("A", "B+")
    )

    if is_hold_candidate:
        # Check revocation
        # Momentum guard: dips shorter than 3 cycles or smaller than 5c are temporary -> keep hold
        dip_is_temporary = (consecutive_down < 3 or cumulative_drop < 0.05)

        if ever_in_profit and effective_current < effective_entry * 0.70 and elapsed_pct > 0.60:
            score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
            if not score_ahead and not dip_is_temporary:
                result["revoke_hold"] = True
                result["reason"] = f"Hold revoked: eff_price {effective_current:.3f} < eff_entry*70%"

        if not ever_in_profit and effective_current < effective_entry * 0.75 and elapsed_pct > 0.70:
            score_ahead = score_info.get("available") and score_info.get("map_diff", 0) > 0
            if not score_ahead and not dip_is_temporary:
                result["revoke_hold"] = True
                result["exit"] = True
                result["layer"] = "hold_revoked"
                result["reason"] = f"Hold revoked + exit: eff_price {effective_current:.3f} < eff_entry*75% at {elapsed_pct:.0%}"

    # Check restore (if previously revoked)
    if hold_was_original and not scouted and hold_revoked_at:
        try:
            revoked_dt = hold_revoked_at if isinstance(hold_revoked_at, datetime) else \
                datetime.fromisoformat(str(hold_revoked_at).replace("Z", "+00:00"))
            minutes_since = (datetime.now(timezone.utc) - revoked_dt).total_seconds() / 60
            if minutes_since >= 10 and effective_current > effective_entry * 0.85:
                score_behind = score_info.get("available") and score_info.get("map_diff", 0) < 0
                if not score_behind:
                    result["restore_hold"] = True
                    result["reason"] = f"Hold restored: eff_price recovered to {effective_current:.3f} > eff_entry*85%"
        except (ValueError, TypeError):
            pass

    # --- Step 6: Edge Decay TP (Layer 5) ---
    # Underdog positions: as match progresses, AI target decays toward market
    # EXCEPTION: late in match (≥60%) and in profit (≥10%) -> let it ride, resolution close
    if ai_probability > 0 and not result.get("exit"):
        effective_ai_side = effective_price(ai_probability, direction)
        late_and_winning = elapsed_pct >= 0.60 and effective_current > effective_entry * 1.10
        if effective_ai_side < 0.65 and not late_and_winning:
            try:
                from src.edge_decay import get_decayed_ai_target
                decayed = get_decayed_ai_target(effective_ai_side, effective_current, elapsed_pct)
                edge_tp = decayed * 0.85
                if effective_current >= edge_tp and effective_current > effective_entry * 1.10:
                    return {**result, "exit": True, "layer": "edge_decay",
                            "reason": f"Edge decay TP: price {effective_current:.3f} >= decayed {edge_tp:.3f}"}
            except ImportError:
                pass  # edge_decay module not available

    result["elapsed_pct"] = elapsed_pct
    return result
