"""Tennis ratings JSON cache — Glicko-2 ratings persistence.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §4.2
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SurfaceRating:
    rating: float
    rd: float           # Rating deviation
    volatility: float


@dataclass
class PlayerRating:
    player_id: str
    player_name: str
    tour: str           # "atp" | "wta"
    overall: SurfaceRating
    serve_clay: SurfaceRating
    serve_grass: SurfaceRating
    serve_hard: SurfaceRating
    return_clay: SurfaceRating
    return_grass: SurfaceRating
    return_hard: SurfaceRating
    last_match_date: str    # ISO date
    match_count_12mo: int


class TennisRatingsStore:
    """JSON cache for player Glicko-2 ratings. Atomic write (temp + rename)."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def load(self) -> dict[str, PlayerRating]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load tennis ratings from %s: %s", self._path, e)
            return {}
        out: dict[str, PlayerRating] = {}
        for pid, d in data.items():
            try:
                out[pid] = PlayerRating(
                    player_id=d["player_id"],
                    player_name=d["player_name"],
                    tour=d.get("tour", "atp"),  # backward compat for pre-WTA JSONs
                    overall=SurfaceRating(**d["overall"]),
                    serve_clay=SurfaceRating(**d["serve_clay"]),
                    serve_grass=SurfaceRating(**d["serve_grass"]),
                    serve_hard=SurfaceRating(**d["serve_hard"]),
                    return_clay=SurfaceRating(**d["return_clay"]),
                    return_grass=SurfaceRating(**d["return_grass"]),
                    return_hard=SurfaceRating(**d["return_hard"]),
                    last_match_date=d["last_match_date"],
                    match_count_12mo=int(d["match_count_12mo"]),
                )
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("Skipping malformed rating for %s: %s", pid, e)
                continue
        logger.info("Loaded %d player ratings from %s", len(out), self._path)
        return out

    def save(self, ratings: dict[str, PlayerRating]) -> None:
        """Atomic write: temp file in same dir + os.replace()."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {pid: asdict(r) for pid, r in ratings.items()}
        fd, tmp_path_str = tempfile.mkstemp(
            dir=str(self._path.parent), prefix=".ratings_", suffix=".tmp",
        )
        tmp_path = Path(tmp_path_str)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self._path)
            logger.info("Saved %d player ratings to %s", len(ratings), self._path)
        except OSError as e:
            logger.error("Failed to save ratings to %s: %s", self._path, e)
            if tmp_path.exists():
                tmp_path.unlink()
            raise
