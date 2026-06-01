"""Generic cache age check — NO DATA → NO TRADE prensibi.

Scrape kaynaklarda (BRScraper BSL/ACB/Lega) captcha/IP block durumunda
sessiz bayat veri ile trade açmamak için tüm lig refresher'larının
ortak guard'ı. Tenis Sackmann + basket nba_api/ESPN/euroleague için de
opsiyonel kullanılır.

Domain-pure değil — Path operations (stat). Infrastructure layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Optional


# 24h default — bir sezonun normal güncellemesi maks 1 günde gelir.
# Scrape kaynaklarda daha sıkı (12h) yapılabilir, lig-başına override.
MAX_CACHE_AGE_HOURS = 24.0


@dataclass(frozen=True)
class SourceFreshnessResult:
    """Cache freshness karar sonucu."""
    fresh: bool
    age_hours: float
    reason: Optional[str] = None  # 'cache_missing' | 'cache_too_old' | None


def is_source_fresh(
    cache_path: Path,
    max_age_hours: float = MAX_CACHE_AGE_HOURS,
) -> SourceFreshnessResult:
    """Cache dosyası taze mi? NO DATA → NO TRADE prensibi.

    Returns:
      SourceFreshnessResult(fresh=True) → bot bu lig için bahis açabilir
      SourceFreshnessResult(fresh=False) → bot SUS, lig hibernation
    """
    if not cache_path.exists():
        return SourceFreshnessResult(
            fresh=False, age_hours=float("inf"), reason="cache_missing",
        )
    age_hours = (time() - cache_path.stat().st_mtime) / 3600.0
    if age_hours > max_age_hours:
        return SourceFreshnessResult(
            fresh=False, age_hours=age_hours, reason="cache_too_old",
        )
    return SourceFreshnessResult(fresh=True, age_hours=age_hours)
