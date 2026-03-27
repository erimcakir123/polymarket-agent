"""Tests for Odds API bridge infrastructure."""
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


def _make_client():
    """Create OddsAPIClient with no real API key (tests use mocks)."""
    from src.odds_api import OddsAPIClient
    client = OddsAPIClient.__new__(OddsAPIClient)
    client.api_key = "test-key"
    client._backup_key = ""
    client._using_backup = False
    client._cache = {}
    client._cache_ttl = 28800
    client._hist_cache_ttl = 28800
    client._requests_used = 0
    client._notified_80 = False
    client._notified_95 = False
    client._notifier = None
    return client


class TestRefreshSchedule:
    def test_8_refresh_boundaries(self):
        """Refresh schedule must have 8 boundaries covering NBA prime time."""
        from src.odds_api import OddsAPIClient
        hours = OddsAPIClient._REFRESH_HOURS_UTC
        assert len(hours) == 8
        # Must cover NBA prime time gap: hours 23 and 5 must be present
        assert 23 in hours, "23 UTC missing — NBA tip-off wave 1 uncovered"
        assert 5 in hours, "05 UTC missing — overnight wrap uncovered"
        assert 12 in hours, "12 UTC missing — European midday uncovered"

    def test_boundary_crossed_at_23_utc(self):
        """Cache from 21:30 UTC must be stale at 23:01 UTC (NBA window)."""
        client = _make_client()
        # Simulate cache written at 21:30 UTC today
        cached_dt = datetime.now(timezone.utc).replace(hour=21, minute=30, second=0)
        cached_ts = cached_dt.timestamp()
        # Check at 23:01 UTC
        with patch("src.odds_api.datetime") as mock_dt:
            mock_dt.now.return_value = cached_dt.replace(hour=23, minute=1)
            mock_dt.fromtimestamp = datetime.fromtimestamp
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = client._past_refresh_boundary(cached_ts)
        assert result is True, "21:30→23:01 should cross boundary 23"
