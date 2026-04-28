"""NHL puck line (-1.5) cover probability via Skellam distribution.

Skellam = difference of two independent Poisson random variables.
Home goals ~ Poisson(λ_home × t), Away goals ~ Poisson(λ_away × t)
diff_change = home_new - away_new ~ Skellam(μ1=λ_home×t, μ2=λ_away×t)

Cover condition: final_margin >= 2 (Polymarket -1.5 favori convention).
final_margin = current_margin + diff_change → diff_change >= 2 - current_margin

P(cover) = P(Skellam(μ1, μ2) >= 2 - current_margin)
        = 1 - skellam.cdf(2 - current_margin - 1, μ1, μ2)
        = 1 - skellam.cdf(1 - current_margin, μ1, μ2)

NHL league avg: 6.142 gol/maç → per-team-per-second:
  λ_per_team = 6.142 / 2 / 3600 = 0.000853 (5v5 avg)
"""
from __future__ import annotations

from scipy.stats import skellam

# Per-team scoring rate (5v5 average, league avg 2026)
LAMBDA_5V5_PER_TEAM_PER_SECOND: float = 0.000853

# Empty net modifier — last 3 min + 1 goal deficit, λ ×1.8 (geri dönmeye çalışan takım)
LAMBDA_EMPTY_NET_MULT: float = 1.8


def skellam_p_favorite_covers_minus_1_5(
    current_margin: int,
    seconds_remaining: int,
    lambda_home: float = LAMBDA_5V5_PER_TEAM_PER_SECOND,
    lambda_away: float = LAMBDA_5V5_PER_TEAM_PER_SECOND,
) -> float:
    """P(home favori final_margin >= 2 | current_margin, seconds_remaining).

    Args:
      current_margin: home_score - away_score (favori bakış açısı)
      seconds_remaining: regulation kalan saniye (OT/SO ayrı handle)
      lambda_home/away: per-second per-team scoring rate

    Returns:
      Cover olasılığı [0, 1].
    """
    if seconds_remaining <= 0:
        return 1.0 if current_margin >= 2 else 0.0

    mu_home = lambda_home * seconds_remaining
    mu_away = lambda_away * seconds_remaining

    threshold = 2 - current_margin  # diff_change >= threshold için cover
    # P(X >= threshold) = 1 - P(X <= threshold - 1) = 1 - cdf(threshold - 1)
    p = 1.0 - skellam.cdf(threshold - 1, mu_home, mu_away)
    return float(max(0.0, min(1.0, p)))
