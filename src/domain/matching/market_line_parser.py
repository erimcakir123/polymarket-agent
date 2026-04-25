"""Polymarket market title'ından spread/total line parse eder.

Desteklenen formatlar (gerçek Gamma API data'sına dayanarak):
  Spread : "Spread: TEAM_NAME (-X.5)"  veya  "TEAM_NAME (-X.5)"
  Totals : "TEAM1 vs TEAM2: O/U X.5"  veya  "Games Total: O/U X.5"

Tanımlanamayan format → None döner → ilgili exit logic devre dışı.
Polymarket konvansiyonu: totals YES token = OVER.
"""
from __future__ import annotations

import re
from typing import Literal

# Spread: parantez içi ±X.5 (1-30 puan arası NBA spreads için yeterli)
_SPREAD_RE = re.compile(r'\([+-]?(\d{1,2}(?:\.\d)?)\)')

# Totals: "O/U X.5" veya "o/u X"
_TOTAL_RE = re.compile(r'[Oo]/[Uu]\s+(\d+(?:\.\d+)?)')


def parse_spread_line(question: str) -> float | None:
    """Spread line'ı parçalar.

    "Spread: Lakers (-5.5)" → 5.5
    "Lakers (-5.5)"         → 5.5
    Eşleşme yoksa → None (exit devre dışı).
    """
    m = _SPREAD_RE.search(question)
    if m:
        return float(m.group(1))
    return None


def parse_total_line(question: str) -> tuple[float, Literal["over", "under"]] | None:
    """Total line ve side'ı parçalar.

    "Lakers vs Rockets: O/U 220.5" → (220.5, "over")
    "Games Total: O/U 2.5"         → (2.5, "over")
    Polymarket konvansiyonu: YES token = OVER.
    Eşleşme yoksa → None (exit devre dışı).
    """
    m = _TOTAL_RE.search(question)
    if m:
        return float(m.group(1)), "over"
    return None
