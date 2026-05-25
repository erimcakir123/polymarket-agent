"""Light-cycle match_start_iso refresh from Polymarket gameStartTime.

Bot caches match_start_iso at position open (gamma_client._parse_market). If
Polymarket reschedules the match later, that cache becomes stale:
  * LIVE badge fires falsely (cached_start < now, real start in future)
  * graduated_sl uses wrong elapsed_pct (over-aggressive SL on positions that
    haven't actually started yet)

This helper re-fetches gameStartTime per open position and updates the
Position.match_start_iso field in place. Caller (tennis_agent run_light_cycle)
invokes every N ticks (cfg.tennis.match_start_refresh_every_n_ticks).

Spec: docs/superpowers/plans/2026-05-26-espn-match-start-refresh.md
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

from src.infrastructure.apis.gamma_client import normalize_game_start

logger = logging.getLogger(__name__)


class _PositionLike(Protocol):
    """Minimal Position interface — keeps orchestration loosely coupled to model."""
    condition_id: str
    match_start_iso: str


class _PortfolioLike(Protocol):
    """Minimal Portfolio interface — positions is condition_id -> Position dict."""
    positions: dict[str, _PositionLike]


class _GammaClientLike(Protocol):
    """Minimal GammaClient interface — only the single-market fetch is used."""
    def fetch_market_by_condition_id(self, condition_id: str) -> dict[str, Any] | None: ...


def refresh_match_start_for_open_positions(
    portfolio: _PortfolioLike,
    gamma_client: _GammaClientLike,
) -> int:
    """Re-fetch gameStartTime from gamma for each open position; update in-place.

    Mutates Position.match_start_iso when Polymarket returns a different value.
    Pydantic v2 models permit attribute assignment by default — Position model
    has no model_config frozen flag.

    Args:
        portfolio: holds the open positions list.
        gamma_client: infra client with fetch_market_by_condition_id method.

    Returns:
        Count of positions whose match_start_iso changed this call.
    """
    updated = 0
    # list() snapshot of values — defensive against mid-iteration portfolio mutation.
    for pos in list(portfolio.positions.values()):
        cid = pos.condition_id
        if not cid:
            continue
        market = gamma_client.fetch_market_by_condition_id(cid)
        if not market:
            continue
        new_start = normalize_game_start(market.get("gameStartTime"))
        if new_start and new_start != pos.match_start_iso:
            old = pos.match_start_iso
            pos.match_start_iso = new_start
            updated += 1
            logger.info(
                "match_start refresh: %s changed %s -> %s",
                cid[:16], old, new_start,
            )
    return updated


def maybe_refresh_match_start(
    tick_count: int,
    every_n_ticks: int,
    portfolio: _PortfolioLike,
    gamma_client: _GammaClientLike | None,
) -> int:
    """Light-cycle trigger gate — fires refresh only when tick_count % N == 0.

    Wraps refresh_match_start_for_open_positions with the every-N-ticks
    cadence + None gamma_client guard + exception swallow (light cycle must
    never crash on optional infra). Keeps tennis_agent.run_light_cycle to a
    single line and stays under the 400-line ARCH_GUARD limit.

    Args:
        tick_count: current light cycle tick counter (already incremented).
        every_n_ticks: 0 disables; positive N fires every Nth tick.
        portfolio: open positions container.
        gamma_client: infra client or None (test/legacy bypass).

    Returns:
        Count of positions updated this call (0 if skipped or no changes).
    """
    if every_n_ticks <= 0 or gamma_client is None:
        return 0
    if tick_count % every_n_ticks != 0:
        return 0
    try:
        n_updated = refresh_match_start_for_open_positions(portfolio, gamma_client)
        if n_updated > 0:
            logger.info("Light cycle refresh: %d positions got new match_start", n_updated)
        return n_updated
    except Exception as e:
        logger.warning("match_start refresh failed: %s", e)
        return 0
