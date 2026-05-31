"""MatchRecord — Sackmann maç verisi için saf domain dataclass.

CSV loader (infra) bu yapıyı doldurur, pricer'lar (domain) tüketir.
Domain'de tutuluyor çünkü saf veri yapısı — I/O yok, business logic yok.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchRecord:
    tourney_id: str
    tourney_date: str  # YYYYMMDD
    surface: str
    winner_name: str
    loser_name: str
    w_svpt: int
    w_1st_in: int
    w_1st_won: int
    w_2nd_won: int
    w_sv_gms: int
    l_svpt: int
    l_1st_in: int
    l_1st_won: int
    l_2nd_won: int
    l_sv_gms: int
    best_of: int
    score: str
