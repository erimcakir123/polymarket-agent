import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from src.orchestration.score_enricher import ScoreEnricher
from src.models.position import Position

@pytest.fixture
def mock_espn():
    return MagicMock()

@pytest.fixture
def enricher(mock_espn):
    return ScoreEnricher(espn_client=mock_espn)

def test_refresh_scores_multi_league_tennis(enricher, mock_espn):
    # Setup: 1 ATP, 1 WTA position
    now_iso = datetime.now(timezone.utc).isoformat()
    
    pos_atp = Position(
        condition_id="0x1",
        token_id="t1",
        direction="BUY_YES",
        slug="atp-madrid-2026",
        sport_tag="tennis",
        match_start_iso=now_iso,
        entry_price=0.5,
        size_usdc=50.0,
        shares=100.0,
        anchor_probability=0.5,
        current_price=0.5
    )
    pos_wta = Position(
        condition_id="0x2",
        token_id="t2",
        direction="BUY_YES",
        slug="wta-madrid-2026",
        sport_tag="tennis",
        match_start_iso=now_iso,
        entry_price=0.5,
        size_usdc=50.0,
        shares=100.0,
        anchor_probability=0.5,
        current_price=0.5
    )
    
    positions = {"0x1": pos_atp, "0x2": pos_wta}
    
    # Mock responses
    mock_espn.fetch.side_effect = [
        [MagicMock(event_id="e1", home_name="ATP Player 1", away_name="ATP Player 2")],
        [MagicMock(event_id="e2", home_name="WTA Player 1", away_name="WTA Player 2")]
    ]
    
    # Execute
    enricher._refresh_scores(positions)
    
    # Verify: fetch called twice (once for atp, once for wta)
    assert mock_espn.fetch.call_count == 2
    calls = [c[0] for c in mock_espn.fetch.call_args_list]
    assert ("tennis", "atp") in calls
    assert ("tennis", "wta") in calls
    
    # Verify: cached_espn has both merged
    assert "tennis" in enricher._cached_espn
    assert len(enricher._cached_espn["tennis"]) == 2
    event_ids = [m.event_id for m in enricher._cached_espn["tennis"]]
    assert "e1" in event_ids
    assert "e2" in event_ids

def test_refresh_scores_multi_league_soccer(enricher, mock_espn):
    # Setup: 2 soccer positions in different leagues
    now_iso = datetime.now(timezone.utc).isoformat()
    
    mock_discovery = MagicMock()
    enricher._soccer_discovery = mock_discovery
    mock_discovery.discover.side_effect = ["eng.1", "esp.1"]
    
    pos1 = Position(
        condition_id="s1",
        token_id="ts1",
        direction="BUY_YES",
        slug="score-epl",
        sport_tag="soccer",
        match_start_iso=now_iso,
        entry_price=0.5,
        size_usdc=50.0,
        shares=100.0,
        anchor_probability=0.5,
        current_price=0.5
    )
    pos2 = Position(
        condition_id="s2",
        token_id="ts2",
        direction="BUY_YES",
        slug="score-laliga",
        sport_tag="soccer",
        match_start_iso=now_iso,
        entry_price=0.5,
        size_usdc=50.0,
        shares=100.0,
        anchor_probability=0.5,
        current_price=0.5
    )
    
    positions = {"s1": pos1, "s2": pos2}
    
    mock_espn.fetch.side_effect = [
        [MagicMock(event_id="se1")],
        [MagicMock(event_id="se2")]
    ]
    
    # Execute
    enricher._refresh_scores(positions)
    
    # Verify
    assert mock_espn.fetch.call_count == 2
    calls = [c[0] for c in mock_espn.fetch.call_args_list]
    assert ("soccer", "eng.1") in calls
    assert ("soccer", "esp.1") in calls
    assert len(enricher._cached_espn["soccer"]) == 2
