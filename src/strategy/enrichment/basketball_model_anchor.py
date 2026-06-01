"""Basketball model anchor — Polymarket market_type → pricer dispatch.

Strategy layer. Tennis model_anchor paralel pattern.
Lig-spesifik margin_std + total_std parametreleri (Faz 2: NCAAB/WNCAAB,
Faz 3: Euroleague farklı tuning).
Eksik veride None (caller bookmaker'a düşer veya skip eder).
"""
from __future__ import annotations

from typing import Optional

from src.domain.pricing.basketball.match_pricer import compute_market_anchor
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.team_elo import EloRating


def compute_model_anchor(
    market_type: str,
    home_elo: EloRating, away_elo: EloRating,
    home_eff: TeamEfficiency, away_eff: TeamEfficiency,
    home_advantage: float, blend_elo: float,
    line: Optional[float] = None,
    margin_std: float = 11.0,
    total_std: float = 20.0,
) -> Optional[float]:
    """P(YES) from model. Eksik veri → None."""
    return compute_market_anchor(
        market_type=market_type,
        home_elo=home_elo, away_elo=away_elo,
        home_eff=home_eff, away_eff=away_eff,
        home_advantage=home_advantage, blend_elo=blend_elo, line=line,
        margin_std=margin_std, total_std=total_std,
    )
