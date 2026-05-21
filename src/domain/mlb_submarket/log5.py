"""Log5 multi-class outcome probability (Haechrel SABR 2014).

SPEC-R Plan 2 T8.

For binary outcomes (Bill James 1980s):
    P(outcome) = (b·p / L) / ((b·p / L) + ((1-b)(1-p)/(1-L)))

Multi-class generalization (Haechrel "Estimating League Average Skill Sets",
SABR Journal 2014, §3):
    or_i = (batter_p_i / league_p_i) × (pitcher_p_i / league_p_i)
    unnormalized_i = or_i × league_p_i
    P(i) = unnormalized_i / sum(unnormalized_j for all j)

Reduces to James formula for k=2 (proof: Haechrel §3.2).

Bias note: Morey & Cohen 2015 (JSA) — Log5 overestimates favored side in
elite-vs-weak extremes. Plan 4 backtest must validate calibration.
"""
from __future__ import annotations


def log5_multiclass(
    batter_rates: dict[str, float],
    pitcher_rates: dict[str, float],
    league_rates: dict[str, float],
) -> dict[str, float]:
    """Compute matchup-specific outcome distribution.

    Args:
        batter_rates: batter's PA outcome distribution (dict outcome → probability).
        pitcher_rates: pitcher's allowed PA outcome distribution.
        league_rates: league-average PA outcome distribution (baseline).

    All three must have the SAME set of keys.

    Returns:
        Normalized matchup distribution (sum to 1.0).

    Raises:
        ValueError: if input key sets differ.
    """
    if not (batter_rates.keys() == pitcher_rates.keys() == league_rates.keys()):
        raise ValueError(
            "batter_rates, pitcher_rates, league_rates must have identical key sets"
        )

    unnormalized: dict[str, float] = {}
    for outcome in batter_rates:
        L = league_rates[outcome]
        if L == 0.0:
            unnormalized[outcome] = 0.0
            continue
        b = batter_rates[outcome]
        p = pitcher_rates[outcome]
        or_i = (b / L) * (p / L)
        unnormalized[outcome] = or_i * L

    total = sum(unnormalized.values())
    if total == 0.0:
        # Degenerate case (everything zero). Fall back to league.
        return dict(league_rates)
    return {k: v / total for k, v in unnormalized.items()}
