# Dashboard: Cycle Aşamaları + Pozisyon Kartı Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard'da Hard cycle'ın 4 aşamasını real-time gösteren etiket + idle MM:SS countdown; Light cycle için Online/Offline; pozisyon kartında takım ismi, countdown (mavi pill), renk kodlu A/B/C conf rozeti ve odds.

**Architecture:** `agent.py` heavy cycle içinde `_write_bot_status_stage()` ile bot_status.json'ı aşama geçişlerinde günceller. `CycleManager.next_heavy_at_iso()` bir sonraki heavy zamanını ISO olarak verir. Frontend `/api/status` endpoint'inden yeni schema'yı okur, `dashboard.js::RENDER.status()` stage→etiket mapping yapar, idle state'te `setInterval(1s)` ile MM:SS countdown günceller. Pozisyon kartı `feed.js::_activeCard` yeniden yazılır — yeni helper'lar (`_teamsTitle`, `_confPill`, `_countdownPill`).

**Tech Stack:** Python 3.12 + Pydantic (backend), Flask (routes), vanilla JS + CSS (frontend), pytest (test).

**Önemli:** Uygulama sırasında bot'u her task sonunda restart etmek **gerekli değil**. E2E doğrulama Task 10'da bot restart ile yapılır. Unit test'ler mock'larla geçer.

---

## File Structure

**Backend (oluşturulacak/değişecek):**
- Modify: `src/orchestration/cycle_manager.py` — `next_heavy_at_iso()` helper
- Modify: `src/orchestration/agent.py` — `_write_bot_status_stage()` + heavy cycle içinde 4 çağrı; mevcut `_write_bot_status` yeni şemayla değişir
- Modify: `src/presentation/dashboard/routes.py` — `/api/status` yeni alanlar

**Frontend (değişecek):**
- Modify: `src/presentation/dashboard/static/js/dashboard.js` — `RENDER.status()` yeniden + `_startIdleCountdown()` interval
- Modify: `src/presentation/dashboard/static/js/feed.js` — `_activeCard`, 3 yeni helper
- Modify: `src/presentation/dashboard/static/css/feed.css` — conf/countdown pill stilleri, layout gap'leri

**Testler (oluşturulacak):**
- Create: `tests/unit/orchestration/test_cycle_manager_next_heavy.py`
- Create: `tests/unit/orchestration/test_agent_stages.py`
- Create: `tests/unit/presentation/__init__.py`
- Create: `tests/unit/presentation/dashboard/__init__.py`
- Create: `tests/unit/presentation/dashboard/test_routes_status.py`

---

## Task 1: CycleManager.next_heavy_at_iso() helper

**Files:**
- Modify: `src/orchestration/cycle_manager.py`
- Test: `tests/unit/orchestration/test_cycle_manager_next_heavy.py`

### ARCH_GUARD self-check (dosyanın başında)
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni (orchestration içi), ✓ magic number yok (interval config'ten), ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor ilgisiz."

- [ ] **Step 1: Failing testi yaz**

Oluştur: `tests/unit/orchestration/test_cycle_manager_next_heavy.py`

```python
"""CycleManager.next_heavy_at_iso — bir sonraki heavy cycle'ın ISO timestamp'i."""
from __future__ import annotations

from datetime import datetime, timezone

from src.config.settings import CycleConfig
from src.orchestration.cycle_manager import CycleManager


def test_next_heavy_at_iso_cold_start_returns_now():
    """İlk heavy hiç çalışmamışsa bir sonraki heavy = şimdi (cold start bekliyor)."""
    fixed_now_ts = 1000.0
    fixed_utc = datetime(2026, 4, 15, 15, 0, 0, tzinfo=timezone.utc)
    mgr = CycleManager(
        CycleConfig(),
        now_fn=lambda: fixed_now_ts,
        utc_now_fn=lambda: fixed_utc,
    )
    # _last_heavy_ts = 0 → cold start
    result = mgr.next_heavy_at_iso()
    assert result == fixed_utc.isoformat()


def test_next_heavy_at_iso_daytime_uses_30min_interval():
    """Gündüzde (UTC hour not in night_hours) last_heavy + 30dk."""
    fixed_now_ts = 10_000.0
    fixed_utc = datetime(2026, 4, 15, 15, 0, 0, tzinfo=timezone.utc)
    mgr = CycleManager(
        CycleConfig(),
        now_fn=lambda: fixed_now_ts,
        utc_now_fn=lambda: fixed_utc,
    )
    mgr._last_heavy_ts = fixed_now_ts
    result = mgr.next_heavy_at_iso()
    # Beklenen: now + 30*60 saniye, ISO formatında
    expected = datetime.fromtimestamp(fixed_now_ts + 1800, tz=timezone.utc).isoformat()
    assert result == expected


def test_next_heavy_at_iso_nighttime_uses_60min_interval():
    """Gece saatlerinde (UTC 08-13) last_heavy + 60dk."""
    fixed_now_ts = 10_000.0
    fixed_utc = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)  # night
    mgr = CycleManager(
        CycleConfig(),
        now_fn=lambda: fixed_now_ts,
        utc_now_fn=lambda: fixed_utc,
    )
    mgr._last_heavy_ts = fixed_now_ts
    result = mgr.next_heavy_at_iso()
    expected = datetime.fromtimestamp(fixed_now_ts + 3600, tz=timezone.utc).isoformat()
    assert result == expected
```

- [ ] **Step 2: Test çalıştır, fail bekle**

Run: `pytest tests/unit/orchestration/test_cycle_manager_next_heavy.py -v`
Expected: FAIL — `AttributeError: 'CycleManager' object has no attribute 'next_heavy_at_iso'`

- [ ] **Step 3: Minimal implementation**

`src/orchestration/cycle_manager.py` dosyasında mevcut `sleep_seconds()` altına ekle (92. satırdan sonra):

```python
    def next_heavy_at_iso(self) -> str:
        """Bir sonraki heavy cycle'ın ISO timestamp'i (UTC).

        Cold start (_last_heavy_ts=0) ise = şimdi. Aksi halde = last_heavy + current interval.
        Dashboard idle countdown için kullanılır.
        """
        if self._last_heavy_ts == 0.0:
            return self._utc_now().isoformat()
        next_ts = self._last_heavy_ts + self._current_heavy_interval_sec()
        return datetime.fromtimestamp(next_ts, tz=timezone.utc).isoformat()
```

- [ ] **Step 4: Test çalıştır, pass bekle**

Run: `pytest tests/unit/orchestration/test_cycle_manager_next_heavy.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/cycle_manager.py tests/unit/orchestration/test_cycle_manager_next_heavy.py
git commit -m "feat(cycle_manager): add next_heavy_at_iso helper for dashboard idle countdown"
```

---

## Task 2: Agent stage snapshot — schema + helper

**Files:**
- Modify: `src/orchestration/agent.py` (mevcut `_write_bot_status`)
- Test: `tests/unit/orchestration/test_agent_stages.py`

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY (tek helper), ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni (orchestration), ✓ magic number yok (stage string'leri const değil string literal ama sınırlı enum-benzeri), ✓ utils yok, ✓ sessiz hata yok (OSError log + continue), ✓ P(YES) ilgisiz."

- [ ] **Step 1: Failing testi yaz**

Oluştur: `tests/unit/orchestration/test_agent_stages.py`

```python
"""Agent cycle stage snapshot yazımı — bot_status.json şeması."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config.settings import AppConfig
from src.infrastructure.persistence.json_store import JsonStore
from src.orchestration.agent import Agent, AgentDeps
from src.orchestration.cycle_manager import CycleTick


def _make_deps(tmp_path: Path) -> AgentDeps:
    """Minimal mock'lu AgentDeps."""
    status_store = JsonStore(str(tmp_path / "bot_status.json"))
    state = MagicMock()
    state.config = AppConfig()
    state.portfolio.positions = {}
    state.portfolio.count.return_value = 0
    cycle_manager = MagicMock()
    cycle_manager.next_heavy_at_iso.return_value = "2026-04-15T15:30:00+00:00"
    return AgentDeps(
        state=state,
        scanner=MagicMock(),
        cycle_manager=cycle_manager,
        executor=MagicMock(),
        odds_client=MagicMock(),
        trade_logger=MagicMock(),
        gate=MagicMock(),
        cooldown=MagicMock(),
        equity_logger=MagicMock(),
        skipped_logger=MagicMock(),
        eligible_snapshot=MagicMock(),
        bot_status_store=status_store,
        price_feed=None,
    )


def test_write_bot_status_stage_writes_expected_schema(tmp_path):
    """Stage yazımı — schema: mode, cycle, stage, stage_at, next_heavy_at, light_alive."""
    deps = _make_deps(tmp_path)
    agent = Agent(deps)
    agent._write_bot_status_stage(cycle="heavy", stage="scanning")

    snap = deps.bot_status_store.load()
    assert snap["mode"] == "dry_run"
    assert snap["cycle"] == "heavy"
    assert snap["stage"] == "scanning"
    assert "stage_at" in snap and snap["stage_at"]  # ISO string
    assert snap["next_heavy_at"] == "2026-04-15T15:30:00+00:00"
    assert snap["light_alive"] is True


def test_write_bot_status_stage_idle_writes_idle_stage(tmp_path):
    """Heavy sonrası idle snapshot — stage='idle', next_heavy_at mevcut."""
    deps = _make_deps(tmp_path)
    agent = Agent(deps)
    agent._write_bot_status_stage(cycle="heavy", stage="idle")

    snap = deps.bot_status_store.load()
    assert snap["stage"] == "idle"
    assert snap["cycle"] == "heavy"


def test_write_bot_status_stage_swallows_oserror(tmp_path, caplog):
    """OSError → logger.warning, exception raise edilmez."""
    deps = _make_deps(tmp_path)
    deps.bot_status_store = MagicMock()
    deps.bot_status_store.save.side_effect = OSError("disk full")
    agent = Agent(deps)
    agent._write_bot_status_stage(cycle="heavy", stage="scanning")  # raise etmemeli
    # warning log atılmış olmalı (mevcut davranış)
```

- [ ] **Step 2: Test çalıştır, fail bekle**

Run: `pytest tests/unit/orchestration/test_agent_stages.py -v`
Expected: FAIL — `AttributeError: 'Agent' object has no attribute '_write_bot_status_stage'`

- [ ] **Step 3: Implementation — yeni helper ekle + eski `_write_bot_status`'u değiştir**

`src/orchestration/agent.py` dosyasında mevcut `_write_bot_status` metodunu (372-383 satırları) şu kodla değiştir:

```python
    def _write_bot_status_stage(self, cycle: str, stage: str) -> None:
        """Dashboard için bot aşama snapshot'ı.

        cycle: 'heavy' | 'light' (hangi cycle türünde)
        stage: 'scanning' | 'analyzing' | 'executing' | 'idle' (hard cycle aşaması;
               light için stage='light' kullanılır — dashboard Online/Offline'a çevirir)
        """
        try:
            self.deps.bot_status_store.save({
                "mode": self.deps.state.config.mode.value,
                "cycle": cycle,
                "stage": stage,
                "stage_at": datetime.now(timezone.utc).isoformat(),
                "next_heavy_at": self.deps.cycle_manager.next_heavy_at_iso(),
                "light_alive": True,
            })
        except OSError as e:
            logger.warning("Bot status stage write failed: %s", e)

    def _write_bot_status(self, tick: CycleTick) -> None:
        """Cycle sonu snapshot — light ise stage='light', heavy ise stage='idle'."""
        cycle = "heavy" if tick.run_heavy else "light"
        stage = "idle" if tick.run_heavy else "light"
        self._write_bot_status_stage(cycle=cycle, stage=stage)
```

- [ ] **Step 4: Test çalıştır, pass bekle**

Run: `pytest tests/unit/orchestration/test_agent_stages.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/agent.py tests/unit/orchestration/test_agent_stages.py
git commit -m "feat(agent): extend bot_status schema with cycle stage snapshots"
```

---

## Task 3: Heavy cycle içinde stage yazımları

**Files:**
- Modify: `src/orchestration/agent.py` (`_run_heavy`, `_process_markets`, `_execute_entry`)

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY (tek helper çağrılır), ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni (orchestration içi), ✓ magic number yok, ✓ utils yok, ✓ sessiz hata yok, ✓ P(YES) ilgisiz."

- [ ] **Step 1: Failing testi yaz — heavy cycle içinde stage snapshot'ları yazıldığını doğrula**

`tests/unit/orchestration/test_agent_stages.py` dosyasına aşağıdaki testi ekle:

```python
def test_run_heavy_writes_scanning_then_analyzing_then_executing_then_idle(tmp_path):
    """_run_heavy tamamlanınca bot_status_store 4 kez save edilmiş olmalı."""
    deps = _make_deps(tmp_path)
    deps.bot_status_store = MagicMock()
    deps.scanner.scan.return_value = []  # Boş → analyzing'e düşer, executing yazılmaz

    agent = Agent(deps)
    agent._run_heavy(prefer_eligible_queue=False)

    stages = [call.args[0]["stage"] for call in deps.bot_status_store.save.call_args_list]
    # Boş market: scanning → analyzing yazılır; executing signal yoksa yazılmaz; idle son
    assert "scanning" in stages
    assert "analyzing" in stages
    assert "idle" in stages
    assert "executing" not in stages  # signal yok


def test_run_heavy_writes_executing_when_signal_exists(tmp_path):
    """Signal üretilmişse executing stage yazılır."""
    from src.models.market import MarketData
    from src.models.signal import Signal
    from src.models.enums import Direction, EntryReason

    deps = _make_deps(tmp_path)
    deps.bot_status_store = MagicMock()
    market = MarketData(
        condition_id="cid", yes_token_id="y", no_token_id="n",
        question="A vs B", slug="a-vs-b", sport_tag="mlb",
        yes_price=0.5, no_price=0.5, liquidity=1000.0, volume_24h=100.0,
        match_start_iso="2026-04-15T23:00:00Z", end_date_iso=None,
        event_id="e1", closed=False, resolved=False, accepting_orders=True,
    )
    signal = Signal(
        condition_id="cid", direction=Direction.BUY_YES,
        anchor_probability=0.6, market_price=0.5, edge=0.1,
        confidence="A", size_usdc=50.0, entry_reason=EntryReason.CONSENSUS,
        bookmaker_prob=0.6, num_bookmakers=3, has_sharp=True,
        sport_tag="mlb", event_id="e1",
    )
    gate_result = MagicMock()
    gate_result.condition_id = "cid"
    gate_result.signal = signal
    gate_result.skipped_reason = None
    deps.scanner.scan.return_value = [market]
    deps.gate.run.return_value = [gate_result]
    deps.gate.config.max_exposure_pct = 0.30
    deps.state.portfolio.positions = {}
    deps.state.portfolio.bankroll = 1000.0
    deps.state.portfolio.add_position.return_value = True
    deps.executor.place_order.return_value = {"status": "simulated", "price": 0.5}

    agent = Agent(deps)
    agent._run_heavy(prefer_eligible_queue=False)

    stages = [call.args[0]["stage"] for call in deps.bot_status_store.save.call_args_list]
    assert "executing" in stages
```

- [ ] **Step 2: Test çalıştır, fail bekle**

Run: `pytest tests/unit/orchestration/test_agent_stages.py -v`
Expected: FAIL — `assert "scanning" in stages` (şu anda hiçbir stage yazılmıyor)

- [ ] **Step 3: Implementation — `_run_heavy` ve `_process_markets` içine stage çağrıları ekle**

`src/orchestration/agent.py` dosyasında:

(A) `_run_heavy` metodunu (mevcut 136-149 satırları) şu kodla değiştir:

```python
    def _run_heavy(self, prefer_eligible_queue: bool = False) -> None:
        """Scan → enrich → gate → execute. Exit-triggered'da queue önce."""
        self._write_bot_status_stage(cycle="heavy", stage="scanning")
        if prefer_eligible_queue:
            queued = self.deps.scanner.drain_eligible()
            if queued:
                logger.info("Heavy (exit-triggered): %d eligible queue entries first", len(queued))
                self._process_markets(queued)
        else:
            markets = self.deps.scanner.scan()
            self._process_markets(markets)

        # Dashboard snapshot'ları (presentation ayrı process olduğu için disk üzerinden)
        self._dump_eligible_queue()
        self._log_equity_snapshot()
        self._write_bot_status_stage(cycle="heavy", stage="idle")
```

(B) `_process_markets` metoduna stage çağrıları ekle. Mevcut 151-185 satırlarını şu kodla değiştir:

```python
    def _process_markets(self, markets: list[MarketData]) -> None:
        """Gate'ten geçir, onaylı signal'leri execute et.

        Gate'de yapılan exposure check statik (300 market tek pass'te değerlendirilir,
        portfolio o an boş gibi görünür). Bu loop'ta execution öncesi TEKRAR kontrol
        edilir — çünkü her add_position sonrası portfolio değişiyor ve cap aşılabilir.
        """
        self._write_bot_status_stage(cycle="heavy", stage="analyzing")
        results = self.deps.gate.run(markets)
        by_cid = {m.condition_id: m for m in markets}
        max_exposure_pct = self.deps.gate.config.max_exposure_pct

        executing_written = False
        for r in results:
            market = by_cid.get(r.condition_id)
            if r.signal is None:
                if market is not None:
                    self._log_skip(market, r.skipped_reason)
                    if r.skipped_reason in ("max_positions_reached", "exposure_cap_reached"):
                        self.deps.scanner.push_eligible(market)
                continue

            if market is None:
                continue

            # Execution-time exposure re-check (gate-time statik check yetersiz)
            if exceeds_exposure_limit(
                self.deps.state.portfolio.positions,
                r.signal.size_usdc,
                self.deps.state.portfolio.bankroll,
                max_exposure_pct,
            ):
                self._log_skip(market, "exposure_cap_reached")
                self.deps.scanner.push_eligible(market)
                continue

            if not executing_written:
                self._write_bot_status_stage(cycle="heavy", stage="executing")
                executing_written = True
            self._execute_entry(market, r.signal)
```

- [ ] **Step 4: Test çalıştır, pass bekle**

Run: `pytest tests/unit/orchestration/test_agent_stages.py -v`
Expected: PASS (5 tests total)

- [ ] **Step 5: Regression — mevcut agent test'leri hala geçiyor mu**

Run: `pytest tests/unit/ -q`
Expected: tüm testler PASS. Kırılan olursa self-review.

- [ ] **Step 6: Commit**

```bash
git add src/orchestration/agent.py tests/unit/orchestration/test_agent_stages.py
git commit -m "feat(agent): emit stage snapshots (scanning/analyzing/executing/idle) during heavy cycle"
```

---

## Task 4: /api/status endpoint genişletme

**Files:**
- Modify: `src/presentation/dashboard/routes.py`
- Test: `tests/unit/presentation/dashboard/test_routes_status.py`
- Create: `tests/unit/presentation/__init__.py` (boş)
- Create: `tests/unit/presentation/dashboard/__init__.py` (boş)

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok (presentation sadece readers çağırır), ✓ katman düzeni (presentation izole), ✓ magic number yok, ✓ utils yok, ✓ sessiz hata yok, ✓ P(YES) ilgisiz."

- [ ] **Step 1: __init__.py dosyalarını oluştur**

`tests/unit/presentation/__init__.py` — boş dosya
`tests/unit/presentation/dashboard/__init__.py` — boş dosya

- [ ] **Step 2: Failing testi yaz**

Oluştur: `tests/unit/presentation/dashboard/test_routes_status.py`

```python
"""/api/status endpoint şema testleri."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from flask import Flask

from src.config.settings import AppConfig
from src.presentation.dashboard.routes import register_routes


@pytest.fixture
def client(tmp_path: Path):
    """bot_status.json ile birlikte flask test client."""
    (tmp_path / "agent.pid").write_text("99999", encoding="utf-8")  # alive=false'a düşecek
    app = Flask(__name__)
    config = AppConfig()
    register_routes(app, config, tmp_path)
    return app.test_client(), tmp_path


def test_api_status_returns_new_fields_when_bot_status_present(client):
    c, logs_dir = client
    (logs_dir / "bot_status.json").write_text(json.dumps({
        "mode": "dry_run",
        "cycle": "heavy",
        "stage": "scanning",
        "stage_at": "2026-04-15T12:00:00+00:00",
        "next_heavy_at": "2026-04-15T12:30:00+00:00",
        "light_alive": True,
    }), encoding="utf-8")

    r = c.get("/api/status")
    data = r.get_json()
    assert data["cycle"] == "heavy"
    assert data["stage"] == "scanning"
    assert data["stage_at"] == "2026-04-15T12:00:00+00:00"
    assert data["next_heavy_at"] == "2026-04-15T12:30:00+00:00"
    assert data["light_alive"] is True


def test_api_status_returns_nulls_when_bot_status_missing(client):
    c, _ = client
    r = c.get("/api/status")
    data = r.get_json()
    assert data["cycle"] is None
    assert data["stage"] is None
    assert data["stage_at"] is None
    assert data["next_heavy_at"] is None
    assert data["light_alive"] is False
```

- [ ] **Step 3: Test çalıştır, fail bekle**

Run: `pytest tests/unit/presentation/dashboard/test_routes_status.py -v`
Expected: FAIL — assertion error (eski şema `last_cycle`, `last_cycle_at`, `reason` döndürüyor).

- [ ] **Step 4: Implementation — routes.py güncelle**

`src/presentation/dashboard/routes.py` dosyasında mevcut `api_status()` handler'ını (32-41 satırları) şu kodla değiştir:

```python
    @app.route("/api/status")
    def api_status():
        status = readers.read_bot_status(logs_dir)
        return jsonify({
            "mode": config.mode.value,
            "bot_alive": readers.bot_is_alive(logs_dir),
            "cycle": status.get("cycle"),
            "stage": status.get("stage"),
            "stage_at": status.get("stage_at"),
            "next_heavy_at": status.get("next_heavy_at"),
            "light_alive": status.get("light_alive", False),
        })
```

- [ ] **Step 5: Test çalıştır, pass bekle**

Run: `pytest tests/unit/presentation/dashboard/test_routes_status.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Regression**

Run: `pytest tests/unit/ -q`
Expected: tüm testler PASS.

- [ ] **Step 7: Commit**

```bash
git add src/presentation/dashboard/routes.py tests/unit/presentation/
git commit -m "feat(dashboard): expand /api/status schema with cycle stage fields"
```

---

## Task 5: Dashboard.js cycle status render + idle countdown

**Files:**
- Modify: `src/presentation/dashboard/static/js/dashboard.js`

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY (tek RENDER objesi), ✓ <400 satır (dashboard.js genişliği kontrol edilecek), ✓ frontend I/O sadece API'den, ✓ katman ihlali yok, ✓ magic number: stale threshold 15s literal (JS'te OK), ✓ helpers yok, ✓ sessiz hata yok, ✓ P(YES) ilgisiz."

**Not:** Frontend için unit test altyapısı yok — doğrulama Task 10'da manuel.

- [ ] **Step 1: `RENDER.status()` yeniden yaz**

`src/presentation/dashboard/static/js/dashboard.js` dosyasında mevcut `status()` bloğunu (249-276 satırları) şu kodla değiştir:

```javascript
    status(data) {
      // Light cycle: Online (bot canlı) / Offline (bot ölü)
      const botAlive = !!data.bot_alive;
      this._applyCycle("cg-light", "light",
        botAlive ? "Online" : "Offline", botAlive);

      // Hard cycle: stage'e göre etiket
      if (!botAlive) {
        this._applyCycle("cg-hard", "offline", "Offline", false);
        return;
      }
      const stage = (data.stage || "").toLowerCase();
      const stageRecent = this._isRecent(data.stage_at, 15);
      let label, live;
      if (stage === "scanning" && stageRecent) { label = "Scanning"; live = true; }
      else if (stage === "analyzing" && stageRecent) { label = "Analyzing"; live = true; }
      else if (stage === "executing" && stageRecent) { label = "Executing"; live = true; }
      else if (stage === "idle" || !stageRecent) {
        label = this._idleLabel(data.next_heavy_at);
        live = false;
      }
      else { label = "Waiting"; live = false; }
      this._applyCycle("cg-hard", "hard", label, live);
    },

    _idleLabel(nextHeavyIso) {
      if (!nextHeavyIso) return "Idle";
      const target = new Date(nextHeavyIso).getTime();
      if (isNaN(target)) return "Idle";
      const diff = Math.max(0, target - Date.now());
      const mins = Math.floor(diff / 60000);
      const secs = Math.floor((diff % 60000) / 1000);
      const mm = String(mins).padStart(2, "0");
      const ss = String(secs).padStart(2, "0");
      return `Idle - next ${mm}:${ss}`;
    },

    _applyCycle(id, variant, label, live) {
      document.getElementById(id).className = "cycle-group " + variant;
      document.getElementById(id + "-status").textContent = label;
      const dot = document.querySelector("#" + id + " .cycle-dot");
      if (dot) dot.classList.toggle("live", live);
    },

    _isRecent(iso, maxSeconds) {
      if (!iso) return false;
      const d = new Date(iso);
      if (isNaN(d.getTime())) return false;
      return (Date.now() - d.getTime()) / 1000 <= maxSeconds;
    },
```

- [ ] **Step 2: Idle countdown interval ekle**

`dashboard.js` dosyasında ilk `RENDER` objesinden sonra (yani `// ── RENDER (DOM updates) ──` bloğundan sonra) en altında global state'i cache'le. Dosyanın sonuna, `})(window);` satırından HEMEN ÖNCE şu ekle:

```javascript
  // Idle countdown — /api/status cevabı cache'lenir, 1s'de bir label re-render edilir
  let _lastStatusData = null;
  const _origStatus = RENDER.status.bind(RENDER);
  RENDER.status = function (data) {
    _lastStatusData = data;
    _origStatus(data);
  };
  setInterval(() => {
    if (_lastStatusData) _origStatus(_lastStatusData);
  }, 1000);
```

Bu, `/api/status` verisi 5 sn'de bir güncellense bile idle countdown MM:SS her saniye değişir.

- [ ] **Step 3: Commit**

```bash
git add src/presentation/dashboard/static/js/dashboard.js
git commit -m "feat(dashboard): render cycle stage labels + idle MM:SS countdown"
```

---

## Task 6: Pozisyon kartı redesign (feed.js)

**Files:**
- Modify: `src/presentation/dashboard/static/js/feed.js`

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY (3 helper), ✓ <400 satır, ✓ frontend, ✓ katman izolasyonu, ✓ magic number yok (saat eşikleri açık), ✓ helpers yok (feed.js içi private fn'lar), ✓ sessiz hata yok (fallback'ler explicit), ✓ P(YES) ilgisiz."

- [ ] **Step 1: Yeni helper'ları ve `_activeCard` yeniden yazımını uygula**

`src/presentation/dashboard/static/js/feed.js` dosyasında mevcut `_title(slug)` helper'ını ve `_activeCard(p)` metodunu (51-87 satırları) şu kodla değiştir:

```javascript
    _title(slug) {
      return `<span class="feed-market">${FMT.escapeHtml(slug || "--")}</span>`;
    },

    _teamsTitle(question, slug) {
      // "Arizona Diamondbacks vs. Baltimore Orioles" → "Diamondbacks vs Orioles"
      if (!question) return FMT.escapeHtml(slug || "--");
      const parts = question.split(/\s+vs\.?\s+/i);
      if (parts.length !== 2) return FMT.escapeHtml(question);
      const shortSide = (s) => {
        const tokens = s.trim().split(/\s+/);
        return tokens[tokens.length - 1] || s;
      };
      return FMT.escapeHtml(`${shortSide(parts[0])} vs ${shortSide(parts[1])}`);
    },

    _confPill(conf) {
      const c = (conf || "?").toUpperCase();
      const cls = c === "A" ? "conf-a" : c === "B" ? "conf-b" : c === "C" ? "conf-c" : "conf-unk";
      return `<span class="feed-conf ${cls}">${c}</span>`;
    },

    _countdownPill(matchStartIso, matchLive) {
      if (!matchStartIso) return "";
      const start = new Date(matchStartIso).getTime();
      if (isNaN(start)) return "";
      const diff = start - Date.now();
      if (diff <= 0) {
        if (matchLive) return `<span class="feed-countdown live">LIVE</span>`;
        return "";
      }
      const mins = Math.floor(diff / 60000);
      const hours = Math.floor(mins / 60);
      const remMins = mins % 60;
      const label = hours > 0 ? `${hours}h ${remMins}m` : `${mins}m`;
      return `<span class="feed-countdown">${label}</span>`;
    },

    _cardOpen(slug) {
      const url = FMT.polyUrl(slug);
      return `<a class="feed-item" href="${url}" target="_blank" rel="noopener noreferrer">`;
    },

    _activeCard(p) {
      const icon = ICONS.getSportEmoji(p.sport_tag, p.slug);
      const dir = p.direction === "BUY_YES" ? "YES" : "NO";
      const dirCls = p.direction === "BUY_YES" ? "badge-yes" : "badge-no";
      // Token-native PnL: shares × current_price − size_usdc. Direction-agnostic
      // çünkü current_price pozisyonun token'ına aittir (YES/NO).
      const pnl = p.shares * p.current_price - p.size_usdc;
      const pnlPct = p.size_usdc > 0 ? (pnl / p.size_usdc) * 100 : 0;
      const odds = Math.round((p.anchor_probability || 0) * 1000) / 10;
      return `${this._cardOpen(p.slug)}
        <div class="feed-top">
          <div class="feed-market-wrap"><span class="feed-tick">${icon}</span>
            <span class="feed-market">${this._teamsTitle(p.question, p.slug)}</span></div>
          <div class="feed-badges">${this._confPill(p.confidence)}<span class="feed-badge ${dirCls}">${dir}</span></div>
        </div>
        <div class="feed-details">
          <span>Entry ${FMT.cents(p.entry_price)}</span>
          <span>Now ${FMT.cents(p.current_price)}</span>
          <span>Odds ${odds.toFixed(1)}%</span>
        </div>
        <div class="feed-impact">
          <div class="feed-impact-bar"><div class="feed-impact-bar-fill${pnl < 0 ? " neg" : ""}"
            style="width:${Math.min(100, Math.abs(pnlPct))}%"></div></div>
          <span class="${FMT.unrealizedClass(pnl)}">${FMT.usdSignedHtml(pnl)}</span>
        </div>
        <div class="feed-time">
          <span>$${p.size_usdc.toFixed(0)}</span>
          <span class="feed-entry-reason">${p.entry_reason || "normal"}</span>
          ${this._countdownPill(p.match_start_iso, p.match_live)}
        </div>
      </a>`;
    },
```

**Not:** `_title(slug)` helper'ı bırakıldı — `_exitedCard`, `_skippedCard`, `_stockCard` hala kullanıyor.

- [ ] **Step 2: Manuel syntax check**

Run: `node -c src/presentation/dashboard/static/js/feed.js`
Expected: hata yok (syntax OK).

Not: `node -c` yoksa, tarayıcıda dashboard'ı açıp console'da hata olup olmadığına bak (Task 10).

- [ ] **Step 3: Commit**

```bash
git add src/presentation/dashboard/static/js/feed.js
git commit -m "feat(dashboard): redesign active position card (team names, countdown, conf pill, odds)"
```

---

## Task 7: CSS — conf pill, countdown pill, layout

**Files:**
- Modify: `src/presentation/dashboard/static/css/feed.css`

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY (BEM-benzeri sınıflar), ✓ <400 satır, ✓ CSS, ✓ katman izolasyonu, ✓ magic number: renkler hex (design system, OK), ✓ helpers yok, ✓ sessiz hata yok, ✓ P(YES) ilgisiz."

- [ ] **Step 1: CSS'i genişlet**

`src/presentation/dashboard/static/css/feed.css` dosyasının SONUNA şunu ekle (mevcut stilleri override etmek için dosya sonunda):

```css
/* Active card — yeni öğeler (Task 7) */
.feed-badges {
  display: inline-flex;
  align-items: center;
  gap: 6px;  /* A ↔ YES arası gap — volatility_swing ↔ $50 ile eşit */
}

.feed-conf {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #0a0a0a;
}
.feed-conf.conf-a   { background: #16c784; }             /* A — yeşil */
.feed-conf.conf-b   { background: #a4d45a; color: #0a0a0a; }  /* B — sarıya yakın yeşil (lime) */
.feed-conf.conf-c   { background: #e6c94d; color: #0a0a0a; }  /* C — sarı */
.feed-conf.conf-unk { background: #4b5563; color: #e5e7eb; }  /* bilinmiyor */

.feed-countdown {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(59, 130, 246, 0.18);  /* mavi @ opacity düşük */
  color: #93c5fd;
  margin-left: auto;  /* alt satır: en sağa yasla */
}
.feed-countdown.live {
  background: rgba(239, 68, 68, 0.22);
  color: #fecaca;
}

/* feed-time: $50 ↔ volatility_swing gap'i A ↔ YES (=6px) ile aynı olsun */
.feed-time {
  display: flex;
  align-items: center;
  gap: 6px;
}
.feed-time .feed-entry-reason {
  color: #9ca3af;
}
/* countdown kartın sağ kenarına yapışık — padding-right'ı parent .feed-item yönetir */
```

- [ ] **Step 2: Dashboard'ı tarayıcıda aç, layout kontrolü**

Bu Task 10'da topluca doğrulanır. Şimdi sadece commit yap.

- [ ] **Step 3: Commit**

```bash
git add src/presentation/dashboard/static/css/feed.css
git commit -m "feat(dashboard): add styles for conf pill, countdown pill, card layout gaps"
```

---

## Task 8: Full test suite regression

**Files:** (yok — sadece test çalıştırma)

- [ ] **Step 1: Tüm testler geçiyor mu**

Run: `pytest -q`
Expected: 0 failed, 0 errors. Eğer kırık varsa:
1. Kırılan test dosyasını oku
2. Değişiklik hangi davranışa dokundu bul
3. Test beklentisini değiştir (dokümante edilmiş bir schema değişikliğiyse) VEYA implementasyonu düzelt
4. Tekrar çalıştır

- [ ] **Step 2: Commit yoksa atla**

Eğer düzeltme gerekirse:
```bash
git add -A
git commit -m "fix: update affected tests for new bot_status schema"
```

---

## Task 9: Bot restart + E2E doğrulama hazırlığı

**Files:** (yok — runtime adımı)

- [ ] **Step 1: Eski dashboard + bot'u kapat**

```bash
taskkill //F //IM python.exe 2>&1 || true
```

(Tüm python süreçlerini kapatır; alternatif: `wmic process where ... terminate` ile sadece ilgili olanlar.)

- [ ] **Step 2: Bot'u tekrar başlat (arka plan)**

Run (background):
```
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m src.main
```

- [ ] **Step 3: Dashboard'ı tekrar başlat (arka plan)**

Run (background):
```
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m src.presentation.dashboard.app
```

- [ ] **Step 4: Log kontrolü**

Run: `tail -5 "logs/bot.log"`
Expected: "Agent starting" satırı mevcut, hata yok.

---

## Task 10: E2E manuel doğrulama

**Files:** (yok — tarayıcı testi)

- [ ] **Step 1: Dashboard'ı aç**

Tarayıcı: `http://localhost:5000` (veya config'de hangi port varsa). Browser console'u aç (F12 → Console).

- [ ] **Step 2: Cycle etiketleri beklenen gibi mi**

İlk heavy cycle (~dakikalar içinde):
- Sayfa yüklenirken "Waiting" gösterir
- Heavy başlayınca sırayla `Scanning` → `Analyzing` → `Executing` → `Idle - next MM:SS` geçişleri görülmeli
- Light cycle etiketi sürekli `Online`
- Console'da JS hatası olmamalı

Eğer etiket "Waiting" kalıyorsa → `logs/bot_status.json`'a bak, `stage` alanı var mı kontrol et. Varsa frontend sorunu, yoksa backend sorunu.

- [ ] **Step 3: Idle countdown MM:SS her saniye azalıyor mu**

Heavy bittikten sonra `Idle - next 29:54`, `Idle - next 29:53`, ... şeklinde saniye bazında güncellenmeli. `setInterval` çalışıyor mu kontrol: console'a `_lastStatusData` yaz, null değilse tamam.

- [ ] **Step 4: Pozisyon kartları beklenen şekilde**

Her aktif pozisyon için:
- Başlıkta takım isimleri (ör. "Diamondbacks vs Orioles"), slug DEĞİL
- Sağ üstte sırayla: conf pill (A yeşil / B lime / C sarı), ardından YES/NO badge
- Detay satırı: `Entry 41¢   Now 41¢   Odds 40.9%`
- Alt satır: `$50   volatility_swing   [54m]` — countdown sağ kenara yapışık, YES ile aynı dikey hiza
- Conf rozeti A ise yeşil, B ise sarıya yakın yeşil (lime)
- Countdown mavi pill, göze batmıyor (düşük opacity)

- [ ] **Step 5: "Sorunlar" dokümante et ve bildir**

Eğer herhangi bir adımda beklenen davranış yoksa:
1. Hangi adımda hata var
2. Ekran görüntüsü veya console çıktısı
3. `logs/bot_status.json` son snapshot'ı
4. Yeni bir task açarak fix

---

## Self-Review Checklist

Bu plan yazıldıktan sonra:

1. **Spec coverage:**
   - [✓] Cycle stage backend (Task 1-3)
   - [✓] /api/status schema (Task 4)
   - [✓] Hard cycle frontend labels + idle countdown (Task 5)
   - [✓] Light Online/Offline (Task 5)
   - [✓] Position card redesign: takım isimleri, countdown, conf pill, odds (Task 6)
   - [✓] CSS renkler + layout gap (Task 7)
   - [✓] Hata toleransı (spec §5) — Task 2 (OSError), Task 5 (stage stale), Task 6 (fallback)
   - [✓] Scope out: entry brainstorm ayrı oturumda (spec §6 — Task listesine dahil değil)

2. **Placeholder scan:** TBD/TODO yok; her step'te gerçek kod var.

3. **Type consistency:**
   - `_write_bot_status_stage(cycle, stage)` Task 2 ve Task 3'te aynı imza.
   - `next_heavy_at_iso()` Task 1 tanımı ve Task 2 kullanımı tutarlı.
   - `/api/status` alan isimleri (cycle, stage, stage_at, next_heavy_at, light_alive) tüm task'larda aynı.

4. **Ambiguity:**
   - Idle stale eşiği: 15s (RENDER.status içinde), sınıf geç kalırsa "Idle" gösterir — açık.
   - Countdown formatı: `Xh Ym` / `Xm` / `LIVE` / boş — açık.
   - Conf renkleri hex ile sabit — açık.
