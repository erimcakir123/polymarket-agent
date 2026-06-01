"""Market type dispatch → P(YES) anchor.

Per-market pricer'lar:
  moneyline → blend(Elo, P(score_diff>0))
  totals    → P(proj_total > line)  (normal approx, std dev sezon kalibrasyonu)
  spreads   → P(margin > line)

Lig-spesifik parametreler config'den gelir (home_advantage, blend_elo,
margin_std, total_std). NBA/WNBA/NCAAB/WNCAAB/Euroleague farklı tuning'ler.
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


# Lig parametresi geçirilmezse default fallback (NBA empiriği).
# Backward compat: Faz 1 testleri parametre vermeden çağırır.
_MARGIN_STD_NBA_DEFAULT = 11.0
_TOTAL_STD_NBA_DEFAULT = 20.0


def _phi(z: float) -> float:
    """Standard normal CDF Φ(z) — math.erf üzerinden."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _moneyline_from_pace(proj: GameProjection, margin_std: float) -> float:
    """Beklenen margin'in 0'dan büyük olma olasılığı (normal varsayım)."""
    return _phi(proj.margin / margin_std)


def compute_market_anchor(
    market_type: str,
    home_elo: EloRating, away_elo: EloRating,
    home_eff: TeamEfficiency, away_eff: TeamEfficiency,
    home_advantage: float, blend_elo: float,
    line: Optional[float],
    margin_std: float = _MARGIN_STD_NBA_DEFAULT,
    total_std: float = _TOTAL_STD_NBA_DEFAULT,
) -> Optional[float]:
    """Market type'a göre P(YES) anchor üret.

    line: totals için over/under sayısı, spreads için home spread (negatif = home favored).
    moneyline için None.
    margin_std/total_std: lig-spesifik (NBA 11/20, WNBA 9.5/16, NCAAB 13/22, EUL 10/16).
    Bilinmeyen market_type veya gerekli parametre None → None.
    """
    mt = market_type.lower()
    proj = project_game(home_eff, away_eff)
    if mt == "moneyline":
        p_elo = expected_win_prob(home_elo, away_elo, home_advantage)
        p_pace = _moneyline_from_pace(proj, margin_std)
        return blend_elo * p_elo + (1.0 - blend_elo) * p_pace
    if mt == "totals":
        if line is None:
            return None
        z = (proj.total - line) / total_std
        return _phi(z)
    if mt == "spreads":
        if line is None:
            return None
        # Home spread negatif = home favored. Cover için margin > -line.
        threshold = -line
        z = (proj.margin - threshold) / margin_std
        return _phi(z)
    return None
