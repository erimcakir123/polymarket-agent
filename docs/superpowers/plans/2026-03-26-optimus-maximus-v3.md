# Optimus Maximus V3 — Pre-Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 22 değişiklik ile botu test-ready hale getir — sport-specific kurallar, odds API optimizasyonu, 11 kritik bug fix, config güncellemeleri.

**Architecture:** 4 bağımsız grup (A/B/C/D) paralel uygulanabilir. Grup B yeni `sport_rules.py` modülü oluşturur, diğerleri mevcut dosyaları düzenler. Spaghetti azaltma: logic'i main.py'den dışarı taşı.

**Tech Stack:** Python 3.11+, Pydantic config, no test framework (py_compile doğrulama)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `config.yaml` | Modify | Bond farming + max_positions config |
| `src/config.py` | Modify | BondFarmingConfig defaults |
| `src/sport_rules.py` | **Create** | 14 spor için SL/TP/re-entry/exit kuralları |
| `src/main.py` | Modify | Milestone kaldır, sport-aware entegrasyon, ULTI fix, correlation fix, odds API calls, VS trailing, drawdown levels |
| `src/portfolio.py` | Modify | Sport-aware SL, priority chain, graduated SL penny-only, edge-decay→match-aware |
| `src/match_exit.py` | Modify | NIP guard SL override fix, losing_badly sport-aware, edge-decay Layer 5 |
| `src/odds_api.py` | Modify | Fallback key, quota notification |
| `src/reentry_farming.py` | Modify | Sport-aware re-entry limits, stale AI 4h→1h for live |
| `src/live_dip_entry.py` | Modify | match_is_toxic global flag |
| `src/correlation.py` | Modify | Bond/penny dahil strateji-agnostik |

---

## GRUP A: Config Değişiklikleri

### Task 1: Bond Farming Config

**Files:**
- Modify: `config.yaml` (bond section ekle)
- Modify: `src/config.py:134-142` (BondFarmingConfig defaults)

- [ ] **Step 1: config.py defaults güncelle**

```python
# src/config.py — BondFarmingConfig class içinde:
# Satır 137: bet_pct: float = 0.15  →  0.08
# Satır 138: max_total_bond_pct: float = 0.35  →  0.20
# Satır 142: max_days_to_resolution: float = 14.0  →  0.25
```

- [ ] **Step 2: config.yaml'a bond section ekle**

```yaml
# config.yaml — bond bölümü ekle (yoksa):
bond:
  bet_pct: 0.08
  max_total_bond_pct: 0.20
  max_days_to_resolution: 0.25
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/config.py`
Expected: No output (success)

---

### Task 2: Max Positions 15 → 20

**Files:**
- Modify: `config.yaml:41`

- [ ] **Step 1: config.yaml güncelle**

```yaml
# Satır 41: max_positions: 15  →  20
max_positions: 20
```

- [ ] **Step 2: Doğrula**

Run: `python -c "from src.config import load_config; c = load_config(); print(f'max_positions={c.risk.max_positions}')"`
Expected: `max_positions=20`

---

### Task 3: Test Planı Milestone Kaldır

**Files:**
- Modify: `src/main.py:68-104` (_load_test_start_date, _MILESTONES)
- Modify: `src/main.py:329-360` (_maybe_send_milestone_reminder)
- Modify: `src/main.py:640` (milestone call in run_cycle)

- [ ] **Step 1: _maybe_send_milestone_reminder çağrısını devre dışı bırak**

main.py satır 640 civarında:
```python
# ESKİ:
self._maybe_send_milestone_reminder()
# YENİ:
# Milestone reminders disabled — 3-4 day test cycle instead
# self._maybe_send_milestone_reminder()
```

- [ ] **Step 2: Doğrula**

Run: `python -m py_compile src/main.py`

---

## GRUP B: Sport-Specific Rules

### Task 4: sport_rules.py Oluştur

**Files:**
- Create: `src/sport_rules.py`

- [ ] **Step 1: sport_rules.py yaz**

Bu dosya tüm spor kurallarını tek bir dict'te tutar. main.py'ye logic eklemek yerine, bu dosyadan okuma yapılır.

```python
"""
sport_rules.py — Sport-specific trading rules.

Tek kaynak: Her sporun SL, TP, re-entry, exit kuralları burada.
main.py, portfolio.py, match_exit.py, reentry_farming.py buradan okur.

Kullanım:
    from src.sport_rules import get_sport_rule, get_stop_loss, get_max_reentries
"""

from __future__ import annotations
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# MASTER RULES TABLE
# ═══════════════════════════════════════════════════════

SPORT_RULES: dict[str, dict] = {
    # ── NBA ──
    "nba": {
        "stop_loss_pct": 0.35,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 3,
        "reentry_max_elapsed_pct": 0.75,
        "halftime_exit": True,
        "halftime_exit_deficit": 15,  # points behind at halftime
        "hold_to_resolve_margin": 5,  # within X points = hold
        "pre_match_mandatory_exit_min": 8,
        "match_duration_hours": 2.5,
        "score_volatility_per_event": 0.004,
        "comeback_probability": "high",
        "losing_badly_deficit": 20,  # points behind = losing badly
        "losing_badly_quarters": ["Q3", "Q4"],
    },
    # ── NFL ──
    "nfl": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": True,
        "halftime_exit_deficit": 14,
        "hold_to_resolve_margin": 7,
        "pre_match_mandatory_exit_min": 15,
        "match_duration_hours": 3.25,
        "score_volatility_per_event": 0.006,
        "comeback_probability": "medium",
        "losing_badly_deficit": 17,
        "losing_badly_quarters": ["Q3", "Q4"],
    },
    # ── NHL ──
    "nhl": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.10,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": False,
        "period_exit": True,
        "period_exit_deficit": 3,  # goals behind after P2
        "hold_to_resolve_margin": 1,  # within 1 goal
        "pre_match_mandatory_exit_min": 10,
        "match_duration_hours": 2.5,
        "score_volatility_per_event": 0.10,
        "comeback_probability": "medium-low",
        "losing_badly_deficit": 3,
        "overtime_rule": "sudden_death",
    },
    # ── MLB ──
    "mlb": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 3,
        "reentry_max_elapsed_pct": 0.78,
        "halftime_exit": False,
        "inning_exit": True,
        "inning_exit_deficit": 5,  # runs behind after 6th
        "inning_exit_after": 6,
        "hold_to_resolve_margin": 2,  # within 2 runs after 6th
        "pre_match_mandatory_exit_min": 20,
        "match_duration_hours": 3.0,
        "score_volatility_per_event": 0.05,
        "comeback_probability": "medium",
        "losing_badly_deficit": 5,
    },
    # ── Soccer ──
    "soccer": {
        "stop_loss_pct": 0.25,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.10,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.75,
        "halftime_exit": True,
        "halftime_exit_deficit": 2,  # goals behind
        "hold_to_resolve_margin": 1,  # drawing or losing by 1 in H1
        "pre_match_mandatory_exit_min": 15,
        "match_duration_hours": 2.0,
        "score_volatility_per_event": 0.15,
        "comeback_probability": "low",
        "losing_badly_deficit": 2,
        "red_card_swing_pct": 0.08,
    },
    # ── Tennis ──
    "tennis": {
        "stop_loss_pct": 0.35,
        "trailing_tp_activation": 0.15,
        "trailing_tp_trail": 0.10,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": False,
        "set_exit": True,
        "set_exit_condition_bo3": "lost 1st set 6-1 or worse",
        "set_exit_condition_bo5": "lost 2 sets",
        "hold_to_resolve_margin": 1,  # within 1 set
        "pre_match_mandatory_exit_min": 0,  # not time-based
        "match_duration_hours_bo3": 1.75,
        "match_duration_hours_bo5": 3.5,
        "match_duration_hours": 2.5,  # default
        "score_volatility_per_set": 0.12,
        "score_volatility_per_break": 0.06,
        "comeback_probability": "high",
        "losing_badly_bo3": "lost 1st set + down break in 2nd",
        "losing_badly_bo5": "lost 2 sets + down break in 3rd",
        "retirement_risk": True,
    },
    # ── MMA/UFC ──
    "mma": {
        "stop_loss_pct": 0.35,
        "trailing_tp_activation": 0.25,
        "trailing_tp_trail": 0.12,
        "max_reentries": 1,
        "reentry_max_elapsed_pct": 0.60,
        "halftime_exit": False,
        "round_exit": True,
        "round_exit_condition_3r": "lost 2 rounds dominantly",
        "round_exit_condition_5r": "lost 3 rounds or near-finish",
        "hold_to_resolve_margin": 0,  # winning on cards
        "pre_match_mandatory_exit_min": 5,
        "match_duration_hours_3r": 0.5,
        "match_duration_hours_5r": 0.75,
        "match_duration_hours": 0.5,
        "score_volatility_per_event": 0.15,
        "comeback_probability": "medium-high",
        "finish_probability": 0.55,
    },
    # ── Boxing ──
    "boxing": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.65,
        "halftime_exit": False,
        "round_exit": True,
        "round_exit_condition": "lost 4+ rounds + knockdown",
        "hold_to_resolve_margin": 0,
        "pre_match_mandatory_exit_min": 10,
        "match_duration_hours": 1.0,
        "score_volatility_per_round": 0.03,
        "score_volatility_knockdown": 0.12,
        "comeback_probability": "low-medium",
    },
    # ── Cricket T20/IPL ──
    "cricket": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.10,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": True,
        "halftime_exit_deficit": 0,  # below par score
        "hold_to_resolve_margin": 0,
        "pre_match_mandatory_exit_min": 15,
        "match_duration_hours": 3.5,
        "score_volatility_per_wicket": 0.06,
        "comeback_probability": "medium",
        "losing_badly_deficit": 0,  # RRR > 12 after 15 overs
    },
    # ── Rugby NRL ──
    "rugby": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": True,
        "halftime_exit_deficit": 18,  # points behind
        "hold_to_resolve_margin": 7,
        "pre_match_mandatory_exit_min": 10,
        "match_duration_hours": 2.0,
        "score_volatility_per_try": 0.07,
        "comeback_probability": "medium-low",
        "losing_badly_deficit": 18,
    },
    # ── CS2 ──
    "cs2": {
        "stop_loss_pct": 0.40,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 3,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": True,
        "halftime_exit_deficit": 7,  # rounds behind (4-11)
        "hold_to_resolve_margin": 3,
        "pre_match_mandatory_exit_min": 0,
        "match_duration_hours": 2.0,
        "score_volatility_per_round": 0.015,
        "score_volatility_per_map": 0.12,
        "comeback_probability": "medium-high",
        "economy_factor": True,
    },
    # ── Valorant ──
    "valorant": {
        "stop_loss_pct": 0.40,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 3,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": False,
        "map_exit": True,
        "map_exit_deficit": 6,  # rounds behind in map 2
        "hold_to_resolve_margin": 0,
        "pre_match_mandatory_exit_min": 0,
        "match_duration_hours": 2.0,
        "score_volatility_per_round": 0.015,
        "score_volatility_per_map": 0.12,
        "comeback_probability": "medium-high",
    },
    # ── League of Legends ──
    "lol": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.15,
        "trailing_tp_trail": 0.08,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.55,
        "halftime_exit": False,
        "objective_exit": True,
        "hold_to_resolve_margin": 0,
        "pre_match_mandatory_exit_min": 0,
        "match_duration_hours": 1.5,
        "score_volatility_per_tower": 0.02,
        "score_volatility_per_dragon": 0.03,
        "score_volatility_per_baron": 0.08,
        "score_volatility_per_map": 0.15,
        "comeback_probability": "low",
        "snowball_ban_elapsed_pct": 0.30,
    },
    # ── Dota 2 ──
    "dota2": {
        "stop_loss_pct": 0.35,
        "trailing_tp_activation": 0.15,
        "trailing_tp_trail": 0.10,
        "max_reentries": 3,
        "reentry_max_elapsed_pct": 0.60,
        "halftime_exit": False,
        "objective_exit": True,
        "hold_to_resolve_margin": 0,
        "pre_match_mandatory_exit_min": 0,
        "match_duration_hours": 2.5,
        "score_volatility_per_tower": 0.015,
        "score_volatility_per_roshan": 0.04,
        "score_volatility_per_map": 0.15,
        "comeback_probability": "medium",
        "snowball_ban_elapsed_pct": 0.30,
        "buyback_factor": True,
    },
}

# ═══════════════════════════════════════════════════════
# DEFAULT — bilinmeyen sporlar için
# ═══════════════════════════════════════════════════════

DEFAULT_RULES: dict = {
    "stop_loss_pct": 0.30,
    "trailing_tp_activation": 0.20,
    "trailing_tp_trail": 0.08,
    "max_reentries": 2,
    "reentry_max_elapsed_pct": 0.65,
    "halftime_exit": False,
    "hold_to_resolve_margin": 0,
    "pre_match_mandatory_exit_min": 15,
    "match_duration_hours": 2.0,
    "score_volatility_per_event": 0.05,
    "comeback_probability": "medium",
    "losing_badly_deficit": 0,
}

# ═══════════════════════════════════════════════════════
# PUBLIC API — diğer modüller bunları çağırır
# ═══════════════════════════════════════════════════════

def get_sport_rule(sport_tag: str, key: str, default=None):
    """Tek bir kural değerini getir."""
    tag = _normalize_tag(sport_tag)
    rules = SPORT_RULES.get(tag, DEFAULT_RULES)
    return rules.get(key, DEFAULT_RULES.get(key, default))


def get_sport_rules(sport_tag: str) -> dict:
    """Bir sporun tüm kurallarını getir (default ile merge)."""
    tag = _normalize_tag(sport_tag)
    merged = dict(DEFAULT_RULES)
    merged.update(SPORT_RULES.get(tag, {}))
    return merged


def get_stop_loss(sport_tag: str, is_esports: bool = False) -> float:
    """Sport-aware stop-loss oranı."""
    return get_sport_rule(sport_tag, "stop_loss_pct", 0.30)


def get_max_reentries(sport_tag: str, number_of_games: int = 0) -> int:
    """Sport-aware max re-entry limiti."""
    return get_sport_rule(sport_tag, "max_reentries", 2)


def get_reentry_max_elapsed(sport_tag: str) -> float:
    """Sport-aware max elapsed % for re-entry."""
    return get_sport_rule(sport_tag, "reentry_max_elapsed_pct", 0.65)


def get_trailing_tp_params(sport_tag: str) -> tuple[float, float]:
    """Sport-aware trailing TP parameters (activation, trail_distance)."""
    activation = get_sport_rule(sport_tag, "trailing_tp_activation", 0.20)
    trail = get_sport_rule(sport_tag, "trailing_tp_trail", 0.08)
    return activation, trail


def get_match_duration(sport_tag: str) -> float:
    """Sport-aware match duration in hours."""
    return get_sport_rule(sport_tag, "match_duration_hours", 2.0)


def is_losing_badly(sport_tag: str, deficit: float, elapsed_pct: float = 0.0) -> bool:
    """Sport-aware 'losing badly' check.

    Args:
        sport_tag: Sport identifier
        deficit: Score deficit (positive = behind). Points for NBA/NFL,
                 goals for soccer/NHL, runs for MLB, etc.
        elapsed_pct: Match elapsed percentage (0.0-1.0)
    """
    tag = _normalize_tag(sport_tag)
    rules = SPORT_RULES.get(tag, DEFAULT_RULES)
    threshold = rules.get("losing_badly_deficit", 0)

    if threshold <= 0:
        return False  # No losing badly rule for this sport

    return deficit >= threshold


def _normalize_tag(sport_tag: str) -> str:
    """Normalize sport tag to match SPORT_RULES keys."""
    if not sport_tag:
        return ""
    tag = sport_tag.lower().strip()
    # Common aliases
    aliases = {
        "basketball": "nba", "americanfootball": "nfl",
        "icehockey": "nhl", "baseball": "mlb",
        "football": "soccer", "mls": "soccer",
        "ufc": "mma", "csgo": "cs2", "counter-strike": "cs2",
        "val": "valorant", "league_of_legends": "lol",
        "dota": "dota2", "cricket_t20": "cricket", "ipl": "cricket",
        "nrl": "rugby",
    }
    return aliases.get(tag, tag)
```

- [ ] **Step 2: Doğrula**

Run: `python -m py_compile src/sport_rules.py`

---

### Task 5: Portfolio.py — Sport-Aware Stop-Loss

**Files:**
- Modify: `src/portfolio.py:278-317` (check_stop_losses)

- [ ] **Step 1: Import ekle**

portfolio.py dosyasının başına:
```python
from src.sport_rules import get_stop_loss
```

- [ ] **Step 2: check_stop_losses içinde sport-aware SL**

Satır 309-312 civarında (esports ve default SL kısmı):
```python
# ESKİ:
elif pos.category == "esports":
    sl = esports_stop_loss_pct + (0.10 if pos.number_of_games >= 5 else 0.0)
else:
    sl = stop_loss_pct

# YENİ:
else:
    sport_tag = getattr(pos, 'sport_tag', '') or ''
    sl = get_stop_loss(sport_tag)
    # BO5+ esports bonus
    if pos.category == "esports" and pos.number_of_games >= 5:
        sl += 0.10
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/portfolio.py`

---

### Task 6: Reentry — Sport-Aware Limits

**Files:**
- Modify: `src/reentry_farming.py:50-52` (MAX_REENTRIES)
- Modify: `src/reentry_farming.py:300-302` (elapsed check)

- [ ] **Step 1: Import ekle**

reentry_farming.py başına:
```python
from src.sport_rules import get_max_reentries, get_reentry_max_elapsed
```

- [ ] **Step 2: MAX_REENTRIES dict'i sport_rules'dan oku**

Satır 345-346 civarında (max reentries check):
```python
# ESKİ:
max_re = MAX_REENTRIES.get(series_key, MAX_REENTRIES["default"])

# YENİ:
sport_tag = getattr(candidate, 'sport_tag', '') or ''
max_re = get_max_reentries(sport_tag, number_of_games)
```

- [ ] **Step 3: Elapsed check sport-aware**

Satır 300-302 civarında:
```python
# ESKİ:
if elapsed_pct >= 0.66:

# YENİ:
max_elapsed = get_reentry_max_elapsed(sport_tag)
if elapsed_pct >= max_elapsed:
```

- [ ] **Step 4: Doğrula**

Run: `python -m py_compile src/reentry_farming.py`

---

### Task 7: Match Exit — Sport-Aware Halftime/Period Exit

**Files:**
- Modify: `src/match_exit.py` (halftime exit logic)

- [ ] **Step 1: Import ekle**

```python
from src.sport_rules import get_sport_rule, is_losing_badly
```

- [ ] **Step 2: Halftime exit'i sport-aware yap**

Mevcut halftime exit logic'ini sport_rules'dan oku:
```python
# Halftime exit check — sport-specific deficit threshold
sport_tag = data.get("sport_tag", "")
ht_deficit = get_sport_rule(sport_tag, "halftime_exit_deficit", 15)
if halftime and deficit >= ht_deficit:
    return {"exit": True, "layer": "halftime", "reason": f"Down {deficit} at halftime (threshold: {ht_deficit})"}
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/match_exit.py`

---

### Task 8: Live Dip — Sport-Aware Losing Badly

**Files:**
- Modify: `src/live_dip_entry.py:212-231`

- [ ] **Step 1: Import ekle**

```python
from src.sport_rules import is_losing_badly
```

- [ ] **Step 2: Losing badly check'i sport-aware yap**

Satır 228 civarında:
```python
# ESKİ:
if fav_behind and deficit >= 7 and drop_pct >= 0.20:

# YENİ:
sport_tag = getattr(market, 'sport_tag', '') or pos_sport_tag or ''
if fav_behind and is_losing_badly(sport_tag, deficit) and drop_pct >= 0.20:
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/live_dip_entry.py`

---

## GRUP C: Odds API Optimizasyonu

### Task 9: Historical Odds + Line Movement Aktif Et

**Files:**
- Modify: `src/main.py:1138-1147` (odds context building)

- [ ] **Step 1: Line movement çağrısı ekle**

main.py satır 1144 civarından sonra:
```python
# Mevcut bookmaker odds çağrısından sonra:
if odds:
    parts.append(self.odds_api.build_odds_context(odds))
    sources.append("odds_api")
    odds_by_market[m.condition_id] = odds

    # Line movement — sharp money signal
    lm = self.odds_api.get_line_movement(m.question, m.slug, m.tags)
    if lm and lm.get("sharp_signal") != "stable":
        parts.append(self.odds_api.build_line_movement_context(lm))
        line_movement_by_market[m.condition_id] = lm
```

- [ ] **Step 2: line_movement_by_market dict'i initialize et**

Heavy cycle başında (odds_by_market yanına):
```python
line_movement_by_market: dict = {}
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/main.py`

---

### Task 10: AI Prompt'a Line Movement Bilgisi

**Files:**
- Modify: `src/odds_api.py:461-477` (build_line_movement_context)

- [ ] **Step 1: build_line_movement_context'i zenginleştir**

Mevcut fonksiyonu kontrol et, gerekirse sharp money signal gücünü ekle:
```python
def build_line_movement_context(self, lm: dict) -> str:
    signal = lm.get("sharp_signal", "stable")
    movement = lm.get("movement_a", 0)
    signal_label = {
        "steam_a": "SHARP MONEY → Team A (professionals moving this way)",
        "steam_b": "SHARP MONEY → Team B (professionals moving this way)",
        "stable": "No significant line movement",
    }.get(signal, "Unknown")

    return (
        f"\n📈 Line Movement (24h):\n"
        f"Movement: {movement:+.1%}\n"
        f"Signal: {signal_label}\n"
        f"Bookmakers: {lm.get('num_bookmakers', 0)}"
    )
```

- [ ] **Step 2: Doğrula**

Run: `python -m py_compile src/odds_api.py`

---

### Task 11: Fallback Key Mekanizması

**Files:**
- Modify: `src/odds_api.py:105-110` (constructor)

- [ ] **Step 1: Backup key + otomatik geçiş ekle**

Constructor'da:
```python
def __init__(self, api_key: str = ""):
    self.api_key = api_key or os.getenv("ODDS_API_KEY", "")
    self._backup_key = os.getenv("ODDS_API_KEY_BACKUP", "")
    self._using_backup = False
    # ... mevcut kod
```

- [ ] **Step 2: API çağrısında 401 yakalayınca backup'a geç**

_fetch metodunda (veya get request yapılan yerde):
```python
if response.status_code == 401 or response.status_code == 429:
    if not self._using_backup and self._backup_key:
        logger.warning("ODDS_API: Primary key exhausted, switching to backup")
        self.api_key = self._backup_key
        self._using_backup = True
        # Retry with backup key
        return self._fetch(endpoint, params)  # recursive retry (max 1)
    else:
        logger.error("ODDS_API: All keys exhausted")
        self._available = False
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/odds_api.py`

---

### Task 12: Telegram Quota Notification

**Files:**
- Modify: `src/odds_api.py:188-193` (quota tracking)

- [ ] **Step 1: Quota threshold uyarıları ekle**

Quota tracking kısmında (satır 189-193 civarı):
```python
remaining = int(response.headers.get("x-requests-remaining", -1))
if remaining >= 0:
    total = remaining + self._requests_used
    usage_pct = self._requests_used / max(total, 1)

    if usage_pct >= 0.95 and not self._notified_95:
        self._notify_quota("⚠️ Odds API %95 kullanıldı — backup key'e geçiş yakın")
        self._notified_95 = True
    elif usage_pct >= 0.80 and not self._notified_80:
        self._notify_quota("📊 Odds API %80 kullanıldı — cycle interval artırılabilir")
        self._notified_80 = True
```

- [ ] **Step 2: _notify_quota helper ekle**

```python
def _notify_quota(self, message: str):
    """Send quota warning via notifier (if available)."""
    logger.warning(message)
    if self._notifier:
        self._notifier.send(message)
```

- [ ] **Step 3: Constructor'a notifier + flags ekle**

```python
self._notifier = None  # Set externally via set_notifier()
self._notified_80 = False
self._notified_95 = False

def set_notifier(self, notifier):
    self._notifier = notifier
```

- [ ] **Step 4: main.py'de notifier'ı bağla**

main.py __init__ içinde:
```python
self.odds_api.set_notifier(self.notifier)
```

- [ ] **Step 5: Doğrula**

Run: `python -m py_compile src/odds_api.py && python -m py_compile src/main.py`

---

## GRUP D: 11 Kritik Bulgu Fix

### Task 13-14: Priority Chain + NIP Guard SL Override Fix

**Files:**
- Modify: `src/match_exit.py:320-330` (never-in-profit guard)
- Modify: `src/portfolio.py:278-317` (stop-loss check)

- [ ] **Step 1: NIP Guard'a SL kontrolü ekle**

match_exit.py satır 320 civarında:
```python
# KURAL: Stop-loss HER ZAMAN Never-in-Profit Guard'dan öncelikli.
# NIP Guard sadece TP'leri engelleyebilir, SL'yi ASLA override edemez.
# Bu yüzden NIP Guard "exit: True" döndürmeden önce SL kontrolü gerekmez —
# NIP Guard zaten "exit" diyor (SL ile aynı yönde).
# AMA NIP Guard "continue (don't exit)" dediğinde, SL tetiklenmişse
# SL kazanmalı. Bu kontrol portfolio.py check_stop_losses'ta yapılır.
```

Asıl fix portfolio.py'de: check_stop_losses'ta NIP guard kontrolü YOK, SL bağımsız çalışıyor. Bu DOĞRU davranış — SL kendi başına tetiklenir, NIP guard ayrı çalışır. Ama hold-to-resolve favori pozisyonlarda SL hala tetikleniyor mu kontrol et.

portfolio.py check_stop_losses satır 295 civarında favorite check var mı bak — YOKSA ekle:
```python
# Hold-to-resolve favorites: SL HALA GEÇERLİ (güvenlik mekanizması)
# Scale-Out: sadece spike koşulunda (>50% profit) çalışır
# Never-in-Profit Guard: SL'yi OVERRIDE EDEMEZ
```

- [ ] **Step 2: Doğrula**

Run: `python -m py_compile src/match_exit.py && python -m py_compile src/portfolio.py`

---

### Task 15: ULTI Rescue Max B- Sınırı

**Files:**
- Modify: `src/main.py:1440` (ULTI #1 confidence upgrade)
- Modify: `src/main.py:1582` (ULTI #2 confidence upgrade)

- [ ] **Step 1: ULTI #1 B+ → B- sınırla**

Satır 1440 civarında:
```python
# ESKİ:
estimate.confidence = "B+"
# YENİ:
estimate.confidence = "B-"  # ULTI rescue = kurtarma, promotion değil
```

- [ ] **Step 2: ULTI #2 aynı fix**

Satır 1582 civarında:
```python
# ESKİ:
estimate.confidence = "B+"
# YENİ:
estimate.confidence = "B-"
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/main.py`

---

### Task 16: Global match_is_toxic Flag

**Files:**
- Modify: `src/live_dip_entry.py:212-231` (losing badly → toxic flag)
- Modify: `src/main.py` (toxic flag'i momentum'a da uygula)

- [ ] **Step 1: live_dip_entry'den toxic market set döndür**

find_live_dip_candidates'ın return dict'ine toxic_markets ekle:
```python
# Fonksiyon sonunda toxic set'i de döndür:
return {
    "candidates": candidates,
    "toxic_markets": toxic_condition_ids,  # losing badly olan market'ler
}
```

- [ ] **Step 2: main.py'de toxic_markets'ı momentum'a da uygula**

_check_momentum_signals'da:
```python
if cid in self._toxic_markets:
    continue  # match_is_toxic — momentum entry de yasak
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/live_dip_entry.py && python -m py_compile src/main.py`

---

### Task 17: Farming Re-entry Stale AI — 4h → 1h for Live

**Files:**
- Modify: `src/reentry_farming.py:350-351` (stale check)

- [ ] **Step 1: Live maç için kısa yaş limiti**

Satır 350-351 civarında:
```python
# ESKİ:
if cycles_since_exit > MAX_ANALYSIS_AGE_CYCLES:

# YENİ:
is_live = getattr(candidate, 'match_live', False) or elapsed_pct > 0.05
max_age = 60 if is_live else MAX_ANALYSIS_AGE_CYCLES  # 1h live, 4h pre-match
if cycles_since_exit > max_age:
```

- [ ] **Step 2: Doğrula**

Run: `python -m py_compile src/reentry_farming.py`

---

### Task 18: Correlation Cap — Strateji-Agnostik

**Files:**
- Modify: `src/main.py` (_check_bond_candidates, _check_penny_candidates)

- [ ] **Step 1: Bond entry'ye correlation check ekle**

_check_bond_candidates içinde (add_position'dan önce):
```python
# Correlation cap — bond da dahil
sport_exposure = self.portfolio.correlated_exposure("", sport_tag=market.sport_tag or "")
if sport_exposure >= self.config.risk.correlation_cap_pct:
    logger.info("Bond skip: correlation cap reached for %s", market.sport_tag)
    continue
```

- [ ] **Step 2: Penny entry'ye correlation check ekle**

_check_penny_candidates içinde aynı check:
```python
sport_exposure = self.portfolio.correlated_exposure("", sport_tag=market.sport_tag or "")
if sport_exposure >= self.config.risk.correlation_cap_pct:
    continue
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/main.py`

---

### Task 19: Graduated SL <9¢ — Sadece Penny Alpha

**Files:**
- Modify: `src/portfolio.py:298-301` (ultra-low SL skip)

- [ ] **Step 1: <9¢ istisnasını penny-only yap**

Satır 298-301 civarında:
```python
# ESKİ:
elif eff_entry_sl < 0.09:
    continue  # Ultra-low entry — no stop-loss

# YENİ:
elif eff_entry_sl < 0.09:
    # Ultra-low: only Penny Alpha skips SL (bet size IS the risk)
    # FAR swing trades and other strategies still get their SL
    if getattr(pos, 'entry_reason', '') in ('penny', 'far') and pos.entry_price <= 0.02:
        continue  # Penny alpha — no stop-loss
    else:
        sl = 0.50  # Other ultra-low entries: wide 50% SL
```

- [ ] **Step 2: Doğrula**

Run: `python -m py_compile src/portfolio.py`

---

### Task 20: Drawdown HALT — Soft/Hard İki Seviye

**Files:**
- Modify: `src/portfolio.py:665-674` (is_drawdown_breaker_active)
- Modify: `src/main.py:660-665` (halt logic)

- [ ] **Step 1: Portfolio'ya iki seviyeli drawdown check ekle**

portfolio.py:
```python
def get_drawdown_level(self, soft_pct: float = 0.50, hard_pct: float = 0.65) -> str:
    """Returns: 'none' | 'soft' | 'hard'"""
    if self.high_water_mark <= 0:
        return "none"
    equity = self.total_value
    drawdown = 1 - (equity / self.high_water_mark)
    if drawdown >= hard_pct:
        return "hard"  # Equity < 35% of HWM → close everything
    elif drawdown >= soft_pct:
        return "soft"  # Equity < 50% of HWM → no new entries
    return "none"
```

- [ ] **Step 2: main.py'de soft/hard ayrımını uygula**

Satır 660-665 civarında:
```python
# ESKİ:
if self.portfolio.is_drawdown_breaker_active():
    self.running = False

# YENİ:
dd_level = self.portfolio.get_drawdown_level()
if dd_level == "hard":
    logger.critical("HARD HALT: equity < 35%% HWM — closing all positions")
    self._close_all_positions()
    self.running = False
elif dd_level == "soft":
    logger.warning("SOFT HALT: equity < 50%% HWM — no new entries")
    skip_new_entries = True  # Flag to skip entry logic below
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/portfolio.py && python -m py_compile src/main.py`

---

### Task 21: VS Trailing Sıkılaştırma

**Files:**
- Modify: `src/main.py` (trailing TP check in light cycle, satır 551-571)

- [ ] **Step 1: Resolution'a yakın trail distance azalt**

Trailing TP hesabında (satır 556 civarında):
```python
# VS pozisyonlar: resolution'a 30dk kala trail sıkılaştır
trail_distance = self.config.trailing_tp.trail_distance  # default 0.08
if pos.volatility_swing:
    hours_left = self._hours_to_end(market_data) if market_data else 99
    if hours_left <= 0.5:  # 30 dakika kala
        trail_distance = 0.04  # %8 → %4 sıkılaştır
```

- [ ] **Step 2: Doğrula**

Run: `python -m py_compile src/main.py`

---

### Task 22: Edge-Decay → Match-Aware Layer 5

**Files:**
- Modify: `src/match_exit.py` (Layer 5 ekle)
- Modify: `src/portfolio.py:443-480` (edge-decay TP kısmını match_exit'e taşı)

- [ ] **Step 1: match_exit.py'ye Layer 5 ekle**

check_match_exit fonksiyonuna:
```python
# Layer 5: Edge Decay (underdog positions)
# Maç ilerledikçe AI target'ı market'e yaklaştır
effective_ai = data.get("ai_probability", 0.5)
if data.get("direction", "").endswith("NO"):
    effective_ai = 1 - effective_ai

if effective_ai < 0.50:  # Underdog position
    from src.edge_decay import get_decayed_ai_target
    decayed = get_decayed_ai_target(effective_ai, effective_current, elapsed_pct)
    edge_tp = decayed * 0.85
    if effective_current >= edge_tp and effective_current > effective_entry * 1.10:
        return {
            "exit": True,
            "layer": "edge_decay",
            "reason": f"Edge decay TP: eff={effective_current:.3f} >= decayed_target={edge_tp:.3f}"
        }
```

- [ ] **Step 2: portfolio.py'den edge-decay kodunu kaldır**

portfolio.py satır 443-480 civarındaki edge-decay TP bloğunu comment out et (match_exit'e taşındı):
```python
# Edge-decay TP moved to match_exit.py Layer 5
# Old code removed to avoid double-triggering
```

- [ ] **Step 3: Doğrula**

Run: `python -m py_compile src/match_exit.py && python -m py_compile src/portfolio.py`

---

## Execution Checklist

After all tasks complete:

- [ ] Full compile check: `python -m py_compile src/*.py`
- [ ] Import chain test: `python -c "from src.main import BotAgent; print('OK')"`
- [ ] Config load test: `python -c "from src.config import load_config; c = load_config(); print(f'bonds={c.bond.max_days_to_resolution}, positions={c.risk.max_positions}')"`
- [ ] Sport rules test: `python -c "from src.sport_rules import get_stop_loss; print(f'nba={get_stop_loss(\"nba\")}, tennis={get_stop_loss(\"tennis\")}, default={get_stop_loss(\"unknown\")}')"`
