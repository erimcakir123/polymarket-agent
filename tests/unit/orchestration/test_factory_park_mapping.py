from src.orchestration.factory import (
    _DEFAULT_BALLPARK_METADATA,
    TEAM_ID_TO_PARK_ID,
    park_meta_for_team,
)


def test_phillies_park_exists_in_metadata():
    park_id = TEAM_ID_TO_PARK_ID[143]  # PHI
    assert park_id in _DEFAULT_BALLPARK_METADATA


def test_guardians_park_exists_in_metadata():
    park_id = TEAM_ID_TO_PARK_ID[114]  # CLE
    assert park_id in _DEFAULT_BALLPARK_METADATA


def test_park_meta_for_phi_returns_park_dict():
    meta = park_meta_for_team(143)
    assert meta is not None
    assert "lat" in meta and "lon" in meta and "cf_orientation_deg" in meta


def test_park_meta_unknown_team_returns_none():
    assert park_meta_for_team(99999) is None


def test_all_30_teams_have_park():
    assert len(TEAM_ID_TO_PARK_ID) == 30
    for team_id, park_id in TEAM_ID_TO_PARK_ID.items():
        assert park_id in _DEFAULT_BALLPARK_METADATA, (
            f"park_id '{park_id}' for team {team_id} not in _DEFAULT_BALLPARK_METADATA"
        )
