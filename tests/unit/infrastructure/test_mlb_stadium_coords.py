from src.infrastructure.data.mlb_stadium_coords import (
    STADIUM_COORDS,
    get_stadium_coords,
)


def test_coords_count_30():
    assert len(STADIUM_COORDS) == 30


def test_coords_format_lat_lon():
    lat, lon = get_stadium_coords("NYY")
    assert -90 < lat < 90
    assert -180 < lon < 180


def test_unknown_team_returns_none():
    assert get_stadium_coords("XXX") is None
