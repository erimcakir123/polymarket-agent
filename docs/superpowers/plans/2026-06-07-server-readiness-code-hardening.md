# Sunucu Hazırlığı — Kod Sertleştirme + Telegram Kontrol (Plan 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **⚠️ ÇALIŞAN BOTA DOKUNMA:** Bu plan **ayrı bir git worktree'de** (çalışan botun `Polymarket Agent 2.0` klasörünün DIŞINDA) uygulanır. Evdeki PAPER bot, cutover'a kadar el değmeden çalışır. Bkz. memory: `feedback-running-bot-untouchable`. Worktree: `git worktree add ../pma-server-readiness feature/server-readiness`.

**Goal:** Botu Linux sunucuda sıfır-teknik-borçla çalışmaya hazırlamak: headless-güvenli açılış, düzgün kapanma sinyalleri, ve Telegram'dan `/pause` `/resume` `/status` ile uzaktan kontrol.

**Architecture:** Mevcut katmanlı mimariye uyumlu. Yeni "duraklatma" özelliği: domain'de saf `TradingControl` (paused bayrağı), kalıcı diske JsonStore ile yazılır, `EntryProcessor` okur (yeni giriş açmaz, çıkışlar etkilenmez), `Agent` komut metodlarıyla çevirir, `TelegramCommandPoller` komutları dağıtır, `factory` bağlar. Headless/sinyal düzeltmeleri küçük, test edilebilir yardımcı modüllere konur (main.py ince kalır).

**Tech Stack:** Python 3.12+, pytest, mevcut JsonStore atomik persistence, mevcut TelegramNotifier/CommandPoller, Flask + (yeni) Gunicorn.

**Kapsam dışı (Plan 2 — sunucu runbook):** E4 kalıcı disk, E5 systemd kilit temizliği, E6 systemd restart, E9 build-essential, E10 model verisi kopyalama, Tailscale/ufw/yedekleme. Bunlar ops işidir, TDD değil.

---

### Task 1: E1 — Headless-güvenli LIVE onayı

Sunucuda klavye yok; `src/main.py:38`'deki `input("CONFIRM LIVE")` sonsuza kadar takılır. Onay mantığını test edilebilir saf bir fonksiyona taşı; klavye yoksa `POLYMARKET_CONFIRM_LIVE=1` ortam değişkeniyle onayla.

**Files:**
- Create: `src/orchestration/live_confirmation.py`
- Create: `tests/unit/orchestration/test_live_confirmation.py`
- Modify: `src/main.py:37-40`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_live_confirmation.py
import pytest

from src.orchestration.live_confirmation import require_live_confirmation


def test_tty_with_correct_phrase_passes():
    require_live_confirmation(is_tty=True, env_value=None, prompt_fn=lambda: "CONFIRM LIVE")


def test_tty_with_wrong_phrase_aborts():
    with pytest.raises(SystemExit):
        require_live_confirmation(is_tty=True, env_value=None, prompt_fn=lambda: "no")


def test_headless_with_env_flag_passes():
    require_live_confirmation(is_tty=False, env_value="1", prompt_fn=None)


def test_headless_without_env_flag_aborts():
    with pytest.raises(SystemExit):
        require_live_confirmation(is_tty=False, env_value=None, prompt_fn=None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestration/test_live_confirmation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.orchestration.live_confirmation'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/orchestration/live_confirmation.py
"""LIVE mod onayı — headless (sunucu) güvenli. main.py ince kalsın diye ayrı."""
from __future__ import annotations

import sys
from typing import Callable

_CONFIRM_PHRASE = "CONFIRM LIVE"
_HEADLESS_ENV_TRUE = "1"


def require_live_confirmation(
    is_tty: bool,
    env_value: str | None,
    prompt_fn: Callable[[], str] | None,
) -> None:
    """LIVE mod için onay iste. Onay yoksa SystemExit.

    - Klavye varsa (is_tty): 'CONFIRM LIVE' yazılmalı.
    - Klavye yoksa (sunucu): POLYMARKET_CONFIRM_LIVE=1 ortam değişkeni şart.
    """
    if is_tty:
        if prompt_fn is None or prompt_fn().strip() != _CONFIRM_PHRASE:
            raise SystemExit("LIVE onayı verilmedi. İptal.")
        return
    if env_value != _HEADLESS_ENV_TRUE:
        raise SystemExit(
            "Headless LIVE onayı yok. Sunucuda LIVE için POLYMARKET_CONFIRM_LIVE=1 gerekli."
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/orchestration/test_live_confirmation.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Wire into main.py**

Replace `src/main.py:37-40` (the `if cfg.mode == Mode.LIVE:` block) with:

```python
    if cfg.mode == Mode.LIVE:
        import os  # noqa: PLC0415
        from src.orchestration.live_confirmation import require_live_confirmation  # noqa: PLC0415
        require_live_confirmation(
            is_tty=sys.stdin.isatty(),
            env_value=os.getenv("POLYMARKET_CONFIRM_LIVE"),
            prompt_fn=lambda: input("Type 'CONFIRM LIVE' to proceed: "),
        )
```

- [ ] **Step 6: Run full suite + commit**

Run: `pytest -q`
Expected: all pass

```bash
git add src/orchestration/live_confirmation.py tests/unit/orchestration/test_live_confirmation.py src/main.py
git commit -m "feat(ops): E1 headless-guvenli LIVE onayi (sunucuda input takilmasin)"
```

---

### Task 2: E2 — Düzgün kapanma sinyalleri (SIGTERM/SIGINT)

Agent'ta sinyal işleyici yok; systemd "dur" derken (SIGTERM) bot anında ölür, in-flight state + Telegram bildirimi kaybolur. Mevcut `Agent.request_stop()` graceful yolu var — sinyalleri ona bağla.

**Files:**
- Create: `src/orchestration/signal_handlers.py`
- Create: `tests/unit/orchestration/test_signal_handlers.py`
- Modify: `src/main.py` (agent.run() öncesi handler kur)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_signal_handlers.py
import signal

from src.orchestration.signal_handlers import build_shutdown_handler


def test_handler_invokes_stop_callback():
    calls = []
    handler = build_shutdown_handler(lambda: calls.append("stop"))
    handler(signal.SIGTERM, None)
    assert calls == ["stop"]


def test_handler_swallows_callback_errors():
    def boom():
        raise RuntimeError("x")
    handler = build_shutdown_handler(boom)
    handler(signal.SIGINT, None)  # exception bastırılmalı, raise etmemeli
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestration/test_signal_handlers.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/orchestration/signal_handlers.py
"""SIGTERM/SIGINT → graceful shutdown. systemd stop temiz kapanma yapsın."""
from __future__ import annotations

import logging
import signal
from typing import Callable

logger = logging.getLogger(__name__)


def build_shutdown_handler(stop_callback: Callable[[], None]) -> Callable[[int, object], None]:
    """Sinyal handler üret — stop_callback'i çağırır, hata bastırır."""
    def _handler(signum: int, _frame: object) -> None:
        logger.info("Signal %s alındı — graceful shutdown başlatılıyor", signum)
        try:
            stop_callback()
        except Exception as e:  # noqa: BLE001 — sinyal handler içinde raise etme
            logger.error("Shutdown callback hatası: %s", e)
    return _handler


def install_graceful_shutdown(stop_callback: Callable[[], None]) -> None:
    """SIGTERM + SIGINT'i graceful stop'a bağla."""
    handler = build_shutdown_handler(stop_callback)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/orchestration/test_signal_handlers.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Wire into main.py**

In `src/main.py:main()`, after `agent = build_agent(state)` and before `agent.run()`, add:

```python
    from src.orchestration.signal_handlers import install_graceful_shutdown  # noqa: PLC0415
    install_graceful_shutdown(agent.request_stop)
```

- [ ] **Step 6: Run full suite + commit**

Run: `pytest -q`
Expected: all pass

```bash
git add src/orchestration/signal_handlers.py tests/unit/orchestration/test_signal_handlers.py src/main.py
git commit -m "feat(ops): E2 SIGTERM/SIGINT graceful shutdown (systemd stop temiz kapatsin)"
```

---

### Task 3: TradingControl domain nesnesi (paused bayrağı)

`/pause` için saf, I/O'suz bir domain nesnesi. Sadece durum + serileştirme.

**Files:**
- Create: `src/domain/control/__init__.py` (boş)
- Create: `src/domain/control/trading_control.py`
- Create: `tests/unit/domain/control/test_trading_control.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/domain/control/test_trading_control.py
from src.domain.control.trading_control import TradingControl


def test_default_not_paused():
    assert TradingControl().paused is False


def test_pause_then_resume():
    tc = TradingControl()
    tc.pause()
    assert tc.paused is True
    tc.resume()
    assert tc.paused is False


def test_roundtrip_serialization():
    tc = TradingControl()
    tc.pause()
    restored = TradingControl.from_dict(tc.to_dict())
    assert restored.paused is True


def test_from_dict_missing_key_defaults_false():
    assert TradingControl.from_dict({}).paused is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/control/test_trading_control.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/domain/control/trading_control.py
"""Trading kontrol durumu — /pause ile yeni giriş durdurma. Saf domain, I/O yok."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TradingControl:
    """Yeni giriş açma izni. paused=True iken EntryProcessor yeni trade açmaz.
    Çıkışlar (ExitProcessor) bu bayraktan etkilenmez."""
    paused: bool = False

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def to_dict(self) -> dict:
        return {"paused": self.paused}

    @classmethod
    def from_dict(cls, data: dict) -> "TradingControl":
        return cls(paused=bool(data.get("paused", False)))
```

Create empty `src/domain/control/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/control/test_trading_control.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/domain/control/ tests/unit/domain/control/
git commit -m "feat(control): TradingControl domain nesnesi (paused bayragi, saf)"
```

---

### Task 4: TradingControl kalıcılığı (bootstrap restore + RuntimeState)

Duraklatma yeniden başlatmada korunsun → `data/trading_control.json`. Mevcut breaker/blacklist restore desenini birebir izle.

**Files:**
- Modify: `src/orchestration/startup.py` (RuntimeState + bootstrap + restore helper)
- Create: `tests/unit/orchestration/test_startup_trading_control.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_startup_trading_control.py
from src.config.settings import load_config
from src.infrastructure.persistence.json_store import JsonStore
from src.orchestration.startup import bootstrap


def test_missing_file_defaults_not_paused(tmp_path):
    state = bootstrap(load_config(), logs_dir=tmp_path)
    assert state.trading_control.paused is False


def test_restores_paused_true(tmp_path):
    JsonStore(tmp_path / "trading_control.json").save({"paused": True})
    state = bootstrap(load_config(), logs_dir=tmp_path)
    assert state.trading_control.paused is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestration/test_startup_trading_control.py -v`
Expected: FAIL — `AttributeError: 'RuntimeState' object has no attribute 'trading_control'`

- [ ] **Step 3: Write minimal implementation**

In `src/orchestration/startup.py`:

Add import near other domain imports:
```python
from src.domain.control.trading_control import TradingControl
```

Add constant near `_BLACKLIST_FILE`:
```python
_TRADING_CONTROL_FILE = "data/trading_control.json"  # noqa: F841 — yol referansı (logs_dir-relative kullanılır)
```

Add fields to `RuntimeState` dataclass (after `blacklist_store`):
```python
    trading_control: TradingControl
    trading_control_store: JsonStore
```

In `bootstrap()`, after the blacklist store/restore lines (around line 78-82), add:
```python
    trading_control_store = JsonStore(logs / "trading_control.json")
    trading_control = _restore_trading_control(trading_control_store)
```

Add the field to the `return RuntimeState(...)` call:
```python
        trading_control=trading_control,
        trading_control_store=trading_control_store,
```

Add the restore helper (near `_restore_blacklist`):
```python
def _restore_trading_control(store: JsonStore) -> TradingControl:
    """data/trading_control.json'dan paused durumunu restore et. Yoksa not-paused."""
    data = store.load(default=None)
    if not data:
        return TradingControl()
    return TradingControl.from_dict(data)
```

> NOT: `JsonStore.load` imzasını doğrula — mevcut kullanım `store.load(default=...)`. Eğer imza farklıysa (örn. positional), mevcut `_restore_blacklist` çağrısını birebir taklit et.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/orchestration/test_startup_trading_control.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run full suite (RuntimeState alanı eklendi — kıran yer var mı) + commit**

Run: `pytest -q`
Expected: all pass. Kırılan test varsa: RuntimeState'i pozisyonel kuran bir test olabilir → keyword'e çevir.

```bash
git add src/orchestration/startup.py tests/unit/orchestration/test_startup_trading_control.py
git commit -m "feat(control): TradingControl bootstrap restore + RuntimeState alani"
```

---

### Task 5: EntryProcessor duraklatmaya uysun (yeni giriş açma)

paused iken heavy cycle yeni giriş açmaz; çıkışlar (light cycle / ExitProcessor) etkilenmez.

**Files:**
- Modify: `src/orchestration/entry_processor.py:38` (run_heavy başı)
- Create: `tests/unit/orchestration/test_entry_processor_pause.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_entry_processor_pause.py
from unittest.mock import MagicMock

from src.domain.control.trading_control import TradingControl
from src.orchestration.entry_processor import EntryProcessor


def _deps(paused: bool):
    deps = MagicMock()
    deps.state.trading_control = TradingControl(paused=paused)
    deps.state.config.mode.value = "paper"
    return deps


def test_paused_skips_scan():
    deps = _deps(paused=True)
    EntryProcessor(deps).run_heavy()
    deps.scanner.scan.assert_not_called()


def test_not_paused_runs_scan():
    deps = _deps(paused=False)
    deps.scanner.scan.return_value = []
    deps.mlb_submarket_engine = None
    EntryProcessor(deps).run_heavy()
    deps.scanner.scan.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestration/test_entry_processor_pause.py -v`
Expected: FAIL — `test_paused_skips_scan` başarısız (scan çağrılıyor)

- [ ] **Step 3: Write minimal implementation**

In `src/orchestration/entry_processor.py`, at the very start of `run_heavy()` (right after the docstring, before `mode = ...`):

```python
        if self.deps.state.trading_control.paused:
            logger.info("Trading PAUSED (Telegram /pause) — yeni giriş açılmıyor")
            return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/orchestration/test_entry_processor_pause.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/entry_processor.py tests/unit/orchestration/test_entry_processor_pause.py
git commit -m "feat(control): EntryProcessor paused iken yeni giris acmaz (cikislar etkilenmez)"
```

---

### Task 6: Agent pause/resume/status metodları

Komutların çağıracağı metodlar. pause/resume bayrağı çevirir + kalıcı diske yazar + Telegram'a bildirir; status özet metni döner.

**Files:**
- Modify: `src/orchestration/agent.py` (yeni metodlar)
- Create: `tests/unit/orchestration/test_agent_control.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_agent_control.py
from unittest.mock import MagicMock

from src.domain.control.trading_control import TradingControl
from src.orchestration.agent import Agent, AgentDeps


def _agent():
    deps = MagicMock(spec=AgentDeps)
    deps.state.trading_control = TradingControl()
    deps.price_feed = None
    deps.notifier = MagicMock()
    deps.state.config.mode.value = "paper"
    deps.state.portfolio.count.return_value = 3
    deps.state.portfolio.realized_pnl = 12.5
    deps.state.portfolio.bankroll = 980.0
    # Agent.__init__ config.telegram.alert erişir → MagicMock güvenli
    return Agent(deps), deps


def test_request_pause_sets_flag_and_persists():
    agent, deps = _agent()
    agent.request_pause()
    assert deps.state.trading_control.paused is True
    deps.state.trading_control_store.save.assert_called_once()


def test_request_resume_clears_flag_and_persists():
    agent, deps = _agent()
    deps.state.trading_control.pause()
    agent.request_resume()
    assert deps.state.trading_control.paused is False
    deps.state.trading_control_store.save.assert_called_once()


def test_status_summary_contains_key_fields():
    agent, deps = _agent()
    text = agent.status_summary()
    assert "paper" in text.lower()
    assert "3" in text          # pozisyon sayısı
    assert "12.5" in text       # realized pnl
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestration/test_agent_control.py -v`
Expected: FAIL — `AttributeError: 'Agent' object has no attribute 'request_pause'`

- [ ] **Step 3: Write minimal implementation**

In `src/orchestration/agent.py`, add three methods after `request_stop()` (around line 116):

```python
    def request_pause(self) -> None:
        """Telegram /pause — yeni giriş açmayı durdur (kalıcı). Çıkışlar sürer."""
        self.deps.state.trading_control.pause()
        self.deps.state.trading_control_store.save(self.deps.state.trading_control.to_dict())
        logger.info("Trading PAUSED via Telegram")

    def request_resume(self) -> None:
        """Telegram /resume — yeni girişe devam (kalıcı)."""
        self.deps.state.trading_control.resume()
        self.deps.state.trading_control_store.save(self.deps.state.trading_control.to_dict())
        logger.info("Trading RESUMED via Telegram")

    def status_summary(self) -> str:
        """Telegram /status — kısa durum metni."""
        p = self.deps.state.portfolio
        paused = self.deps.state.trading_control.paused
        return (
            f"📊 <b>Durum</b>\n"
            f"Mod: {self.deps.state.config.mode.value}\n"
            f"Açık pozisyon: {p.count()}\n"
            f"Realized PnL: ${p.realized_pnl:.2f}\n"
            f"Bankroll: ${p.bankroll:.2f}\n"
            f"Trading: {'⏸ DURAKLATILDI' if paused else '▶ aktif'}"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/orchestration/test_agent_control.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/agent.py tests/unit/orchestration/test_agent_control.py
git commit -m "feat(control): Agent request_pause/resume/status_summary (kalici + telegram)"
```

---

### Task 7: TelegramCommandPoller — /pause /resume /status

Mevcut /stop desenini izleyerek üç komut ekle. /status callback bir metin döner → yanıt olarak gönderilir.

**Files:**
- Modify: `src/infrastructure/telegram/command_poller.py`
- Modify: `tests/unit/infrastructure/telegram/test_command_poller.py` (varsa; yoksa create)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infrastructure/telegram/test_command_poller.py  (ekle veya oluştur)
from src.infrastructure.telegram.command_poller import TelegramCommandPoller


def _poller(calls):
    return TelegramCommandPoller(
        bot_token="t", chat_id="42",
        on_stop=lambda: calls.append("stop"),
        on_pause=lambda: calls.append("pause"),
        on_resume=lambda: calls.append("resume"),
        on_status=lambda: "STATUS-TEXT",
        http_get=lambda *a, **k: None,
        http_post=lambda *a, **k: None,
    )


def _update(text):
    return {"update_id": 1, "message": {"text": text, "chat": {"id": 42}}}


def test_pause_command_dispatches():
    calls = []
    _poller(calls)._handle(_update("/pause"))
    assert calls == ["pause"]


def test_resume_command_dispatches():
    calls = []
    _poller(calls)._handle(_update("/resume"))
    assert calls == ["resume"]


def test_status_command_replies_with_text():
    sent = {}
    p = _poller([])
    p._http_post = lambda url, json, timeout: sent.update(json)
    p._handle(_update("/status"))
    assert sent["text"] == "STATUS-TEXT"


def test_wrong_chat_ignored():
    calls = []
    p = _poller(calls)
    p._handle({"update_id": 2, "message": {"text": "/pause", "chat": {"id": 999}}})
    assert calls == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/telegram/test_command_poller.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'on_pause'`

- [ ] **Step 3: Write minimal implementation**

In `src/infrastructure/telegram/command_poller.py`, update `__init__` signature and body:

```python
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        on_stop: Callable[[], None],
        on_pause: Callable[[], None] | None = None,
        on_resume: Callable[[], None] | None = None,
        on_status: Callable[[], str] | None = None,
        http_get: Callable[..., Any] | None = None,
        http_post: Callable[..., Any] | None = None,
    ) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._on_stop = on_stop
        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_status = on_status
        self._http_get = http_get or requests.get
        self._http_post = http_post or requests.post
        self._offset: int = 0
        self._running = False
        self._thread: threading.Thread | None = None
```

Add setters (after `set_on_stop`):
```python
    def set_handlers(
        self,
        on_pause: Callable[[], None],
        on_resume: Callable[[], None],
        on_status: Callable[[], str],
    ) -> None:
        """Factory wiring: agent metodlarını bağla."""
        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_status = on_status
```

Replace the `_handle` command dispatch block (the `if text == "/stop":` section) with:
```python
        if text == "/stop":
            logger.info("Telegram /stop received from chat %s", chat_id)
            self._send_reply("Bot durduruluyor...")
            self._on_stop()
        elif text == "/pause" and self._on_pause is not None:
            logger.info("Telegram /pause received")
            self._on_pause()
            self._send_reply("⏸ Yeni giriş durduruldu (çıkışlar sürüyor).")
        elif text == "/resume" and self._on_resume is not None:
            logger.info("Telegram /resume received")
            self._on_resume()
            self._send_reply("▶ Yeni girişe devam.")
        elif text == "/status" and self._on_status is not None:
            self._send_reply(self._on_status())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/telegram/test_command_poller.py -v`
Expected: PASS (4 passed). Mevcut /stop testleri de geçmeli (imza geriye-uyumlu: yeni parametreler opsiyonel).

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/telegram/command_poller.py tests/unit/infrastructure/telegram/test_command_poller.py
git commit -m "feat(telegram): /pause /resume /status komutlari (stop deseni)"
```

---

### Task 8: Factory — komutları agent'a bağla

Mevcut `set_on_stop` wiring'inin yanına pause/resume/status bağla.

**Files:**
- Modify: `src/orchestration/factory.py:322-323`
- Create: `tests/unit/orchestration/test_factory_command_wiring.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_factory_command_wiring.py
from unittest.mock import MagicMock

from src.infrastructure.telegram.command_poller import TelegramCommandPoller


def test_set_handlers_binds_callbacks():
    poller = TelegramCommandPoller(bot_token="t", chat_id="1", on_stop=lambda: None)
    agent = MagicMock()
    # factory'nin yaptığı bağlama (Task 8'de eklenen satırlar) bu davranışı üretmeli:
    poller.set_handlers(agent.request_pause, agent.request_resume, agent.status_summary)
    poller._handle({"update_id": 1, "message": {"text": "/pause", "chat": {"id": 1}}})
    poller._http_post = lambda *a, **k: None
    agent.request_pause.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestration/test_factory_command_wiring.py -v`
Expected: PASS aslında (set_handlers Task 7'de eklendi). Bu test wiring sözleşmesini kilitler. Eğer Task 7 atlandıysa FAIL.

> NOT: Bu test factory'nin İÇ davranışını değil, poller sözleşmesini doğrular (factory saf wiring; ünite testi zor). Asıl wiring Step 3'te eklenir, smoke ile doğrulanır.

- [ ] **Step 3: Add wiring in factory.py**

In `src/orchestration/factory.py`, replace lines 322-323 (`if command_poller is not None: command_poller.set_on_stop(agent.request_stop)`) with:

```python
    if command_poller is not None:
        command_poller.set_on_stop(agent.request_stop)
        command_poller.set_handlers(
            on_pause=agent.request_pause,
            on_resume=agent.request_resume,
            on_status=agent.status_summary,
        )
```

- [ ] **Step 4: Smoke test — build_agent çalışıyor mu**

Run: `python -c "from dotenv import load_dotenv; load_dotenv(); from src.config.settings import load_config; from src.orchestration.startup import bootstrap; from src.orchestration.factory import build_agent; build_agent(bootstrap(load_config())); print('OK')"`
Expected: `OK` (import + wiring hatasız)

- [ ] **Step 5: Run full suite + commit**

Run: `pytest -q`
Expected: all pass

```bash
git add src/orchestration/factory.py tests/unit/orchestration/test_factory_command_wiring.py
git commit -m "feat(telegram): factory pause/resume/status'u agent'a bagla"
```

---

### Task 9: E3 — Gunicorn WSGI giriş noktası (pano üretim sunucusu)

Flask dev server yerine Gunicorn. Gunicorn'un import edeceği `app` nesnesi gerekiyor.

**Files:**
- Create: `src/presentation/dashboard/wsgi.py`
- Create: `tests/unit/presentation/dashboard/test_wsgi.py`
- Modify: `requirements.txt` (gunicorn ekle)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/presentation/dashboard/test_wsgi.py
def test_wsgi_app_is_flask():
    from flask import Flask
    from src.presentation.dashboard.wsgi import app
    assert isinstance(app, Flask)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/presentation/dashboard/test_wsgi.py -v`
Expected: FAIL — `ModuleNotFoundError: ...wsgi`

- [ ] **Step 3: Write minimal implementation**

```python
# src/presentation/dashboard/wsgi.py
"""Gunicorn giriş noktası: `gunicorn src.presentation.dashboard.wsgi:app`.

Flask dev server (app.run) yerine üretim WSGI sunucusu kullanılır (E3).
"""
from __future__ import annotations

from src.presentation.dashboard.app import create_app

app = create_app()
```

Add to `requirements.txt`:
```
gunicorn>=21.2.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/presentation/dashboard/test_wsgi.py -v`
Expected: PASS

> NOT: Gunicorn Windows'ta çalışmaz (Linux/sunucu içindir) — bu yüzden sadece import-edilebilir `app` test edilir; gunicorn'u çalıştırma testi Plan 2'de (sunucuda) yapılır. Yerelde pano hâlâ `app.run` ile çalışmaya devam eder (mevcut `app.py:main()` korunur).

- [ ] **Step 5: Commit**

```bash
git add src/presentation/dashboard/wsgi.py tests/unit/presentation/dashboard/test_wsgi.py requirements.txt
git commit -m "feat(dashboard): E3 Gunicorn WSGI giris noktasi (uretim sunucusu)"
```

---

### Task 10: E7 — scripts/basket_*.py sabit Windows yollarını parametreleştir

Tanı (diagnostic) script'lerindeki `c:/Users/...` sabit yolları Linux'ta patlar. Repo köküne göre göreli yap.

**Files:**
- Modify: `scripts/basket_all_history.py:16`
- Modify: `scripts/basket_full_audit.py:15`
- Modify: `scripts/basket_vs_tennis_quality.py:128-130, 148`

- [ ] **Step 1: Tespit — mevcut sabit yolları gör**

Run: `grep -rn "c:/Users\|C:\\\\Users" scripts/basket_all_history.py scripts/basket_full_audit.py scripts/basket_vs_tennis_quality.py`
Expected: 5 sabit yol satırı listelenir.

- [ ] **Step 2: basket_all_history.py + basket_full_audit.py düzelt**

`scripts/basket_all_history.py:16` (`ana_audit = r"c:/Users/.../logs/audit"`) →
```python
from pathlib import Path
ana_audit = str(Path(__file__).resolve().parent.parent / "logs" / "audit")
```
`scripts/basket_full_audit.py:15` için aynı dönüşüm.

- [ ] **Step 3: basket_vs_tennis_quality.py düzelt**

`scripts/basket_vs_tennis_quality.py:128-130, 148`'deki `r"c:/Users/.../tennis-lab/logs/audit/..."` yolları → repo dışı `tennis-lab` referansı olduğu için ortam değişkeniyle parametreleştir:
```python
import os
from pathlib import Path
_TENNIS_LAB = Path(os.getenv("TENNIS_LAB_DIR", str(Path(__file__).resolve().parent.parent.parent / "tennis-lab")))
# kullanım: str(_TENNIS_LAB / "logs" / "audit" / "...")
```

- [ ] **Step 4: Doğrula — sabit Windows yolu kalmadı**

Run: `grep -rn "c:/Users\|C:\\\\Users" scripts/basket_all_history.py scripts/basket_full_audit.py scripts/basket_vs_tennis_quality.py`
Expected: hiç eşleşme yok (boş çıktı)

- [ ] **Step 5: Commit**

```bash
git add scripts/basket_all_history.py scripts/basket_full_audit.py scripts/basket_vs_tennis_quality.py
git commit -m "fix(scripts): E7 sabit Windows yollarini repo-goreli yap (Linux uyumu)"
```

---

## Plan Tamamlanınca — Doğrulama

- [ ] `pytest -q` → tümü geçer
- [ ] `git -C ../pma-server-readiness log --oneline` → 10 task commit'i görünür
- [ ] Çalışan ev botuna **dokunulmadı** (işler ayrı worktree'de yapıldı)
- [ ] Sonraki: **Plan 2 — Sunucu Kurulum Runbook** (Hetzner + Tailscale + systemd + deploy.sh + cutover)

## Edge Case Kapsam Kontrolü (spec Bölüm 5/11 ↔ plan)

- E1 → Task 1 ✓ · E2 → Task 2 ✓ · E3 → Task 9 ✓ · E7 → Task 10 ✓
- Telegram /pause /resume /status → Task 3-8 ✓
- E4, E5, E6, E8, E9, E10 → Plan 2 (sunucu runbook — ops, TDD değil) ⏭
