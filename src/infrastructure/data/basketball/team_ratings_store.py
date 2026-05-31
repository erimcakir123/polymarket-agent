"""Takım rating cache — JSON I/O + atomic write.

Tennis ratings store paraleli (src/infrastructure/data/tennis_ratings_store.py).
Liglerin (NBA, WNBA) snapshot'ları aynı dosyada — load_team_snapshots'da
lige göre filtrelenir.

Atomic write garantisi: tmp dosyaya yaz, rename ile yerine koy. Yarım yazımda
hedef dosya bozulmaz (önceki versiyon korunur).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from src.infrastructure.data.basketball.schemas import TeamSnapshot

logger = logging.getLogger(__name__)


def load_team_snapshots(path: Path, league: str) -> dict[str, TeamSnapshot]:
    """Verilen lig için takım → TeamSnapshot eşlemesi döndür. Dosya yoksa boş dict."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("team_ratings_store: read failed %s — %s", path, exc)
        return {}
    out: dict[str, TeamSnapshot] = {}
    for row in raw:
        try:
            snap = TeamSnapshot.model_validate(row)
        except Exception as exc:  # noqa: BLE001
            logger.warning("team_ratings_store: row validation failed — %s", exc)
            continue
        if snap.league != league:
            continue
        out[snap.team] = snap
    return out


def save_team_snapshots(path: Path, snapshots: Iterable[TeamSnapshot]) -> None:
    """Tüm snapshot listesini atomic write ile JSON'a yaz."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [s.model_dump() for s in snapshots]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def upsert_snapshot(path: Path, snapshot: TeamSnapshot, league: str) -> None:
    """Tek bir takımın snapshot'ını ekle veya değiştir.

    Önce mevcut dosyayı yükle, lige göre filtreleme YAPMAYIP tüm satırları
    koru — sadece kendi (team, league) anahtarını üzerine yaz.
    """
    existing: list[TeamSnapshot] = []
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            existing = [TeamSnapshot.model_validate(r) for r in raw]
        except Exception as exc:  # noqa: BLE001
            logger.warning("upsert: read+parse failed, starting fresh — %s", exc)
            existing = []
    key = (snapshot.team, snapshot.league)
    merged = [s for s in existing if (s.team, s.league) != key]
    merged.append(snapshot)
    save_team_snapshots(path, merged)
