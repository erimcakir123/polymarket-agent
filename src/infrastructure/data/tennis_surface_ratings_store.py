"""LAB v2: Surface-specific tennis ratings loader.

Reads lab_v2/data/tennis_ratings_surface.json and returns a function that
produces a per-surface PlayerSnapshot dict on demand.

When surface-specific rating is too uncertain (phi >= threshold) OR player
not found for that surface, falls back to "overall" rating.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats

_SURFACE_PHI_FALLBACK_THRESHOLD = 150.0  # phi above this → overall rating tercih edilir
_DEFAULT_VALID_SURFACES = ("Hard", "Clay", "Grass")


def _build_serve_by_surface(serve_blob: dict) -> dict[str, PlayerServeStats]:
    """Mevcut serve JSON yapisini PlayerServeStats'a cevir."""
    out = {}
    for surf, stats in (serve_blob or {}).items():
        out[surf] = PlayerServeStats(
            serve_pts_won_pct=float(stats.get("serve_pts_won_pct", 0.6)),
            return_pts_won_pct=float(stats.get("return_pts_won_pct", 0.35)),
            n_points=int(stats.get("n_points", 0)),
        )
    return out


def load_surface_ratings(
    path: Path,
    surface: str,
    phi_fallback: float = _SURFACE_PHI_FALLBACK_THRESHOLD,
) -> dict[str, PlayerSnapshot]:
    """Belirli bir yuzey icin PlayerSnapshot dict yukler.

    surface: "Hard" | "Clay" | "Grass" → o yuzeydeki rating kullanilir
             (phi cok yuksekse overall rating fallback)
    """
    if surface not in _DEFAULT_VALID_SURFACES:
        surface = "Hard"  # safety fallback
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, PlayerSnapshot] = {}
    for name, blob in raw.items():
        if not isinstance(blob, dict):
            continue
        # Surface-specific rating, falls back to overall if too uncertain
        surf_r = blob.get(surface, {})
        overall_r = blob.get("overall", {})
        surf_phi = float(surf_r.get("phi", 350.0))
        if surf_phi >= phi_fallback and overall_r:
            chosen = overall_r
        else:
            chosen = surf_r or overall_r
        if not chosen:
            continue
        rating = Rating(
            mu=float(chosen.get("mu", 1500.0)),
            phi=float(chosen.get("phi", 350.0)),
            sigma=float(chosen.get("sigma", 0.06)),
        )
        serve = _build_serve_by_surface(blob.get("serve", {}))
        out[name] = PlayerSnapshot(rating=rating, serve_by_surface=serve)
    return out


def load_all_surfaces(
    path: Path,
) -> dict[str, dict[str, PlayerSnapshot]]:
    """Hard, Clay, Grass icin 3 ayri dict — dispatch surface'a gore secer."""
    return {s: load_surface_ratings(path, s) for s in _DEFAULT_VALID_SURFACES}
