"""LAB v2: Surface-specific Glicko ratings (Hard/Clay/Grass ayri).

Akademik literatur: yuzey-spesifik Elo/Glicko standard ratingden log-loss'ta
daha iyi (PLOS One 2022). Sebep: Alcaraz toprakta dunya birincisi, sertte top 5;
Sinner sertte birinci, toprakta top 3.

Cikti: lab_v2/data/tennis_ratings_surface.json
  {name: {
    "overall": {mu, phi, sigma},   # tum maclar
    "Hard":    {mu, phi, sigma},   # sadece hard court maclari
    "Clay":    {mu, phi, sigma},
    "Grass":   {mu, phi, sigma},
    "serve":   {...},               # mevcut serve breakdown
  }}

Glicko domain modulu mevcut: src/domain/pricing/tennis/glicko.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# Ana repo'dan import
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.domain.pricing.tennis.glicko import Rating as GlickoRating  # noqa: E402
from src.domain.pricing.tennis.glicko import update_rating  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "sackmann_cache"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "tennis_ratings_surface.json"

# Sackmann surface values: "Hard" | "Clay" | "Grass" | "Carpet" (atla)
_VALID_SURFACES = frozenset({"Hard", "Clay", "Grass"})


def _read_matches(year: int) -> list[dict]:
    """Sackmann CSV'lerini oku — atp_matches + atp_qual_chall + wta_matches + wta_futures."""
    matches = []
    sources = [
        f"atp_matches_{year}.csv",
        f"atp_matches_qual_chall_{year}.csv",
        f"atp_futures_{year}.csv",
        f"wta_matches_{year}.csv",
        f"wta_futures_{year}.csv",
    ]
    for fname in sources:
        fp = CACHE_DIR / fname
        if not fp.exists():
            continue
        with fp.open(encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                surface = row.get("surface", "").strip()
                winner = row.get("winner_name", "").strip()
                loser = row.get("loser_name", "").strip()
                tourney_date = row.get("tourney_date", "")
                if not (surface and winner and loser):
                    continue
                if surface not in _VALID_SURFACES:
                    continue  # Carpet/Indoor — skip
                matches.append({
                    "surface": surface,
                    "winner": winner, "loser": loser,
                    "date": tourney_date,
                })
    return matches


def _fit_glicko(matches: list[dict]) -> dict[str, GlickoRating]:
    """Glicko-2 her oyuncu icin fit. Matches kronolojik sirada gelmeli."""
    matches = sorted(matches, key=lambda m: m["date"])
    ratings: dict[str, GlickoRating] = {}
    for m in matches:
        w, loser = m["winner"], m["loser"]
        r_w = ratings.get(w, GlickoRating())
        r_l = ratings.get(loser, GlickoRating())
        new_w = update_rating(rating=r_w, opponents=[r_l], outcomes=[1.0])
        new_l = update_rating(rating=r_l, opponents=[r_w], outcomes=[0.0])
        ratings[w] = new_w
        ratings[loser] = new_l
    return ratings


def main():
    print(f"[LAB v2] Reading Sackmann from {CACHE_DIR}")
    all_matches = []
    for yr in (2025, 2026):
        ms = _read_matches(yr)
        print(f"  {yr}: {len(ms)} matches")
        all_matches.extend(ms)
    print(f"Total: {len(all_matches)} matches (Hard+Clay+Grass)")

    # 1. Overall (tum maclar)
    print("\n[1/4] Fitting OVERALL Glicko...")
    overall = _fit_glicko(all_matches)
    print(f"  -> {len(overall)} players")

    # 2-4. Per-surface
    by_surface: dict[str, dict[str, GlickoRating]] = {}
    for surf in ("Hard", "Clay", "Grass"):
        print(f"\n[{['', 'Hard', 'Clay', 'Grass'].index(surf)+1}/4] Fitting {surf}-specific Glicko...")
        ms = [m for m in all_matches if m["surface"] == surf]
        by_surface[surf] = _fit_glicko(ms)
        print(f"  -> {len(by_surface[surf])} players ({len(ms)} matches)")

    # 5. Merge into output structure (also read existing serve breakdown from MAIN ratings)
    print("\n[merge] Combining surface ratings + existing serve breakdown...")
    main_ratings_path = ROOT / "data" / "tennis_ratings.json"
    serve_by_player = {}
    if main_ratings_path.exists():
        main_data = json.loads(main_ratings_path.read_text(encoding="utf-8"))
        for name, blob in main_data.items():
            if isinstance(blob, dict) and "serve" in blob:
                serve_by_player[name] = blob["serve"]
        print(f"  serve breakdown loaded for {len(serve_by_player)} players")

    out = {}
    all_names = set(overall.keys())
    for s in by_surface.values():
        all_names.update(s.keys())

    def _to_dict(r: GlickoRating) -> dict:
        return {"mu": r.mu, "phi": r.phi, "sigma": r.sigma}

    for name in all_names:
        out[name] = {
            "overall": _to_dict(overall.get(name, GlickoRating())),
            "Hard":    _to_dict(by_surface["Hard"].get(name, GlickoRating())),
            "Clay":    _to_dict(by_surface["Clay"].get(name, GlickoRating())),
            "Grass":   _to_dict(by_surface["Grass"].get(name, GlickoRating())),
        }
        if name in serve_by_player:
            out[name]["serve"] = serve_by_player[name]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Wrote {len(out)} players to {OUTPUT}")

    # Sanity: top 5 per surface
    for surf in ("Hard", "Clay", "Grass"):
        tops = sorted(
            [(out[n][surf]["mu"], n) for n in out if out[n][surf]["mu"] > 0],
            reverse=True,
        )[:5]
        print(f"\nTop 5 {surf}:")
        for mu, n in tops:
            print(f"  {n:30} {mu:.0f}")


if __name__ == "__main__":
    main()
