"""factory_refresh_hooks testleri — PLAN-DATA1 (eşik config + günlük periyot kararı)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.orchestration import factory_refresh_hooks as hooks


def test_is_daily_check_due_first_time_true():
    now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    assert hooks.is_daily_check_due(None, now) is True


def test_is_daily_check_due_within_period_false():
    now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    assert hooks.is_daily_check_due(now - timedelta(hours=23), now) is False


def test_is_daily_check_due_after_period_true():
    now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    assert hooks.is_daily_check_due(now - timedelta(hours=25), now) is True


def test_startup_refresh_passes_max_age_to_staleness_check(monkeypatch, tmp_path):
    seen: dict = {}

    def fake_stale(cache_dir: Path, max_age_days: int) -> bool:
        seen["stale_args"] = (cache_dir, max_age_days)
        return False  # fresh → indirme yok

    monkeypatch.setattr(hooks, "is_cache_stale", fake_stale)
    hooks.maybe_refresh_sackmann_on_startup(tmp_path, max_age_days=1)
    assert seen["stale_args"] == (tmp_path, 1)


def test_startup_refresh_stale_calls_refresh_with_max_age(monkeypatch, tmp_path):
    seen: dict = {}
    monkeypatch.setattr(hooks, "is_cache_stale", lambda d, a: True)

    def fake_refresh(cache_dir: Path, max_age_days: int) -> bool:
        seen["refresh_args"] = (cache_dir, max_age_days)
        return False  # indirme başarısız senaryosu → rebuild atlanır

    monkeypatch.setattr(hooks, "refresh_if_stale", fake_refresh)
    hooks.maybe_refresh_sackmann_on_startup(tmp_path, max_age_days=2)
    assert seen["refresh_args"] == (tmp_path, 2)
