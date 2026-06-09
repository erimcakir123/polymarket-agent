"""Sackmann maçlarından turnuva→zemin haritası (saf domain, I/O yok)."""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable

from src.domain.pricing.tennis.match_record import MatchRecord

_VALID_SURFACES = {"Hard", "Clay", "Grass", "Carpet"}


def build_surface_map(matches: Iterable[MatchRecord]) -> dict[str, str]:
    """{normalized_tourney_name: surface}. İsim lowercase+strip; birden çok zemin
    görülürse en sık olan; geçersiz/Unknown surface veya boş isim atlanır."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for m in matches:
        name = (m.tourney_name or "").strip().lower()
        if not name or m.surface not in _VALID_SURFACES:
            continue
        counts[name][m.surface] += 1
    return {name: c.most_common(1)[0][0] for name, c in counts.items() if c}
