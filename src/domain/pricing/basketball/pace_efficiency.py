"""Pace × Efficiency projeksiyon — KenPom formülü.

  proj_pace  = (pace_A + pace_B) / 2
  proj_score_A = proj_pace × (AdjO_A + AdjD_B) / 200
  proj_score_B = proj_pace × (AdjO_B + AdjD_A) / 200
  proj_total   = proj_score_A + proj_score_B
  proj_margin  = proj_score_A - proj_score_B (home perspective)

AdjO/AdjD/Pace değerleri Plan 1.B Task 4'te `efficiency_metrics`
modülünde tarihsel maç verisinden hesaplanır. Burada sadece projeksiyon.
"""
from __future__ import annotations

from dataclasses import dataclass


_EFFICIENCY_NORMALIZER = 200.0  # Possession başına = AdjO/100 + AdjD/100 = (AdjO+AdjD)/200


@dataclass(frozen=True)
class TeamEfficiency:
    """Bir takımın güncel AdjO / AdjD / Pace değerleri (KenPom-tarzı)."""
    adj_o: float   # offensive efficiency (puan / 100 poss)
    adj_d: float   # defensive efficiency (allowed puan / 100 poss)
    adj_pace: float  # possessions / 40 min


@dataclass(frozen=True)
class GameProjection:
    home_score: float
    away_score: float
    total: float
    margin: float  # home - away
    proj_pace: float


def project_game(home: TeamEfficiency, away: TeamEfficiency) -> GameProjection:
    """KenPom formülüyle beklenen skor + total + margin."""
    proj_pace = (home.adj_pace + away.adj_pace) / 2.0
    score_home = proj_pace * (home.adj_o + away.adj_d) / _EFFICIENCY_NORMALIZER
    score_away = proj_pace * (away.adj_o + home.adj_d) / _EFFICIENCY_NORMALIZER
    return GameProjection(
        home_score=score_home,
        away_score=score_away,
        total=score_home + score_away,
        margin=score_home - score_away,
        proj_pace=proj_pace,
    )
