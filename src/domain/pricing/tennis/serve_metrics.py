"""Per-player serve/return aggregation by surface.

Domain — saf aggregation. MatchRecord listesi → (player, surface) → serve_stats.

Bartoš-Cohen point-win formula (common-opponent uyumlu):
  P(A wins on own serve) = (A_serve_pct + (1 - B_return_pct)) / 2
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from src.infrastructure.data.sackmann_csv_loader import MatchRecord


@dataclass(frozen=True)
class PlayerServeStats:
    serve_pts_won_pct: float
    return_pts_won_pct: float
    n_points: int


@dataclass
class _Accumulator:
    serve_won: int = 0
    serve_total: int = 0
    return_won: int = 0
    return_total: int = 0

    def to_stats(self) -> PlayerServeStats:
        s_pct = self.serve_won / self.serve_total if self.serve_total else 0.6
        r_pct = self.return_won / self.return_total if self.return_total else 0.35
        return PlayerServeStats(
            serve_pts_won_pct=s_pct,
            return_pts_won_pct=r_pct,
            n_points=self.serve_total + self.return_total,
        )


def aggregate_serve_stats(
    matches: list[MatchRecord],
) -> dict[tuple[str, str], PlayerServeStats]:
    """Returns mapping (player_name, surface) -> PlayerServeStats."""
    acc: dict[tuple[str, str], _Accumulator] = defaultdict(_Accumulator)
    for m in matches:
        w_key = (m.winner_name, m.surface)
        l_key = (m.loser_name, m.surface)
        w_serve_won = m.w_1st_won + m.w_2nd_won
        l_serve_won = m.l_1st_won + m.l_2nd_won
        acc[w_key].serve_won += w_serve_won
        acc[w_key].serve_total += m.w_svpt
        acc[w_key].return_won += m.l_svpt - l_serve_won
        acc[w_key].return_total += m.l_svpt
        acc[l_key].serve_won += l_serve_won
        acc[l_key].serve_total += m.l_svpt
        acc[l_key].return_won += m.w_svpt - w_serve_won
        acc[l_key].return_total += m.w_svpt
    return {k: v.to_stats() for k, v in acc.items()}


def point_win_on_serve(server: PlayerServeStats, returner: PlayerServeStats) -> float:
    """Bartoš-Cohen 2005 — server'ın gerçek serve % tahmini."""
    return (server.serve_pts_won_pct + (1.0 - returner.return_pts_won_pct)) / 2.0
