"""Event grouper — Polymarket flat market list'inden event-bazlı grup üretir.

SPEC-015: 3-way soccer event'leri 3 ayrı binary market olarak gelir.
Bu modül event_id ile grupluyor + market_type sınıflandırması yapıyor.

2-way sporlar (MLB/NBA/...) tek market'lik group olarak pass-through olur.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from src.models.market import MarketData

_THREE_WAY_SPORTS = frozenset({"soccer", "rugby", "afl", "handball"})

_DRAW_KEYWORDS = ("end in a draw", "draw", "level", "tie")


def _is_draw_market(question: str) -> bool:
    q = (question or "").lower()
    return any(kw in q for kw in _DRAW_KEYWORDS)


def _is_three_way_sport(sport_tag: str) -> bool:
    s = (sport_tag or "").lower()
    return any(tw in s for tw in _THREE_WAY_SPORTS)


@dataclass
class EventGroup:
    """Bir event için gruplanmış market'ler."""
    event_id: str
    market_type: str  # "BINARY" | "THREE_WAY"
    markets: list[MarketData]

    def classify_outcomes(self) -> tuple[MarketData | None, MarketData | None, MarketData | None]:
        """3-way için (home, draw, away) tuple. Question keyword based.

        Draw market keyword içerir ("draw"/"tie"/"level"). Kalan 2 market
        non-draw olarak sıralanır (list order → home, away).

        Returns: (home, draw, away). Eksik outcome None döner.
        """
        if self.market_type != "THREE_WAY":
            return (None, None, None)

        draw_market = next((m for m in self.markets if _is_draw_market(m.question)), None)
        non_draw = [m for m in self.markets if m is not draw_market]

        if len(non_draw) == 2:
            home, away = non_draw[0], non_draw[1]
        else:
            home = non_draw[0] if non_draw else None
            away = non_draw[1] if len(non_draw) > 1 else None

        return (home, draw_market, away)


def group_markets_by_event(markets: list[MarketData]) -> list[EventGroup]:
    """Flat MarketData listesi → event_id bazlı EventGroup listesi.

    event_id boş olan market'ler gruplanmaz (atılır).
    3-way sport + ≥2 market → THREE_WAY group.
    Diğer → BINARY group.
    """
    by_event: dict[str, list[MarketData]] = defaultdict(list)
    for m in markets:
        if not m.event_id:
            continue
        by_event[m.event_id].append(m)

    groups: list[EventGroup] = []
    for eid, ms in by_event.items():
        sport = ms[0].sport_tag if ms else ""
        if _is_three_way_sport(sport) and len(ms) >= 2:
            mtype = "THREE_WAY"
        else:
            mtype = "BINARY"
        groups.append(EventGroup(event_id=eid, market_type=mtype, markets=ms))

    return groups
