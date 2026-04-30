"""MLB stadium park factors (2020-2024 Baseball Savant 5-yr aggregate).

Run factor: 1.00 = league average. >1 = hitter friendly, <1 = pitcher friendly.
HR factor: separate for HR (different physics — altitude, dimensions).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParkFactor:
    runs: float
    hr: float


_NEUTRAL = ParkFactor(1.0, 1.0)

PARK_FACTORS: dict[str, ParkFactor] = {
    "ARI": ParkFactor(1.05, 1.10),
    "ATL": ParkFactor(1.00, 1.05),
    "BAL": ParkFactor(1.05, 1.10),
    "BOS": ParkFactor(1.05, 0.95),
    "CHC": ParkFactor(1.00, 1.05),
    "CWS": ParkFactor(1.05, 1.10),
    "CIN": ParkFactor(1.10, 1.15),
    "CLE": ParkFactor(0.98, 0.95),
    "COL": ParkFactor(1.30, 1.25),
    "DET": ParkFactor(0.95, 0.90),
    "HOU": ParkFactor(1.00, 1.05),
    "KC":  ParkFactor(1.02, 0.95),
    "LAA": ParkFactor(0.98, 0.95),
    "LAD": ParkFactor(0.95, 0.95),
    "MIA": ParkFactor(0.92, 0.85),
    "MIL": ParkFactor(1.05, 1.10),
    "MIN": ParkFactor(1.00, 1.00),
    "NYM": ParkFactor(0.95, 0.92),
    "NYY": ParkFactor(1.05, 1.15),
    "OAK": ParkFactor(0.92, 0.85),
    "PHI": ParkFactor(1.05, 1.10),
    "PIT": ParkFactor(0.95, 0.90),
    "SD":  ParkFactor(0.95, 0.92),
    "SEA": ParkFactor(0.95, 0.92),
    "SF":  ParkFactor(0.92, 0.88),
    "STL": ParkFactor(0.98, 0.95),
    "TB":  ParkFactor(0.95, 0.92),
    "TEX": ParkFactor(1.02, 1.05),
    "TOR": ParkFactor(1.05, 1.10),
    "WSH": ParkFactor(1.00, 1.00),
}


def get_park_factor(team_abbr: str | None) -> ParkFactor:
    """Return park factor for team's home stadium; neutral if unknown."""
    if not team_abbr:
        return _NEUTRAL
    return PARK_FACTORS.get(team_abbr.upper(), _NEUTRAL)
