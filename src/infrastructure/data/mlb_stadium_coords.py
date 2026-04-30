"""MLB stadium lat/lon for weather lookups.

Coordinates approximate (stadium centroid). Used by openweather_client
to fetch 3-hour forecast for game time.
"""
from __future__ import annotations


STADIUM_COORDS: dict[str, tuple[float, float]] = {
    "ARI": (33.4453, -112.0667),
    "ATL": (33.8908, -84.4678),
    "BAL": (39.2840, -76.6217),
    "BOS": (42.3467, -71.0972),
    "CHC": (41.9484, -87.6553),
    "CWS": (41.8299, -87.6338),
    "CIN": (39.0975, -84.5072),
    "CLE": (41.4962, -81.6852),
    "COL": (39.7559, -104.9942),
    "DET": (42.3390, -83.0485),
    "HOU": (29.7572, -95.3553),
    "KC":  (39.0517, -94.4803),
    "LAA": (33.8003, -117.8827),
    "LAD": (34.0739, -118.2400),
    "MIA": (25.7781, -80.2197),
    "MIL": (43.0280, -87.9712),
    "MIN": (44.9817, -93.2776),
    "NYM": (40.7571, -73.8458),
    "NYY": (40.8296, -73.9262),
    "OAK": (37.7516, -122.2008),
    "PHI": (39.9061, -75.1665),
    "PIT": (40.4469, -80.0057),
    "SD":  (32.7073, -117.1566),
    "SEA": (47.5914, -122.3325),
    "SF":  (37.7786, -122.3893),
    "STL": (38.6226, -90.1928),
    "TB":  (27.7682, -82.6534),
    "TEX": (32.7472, -97.0817),
    "TOR": (43.6414, -79.3894),
    "WSH": (38.8730, -77.0074),
}


def get_stadium_coords(team_abbr: str | None) -> tuple[float, float] | None:
    """Return (lat, lon) for team's stadium; None if unknown."""
    if not team_abbr:
        return None
    return STADIUM_COORDS.get(team_abbr.upper())
