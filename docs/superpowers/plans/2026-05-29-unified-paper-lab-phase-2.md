# Unified Paper Lab — Phase 2: Paper Realism Executor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fake `_simulate_order` placeholder in `Mode.PAPER` branch with a realistic fill simulator that uses live Polymarket orderbook, applies FOK/GTC strategy parity with live mode, enforces price tick + min order + fees + gas, supports partial fill + stuck position retry. Mode default STAYS `dry_run` — Phase 3 flips default.

**Architecture:**
- New domain module `paper_fill.py` (pure function: walks book, returns FillResult).
- New infra `clob_book.py` (HTTP fetch, 5s LRU cache).
- New infra `paper_executions.py` (JSONL audit writer).
- New orchestration `paper_executor.py` (composition: clob_book → paper_fill → audit → state).
- `executor.py` modified: `Mode.PAPER` branch delegates to `PaperExecutor`; `Mode.DRY_RUN` keeps current behavior.
- `force_close_executor.py` modified: in paper mode, defer to PaperExecutor (no zero-realize).

**Tech Stack:** Python 3.12, pydantic, requests, pytest, JSONL audit.

**Companion design doc:** `docs/superpowers/specs/2026-05-29-unified-paper-lab-design.md` §4.2-4.6, §8 Phase 2.

**Prerequisite (manual before starting):**
- Phase 1 commit merged + user-approved (last commit subject contains "Phase 1").
- `git status` clean.

**ARCH_GUARD self-check before EVERY Edit/Write step (mandatory):**
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."

---

### Task 1: Add PaperConfig to settings.py

**Files:**
- Modify: `src/config/settings.py` (add `PaperConfig` class + `AppConfig.paper` field)

> **ARCH_GUARD self-check** (mandatory before edit).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/config/test_paper_config.py`:

```python
"""PaperConfig dataclass + AppConfig.paper field validation."""
from src.config.settings import AppConfig, PaperConfig


def test_paper_config_defaults() -> None:
    p = PaperConfig()
    assert p.max_buy_slippage_pct == 0.02
    assert p.max_sell_slippage_pct == 0.05
    assert p.min_fill_ratio == 0.95
    assert p.book_cache_ttl_sec == 5
    assert p.max_open_cycles == 6
    assert p.max_stuck_cycles == 12
    assert p.min_order_usdc == 1.0
    assert p.price_tick == 0.01
    assert p.maker_fee_pct == 0.0
    assert p.taker_fee_pct == 0.0
    assert p.polygon_gas_usdc == 0.01


def test_app_config_has_paper_field() -> None:
    cfg = AppConfig()
    assert isinstance(cfg.paper, PaperConfig)
    assert cfg.paper.min_order_usdc == 1.0
```

- [ ] **Step 2: Run test, verify fails with ImportError**

Run:
```bash
pytest tests/unit/config/test_paper_config.py -v 2>&1 | tail -10
```
Expected: ImportError "cannot import name 'PaperConfig'".

- [ ] **Step 3: Add PaperConfig class to settings.py**

In `src/config/settings.py`, insert this class BEFORE the `class AppConfig` line (around line 273):

```python
class PaperConfig(BaseModel):
    """Paper mode realism parameters.

    Real Polymarket behavior (no synthetic latency/rejection):
    - FOK + GTC limit order strategy (parity with live mode)
    - 1¢ price tick rounding (Polymarket constraint)
    - $1 min order (Polymarket constraint)
    - Polygon gas + maker/taker fee modeling
    """
    model_config = ConfigDict(extra="ignore")
    # Slippage tolerance
    max_buy_slippage_pct: float = 0.02
    max_sell_slippage_pct: float = 0.05
    # FOK fill threshold
    min_fill_ratio: float = 0.95
    # Book cache TTL (orderbook freshness)
    book_cache_ttl_sec: int = 5
    # GTC limit order open lifetime (cycles); after, cancelled
    max_open_cycles: int = 6
    # Stuck position alarm threshold (cycles); dashboard surfaces it
    max_stuck_cycles: int = 12
    # Polymarket constraints
    min_order_usdc: float = 1.0
    price_tick: float = 0.01
    # Fee + gas modeling
    maker_fee_pct: float = 0.0
    taker_fee_pct: float = 0.0
    polygon_gas_usdc: float = 0.01
```

- [ ] **Step 4: Add `paper` field to AppConfig**

In `src/config/settings.py`, in `class AppConfig`, after the `mlb_submarket:` line (around line 296), add:

```python
    paper: PaperConfig = Field(default_factory=PaperConfig)
```

- [ ] **Step 5: Run test, verify passes**

Run:
```bash
pytest tests/unit/config/test_paper_config.py -v 2>&1 | tail -10
```
Expected: 2 tests PASS.

- [ ] **Step 6: Verify full pytest still green**

Run:
```bash
pytest -q 2>&1 | tail -3
```
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/config/settings.py tests/unit/config/test_paper_config.py
git commit -m "feat(config): add PaperConfig with real Polymarket constraints

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Add paper block to config.yaml

**Files:**
- Modify: `config.yaml` (add `paper:` block)

> **ARCH_GUARD self-check** (mandatory before edit).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/config/test_paper_yaml_block.py`:

```python
"""Phase 2: config.yaml must declare paper block with real defaults."""
from pathlib import Path

import yaml


def _cfg() -> dict:
    return yaml.safe_load(open("config.yaml", encoding="utf-8")) or {}


def test_paper_block_exists() -> None:
    assert "paper" in _cfg(), "config.yaml must contain `paper:` block"


def test_paper_block_has_required_keys() -> None:
    paper = _cfg()["paper"]
    required = {
        "max_buy_slippage_pct", "max_sell_slippage_pct", "min_fill_ratio",
        "book_cache_ttl_sec", "max_open_cycles", "max_stuck_cycles",
        "min_order_usdc", "price_tick",
        "maker_fee_pct", "taker_fee_pct", "polygon_gas_usdc",
    }
    missing = required - set(paper.keys())
    assert not missing, f"paper block missing keys: {missing}"
```

- [ ] **Step 2: Run, verify fails**

Run: `pytest tests/unit/config/test_paper_yaml_block.py -v 2>&1 | tail -10`
Expected: AssertionError "config.yaml must contain `paper:` block".

- [ ] **Step 3: Add `paper:` block to config.yaml**

In `config.yaml`, at the end of the file (before EOF, after `mlb_submarket:` block), append:

```yaml

paper:
  # 2026-05-29 (unified paper lab Phase 2): real Polymarket fill simulation.
  # No synthetic latency/rejection — bot uses real CLOB orderbook + behavior.
  # Slippage tolerance (caller-side max deviation from target price)
  max_buy_slippage_pct: 0.02     # %2 max for BUY
  max_sell_slippage_pct: 0.05    # %5 max for SELL (more tolerant on exit)
  # FOK fill threshold (below this fraction → REJECTED)
  min_fill_ratio: 0.95           # 95%
  # Orderbook cache
  book_cache_ttl_sec: 5
  # GTC limit order open lifetime
  max_open_cycles: 6             # ~3h with 30-min heavy cycle
  # Stuck position alarm threshold
  max_stuck_cycles: 12           # ~1h before dashboard alarm
  # Polymarket constraints
  min_order_usdc: 1.0
  price_tick: 0.01               # 1¢
  # Fee + gas modeling (known defaults; override if Polymarket adjusts)
  maker_fee_pct: 0.0
  taker_fee_pct: 0.0
  polygon_gas_usdc: 0.01         # ~Polygon gas per order
```

- [ ] **Step 4: Run, verify passes**

Run: `pytest tests/unit/config/test_paper_yaml_block.py -v 2>&1 | tail -10`
Expected: 2 tests PASS.

- [ ] **Step 5: Verify full pytest green**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 6: Commit**

```bash
git add config.yaml tests/unit/config/test_paper_yaml_block.py
git commit -m "feat(config): paper block defaults in config.yaml

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Create `clob_book.py` — orderbook fetch with TTL cache

**Files:**
- Create: `src/infrastructure/apis/clob_book.py`
- Create: `tests/unit/infrastructure/apis/test_clob_book.py`

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: Write the failing test FIRST**

Create `tests/unit/infrastructure/apis/test_clob_book.py`:

```python
"""ClobBook — Polymarket orderbook fetch + TTL cache."""
from unittest.mock import MagicMock

from src.infrastructure.apis.clob_book import ClobBook


def _resp(status: int, payload: dict):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = payload
    m.raise_for_status = MagicMock()
    return m


def _book(asks=None, bids=None) -> dict:
    return {"asks": asks or [], "bids": bids or []}


def test_fetch_returns_parsed_bids_asks() -> None:
    http = MagicMock(return_value=_resp(200, _book(
        asks=[{"price": "0.65", "size": "100"}],
        bids=[{"price": "0.63", "size": "200"}],
    )))
    book = ClobBook(http_get=http, cache_ttl_sec=5)
    out = book.fetch("tok1")
    assert out["asks"] == [{"price": "0.65", "size": "100"}]
    assert out["bids"] == [{"price": "0.63", "size": "200"}]


def test_cache_hit_no_extra_http() -> None:
    http = MagicMock(return_value=_resp(200, _book(asks=[{"price": "0.65", "size": "100"}])))
    book = ClobBook(http_get=http, cache_ttl_sec=60)
    book.fetch("tok1")
    book.fetch("tok1")
    assert http.call_count == 1, "second call must hit cache"


def test_cache_expired_refetches() -> None:
    http = MagicMock(return_value=_resp(200, _book()))
    book = ClobBook(http_get=http, cache_ttl_sec=0)  # immediate expiry
    book.fetch("tok1")
    book.fetch("tok1")
    assert http.call_count == 2, "expired cache must refetch"


def test_http_error_returns_empty_book() -> None:
    http = MagicMock(side_effect=Exception("boom"))
    book = ClobBook(http_get=http, cache_ttl_sec=5)
    out = book.fetch("tok1")
    assert out == {"asks": [], "bids": []}


def test_different_tokens_cached_separately() -> None:
    http = MagicMock(return_value=_resp(200, _book()))
    book = ClobBook(http_get=http, cache_ttl_sec=60)
    book.fetch("tok1")
    book.fetch("tok2")
    assert http.call_count == 2, "different tokens must each fetch"
```

- [ ] **Step 2: Run, verify fails with ImportError**

Run: `pytest tests/unit/infrastructure/apis/test_clob_book.py -v 2>&1 | tail -10`
Expected: ImportError "No module named 'src.infrastructure.apis.clob_book'".

- [ ] **Step 3: Create the module**

Create `src/infrastructure/apis/clob_book.py`:

```python
"""Polymarket CLOB orderbook fetch with TTL cache.

Read-only, no auth, free endpoint. Used by paper mode to simulate fills
against real orderbook state.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

_CLOB_BOOK_URL = "https://clob.polymarket.com/book"
_DEFAULT_TIMEOUT = 10


def _default_http_get(url: str, params: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.get(url, params=params or {}, timeout=timeout)


class ClobBook:
    """Cached orderbook fetch. TTL per token_id."""

    def __init__(
        self,
        http_get: Callable[..., Any] = _default_http_get,
        cache_ttl_sec: int = 5,
    ) -> None:
        self._http = http_get
        self._ttl = cache_ttl_sec
        self._cache: dict[str, tuple[float, dict]] = {}

    def fetch(self, token_id: str) -> dict:
        """Returns {"asks": [{"price": "...", "size": "..."}], "bids": [...]}.

        Empty {"asks": [], "bids": []} on HTTP failure (logged WARNING).
        """
        now = time.time()
        cached = self._cache.get(token_id)
        if cached and (now - cached[0]) < self._ttl:
            return cached[1]
        try:
            resp = self._http(_CLOB_BOOK_URL, params={"token_id": token_id}, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
            book = resp.json() or {}
            normalized = {"asks": book.get("asks") or [], "bids": book.get("bids") or []}
            self._cache[token_id] = (now, normalized)
            return normalized
        except Exception as e:
            logger.warning("clob_book fetch failed for %s: %s", token_id[:16], e)
            return {"asks": [], "bids": []}
```

- [ ] **Step 4: Run tests, verify all pass**

Run: `pytest tests/unit/infrastructure/apis/test_clob_book.py -v 2>&1 | tail -10`
Expected: 5 PASS.

- [ ] **Step 5: Run full pytest**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 6: Commit**

```bash
git add src/infrastructure/apis/clob_book.py tests/unit/infrastructure/apis/test_clob_book.py
git commit -m "feat(infra): ClobBook with TTL cache for paper mode

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Create `paper_fill.py` — pure book walker (domain)

**Files:**
- Create: `src/domain/execution/__init__.py` (empty)
- Create: `src/domain/execution/paper_fill.py`
- Create: `tests/unit/domain/execution/__init__.py` (empty)
- Create: `tests/unit/domain/execution/test_paper_fill.py`

> **ARCH_GUARD self-check** (mandatory). NOTE: domain layer — NO I/O imports.

- [ ] **Step 1: Write the failing test FIRST**

Create `tests/unit/domain/execution/test_paper_fill.py`:

```python
"""paper_fill — pure orderbook walker. Domain layer, no I/O."""
from src.domain.execution.paper_fill import (
    FillResult,
    FillStatus,
    walk_buy,
    walk_sell,
)


def _ask(price: float, size: float) -> dict:
    return {"price": str(price), "size": str(size)}


def _bid(price: float, size: float) -> dict:
    return _ask(price, size)


def test_walk_buy_full_fill_at_target() -> None:
    asks = [_ask(0.65, 100.0)]  # 100 shares @ 0.65 → $65 available
    r = walk_buy(asks, target_price=0.65, target_size_usdc=50.0, max_slippage_pct=0.02, min_fill_ratio=0.95)
    assert r.status == FillStatus.FILLED
    assert r.filled_size_usdc == 50.0
    assert abs(r.weighted_avg_price - 0.65) < 1e-9


def test_walk_buy_partial_through_levels_weighted_avg() -> None:
    asks = [_ask(0.65, 30.0), _ask(0.66, 100.0)]  # $19.50 @ 0.65, then 0.66
    r = walk_buy(asks, target_price=0.66, target_size_usdc=50.0, max_slippage_pct=0.02, min_fill_ratio=0.95)
    assert r.status == FillStatus.FILLED
    assert r.filled_size_usdc == 50.0
    # 30 shares @ 0.65 = $19.50; remaining $30.50 / 0.66 = 46.21 shares
    expected_shares = 30.0 + (50.0 - 30 * 0.65) / 0.66
    assert abs(r.filled_shares - expected_shares) < 1e-6


def test_walk_buy_rejected_when_below_min_fill_ratio() -> None:
    asks = [_ask(0.65, 30.0)]  # only $19.50 available
    r = walk_buy(asks, target_price=0.65, target_size_usdc=100.0, max_slippage_pct=0.02, min_fill_ratio=0.95)
    assert r.status == FillStatus.REJECTED
    assert r.filled_size_usdc == 0.0
    assert "min_fill_ratio" in r.reason


def test_walk_buy_rejected_when_slippage_exceeded() -> None:
    asks = [_ask(0.70, 100.0)]  # 0.70 > 0.65 * 1.02 = 0.663
    r = walk_buy(asks, target_price=0.65, target_size_usdc=50.0, max_slippage_pct=0.02, min_fill_ratio=0.95)
    assert r.status == FillStatus.REJECTED
    assert "slippage" in r.reason or "min_fill_ratio" in r.reason


def test_walk_buy_partial_within_slippage_still_rejected_if_below_min_fill() -> None:
    asks = [_ask(0.65, 20.0), _ask(0.72, 1000.0)]  # 20 shares ok, 2nd > slippage
    r = walk_buy(asks, target_price=0.65, target_size_usdc=100.0, max_slippage_pct=0.02, min_fill_ratio=0.95)
    assert r.status == FillStatus.REJECTED  # only $13 filled, < 95% of $100


def test_walk_buy_empty_asks_rejected() -> None:
    r = walk_buy([], target_price=0.65, target_size_usdc=50.0, max_slippage_pct=0.02, min_fill_ratio=0.95)
    assert r.status == FillStatus.REJECTED
    assert r.filled_size_usdc == 0.0


def test_walk_sell_full_fill() -> None:
    bids = [_bid(0.65, 100.0)]
    r = walk_sell(bids, target_price=0.65, shares=50.0, max_slippage_pct=0.05)
    assert r.status == FillStatus.FILLED
    assert r.filled_shares == 50.0
    assert abs(r.weighted_avg_price - 0.65) < 1e-9


def test_walk_sell_partial_fill_returns_partial() -> None:
    bids = [_bid(0.65, 30.0)]  # only 30 shares of demand
    r = walk_sell(bids, target_price=0.65, shares=100.0, max_slippage_pct=0.05)
    assert r.status == FillStatus.PARTIAL_FILL
    assert r.filled_shares == 30.0


def test_walk_sell_no_bids_rejected() -> None:
    r = walk_sell([], target_price=0.65, shares=50.0, max_slippage_pct=0.05)
    assert r.status == FillStatus.REJECTED
    assert r.filled_shares == 0.0


def test_walk_sell_first_bid_below_slippage_rejected() -> None:
    bids = [_bid(0.30, 1000.0)]  # 0.30 < 0.65 * 0.95 = 0.6175
    r = walk_sell(bids, target_price=0.65, shares=50.0, max_slippage_pct=0.05)
    assert r.status == FillStatus.REJECTED


def test_walk_sell_zero_shares_is_filled_zero() -> None:
    r = walk_sell([_bid(0.65, 100.0)], target_price=0.65, shares=0.0, max_slippage_pct=0.05)
    assert r.status == FillStatus.FILLED
    assert r.filled_shares == 0.0


def test_walk_buy_weighted_avg_multiple_levels() -> None:
    asks = [_ask(0.65, 10.0), _ask(0.66, 10.0), _ask(0.67, 100.0)]
    # 10 @ 0.65 = $6.50, 10 @ 0.66 = $6.60, remaining $36.90 @ 0.67 = 55.07 shares
    r = walk_buy(asks, target_price=0.67, target_size_usdc=50.0, max_slippage_pct=0.05, min_fill_ratio=0.95)
    assert r.status == FillStatus.FILLED
    assert r.filled_size_usdc == 50.0
    total_shares = 10.0 + 10.0 + (50.0 - 6.50 - 6.60) / 0.67
    assert abs(r.filled_shares - total_shares) < 1e-6
    assert abs(r.weighted_avg_price - 50.0 / total_shares) < 1e-6
```

- [ ] **Step 2: Run, verify fails ImportError**

Run: `pytest tests/unit/domain/execution/test_paper_fill.py -v 2>&1 | tail -10`
Expected: ImportError.

- [ ] **Step 3: Create `src/domain/execution/__init__.py`** (empty file)

```python
```

- [ ] **Step 4: Create `tests/unit/domain/execution/__init__.py`** (empty file)

```python
```

- [ ] **Step 5: Create `src/domain/execution/paper_fill.py`**

```python
"""Paper fill walker — pure domain function, no I/O.

Walks orderbook levels under slippage tolerance, returns FillResult.
Caller (paper_executor) handles I/O (fetching the book, persisting state).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FillStatus(str, Enum):
    FILLED = "filled"
    PARTIAL_FILL = "partial_fill"
    REJECTED = "rejected"


@dataclass(frozen=True)
class FillResult:
    status: FillStatus
    filled_shares: float
    filled_size_usdc: float
    weighted_avg_price: float
    reason: str  # short reason tag, empty for FILLED


def _level_price_size(level: dict) -> tuple[float, float]:
    try:
        return float(level.get("price", 0)), float(level.get("size", 0))
    except (TypeError, ValueError):
        return 0.0, 0.0


def walk_buy(
    asks: list[dict],
    target_price: float,
    target_size_usdc: float,
    max_slippage_pct: float,
    min_fill_ratio: float,
) -> FillResult:
    """Walk asks ascending, accumulate fill while price <= target * (1 + slippage).

    REJECTED if filled_usdc < target * min_fill_ratio.
    """
    if not asks or target_size_usdc <= 0:
        return FillResult(FillStatus.REJECTED, 0.0, 0.0, 0.0, "empty_book")

    max_acceptable = target_price * (1.0 + max_slippage_pct)
    filled_shares = 0.0
    filled_usdc = 0.0

    # Polymarket asks are DESC-sorted; best ask = asks[-1]. Walk in ascending price.
    for level in reversed(asks):
        price, size = _level_price_size(level)
        if price <= 0 or size <= 0:
            continue
        if price > max_acceptable:
            break  # slippage exceeded
        level_usdc_available = price * size
        remaining_usdc = target_size_usdc - filled_usdc
        if remaining_usdc <= 0:
            break
        take_usdc = min(level_usdc_available, remaining_usdc)
        take_shares = take_usdc / price
        filled_shares += take_shares
        filled_usdc += take_usdc
        if filled_usdc >= target_size_usdc:
            break

    if filled_usdc < target_size_usdc * min_fill_ratio:
        return FillResult(
            FillStatus.REJECTED, 0.0, 0.0, 0.0,
            f"below_min_fill_ratio_or_slippage (filled=${filled_usdc:.2f}/${target_size_usdc:.2f})",
        )

    wap = filled_usdc / filled_shares if filled_shares > 0 else 0.0
    return FillResult(FillStatus.FILLED, filled_shares, filled_usdc, wap, "")


def walk_sell(
    bids: list[dict],
    target_price: float,
    shares: float,
    max_slippage_pct: float,
) -> FillResult:
    """Walk bids descending, accumulate fill while price >= target * (1 - slippage).

    Returns FILLED (all shares), PARTIAL_FILL (some), or REJECTED (zero).
    Zero shares input → FILLED with 0 (degenerate).
    """
    if shares <= 0:
        return FillResult(FillStatus.FILLED, 0.0, 0.0, 0.0, "")
    if not bids:
        return FillResult(FillStatus.REJECTED, 0.0, 0.0, 0.0, "empty_book")

    min_acceptable = target_price * (1.0 - max_slippage_pct)
    filled_shares = 0.0
    filled_usdc = 0.0

    # Polymarket bids are ASC-sorted; best bid = bids[-1]. Walk in descending price.
    for level in reversed(bids):
        price, size = _level_price_size(level)
        if price <= 0 or size <= 0:
            continue
        if price < min_acceptable:
            break  # slippage exceeded
        remaining_shares = shares - filled_shares
        if remaining_shares <= 0:
            break
        take_shares = min(size, remaining_shares)
        filled_shares += take_shares
        filled_usdc += take_shares * price
        if filled_shares >= shares:
            break

    if filled_shares <= 0:
        return FillResult(FillStatus.REJECTED, 0.0, 0.0, 0.0, "no_bids_above_slippage")
    wap = filled_usdc / filled_shares
    status = FillStatus.FILLED if abs(filled_shares - shares) < 1e-9 else FillStatus.PARTIAL_FILL
    return FillResult(status, filled_shares, filled_usdc, wap, "" if status == FillStatus.FILLED else "partial")
```

- [ ] **Step 6: Run tests, all pass**

Run: `pytest tests/unit/domain/execution/test_paper_fill.py -v 2>&1 | tail -15`
Expected: 12 PASS.

- [ ] **Step 7: Verify domain layer has NO I/O imports**

Run:
```bash
grep -E "^(import|from) (requests|httpx|urllib|socket|open\(|pathlib|os\.path)" src/domain/execution/paper_fill.py
```
Expected: empty (no I/O imports = ARCH_GUARD Rule 2 satisfied).

- [ ] **Step 8: Full pytest green**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 9: Commit**

```bash
git add src/domain/execution/ tests/unit/domain/execution/
git commit -m "feat(domain): paper_fill — pure book walker for FOK/limit fill simulation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Create `paper_executions.py` — JSONL audit writer

**Files:**
- Create: `src/infrastructure/audit/__init__.py` (empty if not exists)
- Create: `src/infrastructure/audit/paper_executions.py`
- Create: `tests/unit/infrastructure/audit/__init__.py` (empty if not exists)
- Create: `tests/unit/infrastructure/audit/test_paper_executions.py`

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: Check if `audit/` dir exists**

Run:
```bash
ls src/infrastructure/audit/ 2>&1
```
If "No such file" → will create.

- [ ] **Step 2: Write the failing test FIRST**

Create `tests/unit/infrastructure/audit/test_paper_executions.py`:

```python
"""PaperExecutionsLogger — JSONL audit append for paper mode fills."""
import json
import tempfile
from pathlib import Path

from src.infrastructure.audit.paper_executions import PaperExecutionsLogger


def test_writes_execution_record_with_book_snapshot() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "exec.jsonl"
        log = PaperExecutionsLogger(p)
        log.write({
            "ts": "2026-05-29T00:00:00Z",
            "token_id": "tok1",
            "side": "BUY",
            "strategy": "market",
            "target_price": 0.65,
            "target_size_usdc": 50.0,
            "result_status": "filled",
            "filled_size_usdc": 50.0,
            "filled_shares": 76.92,
            "weighted_avg_price": 0.65,
            "book_snapshot": {"asks_top3": [{"p": 0.65, "s": 100}], "bids_top3": []},
            "fee_paid": 0.0,
            "gas_paid": 0.01,
        })
        lines = p.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["token_id"] == "tok1"
        assert rec["book_snapshot"]["asks_top3"][0]["p"] == 0.65


def test_appends_not_overwrites() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "exec.jsonl"
        log = PaperExecutionsLogger(p)
        log.write({"ts": "1", "token_id": "a"})
        log.write({"ts": "2", "token_id": "b"})
        assert len(p.read_text(encoding="utf-8").strip().split("\n")) == 2


def test_handles_empty_book_snapshot() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "exec.jsonl"
        log = PaperExecutionsLogger(p)
        log.write({"ts": "1", "token_id": "a", "book_snapshot": {"asks_top3": [], "bids_top3": []}})
        rec = json.loads(p.read_text(encoding="utf-8").strip())
        assert rec["book_snapshot"]["asks_top3"] == []
```

- [ ] **Step 3: Run, verify fails ImportError**

Run: `pytest tests/unit/infrastructure/audit/test_paper_executions.py -v 2>&1 | tail -10`

- [ ] **Step 4: Create dirs if needed**

```bash
mkdir -p src/infrastructure/audit tests/unit/infrastructure/audit
touch src/infrastructure/audit/__init__.py tests/unit/infrastructure/audit/__init__.py
```

- [ ] **Step 5: Create `paper_executions.py`**

```python
"""Paper-mode execution audit — appends one JSONL record per fill decision.

Captures the book snapshot at decision time so post-hoc analysis can verify
the fill decision was correct given the orderbook state.
"""
from __future__ import annotations

import json
from pathlib import Path


class PaperExecutionsLogger:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str))
            f.write("\n")
```

- [ ] **Step 6: Run tests, all 3 pass**

Run: `pytest tests/unit/infrastructure/audit/test_paper_executions.py -v 2>&1 | tail -10`

- [ ] **Step 7: Full pytest green**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 8: Commit**

```bash
git add src/infrastructure/audit/ tests/unit/infrastructure/audit/
git commit -m "feat(infra): PaperExecutionsLogger JSONL audit writer

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Create `paper_executor.py` — orchestration glue

**Files:**
- Create: `src/orchestration/paper_executor.py`
- Create: `tests/integration/test_paper_executor.py`

> **ARCH_GUARD self-check** (mandatory). Orchestration layer — coordinates infra + domain.

- [ ] **Step 1: Write the failing test FIRST**

Create `tests/integration/test_paper_executor.py`:

```python
"""Integration: PaperExecutor end-to-end (book → strategy → fill → audit)."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.config.settings import PaperConfig
from src.orchestration.paper_executor import PaperExecutor


def _book_resp(asks, bids):
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status = MagicMock()
    m.json.return_value = {"asks": asks, "bids": bids}
    return m


def _ask(p, s):
    return {"price": str(p), "size": str(s)}


def _bid(p, s):
    return _ask(p, s)


def test_paper_buy_filled_writes_audit() -> None:
    with tempfile.TemporaryDirectory() as td:
        audit = Path(td) / "exec.jsonl"
        # Polymarket asks DESC sort; best ask at end
        book = _book_resp(asks=[_ask(0.70, 1000), _ask(0.65, 100)], bids=[_bid(0.62, 200)])
        http = MagicMock(return_value=book)
        px = PaperExecutor(
            config=PaperConfig(),
            audit_path=audit,
            http_get=http,
        )
        result = px.place_buy(token_id="tok1", target_price=0.65, target_size_usdc=50.0)
        assert result["status"] == "filled"
        assert result["filled_size_usdc"] == 50.0
        assert audit.exists()
        assert audit.read_text(encoding="utf-8").strip() != ""


def test_paper_buy_below_min_order_rejected() -> None:
    with tempfile.TemporaryDirectory() as td:
        px = PaperExecutor(
            config=PaperConfig(),
            audit_path=Path(td) / "exec.jsonl",
            http_get=MagicMock(return_value=_book_resp([], [])),
        )
        result = px.place_buy(token_id="tok1", target_price=0.65, target_size_usdc=0.5)
        assert result["status"] == "rejected"
        assert "min_order" in result["reason"]


def test_paper_sell_partial_keeps_remaining_shares() -> None:
    with tempfile.TemporaryDirectory() as td:
        # bids ASC sort; best bid at end. Only 30 shares of demand.
        book = _book_resp(asks=[], bids=[_bid(0.65, 30)])
        px = PaperExecutor(
            config=PaperConfig(),
            audit_path=Path(td) / "exec.jsonl",
            http_get=MagicMock(return_value=book),
        )
        result = px.place_sell(token_id="tok1", target_price=0.65, shares=100.0)
        assert result["status"] == "partial_fill"
        assert result["filled_shares"] == 30.0


def test_paper_sell_no_bids_rejected_stuck() -> None:
    with tempfile.TemporaryDirectory() as td:
        px = PaperExecutor(
            config=PaperConfig(),
            audit_path=Path(td) / "exec.jsonl",
            http_get=MagicMock(return_value=_book_resp([], [])),
        )
        result = px.place_sell(token_id="tok1", target_price=0.65, shares=50.0)
        assert result["status"] == "rejected"
        assert result["filled_shares"] == 0.0
```

- [ ] **Step 2: Run, verify ImportError**

Run: `pytest tests/integration/test_paper_executor.py -v 2>&1 | tail -10`

- [ ] **Step 3: Create `src/orchestration/paper_executor.py`**

```python
"""Paper-mode executor — composes ClobBook + paper_fill + audit + fee/gas.

Orchestration layer: coordinates infra (book fetch + audit) and domain
(walk_buy/walk_sell). Returns dict result compatible with Executor.place_order
contract (order_id, status, filled_size_usdc, etc.).
"""
from __future__ import annotations

import datetime
import logging
import uuid
from pathlib import Path
from typing import Any, Callable

from src.config.settings import PaperConfig
from src.domain.execution.paper_fill import FillStatus, walk_buy, walk_sell
from src.infrastructure.apis.clob_book import ClobBook
from src.infrastructure.audit.paper_executions import PaperExecutionsLogger
from src.infrastructure.apis.clob_client import choose_order_strategy

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _top3(levels: list[dict]) -> list[dict]:
    # Polymarket asks DESC / bids ASC. Best at end. Take top 3 best.
    return [{"p": float(l.get("price", 0)), "s": float(l.get("size", 0))} for l in (levels or [])[-3:][::-1]]


class PaperExecutor:
    """Realistic paper fill against live Polymarket orderbook."""

    def __init__(
        self,
        config: PaperConfig,
        audit_path: Path | str = "logs/audit/paper_executions.jsonl",
        http_get: Callable[..., Any] | None = None,
    ) -> None:
        self.cfg = config
        self._book = ClobBook(http_get=http_get, cache_ttl_sec=config.book_cache_ttl_sec) \
            if http_get is not None else ClobBook(cache_ttl_sec=config.book_cache_ttl_sec)
        self._audit = PaperExecutionsLogger(Path(audit_path))

    def place_buy(self, token_id: str, target_price: float, target_size_usdc: float) -> dict:
        target_price = round(target_price, 2)  # 1¢ tick
        if target_size_usdc < self.cfg.min_order_usdc:
            return self._rejected(token_id, "BUY", target_price, target_size_usdc, "below_min_order_usdc", {})
        book = self._book.fetch(token_id)
        strategy = choose_order_strategy(book, "BUY", target_price, target_size_usdc)
        result = walk_buy(
            asks=book.get("asks", []),
            target_price=strategy["price"],
            target_size_usdc=target_size_usdc,
            max_slippage_pct=self.cfg.max_buy_slippage_pct,
            min_fill_ratio=self.cfg.min_fill_ratio,
        )
        return self._record_and_return(
            token_id, "BUY", strategy, target_price, target_size_usdc, result, book,
        )

    def place_sell(self, token_id: str, target_price: float, shares: float) -> dict:
        target_price = round(target_price, 2)
        notional = shares * target_price
        if notional < self.cfg.min_order_usdc:
            return self._rejected(token_id, "SELL", target_price, notional, "below_min_order_usdc", {})
        book = self._book.fetch(token_id)
        strategy = choose_order_strategy(book, "SELL", target_price, notional)
        result = walk_sell(
            bids=book.get("bids", []),
            target_price=strategy["price"],
            shares=shares,
            max_slippage_pct=self.cfg.max_sell_slippage_pct,
        )
        return self._record_and_return(
            token_id, "SELL", strategy, target_price, notional, result, book, shares_in=shares,
        )

    def _record_and_return(
        self, token_id: str, side: str, strategy: dict,
        target_price: float, target_size_usdc: float, result, book: dict,
        shares_in: float | None = None,
    ) -> dict:
        fee = result.filled_size_usdc * (
            self.cfg.taker_fee_pct if strategy.get("strategy") == "market" else self.cfg.maker_fee_pct
        )
        gas = self.cfg.polygon_gas_usdc if result.status != FillStatus.REJECTED else 0.0
        order_id = f"paper_{uuid.uuid4().hex[:8]}"
        rec = {
            "ts": _now_iso(),
            "order_id": order_id,
            "token_id": token_id,
            "side": side,
            "strategy": strategy.get("strategy"),
            "order_type": strategy.get("order_type"),
            "target_price": target_price,
            "strategy_price": strategy.get("price"),
            "target_size_usdc": round(target_size_usdc, 4),
            "result_status": result.status.value,
            "filled_size_usdc": round(result.filled_size_usdc, 4),
            "filled_shares": round(result.filled_shares, 6),
            "weighted_avg_price": round(result.weighted_avg_price, 6),
            "fee_paid": round(fee, 6),
            "gas_paid": round(gas, 6),
            "reason": result.reason,
            "book_snapshot": {
                "asks_top3": _top3(book.get("asks", [])),
                "bids_top3": _top3(book.get("bids", [])),
            },
        }
        if shares_in is not None:
            rec["shares_in"] = shares_in
        self._audit.write(rec)
        return {
            "order_id": order_id,
            "status": result.status.value,
            "mode": "paper",
            "token_id": token_id,
            "side": side,
            "fill_price": result.weighted_avg_price,
            "filled_size_usdc": result.filled_size_usdc,
            "filled_shares": result.filled_shares,
            "fee_paid": fee,
            "gas_paid": gas,
            "reason": result.reason,
        }

    def _rejected(self, token_id: str, side: str, target_price: float, target_size_usdc: float, reason: str, book: dict) -> dict:
        order_id = f"paper_rej_{uuid.uuid4().hex[:8]}"
        rec = {
            "ts": _now_iso(),
            "order_id": order_id,
            "token_id": token_id,
            "side": side,
            "target_price": target_price,
            "target_size_usdc": round(target_size_usdc, 4),
            "result_status": "rejected",
            "filled_size_usdc": 0.0,
            "filled_shares": 0.0,
            "reason": reason,
            "book_snapshot": {
                "asks_top3": _top3(book.get("asks", [])),
                "bids_top3": _top3(book.get("bids", [])),
            },
        }
        self._audit.write(rec)
        return {
            "order_id": order_id,
            "status": "rejected",
            "mode": "paper",
            "token_id": token_id,
            "side": side,
            "reason": reason,
            "filled_size_usdc": 0.0,
            "filled_shares": 0.0,
        }
```

- [ ] **Step 4: Run integration tests**

Run: `pytest tests/integration/test_paper_executor.py -v 2>&1 | tail -15`
Expected: 4 PASS.

- [ ] **Step 5: Check file size <400 lines**

Run: `wc -l src/orchestration/paper_executor.py`
Expected: < 400.

- [ ] **Step 6: Full pytest green**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 7: Commit**

```bash
git add src/orchestration/paper_executor.py tests/integration/test_paper_executor.py
git commit -m "feat(orchestration): PaperExecutor — FOK/GTC strategy + audit + fees

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Wire PaperExecutor into existing `Executor.place_order`

**Files:**
- Modify: `src/infrastructure/executor.py:40-110` (Executor.__init__, place_order, exit_position)
- Modify: `tests/unit/infrastructure/test_executor.py` (or wherever existing executor tests live)

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: Inspect existing executor tests**

Run:
```bash
ls tests/unit/infrastructure/ | grep executor
```
Locate file(s) to extend or create new.

- [ ] **Step 2: Write failing test for Mode.PAPER → PaperExecutor delegation**

Add to (or create) `tests/unit/infrastructure/test_executor_paper_dispatch.py`:

```python
"""Executor must delegate Mode.PAPER to PaperExecutor (not fake _simulate_order)."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.config.settings import Mode, PaperConfig
from src.infrastructure.executor import Executor


def _book_resp(asks, bids):
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status = MagicMock()
    m.json.return_value = {"asks": asks, "bids": bids}
    return m


def test_paper_mode_delegates_to_paper_executor(tmp_path: Path) -> None:
    book = _book_resp(asks=[{"price": "0.65", "size": "200"}], bids=[{"price": "0.62", "size": "100"}])
    http = MagicMock(return_value=book)
    ex = Executor(
        mode=Mode.PAPER,
        http_get=http,
        paper_config=PaperConfig(),
        paper_audit_path=tmp_path / "exec.jsonl",
    )
    result = ex.place_order(token_id="tok1", side="BUY", price=0.65, size_usdc=50.0)
    assert result["mode"] == "paper"
    assert result["status"] == "filled"
    assert (tmp_path / "exec.jsonl").exists()


def test_dry_run_mode_keeps_old_behavior(tmp_path: Path) -> None:
    http = MagicMock(return_value=_book_resp([{"price": "0.65", "size": "1000"}], []))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    result = ex.place_order(token_id="tok1", side="BUY", price=0.65, size_usdc=50.0)
    assert result["mode"] == "dry_run"
    assert result["status"] == "simulated"  # old behavior
```

- [ ] **Step 3: Run, verify fails (current executor uses fake _simulate_order for PAPER)**

Run: `pytest tests/unit/infrastructure/test_executor_paper_dispatch.py -v 2>&1 | tail -10`

- [ ] **Step 4: Modify `src/infrastructure/executor.py`**

Edit imports section (top of file, around line 14):

```python
from src.config.settings import Mode, PaperConfig
from src.orchestration.paper_executor import PaperExecutor
```

Edit `Executor.__init__` (replace lines 40-52):

```python
class Executor:
    def __init__(
        self,
        mode: Mode,
        http_get: Callable[..., Any] = _default_http_get,
        clob_client: Any = None,
        paper_config: PaperConfig | None = None,
        paper_audit_path: Any = "logs/audit/paper_executions.jsonl",
    ) -> None:
        self.mode = mode
        self._http = http_get
        self._clob = clob_client
        if mode == Mode.LIVE and clob_client is None:
            raise ValueError("LIVE mode requires clob_client (ClobOrderClient)")
        self._paper = (
            PaperExecutor(
                config=paper_config or PaperConfig(),
                audit_path=paper_audit_path,
                http_get=http_get,
            )
            if mode == Mode.PAPER else None
        )
```

Edit `Executor.place_order` (find the `if self.mode in (Mode.DRY_RUN, Mode.PAPER):` line):

Replace:
```python
if self.mode in (Mode.DRY_RUN, Mode.PAPER):
    return self._simulate_order(token_id, side, price, size_usdc)
```

With:
```python
if self.mode == Mode.DRY_RUN:
    return self._simulate_order(token_id, side, price, size_usdc)
if self.mode == Mode.PAPER:
    assert self._paper is not None
    return self._paper.place_buy(token_id, price, size_usdc) if side == "BUY" \
        else self._paper.place_sell(token_id, price, size_usdc / price if price > 0 else 0)
```

Edit `Executor.exit_position` similarly:

Replace:
```python
if self.mode in (Mode.DRY_RUN, Mode.PAPER):
    return {
        "order_id": f"sim_exit_{uuid.uuid4().hex[:8]}",
        "status": "simulated",
        "mode": self.mode.value,
        "reason": reason,
    }
```

With:
```python
if self.mode == Mode.DRY_RUN:
    return {
        "order_id": f"sim_exit_{uuid.uuid4().hex[:8]}",
        "status": "simulated",
        "mode": "dry_run",
        "reason": reason,
    }
if self.mode == Mode.PAPER:
    assert self._paper is not None
    token_id = getattr(pos, "token_id", "")
    shares = getattr(pos, "shares", 0)
    bid_price = getattr(pos, "bid_price", None) or getattr(pos, "current_price", 0)
    res = self._paper.place_sell(token_id, target_price=float(bid_price or 0), shares=float(shares))
    return {**res, "reason": reason}
```

- [ ] **Step 5: Run tests, verify pass**

Run: `pytest tests/unit/infrastructure/test_executor_paper_dispatch.py -v 2>&1 | tail -10`
Expected: 2 PASS.

- [ ] **Step 6: Verify dry_run smoke still passes (regression check)**

Run: `pytest -q 2>&1 | tail -3`
Expected: all green.

- [ ] **Step 7: Check executor.py size**

Run: `wc -l src/infrastructure/executor.py`
Expected: < 400.

- [ ] **Step 8: Commit**

```bash
git add src/infrastructure/executor.py tests/unit/infrastructure/test_executor_paper_dispatch.py
git commit -m "feat(infra): Executor delegates Mode.PAPER to PaperExecutor

Mode.DRY_RUN keeps existing fake-fill behavior (test mode).
Mode.PAPER now uses real Polymarket orderbook + FOK/GTC + fees/gas.
Mode.LIVE unchanged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Update `factory.py` to pass paper config

**Files:**
- Modify: `src/orchestration/factory.py:282-294` (`_build_executor` function)

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: Modify `_build_executor`**

Replace the function body (lines 282-294 approximately):

```python
def _build_executor(cfg: AppConfig) -> Executor:
    """Mode dispatch: dry_run → stub; paper → realistic fill; live → CLOB."""
    if cfg.mode == Mode.DRY_RUN:
        return Executor(mode=cfg.mode)
    if cfg.mode == Mode.PAPER:
        return Executor(
            mode=cfg.mode,
            paper_config=cfg.paper,
            paper_audit_path="logs/audit/paper_executions.jsonl",
        )
    # LIVE: py-clob-client runtime wiring
    import os
    from src.infrastructure.apis.clob_client import ClobOrderClient, build_client
    private_key = os.getenv("PRIVATE_KEY", "")
    if not private_key:
        raise RuntimeError("LIVE mode requires PRIVATE_KEY env var")
    raw = build_client(host="https://clob.polymarket.com", chain_id=137, private_key=private_key)
    clob = ClobOrderClient(raw)
    return Executor(mode=cfg.mode, clob_client=clob)
```

- [ ] **Step 2: Full pytest green**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 3: Commit**

```bash
git add src/orchestration/factory.py
git commit -m "feat(orchestration): factory wires PaperConfig to Executor

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Force-close paper-mode awareness

**Files:**
- Modify: `src/orchestration/force_close_executor.py`

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: Inspect current force_close behavior**

Run:
```bash
head -80 src/orchestration/force_close_executor.py
```
Note how it calls `executor.exit_position` and what "bid yoksa 0 realize" path looks like.

- [ ] **Step 2: Identify the zero-realize branch**

Search:
```bash
grep -n "bid\|realize\|0.0\|0\.00" src/orchestration/force_close_executor.py | head -20
```

- [ ] **Step 3: Write failing test**

Create `tests/unit/orchestration/test_force_close_paper_mode.py`:

```python
"""Force-close must NOT zero-realize in paper mode — defer to PaperExecutor stuck logic."""
from unittest.mock import MagicMock

from src.config.settings import Mode


def test_force_close_paper_mode_does_not_zero_realize() -> None:
    """In paper mode, when no bids available, force_close should NOT call
    exit at price=0; instead it should let PaperExecutor's REJECTED status
    propagate so the position becomes 'stuck' (handled by exit_processor)."""
    # This is a behavioral guard test. Implementation: force_close_executor
    # checks executor.mode; if PAPER, uses executor.exit_position result as-is
    # (REJECTED → position stays open). For DRY_RUN/LIVE, current behavior.
    # The exact assertion depends on force_close_executor structure;
    # below is a stub showing intent. Adjust to actual API.

    # Pseudocode (replace with real call):
    # force_closer = ForceCloseExecutor(executor=mock_paper_exec, ...)
    # mock_paper_exec.exit_position.return_value = {"status": "rejected", "mode": "paper"}
    # result = force_closer.try_force_close(stuck_position)
    # assert result["status"] == "rejected"  # stays open, not zero-realized

    # Marker: this test must be implemented after reading force_close_executor.py
    # in Step 2 above. Fill in once API is known.
    assert True, "Placeholder — replace with real assertion in Step 5."
```

- [ ] **Step 4: Read force_close_executor.py fully** and identify which method has the "bid yoksa 0" logic. Look for patterns like:
  - `if not bid` followed by exit at 0
  - `bid_price or 0`
  - Direct exit at `price=0`

Run:
```bash
cat src/orchestration/force_close_executor.py
```

- [ ] **Step 5: Update force_close_executor.py — gate zero-realize behind `executor.mode != Mode.PAPER`**

In the identified zero-realize branch, add a condition:

```python
# Paper mode: do NOT zero-realize. Let PaperExecutor's REJECTED propagate.
# Position remains "stuck" and exit_processor retries next cycle.
from src.config.settings import Mode
if executor.mode == Mode.PAPER:
    # delegate to executor.exit_position; if REJECTED, position stays open
    result = executor.exit_position(position, reason="force_close_timeout")
    return result  # may be {"status": "rejected", ...}
```

(Wrap the existing zero-realize branch in `else:` or `if mode in (DRY_RUN, LIVE):`)

- [ ] **Step 6: Now implement the real test assertion**

Update `tests/unit/orchestration/test_force_close_paper_mode.py` to call the actual `ForceCloseExecutor.try_force_close` (or equivalent method) with a mock `Executor` that has `mode=Mode.PAPER` and returns `{"status": "rejected"}`. Assert the result is `rejected` and no zero-PnL state mutation occurred.

- [ ] **Step 7: Run test**

Run: `pytest tests/unit/orchestration/test_force_close_paper_mode.py -v 2>&1 | tail -10`

- [ ] **Step 8: Full pytest green**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 9: Commit**

```bash
git add src/orchestration/force_close_executor.py tests/unit/orchestration/test_force_close_paper_mode.py
git commit -m "feat(force_close): paper mode skips zero-realize (delegate to PaperExecutor)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Dashboard mode badge

**Files:**
- Modify: `src/presentation/dashboard/static/js/dashboard.js` (add mode badge)
- Modify: `src/presentation/dashboard/static/css/*.css` (badge styles)

> **ARCH_GUARD self-check** (mandatory). Presentation layer, no business logic.

- [ ] **Step 1: Locate existing topbar markup/handler**

Run:
```bash
grep -rn "topbar\|mode\b" src/presentation/dashboard/static/js/dashboard.js | head -20
```

- [ ] **Step 2: Locate bot_status.json mode source**

Run:
```bash
grep -n "mode" src/orchestration/bot_status_writer.py
```
Confirm `mode` is written to `bot_status.json` (if not, add it; the dashboard reads this file via the existing API).

- [ ] **Step 3: Add mode badge to dashboard.js**

Identify where the dashboard renders the topbar (look for `topbar` or `header` selectors). Add a small element:

```javascript
// In the function that updates topbar from bot_status:
function renderModeBadge(mode) {
  const colors = {dry_run: '#dc3545', paper: '#ffc107', live: '#28a745'};
  const labels = {dry_run: 'DRY RUN', paper: 'PAPER', live: 'LIVE'};
  return `<span class="mode-badge" style="background:${colors[mode]||'#666'};padding:4px 10px;border-radius:4px;color:#fff;font-weight:600">${labels[mode]||mode}</span>`;
}
```

Wire into the existing topbar update function.

- [ ] **Step 4: Manual visual check (deferred — Phase 2 smoke covers it)**

Note: dashboard JS testing typically requires a browser. The smoke test in Task 11 visually confirms the badge.

- [ ] **Step 5: Commit**

```bash
git add src/presentation/dashboard/
git commit -m "feat(dashboard): mode badge (dry_run/paper/live)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Phase 2 smoke test — paper mode E2E

**Files:** none (run only).

- [ ] **Step 1: Pre-flight — paper audit file does not exist**

Run:
```bash
rm -f logs/audit/paper_executions.jsonl
ls logs/audit/paper_executions.jsonl 2>&1
```
Expected: "No such file or directory".

- [ ] **Step 2: Run paper mode for one cycle**

Run:
```bash
python -m src.main --once --mode paper 2>&1 | tee logs/runtime/phase2_smoke.log | tail -50
```
Expected: bot starts (mode log line shows `paper`), scanner runs, executor used; no Tracebacks.

- [ ] **Step 3: Verify mode log entry**

Run:
```bash
grep -iE "mode|paper" logs/runtime/phase2_smoke.log | head -10
```
Expected: at least one line confirming `mode=paper`.

- [ ] **Step 4: Verify clob_book was queried**

Run:
```bash
grep -iE "clob_book|polymarket.com/book|fetch" logs/runtime/phase2_smoke.log | head -5
```
Expected: book fetch log lines (if any entry-eligible market exists). If no basketball games in window, file may be empty — that's OK, but check pytest in Step 7.

- [ ] **Step 5: Verify py-clob-client place_order NOT called**

Run:
```bash
grep -iE "place_order|live order placed" logs/runtime/phase2_smoke.log
```
Expected: empty (no live calls in paper mode).

- [ ] **Step 6: Check paper_executions.jsonl created (if any trades)**

Run:
```bash
ls -la logs/audit/paper_executions.jsonl 2>&1 && wc -l logs/audit/paper_executions.jsonl 2>&1
```
Expected: file exists if any entry was evaluated. If 0 lines, no trade happened in this cycle (acceptable; pytest already covers fill logic).

- [ ] **Step 7: Confirm tests still green**

Run: `pytest -q 2>&1 | tail -3`

---

### Task 12: Phase 2 final commit + summary

- [ ] **Step 1: Final git log review**

Run:
```bash
git log --oneline pre-unified-2026-05-29..HEAD
```
Expected: ~10 commits showing each Task's incremental work.

- [ ] **Step 2: Verify no uncommitted changes**

Run: `git status --porcelain`
Expected: empty.

- [ ] **Step 3: Tag Phase 2 completion**

Run:
```bash
git tag -a phase2-paper-executor-2026-05-29 -m "Phase 2 complete: paper realism executor wired. Mode default still dry_run. Phase 3 adds tennis + flips default."
```

---

## Phase 2 Acceptance — User checkpoint

Stop here and ask the user to verify before moving to Phase 3.

Show the user:
1. `git log --oneline pre-unified-2026-05-29..HEAD` — all Phase 2 commits.
2. Output of `pytest -q | tail -3` — all green.
3. `wc -l src/domain/execution/paper_fill.py src/infrastructure/apis/clob_book.py src/orchestration/paper_executor.py` — each < 400.
4. Smoke log path: `logs/runtime/phase2_smoke.log`.

Ask:
> "Phase 2 tamamlandı. Paper mode artık gerçek orderbook + FOK/GTC + fee/gas ile çalışıyor. Mode default hala dry_run (Phase 3'te paper'a çevrilecek). Phase 3'e (tennis migrasyonu + bankroll birleşme + paper default) geçeyim mi?"

If user yes → Phase 3 plan.
If user no → revert with `git reset --hard pre-unified-2026-05-29` (Phase 1 commit lost too — for partial Phase 2 revert use `git reset --hard <phase 1 final commit>`).
