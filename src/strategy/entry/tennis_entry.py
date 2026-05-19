"""Tennis entry strategy — select best 2 edge per match.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §7.3
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class EdgeCandidate:
    """One market prediction candidate ready for entry consideration."""
    event_id: str
    market_type: str
    model_p: float
    market_p: float
    edge: float  # signed: positive = BUY YES, negative = BUY NO


def select_best_2_per_event(candidates: list[EdgeCandidate]) -> list[EdgeCandidate]:
    """Group by event_id, return top 2 by |edge| per event.

    Implements DECISIONS §6.18 event-level guard with tennis-specific rule:
    max 2 positions per match, chosen by edge magnitude.
    """
    by_event: dict[str, list[EdgeCandidate]] = defaultdict(list)
    for c in candidates:
        by_event[c.event_id].append(c)

    selected: list[EdgeCandidate] = []
    for event_id, items in by_event.items():
        sorted_items = sorted(items, key=lambda c: -abs(c.edge))
        selected.extend(sorted_items[:2])
    return selected
