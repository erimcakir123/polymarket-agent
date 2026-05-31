"""Market type dispatch → P(YES) anchor.

Per-market pricer'lar:
  moneyline → blend(Elo, P(score_diff>0))
  totals    → P(proj_total > line)  (normal approx, std dev sezon kalibrasyonu)
  spreads   → P(margin > line)

Lig-spesifik parametreler config'den gelir (home_advantage, blend_elo).
Saf domain — I/O yok.
"""
from __future__ import annotations

import math
from typing import Optional

from src.domain.pricing.basketball.pace_efficiency import (
    GameProjection, TeamEfficiency, project_game,
)
from src.domain.pricing.basketball.team_elo import (
    EloRating, expected_win_prob,
)


# NBA empirik margin std dev (regular season, FiveThirtyEight): ~11
# WNBA: ~9.5. Plan 1.C kalibrasyonunda lig-başına revize.
_MARGIN_STD_DEFAULT = 11.0
# NBA total std dev: ~20 (totals dağılımı margin'den daha geniş)
_TOTAL_STD_DEFAULT = 20.0


def _phi(z: float) -> float:
    """Standard normal CDF Φ(z) — math.erf üzerinden."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _moneyline_from_pace(proj: GameProjection) -> float:
    """Beklenen margin'in 0'dan büyük olma olasılığı (normal varsayım)."""
    return _phi(proj.margin / _MARGIN_STD_DEFAULT)


def compute_market_anchor(
    market_type: str,
    home_elo: EloRating, away_elo: EloRating,
    home_eff: TeamEfficiency, away_eff: TeamEfficiency,
    home_advantage: float, blend_elo: float,
    line: Optional[float],
) -> Optional[float]:
    """Market type'a göre P(YES) anchor üret.

    line: totals için over/under sayısı, spreads için home spread (negatif = home favored).
    moneyline için None.
    Bilinmeyen market_type veya gerekli parametre None → None.
    """
    mt = market_type.lower()
    proj = project_game(home_eff, away_eff)
    if mt == "moneyline":
        p_elo = expected_win_prob(home_elo, away_elo, home_advantage)
        p_pace = _moneyline_from_pace(proj)
        return blend_elo * p_elo + (1.0 - blend_elo) * p_pace
    if mt == "totals":
        if line is None:
            return None
        z = (proj.total - line) / _TOTAL_STD_DEFAULT
        return _phi(z)
    if mt == "spreads":
        if line is None:
            return None
        # Home spread negatif = home favored. Cover için margin > -line gerekir.
        # Örnek: line=-3.5 → home_cover ⇔ margin > 3.5.
        threshold = -line
        z = (proj.margin - threshold) / _MARGIN_STD_DEFAULT
        return _phi(z)
    return None
