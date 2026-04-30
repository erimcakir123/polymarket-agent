"""MLB entry filter chain — pure decision function.

Order: hard gates first (skip on first fail), then fair_price, gap, sizing.
ARCH-pure: no I/O, all thresholds from cfg.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from src.domain.math.mlb_pitcher_adjustment import matchup_winpct
from src.domain.math.mlb_run_line_probability import p_team_covers_runline
from src.domain.math.mlb_totals_probability import p_over_totals
from src.domain.sports.mlb_question_parser import MLBMarketType


@dataclass(frozen=True)
class MLBEntryConfig:
    rain_skip_threshold: float
    rain_partial_threshold: float
    pre_game_window_min_hours: float
    pre_game_window_max_hours: float
    min_volume_usdc: float
    min_liquidity_usdc: float
    min_polymarket_price: float
    max_polymarket_price: float
    gap_threshold: float
    position_cap_pct: float
    max_position_usdc: float
    forbid_runline_minus_15_favorite: bool


@dataclass(frozen=True)
class MLBEntryDecision:
    action: Literal["BUY"]
    size_usdc: float
    fair_price: float
    edge: float
    reason: str


_QUARTER_KELLY: float = 0.25
_RAIN_PARTIAL_MULTIPLIER: float = 0.7
_DEFAULT_RL_LINE: float = 1.5
_DEFAULT_TOTALS_LINE: float = 8.5


def _check_hard_gates(market: Any, enriched: Any, cfg: MLBEntryConfig) -> str | None:
    """Return reason string if gate fails, else None.

    Gate order: pitcher → rain → RL-15-favorite → window → volume → liquidity → price.
    """
    if not enriched.pitcher_confirmed_home or not enriched.pitcher_confirmed_away:
        return "PITCHER_UNCONFIRMED"

    if enriched.rain_chance >= cfg.rain_skip_threshold:
        return "RAIN_SKIP"

    if (
        market.intent.market_type == MLBMarketType.RUN_LINE
        and cfg.forbid_runline_minus_15_favorite
        and market.intent.line == 1.5
        and market.intent.is_favorite_side is True
    ):
        return "RUNLINE_MINUS_15_FORBIDDEN"

    hours_to_game = enriched.seconds_to_game_start / 3600.0
    if not (cfg.pre_game_window_min_hours <= hours_to_game <= cfg.pre_game_window_max_hours):
        return "OUTSIDE_PRE_GAME_WINDOW"

    if market.volume_24h < cfg.min_volume_usdc:
        return "LOW_VOLUME"

    if market.liquidity < cfg.min_liquidity_usdc:
        return "LOW_LIQUIDITY"

    if not (cfg.min_polymarket_price <= market.polymarket_price <= cfg.max_polymarket_price):
        return "PRICE_OUT_OF_RANGE"

    return None


def _compute_fair_price(market: Any, enriched: Any) -> float | None:
    """Compute internal-model fair price for the market side.

    Routes to the correct math module based on market type.
    Returns None for unsupported market types.
    """
    intent = market.intent

    if intent.market_type == MLBMarketType.MONEYLINE:
        p_home = matchup_winpct(
            home_winpct=enriched.home_season_winpct,
            away_winpct=enriched.away_season_winpct,
            home_pitcher_era=enriched.home_pitcher_era,
            away_pitcher_era=enriched.away_pitcher_era,
        )
        return p_home if intent.side_team == intent.team_a else (1.0 - p_home)

    if intent.market_type == MLBMarketType.RUN_LINE:
        if intent.side_team == intent.team_a:
            our_rs = enriched.home_runs_per_game
            opp_rs = enriched.away_runs_per_game
        else:
            our_rs = enriched.away_runs_per_game
            opp_rs = enriched.home_runs_per_game
        return p_team_covers_runline(
            team_runs_per_game=our_rs,
            opp_runs_per_game=opp_rs,
            line=intent.line or _DEFAULT_RL_LINE,
            is_favorite=bool(intent.is_favorite_side),
        )

    if intent.market_type == MLBMarketType.TOTALS:
        p_over = p_over_totals(
            home_runs=enriched.home_runs_per_game,
            away_runs=enriched.away_runs_per_game,
            line=intent.line or _DEFAULT_TOTALS_LINE,
            park_factor=enriched.park_factor.runs,
            weather_run_bias=enriched.weather_run_bias,
        )
        return p_over if intent.totals_side == "OVER" else (1.0 - p_over)

    return None


def _compute_size(
    edge: float,
    price: float,
    bankroll: float,
    cfg: MLBEntryConfig,
    rain_chance: float,
) -> float:
    """Quarter-Kelly with absolute caps + rain partial multiplier.

    Kelly fraction = edge / (1 - price) → scaled by 0.25 → capped by
    position_cap_pct × bankroll and max_position_usdc.
    Rain partial zone reduces size by RAIN_PARTIAL_MULTIPLIER.
    """
    if price <= 0 or price >= 1:
        return 0.0
    kelly_fraction = max(0.0, edge / max(0.01, 1.0 - price))
    quarter_kelly_fraction = _QUARTER_KELLY * kelly_fraction
    size = bankroll * quarter_kelly_fraction
    size = min(size, bankroll * cfg.position_cap_pct)
    size = min(size, cfg.max_position_usdc)
    if cfg.rain_partial_threshold <= rain_chance < cfg.rain_skip_threshold:
        size *= _RAIN_PARTIAL_MULTIPLIER
    return size


def apply_mlb_entry_filters(
    market: Any,
    enriched: Any,
    cfg: MLBEntryConfig,
    bankroll: float,
) -> MLBEntryDecision | None:
    """MLB entry filter chain. Returns decision or None for SKIP.

    Pipeline:
    1. Hard gates (pitcher, rain, RL-favorite, window, volume, liquidity, price)
    2. Fair price computation (ML / RL / Totals routed to math modules)
    3. Edge gap check
    4. Quarter-Kelly sizing with caps
    """
    if enriched is None:
        return None

    gate_reason = _check_hard_gates(market, enriched, cfg)
    if gate_reason:
        return None

    fair_price = _compute_fair_price(market, enriched)
    if fair_price is None:
        return None

    edge = fair_price - market.polymarket_price
    if edge < cfg.gap_threshold:
        return None

    size = _compute_size(edge, market.polymarket_price, bankroll, cfg, enriched.rain_chance)
    if size <= 0:
        return None

    return MLBEntryDecision(
        action="BUY",
        size_usdc=size,
        fair_price=fair_price,
        edge=edge,
        reason="MLB_EDGE_DETECTED",
    )
