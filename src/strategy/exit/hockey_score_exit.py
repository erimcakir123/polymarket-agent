"""Hockey score exit — NHL K1-K4 eşikleri (TODO: yeniden yazılacak)."""
from __future__ import annotations

from src.config.sport_rules import _normalize

_HOCKEY_TAGS: frozenset[str] = frozenset({"nhl", "ahl", "liiga", "shl", "allsvenskan", "mestis"})


def _is_hockey_family(sport_tag: str) -> bool:
    return _normalize(sport_tag) in _HOCKEY_TAGS


def check(**kwargs) -> None:  # TODO: yeniden yazılacak
    return None
