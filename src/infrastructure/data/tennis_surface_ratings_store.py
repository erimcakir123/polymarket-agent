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
    """Serve JSON yapisini PlayerServeStats'a cevir.

    Surface key normalize: "clay"/"Clay" gibi case farkliliklari capitalize ile
    birlestirilir; ayni surface icin birden fazla entry varsa n_points-agirlikli
    ortalama alinir. Bu olmazsa (case-sensitive dict.get) Sackmann build'inden
    lowercase/uppercase karisikligi alt market modelinin %44'unu fail ediyor.
    """
    merged: dict[str, list[dict]] = {}
    for surf, stats in (serve_blob or {}).items():
        if not surf or not isinstance(stats, dict):
            continue
        key = surf.capitalize()  # "clay" → "Clay"
        merged.setdefault(key, []).append(stats)
    out: dict[str, PlayerServeStats] = {}
    for key, entries in merged.items():
        if len(entries) == 1:
            s = entries[0]
            out[key] = PlayerServeStats(
                serve_pts_won_pct=float(s.get("serve_pts_won_pct", 0.6)),
                return_pts_won_pct=float(s.get("return_pts_won_pct", 0.35)),
                n_points=int(s.get("n_points", 0)),
            )
        else:
            # n_points-weighted merge (varsa); pesin pesin sifir n_points ise basit ortalama
            total_n = sum(int(s.get("n_points", 0)) for s in entries)
            if total_n > 0:
                serve_pct = sum(
                    float(s.get("serve_pts_won_pct", 0.6)) * int(s.get("n_points", 0))
                    for s in entries
                ) / total_n
                return_pct = sum(
                    float(s.get("return_pts_won_pct", 0.35)) * int(s.get("n_points", 0))
                    for s in entries
                ) / total_n
            else:
                serve_pct = sum(float(s.get("serve_pts_won_pct", 0.6)) for s in entries) / len(entries)
                return_pct = sum(float(s.get("return_pts_won_pct", 0.35)) for s in entries) / len(entries)
            out[key] = PlayerServeStats(
                serve_pts_won_pct=serve_pct,
                return_pts_won_pct=return_pct,
                n_points=total_n,
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


def save_all_surfaces(
    overall: dict[str, Rating],
    by_surface: dict[str, dict[str, Rating]],
    serve_by_player: dict[str, dict[str, PlayerServeStats]],
    path: Path,
) -> None:
    """Yüzey reytinglerini load_all_surfaces'ın okuduğu formatta yaz (PLAN-DATA1).

    Format lab_v2 build çıktısıyla birebir: {name: {overall, Hard, Clay, Grass, serve}}.
    Atomic yazım: önce .tmp, sonra replace (yarım dosya riski yok).
    """
    def _r(r: Rating | None) -> dict:
        r = r or Rating()
        return {"mu": r.mu, "phi": r.phi, "sigma": r.sigma}

    names = set(overall)
    for d in by_surface.values():
        names.update(d)
    out: dict[str, dict] = {}
    for name in names:
        blob: dict = {"overall": _r(overall.get(name))}
        for surf in _DEFAULT_VALID_SURFACES:
            blob[surf] = _r(by_surface.get(surf, {}).get(name))
        serve = serve_by_player.get(name)
        if serve:
            blob["serve"] = {
                surf: {
                    "serve_pts_won_pct": s.serve_pts_won_pct,
                    "return_pts_won_pct": s.return_pts_won_pct,
                    "n_points": s.n_points,
                }
                for surf, s in serve.items()
            }
        out[name] = blob
    tmp = Path(path).with_suffix(".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
