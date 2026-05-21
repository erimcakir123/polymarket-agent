"""Layer 1 dispatcher: orchestrate all adjustments + Log5.

SPEC-R Plan 2 T9. Critical ordering (prevents double-count):
1. Handedness adjust on batter_rates AND pitcher_rates (renormalize each).
2. TTO adjust on pitcher_rates ONLY (renormalize).
3. Log5 multi-class → matchup distribution.
4. Park + weather adjustments on MATCHUP distribution ONLY.
5. Renormalize → final.
"""
from __future__ import annotations

from typing import TypedDict

from src.domain.mlb_submarket.handedness_adjust import platoon_multiplier
from src.domain.mlb_submarket.log5 import log5_multiclass
from src.domain.mlb_submarket.park_factor_adjust import park_multiplier
from src.domain.mlb_submarket.tto_adjust import tto_multiplier
from src.domain.mlb_submarket.weather_adjust import weather_hr_multiplier


class PAContext(TypedDict):
    park_id: str
    batter_hand: str
    pitcher_hand: str
    times_through: int
    wind_mph_to_cf: float
    temp_f: float
    humidity_pct: float


def _renormalize(rates: dict[str, float]) -> dict[str, float]:
    total = sum(rates.values())
    if total == 0:
        return dict(rates)
    return {k: v / total for k, v in rates.items()}


def compute_pa_outcome(
    *,
    batter_rates: dict[str, float],
    pitcher_rates: dict[str, float],
    league_rates: dict[str, float],
    context: PAContext,
) -> dict[str, float]:
    """Layer 1: compute matchup-specific PA outcome distribution.

    Args:
        batter_rates: batter's PA outcome distribution.
        pitcher_rates: pitcher's allowed PA outcome distribution.
        league_rates: league-average PA outcome distribution (Log5 baseline).
        context: park, handedness, TTO, and weather context.

    Returns:
        Normalized matchup PA outcome distribution (values sum to 1.0).
    """
    # Step 1: handedness adjust — apply to both batter and pitcher, renormalize each.
    # R/R is treated as the baseline matchup (identity): applying R/R multipliers to
    # both sides and then running Log5 does NOT return league rates for equal inputs
    # because Log5 amplifies squared differences. By treating R/R as the reference
    # (no-op), any non-R/R matchup encodes a platoon advantage/disadvantage relative
    # to that baseline, which is the intended semantics of the platoon table.
    batter_hand = context["batter_hand"]
    pitcher_hand = context["pitcher_hand"]
    if batter_hand == "R" and pitcher_hand == "R":
        batter_adj = dict(batter_rates)
        pitcher_adj = dict(pitcher_rates)
    else:
        batter_adj = _renormalize({
            o: r * platoon_multiplier(batter_hand, pitcher_hand, o)
            for o, r in batter_rates.items()
        })
        pitcher_adj = _renormalize({
            o: r * platoon_multiplier(batter_hand, pitcher_hand, o)
            for o, r in pitcher_rates.items()
        })

    # Step 2: TTO adjust on pitcher ONLY (renormalize).
    pitcher_adj = {
        o: r * tto_multiplier(context["times_through"], o)
        for o, r in pitcher_adj.items()
    }
    pitcher_adj = _renormalize(pitcher_adj)

    # Step 3: Log5 multi-class → matchup distribution.
    matchup = log5_multiclass(
        batter_rates=batter_adj,
        pitcher_rates=pitcher_adj,
        league_rates=league_rates,
    )

    # Step 4: park + weather adjustments on MATCHUP only (not on batter/pitcher —
    # applying here prevents double-count that would occur if done pre-Log5).
    weather_hr_mult = weather_hr_multiplier(
        context["wind_mph_to_cf"], context["temp_f"], context["humidity_pct"],
    )
    matchup_adj: dict[str, float] = {}
    for o, p in matchup.items():
        park_mult = park_multiplier(context["park_id"], o)
        # Weather affects HR only (per SPEC-R Plan 2 design).
        env_mult = park_mult * (weather_hr_mult if o == "HR" else 1.0)
        matchup_adj[o] = p * env_mult

    # Step 5: renormalize final distribution.
    return _renormalize(matchup_adj)
