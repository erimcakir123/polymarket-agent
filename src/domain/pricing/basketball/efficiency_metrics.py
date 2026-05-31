"""Takım AdjO/AdjD/Pace hesabı — GameRecord listesinden.

Saf domain — I/O yok. Tarihsel maç verisini alır, takım başına
ortalama offensive / defensive / pace değerleri üretir.

Plan 1.B Faz 1 basit ortalama (NBA için ~%85 doğruluk veriyor).
Plan 1.D: outlier guard (possessions 60-130 dışı tarihsel imkansız → atla).
Strength-of-schedule (SoS) adjustment Faz 2'de planlanır (KenPom
gerçek "Adj"ı SoS ile düzeltir, biz şimdilik raw).
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional

from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.infrastructure.data.basketball.schemas import GameRecord


logger = logging.getLogger(__name__)

_POSS_PER_100 = 100.0

# Tarihsel NBA possessions sınırları — bu aralık dışı = veri hatası
# (50+ yıl NBA verisinde hiçbir maç bu aralık dışına çıkmadı).
_POSS_MIN = 60.0
_POSS_MAX = 130.0


def _raw_efficiency_per_game(g: GameRecord, team: str) -> tuple[float, float, float]:
    """Bir maç → (offensive_eff_per_100, defensive_eff_per_100, pace_per_40)."""
    if g.home_team == team:
        my_score, opp_score = g.home_score, g.away_score
        my_poss, opp_poss = g.home_possessions, g.away_possessions
    elif g.away_team == team:
        my_score, opp_score = g.away_score, g.home_score
        my_poss, opp_poss = g.away_possessions, g.home_possessions
    else:
        raise ValueError(f"team {team} not in game {g.game_id}")
    # NOT: (score * 100) / poss şeklinde sıralı — IEEE-754'te (score/poss)*100
    # 1e-14 mertebesinde drift verir (test'te tam eşitlik kontrol edilir).
    off_eff = my_score * _POSS_PER_100 / my_poss
    def_eff = opp_score * _POSS_PER_100 / opp_poss
    # Pace: ortalama possessions (her iki takım için aynı varsayılır basket'te)
    pace = (my_poss + opp_poss) / 2.0
    return off_eff, def_eff, pace


def compute_team_efficiency(
    games: Iterable[GameRecord], team: str,
) -> Optional[TeamEfficiency]:
    """Tüm maçlardan team'in average AdjO/AdjD/Pace değerini çıkar.

    Takımın hiç maçı yoksa None döner (Plan 1.A Task 5 cache henüz boş
    olabilir — bot başlangıçta tarihsel veriyi çeker, ratings üretir).
    """
    off_vals: list[float] = []
    def_vals: list[float] = []
    pace_vals: list[float] = []
    for g in games:
        if team not in (g.home_team, g.away_team):
            continue
        off, dfn, pace = _raw_efficiency_per_game(g, team)
        if pace < _POSS_MIN or pace > _POSS_MAX:
            logger.warning(
                "outlier game skipped: %s team=%s pace=%.1f (range %.0f-%.0f)",
                g.game_id, team, pace, _POSS_MIN, _POSS_MAX,
            )
            continue
        off_vals.append(off)
        def_vals.append(dfn)
        pace_vals.append(pace)
    if not off_vals:
        return None
    return TeamEfficiency(
        adj_o=sum(off_vals) / len(off_vals),
        adj_d=sum(def_vals) / len(def_vals),
        adj_pace=sum(pace_vals) / len(pace_vals),
    )
