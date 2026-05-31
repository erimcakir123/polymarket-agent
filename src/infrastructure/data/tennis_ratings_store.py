"""tennis_ratings.json read/write.

Infra layer — atomic write (tmp → rename), missing file → empty dict.
Bozuk JSON → log WARNING + empty dict (Kural 12).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.domain.pricing.tennis.serve_metrics import (
    DEFAULT_RETURN_PCT,
    DEFAULT_SERVE_PCT,
    PlayerServeStats,
)

logger = logging.getLogger(__name__)


def save_ratings(snapshot: dict[str, PlayerSnapshot], path: Path) -> None:
    payload = {
        name: {
            "rating": {"mu": s.rating.mu, "phi": s.rating.phi, "sigma": s.rating.sigma},
            "serve": {
                surface: {
                    "serve_pts_won_pct": stats.serve_pts_won_pct,
                    "return_pts_won_pct": stats.return_pts_won_pct,
                    "n_points": stats.n_points,
                }
                for surface, stats in s.serve_by_surface.items()
            },
        }
        for name, s in snapshot.items()
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(target) + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(target)


def load_ratings(path: Path) -> dict[str, PlayerSnapshot]:
    target = Path(path)
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("tennis_ratings.json okunamadı: %s", exc)
        return {}
    out: dict[str, PlayerSnapshot] = {}
    for name, payload in data.items():
        r = payload.get("rating", {})
        rating = Rating(
            mu=float(r.get("mu", 1500.0)),
            phi=float(r.get("phi", 350.0)),
            sigma=float(r.get("sigma", 0.06)),
        )
        serve: dict[str, PlayerServeStats] = {}
        for surface, stats in payload.get("serve", {}).items():
            serve[surface] = PlayerServeStats(
                serve_pts_won_pct=float(stats.get("serve_pts_won_pct", DEFAULT_SERVE_PCT)),
                return_pts_won_pct=float(stats.get("return_pts_won_pct", DEFAULT_RETURN_PCT)),
                n_points=int(stats.get("n_points", 0)),
            )
        out[name] = PlayerSnapshot(rating=rating, serve_by_surface=serve)
    return out
