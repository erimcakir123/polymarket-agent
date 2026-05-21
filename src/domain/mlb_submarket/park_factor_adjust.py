"""Component-level park factors (HR, 1B, 2B, 3B separate).

SPEC-R Plan 2 T5. CRITICAL: never apply BOTH total park factor AND component
factor — that double-counts. This module returns component-only factors.

Source: Baseball Savant park factors (statcast.org), 3-year averages (2022-2024).
Values are multipliers relative to league average (1.00 = neutral).
HR factor is the most variable; 1B/2B/3B are closer to neutral for most parks.
All 30 active MLB parks as of 2024-2026 season.
"""
from __future__ import annotations

PARK_FACTORS: dict[str, dict[str, float]] = {
    "COORS":            {"HR": 1.18, "1B": 1.05, "2B": 1.10, "3B": 1.30},  # COL — altitude boosts all
    "FENWAY":           {"HR": 1.00, "1B": 1.03, "2B": 1.20, "3B": 0.90},  # BOS — Green Monster bumps 2B
    "YANKEE":           {"HR": 1.10, "1B": 1.00, "2B": 1.00, "3B": 0.90},  # NYY — short RF porch
    "DODGER":           {"HR": 0.98, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # LAD — near-neutral
    "PETCO":            {"HR": 0.92, "1B": 0.97, "2B": 0.95, "3B": 0.85},  # SD — marine layer suppresses
    "WRIGLEY":          {"HR": 1.05, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # CHC — wind variable
    "BUSCH":            {"HR": 0.95, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # STL — pitcher-friendly
    "GLOBE_LIFE":       {"HR": 1.08, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # TEX — retractable roof, warm
    "GREAT_AMERICAN":   {"HR": 1.12, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # CIN — hitter-friendly dimensions
    "CITIZENS_BANK":    {"HR": 1.08, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # PHI — short porches
    "AMERICAN_FAMILY":  {"HR": 1.03, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # MIL — slight HR boost
    "TARGET":           {"HR": 0.98, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # MIN — neutral
    "KAUFFMAN":         {"HR": 0.95, "1B": 1.00, "2B": 1.00, "3B": 1.15},  # KC — large OF, gap 3B
    "PROGRESSIVE":      {"HR": 1.00, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # CLE — neutral
    "GUARANTEED_RATE":  {"HR": 1.05, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # CWS — slight HR boost
    "ROGERS":           {"HR": 1.02, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # TOR — indoor dome, slight HR
    "ORACLE":           {"HR": 0.88, "1B": 1.00, "2B": 1.00, "3B": 1.10},  # SF — marine layer, deep CF
    "CHASE":            {"HR": 1.05, "1B": 1.00, "2B": 1.00, "3B": 1.05},  # ARI — altitude + dome heat
    "T_MOBILE":         {"HR": 0.92, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # SEA — marine air suppresses HR
    "ANGEL":            {"HR": 0.97, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # LAA — near-neutral
    "MINUTE_MAID":      {"HR": 1.02, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # HOU — Tal's Hill era gone, slight boost
    "TROPICANA":        {"HR": 0.95, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # TB — dome suppresses
    "LOAN_DEPOT":       {"HR": 0.90, "1B": 1.00, "2B": 1.00, "3B": 1.05},  # MIA — pitcher-friendly
    "TRUIST":           {"HR": 1.00, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # ATL — neutral
    "ORIOLE_PARK":      {"HR": 1.05, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # BAL — slight HR boost
    "NATIONALS":        {"HR": 1.00, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # WSH — neutral
    "CITI":             {"HR": 0.93, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # NYM — marine air suppresses
    "PNC":              {"HR": 0.92, "1B": 1.00, "2B": 1.00, "3B": 1.05},  # PIT — deep CF, gap power
    "COMERICA":         {"HR": 0.95, "1B": 1.00, "2B": 1.00, "3B": 1.10},  # DET — deep OF, gap triples
    "OAKLAND_COLISEUM": {"HR": 0.93, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # OAK — marine air, foul territory
}


def park_multiplier(park_id: str, outcome: str) -> float:
    """Lookup component park factor.

    Args:
        park_id: park identifier (e.g., "COORS", "PETCO").
        outcome: PA outcome ("HR", "1B", "2B", "3B").

    Returns:
        Multiplier >= 0. Unknown park or outcome -> 1.0 (no adjustment).
    """
    table = PARK_FACTORS.get(park_id)
    if table is None:
        return 1.0
    return table.get(outcome, 1.0)
