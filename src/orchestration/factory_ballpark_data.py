"""MLB ballpark metadata + team_id → park_id mapping (saf veri, I/O yok).

Bölünme nedeni: ARCH_GUARD §3 (factory.py 400 satır limitini aştı).
Ballpark koordinatları + CF orientation hava-pricer için kullanılır
(MLBSubmarketEngine içinde weather wrapper).
"""
from __future__ import annotations

from typing import Any


# All 30 active MLB ballparks (2024-2026 season).
# lat/lon rounded to 4 decimals; cf_orientation_deg = direction CF points (0=N, 90=E, 180=S, 270=W).
_DEFAULT_BALLPARK_METADATA: dict[str, dict[str, Any]] = {
    "COORS":            {"park_id": "COORS",            "lat": 39.7559, "lon": -104.9942, "cf_orientation_deg": 0.0},
    "FENWAY":           {"park_id": "FENWAY",           "lat": 42.3467, "lon": -71.0972,  "cf_orientation_deg": 75.0},
    "YANKEE":           {"park_id": "YANKEE",           "lat": 40.8296, "lon": -73.9262,  "cf_orientation_deg": 60.0},
    "DODGER":           {"park_id": "DODGER",           "lat": 34.0739, "lon": -118.2400, "cf_orientation_deg": 0.0},
    "PETCO":            {"park_id": "PETCO",            "lat": 32.7073, "lon": -117.1566, "cf_orientation_deg": 0.0},
    "WRIGLEY":          {"park_id": "WRIGLEY",          "lat": 41.9484, "lon": -87.6553,  "cf_orientation_deg": 70.0},
    "BUSCH":            {"park_id": "BUSCH",            "lat": 38.6226, "lon": -90.1928,  "cf_orientation_deg": 30.0},
    "GLOBE_LIFE":       {"park_id": "GLOBE_LIFE",       "lat": 32.7473, "lon": -97.0817,  "cf_orientation_deg": 0.0},
    "GREAT_AMERICAN":   {"park_id": "GREAT_AMERICAN",   "lat": 39.0975, "lon": -84.5067,  "cf_orientation_deg": 320.0},
    "CITIZENS_BANK":    {"park_id": "CITIZENS_BANK",    "lat": 39.9061, "lon": -75.1665,  "cf_orientation_deg": 30.0},
    "AMERICAN_FAMILY":  {"park_id": "AMERICAN_FAMILY",  "lat": 43.0280, "lon": -87.9712,  "cf_orientation_deg": 0.0},
    "TARGET":           {"park_id": "TARGET",           "lat": 44.9817, "lon": -93.2776,  "cf_orientation_deg": 0.0},
    "KAUFFMAN":         {"park_id": "KAUFFMAN",         "lat": 39.0517, "lon": -94.4803,  "cf_orientation_deg": 90.0},
    "PROGRESSIVE":      {"park_id": "PROGRESSIVE",      "lat": 41.4962, "lon": -81.6852,  "cf_orientation_deg": 90.0},
    "GUARANTEED_RATE":  {"park_id": "GUARANTEED_RATE",  "lat": 41.8300, "lon": -87.6338,  "cf_orientation_deg": 0.0},
    "ROGERS":           {"park_id": "ROGERS",           "lat": 43.6414, "lon": -79.3894,  "cf_orientation_deg": 0.0},
    "ORACLE":           {"park_id": "ORACLE",           "lat": 37.7786, "lon": -122.3893, "cf_orientation_deg": 0.0},
    "CHASE":            {"park_id": "CHASE",            "lat": 33.4453, "lon": -112.0667, "cf_orientation_deg": 0.0},
    "T_MOBILE":         {"park_id": "T_MOBILE",         "lat": 47.5914, "lon": -122.3325, "cf_orientation_deg": 0.0},
    "ANGEL":            {"park_id": "ANGEL",            "lat": 33.8003, "lon": -117.8827, "cf_orientation_deg": 0.0},
    "MINUTE_MAID":      {"park_id": "MINUTE_MAID",      "lat": 29.7572, "lon": -95.3556,  "cf_orientation_deg": 0.0},
    "TROPICANA":        {"park_id": "TROPICANA",        "lat": 27.7682, "lon": -82.6534,  "cf_orientation_deg": 0.0},
    "LOAN_DEPOT":       {"park_id": "LOAN_DEPOT",       "lat": 25.7781, "lon": -80.2197,  "cf_orientation_deg": 0.0},
    "TRUIST":           {"park_id": "TRUIST",           "lat": 33.8908, "lon": -84.4678,  "cf_orientation_deg": 0.0},
    "ORIOLE_PARK":      {"park_id": "ORIOLE_PARK",      "lat": 39.2839, "lon": -76.6217,  "cf_orientation_deg": 70.0},
    "NATIONALS":        {"park_id": "NATIONALS",        "lat": 38.8730, "lon": -77.0074,  "cf_orientation_deg": 30.0},
    "CITI":             {"park_id": "CITI",             "lat": 40.7571, "lon": -73.8458,  "cf_orientation_deg": 60.0},
    "PNC":              {"park_id": "PNC",              "lat": 40.4469, "lon": -80.0058,  "cf_orientation_deg": 290.0},
    "COMERICA":         {"park_id": "COMERICA",         "lat": 42.3390, "lon": -83.0485,  "cf_orientation_deg": 30.0},
    "OAKLAND_COLISEUM": {"park_id": "OAKLAND_COLISEUM", "lat": 37.7516, "lon": -122.2005, "cf_orientation_deg": 0.0},
}

# Stats API team_id → ballpark_id (_DEFAULT_BALLPARK_METADATA anahtarı).
# 2026 sezonu (Athletics geçici Sacramento 2025-2027, OAKLAND_COLISEUM key korunur).
TEAM_ID_TO_PARK_ID: dict[int, str] = {
    # AL East
    110: "ORIOLE_PARK",     # Orioles
    111: "FENWAY",          # Red Sox
    147: "YANKEE",          # Yankees
    139: "TROPICANA",       # Rays
    141: "ROGERS",          # Blue Jays
    # AL Central
    145: "GUARANTEED_RATE", # White Sox
    114: "PROGRESSIVE",     # Guardians
    116: "COMERICA",        # Tigers
    118: "KAUFFMAN",        # Royals
    142: "TARGET",          # Twins
    # AL West
    117: "MINUTE_MAID",     # Astros
    108: "ANGEL",           # Angels
    133: "OAKLAND_COLISEUM",# Athletics (geçici Sacramento 2025-27)
    136: "T_MOBILE",        # Mariners
    140: "GLOBE_LIFE",      # Rangers
    # NL East
    144: "TRUIST",          # Braves
    146: "LOAN_DEPOT",      # Marlins
    121: "CITI",            # Mets
    143: "CITIZENS_BANK",   # Phillies
    120: "NATIONALS",       # Nationals
    # NL Central
    112: "WRIGLEY",         # Cubs
    113: "GREAT_AMERICAN",  # Reds
    158: "AMERICAN_FAMILY", # Brewers
    134: "PNC",             # Pirates
    138: "BUSCH",           # Cardinals
    # NL West
    109: "CHASE",           # D-backs
    115: "COORS",           # Rockies
    119: "DODGER",          # Dodgers
    135: "PETCO",           # Padres
    137: "ORACLE",          # Giants
}


def park_meta_for_team(team_id: int) -> dict | None:
    """Stats API team_id → ballpark metadata. Bilinmeyen → None."""
    park_id = TEAM_ID_TO_PARK_ID.get(team_id)
    if park_id is None:
        return None
    return _DEFAULT_BALLPARK_METADATA.get(park_id)
