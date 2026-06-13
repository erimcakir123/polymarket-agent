"""data_freshness — reyting verisi yaşı → bayat mı saf kararı."""
from src.domain.pricing.tennis.data_freshness import is_ratings_stale


def test_fresh_when_newest_within_threshold():
    assert is_ratings_stale(newest_yyyymmdd="20260612", today_yyyymmdd="20260613", threshold_days=4) is False


def test_stale_when_newest_older_than_threshold():
    assert is_ratings_stale(newest_yyyymmdd="20260525", today_yyyymmdd="20260613", threshold_days=4) is True


def test_stale_when_no_data():
    assert is_ratings_stale(newest_yyyymmdd=None, today_yyyymmdd="20260613", threshold_days=4) is True


def test_boundary_exactly_threshold_is_fresh():
    # 4 gün fark, eşik 4 → bayat DEĞİL (<=)
    assert is_ratings_stale(newest_yyyymmdd="20260609", today_yyyymmdd="20260613", threshold_days=4) is False
