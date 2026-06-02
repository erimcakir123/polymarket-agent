# Telegram Alert Sistemi (SPEC)

> Tarih: 2026-06-02
> Spec ID: SPEC-TG-001
> Status: DRAFT (plan onaylanınca aktif)

---

## Problem

Bot'un Telegram bildirim altyapısı **var ama wired değil**:
- `TelegramNotifier` class hazır (`src/presentation/notifier.py`) — entry/exit/circuit_breaker/force_close/model_degraded helper'ları tanımlı
- `TelegramCommandPoller` çalışıyor (bot.log: "Telegram command poller started") — alıcı tarafı aktif (kullanıcı `/stop` yazabilir)
- `.env`'de `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` set
- `config.yaml` `telegram.enabled: false` (KAPALI) + `bot_token: ""` + `chat_id: ""`
- **`TelegramNotifier(...)` instantiate eden HİÇBİR YER YOK** (grep boş döndü)

Sonuç: Bot kullanıcıya **HİÇBİR BİLDİRİM göndermiyor**. Trade açma/kapama, hata, scraper fail, exposure cap dolu — hiçbiri telegram'a düşmüyor.

## Tam Otomasyon Hedefi

Kullanıcı 7/24 başında oturmaz. Bot kendisini yönetir AMA kullanıcıya **kritik olayları** bildirmelidir:
- ✅ Entry / Exit (her trade)
- ⚠️ Warning: STALE_PRICE_REJECT yoğun (>5/saat), exposure cap %90+ (uzun süre kilitli), ardışık fail trade (5+)
- 🔴 Critical: bot crash, scraper banlandı / cache stale >48h, audit dosya bozuk, model isabet eşik altı
- 🟢 Info: günlük özet (saat 23:00 — pozisyon sayısı, realized PnL, win rate, scraper sağlık özet)

## Mimari

### Bileşenler

```
src/presentation/notifier.py        (MEVCUT, kullanılmıyor — wire edilecek)
src/orchestration/factory.py        (TelegramNotifier instantiate + DI)
src/config/settings.py              (env override — .env'den token/chat_id auto-load)
src/orchestration/entry_processor.py (notify_entry hook)
src/orchestration/exit_processor.py  (notify_exit hook)
src/orchestration/health_monitor.py  (YENİ — periyodik health check + warning/critical alert)
src/infrastructure/telegram/         (mevcut command_poller + alert_sender ek)
```

### Veri Akışı

1. **Entry**:
   - `entry_processor._execute_entry` → trade open
   - sonra: `notifier.notify_entry(slug, direction, price, size, conf, edge, reason)`

2. **Exit**:
   - `exit_processor._execute_exit` → trade close
   - sonra: `notifier.notify_exit(slug, exit_price, realized_pnl, reason)`

3. **Health check** (periyodik, light cycle'da):
   - `health_monitor.check()` → durum dict
   - kritik anomali tespit → `notifier.notify_critical(category, detail)`
   - warning → `notifier.notify_warning(category, detail)`

4. **Crash / atexit**:
   - Python `atexit` handler → `notifier.notify_critical("BOT_DOWN", str(reason))`
   - Process kill (reboot.py) → graceful son mesaj

### Config

```yaml
# config.yaml
telegram:
  enabled: true           # ← önceden false
  bot_token: ""           # .env override (boş bırakılırsa env'den okunur)
  chat_id: ""             # aynı
  # 2026-06-02: Alert seviye eşikleri
  alert:
    entry_exit: true                    # her trade için bildirim
    health_check_interval_sec: 300      # 5dk'da bir health check
    stale_price_rate_threshold: 5       # /saat — bu değerin üstünde warning
    exposure_lockup_minutes: 60         # exposure cap %90+ bu kadar süre → warning
    consecutive_losses: 5               # ardışık zarar → warning
    daily_summary_hour_utc: 20          # 23:00 TR (UTC+3) günlük özet
```

### Env Override

```python
# src/config/settings.py — load_config içinde
def _apply_env_overrides(data: dict) -> dict:
    """Sensitive credentials .env'den override (config.yaml boş bırakılırsa)."""
    import os
    tg = data.setdefault("telegram", {})
    if not tg.get("bot_token"):
        tg["bot_token"] = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not tg.get("chat_id"):
        tg["chat_id"] = os.environ.get("TELEGRAM_CHAT_ID", "")
    return data
```

## Health Monitor Tasarımı

`src/orchestration/health_monitor.py` (yeni dosya, ~150 satır):

```python
class HealthMonitor:
    """Periyodik health check + warning/critical alert tetikleyici.

    Light cycle'da agent.py'den çağrılır. State tutmaz; her tick'te güncel
    bot_status + skipped_trades + positions snapshot'ından durumu hesaplar.
    """

    def __init__(self, notifier, config, state_dir, audit_dir):
        ...

    def check(self) -> list[Alert]:
        """Tüm health check'leri çalıştır, alert listesi döner."""
        alerts = []
        alerts.extend(self._check_stale_price_rate())
        alerts.extend(self._check_exposure_lockup())
        alerts.extend(self._check_consecutive_losses())
        alerts.extend(self._check_scraper_health())  # data_source_health.json oku
        alerts.extend(self._check_calibration_age())
        return alerts

    def daily_summary(self) -> str:
        """Günlük özet metin (positions, realized, win rate)."""
        ...
```

## Out of Scope

- Telegram inline keyboard (sadece düz mesaj)
- Çoklu chat_id (sadece tek kullanıcı)
- Mesaj geçmişi DB'si
- Polymarket'in kendi alert sistemi

## Risk

- Telegram rate limit (30 msg/sn) → throttle gerekli (notifier'da var, kontrol et)
- Tekrarlayan alert spam'i → "son N dakika içinde aynı alert ataba" guard
- .env credentials yanlış / yetkisiz → alert sessizce fail (notifier `enabled` false döner) — kullanıcı `python scripts/test_telegram.py` ile test edebilir

## Done Definition

- Bot başlangıçta "test mesajı" gönderir → kullanıcı doğrular bağlantı OK
- Her entry/exit telegram'a düşer
- Scraper fail / exposure lockup / stale price spike alert gelir
- Günlük 23:00 (TR) özet mesajı gelir
- Bot crash → atexit alert
- 1894+ test geçer
- Config flag ile alert kategorileri açılıp kapanabilir
