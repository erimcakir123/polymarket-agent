# tests/test_scout_dedup.py
import time
from unittest.mock import MagicMock, patch


def _make_scout():
    from src.scout_scheduler import ScoutScheduler
    sports = MagicMock()
    esports = MagicMock()
    esports.available = False
    with patch("src.scout_scheduler.SCOUT_QUEUE_FILE") as qf:
        qf.exists.return_value = False
        s = ScoutScheduler(sports, esports)
    return s


def test_scout_does_not_rerun_within_4h():
    """run_scout called twice in quick succession must return 0 on 2nd call."""
    scout = _make_scout()
    scout._last_run_ts = time.time()  # Pretend ran just now
    with patch.object(scout, "_fetch_espn_upcoming", return_value=[]):
        with patch.object(scout, "_fetch_esports_upcoming", return_value=[]):
            result = scout.run_scout()
    assert result == 0, f"Expected 0, got {result}"


def test_scout_runs_after_cooldown_expires():
    """run_scout should proceed when last run was >4h ago."""
    scout = _make_scout()
    scout._last_run_ts = time.time() - 5 * 3600  # 5 hours ago
    with patch.object(scout, "_fetch_espn_upcoming", return_value=[]):
        with patch.object(scout, "_fetch_esports_upcoming", return_value=[]):
            with patch.object(scout, "_save_queue"):
                with patch("src.scout_scheduler.SCOUT_MARKER_FILE") as mf:
                    mf.parent = MagicMock()
                    result = scout.run_scout()
    assert result == 0  # 0 new matches (empty feeds), but ran
    assert scout._last_run_ts > time.time() - 10  # timestamp was updated
