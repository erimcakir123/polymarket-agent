# PLAN-001 — Faz 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polymarket Agent 2.0 projesinin iskeletini (config + domain modelleri + temel infrastructure + main entry) sıfırdan yazmak; Faz 2+ adımlarının üzerine inşa edileceği stabil tabanı kurmak.

**Architecture:** 5 katmanlı mimari (Presentation → Orchestration → Strategy → Domain → Infrastructure). Faz 1 sadece **models/**, **config/**, **infrastructure/** ve **src/main.py** dosyalarını oluşturur. Domain/Strategy/Orchestration katmanları boş bırakılır (iskelet paketleri + `__init__.py`). ARCHITECTURE_GUARD Kural 2'ye göre domain'de I/O yasak — fakat Faz 1'de henüz domain kodu yazılmayacak; sadece models/ altındaki Pydantic modelleri yer alacak (Pydantic import'u serbest çünkü models/ bir data-definition katmanıdır, TDD §2'de `domain/` dışına yerleştirilmiştir).

**Tech Stack:** Python 3.12+, Pydantic v2, PyYAML, python-dotenv, requests, eth-account, pytest.

**Eski Proje Referansı (CLAUDE.md Selective Migration):** `../Polymarket Agent_Eski/src/`. Her taskda ilgili eski dosya(lar) okunur; **sayısal sabitler ve kanıtlanmış formüller migrate**, mimari/sınıf yapısı **sıfırdan yazılır**. Kod kopyalama yasak (0 satır copy-paste).

**Proje Kök Yolu:** `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\Polymarket Agent 2.0\` (bu plandaki tüm path'ler bu dizine göre relatif).

**Commit Stili:** Her task sonunda commit (Türkçe subject, altında kısa açıklama; `.gitignore` yoksa ilk task'de eklenir — aşağıda Task 0).

---

## Pre-Task Gate (Sürekli geçerli kurallar)

Her task adımında aşağıdaki mental check'i uygula:

- [ ] Dosya TDD §2'deki dizin yapısında mı?
- [ ] Katman sırasına uygun mu (ARCH Kural 1)?
- [ ] Domain'de `requests` / `httpx` / `open(` / `socket` / `websockets` var mı? (Bu faz'da domain boş, ama yine kontrol)
- [ ] Dosya 400 satırı aşıyor mu (ARCH Kural 3)?
- [ ] Class 10+ public method veya 5+ constructor dep mi (ARCH Kural 4)?
- [ ] Magic number var mı (ARCH Kural 6, config'den oku)?
- [ ] Domain fonksiyonuysa unit test yazıldı mı (ARCH Kural 11)?

---

## File Structure (Faz 1'de oluşacak dosyalar)

```
polymarket-agent-2/
├── .env.example                    ← Task 15
├── .gitignore                      ← Task 0
├── config.yaml                     ← Task 3
├── requirements.txt                ← Task 15
├── pyproject.toml                  ← Task 15
├── pytest.ini                      ← Task 15
├── src/
│   ├── __init__.py                 ← Task 0
│   ├── main.py                     ← Task 14
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py             ← Task 1
│   │   └── sport_rules.py          ← Task 2
│   ├── models/
│   │   ├── __init__.py             (re-exports)
│   │   ├── enums.py                ← Task 4
│   │   ├── market.py               ← Task 5
│   │   ├── position.py             ← Task 6
│   │   └── signal.py               ← Task 7
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── wallet.py               ← Task 12
│   │   ├── executor.py             ← Task 13
│   │   ├── apis/
│   │   │   ├── __init__.py
│   │   │   └── gamma_client.py     ← Task 11
│   │   └── persistence/
│   │       ├── __init__.py
│   │       ├── json_store.py       ← Task 8
│   │       ├── trade_logger.py     ← Task 9 (zengin trade case-study log)
│   │       └── price_history.py    ← Task 10
│   ├── domain/__init__.py          ← Task 0 (boş iskelet)
│   ├── strategy/__init__.py        ← Task 0 (boş iskelet)
│   ├── orchestration/__init__.py   ← Task 0 (boş iskelet)
│   └── presentation/__init__.py    ← Task 0 (boş iskelet)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 ← Task 0
│   └── unit/
│       ├── __init__.py
│       ├── config/
│       │   └── test_settings.py           ← Task 1
│       ├── models/
│       │   ├── test_enums.py              ← Task 4
│       │   ├── test_market.py             ← Task 5
│       │   ├── test_position.py           ← Task 6
│       │   └── test_signal.py             ← Task 7
│       └── infrastructure/
│           ├── persistence/
│           │   ├── test_json_store.py     ← Task 8
│           │   ├── test_trade_logger.py   ← Task 9
│           │   └── test_price_history.py  ← Task 10
│           ├── apis/
│           │   └── test_gamma_client.py   ← Task 11
│           ├── test_wallet.py             ← Task 12
│           └── test_executor.py           ← Task 13
└── logs/                           ← .gitignore'da; runtime'da yaratılır
```

**SPEC.md yönetimi:** Her "koda dönüşecek" task'den önce DRAFT spec SPEC.md'ye eklenir, Step 1'den önce. Task'in son step'inde (commit'ten hemen önce) SPEC silinir (CLAUDE.md "Spec Yazdırırken" protokolü).

---

## Task 0: Proje İskeleti + Git/Test/Config Altyapısı

**Amaç:** Tüm paket dizinlerini ve test altyapısını oluştur. İleriki task'ler için zemin hazır olsun.

**Files:**
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `src/config/__init__.py`
- Create: `src/models/__init__.py`
- Create: `src/infrastructure/__init__.py`
- Create: `src/infrastructure/apis/__init__.py`
- Create: `src/infrastructure/persistence/__init__.py`
- Create: `src/domain/__init__.py`
- Create: `src/strategy/__init__.py`
- Create: `src/orchestration/__init__.py`
- Create: `src/presentation/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/config/__init__.py`
- Create: `tests/unit/models/__init__.py`
- Create: `tests/unit/infrastructure/__init__.py`
- Create: `tests/unit/infrastructure/apis/__init__.py`
- Create: `tests/unit/infrastructure/persistence/__init__.py`

- [ ] **Step 1: `.gitignore` oluştur**

```gitignore
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.coverage
htmlcov/
.venv/
venv/
.env
logs/
*.egg-info/
.mypy_cache/
.ruff_cache/
dist/
build/
.idea/
.vscode/
```

- [ ] **Step 2: Tüm `__init__.py` dosyalarını oluştur (boş içerik)**

`src/__init__.py`, `src/config/__init__.py`, `src/models/__init__.py`, `src/infrastructure/__init__.py`, `src/infrastructure/apis/__init__.py`, `src/infrastructure/persistence/__init__.py`, `src/domain/__init__.py`, `src/strategy/__init__.py`, `src/orchestration/__init__.py`, `src/presentation/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/unit/config/__init__.py`, `tests/unit/models/__init__.py`, `tests/unit/infrastructure/__init__.py`, `tests/unit/infrastructure/apis/__init__.py`, `tests/unit/infrastructure/persistence/__init__.py` — her biri boş.

- [ ] **Step 3: `tests/conftest.py` yaz**

```python
"""Shared pytest fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

# Proje kökünü sys.path'e ekle (src.* import'ları için)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
```

- [ ] **Step 4: Import sağlığını doğrula**

Run: `python -c "import src; import src.config; import src.models; import src.infrastructure; import src.infrastructure.apis; import src.infrastructure.persistence; import src.domain; import src.strategy; import src.orchestration; import src.presentation"`
Expected: Hata yok, hiç çıktı yok.

- [ ] **Step 5: Commit**

```bash
git add .gitignore src/ tests/
git commit -m "chore: paket iskeletini ve test altyapısını kur"
```

---

## Task 1: `src/config/settings.py` — Pydantic Config Modelleri

**Amaç:** `config.yaml`'ı typed Pydantic modellere yükleyen ayar katmanını kur. TDD §9 tam şeması.

**Eski Referans:** `../Polymarket Agent_Eski/src/config.py` (165 satır).
- **Migrate edilen değerler:** mode enum (`dry_run`/`paper`/`live`), `load_config()` YAML okuma şeması, varsayılan sayısal değerler.
- **Sıfırdan yazılan:** TDD §9'a uygun alt-model kırılımı, `allowed_sport_tags` listesi, `a_conf_hold`, `favored`, `near_resolve`, `scale_out`, `circuit_breaker`, `manipulation`, `liquidity` alt modelleri — eski `config.py`'de bu granularite yok. `LiveMomentumConfig`, `TennisConfig`, `ChessConfig`, `TrailingTPConfig` → **SİL** (v2'de bunlar yok).

**SPEC entry (SPEC.md'ye Step 0'da ekle, Step 9'da sil):**

```markdown
### SPEC-001: Config Loader (settings.py)
- **Durum**: DRAFT
- **Tarih**: 2026-04-13
- **İlgili Plan**: PLAN-001
- **Katman**: config
- **Dosya**: src/config/settings.py

#### Amaç
config.yaml'ı Pydantic modellerine parse eden, missing file için default'larla çalışan typed config yükleyici.

#### Girdi/Çıktı
- Girdi: `config.yaml` Path (opsiyonel, default `config.yaml`)
- Çıktı: `AppConfig` instance (Pydantic BaseModel)

#### Davranış Kuralları
1. YAML dosyası yoksa → tüm default'larla AppConfig döner (hata atmaz)
2. Geçersiz tip (örn. `edge.min_edge: "high"`) → Pydantic ValidationError fırlat
3. `mode` sadece {"dry_run", "paper", "live"} kabul eder
4. `allowed_sport_tags` list[str], empty list → scanner hiçbir şey toplamaz
5. `night_hours` 0-23 arası int list (TDD §9)

#### Sınır Durumları
- Boş YAML ({} veya None) → tüm default'lar
- Tanınmayan alan → Pydantic `extra="forbid"` değil, `extra="ignore"` (forward compat)
- YAML syntax hatası → yaml.YAMLError fırlat (sessizce yutma)

#### Test Senaryoları
- test_load_config_missing_file_returns_defaults
- test_load_config_valid_yaml_parses
- test_load_config_invalid_mode_raises
- test_load_config_invalid_edge_value_raises
- test_mode_enum_values
- test_config_a_conf_hold_defaults (elapsed_gate=0.85)
```

**Files:**
- Create: `src/config/settings.py`
- Test: `tests/unit/config/test_settings.py`

- [ ] **Step 0: SPEC.md'ye SPEC-001 DRAFT olarak ekle (yukarıdaki blok).**

- [ ] **Step 1: Failing testleri yaz**

Create: `tests/unit/config/test_settings.py`

```python
"""settings.py için birim testler."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.config.settings import AppConfig, Mode, load_config


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "nonexistent.yaml")
    assert isinstance(cfg, AppConfig)
    assert cfg.mode == Mode.DRY_RUN
    assert cfg.initial_bankroll == 1000.0
    assert cfg.edge.min_edge == 0.06


def test_load_config_valid_yaml_parses(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text(
        "mode: paper\n"
        "initial_bankroll: 500.0\n"
        "edge:\n"
        "  min_edge: 0.08\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.mode == Mode.PAPER
    assert cfg.initial_bankroll == 500.0
    assert cfg.edge.min_edge == 0.08


def test_load_config_invalid_mode_raises(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text("mode: chaotic\n", encoding="utf-8")
    with pytest.raises(Exception):  # Pydantic ValidationError
        load_config(p)


def test_load_config_invalid_edge_value_raises(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text("edge:\n  min_edge: high\n", encoding="utf-8")
    with pytest.raises(Exception):
        load_config(p)


def test_mode_enum_values() -> None:
    assert Mode.DRY_RUN.value == "dry_run"
    assert Mode.PAPER.value == "paper"
    assert Mode.LIVE.value == "live"


def test_config_a_conf_hold_defaults() -> None:
    cfg = AppConfig()
    assert cfg.a_conf_hold.market_flip_elapsed_gate == 0.85
    assert cfg.a_conf_hold.min_entry_price == 0.60
    assert cfg.a_conf_hold.market_flip_threshold == 0.50


def test_config_circuit_breaker_defaults() -> None:
    cfg = AppConfig()
    assert cfg.circuit_breaker.daily_max_loss_pct == -0.08
    assert cfg.circuit_breaker.hourly_max_loss_pct == -0.05
    assert cfg.circuit_breaker.consecutive_loss_limit == 4
    assert cfg.circuit_breaker.entry_block_threshold == -0.03


def test_config_scale_out_tiers_defaults() -> None:
    cfg = AppConfig()
    tiers = cfg.scale_out.tiers
    assert len(tiers) == 2
    assert tiers[0].threshold == 0.25
    assert tiers[0].sell_pct == 0.40
    assert tiers[1].threshold == 0.50
    assert tiers[1].sell_pct == 0.50
```

- [ ] **Step 2: Testleri çalıştır, fail gördüğünü doğrula**

Run: `pytest tests/unit/config/test_settings.py -v`
Expected: FAIL with `ModuleNotFoundError: src.config.settings`.

- [ ] **Step 3: `src/config/settings.py` yaz**

```python
"""Pydantic config loader (TDD §9)."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, ConfigDict


class Mode(str, Enum):
    DRY_RUN = "dry_run"
    PAPER = "paper"
    LIVE = "live"


class CycleConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    heavy_interval_min: int = 30
    light_interval_sec: int = 5
    night_interval_min: int = 60
    night_hours: List[int] = [8, 9, 10, 11, 12, 13]


class ScannerConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_liquidity: float = 1000
    max_markets_per_cycle: int = 300
    max_duration_days: int = 14
    allowed_categories: List[str] = ["sports"]
    allowed_sport_tags: List[str] = []


class EdgeConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_edge: float = 0.06
    confidence_multipliers: dict = {"A": 1.25, "B": 1.00}


class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_single_bet_usdc: float = 75
    max_bet_pct: float = 0.05
    max_positions: int = 20
    max_exposure_pct: float = 0.50
    consecutive_loss_cooldown: int = 3
    cooldown_cycles: int = 2
    stop_loss_pct: float = 0.30


class VolatilitySwingConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    max_concurrent: int = 5
    stop_loss_pct: float = 0.20
    take_profit_pct: float = 0.60
    max_token_price: float = 0.50
    min_token_price: float = 0.10
    max_hours_to_start: float = 24.0
    bet_pct: float = 0.05


class EarlyEntryConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    max_slots: int = 2
    max_entry_price: float = 0.70
    min_edge: float = 0.10
    min_anchor_probability: float = 0.55
    min_confidence: str = "B"
    bookmaker_pre_screen_edge: float = 0.08
    min_hours_to_start: float = 6.0
    max_hours_to_start: float = 336.0
    bet_pct: float = 0.05
    stop_loss_pct: float = 0.30


class ConsensusConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    min_price: float = 0.65
    bet_pct: float = 0.05
    max_slots: int = 5


class ScaleOutTier(BaseModel):
    model_config = ConfigDict(extra="ignore")
    threshold: float
    sell_pct: float


class ScaleOutConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    tiers: List[ScaleOutTier] = [
        ScaleOutTier(threshold=0.25, sell_pct=0.40),
        ScaleOutTier(threshold=0.50, sell_pct=0.50),
    ]


class CircuitBreakerConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    daily_max_loss_pct: float = -0.08
    hourly_max_loss_pct: float = -0.05
    consecutive_loss_limit: int = 4
    cooldown_after_daily_min: int = 120
    cooldown_after_hourly_min: int = 60
    cooldown_after_consecutive_min: int = 60
    entry_block_threshold: float = -0.03


class ManipulationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_liquidity_usd: float = 10_000


class LiquidityConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entry_min_depth_usdc: float = 100
    entry_halve_threshold: float = 0.20
    exit_min_fill_ratio: float = 0.80


class NearResolveConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    threshold_cents: int = 94
    pre_match_guard_minutes: int = 5


class AConfHoldConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_entry_price: float = 0.60
    market_flip_threshold: float = 0.50
    market_flip_elapsed_gate: float = 0.85


class FavoredConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    promote_eff_price: float = 0.65
    demote_eff_price: float = 0.65
    conf_required: List[str] = ["A", "B"]


class DashboardConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 5050


class TelegramConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mode: Mode = Mode.DRY_RUN
    initial_bankroll: float = 1000.0
    cycle: CycleConfig = CycleConfig()
    scanner: ScannerConfig = ScannerConfig()
    edge: EdgeConfig = EdgeConfig()
    risk: RiskConfig = RiskConfig()
    volatility_swing: VolatilitySwingConfig = VolatilitySwingConfig()
    early: EarlyEntryConfig = EarlyEntryConfig()
    consensus: ConsensusConfig = ConsensusConfig()
    scale_out: ScaleOutConfig = ScaleOutConfig()
    circuit_breaker: CircuitBreakerConfig = CircuitBreakerConfig()
    manipulation: ManipulationConfig = ManipulationConfig()
    liquidity: LiquidityConfig = LiquidityConfig()
    near_resolve: NearResolveConfig = NearResolveConfig()
    a_conf_hold: AConfHoldConfig = AConfHoldConfig()
    favored: FavoredConfig = FavoredConfig()
    dashboard: DashboardConfig = DashboardConfig()
    telegram: TelegramConfig = TelegramConfig()


def load_config(path: Path = Path("config.yaml")) -> AppConfig:
    """YAML'dan config yükle; dosya yoksa default'larla döner."""
    if not path.exists():
        return AppConfig()
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return AppConfig(**data)
```

- [ ] **Step 4: Testleri tekrar çalıştır**

Run: `pytest tests/unit/config/test_settings.py -v`
Expected: PASS (8/8).

- [ ] **Step 5: ARCH check — dosya 400 satırın altında, magic number yok (hepsi field default)**

Run: `python -c "import pathlib; print(sum(1 for _ in open('src/config/settings.py', encoding='utf-8')))"`
Expected: 400'ün altında bir sayı.

- [ ] **Step 6: SPEC.md'den SPEC-001 entry'sini sil**

- [ ] **Step 7: Commit**

```bash
git add src/config/settings.py tests/unit/config/test_settings.py SPEC.md
git commit -m "feat(config): Pydantic config modelleri + load_config (TDD §9)"
```

---

## Task 2: `src/config/sport_rules.py` — Sport-Specific Kural Tabloları

**Amaç:** Her MVP sporu için stop_loss_pct, match_duration_hours, halftime/period/inning_exit kurallarını sağlayan lookup tabloları.

**Eski Referans:** `../Polymarket Agent_Eski/src/sport_rules.py` (367 satır).
- **Migrate edilen değerler:** `SPORT_RULES` tablosundan NBA, NFL, NHL, MLB, Tennis için sayısal değerler (stop_loss_pct, match_duration_hours, halftime_exit_deficit, period_exit_deficit, inning_exit_deficit). `DEFAULT_RULES` değerleri. `get_stop_loss()` / `get_sport_rule()` public API imzası.
- **Sıfırdan yazılan:** MVP kapsamı (TDD §7.1, draw-possible sporlar hariç). Golf (LPGA/LIV H2H). Baseball sub-leagues (MiLB, NPB, KBO, NCAA) — aynı "mlb" rule'a alias. Basketball sub-leagues (WNBA, NCAAB, Euroleague, NBL) — aynı "nba" alias. Hockey sub-leagues (AHL, Liiga, SHL). Football sub-leagues (NCAAF, CFL, UFL).
- **SİLİNEN:** Eski dosyadaki CS2/Valorant/LoL/Dota2/Boxing/MMA/Cricket/Rugby/Soccer → bunlar MVP dışı (draw-possible veya esports, TODO-001).

**SPEC entry (SPEC.md):**

```markdown
### SPEC-002: Sport Rules Tablosu (sport_rules.py)
- **Durum**: DRAFT
- **Tarih**: 2026-04-13
- **İlgili Plan**: PLAN-001
- **Katman**: config
- **Dosya**: src/config/sport_rules.py

#### Amaç
MVP 2-way sporlarının SL, duration, halftime/period/inning exit kurallarını sağlayan lookup tabloları + public getter API.

#### Girdi/Çıktı
- `get_stop_loss(sport_tag: str) -> float`
- `get_match_duration_hours(sport_tag: str) -> float`
- `get_sport_rule(sport_tag: str, key: str, default=None) -> Any`

#### Davranış Kuralları
1. MVP kapsamı: NBA, NFL (NCAAF/CFL/UFL alias), NHL (AHL/Liiga alias), MLB (MiLB/NPB/KBO alias), Tennis, Golf (LPGA/LIV)
2. Bilinmeyen sport_tag → DEFAULT_RULES
3. Odds API sport_key normalizasyonu: `basketball_nba` → `nba`, `americanfootball_ncaaf` → `nfl` (TDD §7.2 tablosu)
4. TDD §7.2'deki değerleri birebir yansıtır

#### Test Senaryoları
- test_get_stop_loss_nba_returns_035
- test_get_stop_loss_nfl_returns_030
- test_get_stop_loss_unknown_returns_default
- test_get_match_duration_tennis_default
- test_odds_api_key_aliases (basketball_nba → nba)
- test_mvp_sports_have_all_required_keys
```

**Files:**
- Create: `src/config/sport_rules.py`
- Test: `tests/unit/config/test_sport_rules.py`

- [ ] **Step 0: SPEC-002 DRAFT'ını SPEC.md'ye ekle**

- [ ] **Step 1: Testleri yaz**

Create: `tests/unit/config/test_sport_rules.py`

```python
"""sport_rules.py için birim testler."""
from __future__ import annotations

from src.config.sport_rules import (
    DEFAULT_RULES,
    get_match_duration_hours,
    get_sport_rule,
    get_stop_loss,
)


def test_get_stop_loss_nba_returns_035() -> None:
    assert get_stop_loss("nba") == 0.35


def test_get_stop_loss_nfl_returns_030() -> None:
    assert get_stop_loss("nfl") == 0.30


def test_get_stop_loss_nhl_returns_030() -> None:
    assert get_stop_loss("nhl") == 0.30


def test_get_stop_loss_mlb_returns_030() -> None:
    assert get_stop_loss("mlb") == 0.30


def test_get_stop_loss_tennis_returns_035() -> None:
    assert get_stop_loss("tennis") == 0.35


def test_get_stop_loss_golf_returns_030() -> None:
    assert get_stop_loss("golf") == 0.30


def test_get_stop_loss_unknown_returns_default() -> None:
    assert get_stop_loss("unknown_sport") == DEFAULT_RULES["stop_loss_pct"]


def test_get_match_duration_tennis_default() -> None:
    assert get_match_duration_hours("tennis") == 2.5


def test_odds_api_key_alias_basketball_nba() -> None:
    # basketball_nba → nba
    assert get_stop_loss("basketball_nba") == 0.35


def test_odds_api_key_alias_baseball_milb() -> None:
    # baseball_milb → mlb rule set
    assert get_stop_loss("baseball_milb") == 0.30


def test_odds_api_key_alias_americanfootball_ncaaf() -> None:
    assert get_stop_loss("americanfootball_ncaaf") == 0.30


def test_mvp_sports_have_stop_loss() -> None:
    for sport in ["nba", "nfl", "nhl", "mlb", "tennis", "golf"]:
        sl = get_stop_loss(sport)
        assert 0.05 <= sl <= 0.70, f"{sport} sl out of range: {sl}"


def test_get_sport_rule_halftime_deficit_nba() -> None:
    assert get_sport_rule("nba", "halftime_exit_deficit") == 15


def test_get_sport_rule_period_exit_deficit_nhl() -> None:
    assert get_sport_rule("nhl", "period_exit_deficit") == 3


def test_get_sport_rule_inning_exit_deficit_mlb() -> None:
    assert get_sport_rule("mlb", "inning_exit_deficit") == 5


def test_get_sport_rule_missing_key_returns_default_arg() -> None:
    assert get_sport_rule("nba", "nonexistent_key", default=42) == 42
```

- [ ] **Step 2: Testleri çalıştır, FAIL'ı doğrula**

Run: `pytest tests/unit/config/test_sport_rules.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: `src/config/sport_rules.py` yaz**

```python
"""Sport-specific trading rules (TDD §7.2). MVP 2-way sports only.

Draw-possible sporlar TODO-001 kapsamında, bu dosyada YOK.
"""
from __future__ import annotations

from typing import Any

# ── MVP sport rules (2-way) ──
SPORT_RULES: dict[str, dict] = {
    "nba": {
        "stop_loss_pct": 0.35,
        "match_duration_hours": 2.5,
        "halftime_exit": True,
        "halftime_exit_deficit": 15,
    },
    "nfl": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.25,
        "halftime_exit": True,
        "halftime_exit_deficit": 14,
    },
    "nhl": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 2.5,
        "period_exit": True,
        "period_exit_deficit": 3,
    },
    "mlb": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.0,
        "inning_exit": True,
        "inning_exit_deficit": 5,
        "inning_exit_after": 6,
    },
    "tennis": {
        "stop_loss_pct": 0.35,
        "match_duration_hours": 2.5,
        "match_duration_hours_bo3": 1.75,
        "match_duration_hours_bo5": 3.5,
        "set_exit": True,
    },
    "golf": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 4.0,
        "playoff_aware": True,
    },
}

DEFAULT_RULES: dict[str, Any] = {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 2.0,
}

# Odds API key → internal sport key aliases (TDD §7.1 MVP)
_ALIASES: dict[str, str] = {
    # Basketball
    "basketball_nba": "nba",
    "basketball_wnba": "nba",
    "basketball_ncaab": "nba",
    "basketball_wncaab": "nba",
    "basketball_euroleague": "nba",
    "basketball_nbl": "nba",
    "basketball": "nba",
    # American Football
    "americanfootball_ncaaf": "nfl",
    "americanfootball_cfl": "nfl",
    "americanfootball_ufl": "nfl",
    "americanfootball": "nfl",
    # Ice Hockey
    "icehockey_nhl": "nhl",
    "icehockey_ahl": "nhl",
    "icehockey_liiga": "nhl",
    "icehockey_mestis": "nhl",
    "icehockey_sweden_hockey_league": "nhl",
    "icehockey_sweden_allsvenskan": "nhl",
    "icehockey": "nhl",
    # Baseball
    "baseball_mlb": "mlb",
    "baseball_milb": "mlb",
    "baseball_npb": "mlb",
    "baseball_kbo": "mlb",
    "baseball_ncaa": "mlb",
    "baseball": "mlb",
    # Tennis (dinamik — hepsi "tennis")
    "tennis_atp": "tennis",
    "tennis_wta": "tennis",
    # Golf
    "golf_lpga_tour": "golf",
    "golf_liv_tour": "golf",
}


def _normalize(sport_tag: str) -> str:
    tag = (sport_tag or "").lower().strip()
    if tag in SPORT_RULES:
        return tag
    if tag in _ALIASES:
        return _ALIASES[tag]
    # tennis_* prefix match (dinamik turnuvalar)
    if tag.startswith("tennis_"):
        return "tennis"
    return ""


def get_sport_rule(sport_tag: str, key: str, default: Any = None) -> Any:
    tag = _normalize(sport_tag)
    rules = SPORT_RULES.get(tag, DEFAULT_RULES)
    return rules.get(key, DEFAULT_RULES.get(key, default))


def get_stop_loss(sport_tag: str) -> float:
    return float(get_sport_rule(sport_tag, "stop_loss_pct", 0.30))


def get_match_duration_hours(sport_tag: str) -> float:
    return float(get_sport_rule(sport_tag, "match_duration_hours", 2.0))
```

- [ ] **Step 4: Testleri çalıştır**

Run: `pytest tests/unit/config/test_sport_rules.py -v`
Expected: PASS (15/15).

- [ ] **Step 5: SPEC.md'den SPEC-002'yi sil**

- [ ] **Step 6: Commit**

```bash
git add src/config/sport_rules.py tests/unit/config/test_sport_rules.py SPEC.md
git commit -m "feat(config): MVP sport_rules tablosu + Odds API alias normalize"
```

---

## Task 3: `config.yaml` — Varsayılan Konfigürasyon Dosyası

**Amaç:** TDD §9'daki YAML şemasını dosya olarak yaratıp `load_config()` ile okunabilir olduğunu doğrula.

**Eski Referans:** `../Polymarket Agent_Eski/config.yaml` (sadece yapı ipucu; değerler TDD §9'dan).

**Files:**
- Create: `config.yaml`
- Test: reuse `tests/unit/config/test_settings.py` — yeni test ekle.

- [ ] **Step 1: `config.yaml` yaz (TDD §9 birebir)**

```yaml
# config.yaml — Polymarket Agent 2.0 v2 defaults (TDD §9)
mode: dry_run  # dry_run | paper | live
initial_bankroll: 1000.0

cycle:
  heavy_interval_min: 30
  light_interval_sec: 5
  night_interval_min: 60
  night_hours: [8, 9, 10, 11, 12, 13]

scanner:
  min_liquidity: 1000
  max_markets_per_cycle: 300
  max_duration_days: 14
  allowed_categories: ["sports"]
  allowed_sport_tags:
    - baseball_mlb
    - baseball_milb
    - baseball_npb
    - baseball_kbo
    - baseball_ncaa
    - basketball_nba
    - basketball_wnba
    - basketball_ncaab
    - basketball_wncaab
    - basketball_euroleague
    - basketball_nbl
    - icehockey_nhl
    - icehockey_ahl
    - icehockey_liiga
    - icehockey_mestis
    - icehockey_sweden_hockey_league
    - icehockey_sweden_allsvenskan
    - americanfootball_ncaaf
    - americanfootball_cfl
    - americanfootball_ufl
    - golf_lpga_tour
    - golf_liv_tour

edge:
  min_edge: 0.06
  confidence_multipliers:
    A: 1.25
    B: 1.00

risk:
  max_single_bet_usdc: 75
  max_bet_pct: 0.05
  max_positions: 20
  max_exposure_pct: 0.50
  consecutive_loss_cooldown: 3
  cooldown_cycles: 2
  stop_loss_pct: 0.30

volatility_swing:
  enabled: true
  max_concurrent: 5
  stop_loss_pct: 0.20
  take_profit_pct: 0.60
  max_token_price: 0.50
  min_token_price: 0.10
  max_hours_to_start: 24.0
  bet_pct: 0.05

early:
  enabled: true
  max_slots: 2
  max_entry_price: 0.70
  min_edge: 0.10
  min_anchor_probability: 0.55
  min_confidence: "B"
  bookmaker_pre_screen_edge: 0.08
  min_hours_to_start: 6.0
  max_hours_to_start: 336.0
  bet_pct: 0.05
  stop_loss_pct: 0.30

consensus:
  enabled: true
  min_price: 0.65
  bet_pct: 0.05
  max_slots: 5

scale_out:
  enabled: true
  tiers:
    - threshold: 0.25
      sell_pct: 0.40
    - threshold: 0.50
      sell_pct: 0.50

circuit_breaker:
  daily_max_loss_pct: -0.08
  hourly_max_loss_pct: -0.05
  consecutive_loss_limit: 4
  cooldown_after_daily_min: 120
  cooldown_after_hourly_min: 60
  cooldown_after_consecutive_min: 60
  entry_block_threshold: -0.03

manipulation:
  min_liquidity_usd: 10000

liquidity:
  entry_min_depth_usdc: 100
  entry_halve_threshold: 0.20
  exit_min_fill_ratio: 0.80

near_resolve:
  threshold_cents: 94
  pre_match_guard_minutes: 5

a_conf_hold:
  min_entry_price: 0.60
  market_flip_threshold: 0.50
  market_flip_elapsed_gate: 0.85

favored:
  promote_eff_price: 0.65
  demote_eff_price: 0.65
  conf_required: ["A", "B"]

dashboard:
  enabled: true
  host: "127.0.0.1"
  port: 5050

telegram:
  enabled: false
  bot_token: ""
  chat_id: ""
```

- [ ] **Step 2: test ekle — kök config.yaml'ı okuyup validate**

`tests/unit/config/test_settings.py` dosyasının sonuna ekle:

```python
def test_repo_config_yaml_parses() -> None:
    """Kökdeki config.yaml geçerli Pydantic olarak yüklenmeli."""
    from src.config.settings import load_config
    cfg = load_config()  # default Path("config.yaml")
    assert cfg.mode is not None
    assert cfg.initial_bankroll > 0
    assert cfg.edge.min_edge == 0.06
    assert "basketball_nba" in cfg.scanner.allowed_sport_tags
    assert "golf_lpga_tour" in cfg.scanner.allowed_sport_tags
    # Draw-possible sporlar MVP dışı — eklenmemiş olmalı
    for banned in ("soccer_epl", "soccer_laliga", "cricket", "mma", "boxing"):
        assert banned not in cfg.scanner.allowed_sport_tags, f"{banned} MVP dışı"
```

- [ ] **Step 3: Testi çalıştır**

Run: `pytest tests/unit/config/test_settings.py::test_repo_config_yaml_parses -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add config.yaml tests/unit/config/test_settings.py
git commit -m "feat(config): config.yaml MVP defaults (TDD §9)"
```

---

## Task 4: `src/models/enums.py` — Enum Tanımları

**Amaç:** Direction, Confidence, EntryReason, ExitReason — tüm `str` mixin enumları tek yerde.

**Eski Referans:** `../Polymarket Agent_Eski/src/models.py` line 19-22 (sadece Direction), ve çeşitli enum-benzeri string'ler (entry_reason, exit_reason) kod genelinde dağınık — sıfırdan toplu yazılıyor.

**SPEC entry:**

```markdown
### SPEC-003: Domain Enums (enums.py)
- **Durum**: DRAFT
- **Katman**: models
- **Dosya**: src/models/enums.py

#### Davranış Kuralları
1. Tüm enum'lar `str(Enum)` mixin (JSON serializable)
2. Direction: BUY_YES | BUY_NO | HOLD
3. Confidence: A | B | C
4. EntryReason: normal | early | volatility_swing | consensus
5. ExitReason: TDD §5.4 listesi (stop_loss, scale_out, graduated_sl, never_in_profit, market_flip, near_resolve, hold_revoked, ultra_low_guard, circuit_breaker, manual)

#### Test Senaryoları
- test_direction_values
- test_confidence_values
- test_enum_str_mixin (json.dumps çalışmalı)
- test_entry_reason_values
- test_exit_reason_values
```

**Files:**
- Create: `src/models/enums.py`
- Test: `tests/unit/models/test_enums.py`

- [ ] **Step 0: SPEC-003'i SPEC.md'ye ekle**

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/models/test_enums.py
from __future__ import annotations

import json

from src.models.enums import Confidence, Direction, EntryReason, ExitReason


def test_direction_values() -> None:
    assert Direction.BUY_YES.value == "BUY_YES"
    assert Direction.BUY_NO.value == "BUY_NO"
    assert Direction.HOLD.value == "HOLD"


def test_confidence_values() -> None:
    assert Confidence.A.value == "A"
    assert Confidence.B.value == "B"
    assert Confidence.C.value == "C"


def test_entry_reason_values() -> None:
    assert EntryReason.NORMAL.value == "normal"
    assert EntryReason.EARLY.value == "early"
    assert EntryReason.VOLATILITY_SWING.value == "volatility_swing"
    assert EntryReason.CONSENSUS.value == "consensus"


def test_exit_reason_values() -> None:
    assert ExitReason.STOP_LOSS.value == "stop_loss"
    assert ExitReason.SCALE_OUT.value == "scale_out"
    assert ExitReason.GRADUATED_SL.value == "graduated_sl"
    assert ExitReason.NEVER_IN_PROFIT.value == "never_in_profit"
    assert ExitReason.MARKET_FLIP.value == "market_flip"
    assert ExitReason.NEAR_RESOLVE.value == "near_resolve"
    assert ExitReason.HOLD_REVOKED.value == "hold_revoked"
    assert ExitReason.ULTRA_LOW_GUARD.value == "ultra_low_guard"
    assert ExitReason.CIRCUIT_BREAKER.value == "circuit_breaker"
    assert ExitReason.MANUAL.value == "manual"


def test_enum_str_mixin_json_serializable() -> None:
    payload = {
        "direction": Direction.BUY_YES,
        "confidence": Confidence.A,
        "entry_reason": EntryReason.NORMAL,
        "exit_reason": ExitReason.NEAR_RESOLVE,
    }
    encoded = json.dumps(payload)
    assert "BUY_YES" in encoded
    assert '"A"' in encoded
    assert "normal" in encoded
    assert "near_resolve" in encoded
```

- [ ] **Step 2: Testleri çalıştır → FAIL**

Run: `pytest tests/unit/models/test_enums.py -v`

- [ ] **Step 3: `src/models/enums.py` yaz**

```python
"""Domain enumerations (TDD §5.4). Tüm enum'lar str mixin — JSON serializable."""
from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    HOLD = "HOLD"


class Confidence(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class EntryReason(str, Enum):
    NORMAL = "normal"
    EARLY = "early"
    VOLATILITY_SWING = "volatility_swing"
    CONSENSUS = "consensus"


class ExitReason(str, Enum):
    STOP_LOSS = "stop_loss"
    SCALE_OUT = "scale_out"
    GRADUATED_SL = "graduated_sl"
    NEVER_IN_PROFIT = "never_in_profit"
    MARKET_FLIP = "market_flip"
    NEAR_RESOLVE = "near_resolve"
    HOLD_REVOKED = "hold_revoked"
    ULTRA_LOW_GUARD = "ultra_low_guard"
    CIRCUIT_BREAKER = "circuit_breaker"
    MANUAL = "manual"
```

- [ ] **Step 4: Test PASS doğrula**

Run: `pytest tests/unit/models/test_enums.py -v`
Expected: PASS (5/5).

- [ ] **Step 5: SPEC-003'ü SPEC.md'den sil**

- [ ] **Step 6: Commit**

```bash
git add src/models/enums.py tests/unit/models/test_enums.py SPEC.md
git commit -m "feat(models): Direction/Confidence/EntryReason/ExitReason enum'ları"
```

---

## Task 5: `src/models/market.py` — MarketData Modeli

**Amaç:** Gamma'dan parse edilen pazar verisinin Pydantic modeli (TDD §5.1).

**Eski Referans:** `../Polymarket Agent_Eski/src/models.py` line 25-48 — MarketData.
- **Migrate edilen değerler:** Field isimleri (condition_id, yes_token_id, no_token_id, yes_price, no_price, liquidity, volume_24h, tags, end_date_iso, event_id, event_live, event_ended, sport_tag, closed, resolved, accepting_orders, sports_market_type, odds_api_implied_prob).
- **Sıfırdan yazılan:** TDD §5.1 sadeleştirmesi — `description`, `accepting_orders_at` eski alanları çıkarılır (v2'de kullanılmıyor). `match_start_iso` TDD §5.1 şemasına göre default "".

**SPEC entry:**

```markdown
### SPEC-004: MarketData modeli
- **Dosya**: src/models/market.py
#### Davranış Kuralları
1. TDD §5.1 alanları birebir
2. yes_price/no_price 0.0-1.0 arası (validator yok, downstream guard'ı kontrol eder)
3. event_id Optional[str] — Gamma eski event'lerde None dönebilir
4. tags List[str]
5. sports_market_type sadece "moneyline" kabul gate'te kontrol edilir (bu modelde validator yok)

#### Test Senaryoları
- test_market_data_required_fields
- test_market_data_defaults
- test_market_data_json_roundtrip
```

**Files:**
- Create: `src/models/market.py`
- Test: `tests/unit/models/test_market.py`

- [ ] **Step 0: SPEC-004'ü SPEC.md'ye ekle**

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/models/test_market.py
from __future__ import annotations

import json

from src.models.market import MarketData


def _valid_market(**overrides) -> MarketData:
    base = {
        "condition_id": "0xabc",
        "question": "Will Lakers beat Celtics?",
        "slug": "lakers-vs-celtics",
        "yes_token_id": "tok1",
        "no_token_id": "tok2",
        "yes_price": 0.55,
        "no_price": 0.45,
        "liquidity": 12_000.0,
        "volume_24h": 5_000.0,
        "tags": ["basketball", "nba"],
        "end_date_iso": "2026-04-14T23:00:00Z",
    }
    base.update(overrides)
    return MarketData(**base)


def test_market_data_required_fields() -> None:
    m = _valid_market()
    assert m.condition_id == "0xabc"
    assert m.yes_price == 0.55
    assert "basketball" in m.tags


def test_market_data_defaults() -> None:
    m = _valid_market()
    assert m.event_id is None
    assert m.event_live is False
    assert m.event_ended is False
    assert m.match_start_iso == ""
    assert m.sport_tag == ""
    assert m.sports_market_type == ""
    assert m.closed is False
    assert m.resolved is False
    assert m.accepting_orders is True
    assert m.odds_api_implied_prob is None


def test_market_data_json_roundtrip() -> None:
    m = _valid_market(event_id="evt_1", sport_tag="basketball_nba")
    data = m.model_dump()
    reparsed = MarketData(**data)
    assert reparsed.event_id == "evt_1"
    assert reparsed.sport_tag == "basketball_nba"
    # str encoding
    blob = json.dumps(m.model_dump(mode="json"))
    assert "evt_1" in blob
```

- [ ] **Step 2: Test FAIL doğrula**

Run: `pytest tests/unit/models/test_market.py -v`

- [ ] **Step 3: `src/models/market.py` yaz**

```python
"""MarketData — Polymarket Gamma'dan gelen pazar verisi (TDD §5.1)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MarketData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    condition_id: str
    question: str
    slug: str
    yes_token_id: str
    no_token_id: str

    yes_price: float
    no_price: float
    liquidity: float
    volume_24h: float
    tags: list[str] = []

    end_date_iso: str
    match_start_iso: str = ""
    event_id: str | None = None

    event_live: bool = False
    event_ended: bool = False
    sport_tag: str = ""
    sports_market_type: str = ""

    closed: bool = False
    resolved: bool = False
    accepting_orders: bool = True
    odds_api_implied_prob: float | None = None
```

- [ ] **Step 4: Test PASS**

Run: `pytest tests/unit/models/test_market.py -v`

- [ ] **Step 5: SPEC-004'ü sil, commit**

```bash
git add src/models/market.py tests/unit/models/test_market.py SPEC.md
git commit -m "feat(models): MarketData Pydantic modeli (TDD §5.1)"
```

---

## Task 6: `src/models/position.py` — Position Modeli + P(YES) Validator

**Amaç:** TDD §5.2 Position modeli. ARCH Kural 7 (P(YES) anchor) validator seviyesinde zorunlu.

**Eski Referans:** `../Polymarket Agent_Eski/src/models.py` line 51-148 — Position.
- **Migrate edilen değerler:** Tüm field listesi (canlı durum, maç durumu, scale-out state, lossy reentry), `effective_price()` helper fonksiyonu (line 10-16), `anchor_probability` 0.01-0.99 validator mantığı.
- **Sıfırdan yazılan:** TDD §5.2'ye göre sadeleştirilmiş alan listesi (legacy `_migrate_ai_probability` çıkar, `scouted`, `pending_resolution`, `stale_unknown`, `hold_was_original`, `intended_size_usdc`, `scale_in_complete`, `price_history_buffer`, `force_scale_out_tier`, `live_on_clob`, `hold_revoked_at`, `category`, `is_consensus`, `number_of_games` v2'de kullanılmıyor — **çıkar**). `confidence` default "B" (eski "B-" çıkar). `computed_field` ile `current_value`, `unrealized_pnl_usdc`, `unrealized_pnl_pct` korunur.

**SPEC entry:**

```markdown
### SPEC-005: Position modeli
- **Dosya**: src/models/position.py
#### Davranış Kuralları
1. anchor_probability HER ZAMAN P(YES), 0.01-0.99 aralığında (validator zorunlu)
2. BUY_YES ve BUY_NO için aynı alan — yön ayarlaması yapılmaz
3. entry_timestamp default=now(UTC)
4. computed fields: current_value, unrealized_pnl_usdc, unrealized_pnl_pct
5. effective_price(yes_price, direction) helper: BUY_NO için (1 - yes_price)
6. confidence default "B"
7. Scale-out state: scale_out_tier, partial_exits, scale_out_realized_usdc

#### Test Senaryoları
- test_position_anchor_probability_out_of_range_raises
- test_position_anchor_probability_valid
- test_position_effective_price_buy_yes
- test_position_effective_price_buy_no
- test_position_unrealized_pnl_pct_calculation
- test_position_current_value_computed
- test_position_json_roundtrip
```

**Files:**
- Create: `src/models/position.py`
- Test: `tests/unit/models/test_position.py`

- [ ] **Step 0: SPEC-005'i ekle**

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/models/test_position.py
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models.position import Position, effective_price


def _valid(**overrides) -> Position:
    base = dict(
        condition_id="0x1",
        token_id="tok",
        direction="BUY_YES",
        entry_price=0.40,
        size_usdc=40.0,
        shares=100.0,
        current_price=0.40,
        anchor_probability=0.55,
    )
    base.update(overrides)
    return Position(**base)


def test_position_anchor_probability_valid() -> None:
    p = _valid(anchor_probability=0.55)
    assert p.anchor_probability == 0.55


def test_position_anchor_probability_too_low_raises() -> None:
    with pytest.raises(Exception):
        _valid(anchor_probability=0.005)


def test_position_anchor_probability_too_high_raises() -> None:
    with pytest.raises(Exception):
        _valid(anchor_probability=0.995)


def test_effective_price_buy_yes() -> None:
    assert effective_price(0.40, "BUY_YES") == 0.40


def test_effective_price_buy_no() -> None:
    assert abs(effective_price(0.40, "BUY_NO") - 0.60) < 1e-9


def test_position_unrealized_pnl_pct_buy_yes_profit() -> None:
    p = _valid(entry_price=0.40, current_price=0.50, shares=100.0, size_usdc=40.0)
    # current_value = 100 * 0.50 = 50
    # pnl = 50 - 40 = 10 → 25%
    assert abs(p.unrealized_pnl_pct - 0.25) < 1e-9


def test_position_unrealized_pnl_pct_buy_no_profit() -> None:
    p = _valid(direction="BUY_NO", entry_price=0.40, current_price=0.30, shares=100.0, size_usdc=40.0)
    # eff_current = 1 - 0.30 = 0.70 → current_value = 70, pnl = 30, pct = 0.75
    assert abs(p.unrealized_pnl_pct - 0.75) < 1e-9


def test_position_defaults() -> None:
    p = _valid()
    assert p.confidence == "B"
    assert p.scale_out_tier == 0
    assert p.partial_exits == []
    assert p.sl_reentry_count == 0
    assert p.ever_in_profit is False
    assert p.volatility_swing is False
    assert p.favored is False
    assert isinstance(p.entry_timestamp, datetime)


def test_position_json_roundtrip() -> None:
    p = _valid(confidence="A", event_id="evt_99")
    data = p.model_dump(mode="json")
    restored = Position(**data)
    assert restored.confidence == "A"
    assert restored.event_id == "evt_99"
    assert restored.anchor_probability == 0.55
```

- [ ] **Step 2: Test FAIL doğrula**

Run: `pytest tests/unit/models/test_position.py -v`

- [ ] **Step 3: `src/models/position.py` yaz**

```python
"""Position modeli (TDD §5.2). ARCH Kural 7: anchor_probability HER ZAMAN P(YES)."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


def effective_price(yes_price: float, direction: str) -> float:
    """BUY_YES → yes_price; BUY_NO → (1 - yes_price)."""
    return (1.0 - yes_price) if direction == "BUY_NO" else yes_price


class Position(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Giriş bilgileri
    condition_id: str
    token_id: str
    direction: str  # BUY_YES | BUY_NO
    entry_price: float
    size_usdc: float
    shares: float
    slug: str = ""
    entry_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entry_reason: str = ""
    confidence: str = "B"
    anchor_probability: float  # P(YES), 0.01-0.99 — validator aşağıda

    @field_validator("anchor_probability")
    @classmethod
    def _check_pyes(cls, v: float) -> float:
        if not (0.01 <= v <= 0.99):
            raise ValueError(
                f"anchor_probability={v} must be P(YES) in [0.01, 0.99]"
            )
        return v

    # Canlı durum
    current_price: float
    bid_price: float = 0.0
    peak_pnl_pct: float = 0.0
    peak_price: float = 0.0
    ever_in_profit: bool = False
    consecutive_down_cycles: int = 0
    cumulative_drop: float = 0.0
    previous_cycle_price: float = 0.0
    cycles_held: int = 0

    # Maç durumu
    sport_tag: str = ""
    event_id: str = ""
    match_start_iso: str = ""
    match_live: bool = False
    match_ended: bool = False
    match_score: str = ""
    match_period: str = ""
    question: str = ""
    end_date_iso: str = ""

    # Durum flag'leri
    favored: bool = False
    volatility_swing: bool = False

    # Scale-out state
    original_shares: float | None = None
    original_size_usdc: float | None = None
    partial_exits: list[dict] = []
    scale_out_tier: int = 0
    scale_out_realized_usdc: float = 0.0

    # Lossy reentry
    sl_reentry_count: int = 0

    # Bookmaker metadata
    bookmaker_prob: float = 0.0

    @computed_field
    @property
    def current_value(self) -> float:
        return self.shares * effective_price(self.current_price, self.direction)

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
```

- [ ] **Step 4: Test PASS**

Run: `pytest tests/unit/models/test_position.py -v`
Expected: PASS (9/9).

- [ ] **Step 5: SPEC sil, commit**

```bash
git add src/models/position.py tests/unit/models/test_position.py SPEC.md
git commit -m "feat(models): Position + effective_price + P(YES) validator (ARCH Kural 7)"
```

---

## Task 7: `src/models/signal.py` — Signal Modeli

**Amaç:** Entry karar sinyali (TDD §5.3).

**Eski Referans:** `../Polymarket Agent_Eski/src/models.py` line 151-167.
- **Migrate edilen:** `anchor_probability` validator mantığı, field isimleri.
- **Sıfırdan yazılan:** TDD §5.3'e göre `size_usdc`, `entry_reason: EntryReason`, `bookmaker_prob`, `sport_tag`, `event_id` ekleri.

**Files:**
- Create: `src/models/signal.py`
- Test: `tests/unit/models/test_signal.py`
- Edit: `src/models/__init__.py` (re-export)

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/models/test_signal.py
from __future__ import annotations

import pytest

from src.models.enums import Direction, EntryReason
from src.models.signal import Signal


def _valid(**overrides) -> Signal:
    base = dict(
        condition_id="0x1",
        direction=Direction.BUY_YES,
        anchor_probability=0.60,
        market_price=0.50,
        edge=0.10,
        confidence="B",
        size_usdc=40.0,
        entry_reason=EntryReason.NORMAL,
        bookmaker_prob=0.58,
    )
    base.update(overrides)
    return Signal(**base)


def test_signal_valid() -> None:
    s = _valid()
    assert s.direction == Direction.BUY_YES
    assert s.edge == 0.10
    assert s.entry_reason == EntryReason.NORMAL


def test_signal_anchor_probability_out_of_range_raises() -> None:
    with pytest.raises(Exception):
        _valid(anchor_probability=0.0)


def test_signal_default_sport_tag_and_event_id() -> None:
    s = _valid()
    assert s.sport_tag == ""
    assert s.event_id == ""
```

- [ ] **Step 2: FAIL doğrula**

- [ ] **Step 3: `src/models/signal.py` yaz**

```python
"""Entry karar sinyali (TDD §5.3)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from src.models.enums import Direction, EntryReason


class Signal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    condition_id: str
    direction: Direction
    anchor_probability: float  # P(YES)
    market_price: float
    edge: float
    confidence: str
    size_usdc: float
    entry_reason: EntryReason
    bookmaker_prob: float
    sport_tag: str = ""
    event_id: str = ""

    @field_validator("anchor_probability")
    @classmethod
    def _check_pyes(cls, v: float) -> float:
        if not (0.01 <= v <= 0.99):
            raise ValueError(f"anchor_probability={v} must be P(YES)")
        return v
```

- [ ] **Step 4: `src/models/__init__.py` re-export**

```python
"""Domain modelleri — public re-export."""
from src.models.enums import Confidence, Direction, EntryReason, ExitReason
from src.models.market import MarketData
from src.models.position import Position, effective_price
from src.models.signal import Signal

__all__ = [
    "Confidence",
    "Direction",
    "EntryReason",
    "ExitReason",
    "MarketData",
    "Position",
    "Signal",
    "effective_price",
]
```

- [ ] **Step 5: Re-export sağlığını doğrula**

Run: `python -c "from src.models import MarketData, Position, Signal, Direction, Confidence, EntryReason, ExitReason, effective_price; print('OK')"`
Expected: `OK`.

- [ ] **Step 6: Tüm model testlerini çalıştır**

Run: `pytest tests/unit/models/ -v`
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add src/models/signal.py src/models/__init__.py tests/unit/models/test_signal.py
git commit -m "feat(models): Signal modeli + public __init__ re-export"
```

---

## Task 8: `src/infrastructure/persistence/json_store.py` — Atomic JSON Store

**Amaç:** Pozisyon/state JSON okuma/yazma için atomic (tmp→replace) helper. Çoklu tüketici kullanır (portfolio, state dosyaları).

**Eski Referans:** `../Polymarket Agent_Eski/src/portfolio.py` line 38-59 — `_load_positions`, `_save_positions` pattern'ı (atomic tmp write + replace).
- **Migrate edilen değer:** Atomic tmp-write pattern (`tmp.write_text → tmp.replace(path)`), mkdir-parents, encoding="utf-8", `indent=2`, `default=str`.
- **Sıfırdan yazılan:** Portfolio'ya bağımsız generic `JsonStore` class — herhangi bir path'e generic `dict` read/write.

**SPEC entry:**

```markdown
### SPEC-006: JsonStore (generic JSON read/write, atomic)
- **Dosya**: src/infrastructure/persistence/json_store.py
#### Davranış Kuralları
1. `load(default)`: dosya yoksa default döner; bozuk JSON → default + warning log
2. `save(data)`: tmp dosyaya yaz, sonra os.replace → atomic
3. `encoding="utf-8"`, `indent=2`, `default=str` (datetime, enum)
4. Parent dizin yoksa oluştur
5. `exists()` helper

#### Test Senaryoları
- test_json_store_save_load_roundtrip
- test_json_store_load_missing_returns_default
- test_json_store_load_corrupt_returns_default
- test_json_store_save_atomic_tmp_cleanup
- test_json_store_handles_datetime_via_default_str
```

**Files:**
- Create: `src/infrastructure/persistence/json_store.py`
- Test: `tests/unit/infrastructure/persistence/test_json_store.py`

- [ ] **Step 0: SPEC-006 ekle**

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/infrastructure/persistence/test_json_store.py
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.infrastructure.persistence.json_store import JsonStore


def test_save_load_roundtrip(tmp_path: Path) -> None:
    store = JsonStore(tmp_path / "state.json")
    store.save({"bankroll": 1000.0, "mode": "dry_run"})
    data = store.load(default={})
    assert data["bankroll"] == 1000.0
    assert data["mode"] == "dry_run"


def test_load_missing_returns_default(tmp_path: Path) -> None:
    store = JsonStore(tmp_path / "nope.json")
    assert store.load(default={"x": 1}) == {"x": 1}


def test_load_corrupt_returns_default(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    store = JsonStore(p)
    assert store.load(default={"ok": True}) == {"ok": True}


def test_save_creates_parent_dir(tmp_path: Path) -> None:
    p = tmp_path / "nested" / "dir" / "state.json"
    store = JsonStore(p)
    store.save({"a": 1})
    assert p.exists()


def test_save_atomic_no_tmp_leftover(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    store = JsonStore(p)
    store.save({"a": 1})
    tmps = list(tmp_path.glob("*.tmp"))
    assert tmps == []


def test_save_handles_datetime_default_str(tmp_path: Path) -> None:
    store = JsonStore(tmp_path / "t.json")
    store.save({"ts": datetime(2026, 4, 13, tzinfo=timezone.utc)})
    data = store.load(default={})
    assert "2026-04-13" in data["ts"]


def test_exists(tmp_path: Path) -> None:
    store = JsonStore(tmp_path / "state.json")
    assert store.exists() is False
    store.save({})
    assert store.exists() is True
```

- [ ] **Step 2: FAIL**

Run: `pytest tests/unit/infrastructure/persistence/test_json_store.py -v`

- [ ] **Step 3: Implementasyon yaz**

```python
# src/infrastructure/persistence/json_store.py
"""Atomic JSON read/write helper for state files."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JsonStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def exists(self) -> bool:
        return self.path.exists()

    def load(self, default: Any) -> Any:
        if not self.path.exists():
            return default
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("JsonStore.load(%s) failed: %s — returning default", self.path, e)
            return default

    def save(self, data: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(self.path)
```

- [ ] **Step 4: PASS**

Run: `pytest tests/unit/infrastructure/persistence/test_json_store.py -v`

- [ ] **Step 5: SPEC sil, commit**

```bash
git add src/infrastructure/persistence/json_store.py tests/unit/infrastructure/persistence/test_json_store.py SPEC.md
git commit -m "feat(persistence): JsonStore atomic read/write helper"
```

---

## Task 9: `src/infrastructure/persistence/trade_logger.py` — Zengin Trade Case-Study Log

**Amaç:** Her bir maç trade'ini **eksiksiz bir case study** olarak tek bir yerde logla. Testlerde ve karar analizinde referans olacak — giriş verisi, maç ilerleyişi, çıkış, ve biz çıktıktan sonra maçın nasıl sonuçlandığı dahil.

**Kullanıcı şartı (2026-04-13):**
> "Her maç trade'i ayrı bir şekilde, tek bir yerde, doğru biçimde loglansın. Kaçtan girdiğimiz, branş, lig, maç nasıl ilerledi, biz çıktıktan sonra maç sonucu ne oldu dahil **her şey** loglansın."

**Dosya konumu:** `logs/trade_history.jsonl` — bot.log'dan ayrı. Her satır bir maç trade'inin **tam yaşam döngüsü** kaydı.

**Eski Referans:** `../Polymarket Agent_Eski/src/trade_logger.py` (105 satır).
- **Migrate edilen:** Tail-read algoritması (512 byte/line tahmini), append-only JSONL yazma pattern'ı, `json.dumps(default=str)`.
- **Sıfırdan yazılan:** Kayıt şeması **çok daha zengin** — eski dosya basit "event" dict'i atıyordu; biz typed `TradeRecord` Pydantic modeli + entry/exit/resolution üç katmanlı kayıt tutuyoruz. Archive path eski özellik çıkarıldı (YAGNI).

**Kayıt Şeması (TradeRecord):**

| Alan | Açıklama | Ne zaman dolar? |
|---|---|---|
| `slug`, `condition_id`, `event_id`, `token_id` | Market kimliği | Entry |
| `sport_category` | Branş — "basketball", "football", "hockey", "baseball", "tennis", "golf" | Entry |
| `league` | Lig — "nba", "ncaab", "nfl", "nhl", "mlb", "atp", "lpga" vs. | Entry |
| `sport_tag` | Ham Odds API key — "basketball_nba", "tennis_atp_french_open" | Entry |
| `direction` | BUY_YES veya BUY_NO | Entry |
| `entry_price` | **Kaçtan girdik** (effective price: BUY_YES→yes_price, BUY_NO→1-yes_price) | Entry |
| `size_usdc`, `shares` | Pozisyon büyüklüğü | Entry |
| `confidence` | A / B | Entry |
| `bookmaker_prob`, `anchor_probability` | Bookmaker P(YES), giriş P(YES) | Entry |
| `num_bookmakers` | Toplam bookmaker ağırlığı (TDD §6.1) — kaç bookmaker'dan veri aldık | Entry |
| `has_sharp` | Pinnacle / Betfair Exchange gibi sharp book var mı (A-confidence kaynağı) | Entry |
| `entry_reason` | normal / early / volatility_swing / consensus | Entry |
| `entry_timestamp` | ISO UTC | Entry |
| `match_timeline` | **Maç nasıl ilerledi** — list of {ts, score, period, current_price, bid_price, pnl_pct} | Light cycle (Faz 4+) |
| `exit_price`, `exit_reason` | Çıkış verileri | Exit |
| `exit_pnl_usdc`, `exit_pnl_pct` | Realized PnL | Exit |
| `exit_timestamp` | ISO UTC | Exit |
| `final_outcome` | **Biz çıktıktan sonra maç sonucu**: "YES" / "NO" / "unresolved" | Resolution fetch (Faz 5+) |
| `we_were_right` | bool — direction ile final_outcome eşleşti mi | Resolution fetch |
| `resolution_timestamp`, `resolution_source` | Resolution metadata | Resolution fetch |

**Faz 1'de tamamlanan:** `TradeRecord` modeli + `TradeHistoryLogger.log(record)` + `read_recent(n)` + `read_all()`. `match_timeline` alanı boş liste olarak başlar, Faz 4 exit monitor'da doldurulur. `final_outcome` "unresolved" default, Faz 5 resolution job'u güncelleyecek. **Faz 1'de şema sabitleniyor ki downstream fazlarda alan eklemeye gerek kalmasın.**

**Branş/lig türetme stratejisi:** `sport_tag` (örn. `basketball_nba`) → `sport_category="basketball"`, `league="nba"`. Basit `split("_", 1)` mantığı. Türetme yardımcısı `_split_sport_tag(tag)` helper olarak aynı dosyada. `tennis_*` → category="tennis", league=tag'in `tennis_` sonrası (örn. `atp_french_open`).

**SPEC entry:**

```markdown
### SPEC-NEW: TradeHistoryLogger — zengin trade case-study log
- **Durum**: DRAFT
- **Tarih**: 2026-04-13
- **İlgili Plan**: PLAN-001 Task 9
- **Katman**: infrastructure/persistence
- **Dosya**: src/infrastructure/persistence/trade_logger.py

#### Amaç
Her maç trade'ini tek satır-tek kayıt olarak, yaşam döngüsü boyunca tüm metadata ile logla. `logs/trade_history.jsonl`.

#### Davranış Kuralları
1. TradeRecord Pydantic modeli: entry + match_timeline (liste) + exit + resolution
2. `log(record: TradeRecord)` — JSONL'a append, atomic değil (append-only)
3. `read_recent(n)` — tail-read, son N kayıt
4. `read_all()` — tüm dosya (küçük dosya varsayımı)
5. Dosya yoksa parent dizin oluştur
6. `final_outcome` başlangıçta "unresolved", Faz 5+ tarafından güncellenir
7. `sport_category`, `league` — `sport_tag`'dan türev; `_split_sport_tag` helper ile tutarlı

#### Sınır Durumları
- tag="" → category="", league=""
- tag="basketball_nba" → category="basketball", league="nba"
- tag="tennis_atp_french_open" → category="tennis", league="atp_french_open"
- match_timeline default empty list — Faz 4'e kadar boş kalır
- exit alanları None/empty — trade henüz kapanmadıysa (Faz 1'de MVP kullanımı: sadece kapanan trade'ler logla)

#### Test Senaryoları
- test_trade_record_entry_fields_required
- test_trade_record_match_timeline_default_empty
- test_trade_record_resolution_default_unresolved
- test_split_sport_tag_basketball_nba
- test_split_sport_tag_tennis_dynamic
- test_split_sport_tag_empty_returns_empty
- test_logger_log_appends_jsonl_line
- test_logger_read_recent_returns_last_n
- test_logger_read_all
- test_logger_missing_file_returns_empty
- test_logger_creates_parent_dir
```

**Files:**
- Create: `src/infrastructure/persistence/trade_logger.py`
- Test: `tests/unit/infrastructure/persistence/test_trade_logger.py`

- [ ] **Step 0: SPEC'i SPEC.md'ye DRAFT olarak ekle**

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/infrastructure/persistence/test_trade_logger.py
from __future__ import annotations

from pathlib import Path

import pytest

from src.infrastructure.persistence.trade_logger import (
    TradeHistoryLogger,
    TradeRecord,
    _split_sport_tag,
)


def _valid_record(**overrides) -> TradeRecord:
    base = dict(
        slug="lakers-vs-celtics",
        condition_id="0xabc",
        event_id="evt_1",
        token_id="tokY",
        sport_tag="basketball_nba",
        sport_category="basketball",
        league="nba",
        direction="BUY_YES",
        entry_price=0.45,
        size_usdc=40.0,
        shares=88.88,
        confidence="B",
        bookmaker_prob=0.58,
        anchor_probability=0.58,
        num_bookmakers=12.0,
        has_sharp=True,
        entry_reason="normal",
        entry_timestamp="2026-04-13T20:00:00Z",
    )
    base.update(overrides)
    return TradeRecord(**base)


def test_split_sport_tag_basketball_nba() -> None:
    cat, lg = _split_sport_tag("basketball_nba")
    assert cat == "basketball"
    assert lg == "nba"


def test_split_sport_tag_tennis_dynamic() -> None:
    cat, lg = _split_sport_tag("tennis_atp_french_open")
    assert cat == "tennis"
    assert lg == "atp_french_open"


def test_split_sport_tag_empty_returns_empty() -> None:
    assert _split_sport_tag("") == ("", "")


def test_split_sport_tag_no_underscore() -> None:
    assert _split_sport_tag("basketball") == ("basketball", "")


def test_trade_record_entry_fields() -> None:
    r = _valid_record()
    assert r.slug == "lakers-vs-celtics"
    assert r.entry_price == 0.45
    assert r.sport_category == "basketball"
    assert r.league == "nba"
    assert r.confidence == "B"


def test_trade_record_bookmaker_fields() -> None:
    r = _valid_record(num_bookmakers=15.5, has_sharp=True)
    assert r.num_bookmakers == 15.5
    assert r.has_sharp is True
    # Default'lar
    r2 = _valid_record()
    r2_dict = r2.model_dump()
    # _valid_record default num_bookmakers=12.0 has_sharp=True
    assert r2.num_bookmakers == 12.0
    assert r2.has_sharp is True


def test_trade_record_match_timeline_default_empty() -> None:
    r = _valid_record()
    assert r.match_timeline == []


def test_trade_record_resolution_default_unresolved() -> None:
    r = _valid_record()
    assert r.final_outcome == "unresolved"
    assert r.we_were_right is None
    assert r.resolution_timestamp == ""


def test_trade_record_exit_defaults() -> None:
    r = _valid_record()
    assert r.exit_price is None
    assert r.exit_reason == ""
    assert r.exit_pnl_usdc == 0.0


def test_trade_record_full_lifecycle_json_roundtrip() -> None:
    r = _valid_record(
        match_timeline=[
            {"ts": "2026-04-13T20:15:00Z", "score": "12-8", "period": "Q1", "current_price": 0.48, "pnl_pct": 0.067},
            {"ts": "2026-04-13T20:45:00Z", "score": "45-40", "period": "Q2", "current_price": 0.55, "pnl_pct": 0.222},
        ],
        exit_price=0.52,
        exit_reason="scale_out",
        exit_pnl_usdc=6.22,
        exit_pnl_pct=0.155,
        exit_timestamp="2026-04-13T21:00:00Z",
        final_outcome="YES",
        we_were_right=True,
        resolution_timestamp="2026-04-13T22:30:00Z",
        resolution_source="gamma",
    )
    data = r.model_dump(mode="json")
    restored = TradeRecord(**data)
    assert restored.match_timeline[0]["score"] == "12-8"
    assert restored.final_outcome == "YES"
    assert restored.we_were_right is True


def test_logger_log_appends_jsonl_line(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "trade_history.jsonl"))
    log.log(_valid_record(slug="a-b"))
    log.log(_valid_record(slug="c-d"))
    rows = log.read_recent(10)
    assert len(rows) == 2
    assert rows[0]["slug"] == "a-b"
    assert rows[1]["slug"] == "c-d"


def test_logger_read_recent_last_n(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "t.jsonl"))
    for i in range(20):
        log.log(_valid_record(slug=f"m-{i}"))
    recent = log.read_recent(5)
    assert len(recent) == 5
    assert recent[-1]["slug"] == "m-19"
    assert recent[0]["slug"] == "m-15"


def test_logger_read_all(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "t.jsonl"))
    log.log(_valid_record(slug="x"))
    log.log(_valid_record(slug="y"))
    rows = log.read_all()
    assert len(rows) == 2


def test_logger_missing_file_returns_empty(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "nope.jsonl"))
    assert log.read_recent(10) == []
    assert log.read_all() == []


def test_logger_creates_parent_dir(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "deep" / "nested" / "t.jsonl"))
    log.log(_valid_record())
    assert (tmp_path / "deep" / "nested" / "t.jsonl").exists()
```

- [ ] **Step 2: FAIL**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: `src/infrastructure/persistence/trade_logger.py` yaz**

```python
"""Zengin trade case-study logger — her maç trade'i tek kayıt (JSONL).

Kayıt bir maç trade'inin TÜM yaşam döngüsünü tutar:
  - Entry: kaçtan girdik, branş, lig, confidence, bookmaker prob
  - match_timeline: maç ilerlerken skor/fiyat snapshot'ları (Faz 4+)
  - Exit: çıkış fiyatı, sebep, PnL
  - Resolution: biz çıktıktan sonra maç sonucu (Faz 5+)

Testlerde ve karar analizinde referans olarak kullanılır.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

_TAIL_BYTES_PER_LINE = 1000  # Zengin kayıt → daha büyük tahmin


def _split_sport_tag(sport_tag: str) -> tuple[str, str]:
    """'basketball_nba' → ('basketball', 'nba'). 'tennis_atp_french_open' → ('tennis', 'atp_french_open').
    Boş → ('', ''). Underscore yoksa → (tag, '').
    """
    tag = (sport_tag or "").strip()
    if not tag:
        return "", ""
    if "_" not in tag:
        return tag, ""
    category, rest = tag.split("_", 1)
    return category, rest


class TradeRecord(BaseModel):
    """Bir maç trade'inin tam yaşam döngüsü kaydı."""
    model_config = ConfigDict(extra="ignore")

    # ── Market kimliği ──
    slug: str
    condition_id: str
    event_id: str
    token_id: str

    # ── Branş & lig ──
    sport_tag: str           # Ham Odds API key
    sport_category: str      # "basketball"
    league: str              # "nba"

    # ── Giriş ──
    direction: str           # BUY_YES | BUY_NO
    entry_price: float       # Kaçtan girdik (effective price)
    size_usdc: float
    shares: float
    confidence: str          # A | B
    bookmaker_prob: float    # Giriş anı bookmaker P(YES)
    anchor_probability: float  # Giriş anı P(YES)
    num_bookmakers: float = 0.0  # Kaç bookmaker'dan veri aldık (TDD §6.1 ağırlıklı)
    has_sharp: bool = False      # Pinnacle/Betfair Exchange var mı
    entry_reason: str        # normal | early | volatility_swing | consensus
    entry_timestamp: str     # ISO UTC

    # ── Maç ilerleyişi (Faz 4+'te doldurulur) ──
    match_timeline: list[dict] = []

    # ── Çıkış ──
    exit_price: float | None = None
    exit_reason: str = ""
    exit_pnl_usdc: float = 0.0
    exit_pnl_pct: float = 0.0
    exit_timestamp: str = ""

    # ── Resolution (Faz 5+'te doldurulur) ──
    final_outcome: str = "unresolved"   # "YES" | "NO" | "unresolved"
    we_were_right: bool | None = None
    resolution_timestamp: str = ""
    resolution_source: str = ""         # "gamma" | "manual" | ...


class TradeHistoryLogger:
    """Append-only JSONL: her satır = bir TradeRecord."""

    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: TradeRecord) -> None:
        line = record.model_dump_json() + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_recent(self, n: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            with open(self.path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                chunk_size = min(size, n * _TAIL_BYTES_PER_LINE)
                f.seek(size - chunk_size)
                raw = f.read().decode("utf-8", errors="replace")
            lines = [l for l in raw.strip().split("\n") if l.strip()]
            if chunk_size < size and lines:
                lines = lines[1:]  # first line may be partial
            out: list[dict[str, Any]] = []
            for l in lines[-n:]:
                try:
                    out.append(json.loads(l))
                except json.JSONDecodeError:
                    continue
            return out
        except OSError as e:
            logger.warning("TradeHistoryLogger.read_recent failed: %s", e)
            return []

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for l in self.path.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        return out
```

- [ ] **Step 4: PASS**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py -v`
Expected: PASS (13/13).

- [ ] **Step 5: ARCH check — satır sayısı < 400, domain/strategy import yok**

Run: `python -c "print(sum(1 for _ in open('src/infrastructure/persistence/trade_logger.py', encoding='utf-8')))"`
Expected: < 400.

- [ ] **Step 6: SPEC sil, commit**

```bash
git add src/infrastructure/persistence/trade_logger.py tests/unit/infrastructure/persistence/test_trade_logger.py SPEC.md
git commit -m "feat(persistence): TradeHistoryLogger — zengin trade case-study log (entry+timeline+exit+resolution)"
```

**Downstream fazlara not:**
- Faz 4 (exit pipeline): Light cycle'da pozisyon güncellendiğinde `match_timeline` dict'i position'a eklenir, exit anında tüm liste TradeRecord'a kopyalanır.
- Faz 5 (orchestration): Resolved trade'ler için ayrı resolution job'u Gamma'dan `resolved=true` + outcome fetch eder, `trade_history.jsonl`'i rewrite ederek `final_outcome` + `we_were_right` alanlarını doldurur.

<!-- Eski Task 9 yorum bloğu (deprecated — silinebilir):

**Eski Referans:** `../Polymarket Agent_Eski/src/trade_logger.py` (105 satır).
- **Migrate edilen:** `TradeLogger` class yapısı, tail-read algoritması (512 byte/line tahmini, son chunk okuma), append-mode JSONL yazımı, timestamp auto-fill, `default=str` JSON encoding.
- **Sıfırdan yazılan:** Archive path yok (eski özellik MVP'de gereksiz), sadece single-path logging. `read_all()` sadeleştirilir.

**Files:**
- Create: `src/infrastructure/persistence/trade_logger.py`
- Test: `tests/unit/infrastructure/persistence/test_trade_logger.py`

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/infrastructure/persistence/test_trade_logger.py
from __future__ import annotations

from pathlib import Path

from src.infrastructure.persistence.trade_logger import TradeLogger


def test_log_appends_single_line(tmp_path: Path) -> None:
    tl = TradeLogger(str(tmp_path / "trades.jsonl"))
    tl.log({"event": "entry", "slug": "lakers-celtics", "size": 40.0})
    tl.log({"event": "exit", "slug": "lakers-celtics", "pnl": 5.0})
    rows = tl.read_recent(10)
    assert len(rows) == 2
    assert rows[0]["event"] == "entry"
    assert rows[1]["pnl"] == 5.0


def test_log_autofills_timestamp(tmp_path: Path) -> None:
    tl = TradeLogger(str(tmp_path / "trades.jsonl"))
    tl.log({"event": "x"})
    row = tl.read_recent(1)[0]
    assert "timestamp" in row
    assert row["timestamp"]  # non-empty ISO string


def test_read_recent_empty_file_returns_empty_list(tmp_path: Path) -> None:
    tl = TradeLogger(str(tmp_path / "nonexistent.jsonl"))
    assert tl.read_recent(10) == []


def test_log_preserves_explicit_timestamp(tmp_path: Path) -> None:
    tl = TradeLogger(str(tmp_path / "t.jsonl"))
    tl.log({"event": "x", "timestamp": "2026-04-13T00:00:00Z"})
    row = tl.read_recent(1)[0]
    assert row["timestamp"] == "2026-04-13T00:00:00Z"


def test_read_recent_returns_last_n(tmp_path: Path) -> None:
    tl = TradeLogger(str(tmp_path / "t.jsonl"))
    for i in range(50):
        tl.log({"i": i})
    recent = tl.read_recent(5)
    assert len(recent) == 5
    assert recent[-1]["i"] == 49
    assert recent[0]["i"] == 45


def test_log_creates_parent_dir(tmp_path: Path) -> None:
    tl = TradeLogger(str(tmp_path / "deep" / "dir" / "t.jsonl"))
    tl.log({"event": "x"})
    assert (tmp_path / "deep" / "dir" / "t.jsonl").exists()
```

- [ ] **Step 2: FAIL**

- [ ] **Step 3: Implementasyon yaz**

```python
# src/infrastructure/persistence/trade_logger.py
"""Append-only JSONL trade event logger."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TAIL_BYTES_PER_LINE = 500  # Tail-read boyutunu tahmin


class TradeLogger:
    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, data: dict[str, Any]) -> None:
        data = {**data}
        data.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        line = json.dumps(data, default=str) + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_recent(self, n: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            with open(self.path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                chunk_size = min(size, n * _TAIL_BYTES_PER_LINE)
                f.seek(size - chunk_size)
                raw = f.read().decode("utf-8", errors="replace")
            lines = [l for l in raw.strip().split("\n") if l.strip()]
            if chunk_size < size and lines:
                lines = lines[1:]  # first line may be partial
            out: list[dict[str, Any]] = []
            for l in lines[-n:]:
                try:
                    out.append(json.loads(l))
                except json.JSONDecodeError:
                    continue
            return out
        except OSError as e:
            logger.warning("TradeLogger.read_recent failed: %s", e)
            return []
```

- [ ] **Step 4: PASS**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/persistence/trade_logger.py tests/unit/infrastructure/persistence/test_trade_logger.py
git commit -m "feat(persistence): TradeLogger JSONL append-only + tail read"
```

-->

---

## Task 10: `src/infrastructure/persistence/price_history.py` — Price History Saver

**Amaç:** Pozisyon kapandığında CLOB price history'yi çekip post-mortem kayıt olarak diske yaz. Kalibrasyon ve analiz için.

**Eski Referans:** `../Polymarket Agent_Eski/src/price_history.py` (66 satır).
- **Migrate edilen:** URL ("https://clob.polymarket.com/prices-history"), params (`market`, `interval=max`, `fidelity=60`), kayıt şeması (slug, entry_price, exit_price, exit_reason, price_history list).
- **Sıfırdan yazılan:** Class-based yapı (test için DI kolaylığı), `http_get` callable dep injection — infra test'inde mock'lanabilir. MVP için `number_of_games` çıkar (v2 yok).

**SPEC entry:**

```markdown
### SPEC-007: Price History Saver
- **Dosya**: src/infrastructure/persistence/price_history.py
#### Davranış Kuralları
1. Exit sırasında çağrılır, CLOB prices-history endpoint'ten veri çeker
2. Dosya adı: {slug_safe[:80]}_{UTC_timestamp}.json
3. HTTP error → sessizce warning log, raise etme (exit akışını bozmamalı — ARCH Kural 12: infra try/except)
4. Dizin: logs/price_history/
5. `http_get` parametrik (test DI)

#### Test Senaryoları
- test_save_happy_path_writes_file
- test_save_http_error_logs_warning
- test_save_non_200_skips
- test_save_slug_sanitization
```

**Files:**
- Create: `src/infrastructure/persistence/price_history.py`
- Test: `tests/unit/infrastructure/persistence/test_price_history.py`

- [ ] **Step 0: SPEC-007'yi ekle**

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/infrastructure/persistence/test_price_history.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from src.infrastructure.persistence.price_history import PriceHistorySaver


def _mock_response(status: int = 200, body: Any = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body or {"history": [{"t": 1, "p": 0.5}, {"t": 2, "p": 0.6}]}
    return resp


def test_save_happy_path_writes_file(tmp_path: Path) -> None:
    http = MagicMock(return_value=_mock_response())
    saver = PriceHistorySaver(base_dir=tmp_path, http_get=http)
    saver.save(
        slug="lakers-vs-celtics",
        token_id="tok123",
        entry_price=0.40,
        exit_price=0.48,
        exit_reason="scale_out",
        match_score="10-5",
    )
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8"))
    assert record["slug"] == "lakers-vs-celtics"
    assert record["entry_price"] == 0.40
    assert record["exit_price"] == 0.48
    assert record["exit_reason"] == "scale_out"
    assert len(record["price_history"]) == 2


def test_save_http_error_swallowed(tmp_path: Path) -> None:
    http = MagicMock(side_effect=RuntimeError("timeout"))
    saver = PriceHistorySaver(base_dir=tmp_path, http_get=http)
    # Should NOT raise
    saver.save(slug="x", token_id="t", entry_price=0.3, exit_price=0.2, exit_reason="sl", match_score="")
    assert list(tmp_path.glob("*.json")) == []


def test_save_non_200_skips(tmp_path: Path) -> None:
    http = MagicMock(return_value=_mock_response(status=500))
    saver = PriceHistorySaver(base_dir=tmp_path, http_get=http)
    saver.save(slug="x", token_id="t", entry_price=0.3, exit_price=0.2, exit_reason="sl", match_score="")
    assert list(tmp_path.glob("*.json")) == []


def test_save_slug_sanitization(tmp_path: Path) -> None:
    http = MagicMock(return_value=_mock_response())
    saver = PriceHistorySaver(base_dir=tmp_path, http_get=http)
    saver.save(slug="a/b/c weird", token_id="t", entry_price=0.3, exit_price=0.2, exit_reason="sl", match_score="")
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert "/" not in files[0].name
```

- [ ] **Step 2: FAIL**

- [ ] **Step 3: Implementasyon yaz**

```python
# src/infrastructure/persistence/price_history.py
"""CLOB price-history collector (exit sonrası post-mortem kayıt)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

_CLOB_HISTORY_URL = "https://clob.polymarket.com/prices-history"
_DEFAULT_TIMEOUT_SEC = 15


def _default_http_get(url: str, params: dict, timeout: int) -> Any:
    return requests.get(url, params=params, timeout=timeout)


class PriceHistorySaver:
    def __init__(
        self,
        base_dir: Path | str = Path("logs/price_history"),
        http_get: Callable[..., Any] = _default_http_get,
    ) -> None:
        self.base_dir = Path(base_dir)
        self._http_get = http_get

    def save(
        self,
        slug: str,
        token_id: str,
        entry_price: float,
        exit_price: float,
        exit_reason: str,
        match_score: str,
        match_start_iso: str = "",
        ever_in_profit: bool = False,
        peak_pnl_pct: float = 0.0,
    ) -> None:
        try:
            resp = self._http_get(
                _CLOB_HISTORY_URL,
                params={"market": token_id, "interval": "max", "fidelity": "60"},
                timeout=_DEFAULT_TIMEOUT_SEC,
            )
            if resp.status_code != 200:
                logger.warning("price_history fetch %s status=%d", slug[:30], resp.status_code)
                return
            history = resp.json().get("history", [])
        except Exception as e:
            logger.warning("price_history fetch failed for %s: %s", slug[:30], e)
            return

        record = {
            "slug": slug,
            "token_id": token_id,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "match_start_iso": match_start_iso,
            "ever_in_profit": ever_in_profit,
            "peak_pnl_pct": peak_pnl_pct,
            "match_score": match_score,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "price_history": history,
        }

        self.base_dir.mkdir(parents=True, exist_ok=True)
        safe = slug.replace("/", "_").replace(" ", "_")[:80]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self.base_dir / f"{safe}_{ts}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        logger.info("Saved price history: %s (%d points)", slug[:30], len(history))
```

- [ ] **Step 4: PASS**

Run: `pytest tests/unit/infrastructure/persistence/test_price_history.py -v`

- [ ] **Step 5: SPEC sil, commit**

```bash
git add src/infrastructure/persistence/price_history.py tests/unit/infrastructure/persistence/test_price_history.py SPEC.md
git commit -m "feat(persistence): PriceHistorySaver CLOB history collector"
```

---

## Task 11: `src/infrastructure/apis/gamma_client.py` — Polymarket Gamma Client

**Amaç:** Polymarket Gamma API'den event + market ham verisini çekip `MarketData` listesine dönüştür. Tag-based discovery (league tags).

**Eski Referans:** `../Polymarket Agent_Eski/src/market_scanner.py` (469 satır) — bu dosya scanner + parsing + filtering karışık. Faz 1'de sadece HTTP istemci + parse kısmı lazım. Filter/enrichment orkestrasyon katmanında (Faz 5) olacak.
- **Migrate edilen:** `GAMMA_BASE = "https://gamma-api.polymarket.com"`, `/events` endpoint parametreleri (`tag_id`, `active=true`, `closed=false`, `limit`, `offset`, `end_date_min`), `EVENTS_PER_PAGE=200`, `PARENT_TAGS=[("sports", 1), ("esports", 64)]`, `/sports` league-tags discovery + 6h cache pattern.
- **Sıfırdan yazılan:** `GammaClient` class (eski scanner'dan ayrılır — scanner Faz 5'te orchestration olacak). Sadece ham veriyi çeker ve `MarketData` oluşturur; filtering Faz 5'te ayrı. MVP için esports tag'leri filtrelenir — sadece `sports` parent + league tags. `_parse_market` yardımcısı: Gamma raw dict'i `MarketData`'ya çevirir (yes_token_id/no_token_id/yes_price/no_price açılımı).

**ARCH kontrol:** Infrastructure katmanında `import requests` SERBEST (Kural 2 sadece domain için). Bu dosya `src/models/MarketData` import ediyor — bu SERBEST (infra → models, model katmanı Pydantic data-definition, altyapı kullanabilir). Strategy/domain import ediyor MU? Hayır — sadece models. OK.

**SPEC entry:**

```markdown
### SPEC-008: Gamma Client (Polymarket market discovery)
- **Dosya**: src/infrastructure/apis/gamma_client.py
#### Davranış Kuralları
1. /sports endpoint → league tag_id discovery (6h cache)
2. /events?tag_id=X&active=true&closed=false → page by page (limit=200, offset)
3. Parent tag fallback: (sports=1, esports=64) — ama MVP'de esports kullanılmaz
4. HTTP error → warning log, empty list döner (exit akışını bozmasın)
5. `_parse_market(raw) → MarketData | None`: gerekli field eksikse None
6. Per-event meta: event_live, event_ended, sport_tag, event_id raw market'e iliştirilir

#### Girdi/Çıktı
- fetch_events() → list[MarketData]

#### Test Senaryoları
- test_gamma_fetch_happy_path
- test_gamma_parse_market_valid
- test_gamma_parse_market_missing_fields_returns_none
- test_gamma_http_error_returns_empty
- test_gamma_sports_endpoint_caches_6h
- test_gamma_paginates_until_empty
```

**Files:**
- Create: `src/infrastructure/apis/gamma_client.py`
- Test: `tests/unit/infrastructure/apis/test_gamma_client.py`

- [ ] **Step 0: SPEC-008 ekle**

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/infrastructure/apis/test_gamma_client.py
from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

from src.infrastructure.apis.gamma_client import GAMMA_BASE, GammaClient


def _resp(status: int = 200, body: Any = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.raise_for_status = MagicMock(return_value=None) if status < 400 else MagicMock(side_effect=RuntimeError("http"))
    r.json.return_value = body or []
    return r


def _event(cid: str, **market_overrides) -> dict:
    market = {
        "conditionId": cid,
        "question": "Q?",
        "slug": "a-vs-b",
        "clobTokenIds": '["tokY", "tokN"]',
        "outcomePrices": '["0.60", "0.40"]',
        "liquidity": "5000",
        "volume24hr": "1000",
        "endDate": "2026-04-14T00:00:00Z",
        "closed": False,
        "acceptingOrders": True,
    }
    market.update(market_overrides)
    return {
        "id": "evt_1",
        "live": False,
        "ended": False,
        "startTime": "2026-04-13T20:00:00Z",
        "markets": [market],
        "tags": [{"slug": "basketball"}, {"slug": "nba"}],
    }


def test_parse_market_valid() -> None:
    client = GammaClient(http_get=MagicMock())
    raw = _event("0xabc")["markets"][0]
    raw["_event_live"] = True
    raw["_sport_tag"] = "basketball_nba"
    raw["_event_id"] = "evt_1"
    m = client._parse_market(raw)
    assert m is not None
    assert m.condition_id == "0xabc"
    assert m.yes_price == 0.60
    assert m.no_price == 0.40
    assert m.yes_token_id == "tokY"
    assert m.no_token_id == "tokN"
    assert m.event_live is True
    assert m.event_id == "evt_1"
    assert m.sport_tag == "basketball_nba"


def test_parse_market_missing_tokens_returns_none() -> None:
    client = GammaClient(http_get=MagicMock())
    raw = {"conditionId": "0xabc", "question": "Q", "slug": "s"}  # no tokens
    assert client._parse_market(raw) is None


def test_fetch_events_happy_path() -> None:
    http = MagicMock()
    # First call: /sports → no leagues (force fallback to parent tags)
    # Then: /events for parent tag 1 (sports)
    http.side_effect = [
        _resp(200, []),  # /sports empty → fallback
        _resp(200, [_event("0x1")]),  # parent_tag sports page 1
        _resp(200, []),  # parent_tag sports page 2 empty
        _resp(200, []),  # parent_tag esports page 1 empty
    ]
    client = GammaClient(http_get=http)
    markets = client.fetch_events()
    assert len(markets) == 1
    assert markets[0].condition_id == "0x1"


def test_fetch_events_http_error_returns_empty() -> None:
    http = MagicMock(side_effect=RuntimeError("boom"))
    client = GammaClient(http_get=http)
    assert client.fetch_events() == []


def test_sports_endpoint_caches(monkeypatch) -> None:
    http = MagicMock()
    http.side_effect = [
        _resp(200, [{"sport": "nba", "tags": "100,200"}]),  # /sports
        _resp(200, []),  # /events tag=100 empty
        _resp(200, []),  # /events tag=200 empty
        _resp(200, []),  # parent sports empty
        _resp(200, []),  # parent esports empty
    ]
    client = GammaClient(http_get=http)
    # İlk çağrı → 1 kez /sports çağrılır
    client.fetch_events()
    sports_calls = [c for c in http.call_args_list if "/sports" in str(c)]
    assert len(sports_calls) == 1
    # İkinci çağrı (zaman geçmeden) → cache kullanılmalı, /sports yeniden çağrılmamalı
    http.reset_mock()
    http.side_effect = [_resp(200, []), _resp(200, []), _resp(200, []), _resp(200, [])]
    client.fetch_events()
    sports_calls2 = [c for c in http.call_args_list if "/sports" in str(c)]
    assert len(sports_calls2) == 0
```

- [ ] **Step 2: FAIL**

- [ ] **Step 3: `src/infrastructure/apis/gamma_client.py` yaz**

```python
"""Polymarket Gamma API client — event/market discovery (TDD §8)."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

import requests

from src.models.market import MarketData

logger = logging.getLogger(__name__)

GAMMA_BASE = "https://gamma-api.polymarket.com"
EVENTS_PER_PAGE = 200
_SPORTS_CACHE_SEC = 21_600  # 6h
PARENT_TAGS: list[tuple[str, int]] = [
    ("sports", 1),
    ("esports", 64),
]
_DEFAULT_TIMEOUT = 20


def _default_http_get(url: str, params: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.get(url, params=params or {}, timeout=timeout)


class GammaClient:
    """Ham pazar verisini çeken infra istemcisi. Filtering orkestrasyonda."""

    def __init__(self, http_get: Callable[..., Any] = _default_http_get) -> None:
        self._http = http_get
        self._league_tags: list[tuple[str, int]] = []
        self._league_tags_ts: float = 0.0

    def fetch_events(self) -> list[MarketData]:
        try:
            tags = self._fetch_league_tags() or PARENT_TAGS
        except Exception as e:
            logger.warning("Gamma /sports failed: %s — using parent tags", e)
            tags = PARENT_TAGS

        seen: set[str] = set()
        out: list[MarketData] = []

        for category, tag_id in tags:
            try:
                self._fetch_by_tag(tag_id, category, seen, out)
            except Exception as e:
                logger.warning("Gamma fetch tag=%s failed: %s", tag_id, e)

        # Parent fallback (yeni tag'ler için)
        for category, tag_id in PARENT_TAGS:
            try:
                self._fetch_by_tag(tag_id, category, seen, out)
            except Exception as e:
                logger.warning("Gamma parent-tag fetch failed: %s", e)

        logger.info("Gamma fetched %d unique markets", len(out))
        return out

    def _fetch_by_tag(
        self,
        tag_id: int,
        category: str,
        seen: set[str],
        out: list[MarketData],
    ) -> None:
        offset = 0
        while True:
            params = {
                "tag_id": tag_id,
                "active": "true",
                "closed": "false",
                "limit": EVENTS_PER_PAGE,
                "offset": offset,
            }
            resp = self._http(f"{GAMMA_BASE}/events", params=params, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
            events = resp.json() or []
            if not events:
                return
            for event in events:
                self._ingest_event(event, category, seen, out)
            if len(events) < EVENTS_PER_PAGE:
                return
            offset += EVENTS_PER_PAGE

    def _ingest_event(self, event: dict, category: str, seen: set[str], out: list[MarketData]) -> None:
        event_id = str(event.get("id", "")) or None
        event_live = bool(event.get("live", False))
        event_ended = bool(event.get("ended", False))
        sport_tag = category
        # Daha spesifik tag (varsa)
        tags = event.get("tags") or []
        if isinstance(tags, list) and tags:
            first = tags[0]
            if isinstance(first, dict) and first.get("slug"):
                sport_tag = str(first["slug"])
        for raw in event.get("markets", []) or []:
            cid = raw.get("conditionId", "")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            raw["_event_id"] = event_id or ""
            raw["_event_live"] = event_live
            raw["_event_ended"] = event_ended
            raw["_sport_tag"] = sport_tag
            raw["_event_start_time"] = event.get("startTime", "") or ""
            parsed = self._parse_market(raw)
            if parsed is not None:
                out.append(parsed)

    def _parse_market(self, raw: dict) -> MarketData | None:
        try:
            tokens = raw.get("clobTokenIds")
            if isinstance(tokens, str):
                tokens = json.loads(tokens)
            prices = raw.get("outcomePrices")
            if isinstance(prices, str):
                prices = json.loads(prices)
            if not tokens or not prices or len(tokens) < 2 or len(prices) < 2:
                return None
            return MarketData(
                condition_id=str(raw.get("conditionId", "")),
                question=str(raw.get("question", "")),
                slug=str(raw.get("slug", "")),
                yes_token_id=str(tokens[0]),
                no_token_id=str(tokens[1]),
                yes_price=float(prices[0]),
                no_price=float(prices[1]),
                liquidity=float(raw.get("liquidity", 0) or 0),
                volume_24h=float(raw.get("volume24hr", 0) or 0),
                tags=[],
                end_date_iso=str(raw.get("endDate", "") or ""),
                match_start_iso=str(raw.get("_event_start_time", "") or ""),
                event_id=raw.get("_event_id") or None,
                event_live=bool(raw.get("_event_live", False)),
                event_ended=bool(raw.get("_event_ended", False)),
                sport_tag=str(raw.get("_sport_tag", "") or ""),
                sports_market_type=str(raw.get("sportsMarketType", "") or ""),
                closed=bool(raw.get("closed", False)),
                resolved=bool(raw.get("resolved", False)),
                accepting_orders=bool(raw.get("acceptingOrders", True)),
            )
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            logger.debug("parse_market failed for %s: %s", raw.get("conditionId", "?"), e)
            return None

    def _fetch_league_tags(self) -> list[tuple[str, int]]:
        if self._league_tags and (time.time() - self._league_tags_ts) < _SPORTS_CACHE_SEC:
            return self._league_tags
        resp = self._http(f"{GAMMA_BASE}/sports", timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
        sports = resp.json() or []
        seen: set[int] = set()
        result: list[tuple[str, int]] = []
        for entry in sports:
            sport_code = entry.get("sport", "")
            for t in str(entry.get("tags", "")).split(","):
                t = t.strip()
                if t.isdigit():
                    tid = int(t)
                    if tid not in seen:
                        seen.add(tid)
                        result.append((sport_code, tid))
        if result:
            self._league_tags = result
            self._league_tags_ts = time.time()
        return result
```

- [ ] **Step 4: PASS**

Run: `pytest tests/unit/infrastructure/apis/test_gamma_client.py -v`
Expected: PASS (5/5).

- [ ] **Step 5: ARCH check**

Run: `python -c "import pathlib; print(sum(1 for _ in open('src/infrastructure/apis/gamma_client.py', encoding='utf-8')))"`
Expected: < 400.

Run: `python -c "import src.infrastructure.apis.gamma_client as g; assert 'strategy' not in str(g.__dict__); assert 'orchestration' not in str(g.__dict__); print('layer OK')"`
Expected: `layer OK`.

- [ ] **Step 6: SPEC sil, commit**

```bash
git add src/infrastructure/apis/gamma_client.py tests/unit/infrastructure/apis/test_gamma_client.py SPEC.md
git commit -m "feat(infra): GammaClient — Polymarket event/market discovery"
```

---

## Task 12: `src/infrastructure/wallet.py` — Polygon Wallet

**Amaç:** Polygon üzerinden USDC + MATIC bakiyesi okuyan ince wallet sarmalayıcı.

**Eski Referans:** `../Polymarket Agent_Eski/src/wallet.py` (67 satır).
- **Migrate edilen:** `USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"`, `USDC_DECIMALS = 6`, `DEFAULT_RPC = "https://polygon-rpc.com"`, `balanceOf` ERC-20 selector (`0x70a08231`), adres padded 64 char, `eth_getBalance` MATIC formülü.
- **Sıfırdan yazılan:** `http_post` dep injection (test için), `eth_account` import isteğe bağlı değil (bağımlılık zorunlu — requirements.txt'te var). Adres derivasyonu başarısız olursa `ValueError` fırlat.

**Files:**
- Create: `src/infrastructure/wallet.py`
- Test: `tests/unit/infrastructure/test_wallet.py`

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/infrastructure/test_wallet.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.infrastructure.wallet import USDC_ADDRESS, USDC_DECIMALS, Wallet


def _resp(result_hex: str) -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock(return_value=None)
    r.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": result_hex}
    return r


TEST_KEY = "0x" + "11" * 32  # Any valid 32-byte hex key


def test_wallet_requires_private_key() -> None:
    with pytest.raises(ValueError):
        Wallet(private_key="")


def test_wallet_derives_address_from_key() -> None:
    w = Wallet(private_key=TEST_KEY)
    assert w.address.startswith("0x")
    assert len(w.address) == 42


def test_wallet_get_usdc_balance() -> None:
    # balanceOf returns raw integer (1 USDC = 10^6)
    http = MagicMock(return_value=_resp(hex(5_000_000)))  # 5 USDC
    w = Wallet(private_key=TEST_KEY, http_post=http)
    assert w.get_usdc_balance() == 5.0
    # Verify call goes to USDC_ADDRESS with correct selector
    call = http.call_args
    payload = call.kwargs.get("json") or call.args[1]
    assert payload["method"] == "eth_call"
    assert payload["params"][0]["to"] == USDC_ADDRESS
    assert payload["params"][0]["data"].startswith("0x70a08231")


def test_wallet_get_matic_balance() -> None:
    http = MagicMock(return_value=_resp(hex(10**18)))  # 1 MATIC
    w = Wallet(private_key=TEST_KEY, http_post=http)
    assert w.get_matic_balance() == 1.0


def test_wallet_http_error_returns_zero() -> None:
    http = MagicMock(side_effect=RuntimeError("timeout"))
    w = Wallet(private_key=TEST_KEY, http_post=http)
    assert w.get_usdc_balance() == 0.0
    assert w.get_matic_balance() == 0.0


def test_wallet_usdc_decimals_constant() -> None:
    assert USDC_DECIMALS == 6
```

- [ ] **Step 2: FAIL**

- [ ] **Step 3: `src/infrastructure/wallet.py` yaz**

```python
"""Polygon USDC/MATIC balance reader."""
from __future__ import annotations

import logging
from typing import Any, Callable

import requests
from eth_account import Account

logger = logging.getLogger(__name__)

USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_DECIMALS = 6
DEFAULT_RPC = "https://polygon-rpc.com"
_DEFAULT_TIMEOUT = 10


def _default_http_post(url: str, json: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.post(url, json=json, timeout=timeout)


class Wallet:
    def __init__(
        self,
        private_key: str,
        rpc_url: str = DEFAULT_RPC,
        http_post: Callable[..., Any] = _default_http_post,
    ) -> None:
        if not private_key:
            raise ValueError("private_key is required")
        self.private_key = private_key
        self.rpc_url = rpc_url
        self._http = http_post
        self.address = Account.from_key(private_key).address

    def get_usdc_balance(self) -> float:
        addr = self.address.lower().replace("0x", "").zfill(64)
        data = f"0x70a08231{addr}"
        payload = {
            "jsonrpc": "2.0", "method": "eth_call",
            "params": [{"to": USDC_ADDRESS, "data": data}, "latest"],
            "id": 1,
        }
        return self._read_balance(payload, decimals=USDC_DECIMALS)

    def get_matic_balance(self) -> float:
        payload = {
            "jsonrpc": "2.0", "method": "eth_getBalance",
            "params": [self.address, "latest"],
            "id": 1,
        }
        return self._read_balance(payload, decimals=18)

    def _read_balance(self, payload: dict, decimals: int) -> float:
        try:
            resp = self._http(self.rpc_url, json=payload, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
            raw = int(resp.json()["result"], 16)
            return raw / (10 ** decimals)
        except Exception as e:
            logger.error("Wallet RPC failed (method=%s): %s", payload.get("method"), e)
            return 0.0
```

- [ ] **Step 4: PASS**

Run: `pytest tests/unit/infrastructure/test_wallet.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/wallet.py tests/unit/infrastructure/test_wallet.py
git commit -m "feat(infra): Polygon Wallet — USDC/MATIC bakiye okuyucu"
```

---

## Task 13: `src/infrastructure/executor.py` — Executor (dry_run mock)

**Amaç:** `place_order` / `place_exit_order` / `exit_position` işlevlerini dry_run (sim), paper (sim), live (mock wired — Faz 3'te gerçek CLOB bağlanır) modlarında sunan executor.

**Eski Referans:** `../Polymarket Agent_Eski/src/executor.py` (263 satır).
- **Migrate edilen:** `LIQUID_DEPTH_USDC=500`, `LIMIT_OFFSET_CENTS=0.01`, `STALE_PRICE_MAX_DRIFT=0.05` sabitleri. `_best_price_from_book` (asks DESC / bids ASC) yorumu ve helper — Polymarket orderbook non-standard sort **kritik bilgi**, kesinlikle migrate edilecek. Dry_run simulated response yapısı (`sim_xxx` order_id).
- **Sıfırdan yazılan:** Live mode **Faz 3**'te doldurulacak (stub: `NotImplementedError` değil, `raise RuntimeError("live executor not wired in Phase 1")`). Order book fetch Faz 1'de sadece dry_run sanity check için yapılıyor — HTTP DI ile. Hybrid order routing Faz 3'e ertelenir (stub).

**SPEC entry:**

```markdown
### SPEC-009: Executor (dry_run mock + infra scaffold)
- **Dosya**: src/infrastructure/executor.py
#### Davranış Kuralları
1. dry_run/paper modlarda gerçekten emir göndermez; sim_xxx order_id döner
2. live modda bu Faz'da stub RuntimeError — CLOB client Faz 3'te wire edilir
3. `_best_price_from_book`: Polymarket asks DESC, bids ASC — [-1] indeksle best price
4. Stale-price guard: scanner fiyatı ile CLOB live fiyat farkı > 5% → reject "stale_price"
5. `exit_position(pos, reason)`: pozisyon slug ve token_id'yi loglar, dry_run modda sim_exit döndürür
6. CLOB fetch HTTP failure → warning log, empty book döner

#### Test Senaryoları
- test_executor_dry_run_place_order_returns_sim
- test_executor_paper_place_order_returns_sim
- test_executor_live_raises_runtime_error_in_phase1
- test_executor_stale_price_rejects
- test_executor_non_stale_adjusts_price
- test_executor_best_price_from_book_asks_desc
- test_executor_best_price_from_book_bids_asc
- test_executor_exit_position_dry_run
```

**Files:**
- Create: `src/infrastructure/executor.py`
- Test: `tests/unit/infrastructure/test_executor.py`

- [ ] **Step 0: SPEC-009 ekle**

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/infrastructure/test_executor.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.config.settings import Mode
from src.infrastructure.executor import (
    STALE_PRICE_MAX_DRIFT,
    Executor,
    _best_price_from_book,
)


def test_best_price_from_book_asks_desc_uses_last() -> None:
    # Polymarket asks DESC-sorted: last = lowest = best ask
    book = {"asks": [{"price": "0.99", "size": "10"}, {"price": "0.50", "size": "5"}, {"price": "0.48", "size": "20"}]}
    assert _best_price_from_book(book, "BUY") == 0.48


def test_best_price_from_book_bids_asc_uses_last() -> None:
    # Polymarket bids ASC-sorted: last = highest = best bid
    book = {"bids": [{"price": "0.01", "size": "10"}, {"price": "0.40", "size": "5"}, {"price": "0.46", "size": "20"}]}
    assert _best_price_from_book(book, "SELL") == 0.46


def test_best_price_empty_returns_none() -> None:
    assert _best_price_from_book({"asks": []}, "BUY") is None


def test_executor_dry_run_returns_sim_order() -> None:
    # CLOB fetch returns a book with best ask close to scanner price
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.40))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    out = ex.place_order(token_id="tok", side="BUY", price=0.40, size_usdc=40.0)
    assert out["status"] == "simulated"
    assert out["order_id"].startswith("sim_")
    assert out["mode"] == "dry_run"


def test_executor_paper_returns_sim_order() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.40))
    ex = Executor(mode=Mode.PAPER, http_get=http)
    out = ex.place_order(token_id="tok", side="BUY", price=0.40, size_usdc=40.0)
    assert out["status"] == "simulated"
    assert out["mode"] == "paper"


def test_executor_live_raises_in_phase1() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.40))
    ex = Executor(mode=Mode.LIVE, http_get=http)
    with pytest.raises(RuntimeError, match="live executor not wired"):
        ex.place_order(token_id="tok", side="BUY", price=0.40, size_usdc=40.0)


def test_executor_stale_price_rejects() -> None:
    # Scanner says 0.40, CLOB says 0.25 → drift 37.5% > 5% → reject
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.25))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    out = ex.place_order(token_id="tok", side="BUY", price=0.40, size_usdc=40.0)
    assert out["status"] == "error"
    assert out["reason"] == "stale_price"


def test_executor_small_drift_adjusts_price() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.415))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    out = ex.place_order(token_id="tok", side="BUY", price=0.40, size_usdc=40.0)
    assert out["status"] == "simulated"
    assert abs(out["price"] - 0.415) < 1e-6


def test_executor_exit_position_dry_run() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.40))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    pos = MagicMock(token_id="tok", shares=100, slug="a-vs-b")
    out = ex.exit_position(pos, reason="scale_out")
    assert out["status"] == "simulated"
    assert out["reason"] == "scale_out"


def _mock_ob_resp(best_ask: float) -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock(return_value=None)
    # DESC-sorted asks, last = best (lowest)
    r.json.return_value = {
        "asks": [{"price": "0.99", "size": "10"}, {"price": f"{best_ask}", "size": "100"}],
        "bids": [{"price": "0.01", "size": "10"}, {"price": f"{best_ask - 0.01:.3f}", "size": "100"}],
    }
    return r
```

- [ ] **Step 2: FAIL**

- [ ] **Step 3: Implementasyon yaz**

```python
# src/infrastructure/executor.py
"""Order executor — Phase 1: dry_run/paper sim + live stub."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

import requests

from src.config.settings import Mode

logger = logging.getLogger(__name__)

_CLOB_BOOK_URL = "https://clob.polymarket.com/book"
_DEFAULT_TIMEOUT = 10

LIQUID_DEPTH_USDC = 500.0
LIMIT_OFFSET_CENTS = 0.01
# Scanner'dan gelen fiyat ile CLOB live fiyat farkı > bu oran → reject
STALE_PRICE_MAX_DRIFT = 0.05


def _default_http_get(url: str, params: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.get(url, params=params or {}, timeout=timeout)


def _best_price_from_book(book: dict, side: str) -> float | None:
    """Polymarket non-standard sort:
      asks → DESC (last = lowest = best ask)
      bids → ASC (last = highest = best bid)
    """
    levels = book.get("asks" if side == "BUY" else "bids", [])
    if not levels:
        return None
    try:
        return float(levels[-1].get("price", 0)) or None
    except (TypeError, ValueError, KeyError):
        return None


class Executor:
    def __init__(
        self,
        mode: Mode,
        http_get: Callable[..., Any] = _default_http_get,
    ) -> None:
        self.mode = mode
        self._http = http_get

    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size_usdc: float,
    ) -> dict:
        # Stale-price guard (dry/paper/live hepsinde)
        clob_fill = self._fetch_best_price(token_id, side)
        if clob_fill is not None and clob_fill > 0 and price > 0:
            drift = abs(clob_fill - price) / price
            if drift > STALE_PRICE_MAX_DRIFT:
                logger.warning(
                    "STALE_PRICE_REJECT: %s side=%s scanner=%.3f clob=%.3f drift=%.1f%%",
                    token_id[:16], side, price, clob_fill, drift * 100,
                )
                return {
                    "order_id": f"rej_{uuid.uuid4().hex[:8]}",
                    "status": "error",
                    "reason": "stale_price",
                    "mode": self.mode.value,
                    "token_id": token_id,
                    "side": side,
                    "scanner_price": price,
                    "clob_price": clob_fill,
                    "drift": round(drift, 4),
                }
            if abs(clob_fill - price) > 0.001:
                logger.info("CLOB fill adjust: %s %.3f → %.3f", token_id[:16], price, clob_fill)
                price = clob_fill

        if self.mode in (Mode.DRY_RUN, Mode.PAPER):
            oid = f"sim_{uuid.uuid4().hex[:8]}"
            logger.info("[%s] sim %s %s @ $%.3f, size=$%.2f",
                        self.mode.value, side, token_id[:8], price, size_usdc)
            return {
                "order_id": oid,
                "status": "simulated",
                "mode": self.mode.value,
                "token_id": token_id,
                "side": side,
                "price": price,
                "size_usdc": size_usdc,
            }

        # Live — Phase 3'te wire edilecek
        raise RuntimeError("live executor not wired in Phase 1 — see Phase 3 (CLOB client)")

    def place_exit_order(self, token_id: str, shares: float) -> dict:
        if self.mode in (Mode.DRY_RUN, Mode.PAPER):
            return {
                "order_id": f"sim_exit_{uuid.uuid4().hex[:8]}",
                "status": "simulated",
                "mode": self.mode.value,
            }
        raise RuntimeError("live executor not wired in Phase 1")

    def exit_position(self, pos: Any, reason: str = "") -> dict:
        slug = getattr(pos, "slug", "") or getattr(pos, "token_id", "")
        logger.info("EXIT_POSITION: %s reason=%s mode=%s shares=%.2f",
                    slug[:40], reason, self.mode.value, getattr(pos, "shares", 0))
        if self.mode in (Mode.DRY_RUN, Mode.PAPER):
            return {
                "order_id": f"sim_exit_{uuid.uuid4().hex[:8]}",
                "status": "simulated",
                "mode": self.mode.value,
                "reason": reason,
            }
        raise RuntimeError("live executor not wired in Phase 1")

    def _fetch_best_price(self, token_id: str, side: str) -> float | None:
        try:
            resp = self._http(_CLOB_BOOK_URL, params={"token_id": token_id}, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
            return _best_price_from_book(resp.json(), side)
        except Exception as e:
            logger.warning("CLOB book fetch failed for %s: %s", token_id[:16], e)
            return None
```

- [ ] **Step 4: PASS**

Run: `pytest tests/unit/infrastructure/test_executor.py -v`
Expected: PASS (9/9).

- [ ] **Step 5: ARCH check — satır sayısı**

Run: `python -c "print(sum(1 for _ in open('src/infrastructure/executor.py', encoding='utf-8')))"`
Expected: < 400.

- [ ] **Step 6: SPEC sil, commit**

```bash
git add src/infrastructure/executor.py tests/unit/infrastructure/test_executor.py SPEC.md
git commit -m "feat(infra): Executor — dry_run/paper sim + stale-price guard + live stub"
```

---

## Task 14: `src/main.py` — Tek Giriş Noktası (max 50 satır, ARCH Kural 5)

**Amaç:** Bot'un tek başlangıç noktası. Argparse (mode override), config yükle, wallet init, Agent placeholder.

**ARCH Kural 5 hatırlatması:** main.py max 50 satır, iş mantığı yok. Agent henüz yok (Faz 5), placeholder olarak "not implemented" logla ve çık.

**Eski Referans:** `../Polymarket Agent_Eski/src/main.py` (97 satır).
- **Migrate edilen:** `load_dotenv()` çağrısı, `logging.basicConfig` + RotatingFileHandler pattern, `mode == LIVE` için "CONFIRM LIVE" prompt'u.
- **Sıfırdan yazılan:** `--reset` flag Faz 1'de YOK (scripts/reset_bot.py'ye taşınacak — TDD §2). `acquire_lock` Faz 5'te yapılacak. Faz 1'de `Agent` yok → placeholder.

**Files:**
- Create: `src/main.py`
- Test: `tests/unit/test_main.py` (light — sadece import sağlığı)

- [ ] **Step 1: Testleri yaz**

```python
# tests/unit/test_main.py
from __future__ import annotations


def test_main_module_imports_without_side_effects() -> None:
    import src.main  # Sadece import → RotatingFileHandler setup henüz tetiklenmemeli
    assert hasattr(src.main, "main")
    assert callable(src.main.main)


def test_main_max_50_lines() -> None:
    import pathlib
    lines = pathlib.Path("src/main.py").read_text(encoding="utf-8").splitlines()
    # Boş satır ve yorumlar dahil toplam satır sayısı (ARCH Kural 5)
    assert len(lines) <= 50, f"main.py is {len(lines)} lines — max 50 (ARCH Kural 5)"
```

- [ ] **Step 2: FAIL**

- [ ] **Step 3: `src/main.py` yaz (MAX 50 satır)**

```python
"""Bot tek giriş noktası (ARCH Kural 5 — max 50 satır, iş mantığı yok)."""
from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

from src.config.settings import Mode, load_config


def _setup_logging() -> None:
    Path("logs").mkdir(exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    file_h = RotatingFileHandler("logs/bot.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_h.setFormatter(logging.Formatter(fmt))
    con_h = logging.StreamHandler()
    con_h.setFormatter(logging.Formatter(fmt))
    logging.basicConfig(level=logging.INFO, handlers=[file_h, con_h])


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="polymarket-agent")
    parser.add_argument("--mode", choices=[m.value for m in Mode], default=None)
    args = parser.parse_args()
    _setup_logging()
    cfg = load_config()
    if args.mode:
        cfg = cfg.model_copy(update={"mode": Mode(args.mode)})
    if cfg.mode == Mode.LIVE:
        if input("Type 'CONFIRM LIVE' to proceed: ").strip() != "CONFIRM LIVE":
            print("Aborted.")
            sys.exit(1)
    logging.getLogger(__name__).info("Phase 1 bootstrap ok: mode=%s bankroll=$%.2f",
                                     cfg.mode.value, cfg.initial_bankroll)
    logging.getLogger(__name__).info("Agent not yet wired (Phase 5). Exiting.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: PASS**

Run: `pytest tests/unit/test_main.py -v`
Expected: PASS (2/2).

- [ ] **Step 5: Manuel smoke — bot başlatılıyor mu**

Run: `python -m src.main --mode dry_run`
Expected: çıktıda "Phase 1 bootstrap ok: mode=dry_run", ardından "Agent not yet wired (Phase 5)" ve exit.

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/unit/test_main.py
git commit -m "feat(main): tek giriş noktası + argparse + LIVE confirm (ARCH Kural 5)"
```

---

## Task 15: Meta — `.env.example`, `requirements.txt`, `pyproject.toml`, `pytest.ini`

**Amaç:** Geliştirme ortamının kurulabilir olmasını sağla. Bağımlılıklar, test runner, Python version pinning.

**Eski Referans:** `../Polymarket Agent_Eski/requirements.txt` (15 paket).
- **Migrate edilen:** `pydantic>=2.5.0`, `pyyaml>=6.0.1`, `python-dotenv>=1.0.0`, `requests>=2.31.0`, `eth-account>=0.11.0`, `pytest>=8.0.0`.
- **SİLİNEN (v2'de kullanılmıyor):** `feedparser` (news scanner yok v2'de), `trafilatura` (news scraping yok), `rapidfuzz` (matching Faz 2'de yeniden değerlendirilecek — TODO'ya yaz: eklenebilir).
- **v2'ye özgü:** Faz 1'de sadece `requests`, `eth-account`, `pydantic`, `pyyaml`, `python-dotenv`, `pytest`. `py-clob-client` Faz 3'te eklenir. `websockets` Faz 4'te. `flask` Faz 7'de. Şimdilik koymayalım — YAGNI.

**Files:**
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `pytest.ini`

- [ ] **Step 1: `requirements.txt` yaz (Faz 1 minimum set)**

```
# Phase 1 minimum — sonraki fazlarda genişler (py-clob-client → Faz 3, websockets → Faz 4, flask → Faz 7)
pydantic>=2.5.0
pyyaml>=6.0.1
python-dotenv>=1.0.0
requests>=2.31.0
eth-account>=0.11.0
pytest>=8.0.0
```

- [ ] **Step 2: `.env.example` yaz**

```
# Polymarket Agent 2.0 — environment variables template
# Copy to .env and fill in secrets (gitignored).

# Polygon wallet private key (0x-prefixed, 64-char hex)
PRIVATE_KEY=

# Odds API key (https://the-odds-api.com)
ODDS_API_KEY=

# Polygon RPC URL (opsiyonel, default: https://polygon-rpc.com)
POLYGON_RPC_URL=

# Telegram notifier (opsiyonel)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

- [ ] **Step 3: `pyproject.toml` yaz**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "polymarket-agent-2"
version = "2.0.0"
description = "Autonomous Polymarket trading bot — bookmaker-derived edge."
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.5.0",
    "pyyaml>=6.0.1",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
    "eth-account>=0.11.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
```

- [ ] **Step 4: `pytest.ini` yaz**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra --strict-markers
```

- [ ] **Step 5: Tüm test suite'i çalıştır — full green gate**

Run: `pytest -v`
Expected: Bu faz'da yazılan tüm testler PASS. Fail yok.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example pyproject.toml pytest.ini
git commit -m "chore: proje meta dosyaları — requirements, env.example, pyproject, pytest.ini"
```

---

## Final Kabul Kriterleri Doğrulaması (PLAN-001)

**Plan kabul kriterlerini adım adım doğrula. Her biri için komut + beklenen çıktı:**

- [ ] **Kriter 1: Dizin yapısı TDD §2 uyumlu**

Run: `python -c "import src.config.settings, src.config.sport_rules, src.models, src.infrastructure.apis.gamma_client, src.infrastructure.wallet, src.infrastructure.executor, src.infrastructure.persistence.json_store, src.infrastructure.persistence.trade_logger, src.infrastructure.persistence.price_history, src.main; print('dirs OK')"`
Expected: `dirs OK`.

- [ ] **Kriter 2: Model re-export çalışıyor**

Run: `python -c "from src.models import MarketData, Position, Signal; print('models OK')"`
Expected: `models OK`.

- [ ] **Kriter 3: config.yaml validation geçiyor**

Run: `python -c "from src.config.settings import load_config; cfg = load_config(); print(cfg.mode.value, cfg.initial_bankroll)"`
Expected: `dry_run 1000.0`.

- [ ] **Kriter 4: Enum testleri yeşil**

Run: `pytest tests/unit/models/test_enums.py -v`

- [ ] **Kriter 5: JSON store read/write unit test yeşil**

Run: `pytest tests/unit/infrastructure/persistence/ -v`

- [ ] **Kriter 6: Infrastructure domain/strategy import etmiyor (ARCH Kural 1)**

Run:
```bash
grep -r "from src.strategy\|from src.orchestration\|import src.strategy\|import src.orchestration" src/infrastructure/
```
Expected: Çıktı boş.

Run:
```bash
grep -r "from src.infrastructure\|import src.infrastructure" src/domain/ 2>/dev/null || echo "(domain dir empty — OK)"
```
Expected: Boş veya "(domain dir empty — OK)" (Faz 1'de domain boş).

- [ ] **Kriter 7: Tüm test suite yeşil**

Run: `pytest -v`
Expected: All PASS, 0 FAIL, 0 ERROR.

- [ ] **Kriter 8: main.py max 50 satır (ARCH Kural 5)**

Run: `python -c "print(sum(1 for _ in open('src/main.py', encoding='utf-8')))"`
Expected: ≤ 50.

- [ ] **Kriter 9: Hiçbir dosya 400 satırı aşmıyor (ARCH Kural 3)**

Run (bash):
```bash
find src -name "*.py" -exec wc -l {} \; | awk '$1 > 400 {print}' | tee /dev/stderr
```
Expected: Çıktı boş.

- [ ] **Kriter 10: PLAN.md'den PLAN-001'i DONE olarak işaretle ve sil (CLAUDE.md protokolü)**

PLAN.md'de PLAN-001 entry'sini kaldır (Faz 2+ planları kalır).

- [ ] **Kriter 11: Final commit — PLAN-001 tamamlandı**

```bash
git add PLAN.md
git commit -m "docs(plan): PLAN-001 Foundation tamamlandı, PLAN.md'den silindi"
```

---

## Self-Review Notları

- Her task'te SPEC entry (varsa) Step 0'da eklenir, son Step'te (commit öncesi) SPEC.md'den silinir — CLAUDE.md "Spec Yazdırırken" protokolü.
- TDD §10.1 unit test listesi **Faz 2 için**. Faz 1'de models/config/infrastructure testleri var; domain testleri (probability, confidence, edge, circuit breaker, vb.) Faz 2'de PLAN-002 ile gelecek.
- Event-level guard (ARCH Kural 8) Faz 1'de DEĞİL — `entry/gate.py` seviyesinde kontrol edilecek (Faz 3, PLAN-003).
- Domain katmanı Faz 1'de BOŞ (sadece `__init__.py`). ARCH Kural 2 (domain I/O yasak) kontrolü domain dosyaları yazılmaya başlandığında anlam kazanır (Faz 2).
- `rapidfuzz` eksikliği Faz 2 matching modülleri için TODO — PLAN-002 yazılırken hatırla.

---

## Soru — Onay Gerekli (CLAUDE.md "kritik kararlar")

Erim, plan kaydedilmeden önce şu iki karar noktasını onayla:

1. **Faz 1 requirements.txt'te `py-clob-client`, `websockets`, `flask` YOK** — sonraki fazlarda eklenecek. YAGNI: şimdi eklersek kullanılmayan bağımlılık olur. Onaylıyor musun?
2. **`rapidfuzz` Faz 1'e değil Faz 2'ye erteleniyor** — matching modülleri orada yazılacak. Alternatif: şimdi eklemek istersen TODO'ya not düşeyim. Hangisi?

Sen yeşil ışık verince subagent-driven-development ile task-by-task uygulamaya geçeriz.
