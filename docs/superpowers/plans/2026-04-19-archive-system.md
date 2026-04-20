# Archive System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Her exit, skor degisikligi ve mac sonucunu `logs/archive/` altinda append-only JSONL'lere yazan arsiv sistemi. Reboot/reload arsive dokunmaz.

**Architecture:** Yeni `ArchiveLogger` infrastructure'da, exit_processor ve score_enricher'dan cagrilir. 3 dosya: exits.jsonl, score_events.jsonl, match_results.jsonl. Her 3'u append-only; duplicate match_result engellemesi icin startup'ta existing event_id'ler set'e yuklenir.

**Tech Stack:** Python 3.12+, Pydantic, pytest, JSONL append-only

---

### Task 1: ArchiveLogger infrastructure + 3 Pydantic model + unit testler

**Files:**
- Create: `src/infrastructure/persistence/archive_logger.py`
- Create: `tests/unit/infrastructure/persistence/test_archive_logger.py`

- [ ] **Step 1: Test dosyasini yaz (failing)**

Create `tests/unit/infrastructure/persistence/test_archive_logger.py`:

```python
"""archive_logger.py icin birim testler."""
from __future__ import annotations

import json
from pathlib import Path

from src.infrastructure.persistence.archive_logger import (
    ArchiveExitRecord,
    ArchiveLogger,
    ArchiveMatchResult,
    ArchiveScoreEvent,
)


def _make_exit_record() -> ArchiveExitRecord:
    return ArchiveExitRecord(
        slug="mlb-bos-nyy-2026-04-19",
        condition_id="0xabc",
        event_id="12345",
        token_id="token1",
        sport_tag="mlb",
        question="Boston Red Sox vs New York Yankees",
        direction="BUY_YES",
        entry_price=0.55,
        entry_timestamp="2026-04-19T14:00:00Z",
        size_usdc=50.0,
        shares=90.91,
        confidence="A",
        anchor_probability=0.60,
        entry_reason="consensus",
        exit_price=0.94,
        exit_pnl_usdc=35.50,
        exit_reason="near_resolve",
        exit_timestamp="2026-04-19T17:30:00Z",
        score_at_exit="5-2",
        period_at_exit="Top 9th",
        elapsed_pct_at_exit=0.95,
    )


def test_archive_dir_created_on_init(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    ArchiveLogger(str(archive_dir))
    assert archive_dir.exists()
    assert archive_dir.is_dir()


def test_log_exit_writes_jsonl_line(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    record = _make_exit_record()
    archive.log_exit(record)

    exits_file = tmp_path / "exits.jsonl"
    assert exits_file.exists()
    lines = exits_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["slug"] == "mlb-bos-nyy-2026-04-19"
    assert loaded["exit_pnl_usdc"] == 35.50
    assert loaded["score_at_exit"] == "5-2"


def test_log_score_event_writes_jsonl_line(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    event = ArchiveScoreEvent(
        event_id="12345",
        slug="mlb-bos-nyy-2026-04-19",
        sport_tag="mlb",
        timestamp="2026-04-19T15:30:00Z",
        prev_score="1-1",
        new_score="2-1",
        period="Top 5th",
    )
    archive.log_score_event(event)

    file = tmp_path / "score_events.jsonl"
    lines = file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["prev_score"] == "1-1"
    assert loaded["new_score"] == "2-1"


def test_log_match_result_writes_jsonl_line(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    result = ArchiveMatchResult(
        event_id="12345",
        slug="mlb-bos-nyy-2026-04-19",
        sport_tag="mlb",
        final_score="5-3",
        winner_home=True,
        completed_timestamp="2026-04-19T18:00:00Z",
        source="espn",
    )
    archive.log_match_result(result)

    file = tmp_path / "match_results.jsonl"
    lines = file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["final_score"] == "5-3"
    assert loaded["winner_home"] is True


def test_multiple_exits_append_only(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    archive.log_exit(_make_exit_record())
    archive.log_exit(_make_exit_record())
    archive.log_exit(_make_exit_record())

    lines = (tmp_path / "exits.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3


def test_load_logged_match_event_ids_empty(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    ids = archive.load_logged_match_event_ids()
    assert ids == set()


def test_load_logged_match_event_ids_with_existing(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    archive.log_match_result(ArchiveMatchResult(
        event_id="E1", slug="a", sport_tag="mlb", final_score="1-0",
        winner_home=True, completed_timestamp="2026-04-19T18:00:00Z",
    ))
    archive.log_match_result(ArchiveMatchResult(
        event_id="E2", slug="b", sport_tag="nhl", final_score="3-2",
        winner_home=False, completed_timestamp="2026-04-19T19:00:00Z",
    ))

    # Yeni logger instance — dosyadan okusun
    archive2 = ArchiveLogger(str(tmp_path))
    ids = archive2.load_logged_match_event_ids()
    assert ids == {"E1", "E2"}
```

- [ ] **Step 2: Run test — FAIL bekleniyor**

Run: `pytest tests/unit/infrastructure/persistence/test_archive_logger.py -v`
Expected: FAIL with "No module named 'src.infrastructure.persistence.archive_logger'"

- [ ] **Step 3: ArchiveLogger modulunu yaz**

Create `src/infrastructure/persistence/archive_logger.py`:

```python
"""Retrospective rule analysis arsivi (SPEC-009) — append-only JSONL.

3 ayri dosya:
  - exits.jsonl        — her exit'in tam snapshot'i + skor
  - score_events.jsonl — mac icindeki her skor degisikligi
  - match_results.jsonl — mac final result

Reboot/reload DOKUNMAZ: bu dosyalar sifirlanmaz.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ArchiveExitRecord(BaseModel):
    """Bir exit anindaki tam snapshot — trade detayi + skor."""
    model_config = ConfigDict(extra="ignore")

    # Trade kimligi
    slug: str
    condition_id: str
    event_id: str
    token_id: str
    sport_tag: str
    question: str

    # Entry
    direction: str
    entry_price: float
    entry_timestamp: str
    size_usdc: float
    shares: float
    confidence: str
    anchor_probability: float
    entry_reason: str

    # Exit
    exit_price: float
    exit_pnl_usdc: float
    exit_reason: str
    exit_timestamp: str
    partial_exits: list[dict] = []

    # Skor snapshot (exit aninda)
    score_at_exit: str = ""
    period_at_exit: str = ""
    elapsed_pct_at_exit: float = -1.0


class ArchiveScoreEvent(BaseModel):
    """Bir mac icindeki tek bir skor degisikligi."""
    model_config = ConfigDict(extra="ignore")

    event_id: str
    slug: str
    sport_tag: str
    timestamp: str
    prev_score: str
    new_score: str
    period: str = ""


class ArchiveMatchResult(BaseModel):
    """Mac final result — mac tamamlandiginda yazilir."""
    model_config = ConfigDict(extra="ignore")

    event_id: str
    slug: str
    sport_tag: str
    final_score: str
    winner_home: bool | None
    completed_timestamp: str
    source: str = "espn"


class ArchiveLogger:
    """3 ayri append-only JSONL'e yazar. Retrospektif analiz icin."""

    _EXITS_FILE = "exits.jsonl"
    _SCORE_EVENTS_FILE = "score_events.jsonl"
    _MATCH_RESULTS_FILE = "match_results.jsonl"

    def __init__(self, archive_dir: str) -> None:
        self.dir = Path(archive_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def log_exit(self, record: ArchiveExitRecord) -> None:
        self._append(self._EXITS_FILE, record)

    def log_score_event(self, event: ArchiveScoreEvent) -> None:
        self._append(self._SCORE_EVENTS_FILE, event)

    def log_match_result(self, result: ArchiveMatchResult) -> None:
        self._append(self._MATCH_RESULTS_FILE, result)

    def load_logged_match_event_ids(self) -> set[str]:
        """Startup'ta cagrilir — daha once yazilmis match_result'larin
        event_id set'ini dondur. Duplicate yazim engellemesi icin."""
        path = self.dir / self._MATCH_RESULTS_FILE
        if not path.exists():
            return set()
        ids: set[str] = set()
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event_id = data.get("event_id", "")
                    if event_id:
                        ids.add(event_id)
                except json.JSONDecodeError:
                    continue
        return ids

    def _append(self, filename: str, record: BaseModel) -> None:
        with open(self.dir / filename, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
```

- [ ] **Step 4: Run test — PASS bekleniyor**

Run: `pytest tests/unit/infrastructure/persistence/test_archive_logger.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/persistence/archive_logger.py tests/unit/infrastructure/persistence/test_archive_logger.py
git commit -m "feat(persistence): ArchiveLogger + 3 model (SPEC-009 Task 1)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: ArchiveLogger factory DI + AgentDeps

**Files:**
- Modify: `src/orchestration/agent.py` (AgentDeps dataclass)
- Modify: `src/orchestration/factory.py` (wire archive_logger)

- [ ] **Step 1: AgentDeps'e archive_logger ekle**

In `src/orchestration/agent.py`, add import at top (with other persistence imports):

```python
from src.infrastructure.persistence.archive_logger import ArchiveLogger
```

In the `AgentDeps` dataclass (around line 35-52), add field:

```python
@dataclass
class AgentDeps:
    """Dependency injection container — test için mock'lanabilir."""
    state: RuntimeState
    scanner: MarketScanner
    cycle_manager: CycleManager
    executor: Executor
    odds_client: object
    trade_logger: TradeHistoryLogger
    gate: EntryGate
    cooldown: CooldownTracker
    equity_logger: EquityHistoryLogger
    skipped_logger: SkippedTradeLogger
    stock: StockQueue
    bot_status_writer: BotStatusWriter
    archive_logger: ArchiveLogger  # YENI
    price_feed: PriceFeed | None = None
    score_enricher: ScoreEnricher | None = None
    command_poller: TelegramCommandPoller | None = None
```

- [ ] **Step 2: factory.py'de archive_logger olustur ve gecir**

In `src/orchestration/factory.py`, add import at top:

```python
from src.infrastructure.persistence.archive_logger import ArchiveLogger
```

In `build_agent()` function, find the section where loggers are created (`trade_logger = ...`, `equity_logger = ...`) around line 57-60. Add:

```python
trade_logger = TradeHistoryLogger("logs/trade_history.jsonl")
equity_logger = EquityHistoryLogger("logs/equity_history.jsonl")
skipped_logger = SkippedTradeLogger("logs/skipped_trades.jsonl")
archive_logger = ArchiveLogger("logs/archive")  # YENI
```

Then in the `AgentDeps(...)` construction (around line 141-150), add `archive_logger=archive_logger`:

```python
deps = AgentDeps(
    state=state, scanner=scanner, cycle_manager=cycle_manager,
    executor=executor, odds_client=odds, trade_logger=trade_logger,
    gate=gate, cooldown=cooldown,
    equity_logger=equity_logger, skipped_logger=skipped_logger,
    stock=stock, bot_status_writer=bot_status_writer,
    archive_logger=archive_logger,  # YENI
    price_feed=price_feed,
    score_enricher=score_enricher,
    command_poller=command_poller,
)
```

- [ ] **Step 3: test_agent.py'yi guncelle**

In `tests/unit/orchestration/test_agent.py`, bul AgentDeps(...) olusturan test helper'i. archive_logger parametresi eklenmeli. Muhtemelen `_make_deps()` veya benzeri bir fonksiyonda. Ilgili satirlarda:

```python
from src.infrastructure.persistence.archive_logger import ArchiveLogger

# ... helper icinde:
archive_logger = ArchiveLogger(str(tmp_path / "archive"))

deps = AgentDeps(
    # ... mevcut fields ...
    archive_logger=archive_logger,
    # ...
)
```

Tam yeri bulmak icin: `grep -n "AgentDeps(" tests/unit/orchestration/test_agent.py` ile bulup her cagride archive_logger=... ekle.

- [ ] **Step 4: Tum testleri calistir**

Run: `pytest tests/ -x -q`
Expected: ALL PASS (archive_logger zorunlu field oldu, test AgentDeps'lerde de eklenmeli)

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/agent.py src/orchestration/factory.py tests/unit/orchestration/test_agent.py
git commit -m "feat(orchestration): ArchiveLogger DI AgentDeps'e eklendi (SPEC-009 Task 2)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Exit processor archive entegrasyonu (full + partial exit)

**Files:**
- Modify: `src/orchestration/exit_processor.py`
- Modify: `tests/unit/orchestration/test_exit_processor.py`

- [ ] **Step 1: Test yaz (failing) — full exit archive log'lar**

In `tests/unit/orchestration/test_exit_processor.py`, add new test:

```python
def test_full_exit_writes_to_archive(tmp_path):
    """Full exit → exits.jsonl'e yazilir."""
    from src.infrastructure.persistence.archive_logger import ArchiveLogger
    import json

    # Mevcut test helper'lari ile deps olustur. Archive_logger verilecek.
    archive = ArchiveLogger(str(tmp_path / "archive"))
    deps = _make_deps(tmp_path, archive_logger=archive)  # helper archive_logger parametresi almali

    # Pozisyon ekle, exit tetikle
    pos = _make_position(condition_id="cid1", slug="mlb-bos-nyy-2026-04-19",
                         entry_price=0.60, current_price=0.94,
                         match_score="5-2", match_period="Top 9th")
    deps.state.portfolio.positions["cid1"] = pos

    exit_processor = ExitProcessor(deps)
    exit_processor.run_light()

    exits_file = tmp_path / "archive" / "exits.jsonl"
    assert exits_file.exists()
    lines = exits_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["slug"] == "mlb-bos-nyy-2026-04-19"
    assert data["score_at_exit"] == "5-2"
    assert data["period_at_exit"] == "Top 9th"
    assert data["exit_reason"] == "near_resolve"
```

Not: Bu test mevcut `_make_deps` ve `_make_position` helper'larini kullaniyor. Eger yoksa test file icinde fake deps olusturan daha kisa helper'i referans al.

- [ ] **Step 2: Run test — FAIL**

Run: `pytest tests/unit/orchestration/test_exit_processor.py::test_full_exit_writes_to_archive -v`
Expected: FAIL — exits.jsonl yazilmiyor cunku entegrasyon yok

- [ ] **Step 3: exit_processor.py'de archive call'u ekle**

In `src/orchestration/exit_processor.py`, add import at top:

```python
from src.infrastructure.persistence.archive_logger import (
    ArchiveExitRecord,
    ArchiveLogger,
)
```

Add a helper method inside `ExitProcessor` class (before `_write_fallback_entry`):

```python
def _log_exit_to_archive(
    self, pos: Position, signal: ExitSignal, realized: float,
    exit_price: float, elapsed_pct: float,
) -> None:
    """Exit'i arsive yaz — retrospektif analiz icin (SPEC-009)."""
    archive_logger = getattr(self.deps, "archive_logger", None)
    if archive_logger is None:
        return
    record = ArchiveExitRecord(
        slug=pos.slug,
        condition_id=pos.condition_id,
        event_id=getattr(pos, "event_id", "") or "",
        token_id=pos.token_id,
        sport_tag=pos.sport_tag,
        question=pos.question,
        direction=pos.direction,
        entry_price=pos.entry_price,
        entry_timestamp=str(getattr(pos, "entry_timestamp", "")),
        size_usdc=pos.size_usdc,
        shares=pos.shares,
        confidence=pos.confidence,
        anchor_probability=pos.anchor_probability,
        entry_reason=getattr(pos, "entry_reason", ""),
        exit_price=exit_price,
        exit_pnl_usdc=round(realized, 2),
        exit_reason=signal.reason.value,
        exit_timestamp=datetime.now(timezone.utc).isoformat(),
        partial_exits=list(getattr(pos, "partial_exits", [])),
        score_at_exit=pos.match_score or "",
        period_at_exit=pos.match_period or "",
        elapsed_pct_at_exit=elapsed_pct,
    )
    archive_logger.log_exit(record)
```

Sonra `_execute_exit()` metodunun sonunda (in-memory mutation'dan SONRA, log.info'dan once), archive cagrisini ekle:

Find this section in `_execute_exit()` (after `logger.info("EXIT ...")` on around line 121):

```python
        logger.info("EXIT %s: reason=%s realized=$%.2f detail=%s",
                    pos.slug[:35], signal.reason.value, realized, signal.detail)
```

Add after that, ama EXIT log'undan once — archive'i in-memory mutation'dan ONCE veya SONRA ekleyebilirsin; operasyon sirasina gore: trade_logger (disk) → portfolio mutation → archive. Bu duruma uygun yer:

Refactor `_execute_exit()` to include archive call. Replace the existing `_execute_exit()` with:

```python
    def _execute_exit(self, pos: Position, signal: ExitSignal, elapsed_pct: float = -1.0) -> None:
        """Exit sinyalini execute et — full veya partial.

        Operasyon sirasi: trade_logger (disk) → portfolio mutation (in-memory) → archive.
        Crash durumunda trade_history guncellenmise orphan olusmaz;
        pozisyon hala portfolio'daysa sonraki cycle tekrar exit tetikler.
        """
        if signal.partial:
            self._execute_partial_exit(pos, signal, elapsed_pct)
            return

        self.deps.executor.exit_position(pos, reason=signal.reason.value)
        realized = pos.unrealized_pnl_usdc
        pnl_pct = realized / pos.size_usdc if pos.size_usdc > 0 else 0.0
        exit_price = pos.current_price

        # 1. Disk — trade_logger ONCE
        exit_data = {
            "exit_price": exit_price,
            "exit_reason": signal.reason.value,
            "exit_pnl_usdc": round(realized, 2),
            "exit_pnl_pct": round(pnl_pct, 4),
            "exit_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if not self.deps.trade_logger.update_on_exit(pos.condition_id, exit_data):
            logger.warning("EXIT record missing for %s — writing fallback entry+exit", pos.slug[:35])
            self._write_fallback_entry(pos, exit_data)

        # 2. Archive — SPEC-009 retrospektif analiz
        self._log_exit_to_archive(pos, signal, realized, exit_price, elapsed_pct)

        # 3. In-memory — portfolio mutation SONRA
        self.deps.state.portfolio.remove_position(pos.condition_id, realized_pnl_usdc=realized)
        self.deps.state.circuit_breaker.record_exit(pnl_usd=realized)
        self.deps.cooldown.record_outcome(win=(realized >= 0))

        if self.deps.price_feed is not None:
            self.deps.price_feed.unsubscribe([pos.token_id])

        logger.info("EXIT %s: reason=%s realized=$%.2f detail=%s",
                    pos.slug[:35], signal.reason.value, realized, signal.detail)
```

Also update `_execute_partial_exit()` to accept `elapsed_pct` parameter and call archive. Find current signature:

```python
    def _execute_partial_exit(self, pos: Position, signal: ExitSignal) -> None:
```

Change to:

```python
    def _execute_partial_exit(self, pos: Position, signal: ExitSignal, elapsed_pct: float = -1.0) -> None:
```

At end of `_execute_partial_exit()` (after `logger.info("SCALE-OUT ...")` around line 163), add:

```python
        # Archive — partial exit de arsive yazilir
        self._log_exit_to_archive(pos, signal, realized, pos.current_price, elapsed_pct)
```

Also update `run_light()` to pass `elapsed_pct` when calling `_execute_exit`. Find this block:

```python
            if result.exit_signal is not None:
                self._execute_exit(pos, result.exit_signal)
                exits_processed += 1
```

Change to:

```python
            if result.exit_signal is not None:
                self._execute_exit(pos, result.exit_signal, elapsed_pct=result.elapsed_pct)
                exits_processed += 1
```

- [ ] **Step 4: Run test — PASS bekleniyor**

Run: `pytest tests/unit/orchestration/test_exit_processor.py -v`
Expected: ALL PASS (yeni test + eski testler)

- [ ] **Step 5: Tum testleri calistir**

Run: `pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/orchestration/exit_processor.py tests/unit/orchestration/test_exit_processor.py
git commit -m "feat(exit): archive entegrasyonu - full + partial exit arsive yazilir (SPEC-009 Task 3)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Score enricher — skor degisikligi event'i log'la

**Files:**
- Modify: `src/orchestration/score_enricher.py`
- Modify: `tests/unit/orchestration/test_score_enricher.py`

- [ ] **Step 1: Test yaz (failing)**

In `tests/unit/orchestration/test_score_enricher.py`, add:

```python
def test_score_change_logs_to_archive(tmp_path):
    """Skor degisince score_events.jsonl'e yazilir."""
    import json
    from src.infrastructure.persistence.archive_logger import ArchiveLogger

    archive = ArchiveLogger(str(tmp_path / "archive"))
    # ScoreEnricher helper'i ile olustur — espn mock'layarak
    enricher = ScoreEnricher(
        espn_client=_FakeESPN(  # mevcut helper
            [_mock_espn_score("Red Sox", "Yankees", home_score=1, away_score=0, period="Top 3rd")]
        ),
        odds_client=None,
        archive_logger=archive,
    )

    pos = _make_position(
        slug="mlb-bos-nyy-2026-04-19",
        sport_tag="mlb",
        question="Red Sox vs Yankees",
        direction="BUY_YES",
        match_start_iso=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    )
    pos.event_id = "E1"
    positions = {"cid1": pos}

    # Ilk cagri: skor 1-0 — ilk goruldu, prev_score yok, archive log YOK
    enricher.get_scores_if_due(positions)
    assert not (tmp_path / "archive" / "score_events.jsonl").exists()

    # Skor degisti: 1-0 → 2-0 (home 2, away 0)
    enricher._cached_espn["mlb"] = [
        _mock_espn_score("Red Sox", "Yankees", home_score=2, away_score=0, period="Top 4th")
    ]
    enricher._last_poll_ts = 0  # poll'u tekrar zorla
    enricher.get_scores_if_due(positions)

    events_file = tmp_path / "archive" / "score_events.jsonl"
    assert events_file.exists()
    lines = events_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["prev_score"] == "1-0"
    assert data["new_score"] == "2-0"
    assert data["event_id"] == "E1"


def test_same_score_no_archive_log(tmp_path):
    """Skor degismezse score_events.jsonl'e yazilmaz."""
    from src.infrastructure.persistence.archive_logger import ArchiveLogger

    archive = ArchiveLogger(str(tmp_path / "archive"))
    enricher = ScoreEnricher(
        espn_client=_FakeESPN(
            [_mock_espn_score("Red Sox", "Yankees", home_score=1, away_score=0, period="Top 3rd")]
        ),
        odds_client=None,
        archive_logger=archive,
    )
    pos = _make_position(
        slug="mlb-bos-nyy-2026-04-19", sport_tag="mlb",
        question="Red Sox vs Yankees", direction="BUY_YES",
        match_start_iso=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    )
    pos.event_id = "E1"
    positions = {"cid1": pos}

    enricher.get_scores_if_due(positions)
    enricher._last_poll_ts = 0
    enricher.get_scores_if_due(positions)  # ayni skor
    enricher._last_poll_ts = 0
    enricher.get_scores_if_due(positions)

    # Dosya bile olusmadi
    assert not (tmp_path / "archive" / "score_events.jsonl").exists()
```

Not: `_FakeESPN`, `_mock_espn_score`, `_make_position` helper'lari mevcut test dosyasinda yoksa benzer pattern ile ekle veya mevcut pattern'i kullan.

- [ ] **Step 2: Run test — FAIL**

Run: `pytest tests/unit/orchestration/test_score_enricher.py::test_score_change_logs_to_archive -v`
Expected: FAIL — ScoreEnricher archive_logger parametresi almiyor

- [ ] **Step 3: ScoreEnricher'a archive_logger ekle**

In `src/orchestration/score_enricher.py`:

Add imports at top:

```python
from src.infrastructure.persistence.archive_logger import (
    ArchiveLogger,
    ArchiveScoreEvent,
)
```

Update `__init__` signature (around line 158-172). Replace with:

```python
    def __init__(
        self,
        espn_client=None,
        odds_client=None,
        poll_normal_sec: int = 60,
        poll_critical_sec: int = 30,
        critical_price_threshold: float = 0.35,
        match_window_hours: float = 4.0,
        archive_logger: ArchiveLogger | None = None,
    ) -> None:
        self._espn = espn_client
        self._odds = odds_client
        self._poll_normal_sec = poll_normal_sec
        self._poll_critical_sec = poll_critical_sec
        self._critical_threshold = critical_price_threshold
        self._window_hours = match_window_hours
        self._poll_sec: int = poll_normal_sec
        self._last_poll_ts: float = 0.0
        self._cached_espn: dict[str, list[ESPNMatchScore]] = {}
        self._cached_odds: dict[str, list[MatchScore]] = {}
        self._archive_logger = archive_logger
        # event_id → last known score string (skor degisikligi tespiti icin)
        self._prev_score_by_event: dict[str, str] = {}
```

Update `_match_cached()` (around line 261) to emit score events. Current version:

```python
    def _match_cached(self, positions: dict[str, Position]) -> dict[str, dict]:
        """Cached skor verisiyle pozisyonları eşleştir."""
        result: dict[str, dict] = {}
        for cid, pos in positions.items():
            tag = _normalize(pos.sport_tag)

            # ESPN cache öncelikli
            espn_scores = self._cached_espn.get(tag, [])
            if espn_scores:
                em = _find_espn_match(pos, espn_scores)
                if em:
                    result[cid] = _build_score_info(pos, em)
                    continue

            # Odds API fallback cache
            odds_scores = self._cached_odds.get(tag, [])
            if odds_scores:
                ms = _find_match(pos, odds_scores)
                if ms:
                    result[cid] = _build_score_info(pos, ms)

        return result
```

Replace with:

```python
    def _match_cached(self, positions: dict[str, Position]) -> dict[str, dict]:
        """Cached skor verisiyle pozisyonları eşleştir."""
        result: dict[str, dict] = {}
        for cid, pos in positions.items():
            tag = _normalize(pos.sport_tag)
            matched_score_obj = None

            # ESPN cache öncelikli
            espn_scores = self._cached_espn.get(tag, [])
            if espn_scores:
                em = _find_espn_match(pos, espn_scores)
                if em:
                    result[cid] = _build_score_info(pos, em)
                    matched_score_obj = em

            # Odds API fallback cache (ESPN yoksa)
            if matched_score_obj is None:
                odds_scores = self._cached_odds.get(tag, [])
                if odds_scores:
                    ms = _find_match(pos, odds_scores)
                    if ms:
                        result[cid] = _build_score_info(pos, ms)
                        matched_score_obj = ms

            # Archive: skor degisikligi varsa log'la
            if matched_score_obj is not None:
                self._maybe_log_score_event(pos, matched_score_obj)

        return result

    def _maybe_log_score_event(self, pos: Position, ms) -> None:
        """Skor degisikligini tespit edip archive'a yaz (SPEC-009)."""
        if self._archive_logger is None:
            return
        event_id = getattr(pos, "event_id", "") or ""
        if not event_id:
            return
        home_score = getattr(ms, "home_score", None)
        away_score = getattr(ms, "away_score", None)
        if home_score is None or away_score is None:
            return
        new_score = f"{home_score}-{away_score}"
        prev_score = self._prev_score_by_event.get(event_id, "")
        # Ilk sefer (prev yok) → log atma, sadece kaydet
        if prev_score == "":
            self._prev_score_by_event[event_id] = new_score
            return
        if new_score == prev_score:
            return
        # Degisiklik var → log
        self._archive_logger.log_score_event(ArchiveScoreEvent(
            event_id=event_id,
            slug=pos.slug,
            sport_tag=pos.sport_tag,
            timestamp=datetime.now(timezone.utc).isoformat(),
            prev_score=prev_score,
            new_score=new_score,
            period=getattr(ms, "period", "") or "",
        ))
        self._prev_score_by_event[event_id] = new_score
```

- [ ] **Step 4: factory.py'de score_enricher'a archive_logger gecir**

In `src/orchestration/factory.py`, find the ScoreEnricher construction (around line 132-139). Add `archive_logger=archive_logger`:

```python
        score_enricher = ScoreEnricher(
            espn_client=_ESPNBridge(),
            odds_client=odds,
            poll_normal_sec=cfg.score.poll_normal_sec,
            poll_critical_sec=cfg.score.poll_critical_sec,
            critical_price_threshold=cfg.score.critical_price_threshold,
            match_window_hours=cfg.score.match_window_hours,
            archive_logger=archive_logger,  # YENI
        )
```

- [ ] **Step 5: Run test — PASS**

Run: `pytest tests/unit/orchestration/test_score_enricher.py -v`
Expected: ALL PASS

- [ ] **Step 6: Tum testleri calistir**

Run: `pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add src/orchestration/score_enricher.py src/orchestration/factory.py tests/unit/orchestration/test_score_enricher.py
git commit -m "feat(score): skor degisikligi archive log'lari (SPEC-009 Task 4)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Match result logging (mac tamamlaninca)

**Files:**
- Modify: `src/orchestration/score_enricher.py`
- Modify: `tests/unit/orchestration/test_score_enricher.py`

- [ ] **Step 1: Test yaz (failing)**

In `tests/unit/orchestration/test_score_enricher.py`, add:

```python
def test_match_completion_logs_result(tmp_path):
    """Mac bittiginde match_results.jsonl'e yazilir."""
    import json
    from src.infrastructure.persistence.archive_logger import ArchiveLogger

    archive = ArchiveLogger(str(tmp_path / "archive"))
    enricher = ScoreEnricher(
        espn_client=_FakeESPN(
            # is_completed=True, period="Final"
            [_mock_espn_score("Red Sox", "Yankees", home_score=5, away_score=3,
                              period="Final", is_completed=True)]
        ),
        odds_client=None,
        archive_logger=archive,
    )
    pos = _make_position(
        slug="mlb-bos-nyy-2026-04-19", sport_tag="mlb",
        question="Red Sox vs Yankees", direction="BUY_YES",
        match_start_iso=(datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
    )
    pos.event_id = "E1"
    positions = {"cid1": pos}

    enricher.get_scores_if_due(positions)

    results_file = tmp_path / "archive" / "match_results.jsonl"
    assert results_file.exists()
    lines = results_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["event_id"] == "E1"
    assert data["final_score"] == "5-3"
    assert data["winner_home"] is True


def test_match_result_not_duplicated_on_restart(tmp_path):
    """Startup'ta existing event_id'ler set'e yuklenir, duplicate atilmaz."""
    import json
    from src.infrastructure.persistence.archive_logger import (
        ArchiveLogger, ArchiveMatchResult,
    )

    archive_dir = tmp_path / "archive"
    # Onceden 1 match_result yazmis ol
    archive1 = ArchiveLogger(str(archive_dir))
    archive1.log_match_result(ArchiveMatchResult(
        event_id="E1", slug="a", sport_tag="mlb", final_score="5-3",
        winner_home=True, completed_timestamp="2026-04-19T18:00:00Z",
    ))

    # Yeni enricher instance — startup simulation
    archive2 = ArchiveLogger(str(archive_dir))
    enricher = ScoreEnricher(
        espn_client=_FakeESPN(
            [_mock_espn_score("Red Sox", "Yankees", home_score=5, away_score=3,
                              period="Final", is_completed=True)]
        ),
        odds_client=None,
        archive_logger=archive2,
    )
    enricher._logged_match_event_ids = archive2.load_logged_match_event_ids()

    pos = _make_position(
        slug="mlb-bos-nyy-2026-04-19", sport_tag="mlb",
        question="Red Sox vs Yankees", direction="BUY_YES",
        match_start_iso=(datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
    )
    pos.event_id = "E1"  # zaten log'lanmis
    positions = {"cid1": pos}

    enricher.get_scores_if_due(positions)

    # match_results.jsonl hala 1 satir (duplicate yok)
    results_file = archive_dir / "match_results.jsonl"
    lines = results_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
```

- [ ] **Step 2: Run test — FAIL**

Run: `pytest tests/unit/orchestration/test_score_enricher.py::test_match_completion_logs_result -v`
Expected: FAIL — match_result log'lanmiyor

- [ ] **Step 3: ScoreEnricher'a match_result log'lama ekle**

In `src/orchestration/score_enricher.py`:

Add import at top (where archive_logger imports are):

```python
from src.infrastructure.persistence.archive_logger import (
    ArchiveLogger,
    ArchiveMatchResult,
    ArchiveScoreEvent,
)
```

Update `__init__()` — add `_logged_match_event_ids` init. Find:

```python
        self._archive_logger = archive_logger
        self._prev_score_by_event: dict[str, str] = {}
```

Add below:

```python
        # event_id set'i — daha once match_result log'landi mi? Startup'ta
        # archive'dan yuklenir (duplicate engellemesi).
        self._logged_match_event_ids: set[str] = (
            archive_logger.load_logged_match_event_ids()
            if archive_logger is not None else set()
        )
```

Update `_maybe_log_score_event()` — aslinda ayri bir fonksiyon ekleyelim `_maybe_log_match_result()`. `_match_cached()` icinde `_maybe_log_score_event()` cagrisinin hemen altina `_maybe_log_match_result()` ekle. Replace the call:

```python
            if matched_score_obj is not None:
                self._maybe_log_score_event(pos, matched_score_obj)
```

with:

```python
            if matched_score_obj is not None:
                self._maybe_log_score_event(pos, matched_score_obj)
                self._maybe_log_match_result(pos, matched_score_obj)
```

Add new method below `_maybe_log_score_event()`:

```python
    def _maybe_log_match_result(self, pos: Position, ms) -> None:
        """Mac tamamlandiysa match_result log'la (SPEC-009). Duplicate atma."""
        if self._archive_logger is None:
            return
        is_completed = getattr(ms, "is_completed", False)
        if not is_completed:
            return
        event_id = getattr(pos, "event_id", "") or ""
        if not event_id or event_id in self._logged_match_event_ids:
            return
        home_score = getattr(ms, "home_score", None)
        away_score = getattr(ms, "away_score", None)
        if home_score is None or away_score is None:
            return
        winner_home: bool | None = None
        if home_score > away_score:
            winner_home = True
        elif away_score > home_score:
            winner_home = False
        # esit skor (nadir, draw) → None kalir

        self._archive_logger.log_match_result(ArchiveMatchResult(
            event_id=event_id,
            slug=pos.slug,
            sport_tag=pos.sport_tag,
            final_score=f"{home_score}-{away_score}",
            winner_home=winner_home,
            completed_timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        self._logged_match_event_ids.add(event_id)
```

- [ ] **Step 4: Run test — PASS**

Run: `pytest tests/unit/orchestration/test_score_enricher.py -v`
Expected: ALL PASS

- [ ] **Step 5: Tum testleri calistir**

Run: `pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/orchestration/score_enricher.py tests/unit/orchestration/test_score_enricher.py
git commit -m "feat(score): match_result archive log (mac bitince) (SPEC-009 Task 5)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Dokuman guncellemeleri (CLAUDE.md, TDD.md, PRD.md)

**Files:**
- Modify: `CLAUDE.md` (Restart + Trade Silme)
- Modify: `TDD.md` (§5.8)
- Modify: `PRD.md` (F-madde ekle)

- [ ] **Step 1: CLAUDE.md - Restart Protokolu**

Find this section:
```markdown
## Restart Protokolü

Kullanıcı "restart" dediğinde **her seferinde** sor: **Reload mu Reboot mu?**
- **Reload**: Kod güncellenir, veri korunur
- **Reboot**: Her şey sıfırlanır — **onay zorunlu** (uyarı mesajı göster)

Her ikisi de bot + dashboard'u kapsar. Adımlar: TDD §5.8.
```

Replace with:

```markdown
## Restart Protokolü

Kullanıcı "restart" dediğinde **her seferinde** sor: **Reload mu Reboot mu?**
- **Reload**: Kod güncellenir, veri korunur
- **Reboot**: `logs/` kökündeki aktif state dosyaları sıfırlanır — **onay zorunlu**

**ARCHIVE ASLA SİLİNMEZ**: `logs/archive/` dizini (exits.jsonl, score_events.jsonl,
match_results.jsonl) **reboot'ta dahi dokunulmaz**. Geçmiş trade'lerin retrospektif
analizi için korunur (SPEC-009).

Her ikisi de bot + dashboard'u kapsar. Adımlar: TDD §5.8.
```

- [ ] **Step 2: CLAUDE.md - Trade Silme Protokolu**

Find "Trade Silme / Düzeltme Protokolü" section. In the "Etkilenen Dosyalar" table, add a new row at the bottom:

Before:
```markdown
| 6 | `logs/bot.log` | DEĞİŞTİRME (audit trail). |
```

After:
```markdown
| 6 | `logs/bot.log` | DEĞİŞTİRME (audit trail). |
| 7 | `logs/archive/*.jsonl` | DOKUNMA — exit, score_event ve match_result audit trail olarak korunur (SPEC-009). |
```

- [ ] **Step 3: TDD.md §5.8 guncelle**

Find §5.8 (Restart Protokolleri). At the end of the Reboot section, add:

```markdown
**Archive Koruma (SPEC-009)**:

Reboot aşağıdaki dosyalara ASLA dokunmaz (active logs sıfırlansa bile):
- `logs/archive/exits.jsonl`
- `logs/archive/score_events.jsonl`
- `logs/archive/match_results.jsonl`

Archive retrospektif rule analysis için kullanılır. Reboot sonrası bot yeni
trade'leri bu dosyalara appending devam eder.
```

- [ ] **Step 4: PRD.md F-madde ekle**

Find the "F" features list (F1, F2, ...). Add new feature at the end:

```markdown
### F9: Retrospektif Analiz Arşivi (SPEC-009)

**Amaç**: Kural (scale-out, exit threshold'ları, near_resolve) etkinliğini
geriye dönük veriyle değerlendirmek.

**Ne tutulur**:
- `logs/archive/exits.jsonl` — her exit tam snapshot + o anki skor
- `logs/archive/score_events.jsonl` — maç içindeki her skor değişikliği
- `logs/archive/match_results.jsonl` — maç final result

**Koruma**: Reboot/reload/trade silme archive'a dokunmaz. Append-only.

**Analiz örneği**: "MLB'de 2-1 gerideyken çıktığımız maçların kaçı geri dönüp
kazandı?" sorusu event_id JOIN ile cevaplanabilir.
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md TDD.md PRD.md
git commit -m "docs: SPEC-009 archive sistemi TDD/PRD/CLAUDE.md'ye eklendi

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Final entegrasyon + spec IMPLEMENTED

**Files:**
- Modify: `docs/superpowers/specs/2026-04-19-archive-system-design.md`

- [ ] **Step 1: Tum testleri calistir**

Run: `pytest tests/ -v 2>&1 | tail -10`
Expected: ALL PASS, archive testleri dahil

- [ ] **Step 2: Arch guard dogrulama**

```bash
find src -name "*.py" -not -path "*__pycache__*" -exec wc -l {} + | sort -n | tail -5
```

Expected: `archive_logger.py` < 400 satir. Hicbiri 400+ degil.

```bash
grep -rn "from src.orchestration\|from src.strategy\|from src.presentation" src/domain/ src/infrastructure/ --include="*.py" | grep -v __pycache__
```

Expected: 0 sonuc (katman ihlali yok).

- [ ] **Step 3: Bot'u baslatip dosyalari dogrula**

```bash
python -m src.main --mode dry_run &
sleep 5
ls -la logs/archive/
```

Expected: `logs/archive/` dizini var, bot calisiyor.

- [ ] **Step 4: Spec durumunu IMPLEMENTED yap**

In `docs/superpowers/specs/2026-04-19-archive-system-design.md`, change:
```
> **Durum**: DRAFT
```
to:
```
> **Durum**: IMPLEMENTED
```

- [ ] **Step 5: Final commit**

```bash
git add docs/superpowers/specs/2026-04-19-archive-system-design.md
git commit -m "feat: SPEC-009 archive system tamamlandi

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```
