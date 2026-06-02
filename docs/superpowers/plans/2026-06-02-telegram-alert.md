# Telegram Alert Sistemi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TelegramNotifier'ı wire et + health monitor ekle + .env override → bot tüm kritik olayları kullanıcıya gönderir.

**Architecture:** DI pattern (factory'de notifier oluştur, dependent processor'lara inject). HealthMonitor yeni domain — light cycle'da çağrılır. Throttle + dedupe.

**Tech Stack:** Python 3.12+, requests, .env (python-dotenv mevcut), Telegram Bot API.

---

## Task 1: Settings .env Override

**Files:**
- Modify: `src/config/settings.py:380-400` (load_config içinde)
- Test: `tests/unit/config/test_env_override.py` (yeni)

- [ ] **Step 1.1: Test yaz**

```python
# tests/unit/config/test_env_override.py
import os
from unittest.mock import patch
from pathlib import Path
from src.config.settings import load_config

def test_telegram_credentials_from_env(tmp_path):
    """config.yaml'da boş bırakılan token/chat_id .env'den alınır."""
    cfg_file = tmp_path / "test.yaml"
    cfg_file.write_text("""
mode: paper
initial_bankroll: 1000.0
telegram:
  enabled: true
  bot_token: ""
  chat_id: ""
""")
    with patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test-token-123",
        "TELEGRAM_CHAT_ID": "test-chat-456",
    }):
        cfg = load_config(cfg_file)
    assert cfg.telegram.bot_token == "test-token-123"
    assert cfg.telegram.chat_id == "test-chat-456"


def test_telegram_config_explicit_wins(tmp_path):
    """config.yaml'da değer varsa .env'i override etmez."""
    cfg_file = tmp_path / "test.yaml"
    cfg_file.write_text("""
mode: paper
initial_bankroll: 1000.0
telegram:
  enabled: true
  bot_token: "explicit-token"
  chat_id: "explicit-chat"
""")
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "env-token"}):
        cfg = load_config(cfg_file)
    assert cfg.telegram.bot_token == "explicit-token"
```

- [ ] **Step 1.2: Test FAIL doğrula**

Run: `pytest tests/unit/config/test_env_override.py -v`
Expected: FAIL (settings.py'da env override yok)

- [ ] **Step 1.3: settings.py implement**

`load_config` içinde, telegram section'a env fallback:

```python
# src/config/settings.py — load_config yakınında, parse öncesi
import os

def _apply_env_overrides(data: dict) -> dict:
    """Sensitive credentials .env'den override (config.yaml boş bırakılırsa)."""
    tg = data.setdefault("telegram", {})
    if not tg.get("bot_token"):
        tg["bot_token"] = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not tg.get("chat_id"):
        tg["chat_id"] = os.environ.get("TELEGRAM_CHAT_ID", "")
    return data


def load_config(path: Path) -> AppConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw = _apply_env_overrides(raw)
    # ... mevcut parse devam
```

- [ ] **Step 1.4: Test PASS doğrula**

Run: `pytest tests/unit/config/test_env_override.py -v`
Expected: PASS

- [ ] **Step 1.5: Commit**

```bash
git add src/config/settings.py tests/unit/config/test_env_override.py
git commit -m "feat(config): .env override for telegram credentials"
```

---

## Task 2: Factory'de TelegramNotifier Wire

**Files:**
- Modify: `src/orchestration/factory.py:255-265` (telegram bölümü)
- Test: yok (DI smoke test factory ile)

- [ ] **Step 2.1: factory.py'da TelegramNotifier oluştur**

Mevcut kod (factory.py:258 civarı):

```python
tg = cfg.telegram
if tg.enabled and tg.bot_token and tg.chat_id:
    command_poller = TelegramCommandPoller(
        bot_token=tg.bot_token, chat_id=tg.chat_id, on_stop=lambda: None,
    )
```

Yeni:

```python
from src.presentation.notifier import TelegramNotifier

# ... yukarıdan TelegramCommandPoller mevcut

tg = cfg.telegram
notifier = TelegramNotifier(
    enabled=tg.enabled,
    bot_token=tg.bot_token,
    chat_id=tg.chat_id,
)
if tg.enabled and tg.bot_token and tg.chat_id:
    command_poller = TelegramCommandPoller(
        bot_token=tg.bot_token, chat_id=tg.chat_id, on_stop=lambda: None,
    )
    # Boot mesajı: kullanıcı bağlantıyı doğrulasın
    notifier.send(
        f"🤖 <b>Bot başladı</b>\n"
        f"Mode: {cfg.mode.value}\n"
        f"Bankroll: ${cfg.initial_bankroll:.0f}"
    )
else:
    command_poller = None
```

- [ ] **Step 2.2: AgentDeps'e notifier ekle**

`src/orchestration/factory.py` AgentDeps namedtuple/dataclass'ına `notifier: TelegramNotifier` field ekle. Agent constructor'a inject et.

- [ ] **Step 2.3: Manuel boot test**

Bot'u başlat (`python scripts/reboot.py reload --mode paper`). Telegram'a "Bot başladı" mesajı düşmeli.

- [ ] **Step 2.4: Commit**

```bash
git add src/orchestration/factory.py
git commit -m "feat(telegram): TelegramNotifier wire + boot mesajı"
```

---

## Task 3: Entry/Exit Notify Çağrıları

**Files:**
- Modify: `src/orchestration/entry_processor.py:385` (trade_logger.log sonrası)
- Modify: `src/orchestration/exit_processor.py` (exit log sonrası)
- Test: `tests/unit/orchestration/test_entry_processor_notify.py` (yeni)

- [ ] **Step 3.1: Entry notify test yaz**

```python
# tests/unit/orchestration/test_entry_processor_notify.py
from unittest.mock import Mock

def test_entry_processor_calls_notify_entry_on_success():
    notifier = Mock()
    # ... entry processor mocked deps ile çağır
    # Beklenen: notifier.notify_entry çağrıldı, doğru argümanlarla
    notifier.notify_entry.assert_called_once_with(
        slug=...,
        direction=...,
        entry_price=...,
        size_usdc=...,
        confidence=...,
        edge=...,
        entry_reason=...,
    )
```

- [ ] **Step 3.2: Test FAIL doğrula**

Run: `pytest tests/unit/orchestration/test_entry_processor_notify.py -v`
Expected: FAIL (entry_processor henüz notifier çağırmıyor)

- [ ] **Step 3.3: entry_processor.py implement**

`_execute_entry` sonunda, `trade_logger.log(record)` satırının ardından:

```python
# Telegram notify (opsiyonel — enabled=False ise no-op)
self.deps.notifier.notify_entry(
    slug=market.slug,
    direction=signal.direction.value,
    entry_price=pos.entry_price,
    size_usdc=pos.size_usdc,
    confidence=signal.confidence,
    edge=signal.edge,
    entry_reason=signal.entry_reason.value,
)
```

- [ ] **Step 3.4: Test PASS doğrula**

Run: `pytest tests/unit/orchestration/test_entry_processor_notify.py -v`
Expected: PASS

- [ ] **Step 3.5: Exit notify aynı pattern**

`exit_processor.py`'da exit log sonrası:

```python
self.deps.notifier.notify_exit(
    slug=pos.slug,
    exit_price=fill_price,
    realized_pnl=realized,
    reason=exit_reason.value,
)
```

- [ ] **Step 3.6: Test (exit) yaz + PASS**

```python
# tests/unit/orchestration/test_exit_processor_notify.py — benzer pattern
```

- [ ] **Step 3.7: Full pytest**

Run: `python -m pytest -q`

- [ ] **Step 3.8: Commit**

```bash
git add src/orchestration/entry_processor.py src/orchestration/exit_processor.py tests/unit/orchestration/test_*_notify.py
git commit -m "feat(telegram): entry/exit notify hooks"
```

---

## Task 4: Health Monitor (Yeni Dosya)

**Files:**
- Create: `src/orchestration/health_monitor.py` (~150 satır)
- Modify: `src/orchestration/agent.py` (light cycle'da health.check() çağrısı)
- Test: `tests/unit/orchestration/test_health_monitor.py`

- [ ] **Step 4.1: Domain model**

```python
# src/orchestration/health_monitor.py
"""Periyodik health check — agent.py light cycle'dan çağrılır.

Sport-agnostic: tüm scraper'lar/sport_tag'ler için aynı pattern. Yeni eklenen
ligler/scraper'lar otomatik kapsanır (data_source_health.json okuma).
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import logging
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Alert:
    severity: str  # "critical" | "warning" | "info"
    category: str  # "stale_price" | "exposure_lockup" | "scraper_down" | ...
    message: str


class HealthMonitor:
    """Periyodik health check + dedupe (aynı alert N dk içinde tekrar atılmaz)."""

    def __init__(
        self,
        notifier,
        state_dir: Path,
        audit_dir: Path,
        runtime_dir: Path,
        stale_price_threshold: int = 5,
        exposure_lockup_minutes: int = 60,
        consecutive_losses: int = 5,
        dedupe_window_minutes: int = 30,
    ):
        self.notifier = notifier
        self.state_dir = state_dir
        self.audit_dir = audit_dir
        self.runtime_dir = runtime_dir
        self.stale_price_threshold = stale_price_threshold
        self.exposure_lockup_minutes = exposure_lockup_minutes
        self.consecutive_losses_threshold = consecutive_losses
        self.dedupe_window = dedupe_window_minutes
        self._sent_alerts: dict[tuple[str, str], datetime] = {}

    def check_all(self) -> list[Alert]:
        alerts = []
        alerts.extend(self._check_stale_price_rate())
        alerts.extend(self._check_exposure_lockup())
        alerts.extend(self._check_consecutive_losses())
        alerts.extend(self._check_scraper_health())
        alerts.extend(self._check_calibration_age())
        return alerts

    def send_alerts(self, alerts: list[Alert]) -> None:
        """Throttle/dedupe ile alert gönder."""
        now = datetime.now(timezone.utc)
        for alert in alerts:
            key = (alert.severity, alert.category)
            last = self._sent_alerts.get(key)
            if last and (now - last).total_seconds() < self.dedupe_window * 60:
                continue
            emoji = {"critical": "🔴", "warning": "⚠️", "info": "🟢"}.get(alert.severity, "")
            msg = f"{emoji} <b>{alert.category}</b>\n{alert.message}"
            self.notifier.send(msg)
            self._sent_alerts[key] = now

    # ── Spesifik check'ler ──

    def _check_stale_price_rate(self) -> list[Alert]:
        """Son 1 saatte STALE_PRICE_REJECT > threshold ise warning."""
        from datetime import timedelta
        log_path = self.runtime_dir / "bot.log"
        if not log_path.exists():
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        count = 0
        with log_path.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "STALE_PRICE_REJECT" not in line:
                    continue
                # ... parse timestamp, cutoff sonrası say
                count += 1
        if count >= self.stale_price_threshold:
            return [Alert(
                severity="warning",
                category="STALE_PRICE_RATE",
                message=f"Son 1 saatte {count} stale price reject (eşik: {self.stale_price_threshold})",
            )]
        return []

    def _check_exposure_lockup(self) -> list[Alert]:
        """positions.json invested / total_equity > 0.9 + duration > threshold → warning."""
        # ... implement
        return []

    def _check_consecutive_losses(self) -> list[Alert]:
        """trade_history son N exit'in hepsi zarar → warning."""
        # ... implement
        return []

    def _check_scraper_health(self) -> list[Alert]:
        """data_source_health.json oku — herhangi bir source 'broken' ise critical."""
        health = self.state_dir / "basketball_cache" / "_health" / "sources_status.json"
        if not health.exists():
            return []
        try:
            data = json.loads(health.read_text(encoding="utf-8"))
        except Exception:
            return []
        alerts = []
        for source, status in data.items():
            if isinstance(status, dict) and status.get("state") == "broken":
                alerts.append(Alert(
                    severity="critical",
                    category=f"SCRAPER_DOWN_{source}",
                    message=f"Veri kaynağı '{source}' çalışmıyor. Son fail: {status.get('last_fail','')}",
                ))
        return alerts

    def _check_calibration_age(self) -> list[Alert]:
        """tennis_calibration.json > 7 gün eski → info."""
        # ... implement
        return []

    def daily_summary(self, positions_path: Path) -> str:
        """Günlük 23:00 özet."""
        # ... pos sayısı, realized, win rate, sport breakdown
        return ""
```

- [ ] **Step 4.2: Test yaz**

```python
# tests/unit/orchestration/test_health_monitor.py
def test_health_monitor_scraper_down_triggers_critical(tmp_path):
    """data_source_health.json broken state → critical alert."""
    state_dir = tmp_path / "data"
    (state_dir / "basketball_cache" / "_health").mkdir(parents=True)
    (state_dir / "basketball_cache" / "_health" / "sources_status.json").write_text(
        '{"nba_api": {"state": "broken", "last_fail": "2026-06-02T18:00"}}'
    )
    notifier = Mock()
    monitor = HealthMonitor(notifier, state_dir, tmp_path / "logs/audit", tmp_path / "logs/runtime")
    alerts = monitor.check_all()
    assert any(a.severity == "critical" and "SCRAPER_DOWN" in a.category for a in alerts)


def test_dedupe_prevents_spam():
    """Aynı alert dedupe_window içinde tekrar gönderilmez."""
    # ...
```

- [ ] **Step 4.3: Test PASS**

Run: `pytest tests/unit/orchestration/test_health_monitor.py -v`

- [ ] **Step 4.4: agent.py'a entegre et**

Light cycle'da (her N saniyede bir):

```python
# src/orchestration/agent.py — light tick içinde
if self._health_tick % HEALTH_CHECK_EVERY_N_TICKS == 0:
    alerts = self.health.check_all()
    self.health.send_alerts(alerts)
self._health_tick += 1
```

`HEALTH_CHECK_EVERY_N_TICKS = config.telegram.alert.health_check_interval_sec / light_interval_sec`.

- [ ] **Step 4.5: Daily summary cron (basit)**

`agent.py`'da `_last_daily_summary_date` track + her tick'te UTC saat == config.daily_summary_hour_utc ise summary gönder.

- [ ] **Step 4.6: Commit**

```bash
git add src/orchestration/health_monitor.py src/orchestration/agent.py tests/unit/orchestration/test_health_monitor.py
git commit -m "feat(telegram): HealthMonitor — periyodik check + scraper/exposure/staleprice alerts"
```

---

## Task 5: Atexit Critical Alert + Config Aktif

**Files:**
- Modify: `src/main.py` (atexit handler)
- Modify: `config.yaml` (telegram.enabled: true + alert section)

- [ ] **Step 5.1: main.py atexit handler ekle**

```python
# src/main.py
import atexit

def _on_exit_alert(notifier):
    def _handler():
        notifier.send("🔴 <b>Bot kapandı</b>\nProcess exit detected.")
    return _handler

# main() içinde, agent build sonrası:
atexit.register(_on_exit_alert(agent.deps.notifier))
```

- [ ] **Step 5.2: config.yaml güncelle**

```yaml
telegram:
  enabled: true
  bot_token: ""        # .env'den override
  chat_id: ""          # .env'den override
  alert:
    entry_exit: true
    health_check_interval_sec: 300
    stale_price_rate_threshold: 5
    exposure_lockup_minutes: 60
    consecutive_losses: 5
    daily_summary_hour_utc: 20
```

- [ ] **Step 5.3: Settings model alert section ekle**

```python
# src/config/settings.py — TelegramConfig'e alt-class
class TelegramAlertConfig(BaseModel):
    entry_exit: bool = True
    health_check_interval_sec: int = 300
    stale_price_rate_threshold: int = 5
    exposure_lockup_minutes: int = 60
    consecutive_losses: int = 5
    daily_summary_hour_utc: int = 20


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    alert: TelegramAlertConfig = TelegramAlertConfig()
```

- [ ] **Step 5.4: Manuel test — telegram'a mesaj gelsin**

Run: `python scripts/reboot.py reload --mode paper`
Expected: Telegram'a "Bot başladı" mesajı düşer.

- [ ] **Step 5.5: Full pytest**

Run: `python -m pytest -q`
Expected: 1894+ passed, 0 fail.

- [ ] **Step 5.6: Commit**

```bash
git add src/main.py config.yaml src/config/settings.py
git commit -m "feat(telegram): atexit critical alert + config aktif + alert eşikleri"
```

---

## Final Self-Review

- [ ] **Spec coverage:** SPEC-TG-001 tüm gereksinimler → 5 Task'a dağıtılmış ✓
- [ ] **Yan task atlama:** entry/exit notify, health check (5 kategori), atexit, env override → kapsam tam
- [ ] **Future-proof:** Health monitor yeni scraper'lar/scrub kategorileri için extendable (Alert dataclass + check_* metod ekleyerek)
- [ ] **ARCH_GUARD:** HealthMonitor domain'de I/O sadece read-only (positions.json, audit/, runtime/); 200 satır altında
- [ ] **Dead code yok:** TelegramNotifier mevcut + wire edildi (yeni class değil)
- [ ] **Drift yok:** Alert config flag'lere bağlı, açılıp kapatılabilir; dedupe spam'i önler

---

## Execution Order

1. Task 1 (env override) — bağımsız (~15dk)
2. Task 2 (factory wire) — Task 1 bağımlı (~20dk)
3. Task 3 (entry/exit notify) — Task 2 bağımlı (~30dk)
4. Task 4 (health monitor) — Task 2 bağımlı, Task 3 paralel olabilir (~40dk)
5. Task 5 (atexit + config) — Task 1-4 bağımlı (~10dk)

**Toplam:** ~2 saat

## Verification Before Completion

- [ ] 1894+ pytest passed
- [ ] Bot reload sonrası "Bot başladı" telegram mesajı geldi
- [ ] Manuel entry/exit test → telegram'a düştü
- [ ] Sahte scraper "broken" state → critical alert (test)
- [ ] DECISIONS.md'ye "SPEC-TG-001 done" notu eklenmiş
