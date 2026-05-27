"""MatchStatus — ESPN'den çekilen maç durumu için pure value object.

Domain/strategy/infrastructure üç katman bu tipi paylaşır. Saf dataclass:
infrastructure üretir (ESPN client), strategy tüketir (force-close kararı),
hiçbiri tipin sahibi değil — bu yüzden models/ altında.

SPEC: docs/superpowers/specs/2026-05-27-force-close-design.md
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchStatus:
    """ESPN'den maç state özeti — force-close kararı için.

    state: ESPN type.state normalize edilmiş — "pre" / "in" / "post"
    period: cari/son period numarası (tenis: set, basketbol: çeyrek)
    is_completed: ESPN type.completed flag
    """
    state: str
    period: int | None
    is_completed: bool
