"""Telegram config — TelegramConfig + TelegramAlertConfig (SPEC-TG-001).

settings.py'dan ayrildi (ARCH_GUARD Kural 3: 400 satir limiti).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TelegramAlertConfig(BaseModel):
    """HealthMonitor alert esikleri."""
    model_config = ConfigDict(extra="ignore")
    entry_exit: bool = True                        # her trade icin entry/exit mesaji
    health_check_interval_sec: int = 300           # 5dk: HealthMonitor.check_all sikligi
    stale_price_rate_threshold: int = 5            # /saat - bu sayinin ustu warning
    exposure_lockup_minutes: int = 60              # exposure %90+ bu kadar dakika warning
    consecutive_losses: int = 5                    # ardisik zarar warning
    daily_summary_hour_utc: int = 20               # 23:00 TR (UTC+3) gunluk ozet
    dedupe_window_minutes: int = 30                # ayni alert N dk icinde tekrar atilmaz
    calibration_stale_days: int = 7                # tennis_calibration.json N gun+ eski warning
    scraper_stale_hours: int = 24                  # data source last_success N saat+ eski warning
    odds_low_credit_threshold: int = 50            # Odds API kalan kredi < bu → warning (bitince critical)
    # SPEC-Z10 (2026-06-03): Kategori bazli alert mute. Tam category match.
    # Avrupa basket scraper'lar (ACB/BSL/Lega) HTML parser revize bekliyor;
    # bu lig'ler ML-only (totals/spreads exclude_combos ile kapali) ve cache
    # yok zaten — scraper down/stale spam'i kullaniciyi gereksiz geriyordu.
    muted_alert_categories: list[str] = []


class TelegramConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    alert: TelegramAlertConfig = TelegramAlertConfig()
