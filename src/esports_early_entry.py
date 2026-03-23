"""Esports Early Entry — enter esports markets before match starts, profit from price correction.

Strategy:
- Esports markets open with low volume and mispriced odds (~50/50)
- PandaScore data reveals true probability (team form, H2H, rankings)
- Enter early when market price is far from fair value
- As match approaches, volume increases and market corrects toward fair value
- Take profit when price reaches our estimated fair value
- Re-entry on dips is rule-based (no AI needed — fair value already known)

Rules:
- Only enter esports markets (CS2, LoL, Dota2, Valorant)
- Use PandaScore data to estimate fair probability
- Min edge: 10% between market price and estimated fair value
- Don't enter if match is already live (_estimate_match_live)
- Don't enter if already in this market
- Max 3 concurrent esports early positions
- Skip min_liquidity filter for esports (low liquidity is expected early)
- Re-entry: if fair_value is cached and price dips, enter without AI
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Fair value cache: condition_id -> (fair_value, direction, question)
_fair_value_cache: Dict[str, Tuple[float, str, str]] = {}


@dataclass
class EsportsEarlyCandidate:
    """An esports market with edge based on PandaScore data."""
    condition_id: str
    slug: str
    question: str
    market_price: float       # Current YES price on market
    fair_value: float         # Estimated fair probability from PandaScore
    edge: float               # fair_value - market_price (or inverse for NO)
    direction: str            # BUY_YES or BUY_NO
    token_id: str             # Token to buy
    token_price: float        # Price of the token we're buying
    team_a_wr: float          # Team A win rate from PandaScore
    team_b_wr: float          # Team B win rate from PandaScore
    data_summary: str         # Brief stats summary for logging
    is_reentry: bool = False  # True if using cached fair value (no AI needed)
    match_start_iso: str = "" # Match start time from PandaScore
    number_of_games: int = 0  # BO format (3=BO3, 5=BO5, 0=unknown)


def estimate_fair_value_from_pandascore(
    team_a_stats: Optional[dict],
    team_b_stats: Optional[dict],
) -> Optional[float]:
    """Estimate fair probability for Team A winning based on PandaScore data.

    Uses win rates weighted by recency and head-to-head record.
    Returns probability for Team A (YES side).
    """
    if not team_a_stats and not team_b_stats:
        return None

    a_wr = team_a_stats.get("win_rate", 0.5) if team_a_stats else 0.5
    b_wr = team_b_stats.get("win_rate", 0.5) if team_b_stats else 0.5

    # Need actual data from BOTH teams to estimate
    a_games = (team_a_stats.get("wins", 0) + team_a_stats.get("losses", 0)) if team_a_stats else 0
    b_games = (team_b_stats.get("wins", 0) + team_b_stats.get("losses", 0)) if team_b_stats else 0
    if a_games < 3 or b_games < 3:
        return None  # Not enough data for either team

    # Simple relative strength model:
    # P(A wins) = A_winrate / (A_winrate + B_winrate)
    total = a_wr + b_wr
    if total <= 0:
        return 0.5

    fair_a = a_wr / total

    # Regress toward 50% to account for uncertainty (shrinkage)
    # Less data = more shrinkage
    a_games = (team_a_stats.get("wins", 0) + team_a_stats.get("losses", 0)) if team_a_stats else 0
    b_games = (team_b_stats.get("wins", 0) + team_b_stats.get("losses", 0)) if team_b_stats else 0
    min_games = min(a_games, b_games)

    if min_games < 5:
        shrinkage = 0.6  # Heavy regression — not enough data
    elif min_games < 10:
        shrinkage = 0.3  # Moderate
    else:
        shrinkage = 0.15  # Light — good sample

    fair_a = fair_a * (1 - shrinkage) + 0.5 * shrinkage

    # Clamp to reasonable range
    fair_a = max(0.15, min(0.85, fair_a))

    return round(fair_a, 3)


def find_esports_early_candidates(
    markets: list,
    esports_client,
    portfolio_positions: dict,
    exited_markets: set,
    exit_cooldowns: dict,
    cycle_count: int,
    max_concurrent: int = 3,
    min_edge: float = 0.10,
) -> List[EsportsEarlyCandidate]:
    """Scan esports markets for early entry opportunities.

    First pass: use PandaScore to estimate fair value and find edge.
    Re-entry: use cached fair value if market was previously analyzed.
    """
    if not esports_client.available:
        return []

    # Count existing esports early positions
    current_count = sum(
        1 for p in portfolio_positions.values()
        if getattr(p, "entry_reason", "") == "esports_early"
    )
    if current_count >= max_concurrent:
        return []

    candidates = []

    for m in markets:
        # Skip if already in portfolio or exited/on cooldown
        if m.condition_id in portfolio_positions:
            continue
        if m.condition_id in exited_markets:
            continue
        if exit_cooldowns.get(m.condition_id, 0) > cycle_count:
            continue

        q = m.question.lower()
        # Only esports markets
        esport_kw = ["lol:", "cs2:", "cs:", "csgo:", "counter-strike:", "valorant:", "dota 2:",
                     "bo1", "bo3", "bo5"]
        if not any(k in q for k in esport_kw):
            continue

        # Skip sub-markets (Game 1 Winner, Map 1 Winner, etc.)
        import re
        if re.search(r"\b(Game\s+\d+\s+Winner|Map\s+\d+\s+Winner|Set\s+\d+\s+Winner|Round\s+\d+\s+Winner)\b",
                      m.question, re.IGNORECASE):
            continue

        # Skip handicap markets (Game Handicap)
        if "handicap" in q:
            continue

        current_yes = m.yes_price
        if not current_yes or current_yes <= 0.05 or current_yes >= 0.95:
            continue

        # Check if we have cached fair value (re-entry — no AI/PandaScore needed)
        cached = _fair_value_cache.get(m.condition_id)
        if cached:
            fair_value, _, _ = cached
            is_reentry = True
            data_summary = "cached fair value"
            team_a_wr = 0.0
            team_b_wr = 0.0
        else:
            # First entry — fetch PandaScore data
            game_slug = esports_client.detect_game(m.question, m.tags)
            if not game_slug:
                continue

            team_a_name, team_b_name = esports_client._extract_team_names(m.question)
            if not team_a_name or not team_b_name:
                continue

            team_a_stats = esports_client.get_team_recent_results(game_slug, team_a_name)
            team_b_stats = esports_client.get_team_recent_results(game_slug, team_b_name)

            fair_value = estimate_fair_value_from_pandascore(team_a_stats, team_b_stats)
            if fair_value is None:
                continue

            team_a_wr = team_a_stats.get("win_rate", 0) if team_a_stats else 0
            team_b_wr = team_b_stats.get("win_rate", 0) if team_b_stats else 0

            a_name = team_a_stats.get("team_name", team_a_name) if team_a_stats else team_a_name
            b_name = team_b_stats.get("team_name", team_b_name) if team_b_stats else team_b_name
            a_total = (team_a_stats["wins"] + team_a_stats["losses"]) if team_a_stats else 0
            b_total = (team_b_stats["wins"] + team_b_stats["losses"]) if team_b_stats else 0

            data_summary = (
                f"{a_name}: {team_a_wr:.0%} WR ({a_total} games) | "
                f"{b_name}: {team_b_wr:.0%} WR ({b_total} games) | "
                f"Fair value: {fair_value:.0%}"
            )
            is_reentry = False

        # Fetch match time and BO format from PandaScore
        match_start_iso = ""
        number_of_games = 0
        _game = game_slug if not is_reentry else esports_client.detect_game(m.question, getattr(m, "tags", []))
        _ta = team_a_name if not is_reentry else None
        _tb = team_b_name if not is_reentry else None
        if is_reentry and _game:
            _ta, _tb = esports_client._extract_team_names(m.question)
        if _game and _ta and _tb:
            match_info = esports_client.get_upcoming_match_info(_game, _ta, _tb)
            if match_info:
                match_start_iso = match_info.get("begin_at", "")
                number_of_games = match_info.get("number_of_games", 0)

        # Skip if match already started or too far away (max 24h)
        if match_start_iso:
            from datetime import datetime, timezone
            try:
                start_dt = datetime.fromisoformat(match_start_iso.replace("Z", "+00:00"))
                hours_to_match = (start_dt - datetime.now(timezone.utc)).total_seconds() / 3600
                if hours_to_match < 0:
                    logger.info("Esports early skip (LIVE): %s started %.1fh ago", m.question[:50], abs(hours_to_match))
                    continue
                if hours_to_match > 24:
                    logger.info("Esports early skip (too far): %s in %.0fh", m.question[:50], hours_to_match)
                    continue
            except (ValueError, TypeError):
                pass
        else:
            # No match start time available — skip (can't verify timing)
            logger.info("Esports early skip (no start time): %s", m.question[:50])
            continue

        # Calculate edge and direction
        # fair_value is P(YES wins)
        edge_yes = fair_value - current_yes         # Edge if we buy YES
        edge_no = (1 - fair_value) - (1 - current_yes)  # Edge if we buy NO = -(edge_yes)

        if edge_yes >= min_edge:
            direction = "BUY_YES"
            edge = edge_yes
            token_id = m.yes_token_id
            token_price = current_yes
        elif edge_no >= min_edge:
            direction = "BUY_NO"
            edge = edge_no
            token_id = m.no_token_id
            token_price = 1 - current_yes
        else:
            continue

        # Cache the fair value for re-entry
        _fair_value_cache[m.condition_id] = (fair_value, direction, m.question)

        logger.info(
            "Esports early candidate: %s | market=%.0f%% fair=%.0f%% edge=%.0f%% %s%s",
            m.question[:55], current_yes * 100, fair_value * 100, edge * 100,
            direction, " (RE-ENTRY)" if is_reentry else "",
        )

        candidates.append(EsportsEarlyCandidate(
            condition_id=m.condition_id,
            slug=m.slug,
            question=m.question,
            market_price=current_yes,
            fair_value=fair_value,
            edge=edge,
            direction=direction,
            token_id=token_id,
            token_price=token_price,
            team_a_wr=team_a_wr,
            team_b_wr=team_b_wr,
            data_summary=data_summary,
            is_reentry=is_reentry,
            match_start_iso=match_start_iso,
            number_of_games=number_of_games,
        ))

    # Sort by edge (highest first)
    candidates.sort(key=lambda c: c.edge, reverse=True)

    # Limit to available slots
    available = max_concurrent - current_count
    return candidates[:available]


def get_cached_fair_value(condition_id: str) -> Optional[Tuple[float, str]]:
    """Get cached fair value for re-entry decisions.

    Returns (fair_value, direction) or None.
    """
    cached = _fair_value_cache.get(condition_id)
    if cached:
        return cached[0], cached[1]
    return None
