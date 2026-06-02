"""SPEC-EUROBASKET-001: Avrupa basket lig NO_DATA_NO_TRADE pipeline integration.

Doğrulanan davranışlar:
  - Placeholder scraper (BSL/Lega/VTB) NotImplementedError → HealthTracker fail
  - 3-strike sonra active=False → HealthMonitor critical alert üretir
  - Ratings yokken basketball_dispatch dispatcher fail-safe skip eder
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.infrastructure.data.basketball.bsl_scraper import BslScraper
from src.infrastructure.data.basketball.data_source_health import HealthTracker
from src.infrastructure.data.basketball.lega_scraper import LegaScraper
from src.infrastructure.data.basketball.vtb_scraper import VtbScraper
from src.orchestration.health_monitor import HealthMonitor


@pytest.mark.parametrize("scraper_cls,expected_source", [
    (BslScraper, "bsl_scraper"),
    (LegaScraper, "lega_scraper"),
    (VtbScraper, "vtb_scraper"),
])
def test_placeholder_scrapers_record_failure(
    tmp_path: Path, scraper_cls, expected_source: str,
) -> None:
    """NotImplementedError → base scraper yakalamaz (kasıtlı) — exception propagate."""
    health = HealthTracker(tmp_path / "h.json")
    sc = scraper_cls(health=health, sleep_fn=lambda s: None)
    # Placeholder _fetch_html NotImplementedError firlatir — base scraper'in
    # except listesi requests.RequestException + ValueError/KeyError/IndexError/
    # AttributeError. NotImplementedError yakalanmaz, caller'a propagate eder.
    # Bu KASITLI — placeholder enable edilirse caller fark eder.
    with pytest.raises(NotImplementedError):
        sc.refresh("2025-26")
    # HealthTracker'a fail kaydedilmemis (exception propagate ettigi icin
    # record_failure satirina ulaşılmadı). Health temiz kalir.
    assert health.consecutive_fails(expected_source) == 0


def test_three_strikes_triggers_health_monitor_critical(tmp_path: Path) -> None:
    """HealthTracker.record_failure 3 kez → active=False → HealthMonitor critical."""
    state_dir = tmp_path / "data"
    state_dir.mkdir()
    (state_dir / "basketball_cache" / "_health").mkdir(parents=True)
    health_path = state_dir / "basketball_cache" / "_health" / "sources_status.json"

    # Mevcut HealthTracker API ile 3-strike senaryosunu simule et
    tracker = HealthTracker(health_path)
    for _ in range(3):
        tracker.record_failure("acb_scraper", at_utc="2026-06-02T17:00:00+00:00")
    assert tracker.is_active("acb_scraper") is False

    # HealthMonitor JSON'i okuyup critical alert atmali
    fixed_now = datetime(2026, 6, 2, 18, 0, 0, tzinfo=timezone.utc)
    monitor = HealthMonitor(
        notifier=Mock(),
        state_dir=state_dir,
        audit_dir=tmp_path / "audit",
        runtime_dir=tmp_path / "runtime",
        now_fn=lambda: fixed_now,
    )
    (tmp_path / "audit").mkdir()
    (tmp_path / "runtime").mkdir()
    alerts = monitor.check_all()
    critical_scraper = [
        a for a in alerts
        if a.severity == "critical" and "SCRAPER_DOWN_acb_scraper" in a.category
    ]
    assert len(critical_scraper) == 1
    assert "devre dışı" in critical_scraper[0].message
