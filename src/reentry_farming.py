"""Unified Re-entry Farming — enter/exit/re-enter the same match repeatedly.

After any profitable exit (TP, trailing stop, spike exit, scale_out_final),
the position is saved to a re-entry pool. On each cycle, the pool is checked
for dip opportunities using a 3-tier system with escalating requirements.

Key design decisions:
- NO additional AI cost — uses saved AI probability from original entry
- Thesis check: if price drops below original entry - 5¢, thesis is broken → block
- Profit protection: re-entry risk capped at 50% of realized profit from this market
- Event-level tracking: re-entries per event_id (not just condition_id)
- Resolve guard: re-entry positions auto-exit if price hits 95¢/5¢ (handled in main loop)
- No momentum confirmation (user feedback: "çıkınca tam çıkıyor")

Tiers:
  Tier 1: 4¢ or 6% dip, 80% size, 2-cycle stabilization
  Tier 2: 7¢ or 10% dip, 60% size, 3-cycle stabilization
  Tier 3: 11¢ or 15% dip, 40% size, 3-cycle stabilization

Max re-entries per market: sport-dependent (BO1:2, BO3:3, BO5:3, NBA:3, NHL:2)

TODO(live): Add WebSocket price feeds for real-time re-entry checks
TODO(live): Add orderbook depth check before re-entry (skip if depth < $100)
TODO(live): Add liquidity impact check (if order > 20% of book, halve size)
TODO(esports-api): Integrate PandaScore/HLTV for live score → score-based probability adjustment
TODO(esports-api): Detect map breaks and pause re-entry evaluation during breaks
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REENTRY_TIERS = [
    {"tier": 1, "min_dip_cents": 0.04, "min_dip_pct": 0.06, "size_mult": 0.80, "min_edge": 0.07, "stabilize_cycles": 2},
    {"tier": 2, "min_dip_cents": 0.07, "min_dip_pct": 0.10, "size_mult": 0.60, "min_edge": 0.07, "stabilize_cycles": 3},
    {"tier": 3, "min_dip_cents": 0.11, "min_dip_pct": 0.15, "size_mult": 0.40, "min_edge": 0.10, "stabilize_cycles": 3},
]

MAX_REENTRIES = {
    "bo1": 2, "bo3": 3, "bo5": 3, "nba": 3, "nhl": 2, "default": 2,
}

# Freefall detection thresholds
FREEFALL_ESPORTS = {"drop": 0.15, "cycles": 5}
FREEFALL_SPORTS = {"drop": 0.20, "cycles": 8}

# Max age of original AI analysis before blocking re-entry
MAX_ANALYSIS_AGE_CYCLES = 240  # ~4 hours at 1 min/cycle

# Profit protection: max 50% of realized profit can be risked on re-entries
PROFIT_RISK_CAP = 0.50

# Thesis broken: if price drops below (original_entry - THESIS_BROKEN_BUFFER), block
THESIS_BROKEN_BUFFER = 0.05  # 5¢

# Price extremes: don't re-enter if token price > 85¢ or < 15¢
PRICE_EXTREME_HIGH = 0.85
PRICE_EXTREME_LOW = 0.15


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ReentryCandidate:
    """A market saved for potential re-entry after profitable exit."""
    condition_id: str
    event_id: str
    slug: str
    question: str
    direction: str
    token_id: str
    ai_probability: float
    confidence: str
    original_entry_price: float  # First-ever entry price (for thesis check)
    last_exit_price: float       # Price at most recent exit
    last_exit_cycle: int
    end_date_iso: str
    match_start_iso: str
    sport_tag: str
    number_of_games: int
    was_scouted: bool
    reentry_count: int = 0       # How many times we've re-entered this market
    total_realized_profit: float = 0.0  # Sum of all realized P&L from this market
    total_reentry_risk: float = 0.0     # Sum of all re-entry position sizes
    price_history: list = field(default_factory=list)  # Last N prices for stabilization
    created_at: float = field(default_factory=time.time)


class ReentryPool:
    """Manages the unified re-entry pool across all exit types."""

    def __init__(self, path: str = "logs/reentry_pool.json"):
        self._path = Path(path)
        self._pool: dict[str, ReentryCandidate] = {}
        self._load()

    # ------ Pool management ------

    def add(
        self,
        condition_id: str,
        event_id: str,
        slug: str,
        question: str,
        direction: str,
        token_id: str,
        ai_probability: float,
        confidence: str,
        original_entry_price: float,
        exit_price: float,
        exit_cycle: int,
        end_date_iso: str,
        match_start_iso: str,
        sport_tag: str,
        number_of_games: int,
        was_scouted: bool,
        realized_pnl: float,
    ) -> None:
        """Add or update a market in the re-entry pool after a profitable exit."""

        existing = self._pool.get(condition_id)
        if existing:
            # Update existing entry (subsequent exit from same market)
            existing.last_exit_price = exit_price
            existing.last_exit_cycle = exit_cycle
            existing.total_realized_profit += realized_pnl
            existing.price_history = []
            logger.info("Re-entry pool UPDATE: %s | exits=%d | total_profit=$%.2f",
                        slug[:40], existing.reentry_count, existing.total_realized_profit)
        else:
            self._pool[condition_id] = ReentryCandidate(
                condition_id=condition_id,
                event_id=event_id,
                slug=slug,
                question=question,
                direction=direction,
                token_id=token_id,
                ai_probability=ai_probability,
                confidence=confidence,
                original_entry_price=original_entry_price,
                last_exit_price=exit_price,
                last_exit_cycle=exit_cycle,
                end_date_iso=end_date_iso,
                match_start_iso=match_start_iso,
                sport_tag=sport_tag,
                number_of_games=number_of_games,
                was_scouted=was_scouted,
                total_realized_profit=realized_pnl,
            )
            logger.info("Re-entry pool ADD: %s | profit=$%.2f | AI=%.0f%% | %s",
                        slug[:40], realized_pnl, ai_probability * 100, direction)
        self._save()

    def remove(self, condition_id: str) -> None:
        self._pool.pop(condition_id, None)
        self._save()

    def get(self, condition_id: str) -> Optional[ReentryCandidate]:
        return self._pool.get(condition_id)

    def record_reentry(self, condition_id: str, size_usdc: float) -> None:
        """Record that a re-entry was executed."""
        c = self._pool.get(condition_id)
        if c:
            c.reentry_count += 1
            c.total_reentry_risk += size_usdc
            self._save()

    def update_price(self, condition_id: str, price: float) -> None:
        """Track price for stabilization check."""
        c = self._pool.get(condition_id)
        if c:
            c.price_history.append(price)
            if len(c.price_history) > 10:
                c.price_history = c.price_history[-10:]

    @property
    def candidates(self) -> dict[str, ReentryCandidate]:
        return self._pool

    # ------ Persistence ------

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for cid, c in self._pool.items():
            d = asdict(c)
            data[cid] = d
        self._path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            for cid, d in data.items():
                # Handle missing fields for backward compat
                d.setdefault("price_history", [])
                d.setdefault("created_at", 0)
                d.setdefault("total_reentry_risk", 0.0)
                self._pool[cid] = ReentryCandidate(**d)
            logger.info("Loaded %d re-entry candidates from disk", len(self._pool))
        except Exception as e:
            logger.warning("Failed to load reentry pool: %s", e)

    def cleanup_expired(self, current_cycle: int) -> None:
        """Remove entries that are too old or match has ended."""
        expired = []
        now = datetime.now(timezone.utc)
        for cid, c in self._pool.items():
            # Analysis too old
            if current_cycle - c.last_exit_cycle > MAX_ANALYSIS_AGE_CYCLES:
                expired.append(cid)
                continue
            # Match ended (by end_date_iso)
            if c.end_date_iso:
                try:
                    end_dt = datetime.fromisoformat(c.end_date_iso.replace("Z", "+00:00"))
                    if now > end_dt:
                        expired.append(cid)
                        continue
                except (ValueError, TypeError):
                    pass
        for cid in expired:
            logger.info("Re-entry pool EXPIRED: %s", self._pool[cid].slug[:40])
            del self._pool[cid]
        if expired:
            self._save()


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------

def _get_max_reentries(sport_tag: str, number_of_games: int) -> int:
    """Get max re-entries based on sport/format."""
    st = sport_tag.lower() if sport_tag else ""
    if st in ("nhl", "hockey"):
        return MAX_REENTRIES["nhl"]
    if st in ("nba", "basketball", "cbb"):
        return MAX_REENTRIES["nba"]
    if number_of_games >= 5:
        return MAX_REENTRIES["bo5"]
    if number_of_games >= 3:
        return MAX_REENTRIES["bo3"]
    if number_of_games == 1:
        return MAX_REENTRIES["bo1"]
    return MAX_REENTRIES["default"]


def _get_effective_price(price: float, direction: str) -> float:
    """Get the effective price for our side (YES or NO)."""
    return (1.0 - price) if direction == "BUY_NO" else price


def check_reentry(
    candidate: ReentryCandidate,
    current_yes_price: float,
    current_cycle: int,
    portfolio_positions: dict,
    held_event_ids: set,
    daily_reentry_count: int,
) -> dict:
    """Evaluate whether to re-enter a market from the farming pool.

    Returns {"action": "ENTER"|"WAIT"|"BLOCK", "tier": int, "size_mult": float, "reason": str}
    """
    c = candidate
    eff_price = _get_effective_price(current_yes_price, c.direction)
    eff_exit = _get_effective_price(c.last_exit_price, c.direction)
    eff_entry = _get_effective_price(c.original_entry_price, c.direction)
    eff_ai = c.ai_probability if c.direction == "BUY_YES" else (1.0 - c.ai_probability)

    # --- HARD BLOCKS ---

    # Match timing: don't re-enter if match is too far along
    # Rule: block if >66% of match elapsed (past first 1/3 of second half)
    if c.match_start_iso and c.end_date_iso:
        try:
            _ms = datetime.fromisoformat(c.match_start_iso.replace("Z", "+00:00"))
            _ed = datetime.fromisoformat(c.end_date_iso.replace("Z", "+00:00"))
            _now = datetime.now(timezone.utc)
            _total = (_ed - _ms).total_seconds()
            if _total > 0:
                elapsed_pct = max(0.0, min(1.0, (_now - _ms).total_seconds() / _total))
                if elapsed_pct >= 0.66:
                    return _block(f"Match too far along: {elapsed_pct:.0%} elapsed")
        except (ValueError, TypeError):
            pass

    # AI says losing side (prob < 50%) — don't re-enter a likely loser
    if eff_ai < 0.50:
        return _block(f"AI says losing side: {eff_ai:.0%}")

    # Already in portfolio
    if c.condition_id in portfolio_positions:
        return _block("Already in portfolio")

    # Same event already held (duplicate guard)
    if c.event_id and c.event_id in held_event_ids:
        return _block("Same event already held")

    # Max re-entries reached
    max_re = _get_max_reentries(c.sport_tag, c.number_of_games)
    if c.reentry_count >= max_re:
        return _block(f"Max re-entries ({max_re}) reached")

    # Analysis too old
    cycles_since_exit = current_cycle - c.last_exit_cycle
    if cycles_since_exit > MAX_ANALYSIS_AGE_CYCLES:
        return _block("Analysis too stale (>4h)")

    # Price extremes — don't buy at 85¢+ or 15¢-
    if eff_price >= PRICE_EXTREME_HIGH or eff_price <= PRICE_EXTREME_LOW:
        return _block(f"Price extreme: {eff_price:.0%}")

    # Thesis broken — price dropped below original entry - buffer
    if eff_price < eff_entry - THESIS_BROKEN_BUFFER:
        return _block(f"Thesis broken: price {eff_price:.0%} < entry {eff_entry:.0%} - 5¢")

    # Daily re-entry cap
    if daily_reentry_count >= 8:
        return _block("Daily re-entry limit (8) reached")

    # Profit protection — don't risk more than 50% of realized profit
    if c.total_realized_profit > 0 and c.total_reentry_risk >= c.total_realized_profit * PROFIT_RISK_CAP:
        return _block(f"Profit cap: risked ${c.total_reentry_risk:.2f} >= 50% of ${c.total_realized_profit:.2f}")

    # Freefall detection
    is_esports = c.sport_tag.lower() in ("cs2", "csgo", "valorant", "lol", "dota2", "val")
    ff = FREEFALL_ESPORTS if is_esports else FREEFALL_SPORTS
    actual_drop = eff_exit - eff_price
    if actual_drop > ff["drop"] and cycles_since_exit < ff["cycles"]:
        return _block(f"Freefall: {actual_drop:.0%} drop in {cycles_since_exit} cycles")

    # --- TIER EVALUATION ---
    tier_idx = c.reentry_count  # 0-indexed: first re-entry = tier 0 (Tier 1)
    if tier_idx >= len(REENTRY_TIERS):
        return _block("No more tiers available")

    tier = REENTRY_TIERS[tier_idx]

    # Required dip
    required_dip = max(tier["min_dip_cents"], eff_exit * tier["min_dip_pct"])
    if actual_drop < required_dip:
        return _wait(f"Dip {actual_drop:.3f} < required {required_dip:.3f} (Tier {tier['tier']})")

    # Edge check
    edge = eff_ai - eff_price
    if edge < tier["min_edge"]:
        return _wait(f"Edge {edge:.1%} < {tier['min_edge']:.1%}")

    # Stabilization check — price must not have dropped for N consecutive cycles
    history = c.price_history
    required_stable = tier["stabilize_cycles"]
    if len(history) < required_stable:
        return _wait(f"Not enough price history ({len(history)}/{required_stable})")

    recent = history[-required_stable:]
    # Check that each price is >= the one before it (not dropping)
    for i in range(1, len(recent)):
        if recent[i] < recent[i - 1] - 0.005:  # 0.5¢ tolerance
            return _wait(f"Still dropping: {recent}")

    # --- ALL CHECKS PASSED ---
    return {
        "action": "ENTER",
        "tier": tier["tier"],
        "size_mult": tier["size_mult"],
        "edge": edge,
        "adjusted_prob": eff_ai,
        "reason": f"Tier {tier['tier']}: dip={actual_drop:.3f}, edge={edge:.1%}, size={tier['size_mult']:.0%}",
    }


def _block(reason: str) -> dict:
    return {"action": "BLOCK", "reason": reason}


def _wait(reason: str) -> dict:
    return {"action": "WAIT", "reason": reason}
