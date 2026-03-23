"""Live Dip Entry — rule-based re-entry during live matches (no AI needed).

When a favorite's price drops significantly during a live match (e.g., they fall
behind early), this module enters a position betting on the favorite to recover.
Exit is handled by existing TP/trailing stop logic.

Rules:
- Only enter if match is confirmed live via ESPN scoreboard
- Favorite must have dropped 10%+ from pre-match price
- Don't enter if already in this market
- Don't enter if market is in exited_markets
- Max 2 concurrent live-dip positions
- Use fixed bet size (not Kelly — no AI probability available)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports"

# Map sport keywords to ESPN endpoints
_SPORT_MAP = [
    (["nba"], "basketball", "nba"),
    (["cbb", "ncaa", "march-madness"], "basketball", "mens-college-basketball"),
    (["nhl", "hockey"], "hockey", "nhl"),
    (["nfl"], "football", "nfl"),
    (["mlb", "baseball"], "baseball", "mlb"),
    (["epl", "premier-league"], "soccer", "eng.1"),
    (["la-liga"], "soccer", "esp.1"),
    (["serie-a"], "soccer", "ita.1"),
    (["bundesliga"], "soccer", "ger.1"),
    (["ucl", "champions-league"], "soccer", "uefa.champions"),
]


@dataclass
class LiveDipCandidate:
    """A market where the favorite's price has dipped during a live match."""
    condition_id: str
    slug: str
    question: str
    pre_match_price: float  # YES price before match started
    current_price: float    # Current YES price
    drop_pct: float         # How much the favorite dropped (0.0-1.0)
    direction: str          # BUY_YES or BUY_NO (buy the dipped favorite)
    espn_status: str        # "in" = in progress
    score_summary: str      # e.g., "NYK 45 - BKN 52 (Q2)"


def check_espn_live(slug: str, question: str) -> dict | None:
    """Check ESPN if this market's match is currently live.

    Returns dict with status info or None if not found/not live.
    """
    text = (slug + " " + question).lower()

    # Find the right ESPN endpoint
    sport = league = None
    for keywords, s, l in _SPORT_MAP:
        if any(k in text for k in keywords):
            sport, league = s, l
            break

    if not sport:
        return None

    try:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        url = f"{ESPN_SCOREBOARD}/{sport}/{league}/scoreboard?dates={today}"
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return None

        events = resp.json().get("events", [])
        for event in events:
            status = event.get("status", {}).get("type", {})
            state = status.get("state", "")

            if state != "in":
                continue

            # Check if this event matches our market
            comps = event.get("competitions", [{}])[0]
            competitors = comps.get("competitors", [])
            if len(competitors) != 2:
                continue

            team_names = []
            scores = []
            for c in competitors:
                team = c.get("team", {})
                name = team.get("displayName", "").lower()
                abbrev = team.get("abbreviation", "").lower()
                short = team.get("shortDisplayName", "").lower()
                team_names.append((name, abbrev, short))
                scores.append(c.get("score", "0"))

            # Try to match teams to slug/question
            matched = 0
            for name, abbrev, short in team_names:
                if abbrev in text or short in text or name in text:
                    matched += 1
                # Also try first 4 chars of team name
                if len(name) > 3 and name[:4] in text:
                    matched += 1

            if matched >= 2:
                detail = status.get("detail", "")
                score_str = f"{team_names[0][2]} {scores[0]} - {team_names[1][2]} {scores[1]} ({detail})"
                return {
                    "state": "in",
                    "detail": detail,
                    "score_summary": score_str,
                    "scores": scores,
                    "team_names": team_names,
                }

    except Exception as e:
        logger.debug("ESPN live check error: %s", e)

    return None


def find_live_dip_candidates(
    markets: list,
    portfolio_positions: dict,
    exited_markets: set,
    get_clob_midpoint,
    max_concurrent: int = 2,
    min_drop_pct: float = 0.10,
) -> list[LiveDipCandidate]:
    """Scan markets for live-dip entry opportunities.

    Args:
        markets: List of market objects from scanner
        portfolio_positions: Current positions (to avoid duplicates)
        exited_markets: Set of condition_ids we've already exited
        get_clob_midpoint: Function to get current CLOB price
        max_concurrent: Max simultaneous live-dip positions
        min_drop_pct: Minimum price drop to trigger entry (default 10%)

    Returns:
        List of LiveDipCandidate objects ready for entry
    """
    # Count existing live-dip positions
    current_dips = sum(
        1 for p in portfolio_positions.values()
        if getattr(p, "entry_reason", "") == "live_dip"
    )
    if current_dips >= max_concurrent:
        return []

    candidates = []

    for m in markets:
        # Skip if already in portfolio or exited
        if m.condition_id in portfolio_positions:
            continue
        if m.condition_id in exited_markets:
            continue

        # Get current CLOB price
        mid = get_clob_midpoint(m.yes_token_id)
        if not mid or mid <= 0:
            continue

        # We need a pre-match price reference
        # Use the market's original yes_price from Gamma (set at discovery)
        pre_match = m.yes_price
        if not pre_match or pre_match <= 0:
            continue

        current_yes = mid

        # Determine who was the favorite pre-match (65%+ = real favorite, consistent with rest of system)
        if pre_match > 0.65:
            # YES was favorite, check if YES dropped
            drop = pre_match - current_yes
            drop_pct = drop / pre_match
            if drop_pct >= min_drop_pct:
                direction = "BUY_YES"
                candidate_price = current_yes
            else:
                continue
        elif pre_match < 0.35:
            # NO was favorite, check if NO dropped (= YES rose)
            no_pre = 1 - pre_match
            no_current = 1 - current_yes
            drop = no_pre - no_current
            drop_pct = drop / no_pre
            if drop_pct >= min_drop_pct:
                direction = "BUY_NO"
                candidate_price = no_current
            else:
                continue
        else:
            # Not a clear favorite (<65%), skip
            continue

        # Confirm match is live via ESPN
        espn = check_espn_live(m.slug, m.question)
        if not espn:
            continue

        # Score-based losing check: skip if favorite is losing badly
        # If favorite dropped AND is behind on scoreboard, recovery is unlikely
        try:
            scores = espn.get("scores", [])
            if len(scores) == 2:
                s0, s1 = int(scores[0]), int(scores[1])
                # Determine which team is the favorite based on direction
                if direction == "BUY_YES":
                    # YES team is favorite (team index 0 typically = home)
                    fav_behind = s0 < s1
                    deficit = s1 - s0
                else:
                    # NO team is favorite (team index 1)
                    fav_behind = s1 < s0
                    deficit = s0 - s1
                # Skip if favorite is losing by significant margin AND price dropped a lot
                if fav_behind and deficit >= 7 and drop_pct >= 0.20:
                    logger.info("Live dip skip (losing badly): %s | deficit=%d drop=%.0f%%",
                                m.slug[:40], deficit, drop_pct * 100)
                    continue
        except (ValueError, TypeError, IndexError):
            pass  # Can't parse scores — proceed anyway

        candidates.append(LiveDipCandidate(
            condition_id=m.condition_id,
            slug=m.slug,
            question=m.question,
            pre_match_price=pre_match,
            current_price=current_yes,
            drop_pct=drop_pct,
            direction=direction,
            espn_status=espn["state"],
            score_summary=espn["score_summary"],
        ))

        time.sleep(0.3)  # Rate limit ESPN

    # Sort by biggest drop first
    candidates.sort(key=lambda c: c.drop_pct, reverse=True)

    # Limit to available slots
    available = max_concurrent - current_dips
    return candidates[:available]
