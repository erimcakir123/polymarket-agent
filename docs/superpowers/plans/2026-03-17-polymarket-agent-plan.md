# Polymarket Trading Agent — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated prediction market trading agent that detects edge via AI analysis and executes trades on Polymarket with compound growth.

**Architecture:** Single Python process with 30-min adaptive cycles. Gamma API for market discovery, CLOB API for trading, Claude Sonnet for dual-prompt probability estimation, Half-Kelly position sizing. Modes: dry_run → paper → live.

**Tech Stack:** Python 3.11+, py-clob-client, anthropic, requests, websockets, pydantic, pyyaml, python-dotenv, Flask, feedparser

**Spec:** `docs/superpowers/specs/2026-03-17-polymarket-agent-design.md`
**Skills:** `~/.claude/skills/polymarket-api/`, `~/.claude/skills/ai-signal-engine/`, `~/.claude/skills/trading-risk-manager/`, `~/.claude/skills/polymarket-executor/`

---

## File Map

| File | Responsibility |
|------|---------------|
| `config.yaml` | All tunable parameters |
| `.env.example` | Template for secrets |
| `requirements.txt` | Python dependencies |
| `src/__init__.py` | Package init |
| `src/models.py` | Pydantic data models (MarketData, Position, Trade, Signal, etc.) |
| `src/config.py` | Pydantic config loader from YAML |
| `src/trade_logger.py` | JSONL append-only logging |
| `src/market_scanner.py` | Gamma API market discovery + filtering |
| `src/ai_analyst.py` | Dual-prompt Claude Sonnet probability estimation |
| `src/edge_calculator.py` | Edge detection: AI prob vs market price |
| `src/risk_manager.py` | Half-Kelly sizing, Iron Rules, veto power |
| `src/portfolio.py` | Position tracking, PnL, stop-loss, take-profit |
| `src/wallet.py` | On-chain USDC/MATIC balance, allowances |
| `src/executor.py` | Order execution (dry_run/paper/live) |
| `src/order_manager.py` | Pending order tracking, stale cancellation |
| `src/orderbook_analyzer.py` | Order book depth, slippage estimation |
| `src/news_scanner.py` | RSS headline fetcher, breaking news detection |
| `src/whale_tracker.py` | Large position monitoring via Data API |
| `src/event_cluster.py` | Correlated market grouping |
| `src/cycle_timer.py` | Dynamic cycle interval (10-60 min) |
| `src/liquidity_provider.py` | Idle-mode spread earning |
| `src/performance_tracker.py` | Win rate, edge accuracy, auto-tuning |
| `src/notifier.py` | Telegram bot notifications |
| `src/dashboard.py` | Flask web dashboard |
| `src/main.py` | Entry point, main loop, graceful shutdown |

---

## Task 1: Project Scaffold + Config

**Files:**
- Create: `requirements.txt`, `.env.example`, `.gitignore`, `config.yaml`
- Create: `src/__init__.py`, `src/config.py`, `src/models.py`
- Create: `tests/__init__.py`, `tests/test_config.py`
- Create: `logs/.gitkeep`

- [ ] **Step 1: Create requirements.txt**

```
py-clob-client>=0.15.0
anthropic>=0.39.0
requests>=2.31.0
websockets>=12.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
pyyaml>=6.0.1
python-dotenv>=1.0.0
flask>=3.0.0
feedparser>=6.0.0
httpx>=0.27.0
eth-account>=0.11.0
```

- [ ] **Step 2: Create .gitignore**

```
.env
__pycache__/
*.pyc
logs/*.jsonl
.venv/
*.egg-info/
dist/
```

- [ ] **Step 3: Create .env.example**

```
# Wallet
PRIVATE_KEY=0x_your_private_key_here
SIGNATURE_TYPE=0

# Polymarket API (generated via py-clob-client)
POLY_API_KEY=
POLY_API_SECRET=
POLY_API_PASSPHRASE=

# Optional: proxy wallet for email/browser wallets
PROXY_WALLET_ADDRESS=

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxx

# Telegram (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# NewsAPI (optional)
NEWS_API_KEY=
```

- [ ] **Step 4: Create config.yaml**

```yaml
mode: dry_run  # dry_run | paper | live

cycle:
  default_interval_min: 30
  breaking_news_interval_min: 10
  near_stop_loss_interval_min: 15
  night_interval_min: 60
  night_hours: [0, 1, 2, 3, 4, 5, 6]

scanner:
  min_volume_24h: 50000
  min_liquidity: 5000
  tags: ["politics", "geopolitics"]
  max_markets_per_cycle: 20

ai:
  model: "claude-sonnet-4-20250514"
  max_tokens: 1024
  cache_ttl_min: 15
  cache_invalidate_price_move_pct: 0.05
  batch_size: 5

edge:
  min_edge: 0.06
  confidence_multipliers:
    low: 1.5
    medium: 1.0
    high: 0.75

risk:
  kelly_fraction: 0.50
  max_single_bet_usdc: 75
  max_bet_pct: 0.15
  max_positions: 5
  correlation_cap_pct: 0.30
  stop_loss_pct: 0.30
  take_profit_pct: 0.40
  consecutive_loss_cooldown: 3
  cooldown_cycles: 2
  drawdown_halt_pct: 0.50

whale:
  min_position_usd: 50000
  min_win_rate: 0.55
  signal_weight: 0.15

liquidity_provider:
  enabled: true
  spread_cents: 1
  max_exposure_pct: 0.05
  min_spread_cents: 3
  price_move_cancel_pct: 0.02

orderbook:
  max_slippage_pct: 0.015
  wall_threshold_usd: 5000

notifications:
  telegram_enabled: false
  daily_summary_hour: 21

dashboard:
  host: "127.0.0.1"
  port: 5050

logging:
  trades_file: "logs/trades.jsonl"
  portfolio_file: "logs/portfolio.jsonl"
  performance_file: "logs/performance.jsonl"
```

- [ ] **Step 5: Write test for config loading**

```python
# tests/test_config.py
import pytest
from pathlib import Path

def test_config_loads_from_yaml():
    from src.config import load_config
    config = load_config(Path("config.yaml"))
    assert config.mode == "dry_run"
    assert config.risk.kelly_fraction == 0.50
    assert config.risk.max_single_bet_usdc == 75
    assert config.edge.min_edge == 0.06
    assert config.cycle.default_interval_min == 30

def test_config_rejects_invalid_mode():
    from src.config import AppConfig
    with pytest.raises(Exception):
        AppConfig(mode="yolo")

def test_config_risk_constraints():
    from src.config import load_config
    config = load_config(Path("config.yaml"))
    assert 0 < config.risk.kelly_fraction <= 1.0
    assert config.risk.max_bet_pct <= 1.0
    assert config.risk.stop_loss_pct <= 1.0
```

- [ ] **Step 6: Run tests — expect FAIL**

Run: `cd "C:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent" && python -m pytest tests/test_config.py -v`
Expected: FAIL — `src.config` does not exist yet

- [ ] **Step 7: Implement src/config.py**

```python
"""Pydantic config loader from YAML."""
from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, field_validator


class Mode(str, Enum):
    DRY_RUN = "dry_run"
    PAPER = "paper"
    LIVE = "live"


class CycleConfig(BaseModel):
    default_interval_min: int = 30
    breaking_news_interval_min: int = 10
    near_stop_loss_interval_min: int = 15
    night_interval_min: int = 60
    night_hours: List[int] = [0, 1, 2, 3, 4, 5, 6]


class ScannerConfig(BaseModel):
    min_volume_24h: float = 50_000
    min_liquidity: float = 5_000
    tags: List[str] = ["politics", "geopolitics"]
    max_markets_per_cycle: int = 20


class AIConfig(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024
    cache_ttl_min: int = 15
    cache_invalidate_price_move_pct: float = 0.05
    batch_size: int = 5


class EdgeConfig(BaseModel):
    min_edge: float = 0.06
    confidence_multipliers: dict[str, float] = {
        "low": 1.5, "medium": 1.0, "high": 0.75
    }


class RiskConfig(BaseModel):
    kelly_fraction: float = 0.50
    max_single_bet_usdc: float = 75
    max_bet_pct: float = 0.15
    max_positions: int = 5
    correlation_cap_pct: float = 0.30
    stop_loss_pct: float = 0.30
    take_profit_pct: float = 0.40
    consecutive_loss_cooldown: int = 3
    cooldown_cycles: int = 2
    drawdown_halt_pct: float = 0.50

    @field_validator("kelly_fraction")
    @classmethod
    def kelly_in_range(cls, v: float) -> float:
        if not 0 < v <= 1.0:
            raise ValueError("kelly_fraction must be in (0, 1]")
        return v


class WhaleConfig(BaseModel):
    min_position_usd: float = 50_000
    min_win_rate: float = 0.55
    signal_weight: float = 0.15


class LPConfig(BaseModel):
    enabled: bool = True
    spread_cents: int = 1
    max_exposure_pct: float = 0.05
    min_spread_cents: int = 3
    price_move_cancel_pct: float = 0.02


class OrderBookConfig(BaseModel):
    max_slippage_pct: float = 0.015
    wall_threshold_usd: float = 5_000


class NotificationConfig(BaseModel):
    telegram_enabled: bool = False
    daily_summary_hour: int = 21


class DashboardConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 5050


class LoggingConfig(BaseModel):
    trades_file: str = "logs/trades.jsonl"
    portfolio_file: str = "logs/portfolio.jsonl"
    performance_file: str = "logs/performance.jsonl"


class AppConfig(BaseModel):
    mode: Mode = Mode.DRY_RUN
    cycle: CycleConfig = CycleConfig()
    scanner: ScannerConfig = ScannerConfig()
    ai: AIConfig = AIConfig()
    edge: EdgeConfig = EdgeConfig()
    risk: RiskConfig = RiskConfig()
    whale: WhaleConfig = WhaleConfig()
    liquidity_provider: LPConfig = LPConfig()
    orderbook: OrderBookConfig = OrderBookConfig()
    notifications: NotificationConfig = NotificationConfig()
    dashboard: DashboardConfig = DashboardConfig()
    logging: LoggingConfig = LoggingConfig()


def load_config(path: Path = Path("config.yaml")) -> AppConfig:
    """Load config from YAML file, fall back to defaults if missing."""
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)
    return AppConfig()
```

- [ ] **Step 8: Create src/__init__.py (empty) and logs/.gitkeep**

- [ ] **Step 9: Run tests — expect PASS**

Run: `python -m pytest tests/test_config.py -v`
Expected: 3 PASS

- [ ] **Step 10: Commit**

```bash
git add requirements.txt .gitignore .env.example config.yaml src/__init__.py src/config.py tests/__init__.py tests/test_config.py logs/.gitkeep
git commit -m "feat: project scaffold with config system"
```

---

## Task 2: Pydantic Data Models

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write test for models**

```python
# tests/test_models.py
import pytest
from datetime import datetime, timezone

def test_market_data_creation():
    from src.models import MarketData
    m = MarketData(
        condition_id="0xabc", question="Will X happen?",
        yes_price=0.65, no_price=0.35,
        yes_token_id="tok_yes", no_token_id="tok_no",
        volume_24h=100000, liquidity=20000,
        slug="will-x-happen", tags=["politics"],
        end_date_iso="2026-12-01T00:00:00Z",
    )
    assert m.yes_price + m.no_price == pytest.approx(1.0)
    assert m.condition_id == "0xabc"

def test_position_pnl():
    from src.models import Position
    p = Position(
        condition_id="0xabc", token_id="tok_yes",
        direction="BUY_YES", entry_price=0.50,
        size_usdc=20.0, shares=40.0,
        current_price=0.65, slug="test-market",
    )
    assert p.unrealized_pnl_usdc == pytest.approx(6.0)
    assert p.unrealized_pnl_pct == pytest.approx(0.30)

def test_signal_creation():
    from src.models import Signal, Direction
    s = Signal(
        condition_id="0xabc",
        direction=Direction.BUY_YES,
        ai_probability=0.72,
        market_price=0.60,
        edge=0.12,
        confidence="high",
    )
    assert s.edge == 0.12
    assert s.direction == Direction.BUY_YES

def test_trade_record():
    from src.models import TradeRecord
    t = TradeRecord(
        condition_id="0xabc", slug="test",
        direction="BUY_YES", size_usdc=15.0,
        price=0.55, edge=0.08, confidence="medium",
        mode="dry_run", status="executed",
    )
    assert t.mode == "dry_run"
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_models.py -v`

- [ ] **Step 3: Implement src/models.py**

```python
"""Pydantic data models for the trading agent."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, computed_field


class Direction(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    HOLD = "HOLD"


class MarketData(BaseModel):
    condition_id: str
    question: str
    yes_price: float
    no_price: float
    yes_token_id: str
    no_token_id: str
    volume_24h: float = 0
    liquidity: float = 0
    slug: str = ""
    tags: List[str] = []
    end_date_iso: str = ""
    description: str = ""
    event_id: Optional[str] = None


class Position(BaseModel):
    condition_id: str
    token_id: str
    direction: str
    entry_price: float
    size_usdc: float
    shares: float
    current_price: float
    slug: str = ""
    entry_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    category: str = ""

    @computed_field
    @property
    def current_value(self) -> float:
        return self.shares * self.current_price

    @computed_field
    @property
    def unrealized_pnl_usdc(self) -> float:
        return self.current_value - self.size_usdc

    @computed_field
    @property
    def unrealized_pnl_pct(self) -> float:
        if self.size_usdc == 0:
            return 0.0
        return self.unrealized_pnl_usdc / self.size_usdc


class Signal(BaseModel):
    condition_id: str
    direction: Direction
    ai_probability: float
    market_price: float
    edge: float
    confidence: str  # low | medium | high
    reasoning: str = ""
    whale_boost: float = 0.0


class TradeRecord(BaseModel):
    condition_id: str
    slug: str
    direction: str
    size_usdc: float
    price: float
    edge: float
    confidence: str
    mode: str
    status: str  # executed | rejected | simulated
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reasoning: str = ""
    order_id: Optional[str] = None


class PortfolioSnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    bankroll_usdc: float
    positions_count: int
    unrealized_pnl: float
    high_water_mark: float
    consecutive_losses: int = 0
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_models.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add Pydantic data models"
```

---

## Task 3: Trade Logger

**Files:**
- Create: `src/trade_logger.py`
- Create: `tests/test_trade_logger.py`

- [ ] **Step 1: Write test**

```python
# tests/test_trade_logger.py
import json, tempfile, pytest
from pathlib import Path

def test_log_trade_appends_jsonl(tmp_path):
    from src.trade_logger import TradeLogger
    log_file = tmp_path / "trades.jsonl"
    logger = TradeLogger(str(log_file))
    logger.log({"market": "test", "action": "BUY_YES", "edge": 0.08})
    logger.log({"market": "test2", "action": "HOLD"})
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["market"] == "test"

def test_log_trade_adds_timestamp(tmp_path):
    from src.trade_logger import TradeLogger
    log_file = tmp_path / "trades.jsonl"
    logger = TradeLogger(str(log_file))
    logger.log({"market": "test"})
    record = json.loads(log_file.read_text().strip())
    assert "timestamp" in record

def test_read_recent(tmp_path):
    from src.trade_logger import TradeLogger
    log_file = tmp_path / "trades.jsonl"
    logger = TradeLogger(str(log_file))
    for i in range(10):
        logger.log({"i": i})
    recent = logger.read_recent(3)
    assert len(recent) == 3
    assert recent[-1]["i"] == 9
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/trade_logger.py**

```python
"""Append-only JSONL trade logger."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TradeLogger:
    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, data: dict[str, Any]) -> None:
        data = {**data}  # Don't mutate caller's dict
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def read_recent(self, n: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().split("\n")
        lines = [l for l in lines if l.strip()]
        return [json.loads(l) for l in lines[-n:]]

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().split("\n")
        return [json.loads(l) for l in lines if l.strip()]
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/trade_logger.py tests/test_trade_logger.py
git commit -m "feat: add JSONL trade logger"
```

---

## Task 4: Market Scanner (Gamma API)

**Files:**
- Create: `src/market_scanner.py`
- Create: `tests/test_market_scanner.py`

@polymarket-api skill for Gamma API patterns.

- [ ] **Step 1: Write test with mocked HTTP**

```python
# tests/test_market_scanner.py
import json, pytest
from unittest.mock import patch, MagicMock

SAMPLE_MARKET = {
    "conditionId": "0xabc123",
    "question": "Will Trump win 2028?",
    "slug": "will-trump-win-2028",
    "outcomePrices": json.dumps(["0.62", "0.38"]),
    "outcomes": json.dumps(["Yes", "No"]),
    "clobTokenIds": json.dumps(["tok_yes_1", "tok_no_1"]),
    "volume24hr": "120000",
    "liquidity": "25000",
    "tags": json.dumps([{"label": "politics"}]),
    "endDate": "2028-11-15T00:00:00Z",
    "description": "Resolution based on...",
    "eventId": "evt_001",
}

@patch("src.market_scanner.requests.get")
def test_fetch_markets_parses_gamma_response(mock_get):
    from src.market_scanner import MarketScanner
    from src.config import ScannerConfig
    mock_resp = MagicMock()
    mock_resp.json.return_value = [SAMPLE_MARKET]
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    scanner = MarketScanner(ScannerConfig())
    markets = scanner.fetch()
    assert len(markets) == 1
    assert markets[0].yes_price == pytest.approx(0.62)
    assert markets[0].no_price == pytest.approx(0.38)
    assert markets[0].condition_id == "0xabc123"

@patch("src.market_scanner.requests.get")
def test_fetch_markets_filters_low_volume(mock_get):
    from src.market_scanner import MarketScanner
    from src.config import ScannerConfig
    low_vol = {**SAMPLE_MARKET, "volume24hr": "1000", "liquidity": "500"}
    mock_resp = MagicMock()
    mock_resp.json.return_value = [low_vol]
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    scanner = MarketScanner(ScannerConfig())
    markets = scanner.fetch()
    assert len(markets) == 0

@patch("src.market_scanner.requests.get")
def test_fetch_markets_filters_by_tag(mock_get):
    from src.market_scanner import MarketScanner
    from src.config import ScannerConfig
    crypto = {**SAMPLE_MARKET, "tags": json.dumps([{"label": "crypto"}])}
    mock_resp = MagicMock()
    mock_resp.json.return_value = [crypto]
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    scanner = MarketScanner(ScannerConfig(tags=["politics", "geopolitics"]))
    markets = scanner.fetch()
    assert len(markets) == 0
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/market_scanner.py**

```python
"""Gamma API market discovery and filtering."""
from __future__ import annotations
import json
import logging
from typing import List

import requests

from src.config import ScannerConfig
from src.models import MarketData

logger = logging.getLogger(__name__)

GAMMA_BASE = "https://gamma-api.polymarket.com"


class MarketScanner:
    def __init__(self, config: ScannerConfig) -> None:
        self.config = config

    def fetch(self) -> List[MarketData]:
        params = {
            "active": "true",
            "closed": "false",
            "limit": self.config.max_markets_per_cycle,
            "order": "volume24hr",
            "ascending": "false",
        }
        try:
            resp = requests.get(f"{GAMMA_BASE}/markets", params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error("Gamma API error: %s", e)
            return []

        result: List[MarketData] = []
        for raw in resp.json():
            market = self._parse_market(raw)
            if market and self._passes_filters(market):
                result.append(market)
        return result

    def _parse_market(self, raw: dict) -> MarketData | None:
        try:
            prices = json.loads(raw.get("outcomePrices", '["0.5","0.5"]'))
            tokens = json.loads(raw.get("clobTokenIds", '["",""]'))
            tags_raw = json.loads(raw.get("tags", "[]"))
            tag_labels = [t.get("label", "") for t in tags_raw if isinstance(t, dict)]

            return MarketData(
                condition_id=raw.get("conditionId", ""),
                question=raw.get("question", ""),
                yes_price=float(prices[0]),
                no_price=float(prices[1]),
                yes_token_id=tokens[0],
                no_token_id=tokens[1],
                volume_24h=float(raw.get("volume24hr", 0) or 0),
                liquidity=float(raw.get("liquidity", 0) or 0),
                slug=raw.get("slug", ""),
                tags=tag_labels,
                end_date_iso=raw.get("endDate", ""),
                description=raw.get("description", ""),
                event_id=raw.get("eventId"),
            )
        except (json.JSONDecodeError, IndexError, ValueError) as e:
            logger.warning("Failed to parse market: %s", e)
            return None

    def _passes_filters(self, market: MarketData) -> bool:
        if market.volume_24h < self.config.min_volume_24h:
            return False
        if market.liquidity < self.config.min_liquidity:
            return False
        if self.config.tags:
            if not any(t in self.config.tags for t in market.tags):
                return False
        return True
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/market_scanner.py tests/test_market_scanner.py
git commit -m "feat: add Gamma API market scanner"
```

---

## Task 5: Edge Calculator

**Files:**
- Create: `src/edge_calculator.py`
- Create: `tests/test_edge_calculator.py`

@ai-signal-engine skill for edge calculation patterns.

- [ ] **Step 1: Write test**

```python
# tests/test_edge_calculator.py
import pytest

def test_buy_yes_when_ai_higher():
    from src.edge_calculator import calculate_edge
    from src.models import Direction
    direction, edge = calculate_edge(0.72, 0.60, min_edge=0.06, confidence="medium")
    assert direction == Direction.BUY_YES
    assert edge == pytest.approx(0.12)

def test_buy_no_when_ai_lower():
    from src.edge_calculator import calculate_edge
    from src.models import Direction
    direction, edge = calculate_edge(0.30, 0.55, min_edge=0.06, confidence="medium")
    assert direction == Direction.BUY_NO
    assert edge == pytest.approx(0.25)

def test_hold_when_no_edge():
    from src.edge_calculator import calculate_edge
    from src.models import Direction
    direction, edge = calculate_edge(0.52, 0.50, min_edge=0.06, confidence="medium")
    assert direction == Direction.HOLD

def test_high_confidence_lower_threshold():
    from src.edge_calculator import calculate_edge
    from src.models import Direction
    direction, _ = calculate_edge(0.55, 0.50, min_edge=0.06, confidence="high")
    assert direction == Direction.BUY_YES  # 5% > 4.5% threshold

def test_low_confidence_higher_threshold():
    from src.edge_calculator import calculate_edge
    from src.models import Direction
    direction, _ = calculate_edge(0.57, 0.50, min_edge=0.06, confidence="low")
    assert direction == Direction.HOLD  # 7% < 9% threshold

def test_whale_signal_blending():
    from src.edge_calculator import calculate_edge_with_whale
    from src.models import Direction
    direction, edge = calculate_edge_with_whale(
        ai_prob=0.60, market_price=0.50, min_edge=0.06,
        confidence="medium", whale_prob=0.70, whale_weight=0.15
    )
    # blended = 0.60 * 0.85 + 0.70 * 0.15 = 0.615
    assert direction == Direction.BUY_YES
    assert edge == pytest.approx(0.115)
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/edge_calculator.py**

```python
"""Edge detection: AI probability vs market price."""
from __future__ import annotations
from src.models import Direction

CONFIDENCE_MULTIPLIERS = {"low": 1.5, "medium": 1.0, "high": 0.75}


def calculate_edge(
    ai_prob: float,
    market_yes_price: float,
    min_edge: float = 0.06,
    confidence: str = "medium",
) -> tuple[Direction, float]:
    multiplier = CONFIDENCE_MULTIPLIERS.get(confidence, 1.0)
    threshold = min_edge * multiplier
    raw = ai_prob - market_yes_price

    if raw > threshold:
        return Direction.BUY_YES, raw
    elif raw < -threshold:
        return Direction.BUY_NO, abs(raw)
    else:
        return Direction.HOLD, abs(raw)


def calculate_edge_with_whale(
    ai_prob: float,
    market_price: float,
    min_edge: float = 0.06,
    confidence: str = "medium",
    whale_prob: float | None = None,
    whale_weight: float = 0.15,
) -> tuple[Direction, float]:
    if whale_prob is not None:
        blended = ai_prob * (1 - whale_weight) + whale_prob * whale_weight
    else:
        blended = ai_prob
    return calculate_edge(blended, market_price, min_edge, confidence)
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/edge_calculator.py tests/test_edge_calculator.py
git commit -m "feat: add edge calculator with whale blending"
```

---

## Task 6: Risk Manager

**Files:**
- Create: `src/risk_manager.py`
- Create: `tests/test_risk_manager.py`

@trading-risk-manager skill for Kelly and Iron Rules.

- [ ] **Step 1: Write test**

```python
# tests/test_risk_manager.py
import pytest

def test_kelly_basic():
    from src.risk_manager import kelly_position_size
    bet = kelly_position_size(ai_prob=0.70, market_price=0.55, bankroll=100.0)
    assert 0 < bet <= 15.0  # max 15% of 100

def test_kelly_caps_at_max_usdc():
    from src.risk_manager import kelly_position_size
    bet = kelly_position_size(ai_prob=0.90, market_price=0.50, bankroll=10000.0)
    assert bet <= 75.0  # max_single_bet_usdc

def test_kelly_caps_at_max_pct():
    from src.risk_manager import kelly_position_size
    bet = kelly_position_size(ai_prob=0.90, market_price=0.50, bankroll=200.0)
    assert bet <= 30.0  # 15% of 200

def test_kelly_returns_zero_no_edge():
    from src.risk_manager import kelly_position_size
    bet = kelly_position_size(ai_prob=0.50, market_price=0.55, bankroll=100.0)
    assert bet == 0.0

def test_kelly_buy_no():
    from src.risk_manager import kelly_position_size
    bet = kelly_position_size(ai_prob=0.30, market_price=0.55, bankroll=100.0, direction="BUY_NO")
    assert bet > 0  # AI says NO is underpriced

def test_risk_manager_vetoes_max_positions():
    from src.risk_manager import RiskManager
    from src.config import RiskConfig
    from src.models import Signal, Direction
    rm = RiskManager(RiskConfig(max_positions=2))
    open_positions = {"m1": {}, "m2": {}}
    signal = Signal(condition_id="m3", direction=Direction.BUY_YES,
                    ai_probability=0.75, market_price=0.60, edge=0.15, confidence="high")
    result = rm.evaluate(signal, bankroll=100.0, open_positions=open_positions)
    assert result.approved is False
    assert "max_positions" in result.reason

def test_risk_manager_cooldown():
    from src.risk_manager import RiskManager
    from src.config import RiskConfig
    from src.models import Signal, Direction
    rm = RiskManager(RiskConfig())
    rm.consecutive_losses = 3
    signal = Signal(condition_id="m1", direction=Direction.BUY_YES,
                    ai_probability=0.75, market_price=0.60, edge=0.15, confidence="high")
    result = rm.evaluate(signal, bankroll=100.0, open_positions={})
    assert result.approved is False
    assert "cooldown" in result.reason.lower()
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/risk_manager.py**

```python
"""Half-Kelly position sizing and risk gatekeeper."""
from __future__ import annotations
import logging
from dataclasses import dataclass

from src.config import RiskConfig
from src.models import Signal

logger = logging.getLogger(__name__)


def kelly_position_size(
    ai_prob: float,
    market_price: float,
    bankroll: float,
    kelly_fraction: float = 0.50,
    max_bet_usdc: float = 75,
    max_bet_pct: float = 0.15,
    direction: str = "BUY_YES",
) -> float:
    if direction == "BUY_YES":
        p, cost = ai_prob, market_price
    else:
        p, cost = 1 - ai_prob, 1 - market_price

    if cost <= 0 or cost >= 1:
        return 0.0

    q = 1 - p
    b = (1 - cost) / cost
    if b <= 0:
        return 0.0

    full_kelly = max(0, (p * b - q) / b)
    actual = full_kelly * kelly_fraction
    bet = min(bankroll * actual, max_bet_usdc, bankroll * max_bet_pct, bankroll)
    return max(0, round(bet, 2))


@dataclass
class RiskDecision:
    approved: bool
    size_usdc: float
    reason: str


class RiskManager:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config
        self.consecutive_losses: int = 0
        self.cooldown_remaining: int = 0

    def evaluate(
        self,
        signal: Signal,
        bankroll: float,
        open_positions: dict,
        correlated_exposure: float = 0.0,
    ) -> RiskDecision:
        # Cooldown check
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1
            return RiskDecision(False, 0, "Cooldown active after consecutive losses")

        if self.consecutive_losses >= self.config.consecutive_loss_cooldown:
            self.cooldown_remaining = self.config.cooldown_cycles
            self.consecutive_losses = 0
            return RiskDecision(False, 0, "Cooldown triggered: consecutive losses")

        # Max positions
        if len(open_positions) >= self.config.max_positions:
            return RiskDecision(False, 0, f"max_positions reached ({self.config.max_positions})")

        # Already in this market
        if signal.condition_id in open_positions:
            return RiskDecision(False, 0, "Already have position in this market")

        # Correlation cap
        if correlated_exposure >= self.config.correlation_cap_pct:
            return RiskDecision(False, 0, "Correlation cap exceeded")

        # Kelly sizing
        size = kelly_position_size(
            ai_prob=signal.ai_probability,
            market_price=signal.market_price,
            bankroll=bankroll,
            kelly_fraction=self.config.kelly_fraction,
            max_bet_usdc=self.config.max_single_bet_usdc,
            max_bet_pct=self.config.max_bet_pct,
            direction=signal.direction.value,
        )

        if size < 5.0:  # Polymarket min order
            return RiskDecision(False, 0, f"Kelly size too small: ${size:.2f}")

        return RiskDecision(True, size, f"Approved: ${size:.2f} via half-Kelly")

    def record_outcome(self, win: bool) -> None:
        if win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.config.consecutive_loss_cooldown:
                self.cooldown_remaining = self.config.cooldown_cycles
                logger.warning("Cooldown triggered: %d consecutive losses", self.consecutive_losses)
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/risk_manager.py tests/test_risk_manager.py
git commit -m "feat: add risk manager with Kelly sizing and veto logic"
```

---

## Task 7: Portfolio Tracker

**Files:**
- Create: `src/portfolio.py`
- Create: `tests/test_portfolio.py`

- [ ] **Step 1: Write test**

```python
# tests/test_portfolio.py
import pytest

def test_add_position():
    from src.portfolio import Portfolio
    pf = Portfolio()
    pf.add_position("0xabc", "tok_yes", "BUY_YES", 0.55, 20.0, 36.36, "test-market")
    assert "0xabc" in pf.positions
    assert pf.positions["0xabc"].entry_price == 0.55

def test_stop_loss_triggered():
    from src.portfolio import Portfolio
    pf = Portfolio()
    pf.add_position("0xabc", "tok_yes", "BUY_YES", 0.50, 20.0, 40.0, "test")
    pf.update_price("0xabc", 0.30)  # 60% loss > 30% threshold
    stops = pf.check_stop_losses(stop_loss_pct=0.30)
    assert "0xabc" in stops

def test_take_profit_triggered():
    from src.portfolio import Portfolio
    pf = Portfolio()
    pf.add_position("0xabc", "tok_yes", "BUY_YES", 0.50, 20.0, 40.0, "test")
    pf.update_price("0xabc", 0.80)  # 60% gain > 40% threshold
    takes = pf.check_take_profits(take_profit_pct=0.40)
    assert "0xabc" in takes

def test_high_water_mark():
    from src.portfolio import Portfolio
    pf = Portfolio(initial_bankroll=100.0)
    pf.update_bankroll(150.0)
    assert pf.high_water_mark == 150.0
    pf.update_bankroll(120.0)
    assert pf.high_water_mark == 150.0  # doesn't decrease

def test_drawdown_breaker():
    from src.portfolio import Portfolio
    pf = Portfolio(initial_bankroll=100.0)
    pf.update_bankroll(200.0)  # HWM = 200
    pf.update_bankroll(90.0)   # 55% drawdown
    assert pf.is_drawdown_breaker_active(halt_pct=0.50)
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/portfolio.py**

```python
"""Position tracking, PnL, stop-loss, take-profit, drawdown breaker."""
from __future__ import annotations
import logging
from typing import Dict, List

from src.models import Position

logger = logging.getLogger(__name__)


class Portfolio:
    def __init__(self, initial_bankroll: float = 0.0) -> None:
        self.positions: Dict[str, Position] = {}
        self.bankroll: float = initial_bankroll
        self.high_water_mark: float = initial_bankroll

    def add_position(
        self,
        condition_id: str,
        token_id: str,
        direction: str,
        entry_price: float,
        size_usdc: float,
        shares: float,
        slug: str = "",
        category: str = "",
    ) -> None:
        self.positions[condition_id] = Position(
            condition_id=condition_id,
            token_id=token_id,
            direction=direction,
            entry_price=entry_price,
            size_usdc=size_usdc,
            shares=shares,
            current_price=entry_price,
            slug=slug,
            category=category,
        )

    def remove_position(self, condition_id: str) -> Position | None:
        return self.positions.pop(condition_id, None)

    def update_price(self, condition_id: str, new_price: float) -> None:
        if condition_id in self.positions:
            self.positions[condition_id].current_price = new_price

    def update_bankroll(self, new_bankroll: float) -> None:
        self.bankroll = new_bankroll
        if new_bankroll > self.high_water_mark:
            self.high_water_mark = new_bankroll

    def check_stop_losses(self, stop_loss_pct: float = 0.30) -> List[str]:
        triggered = []
        for cid, pos in self.positions.items():
            if pos.unrealized_pnl_pct < -stop_loss_pct:
                triggered.append(cid)
                logger.warning("Stop-loss triggered for %s: %.1f%%", pos.slug, pos.unrealized_pnl_pct * 100)
        return triggered

    def check_take_profits(self, take_profit_pct: float = 0.40) -> List[str]:
        triggered = []
        for cid, pos in self.positions.items():
            if pos.unrealized_pnl_pct > take_profit_pct:
                triggered.append(cid)
                logger.info("Take-profit triggered for %s: %.1f%%", pos.slug, pos.unrealized_pnl_pct * 100)
        return triggered

    def is_drawdown_breaker_active(self, halt_pct: float = 0.50) -> bool:
        if self.high_water_mark <= 0:
            return False
        return self.bankroll < self.high_water_mark * (1 - halt_pct)

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl_usdc for p in self.positions.values())

    def correlated_exposure(self, category: str) -> float:
        if self.bankroll <= 0:
            return 0.0
        cat_total = sum(p.size_usdc for p in self.positions.values() if p.category == category)
        return cat_total / self.bankroll
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/portfolio.py tests/test_portfolio.py
git commit -m "feat: add portfolio tracker with stop-loss and drawdown breaker"
```

---

## Task 8: AI Analyst (Dual-Prompt)

**Files:**
- Create: `src/ai_analyst.py`
- Create: `tests/test_ai_analyst.py`

@ai-signal-engine skill for Claude API patterns.

- [ ] **Step 1: Write test with mocked Claude API**

```python
# tests/test_ai_analyst.py
import json, pytest
from unittest.mock import patch, MagicMock
from src.models import MarketData

SAMPLE_MARKET = MarketData(
    condition_id="0xabc", question="Will X happen?",
    yes_price=0.60, no_price=0.40,
    yes_token_id="t1", no_token_id="t2",
    volume_24h=100000, liquidity=20000, slug="will-x-happen",
)

def _mock_claude_response(prob: float, confidence: str = "medium"):
    resp = MagicMock()
    resp.content = [MagicMock()]
    resp.content[0].text = json.dumps({
        "probability": prob, "confidence": confidence,
        "reasoning": "test reasoning",
        "key_evidence_for": ["a"], "key_evidence_against": ["b"],
    })
    return resp

@patch("src.ai_analyst.anthropic.Anthropic")
def test_dual_prompt_averages(mock_cls):
    from src.ai_analyst import AIAnalyst
    from src.config import AIConfig
    client = MagicMock()
    mock_cls.return_value = client
    # Call A (pro) returns 0.70, Call B (con) returns 0.60
    client.messages.create.side_effect = [
        _mock_claude_response(0.70, "high"),
        _mock_claude_response(0.60, "medium"),
    ]
    analyst = AIAnalyst(AIConfig())
    result = analyst.analyze_market(SAMPLE_MARKET)
    assert 0.60 <= result.ai_probability <= 0.70
    assert result.confidence in ("low", "medium", "high")

@patch("src.ai_analyst.anthropic.Anthropic")
def test_batch_analysis(mock_cls):
    from src.ai_analyst import AIAnalyst
    from src.config import AIConfig
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        _mock_claude_response(0.65), _mock_claude_response(0.55),
        _mock_claude_response(0.80), _mock_claude_response(0.70),
    ]
    analyst = AIAnalyst(AIConfig(batch_size=5))
    results = analyst.analyze_batch([SAMPLE_MARKET, SAMPLE_MARKET])
    assert len(results) == 2
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/ai_analyst.py**

```python
"""Dual-prompt Claude Sonnet probability estimation."""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Dict

import anthropic

from src.config import AIConfig
from src.models import MarketData

logger = logging.getLogger(__name__)

PRO_SYSTEM = """You are an expert superforecaster arguing FOR this outcome.
Estimate the probability that this market resolves YES. Be thorough.
Start with base rate, update with evidence. Account for time remaining.
Respond with ONLY JSON: {"probability": 0.XX, "confidence": "low|medium|high",
"reasoning": "...", "key_evidence_for": [...], "key_evidence_against": [...]}"""

CON_SYSTEM = """You are an expert superforecaster arguing AGAINST this outcome.
Estimate the probability that this market resolves YES. Be thorough.
Focus on why it might NOT happen. Be skeptical.
Respond with ONLY JSON: {"probability": 0.XX, "confidence": "low|medium|high",
"reasoning": "...", "key_evidence_for": [...], "key_evidence_against": [...]}"""


@dataclass
class AIEstimate:
    ai_probability: float
    confidence: str
    reasoning_pro: str
    reasoning_con: str


class AIAnalyst:
    def __init__(self, config: AIConfig) -> None:
        self.config = config
        self.client = anthropic.Anthropic()
        self._cache: Dict[str, tuple[AIEstimate, float, float]] = {}

    def analyze_market(
        self, market: MarketData, news_context: str = ""
    ) -> AIEstimate:
        # Check cache
        cached = self._cache.get(market.condition_id)
        if cached:
            estimate, cached_time, cached_price = cached
            age_min = (time.time() - cached_time) / 60
            price_move = abs(market.yes_price - cached_price)
            if age_min < self.config.cache_ttl_min and price_move < self.config.cache_invalidate_price_move_pct:
                return estimate

        prompt = self._build_prompt(market, news_context)

        # Dual calls
        pro_result = self._call_claude(PRO_SYSTEM, prompt)
        con_result = self._call_claude(CON_SYSTEM, prompt)

        if pro_result is None or con_result is None:
            return AIEstimate(ai_probability=market.yes_price, confidence="low",
                              reasoning_pro="API error", reasoning_con="API error")

        # Weighted average (equal weight for now)
        avg_prob = (pro_result["probability"] + con_result["probability"]) / 2
        avg_prob = max(0.01, min(0.99, avg_prob))

        # Conservative confidence: take the lower one
        conf_order = {"low": 0, "medium": 1, "high": 2}
        pro_conf = conf_order.get(pro_result.get("confidence", "medium"), 1)
        con_conf = conf_order.get(con_result.get("confidence", "medium"), 1)
        conf_map = {0: "low", 1: "medium", 2: "high"}
        final_conf = conf_map[min(pro_conf, con_conf)]

        estimate = AIEstimate(
            ai_probability=round(avg_prob, 3),
            confidence=final_conf,
            reasoning_pro=pro_result.get("reasoning", ""),
            reasoning_con=con_result.get("reasoning", ""),
        )

        self._cache[market.condition_id] = (estimate, time.time(), market.yes_price)
        return estimate

    def analyze_batch(
        self, markets: List[MarketData], news_context: str = ""
    ) -> List[AIEstimate]:
        return [self.analyze_market(m, news_context) for m in markets[:self.config.batch_size]]

    def invalidate_cache(self, condition_id: str) -> None:
        self._cache.pop(condition_id, None)

    def _build_prompt(self, market: MarketData, news_context: str) -> str:
        parts = [
            f"Question: {market.question}",
            f"Description: {market.description}" if market.description else "",
            f"Current YES price: ${market.yes_price:.2f}",
            f"Resolution date: {market.end_date_iso}" if market.end_date_iso else "",
        ]
        if news_context:
            parts.append(f"\nRecent news:\n{news_context}")
        return "\n".join(p for p in parts if p)

    def _call_claude(self, system: str, prompt: str) -> Optional[dict]:
        try:
            resp = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception as e:
            logger.error("Claude API error: %s", e)
            return None
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/ai_analyst.py tests/test_ai_analyst.py
git commit -m "feat: add dual-prompt AI analyst with caching"
```

---

## Task 9: Executor + Order Manager

**Files:**
- Create: `src/executor.py`, `src/order_manager.py`
- Create: `tests/test_executor.py`

@polymarket-executor skill for order patterns.

- [ ] **Step 1: Write test**

```python
# tests/test_executor.py
import pytest
from unittest.mock import MagicMock

def test_dry_run_never_places_real_orders():
    from src.executor import Executor
    from src.config import Mode
    executor = Executor(mode=Mode.DRY_RUN, clob_client=None)
    result = executor.place_order("tok_yes", "BUY", 0.55, 20.0)
    assert result["status"] == "simulated"
    assert result["mode"] == "dry_run"

def test_paper_mode_simulates():
    from src.executor import Executor
    from src.config import Mode
    executor = Executor(mode=Mode.PAPER, clob_client=None)
    result = executor.place_order("tok_yes", "BUY", 0.55, 20.0)
    assert result["status"] == "simulated"
    assert result["mode"] == "paper"

def test_live_mode_requires_client():
    from src.executor import Executor
    from src.config import Mode
    with pytest.raises(ValueError, match="CLOB client required"):
        Executor(mode=Mode.LIVE, clob_client=None)

def test_order_manager_tracks_pending():
    from src.order_manager import OrderManager
    om = OrderManager(stale_after_cycles=2)
    om.add_pending("order_1", "0xabc", "BUY_YES", 0.55, 20.0)
    assert len(om.pending_orders) == 1
    om.tick_cycle()
    om.tick_cycle()
    stale = om.get_stale_orders()
    assert "order_1" in [o["order_id"] for o in stale]
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/executor.py**

```python
"""Order execution: dry_run, paper, live modes."""
from __future__ import annotations
import logging
import uuid
from typing import Any, Optional

from src.config import Mode

logger = logging.getLogger(__name__)


class Executor:
    def __init__(self, mode: Mode, clob_client: Any = None) -> None:
        self.mode = mode
        self.client = clob_client
        if mode == Mode.LIVE and clob_client is None:
            raise ValueError("CLOB client required for live mode")

    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size_usdc: float,
        order_type: str = "GTC",
    ) -> dict:
        if self.mode in (Mode.DRY_RUN, Mode.PAPER):
            order_id = f"sim_{uuid.uuid4().hex[:8]}"
            logger.info("[%s] Simulated %s %s @ $%.2f, size=$%.2f",
                        self.mode.value, side, token_id[:8], price, size_usdc)
            return {
                "order_id": order_id,
                "status": "simulated",
                "mode": self.mode.value,
                "token_id": token_id,
                "side": side,
                "price": price,
                "size_usdc": size_usdc,
            }

        # Live mode
        return self._execute_live(token_id, side, price, size_usdc, order_type)

    def place_exit_order(self, token_id: str, shares: float) -> dict:
        if self.mode in (Mode.DRY_RUN, Mode.PAPER):
            return {
                "order_id": f"sim_exit_{uuid.uuid4().hex[:8]}",
                "status": "simulated",
                "mode": self.mode.value,
            }
        return self._execute_live_exit(token_id, shares)

    def _execute_live(
        self, token_id: str, side: str, price: float, size_usdc: float, order_type: str
    ) -> dict:
        from py_clob_client.clob_types import OrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY, SELL

        clob_side = BUY if side == "BUY" else SELL
        shares = size_usdc / price
        order_args = OrderArgs(token_id=token_id, price=price, size=shares, side=clob_side)
        signed = self.client.create_order(order_args)
        ot = {"GTC": OrderType.GTC, "FOK": OrderType.FOK}.get(order_type, OrderType.GTC)
        resp = self.client.post_order(signed, ot)
        logger.info("Live order placed: %s", resp)
        return {"order_id": resp.get("orderID", ""), "status": "placed", "mode": "live", "response": resp}

    def _execute_live_exit(self, token_id: str, shares: float) -> dict:
        from py_clob_client.clob_types import MarketOrderArgs, OrderType
        from py_clob_client.order_builder.constants import SELL

        mo = MarketOrderArgs(token_id=token_id, amount=shares, side=SELL)
        signed = self.client.create_market_order(mo)
        resp = self.client.post_order(signed, OrderType.FOK)
        return {"order_id": resp.get("orderID", ""), "status": "placed", "mode": "live", "response": resp}
```

- [ ] **Step 4: Implement src/order_manager.py**

```python
"""Pending order tracking and stale order cancellation."""
from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class OrderManager:
    def __init__(self, stale_after_cycles: int = 2) -> None:
        self.stale_after_cycles = stale_after_cycles
        self.pending_orders: Dict[str, dict] = {}

    def add_pending(
        self, order_id: str, condition_id: str, direction: str, price: float, size: float
    ) -> None:
        self.pending_orders[order_id] = {
            "order_id": order_id,
            "condition_id": condition_id,
            "direction": direction,
            "price": price,
            "size": size,
            "cycles_waiting": 0,
        }

    def tick_cycle(self) -> None:
        for order in self.pending_orders.values():
            order["cycles_waiting"] += 1

    def get_stale_orders(self) -> List[dict]:
        return [o for o in self.pending_orders.values()
                if o["cycles_waiting"] >= self.stale_after_cycles]

    def remove_order(self, order_id: str) -> None:
        self.pending_orders.pop(order_id, None)

    def cancel_stale(self, executor: Any) -> List[str]:
        cancelled = []
        for order in self.get_stale_orders():
            oid = order["order_id"]
            logger.info("Cancelling stale order: %s", oid)
            self.remove_order(oid)
            cancelled.append(oid)
        return cancelled
```

- [ ] **Step 5: Run tests — expect PASS**

- [ ] **Step 6: Commit**

```bash
git add src/executor.py src/order_manager.py tests/test_executor.py
git commit -m "feat: add executor (dry/paper/live) and order manager"
```

---

## Task 10: Wallet Module

**Files:**
- Create: `src/wallet.py`
- Create: `tests/test_wallet.py`

- [ ] **Step 1: Write test**

```python
# tests/test_wallet.py
import pytest
from unittest.mock import patch, MagicMock

@patch("src.wallet.requests.post")
def test_get_usdc_balance(mock_post):
    from src.wallet import Wallet
    mock_resp = MagicMock()
    # USDC has 6 decimals, 60 USDC = 60_000_000
    mock_resp.json.return_value = {"result": hex(60_000_000)}
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp
    w = Wallet(private_key="0x" + "a" * 64, rpc_url="https://polygon-rpc.com")
    balance = w.get_usdc_balance()
    assert balance == pytest.approx(60.0)

def test_wallet_requires_private_key():
    from src.wallet import Wallet
    with pytest.raises(ValueError):
        Wallet(private_key="", rpc_url="https://polygon-rpc.com")
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/wallet.py**

```python
"""On-chain USDC/MATIC balance and allowance checks on Polygon."""
from __future__ import annotations
import logging

import requests

logger = logging.getLogger(__name__)

USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_DECIMALS = 6
DEFAULT_RPC = "https://polygon-rpc.com"


class Wallet:
    def __init__(self, private_key: str, rpc_url: str = DEFAULT_RPC) -> None:
        if not private_key:
            raise ValueError("Private key is required")
        self.private_key = private_key
        self.rpc_url = rpc_url
        # Derive address from private key
        try:
            from eth_account import Account
            self.address = Account.from_key(private_key).address
        except ImportError:
            # Fallback: address must be provided separately
            self.address = ""

    def get_usdc_balance(self) -> float:
        """Get USDC balance on Polygon via RPC."""
        # balanceOf(address) selector = 0x70a08231
        addr_padded = self.address.lower().replace("0x", "").zfill(64)
        data = f"0x70a08231{addr_padded}"
        payload = {
            "jsonrpc": "2.0", "method": "eth_call",
            "params": [{"to": USDC_ADDRESS, "data": data}, "latest"],
            "id": 1,
        }
        try:
            resp = requests.post(self.rpc_url, json=payload, timeout=10)
            resp.raise_for_status()
            raw = int(resp.json()["result"], 16)
            return raw / (10 ** USDC_DECIMALS)
        except Exception as e:
            logger.error("Failed to get USDC balance: %s", e)
            return 0.0

    def get_matic_balance(self) -> float:
        """Get MATIC balance for gas."""
        payload = {
            "jsonrpc": "2.0", "method": "eth_getBalance",
            "params": [self.address, "latest"],
            "id": 1,
        }
        try:
            resp = requests.post(self.rpc_url, json=payload, timeout=10)
            resp.raise_for_status()
            raw = int(resp.json()["result"], 16)
            return raw / (10 ** 18)
        except Exception as e:
            logger.error("Failed to get MATIC balance: %s", e)
            return 0.0
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/wallet.py tests/test_wallet.py
git commit -m "feat: add wallet module for on-chain balance checks"
```

---

## Task 11: Order Book Analyzer

**Files:**
- Create: `src/orderbook_analyzer.py`
- Create: `tests/test_orderbook_analyzer.py`

- [ ] **Step 1: Write test**

```python
# tests/test_orderbook_analyzer.py
import pytest

def test_estimate_slippage():
    from src.orderbook_analyzer import OrderBookAnalyzer
    # Simulated order book: bids at 0.55 ($3000), 0.54 ($2000)
    book = {
        "bids": [
            {"price": "0.55", "size": "5454.5"},  # ~$3000
            {"price": "0.54", "size": "3703.7"},   # ~$2000
        ],
        "asks": [
            {"price": "0.56", "size": "3571.4"},   # ~$2000
            {"price": "0.57", "size": "5263.2"},   # ~$3000
        ],
    }
    analyzer = OrderBookAnalyzer(wall_threshold_usd=5000)
    result = analyzer.analyze(book, side="BUY", size_usdc=20.0)
    assert result["estimated_avg_price"] > 0
    assert "slippage_pct" in result

def test_detect_walls():
    from src.orderbook_analyzer import OrderBookAnalyzer
    book = {
        "bids": [{"price": "0.50", "size": "20000"}],  # $10K wall
        "asks": [{"price": "0.55", "size": "100"}],
    }
    analyzer = OrderBookAnalyzer(wall_threshold_usd=5000)
    walls = analyzer.detect_walls(book)
    assert len(walls["bid_walls"]) == 1
    assert walls["bid_walls"][0]["price"] == 0.50
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/orderbook_analyzer.py**

```python
"""Order book depth analysis and slippage estimation."""
from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class OrderBookAnalyzer:
    def __init__(self, wall_threshold_usd: float = 5000, max_slippage_pct: float = 0.015) -> None:
        self.wall_threshold = wall_threshold_usd
        self.max_slippage = max_slippage_pct

    def analyze(self, book: Dict[str, Any], side: str, size_usdc: float) -> Dict[str, Any]:
        levels = book.get("asks" if side == "BUY" else "bids", [])
        if not levels:
            return {"estimated_avg_price": 0, "slippage_pct": 1.0, "executable": False}

        remaining = size_usdc
        total_shares = 0.0
        total_cost = 0.0

        for level in levels:
            price = float(level["price"])
            shares_available = float(level["size"])
            level_cost = shares_available * price

            if remaining <= level_cost:
                shares_bought = remaining / price
                total_shares += shares_bought
                total_cost += remaining
                remaining = 0
                break
            else:
                total_shares += shares_available
                total_cost += level_cost
                remaining -= level_cost

        if total_shares == 0:
            return {"estimated_avg_price": 0, "slippage_pct": 1.0, "executable": False}

        avg_price = total_cost / total_shares
        best_price = float(levels[0]["price"])
        slippage = abs(avg_price - best_price) / best_price if best_price > 0 else 0

        return {
            "estimated_avg_price": round(avg_price, 4),
            "slippage_pct": round(slippage, 4),
            "executable": remaining == 0 and slippage <= self.max_slippage,
            "unfilled_usdc": round(remaining, 2),
        }

    def detect_walls(self, book: Dict[str, Any]) -> Dict[str, List[dict]]:
        result: Dict[str, List[dict]] = {"bid_walls": [], "ask_walls": []}
        for side_key, wall_key in [("bids", "bid_walls"), ("asks", "ask_walls")]:
            for level in book.get(side_key, []):
                price = float(level["price"])
                size = float(level["size"])
                value = price * size
                if value >= self.wall_threshold:
                    result[wall_key].append({"price": price, "size": size, "value_usd": round(value, 2)})
        return result
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/orderbook_analyzer.py tests/test_orderbook_analyzer.py
git commit -m "feat: add order book analyzer with slippage estimation"
```

---

## Task 12: News Scanner

**Files:**
- Create: `src/news_scanner.py`
- Create: `tests/test_news_scanner.py`

- [ ] **Step 1: Write test**

```python
# tests/test_news_scanner.py
import pytest
from unittest.mock import patch, MagicMock

def test_match_headlines_to_markets():
    from src.news_scanner import NewsScanner
    scanner = NewsScanner()
    headlines = [
        {"title": "Trump announces new trade policy", "published": "2026-03-17"},
        {"title": "Weather forecast for tomorrow", "published": "2026-03-17"},
    ]
    market_keywords = {"0xabc": ["trump", "election", "republican"]}
    matches = scanner.match_headlines(headlines, market_keywords)
    assert "0xabc" in matches
    assert len(matches["0xabc"]) == 1
    assert "Trump" in matches["0xabc"][0]["title"]

def test_no_match_returns_empty():
    from src.news_scanner import NewsScanner
    scanner = NewsScanner()
    headlines = [{"title": "Cat video goes viral", "published": "2026-03-17"}]
    market_keywords = {"0xabc": ["trump", "election"]}
    matches = scanner.match_headlines(headlines, market_keywords)
    assert len(matches.get("0xabc", [])) == 0

def test_breaking_news_detection():
    from src.news_scanner import NewsScanner
    scanner = NewsScanner()
    headlines = [
        {"title": "BREAKING: Major political event unfolds", "published": "2026-03-17"},
    ]
    market_keywords = {"0xabc": ["political", "event"]}
    matches = scanner.match_headlines(headlines, market_keywords)
    assert matches["0xabc"][0].get("is_breaking", False)
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/news_scanner.py**

```python
"""RSS headline fetcher and breaking news detection."""
from __future__ import annotations
import logging
import re
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZ4ZERBU0FtVnVHZ0pWVXlnQVAB",  # US politics
    "https://feeds.reuters.com/reuters/politicsNews",
]

BREAKING_PATTERNS = re.compile(r"\b(BREAKING|URGENT|JUST IN|FLASH)\b", re.IGNORECASE)


class NewsScanner:
    def __init__(self, feeds: Optional[List[str]] = None) -> None:
        self.feeds = feeds or RSS_FEEDS
        self._cache: List[dict] = []
        self._last_fetch: float = 0
        self._cache_ttl: float = 1800  # 30 min

    def fetch_headlines(self, max_per_feed: int = 10) -> List[dict]:
        now = time.time()
        if self._cache and (now - self._last_fetch) < self._cache_ttl:
            return self._cache

        headlines: List[dict] = []
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser not installed, skipping RSS")
            return []

        for url in self.feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_per_feed]:
                    headlines.append({
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "summary": entry.get("summary", "")[:200],
                    })
            except Exception as e:
                logger.warning("Failed to fetch feed %s: %s", url, e)

        self._cache = headlines
        self._last_fetch = now
        return headlines

    def match_headlines(
        self,
        headlines: List[dict],
        market_keywords: Dict[str, List[str]],
    ) -> Dict[str, List[dict]]:
        matches: Dict[str, List[dict]] = {}
        for cid, keywords in market_keywords.items():
            for h in headlines:
                title_lower = h["title"].lower()
                if any(kw.lower() in title_lower for kw in keywords):
                    entry = {**h, "is_breaking": bool(BREAKING_PATTERNS.search(h["title"]))}
                    matches.setdefault(cid, []).append(entry)
        return matches

    def build_news_context(self, headlines: List[dict], max_headlines: int = 5) -> str:
        if not headlines:
            return ""
        lines = [f"- {h['title']}" for h in headlines[:max_headlines]]
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/news_scanner.py tests/test_news_scanner.py
git commit -m "feat: add news scanner with RSS and breaking news detection"
```

---

## Task 13: Whale Tracker

**Files:**
- Create: `src/whale_tracker.py`
- Create: `tests/test_whale_tracker.py`

- [ ] **Step 1: Write test**

```python
# tests/test_whale_tracker.py
import pytest
from unittest.mock import patch, MagicMock

@patch("src.whale_tracker.requests.get")
def test_detect_whale_positions(mock_get):
    from src.whale_tracker import WhaleTracker
    from src.config import WhaleConfig
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"proxyWallet": "0xwhale1", "conditionId": "0xabc",
         "size": "60000", "outcome": "Yes", "currentValue": "65000"},
    ]
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    tracker = WhaleTracker(WhaleConfig(min_position_usd=50000))
    whales = tracker.check_market("0xabc")
    assert len(whales) == 1
    assert whales[0]["direction"] == "YES"

def test_whale_signal_computation():
    from src.whale_tracker import WhaleTracker
    from src.config import WhaleConfig
    tracker = WhaleTracker(WhaleConfig())
    signal = tracker.compute_signal([
        {"direction": "YES", "size_usd": 80000},
        {"direction": "YES", "size_usd": 60000},
    ])
    assert signal > 0.5  # Whales bullish
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/whale_tracker.py**

```python
"""Large position monitoring via Polymarket Data API."""
from __future__ import annotations
import logging
from typing import Dict, List, Optional

import requests

from src.config import WhaleConfig

logger = logging.getLogger(__name__)

DATA_API_BASE = "https://data-api.polymarket.com"


class WhaleTracker:
    def __init__(self, config: WhaleConfig) -> None:
        self.config = config
        self._whale_history: Dict[str, List[dict]] = {}

    def check_market(self, condition_id: str) -> List[dict]:
        try:
            resp = requests.get(
                f"{DATA_API_BASE}/positions",
                params={"market": condition_id, "sizeThreshold": self.config.min_position_usd},
                timeout=10,
            )
            resp.raise_for_status()
            positions = resp.json()
        except Exception as e:
            logger.warning("Whale tracker API error: %s", e)
            return []

        whales = []
        for pos in positions:
            size = float(pos.get("size", 0))
            if size >= self.config.min_position_usd:
                whales.append({
                    "address": pos.get("proxyWallet", ""),
                    "direction": pos.get("outcome", "").upper(),
                    "size_usd": size,
                    "condition_id": condition_id,
                })
        return whales

    def compute_signal(self, whale_positions: List[dict]) -> Optional[float]:
        if not whale_positions:
            return None
        yes_total = sum(w["size_usd"] for w in whale_positions if w.get("direction") == "YES")
        no_total = sum(w["size_usd"] for w in whale_positions if w.get("direction") == "NO")
        total = yes_total + no_total
        if total == 0:
            return None
        return yes_total / total  # 0.0 = all NO, 1.0 = all YES
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/whale_tracker.py tests/test_whale_tracker.py
git commit -m "feat: add whale tracker for large position monitoring"
```

---

## Task 14: Event Cluster + Cycle Timer

**Files:**
- Create: `src/event_cluster.py`, `src/cycle_timer.py`
- Create: `tests/test_event_cluster.py`, `tests/test_cycle_timer.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_event_cluster.py
import pytest
from src.models import MarketData

def test_cluster_groups_by_event_id():
    from src.event_cluster import EventCluster
    markets = [
        MarketData(condition_id="m1", question="Trump wins?", yes_price=0.60, no_price=0.40,
                   yes_token_id="t1", no_token_id="t2", event_id="evt1", slug="m1"),
        MarketData(condition_id="m2", question="Republicans win House?", yes_price=0.55, no_price=0.45,
                   yes_token_id="t3", no_token_id="t4", event_id="evt1", slug="m2"),
        MarketData(condition_id="m3", question="Fed cuts rates?", yes_price=0.40, no_price=0.60,
                   yes_token_id="t5", no_token_id="t6", event_id="evt2", slug="m3"),
    ]
    ec = EventCluster()
    clusters = ec.group(markets)
    assert "evt1" in clusters
    assert len(clusters["evt1"]) == 2
    assert len(clusters["evt2"]) == 1

def test_arbitrage_detection():
    from src.event_cluster import EventCluster
    markets = [
        MarketData(condition_id="m1", question="A wins", yes_price=0.60, no_price=0.40,
                   yes_token_id="t1", no_token_id="t2", event_id="evt1", slug="m1"),
        MarketData(condition_id="m2", question="B wins", yes_price=0.50, no_price=0.50,
                   yes_token_id="t3", no_token_id="t4", event_id="evt1", slug="m2"),
    ]
    ec = EventCluster()
    arb = ec.check_arbitrage(markets)
    # Sum = 1.10 > 1.05 → arbitrage
    assert arb["sum_yes"] == pytest.approx(1.10)
    assert arb["is_arbitrage"] is True
```

```python
# tests/test_cycle_timer.py
import pytest

def test_default_interval():
    from src.cycle_timer import CycleTimer
    from src.config import CycleConfig
    timer = CycleTimer(CycleConfig())
    assert timer.get_interval() == 30

def test_breaking_news_shortens():
    from src.cycle_timer import CycleTimer
    from src.config import CycleConfig
    timer = CycleTimer(CycleConfig())
    timer.signal_breaking_news()
    assert timer.get_interval() == 10

def test_near_stop_loss_shortens():
    from src.cycle_timer import CycleTimer
    from src.config import CycleConfig
    timer = CycleTimer(CycleConfig())
    timer.signal_near_stop_loss()
    assert timer.get_interval() == 15

def test_night_mode_extends():
    from src.cycle_timer import CycleTimer
    from src.config import CycleConfig
    timer = CycleTimer(CycleConfig(night_hours=[0,1,2,3,4,5,6]))
    timer.signal_night_mode(current_hour=3)
    assert timer.get_interval() == 60
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/event_cluster.py**

```python
"""Correlated market grouping by event_id."""
from __future__ import annotations
import logging
from typing import Dict, List

from src.models import MarketData

logger = logging.getLogger(__name__)


class EventCluster:
    def group(self, markets: List[MarketData]) -> Dict[str, List[MarketData]]:
        clusters: Dict[str, List[MarketData]] = {}
        for m in markets:
            if m.event_id:
                clusters.setdefault(m.event_id, []).append(m)
        return clusters

    def check_arbitrage(
        self, cluster_markets: List[MarketData], threshold: float = 0.05
    ) -> dict:
        sum_yes = sum(m.yes_price for m in cluster_markets)
        return {
            "sum_yes": round(sum_yes, 4),
            "is_arbitrage": abs(sum_yes - 1.0) > threshold,
            "direction": "SELL" if sum_yes > 1.0 + threshold else "BUY" if sum_yes < 1.0 - threshold else "NONE",
            "markets": [m.slug for m in cluster_markets],
        }
```

- [ ] **Step 4: Implement src/cycle_timer.py**

```python
"""Dynamic cycle interval based on market conditions."""
from __future__ import annotations
import logging

from src.config import CycleConfig

logger = logging.getLogger(__name__)


class CycleTimer:
    def __init__(self, config: CycleConfig) -> None:
        self.config = config
        self._override: int | None = None
        self._override_cycles: int = 0

    def get_interval(self) -> int:
        if self._override and self._override_cycles > 0:
            return self._override
        return self.config.default_interval_min

    def signal_breaking_news(self, duration_cycles: int = 3) -> None:
        self._override = self.config.breaking_news_interval_min
        self._override_cycles = duration_cycles
        logger.info("Cycle shortened to %d min (breaking news)", self._override)

    def signal_near_stop_loss(self, duration_cycles: int = 2) -> None:
        current = self.get_interval()
        target = self.config.near_stop_loss_interval_min
        if target < current:
            self._override = target
            self._override_cycles = duration_cycles
            logger.info("Cycle shortened to %d min (near stop-loss)", target)

    def signal_night_mode(self, current_hour: int) -> None:
        if current_hour in self.config.night_hours:
            self._override = self.config.night_interval_min
            self._override_cycles = 1
            logger.info("Cycle extended to %d min (night mode)", self._override)

    def tick(self) -> None:
        if self._override_cycles > 0:
            self._override_cycles -= 1
            if self._override_cycles == 0:
                self._override = None
                logger.info("Cycle interval returned to default %d min", self.config.default_interval_min)
```

- [ ] **Step 5: Run tests — expect PASS**

- [ ] **Step 6: Commit**

```bash
git add src/event_cluster.py src/cycle_timer.py tests/test_event_cluster.py tests/test_cycle_timer.py
git commit -m "feat: add event clustering and dynamic cycle timer"
```

---

## Task 15: Liquidity Provider

**Files:**
- Create: `src/liquidity_provider.py`
- Create: `tests/test_liquidity_provider.py`

- [ ] **Step 1: Write test**

```python
# tests/test_liquidity_provider.py
import pytest

def test_generate_lp_orders():
    from src.liquidity_provider import LiquidityProvider
    from src.config import LPConfig
    lp = LiquidityProvider(LPConfig(spread_cents=1, max_exposure_pct=0.05, min_spread_cents=3))
    orders = lp.generate_orders(
        token_id="tok_yes", midpoint=0.55, spread=0.04, bankroll=100.0
    )
    assert len(orders) == 2  # bid + ask
    assert orders[0]["side"] == "BUY"
    assert orders[1]["side"] == "SELL"
    assert orders[0]["price"] < orders[1]["price"]

def test_skip_narrow_spread():
    from src.liquidity_provider import LiquidityProvider
    from src.config import LPConfig
    lp = LiquidityProvider(LPConfig(min_spread_cents=3))
    orders = lp.generate_orders(
        token_id="tok_yes", midpoint=0.55, spread=0.02, bankroll=100.0
    )
    assert len(orders) == 0  # 2 cents < 3 cents minimum

def test_max_exposure_cap():
    from src.liquidity_provider import LiquidityProvider
    from src.config import LPConfig
    lp = LiquidityProvider(LPConfig(max_exposure_pct=0.05))
    orders = lp.generate_orders(
        token_id="tok_yes", midpoint=0.50, spread=0.05, bankroll=100.0
    )
    for order in orders:
        assert order["size_usdc"] <= 5.0  # 5% of 100
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/liquidity_provider.py**

```python
"""Idle-mode spread earning via symmetric limit orders."""
from __future__ import annotations
import logging
from typing import List

from src.config import LPConfig

logger = logging.getLogger(__name__)


class LiquidityProvider:
    def __init__(self, config: LPConfig) -> None:
        self.config = config
        self.active_orders: List[dict] = []

    def generate_orders(
        self, token_id: str, midpoint: float, spread: float, bankroll: float
    ) -> List[dict]:
        if spread < self.config.min_spread_cents / 100:
            logger.debug("Spread too narrow (%.1f cents), skipping LP", spread * 100)
            return []

        max_size = bankroll * self.config.max_exposure_pct
        offset = self.config.spread_cents / 100

        bid_price = round(midpoint - offset, 2)
        ask_price = round(midpoint + offset, 2)

        if bid_price <= 0 or ask_price >= 1:
            return []

        orders = [
            {"token_id": token_id, "side": "BUY", "price": bid_price,
             "size_usdc": round(max_size, 2), "mode": "liquidity_provider"},
            {"token_id": token_id, "side": "SELL", "price": ask_price,
             "size_usdc": round(max_size, 2), "mode": "liquidity_provider"},
        ]
        return orders

    def should_cancel(self, midpoint: float, placement_midpoint: float) -> bool:
        move = abs(midpoint - placement_midpoint) / placement_midpoint if placement_midpoint > 0 else 0
        return move > self.config.price_move_cancel_pct
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/liquidity_provider.py tests/test_liquidity_provider.py
git commit -m "feat: add liquidity provider for idle-mode spread earning"
```

---

## Task 16: Performance Tracker

**Files:**
- Create: `src/performance_tracker.py`
- Create: `tests/test_performance_tracker.py`

- [ ] **Step 1: Write test**

```python
# tests/test_performance_tracker.py
import pytest

def test_track_win_loss():
    from src.performance_tracker import PerformanceTracker
    pt = PerformanceTracker()
    pt.record_trade("politics", won=True, edge=0.10)
    pt.record_trade("politics", won=True, edge=0.08)
    pt.record_trade("politics", won=False, edge=0.07)
    assert pt.win_rate("politics") == pytest.approx(2/3)
    assert pt.overall_win_rate() == pytest.approx(2/3)

def test_category_underperformance():
    from src.performance_tracker import PerformanceTracker
    pt = PerformanceTracker()
    for _ in range(10):
        pt.record_trade("crypto", won=False, edge=0.05)
    assert pt.win_rate("crypto") == 0.0
    recs = pt.get_recommendations(min_win_rate=0.50, min_trades=5)
    assert "crypto" in recs.get("exclude_categories", [])

def test_edge_accuracy():
    from src.performance_tracker import PerformanceTracker
    pt = PerformanceTracker()
    pt.record_trade("politics", won=True, edge=0.10, ai_prob=0.70, actual_resolved_yes=True)
    pt.record_trade("politics", won=False, edge=0.08, ai_prob=0.65, actual_resolved_yes=False)
    brier = pt.brier_score()
    assert 0 <= brier <= 1
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/performance_tracker.py**

```python
"""Self-improving performance tracking with auto-tuning recommendations."""
from __future__ import annotations
import logging
from collections import defaultdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PerformanceTracker:
    def __init__(self) -> None:
        self._trades: List[dict] = []
        self._by_category: Dict[str, List[dict]] = defaultdict(list)

    def record_trade(
        self,
        category: str,
        won: bool,
        edge: float,
        ai_prob: Optional[float] = None,
        actual_resolved_yes: Optional[bool] = None,
    ) -> None:
        record = {
            "category": category, "won": won, "edge": edge,
            "ai_prob": ai_prob, "actual_resolved_yes": actual_resolved_yes,
        }
        self._trades.append(record)
        self._by_category[category].append(record)

    def win_rate(self, category: Optional[str] = None) -> float:
        trades = self._by_category.get(category, []) if category else self._trades
        if not trades:
            return 0.0
        return sum(1 for t in trades if t["won"]) / len(trades)

    def overall_win_rate(self) -> float:
        return self.win_rate(None)

    def brier_score(self) -> float:
        scored = [t for t in self._trades if t["ai_prob"] is not None and t["actual_resolved_yes"] is not None]
        if not scored:
            return 0.0
        total = sum(
            (t["ai_prob"] - (1.0 if t["actual_resolved_yes"] else 0.0)) ** 2
            for t in scored
        )
        return total / len(scored)

    def get_recommendations(
        self, min_win_rate: float = 0.50, min_trades: int = 10
    ) -> dict:
        exclude = []
        raise_edge = []
        for cat, trades in self._by_category.items():
            if len(trades) >= min_trades:
                wr = self.win_rate(cat)
                if wr < min_win_rate * 0.5:
                    exclude.append(cat)
                elif wr < min_win_rate:
                    raise_edge.append(cat)
        return {
            "exclude_categories": exclude,
            "raise_min_edge_categories": raise_edge,
            "overall_win_rate": self.overall_win_rate(),
            "brier_score": self.brier_score(),
            "total_trades": len(self._trades),
        }
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/performance_tracker.py tests/test_performance_tracker.py
git commit -m "feat: add self-improving performance tracker"
```

---

## Task 17: Telegram Notifier

**Files:**
- Create: `src/notifier.py`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: Write test**

```python
# tests/test_notifier.py
import pytest
from unittest.mock import patch, MagicMock

@patch("src.notifier.requests.post")
def test_send_notification(mock_post):
    from src.notifier import TelegramNotifier
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="test_token", chat_id="123")
    result = notifier.send("Test message")
    assert result is True
    mock_post.assert_called_once()

def test_notifier_disabled():
    from src.notifier import TelegramNotifier
    notifier = TelegramNotifier(bot_token="", chat_id="")
    result = notifier.send("Test message")
    assert result is False  # Disabled, should not send

def test_format_trade_message():
    from src.notifier import TelegramNotifier
    notifier = TelegramNotifier(bot_token="test", chat_id="123")
    msg = notifier.format_trade("Will X?", "BUY_YES", 15.0, 0.55, 0.10)
    assert "Will X?" in msg
    assert "BUY_YES" in msg
    assert "$15.00" in msg
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/notifier.py**

```python
"""Telegram bot notifications."""
from __future__ import annotations
import logging

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    def send(self, message: str, parse_mode: str = "Markdown") -> bool:
        if not self.enabled:
            logger.debug("Telegram notifications disabled")
            return False
        try:
            url = TELEGRAM_API.format(token=self.bot_token)
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
            }, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error("Telegram send failed: %s", e)
            return False

    def format_trade(
        self, question: str, direction: str, size: float, price: float, edge: float
    ) -> str:
        return (
            f"*Trade Opened*\n"
            f"Market: {question}\n"
            f"Direction: `{direction}`\n"
            f"Size: `${size:.2f}`\n"
            f"Price: `${price:.2f}`\n"
            f"Edge: `{edge:.1%}`"
        )

    def format_exit(self, question: str, reason: str, pnl: float) -> str:
        emoji = "+" if pnl >= 0 else ""
        return (
            f"*Position Closed*\n"
            f"Market: {question}\n"
            f"Reason: {reason}\n"
            f"PnL: `{emoji}${pnl:.2f}`"
        )

    def format_daily_summary(
        self, bankroll: float, positions: int, daily_pnl: float, win_rate: float
    ) -> str:
        return (
            f"*Daily Summary*\n"
            f"Bankroll: `${bankroll:.2f}`\n"
            f"Open positions: `{positions}`\n"
            f"Daily PnL: `${daily_pnl:+.2f}`\n"
            f"Win rate: `{win_rate:.0%}`"
        )

    def alert_drawdown(self, bankroll: float, hwm: float) -> str:
        return (
            f"*DRAWDOWN BREAKER ACTIVATED*\n"
            f"Bankroll: `${bankroll:.2f}`\n"
            f"High Water Mark: `${hwm:.2f}`\n"
            f"All trading halted. Manual review required."
        )
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/notifier.py tests/test_notifier.py
git commit -m "feat: add Telegram notifier"
```

---

## Task 18: Main Loop Integration

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main_loop.py`

@polymarket-executor skill for main loop pattern.

- [ ] **Step 1: Write test for one cycle**

```python
# tests/test_main_loop.py
import pytest
from unittest.mock import MagicMock, patch

def test_single_cycle_dry_run():
    from src.main import Agent
    from src.config import load_config
    config = load_config()
    agent = Agent(config)
    # Mock all external dependencies
    agent.scanner = MagicMock()
    agent.scanner.fetch.return_value = []
    agent.wallet = MagicMock()
    agent.wallet.get_usdc_balance.return_value = 60.0
    agent.news_scanner = MagicMock()
    agent.news_scanner.fetch_headlines.return_value = []
    # Run one cycle
    agent.run_cycle()
    agent.scanner.fetch.assert_called_once()

def test_graceful_shutdown_flag():
    from src.main import Agent
    from src.config import load_config
    config = load_config()
    agent = Agent(config)
    assert agent.running is True
    agent.shutdown()
    assert agent.running is False
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement src/main.py**

```python
"""Entry point and main agent loop."""
from __future__ import annotations
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.config import AppConfig, Mode, load_config
from src.market_scanner import MarketScanner
from src.ai_analyst import AIAnalyst
from src.edge_calculator import calculate_edge_with_whale
from src.risk_manager import RiskManager
from src.portfolio import Portfolio
from src.executor import Executor
from src.order_manager import OrderManager
from src.orderbook_analyzer import OrderBookAnalyzer
from src.news_scanner import NewsScanner
from src.whale_tracker import WhaleTracker
from src.event_cluster import EventCluster
from src.cycle_timer import CycleTimer
from src.liquidity_provider import LiquidityProvider
from src.performance_tracker import PerformanceTracker
from src.trade_logger import TradeLogger
from src.notifier import TelegramNotifier
from src.models import Signal, Direction

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.running = True
        self.consecutive_api_failures = 0

        # Core modules
        self.scanner = MarketScanner(config.scanner)
        self.ai = AIAnalyst(config.ai)
        self.risk = RiskManager(config.risk)
        self.portfolio = Portfolio()
        self.order_manager = OrderManager()
        self.ob_analyzer = OrderBookAnalyzer(
            wall_threshold_usd=config.orderbook.wall_threshold_usd,
            max_slippage_pct=config.orderbook.max_slippage_pct,
        )

        # Signal enhancers
        self.news_scanner = NewsScanner()
        self.whale_tracker = WhaleTracker(config.whale)
        self.event_cluster = EventCluster()
        self.cycle_timer = CycleTimer(config.cycle)
        self.lp = LiquidityProvider(config.liquidity_provider)
        self.perf = PerformanceTracker()

        # Logging & notifications
        self.trade_log = TradeLogger(config.logging.trades_file)
        self.portfolio_log = TradeLogger(config.logging.portfolio_file)
        self.notifier = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        )

        # Wallet & executor
        self.wallet = None
        self.executor = Executor(mode=Mode(config.mode), clob_client=None)

    def shutdown(self) -> None:
        self.running = False
        logger.info("Shutdown requested — finishing current cycle")

    def run_cycle(self) -> None:
        logger.info("=== Cycle start ===")

        # 1. Check bankroll
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.portfolio.update_bankroll(bankroll)

        # Drawdown check
        if self.portfolio.is_drawdown_breaker_active(self.config.risk.drawdown_halt_pct):
            msg = self.notifier.alert_drawdown(bankroll, self.portfolio.high_water_mark)
            self.notifier.send(msg)
            logger.critical("DRAWDOWN BREAKER — halting")
            self.running = False
            return

        # 2. Update positions
        for cid, pos in list(self.portfolio.positions.items()):
            try:
                # In live mode, fetch midpoint from CLOB
                pass  # Placeholder for CLOB midpoint fetch
            except Exception as e:
                logger.warning("Failed to update price for %s: %s", cid, e)

        # 3. Check stop-losses and take-profits
        for cid in self.portfolio.check_stop_losses(self.config.risk.stop_loss_pct):
            self._exit_position(cid, "stop_loss")
        for cid in self.portfolio.check_take_profits(self.config.risk.take_profit_pct):
            self._exit_position(cid, "take_profit")

        # 4. Order manager tick
        self.order_manager.tick_cycle()
        self.order_manager.cancel_stale(self.executor)

        # 5. Fetch news
        headlines = self.news_scanner.fetch_headlines()

        # 6. Scan markets
        markets = self.scanner.fetch()
        if not markets:
            self._try_liquidity_providing(bankroll)
            self._log_cycle_summary(bankroll, "no qualifying markets")
            return

        # 7. Cluster and analyze
        clusters = self.event_cluster.group(markets)
        news_context = self.news_scanner.build_news_context(headlines)
        estimates = self.ai.analyze_batch(markets[:self.config.ai.batch_size], news_context)

        # 8. Generate signals
        signals_generated = False
        for market, estimate in zip(markets, estimates):
            whale_positions = self.whale_tracker.check_market(market.condition_id)
            whale_prob = self.whale_tracker.compute_signal(whale_positions)

            direction, edge = calculate_edge_with_whale(
                ai_prob=estimate.ai_probability,
                market_price=market.yes_price,
                min_edge=self.config.edge.min_edge,
                confidence=estimate.confidence,
                whale_prob=whale_prob,
                whale_weight=self.config.whale.signal_weight,
            )

            if direction == Direction.HOLD:
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": edge, "mode": self.config.mode,
                })
                continue

            signals_generated = True
            signal = Signal(
                condition_id=market.condition_id,
                direction=direction,
                ai_probability=estimate.ai_probability,
                market_price=market.yes_price,
                edge=edge,
                confidence=estimate.confidence,
            )

            # Risk check
            corr_exposure = self.portfolio.correlated_exposure(
                market.tags[0] if market.tags else ""
            )
            decision = self.risk.evaluate(
                signal, bankroll, self.portfolio.positions, corr_exposure
            )

            if not decision.approved:
                self.trade_log.log({
                    "market": market.slug, "action": direction.value,
                    "edge": edge, "rejected": decision.reason, "mode": self.config.mode,
                })
                continue

            # Execute
            token_id = market.yes_token_id if direction == Direction.BUY_YES else market.no_token_id
            price = market.yes_price if direction == Direction.BUY_YES else market.no_price
            result = self.executor.place_order(token_id, "BUY", price, decision.size_usdc)

            # Track
            shares = decision.size_usdc / price if price > 0 else 0
            self.portfolio.add_position(
                market.condition_id, token_id, direction.value,
                price, decision.size_usdc, shares, market.slug,
                market.tags[0] if market.tags else "",
            )
            self.trade_log.log({
                "market": market.slug, "action": direction.value,
                "size": decision.size_usdc, "price": price,
                "edge": edge, "confidence": estimate.confidence,
                "mode": self.config.mode, "status": result["status"],
            })
            self.notifier.send(self.notifier.format_trade(
                market.question, direction.value, decision.size_usdc, price, edge
            ))

        if not signals_generated:
            self._try_liquidity_providing(bankroll)

        self._log_cycle_summary(bankroll, "complete")

    def _exit_position(self, condition_id: str, reason: str) -> None:
        pos = self.portfolio.remove_position(condition_id)
        if not pos:
            return
        result = self.executor.place_exit_order(pos.token_id, pos.shares)
        self.risk.record_outcome(win=pos.unrealized_pnl_usdc > 0)
        self.perf.record_trade(
            pos.category, won=pos.unrealized_pnl_usdc > 0, edge=0
        )
        self.trade_log.log({
            "market": pos.slug, "action": "EXIT",
            "reason": reason, "pnl": pos.unrealized_pnl_usdc,
            "mode": self.config.mode, "status": result.get("status", ""),
        })
        self.notifier.send(self.notifier.format_exit(
            pos.slug, reason, pos.unrealized_pnl_usdc
        ))

    def _try_liquidity_providing(self, bankroll: float) -> None:
        if not self.config.liquidity_provider.enabled:
            return
        logger.info("No edge signals — trying LP mode")
        # LP logic would go here with actual midpoint data

    def _log_cycle_summary(self, bankroll: float, status: str) -> None:
        self.portfolio_log.log({
            "bankroll": bankroll,
            "positions": len(self.portfolio.positions),
            "unrealized_pnl": self.portfolio.total_unrealized_pnl(),
            "hwm": self.portfolio.high_water_mark,
            "status": status,
        })

    def run(self) -> None:
        logger.info("Agent starting in %s mode", self.config.mode)
        signal.signal(signal.SIGINT, lambda *_: self.shutdown())

        while self.running:
            try:
                self.run_cycle()
                self.consecutive_api_failures = 0
            except Exception as e:
                self.consecutive_api_failures += 1
                logger.error("Cycle error (%d): %s", self.consecutive_api_failures, e)
                if self.consecutive_api_failures >= 3:
                    logger.warning("3 consecutive failures — pausing 5 min")
                    time.sleep(300)
                    self.consecutive_api_failures = 0

            interval = self.cycle_timer.get_interval()
            self.cycle_timer.tick()

            # Night mode check
            current_hour = datetime.now().hour
            self.cycle_timer.signal_night_mode(current_hour)

            # Near stop-loss check
            for pos in self.portfolio.positions.values():
                if pos.unrealized_pnl_pct < -(self.config.risk.stop_loss_pct * 0.83):
                    self.cycle_timer.signal_near_stop_loss()
                    break

            logger.info("Next cycle in %d min", interval)
            for _ in range(interval * 60):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Agent stopped")


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = load_config()

    # Iron Rule 6: User must explicitly confirm before live trading
    if config.mode == "live":
        print("\n*** WARNING: LIVE TRADING MODE ***")
        print("This will execute REAL orders with REAL money on Polymarket.")
        confirm = input("Type 'CONFIRM LIVE' to proceed: ")
        if confirm.strip() != "CONFIRM LIVE":
            print("Aborted. Set mode to 'dry_run' or 'paper' in config.yaml.")
            sys.exit(1)

    agent = Agent(config)
    agent.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main_loop.py
git commit -m "feat: add main agent loop with all module integration"
```

---

## Task 19: Dashboard (Web UI)

**Files:**
- Create: `src/dashboard.py`
- Create: `templates/dashboard.html`

- [ ] **Step 1: Implement src/dashboard.py**

```python
"""Flask web dashboard — read-only portfolio monitoring."""
from __future__ import annotations
import json
from pathlib import Path

from flask import Flask, render_template_string, jsonify

from src.trade_logger import TradeLogger

app = Flask(__name__)

DASHBOARD_HTML = Path(__file__).parent.parent / "templates" / "dashboard.html"


def create_app(
    trades_file: str = "logs/trades.jsonl",
    portfolio_file: str = "logs/portfolio.jsonl",
    performance_file: str = "logs/performance.jsonl",
) -> Flask:
    trade_log = TradeLogger(trades_file)
    portfolio_log = TradeLogger(portfolio_file)
    perf_log = TradeLogger(performance_file)

    @app.route("/")
    def index():
        html = DASHBOARD_HTML.read_text(encoding="utf-8") if DASHBOARD_HTML.exists() else "<h1>Dashboard</h1>"
        return html

    @app.route("/api/trades")
    def api_trades():
        return jsonify(trade_log.read_recent(100))

    @app.route("/api/portfolio")
    def api_portfolio():
        return jsonify(portfolio_log.read_recent(100))

    @app.route("/api/performance")
    def api_performance():
        return jsonify(perf_log.read_recent(100))

    return app
```

- [ ] **Step 2: Create templates/dashboard.html**

A single-page dashboard with:
- Portfolio summary cards
- Bankroll line chart (Chart.js)
- Trade history table
- Auto-refresh every 30 seconds

This is a larger file — implement as a standalone HTML with inline JS using Chart.js CDN.

- [ ] **Step 3: Commit**

```bash
git add src/dashboard.py templates/dashboard.html
git commit -m "feat: add Flask web dashboard with bankroll chart"
```

---

## Task 20: Final Integration + Run All Tests

- [ ] **Step 1: Run full test suite**

```bash
cd "C:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent"
python -m pytest tests/ -v --tb=short
```

Expected: All tests PASS

- [ ] **Step 2: Fix any failures**

- [ ] **Step 3: Verify dry_run mode works end-to-end**

```bash
python -m src.main
```

Expected: Agent starts, runs one cycle in dry_run mode, logs to JSONL, exits cleanly on Ctrl+C.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete Polymarket trading agent — all modules integrated"
```

---

## Execution Notes

- **Total tasks:** 20
- **Total source files:** 23 (22 Python + 1 HTML template)
- **Total test files:** 15
- **Estimated commits:** 20
- **Working directory:** `C:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent`
- **NEVER touch:** Website, Mobile App, or any files outside this directory
- **Default mode:** Always `dry_run` — never auto-switch to live
- **Skills to reference:** @polymarket-api, @ai-signal-engine, @trading-risk-manager, @polymarket-executor
