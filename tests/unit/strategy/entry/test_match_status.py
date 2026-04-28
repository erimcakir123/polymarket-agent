"""is_match_likely_finished() — sport-aware finish heuristic tests."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from src.strategy.entry._match_status import is_match_likely_finished


def _iso_minus(hours: float) -> str:
    """ISO timestamp `hours` saat öncesi (UTC)."""
    t = datetime.now(timezone.utc) - timedelta(hours=hours)
    return t.isoformat()


class TestIsMatchLikelyFinished:
    def test_empty_match_start_returns_false(self):
        finished, _ = is_match_likely_finished("", "nba")
        assert finished is False

    def test_invalid_timestamp_returns_false(self):
        finished, _ = is_match_likely_finished("garbage-string", "nba")
        assert finished is False

    def test_nba_just_started_returns_false(self):
        """NBA 1 saat önce başladı (live, devam ediyor)."""
        finished, _ = is_match_likely_finished(_iso_minus(1.0), "nba")
        assert finished is False

    def test_nba_in_progress_returns_false(self):
        """NBA 2.5 saat önce başladı (maç bitiyor olabilir, henüz buffer içi)."""
        finished, _ = is_match_likely_finished(_iso_minus(2.5), "nba")
        # NBA duration 2.5h + 0.5h buffer = 3.0h threshold; 2.5 < 3.0 → not finished yet
        assert finished is False

    def test_nba_finished_long_ago_returns_true(self):
        """NBA 6.3 saat önce başladı (Trade 2 senaryosu) → bitmiş."""
        finished, reason = is_match_likely_finished(_iso_minus(6.3), "nba")
        assert finished is True
        assert "hours_since_start" in reason
        assert "threshold" in reason

    def test_nhl_finished_returns_true(self):
        """NHL 4 saat önce başladı (NHL 2.5h + 0.5h = 3.0h threshold)."""
        finished, _ = is_match_likely_finished(_iso_minus(4.0), "nhl")
        assert finished is True

    def test_nfl_grace_period(self):
        """NFL 3.5 saat (NFL 3.25h + 0.5h = 3.75h threshold) → henüz biten gibi değil."""
        finished, _ = is_match_likely_finished(_iso_minus(3.5), "nfl")
        assert finished is False

    def test_nfl_finished_returns_true(self):
        """NFL 4.5 saat (3.75h threshold üstünde) → bitmiş."""
        finished, _ = is_match_likely_finished(_iso_minus(4.5), "nfl")
        assert finished is True

    def test_unknown_sport_uses_default_duration(self):
        """Bilinmeyen sport → default 2.0h duration. 2.5h şüpheli, 3.0h kesin bitmiş."""
        # 2.5h üstü, 0.5 buffer → threshold 2.5h. 2.5h tam sınır.
        finished_borderline, _ = is_match_likely_finished(_iso_minus(2.4), "unknown_sport")
        finished_clear, _ = is_match_likely_finished(_iso_minus(3.0), "unknown_sport")
        assert finished_borderline is False
        assert finished_clear is True
