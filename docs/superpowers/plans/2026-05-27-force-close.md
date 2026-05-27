# Force-Close Stuck Losing Positions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Açık kalmış kayıp pozisyonlar için "match bitti" sinyalinde (ESPN status veya elapsed timeout) zorla satış + bid yoksa 0 ile realize.

**Architecture:** Infrastructure'da ESPN client'a 1 method; Strategy'de yeni saf karar modülü (`time_force_close.py`); Orchestration'da exit_processor'a force-close akışı; Config'de timeout tablosu. 3 bot'a sırayla uygulanır (paper → lab → ana bot).

**Tech Stack:** Python 3.12+, pydantic config, pytest, httpx (ESPN), mevcut paper_fill walker.

**Spec:** [docs/superpowers/specs/2026-05-27-force-close-design.md](../specs/2026-05-27-force-close-design.md)

---

## File Map (Phase 1 — tennis-paper-lab)

| Dosya | Action | Sorumluluk |
|---|---|---|
| `src/infrastructure/apis/espn_client.py` | Modify | `get_match_status(event_id, sport)` method ekle |
| `src/strategy/exit/time_force_close.py` | **Create** | Saf karar: signal var/yok |
| `src/models/exit_signal.py` (varsa) veya `strategy/exit/monitor.py` | Modify | `ForceCloseSignal` ya da `ExitReason.FORCE_CLOSE_*` enum |
| `src/config/settings.py` | Modify | `ForceCloseTimeoutsConfig` pydantic model |
| `config_tennis.yaml` | Modify | `force_close_timeouts` block ekle |
| `src/orchestration/exit_processor.py` | Modify | Force-close çağrısı + slippage-bypass execute |
| `src/infrastructure/paper_fill.py` (varsa) | Read-only | Mevcut walk_book_sell tekrar kullanılır |
| `tests/unit/strategy/exit/test_time_force_close.py` | **Create** | 8 unit test |
| `tests/unit/infrastructure/apis/test_espn_client.py` | Modify | get_match_status için 4 test ekle |
| `tests/integration/orchestration/test_exit_processor_force_close.py` | **Create** | 2 integration test |

---

# PHASE 1 — Tennis Paper Lab (en az risk, ana implementasyon)

## Task 1: ESPNMatchStatus data class + helper

**Files:**
- Modify: `c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/infrastructure/apis/espn_client.py`
- Test: `c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/tests/unit/infrastructure/apis/test_espn_client.py`

- [ ] **Step 1: Write failing test for MatchStatus structure**

Add to `test_espn_client.py`:
```python
def test_match_status_dataclass_fields():
    from src.infrastructure.apis.espn_client import MatchStatus
    s = MatchStatus(state="FINAL", period=2, is_completed=True)
    assert s.state == "FINAL"
    assert s.period == 2
    assert s.is_completed is True
```

- [ ] **Step 2: Run, expect ImportError**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && PYTHONIOENCODING=utf-8 pytest tests/unit/infrastructure/apis/test_espn_client.py::test_match_status_dataclass_fields -v
```
Expected: FAIL, "cannot import name 'MatchStatus'"

- [ ] **Step 3: Add MatchStatus dataclass in espn_client.py**

After existing `ESPNMatchScore` dataclass (~line 28), add:
```python
@dataclass(frozen=True)
class MatchStatus:
    """ESPN'den maç state özeti — force-close kararı için.

    state: ESPN type.state normalize edilmiş — "pre" / "in" / "post"
    period: cari/son period numarası (tenis: set, basketbol: çeyrek)
    is_completed: ESPN type.completed flag
    """
    state: str
    period: int | None
    is_completed: bool
```

- [ ] **Step 4: Run, expect PASS**

```bash
PYTHONIOENCODING=utf-8 pytest tests/unit/infrastructure/apis/test_espn_client.py::test_match_status_dataclass_fields -v
```
Expected: PASS

- [ ] **Step 5: Commit**

Not commit yet — kullanıcı onayı bekleniyor (CLAUDE.md kuralı). Atla, sıradaki task.

---

## Task 2: ESPN `get_match_status(event_id, sport)` method

**Files:**
- Modify: `src/infrastructure/apis/espn_client.py`
- Test: `tests/unit/infrastructure/apis/test_espn_client.py`

- [ ] **Step 1: Write 4 failing tests**

Add to `test_espn_client.py`:
```python
def test_get_match_status_returns_final_when_completed(monkeypatch):
    from src.infrastructure.apis.espn_client import ESPNClient

    def fake_http_get(url, params=None, timeout=None):
        class R:
            status_code = 200
            def json(self):
                return {
                    "events": [{
                        "groupings": [{
                            "competitions": [{
                                "id": "401234",
                                "status": {"type": {"state": "post", "completed": True}, "period": 2},
                                "competitors": [
                                    {"homeAway": "home", "athlete": {"displayName": "A"}},
                                    {"homeAway": "away", "athlete": {"displayName": "B"}},
                                ],
                                "linescores": [],
                            }]
                        }],
                    }],
                }
        return R()

    client = ESPNClient(http_get=fake_http_get)
    result = client.get_match_status("401234", sport="tennis")
    assert result is not None
    assert result.is_completed is True
    assert result.state == "post"


def test_get_match_status_returns_in_progress(monkeypatch):
    from src.infrastructure.apis.espn_client import ESPNClient

    def fake_http_get(url, params=None, timeout=None):
        class R:
            status_code = 200
            def json(self):
                return {"events": [{"groupings": [{"competitions": [{
                    "id": "401234",
                    "status": {"type": {"state": "in", "completed": False}, "period": 1},
                    "competitors": [
                        {"homeAway": "home", "athlete": {"displayName": "A"}},
                        {"homeAway": "away", "athlete": {"displayName": "B"}},
                    ],
                    "linescores": [],
                }]}]}]}
        return R()

    client = ESPNClient(http_get=fake_http_get)
    result = client.get_match_status("401234", sport="tennis")
    assert result is not None
    assert result.is_completed is False
    assert result.state == "in"
    assert result.period == 1


def test_get_match_status_event_not_found_returns_none():
    from src.infrastructure.apis.espn_client import ESPNClient

    def fake_http_get(url, params=None, timeout=None):
        class R:
            status_code = 200
            def json(self):
                return {"events": []}
        return R()

    client = ESPNClient(http_get=fake_http_get)
    result = client.get_match_status("nonexistent", sport="tennis")
    assert result is None


def test_get_match_status_api_error_returns_none():
    import httpx
    from src.infrastructure.apis.espn_client import ESPNClient

    def fake_http_get(url, params=None, timeout=None):
        raise httpx.TimeoutException("timeout")

    client = ESPNClient(http_get=fake_http_get)
    result = client.get_match_status("401234", sport="tennis")
    assert result is None
```

- [ ] **Step 2: Run, expect 4 FAIL**

```bash
PYTHONIOENCODING=utf-8 pytest tests/unit/infrastructure/apis/test_espn_client.py::test_get_match_status -v
```
Expected: 4 FAIL, "ESPNClient has no get_match_status"

- [ ] **Step 3: Implement `get_match_status` in ESPNClient**

Add inside `ESPNClient` class (after `fetch_scoreboard`, ~line 130):
```python
def get_match_status(self, event_id: str, sport: str) -> MatchStatus | None:
    """Belirli bir event_id için ESPN status'ını döner.

    Returns:
        MatchStatus: maç bulundu ve parse edildi
        None: API hatası, parse hatası, event bulunamadı
    """
    # ESPN tennis scoreboard üç tarihten oluşan pencere içerir; bugünün scoreboard'ı yeterli.
    # Diğer sporlar için league parameter ileride eklenebilir (default: scoreboard'lar)
    if sport == "tennis":
        leagues = ["atp", "wta"]
    else:
        # Ana bot diğer sportlar için league'i ayrı çağırır; bu method tennis-paper için
        # tennis odaklı, league taraması infrastructure'da sport_routing.py'a delege edilebilir.
        leagues = [sport]

    for league in leagues:
        url = f"{_ESPN_BASE_URL}/{sport}/{league}/scoreboard"
        try:
            resp = self._http_get(url, params={}, timeout=self._timeout)
            if resp.status_code >= 400:
                continue
            data = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN status %s/%s failed: %s", sport, league, e)
            continue
        except Exception as e:
            logger.warning("ESPN status %s/%s unexpected: %s", sport, league, e)
            continue

        status = self._find_event_status(data, event_id, sport)
        if status is not None:
            return status

    return None

def _find_event_status(self, data: dict, event_id: str, sport: str) -> MatchStatus | None:
    """ESPN scoreboard data'sında event_id'yi bul, MatchStatus döndür."""
    events = data.get("events") or []
    for ev in events:
        if sport == "tennis":
            for grouping in (ev.get("groupings") or []):
                for comp in (grouping.get("competitions") or []):
                    if str(comp.get("id", "")) == str(event_id):
                        return self._extract_status(comp)
        else:
            if str(ev.get("id", "")) == str(event_id):
                comps = ev.get("competitions") or []
                if comps:
                    return self._extract_status(comps[0])
    return None

@staticmethod
def _extract_status(comp: dict) -> MatchStatus | None:
    """Competition dict'ten MatchStatus üret. None → parse başarısız."""
    status = comp.get("status") or {}
    type_info = status.get("type") or {}
    state = (type_info.get("state") or "").lower()
    if not state:
        return None
    period_raw = status.get("period")
    period = period_raw if isinstance(period_raw, int) and period_raw > 0 else None
    completed = bool(type_info.get("completed", False))
    return MatchStatus(state=state, period=period, is_completed=completed)
```

- [ ] **Step 4: Run all 4 tests, expect PASS**

```bash
PYTHONIOENCODING=utf-8 pytest tests/unit/infrastructure/apis/test_espn_client.py::test_get_match_status -v
```
Expected: 4 PASS

---

## Task 3: ForceCloseTimeoutsConfig pydantic model

**Files:**
- Modify: `src/config/settings.py`
- Test: `tests/unit/config/test_settings.py`

- [ ] **Step 1: Write failing test**

Add to `tests/unit/config/test_settings.py`:
```python
def test_force_close_timeouts_loads_from_yaml(tmp_path):
    import yaml
    from src.config.settings import load_config
    cfg_dict = {
        "initial_bankroll": 1000,
        "scan_interval_seconds": 60,
        "max_active_markets": 30,
        "edge": {"min_edge": 0.05, "min_market_volume": 100},
        "risk": {
            "max_single_bet_usdc": 50,
            "max_bet_pct": 0.05,
            "confidence_bet_pct": {"A": 0.05, "B": 0.035},
            "force_close_timeouts": {
                "tennis_first_set_winner": 60,
                "default": 300,
            },
        },
    }
    cfg_path = tmp_path / "test_config.yaml"
    cfg_path.write_text(yaml.dump(cfg_dict), encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.risk.force_close_timeouts["tennis_first_set_winner"] == 60
    assert cfg.risk.force_close_timeouts["default"] == 300


def test_force_close_timeouts_defaults_to_empty():
    from src.config.settings import RiskConfig
    rc = RiskConfig(max_single_bet_usdc=50, max_bet_pct=0.05,
                    confidence_bet_pct={"A": 0.05, "B": 0.035})
    assert rc.force_close_timeouts == {}
```

- [ ] **Step 2: Run, expect FAIL**

```bash
PYTHONIOENCODING=utf-8 pytest tests/unit/config/test_settings.py::test_force_close_timeouts -v
```
Expected: 2 FAIL

- [ ] **Step 3: Add `force_close_timeouts` to `RiskConfig`**

In `src/config/settings.py`, locate `class RiskConfig` and add field:
```python
class RiskConfig(BaseModel):
    # ... existing fields ...
    # 2026-05-27 (SPEC-force-close): market_type → max dakika; süre dolarsa pozisyon zorla kapatılır.
    # Boş dict → feature devre dışı (mevcut SL/TP zincirine etki yok).
    force_close_timeouts: dict[str, int] = Field(default_factory=dict)
```

- [ ] **Step 4: Run tests, expect PASS**

```bash
PYTHONIOENCODING=utf-8 pytest tests/unit/config/test_settings.py::test_force_close_timeouts -v
```
Expected: 2 PASS

---

## Task 4: `time_force_close.py` saf karar modülü

**Files:**
- Create: `src/strategy/exit/time_force_close.py`
- Create: `tests/unit/strategy/exit/test_time_force_close.py`

- [ ] **Step 1: Write 8 failing tests**

Create `tests/unit/strategy/exit/test_time_force_close.py`:
```python
"""Force-close strategy tests — saf karar mantığı.

8 case:
  1. ESPN says FINAL → signal "espn_event_ended"
  2. ESPN says set N>=2 for first_set_winner → signal
  3. ESPN says still in set 1 for first_set_winner → None
  4. No ESPN + elapsed > timeout → signal "time_expired"
  5. No ESPN + elapsed < timeout → None
  6. Missing match_start_iso → None (skip)
  7. market_type not in timeouts → use default
  8. market_type not in timeouts AND no default → None
"""
from datetime import datetime, timezone, timedelta
from src.infrastructure.apis.espn_client import MatchStatus
from src.strategy.exit.time_force_close import check, ForceCloseSignal
from src.models.position import Position


def _make_position(market_type: str, started_minutes_ago: int) -> Position:
    start = datetime.now(timezone.utc) - timedelta(minutes=started_minutes_ago)
    return Position(
        condition_id="0xabc",
        token_id="123",
        direction="BUY_YES",
        entry_price=0.5,
        size_usdc=35.0,
        shares=70.0,
        slug="test-match",
        entry_timestamp=start.isoformat(),
        entry_reason="test",
        confidence="B",
        anchor_probability=0.5,
        current_price=0.05,
        bid_price=0.04,
        match_start_iso=start.isoformat(),
        event_id="401234",
        sports_market_type=market_type,
    )


def test_espn_final_returns_signal():
    pos = _make_position("tennis_match_winner", 100)
    espn = MatchStatus(state="post", period=3, is_completed=True)
    now = datetime.now(timezone.utc)
    result = check(pos, espn, now, timeouts={"tennis_match_winner": 200}, market_type=pos.sports_market_type)
    assert isinstance(result, ForceCloseSignal)
    assert result.reason == "espn_event_ended"


def test_espn_set_2_for_first_set_market_returns_signal():
    pos = _make_position("tennis_first_set_winner", 70)
    espn = MatchStatus(state="in", period=2, is_completed=False)
    now = datetime.now(timezone.utc)
    result = check(pos, espn, now, timeouts={"tennis_first_set_winner": 60}, market_type=pos.sports_market_type)
    assert result is not None
    assert result.reason == "espn_event_ended"


def test_espn_still_in_set_1_returns_none():
    pos = _make_position("tennis_first_set_winner", 30)
    espn = MatchStatus(state="in", period=1, is_completed=False)
    now = datetime.now(timezone.utc)
    result = check(pos, espn, now, timeouts={"tennis_first_set_winner": 60}, market_type=pos.sports_market_type)
    assert result is None


def test_no_espn_elapsed_exceeds_timeout_returns_signal():
    pos = _make_position("tennis_first_set_winner", 90)
    now = datetime.now(timezone.utc)
    result = check(pos, espn_status=None, now=now, timeouts={"tennis_first_set_winner": 60}, market_type=pos.sports_market_type)
    assert result is not None
    assert result.reason == "time_expired"


def test_no_espn_elapsed_under_timeout_returns_none():
    pos = _make_position("tennis_first_set_winner", 30)
    now = datetime.now(timezone.utc)
    result = check(pos, espn_status=None, now=now, timeouts={"tennis_first_set_winner": 60}, market_type=pos.sports_market_type)
    assert result is None


def test_missing_match_start_returns_none():
    pos = _make_position("tennis_first_set_winner", 90)
    pos.match_start_iso = ""
    now = datetime.now(timezone.utc)
    result = check(pos, espn_status=None, now=now, timeouts={"tennis_first_set_winner": 60}, market_type=pos.sports_market_type)
    assert result is None


def test_unknown_market_type_uses_default():
    pos = _make_position("unknown_market_xyz", 400)
    now = datetime.now(timezone.utc)
    result = check(pos, espn_status=None, now=now, timeouts={"default": 300}, market_type=pos.sports_market_type)
    assert result is not None
    assert result.reason == "time_expired"


def test_unknown_market_type_no_default_returns_none():
    pos = _make_position("unknown_market_xyz", 400)
    now = datetime.now(timezone.utc)
    result = check(pos, espn_status=None, now=now, timeouts={}, market_type=pos.sports_market_type)
    assert result is None
```

- [ ] **Step 2: Run, expect ImportError**

```bash
PYTHONIOENCODING=utf-8 pytest tests/unit/strategy/exit/test_time_force_close.py -v
```
Expected: 8 errors (module not found)

- [ ] **Step 3: Create `src/strategy/exit/time_force_close.py`**

```python
"""Force-close strategy — kayıp pozisyonların maç bittikten sonra zorla kapatılması.

Pure decision module — I/O yok, sadece state + ESPN status + zaman → signal.
Implementation entegrasyonu exit_processor.py'da.

Karar mantığı (hybrid):
  1. ESPN says event ended (set bitti / match final) → signal
  2. ESPN cevap yok / event bulunamadı → elapsed time check
  3. elapsed > timeouts[market_type] (veya default) → signal
  4. Hiçbiri yoksa → None (normal exit chain devam)

SPEC: docs/superpowers/specs/2026-05-27-force-close-design.md
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping

from src.infrastructure.apis.espn_client import MatchStatus
from src.models.position import Position

ForceCloseReason = Literal["espn_event_ended", "time_expired"]


@dataclass(frozen=True)
class ForceCloseSignal:
    """Force-close tetiklendi — exit_processor slippage-bypass satışı çalıştırır."""
    reason: ForceCloseReason


def check(
    pos: Position,
    espn_status: MatchStatus | None,
    now: datetime,
    timeouts: Mapping[str, int],
    market_type: str,
) -> ForceCloseSignal | None:
    """Pozisyon için force-close sinyali üret — None = sinyal yok."""
    # 1. ESPN-first: bu market_type'ın olayı bittiyse hemen sinyal
    if espn_status is not None and _espn_indicates_event_done(espn_status, market_type):
        return ForceCloseSignal(reason="espn_event_ended")

    # 2. Time-based fallback
    if not pos.match_start_iso:
        return None

    try:
        start = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
    except ValueError:
        return None

    elapsed_min = (now - start).total_seconds() / 60
    timeout_min = timeouts.get(market_type) or timeouts.get("default")
    if timeout_min is None:
        return None
    if elapsed_min > timeout_min:
        return ForceCloseSignal(reason="time_expired")
    return None


def _espn_indicates_event_done(status: MatchStatus, market_type: str) -> bool:
    """Market_type için ilgili period/match bitmiş mi?

    Period-based markets (e.g. tennis_first_set_winner): cari period >=2 yeterli.
    Match-level markets (e.g. tennis_match_winner): completed=True gerek.
    """
    if status.is_completed:
        return True
    # First-set / set-N specific markets: o setin bitmiş olduğu = period > 1
    if "first_set" in market_type and status.period is not None and status.period >= 2:
        return True
    # Quarter/period-based extension: q1 winner için period >= 2
    # (NBA için ileride ana bot'a aynı pattern uygulanır)
    if "_quarter_1" in market_type and status.period is not None and status.period >= 2:
        return True
    return False
```

- [ ] **Step 4: Run 8 tests, expect PASS**

```bash
PYTHONIOENCODING=utf-8 pytest tests/unit/strategy/exit/test_time_force_close.py -v
```
Expected: 8 PASS

---

## Task 5: Add `force_close_timeouts` to config_tennis.yaml

**Files:**
- Modify: `config_tennis.yaml`

- [ ] **Step 1: Add config block**

In `config_tennis.yaml`, locate `risk:` block. After `stop_loss_exempt_market_types:` add:
```yaml
  # 2026-05-27 (SPEC-force-close): market_type başına max dakika.
  # Süre dolduğunda + ESPN bittiğini gösterirse pozisyon zorla bid'den satılır,
  # bid yoksa 0 ile realize. Saf güvenlik ağı — normal SL/TP zincirine etki yok.
  force_close_timeouts:
    tennis_first_set_winner: 60
    tennis_set_handicap: 60
    tennis_first_set_totals: 60
    tennis_match_winner: 200
    tennis_match_totals: 200
    tennis_set_totals: 200
    moneyline: 200       # tenis moneyline (canlıdaki çoğu first-set olmayan binary market)
    default: 300
```

- [ ] **Step 2: Verify config loads without error**

```bash
PYTHONIOENCODING=utf-8 python -c "from src.config.settings import load_config; cfg = load_config('config_tennis.yaml'); print(cfg.risk.force_close_timeouts)"
```
Expected: dict yazdırır

---

## Task 6: Integrate force-close into exit_processor

**Files:**
- Modify: `src/orchestration/exit_processor.py`
- Modify: `src/strategy/exit/monitor.py` (ExitReason enum'a ekleme)
- Test: `tests/integration/orchestration/test_exit_processor_force_close.py` (create)

- [ ] **Step 1: Inspect `monitor.py` to find ExitReason enum**

Read `src/strategy/exit/monitor.py`, locate `ExitReason` enum (search: `class ExitReason`). Note its location for next step.

- [ ] **Step 2: Add new ExitReason values**

In `monitor.py` ExitReason enum, add:
```python
FORCE_CLOSE_ESPN = "force_close_espn_event_ended"
FORCE_CLOSE_TIME = "force_close_time_expired"
FORCE_CLOSE_NO_BIDS = "force_close_no_bids"
```

- [ ] **Step 3: Write failing integration test**

Create `tests/integration/orchestration/test_exit_processor_force_close.py`:
```python
"""Integration test — exit_processor force-close akışı.

Senaryolar:
  1. Force-close signal + bid var → slippage bypass ile satılır, realize edilir
  2. Force-close signal + bid yok → 0 ile realize, exit_reason=FORCE_CLOSE_NO_BIDS
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest


def test_force_close_with_bid_realizes_at_bid(tmp_path):
    # SETUP: position 2 saatlik açık, time_expired
    # MOCK: paper_fill.walk_book_sell → FILLED at 0.01
    # ASSERT: realized_pnl = -size + (shares * 0.01), exit_reason=FORCE_CLOSE_TIME
    # SCAFFOLD: bu test exit_processor refactor sonrası yazılır (Task 6 step 4)
    pytest.skip("scaffolded — implement after exit_processor refactor")


def test_force_close_no_bids_realizes_zero():
    # SETUP: position 2 saatlik açık
    # MOCK: paper_fill.walk_book_sell → REJECTED (no bids)
    # ASSERT: realized_pnl = -size_usdc (tam kayıp), exit_reason=FORCE_CLOSE_NO_BIDS
    pytest.skip("scaffolded — implement after exit_processor refactor")
```

- [ ] **Step 4: Add force-close branch to exit_processor.run_light**

In `src/orchestration/exit_processor.py`, after existing `exit_monitor.evaluate(...)` call and before `self._execute_exit(...)`, add force-close check.

Find the loop:
```python
for cid in list(state.portfolio.positions.keys()):
    pos = state.portfolio.positions.get(cid)
    if pos is None:
        continue

    tick_position_state(pos)
    score_info = scores.get(cid, {})
    result: MonitorResult = exit_monitor.evaluate(...)
    self._apply_fav_transition(pos, result.fav_transition)

    if result.exit_signal is not None:
        self._execute_exit(pos, result.exit_signal)
        exits_processed += 1
```

Replace the `if result.exit_signal is not None:` block with:
```python
    if result.exit_signal is not None:
        self._execute_exit(pos, result.exit_signal)
        exits_processed += 1
        continue

    # Force-close safety net: maç bittikten sonra hâlâ açık kayıp pozisyonlar
    force_signal = self._check_force_close(pos)
    if force_signal is not None:
        self._execute_force_close(pos, force_signal)
        exits_processed += 1
```

Then add two private methods to `ExitProcessor`:
```python
def _check_force_close(self, pos: Position):
    """Force-close sinyali kontrolü — sadece pozisyon zaraydaysa."""
    if pos.unrealized_pnl_pct >= -0.5:  # %50 zararın altıysa force-close gerek yok
        return None
    from src.strategy.exit.time_force_close import check as fc_check
    timeouts = self.deps.state.config.risk.force_close_timeouts
    if not timeouts:
        return None
    espn_status = self._fetch_espn_status_cached(pos.event_id, pos.sport_tag)
    return fc_check(
        pos=pos,
        espn_status=espn_status,
        now=datetime.now(timezone.utc),
        timeouts=timeouts,
        market_type=pos.sports_market_type or pos.sport_tag,
    )

def _fetch_espn_status_cached(self, event_id: str, sport: str):
    """ESPN status — 60sn TTL cache. self._espn_cache: dict[event_id, (ts, status)]"""
    if not hasattr(self, "_espn_cache"):
        self._espn_cache = {}
    now_ts = datetime.now(timezone.utc).timestamp()
    cached = self._espn_cache.get(event_id)
    if cached is not None and (now_ts - cached[0]) < 60:
        return cached[1]
    espn = getattr(self.deps, "espn_client", None)
    if espn is None:
        return None
    try:
        status = espn.get_match_status(event_id, sport)
    except Exception as e:
        logger.warning("force_close: ESPN fetch failed for %s: %s", event_id, e)
        status = None
    self._espn_cache[event_id] = (now_ts, status)
    return status

def _execute_force_close(self, pos: Position, signal) -> None:
    """Force-close: slippage bypass'lı satış, bid yoksa 0 realize."""
    from src.infrastructure.paper_fill import walk_book_sell
    from src.strategy.exit.monitor import ExitReason

    # Hangi reason audit'e yazılacak
    if signal.reason == "espn_event_ended":
        exit_reason = ExitReason.FORCE_CLOSE_ESPN.value
    else:
        exit_reason = ExitReason.FORCE_CLOSE_TIME.value

    # Bid orderbook'a satış denemesi — %100 slippage = ne fiyatta olursa olsun
    book = self.deps.market_client.fetch_orderbook(pos.token_id)
    bids = (book or {}).get("bids", [])
    fill = walk_book_sell(
        bids=bids,
        target_price=pos.current_price or 0.001,
        shares=pos.shares,
        max_slippage_pct=1.0,  # full bypass
    )

    if fill.status in ("FILLED", "PARTIAL_FILL") and fill.filled_shares > 0:
        exit_price = fill.avg_price
        sold_shares = fill.filled_shares
        realized = sold_shares * exit_price - (sold_shares / pos.shares) * pos.size_usdc
        self._finalize_exit(pos, exit_price=exit_price, realized=realized,
                            exit_reason=exit_reason, fully_closed=(fill.status == "FILLED"))
    else:
        # Bid yok — 0 realize
        self._finalize_exit(pos, exit_price=0.0, realized=-pos.size_usdc,
                            exit_reason=ExitReason.FORCE_CLOSE_NO_BIDS.value, fully_closed=True)
    logger.info("FORCE_CLOSE %s reason=%s exit_price=%.4f",
                pos.slug[:40], exit_reason, fill.avg_price or 0)
```

> **NOT (engineer):** `_finalize_exit` zaten exit_processor'da var mı? Yoksa mevcut `_execute_exit` yapısını incele ve realize/audit/portfolio update'lerini aynı şekilde çağır. Reuse, duplicate yok (ARCH_GUARD DRY).

- [ ] **Step 5: Implement integration tests (Task 6 step 3'te scaffolded)**

`test_exit_processor_force_close.py` içindeki iki testin `pytest.skip` satırını kaldır, asıl assertion mantığını yaz. Mock structure:
```python
def test_force_close_with_bid_realizes_at_bid():
    # Build minimal deps
    deps = MagicMock()
    deps.state.config.risk.force_close_timeouts = {"tennis_first_set_winner": 60}
    deps.state.portfolio.positions = {}
    deps.market_client.fetch_orderbook.return_value = {"bids": [{"price": 0.01, "size": 100}]}
    deps.espn_client.get_match_status.return_value = None  # ESPN yok, time-based

    # ... create position with match_start 2 hours ago, -%99 pnl
    # ... add to portfolio
    # ... call ExitProcessor(deps).run_light()
    # assert: position removed, realized_pnl ~= -size + shares*0.01
```

(Bu test scaffold'unu engineer detaylandırır — exit_processor'un gerçek arayüzünü test sırasında okur.)

- [ ] **Step 6: Run all tests, expect PASS**

```bash
PYTHONIOENCODING=utf-8 pytest tests/unit/strategy/exit/test_time_force_close.py tests/unit/infrastructure/apis/test_espn_client.py tests/unit/config/test_settings.py tests/integration/orchestration/test_exit_processor_force_close.py -v
```
Expected: hepsi PASS

---

## Task 7: Manual humbert-halys regression check

**Files:** none (manual)

- [ ] **Step 1: Bot'u reload et**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab" && PYTHONIOENCODING=utf-8 python scripts/reboot.py reload
```

- [ ] **Step 2: Sentetik test pozisyonu enjekte et veya mevcut humbert-halys'i izle**

`data/positions.json`'da humbert-halys hâlâ açıksa: bot bir sonraki cycle'da force-close yapmalı (match_start_iso 14:25, şimdi 2+ saat geçmiş, timeout 60dk). Bot.log'da `FORCE_CLOSE` satırı görünmeli.

Eğer humbert-halys yoksa: synthetic_test_position.py ile (yoksa bu testi atla) sahte bir kayıp pozisyon ekle.

- [ ] **Step 3: Doğrula**

```bash
PYTHONIOENCODING=utf-8 python -c "import json; d=json.load(open('data/positions.json')); print('humbert' in str(d), len(d['positions']), d['realized_pnl'])"
grep "FORCE_CLOSE" logs/runtime/bot.log | tail -5
```
Expected: humbert pozisyonu artık açık değil (False), realized_pnl güncellenmiş, log'da FORCE_CLOSE event'i.

---

# PHASE 2 — Tennis Lab (mirror from paper-lab)

## Task 8: Tennis-lab'a dosyaları kopyala

**Files:**
- Mirror from `tennis-paper-lab/` to `tennis-lab/`:
  - `src/infrastructure/apis/espn_client.py` (Task 1+2 değişiklikleri)
  - `src/strategy/exit/time_force_close.py` (yeni dosya)
  - `tests/unit/strategy/exit/test_time_force_close.py` (yeni)
  - `tests/unit/infrastructure/apis/test_espn_client.py` (4 yeni test)
  - `src/config/settings.py` (RiskConfig.force_close_timeouts field)
  - `tests/unit/config/test_settings.py` (2 yeni test)
  - `src/orchestration/exit_processor.py` (force-close integration)
  - `src/strategy/exit/monitor.py` (ExitReason enum genişlemesi)
  - `tests/integration/orchestration/test_exit_processor_force_close.py` (yeni)

- [ ] **Step 1: Diff tennis-lab vs tennis-paper-lab — uyumsuzlukları tespit et**

Her dosya için:
```bash
diff "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/src/infrastructure/apis/espn_client.py" \
     "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/infrastructure/apis/espn_client.py"
```
Beklenen: ya identik ya minor whitespace fark. Eğer büyük fark varsa: tennis-lab'da kendi versiyonu var, manual merge gerek.

- [ ] **Step 2: Her dosya için aynı edit'leri uygula**

Paper-lab'daki değişiklikleri tennis-lab'a manual olarak aynı şekilde yap. NOT: `cp` kullanma — dosyalar birebir aynı değil (mode, comment ufak farklar). Edit ile uygula.

- [ ] **Step 3: Tennis-lab config_tennis.yaml'a force_close_timeouts block ekle**

Paper-lab'daki yaml block'unu aynen kopyala.

- [ ] **Step 4: Tennis-lab testlerini çalıştır**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab" && PYTHONIOENCODING=utf-8 pytest tests/ -v -k "force_close or get_match_status or force_close_timeouts"
```
Expected: 14+ test PASS

- [ ] **Step 5: Tennis-lab'ı reload + manual check**

```bash
PYTHONIOENCODING=utf-8 python scripts/reboot.py reload
```

---

# PHASE 3 — Ana Bot (Polymarket Agent 2.0)

## Task 9: Ana bot için tasarım uyarlamaları

**Files:** none (sadece keşif)

Ana bot tenisten farklı:
- Sports: NBA, NFL, NHL, MLB, WNBA, ATP (tenis lab değil, ana bot'ta da tenis var mı? config kontrolü)
- ESPN client mevcut — get_match_status method'u 1:1 taşınır
- Exit processor benzer yapıda

- [ ] **Step 1: Mevcut espn_client.py'ı oku, tenis paper-lab'daki ile karşılaştır**

```bash
diff "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/src/infrastructure/apis/espn_client.py" \
     "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/infrastructure/apis/espn_client.py"
```
Beklenen output kullanılarak Phase 3'teki adımlar belirlenir.

- [ ] **Step 2: config.yaml'a force_close_timeouts block ekle (ana bot sporları)**

```yaml
risk:
  # ... mevcut ...
  force_close_timeouts:
    nba_quarter_1_winner: 35
    nba_match_winner: 180
    nfl_quarter_1: 45
    nfl_match_winner: 240
    nhl_match_winner: 200
    mlb_match_winner: 240
    wnba_match_winner: 180
    moneyline: 240
    totals: 240
    spread: 240
    default: 300
```

## Task 10: Ana bot — Task 1-6'yı tekrarla

Phase 1'deki Task 1-6'yı sırayla ana bot'a uygula. Tek fark: market_type isimleri farklı (NBA için "nba_quarter_1_winner" gibi). `_espn_indicates_event_done` fonksiyonunda "_quarter_1" branch'i zaten ekli.

- [ ] **Task 10.1:** ESPN MatchStatus + get_match_status (Task 1+2 aynısı)
- [ ] **Task 10.2:** RiskConfig.force_close_timeouts (Task 3 aynısı)
- [ ] **Task 10.3:** time_force_close.py (Task 4 aynısı, içerik birebir)
- [ ] **Task 10.4:** config.yaml force_close_timeouts (Task 9 step 2'deki block)
- [ ] **Task 10.5:** exit_processor entegrasyonu (Task 6 aynısı, ana bot exit_processor.py'a)
- [ ] **Task 10.6:** Pytest -q tümü geçer

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && PYTHONIOENCODING=utf-8 pytest -q
```
Expected: tüm testler PASS, yeni 14 test eklenmiş

## Task 11: Ana bot reload + integration check

- [ ] **Step 1: Reload**

```bash
PYTHONIOENCODING=utf-8 python scripts/reboot.py reload
```

- [ ] **Step 2: Mevcut açık pozisyonların durumunu izle**

15 dk sonra bot.log'da FORCE_CLOSE event'i var mı kontrol et:
```bash
grep "FORCE_CLOSE" logs/runtime/bot.log | tail -10
```

---

# Phase 4 — Cleanup + Commit

## Task 12: ARCH_GUARD drift check

- [ ] **Step 1: 3 bot'taki `time_force_close.py` birebir aynı mı?**

```bash
diff "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/src/strategy/exit/time_force_close.py" \
     "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/strategy/exit/time_force_close.py"
diff "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab/src/strategy/exit/time_force_close.py" \
     "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab/src/strategy/exit/time_force_close.py"
```
Expected: identik (no diff). Drift varsa düzelt.

- [ ] **Step 2: ARCH_GUARD self-scan**

```bash
# Dosya boyutu kontrolü
wc -l "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/src/strategy/exit/time_force_close.py"
wc -l "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0/src/orchestration/exit_processor.py"
```
Expected: time_force_close.py < 100 satır, exit_processor.py < 400 satır.

Eğer exit_processor.py 400+ olduysa: force-close helper'larını ayrı modül `orchestration/force_close_executor.py`'a taşı.

- [ ] **Step 3: DRY drift check**

```bash
grep -rn "force_close_timeouts" "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/" --include="*.py" --include="*.yaml" | grep -v "_pre_" | grep -v ".bak"
```
Expected: her bot'ta config + settings.py + time_force_close.py — 3 yer x 3 bot = 9 satır. Daha fazla varsa drift var.

## Task 13: DECISIONS.md güncelle (ana bot)

- [ ] **Step 1: DECISIONS.md'ye yeni SPEC kaydı ekle**

`Polymarket Agent 2.0/DECISIONS.md` dosyasında §B SPEC log'a:
```markdown
## SPEC-force-close (2026-05-27) — DONE

**Sorun:** Bazı pozisyonlar -%99 zarara düşüp orderbook'ta alıcı kalmayınca SL bypass'a takılıp açık kalıyordu (humbert-halys örneği).

**Çözüm:** Hybrid time+ESPN force-close güvenlik ağı:
1. ESPN-first: maç state'i FINAL veya period bitti → satış
2. Time fallback: match_start_iso'dan timeout aşıldıysa satış
3. Slippage bypass: ne fiyatta olursa olsun bid'den sat
4. Bid yoksa 0 ile realize

**Etki:** 3 bot (ana + tennis-lab + tennis-paper-lab) aynı kod, ayrı config. Yeni spor eklendiğinde:
- ESPN destekliyorsa → otomatik çalışır
- Desteklemiyorsa → config'e 1-2 satır ekle

**Spec:** docs/superpowers/specs/2026-05-27-force-close-design.md
**Plan:** docs/superpowers/plans/2026-05-27-force-close.md
```

## Task 14: Final commit (kullanıcı onayıyla)

- [ ] **Step 1: Kullanıcıya commit onayı sor**

> "Tüm değişiklikler hazır. 3 bot için ayrı commit'ler atayım mı?"

- [ ] **Step 2: Onay alınınca 3 ayrı commit (her bot kendi git repo'sunda)**

Ana bot:
```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0"
git add src/infrastructure/apis/espn_client.py src/strategy/exit/time_force_close.py \
        src/strategy/exit/monitor.py src/config/settings.py config.yaml \
        src/orchestration/exit_processor.py tests/ DECISIONS.md \
        docs/superpowers/specs/2026-05-27-force-close-design.md \
        docs/superpowers/plans/2026-05-27-force-close.md
git commit -m "$(cat <<'EOF'
feat(force-close): zorla kapatma — kayıp pozisyonlar için ESPN+time hybrid safety net

- ESPN match status (FINAL/period bitti) öncelikli kontrol
- match_start_iso'dan timeout aşılırsa zaman tabanlı fallback
- Slippage bypass'lı satış, bid yoksa 0 realize
- 3 bot'a uygulandı: ana + tennis-lab + tennis-paper-lab
- SPEC-force-close, plan + spec doc'lar dahil

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Tennis-lab ve tennis-paper-lab kendi git'lerinde commit (varsa).

---

# Acceptance Verification

Plan tamamlandığında bu maddelerin hepsi check'lenmiş olmalı:

- [ ] 3 bot'ta `force_close_timeouts` config'i mevcut
- [ ] `time_force_close.check()` saf fonksiyon, 8 unit test PASS
- [ ] ESPN `get_match_status` method'u 4 unit test PASS
- [ ] `RiskConfig.force_close_timeouts` 2 unit test PASS
- [ ] `exit_processor` force-close akışı 2 integration test PASS
- [ ] Yeni `ExitReason` enum değerleri dashboard'da görünür
- [ ] `pytest -q` her 3 bot'ta TÜMÜ PASS
- [ ] Humbert-halys (veya benzeri sentetik test) zorla kapatılıyor — manuel check OK
- [ ] DECISIONS.md SPEC-force-close maddesi mevcut (ana bot)
- [ ] 3 bot'ta `time_force_close.py` birebir aynı (drift yok)
- [ ] `exit_processor.py` < 400 satır (ARCH_GUARD kural 3)
- [ ] Hiçbir dosyada `# TODO` veya `# FIXME` placeholder yok (dead code yok)
