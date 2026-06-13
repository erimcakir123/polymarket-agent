"""Taze tenis sonuçları jsonl deposu — append-only + maç-anahtarı dedupe.

Infrastructure: dosya I/O sınırda; domain HarvestedResult döner. Bozuk satır
atlanır + log (ARCH_GUARD Kural 12).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.domain.pricing.tennis.harvested_result import HarvestedResult

logger = logging.getLogger(__name__)


def load_results(path: Path) -> list[HarvestedResult]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[HarvestedResult] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            out.append(HarvestedResult(
                winner=d["winner"], loser=d["loser"],
                surface=d.get("surface", "Unknown"), date=d["date"],
            ))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("tennis_results_store: bozuk satır atlandı: %s", e)
    return out


def harvested_keys(path: Path) -> set[str]:
    return {r.match_key() for r in load_results(path)}


def append_results(results: list[HarvestedResult], path: Path) -> int:
    """Yeni (dedupe edilmiş) sonuçları ekle. Eklenen satır sayısını döner."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = harvested_keys(p)
    added = 0
    with open(p, "a", encoding="utf-8") as f:
        for r in results:
            if r.match_key() in existing:
                continue
            existing.add(r.match_key())
            f.write(json.dumps({
                "winner": r.winner, "loser": r.loser,
                "surface": r.surface, "date": r.date,
            }, ensure_ascii=False) + "\n")
            added += 1
    return added
