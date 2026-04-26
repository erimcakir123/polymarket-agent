# NBA Spread + Totals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NBA trading'i spread ve totals market tiplerini destekleyecek şekilde genişlet — market line parsing, Bill James math extensions (is_spread_dead, is_total_dead), dedicated exit modules, monitor.py market_type routing.

**Architecture:** Mevcut 5-katman mimarisi. Domain layer'a pure math ekle. strategy/exit/ altına nba_score_exit.py pattern'i takip eden yeni modüller. Monitor `pos.sports_market_type`'a göre route eder. Gate parsed market_line verisini Signal → Position'a propagate eder. Tüm check result tipleri aynı interface'i paylaşır (reason, sell_pct, partial).

**Tech Stack:** Python 3.12+, Pydantic v2, `re` stdlib, mevcut `ExitReason` enum, `math.sqrt`, `Literal` typing.

**Önkoşul:** NBA moneyline tamamlandı (commit `foundation-v1`, 863 test geçiyor).

---

## Gerçek Polymarket Market Format Bulguları

**Spread** (`sportsMarketType='spreads'`):
- `"Spread: Lakers (-5.5)"` — spread_line = 5.5
- `"Spread: Club ABB (-1.5)"` — spread_line = 1.5
- `groupItemTitle: "Lakers (-5.5)"`

**Totals** (`sportsMarketType='totals'`):
- `"Lakers vs Rockets: O/U 220.5"` — total_line = 220.5
- `"Games Total: O/U 2.5"` — total_line = 2.5
- `groupItemTitle: "O/U 220.5"`
- Konvansiyon: YES token = OVER, NO token = UNDER

**Bilinmeyen format → parser None döner → exit devre dışı** (güvenli default).

---

## Dosya Haritası

| İşlem | Dosya | Neden |
|---|---|---|
| CREATE | `src/domain/matching/market_line_parser.py` | Spread/total line parse, domain-pure |
| CREATE | `src/strategy/exit/nba_spread_exit.py` | Spread-specific exit logic |
| CREATE | `src/strategy/exit/nba_totals_exit.py` | Totals-specific exit logic |
| CREATE | `tests/unit/domain/matching/test_market_line_parser.py` | Parser unit tests |
| CREATE | `tests/unit/strategy/exit/test_nba_spread_exit.py` | Spread exit unit tests |
| CREATE | `tests/unit/strategy/exit/test_nba_totals_exit.py` | Totals exit unit tests |
| MODIFY | `src/domain/math/safe_lead.py` | +is_spread_dead, +is_total_dead |
| MODIFY | `src/models/signal.py` | +sports_market_type, spread_line, total_line, total_side |
| MODIFY | `src/models/position.py` | +sports_market_type, spread_line, total_line, total_side |
| MODIFY | `src/config/settings.py` | EntryConfig flat +4 spread +3 totals fields; BasketballExitConfig +totals_multiplier, +spread/totals empirical |
| MODIFY | `config.yaml` | entry + exit_basketball yeni değerler |
| MODIFY | `src/strategy/entry/gate.py` | market_type filter + market_line propagation |
| MODIFY | `src/strategy/exit/monitor.py` | NBA routing by sports_market_type; basketball_exit_cfg param |
| MODIFY | `src/orchestration/entry_processor.py` | +sports_market_type, spread_line, total_line, total_side Position'a |
| MODIFY | `src/orchestration/factory.py` | GateConfig'e yeni spread/totals alanları; monitor çağrısı güncelle |
| MODIFY | `src/orchestration/scanner.py` | NBA için spreads/totals SMT'ye izin ver |
| MODIFY | `tests/unit/domain/math/test_safe_lead.py` | is_spread_dead + is_total_dead testleri |
| MODIFY | `tests/unit/strategy/entry/test_gate.py` | Spread/totals filter testleri |
| MODIFY | `DECISIONS.md` | NBA Spread + Totals bölümleri |

---

## Task 1: Position + Signal Model Extensions

**Files:**
- Modify: `src/models/signal.py`
- Modify: `src/models/position.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test yaz**

`tests/unit/domain/models/test_market_line_fields.py` (yeni dosya oluştur):

```python
"""sports_market_type, spread_line, total_line, total_side field testleri."""
from __future__ import annotations

from src.models.signal import Signal
from src.models.position import Position
from src.models.enums import Direction, EntryReason


def _make_signal(**kw) -> Signal:
    base = dict(
        condition_id="cid",
        direction=Direction.BUY_YES,
        anchor_probability=0.65,
        market_price=0.50,
        confidence="A",
        size_usdc=50.0,
        entry_reason=EntryReason.NORMAL,
        bookmaker_prob=0.65,
    )
    base.update(kw)
    return Signal(**base)


def _make_position(**kw) -> Position:
    base = dict(
        condition_id="cid",
        token_id="tok",
        direction="BUY_YES",
        entry_price=0.50,
        size_usdc=50.0,
        shares=100.0,
        current_price=0.50,
        anchor_probability=0.65,
    )
    base.update(kw)
    return Position(**base)


# ── Signal ───────────────────────────────────────────────────────
def test_signal_sports_market_type_default():
    assert _make_signal().sports_market_type == ""


def test_signal_spread_line_default():
    assert _make_signal().spread_line is None


def test_signal_total_line_default():
    assert _make_signal().total_line is None


def test_signal_total_side_default():
    assert _make_signal().total_side is None


def test_signal_spread_fields_set():
    sig = _make_signal(sports_market_type="spreads", spread_line=5.5)
    assert sig.sports_market_type == "spreads"
    assert sig.spread_line == 5.5


def test_signal_totals_fields_set():
    sig = _make_signal(sports_market_type="totals", total_line=220.5, total_side="over")
    assert sig.total_line == 220.5
    assert sig.total_side == "over"


# ── Position ─────────────────────────────────────────────────────
def test_position_sports_market_type_default():
    assert _make_position().sports_market_type == ""


def test_position_spread_line_default():
    assert _make_position().spread_line is None


def test_position_total_line_default():
    assert _make_position().total_line is None


def test_position_total_side_default():
    assert _make_position().total_side is None


def test_position_spread_fields_set():
    pos = _make_position(sports_market_type="spreads", spread_line=7.5)
    assert pos.sports_market_type == "spreads"
    assert pos.spread_line == 7.5


def test_position_totals_fields_set():
    pos = _make_position(sports_market_type="totals", total_line=215.0, total_side="under")
    assert pos.total_line == 215.0
    assert pos.total_side == "under"
```

- [ ] **Step 2: Testi çalıştır, fail ettiğini doğrula**

```
pytest tests/unit/domain/models/test_market_line_fields.py -v
```
Beklenen: `ImportError` veya `AttributeError`.

- [ ] **Step 3: Signal'e yeni alanları ekle**

`src/models/signal.py` — mevcut alanların ALTINA ekle (sona):

```python
from typing import Literal  # dosyanın üstüne ekle (mevcut importların yanına)

class Signal(BaseModel):
    # ... mevcut alanlar değişmez ...
    sport_tag: str = ""
    event_id: str = ""
    # YENİ — moneyline'da None kalır
    sports_market_type: str = ""
    spread_line: float | None = None
    total_line: float | None = None
    total_side: Literal["over", "under"] | None = None
```

- [ ] **Step 4: Position'a yeni alanları ekle**

`src/models/position.py` — "Bookmaker metadata" bölümünün altına ekle:

```python
from typing import Literal  # dosyanın üstüne ekle

# Position class içinde, bookmaker_prob'dan sonra:
    # Market tipi — moneyline'da "" kalır; spread/totals'ta dolu
    sports_market_type: str = ""
    spread_line: float | None = None
    total_line: float | None = None
    total_side: Literal["over", "under"] | None = None
```

- [ ] **Step 5: Testi çalıştır, pass ettiğini doğrula**

```
pytest tests/unit/domain/models/test_market_line_fields.py -v
```
Beklenen: 12 PASSED.

- [ ] **Step 6: Mevcut testlerin kırılmadığını doğrula**

```
pytest tests/ -q --tb=short 2>&1 | tail -5
```
Beklenen: 863 passed (yeni 12 eklenerek 875).

- [ ] **Step 7: Commit**

```bash
git add src/models/signal.py src/models/position.py tests/unit/domain/models/test_market_line_fields.py
git commit -m "feat(models): add sports_market_type, spread_line, total_line, total_side to Signal + Position"
```

---

## Task 2: Market Line Parser

**Files:**
- Create: `src/domain/matching/market_line_parser.py`
- Create: `tests/unit/domain/matching/test_market_line_parser.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

Polymarket format (gerçek data'dan doğrulandı):
- Spread: `"Spread: Lakers (-5.5)"` → `5.5`
- Totals: `"Lakers vs Rockets: O/U 220.5"` → `(220.5, "over")`

- [ ] **Step 1: Failing test yaz**

```python
# tests/unit/domain/matching/test_market_line_parser.py
"""Market line parser — gerçek Polymarket format'larına karşı test."""
from __future__ import annotations

import pytest
from src.domain.matching.market_line_parser import parse_spread_line, parse_total_line


# ── parse_spread_line ─────────────────────────────────────────────
def test_spread_standard_format():
    """'Spread: Lakers (-5.5)' → 5.5"""
    assert parse_spread_line("Spread: Lakers (-5.5)") == 5.5


def test_spread_integer_line():
    """'Spread: Celtics (-6)' → 6.0"""
    assert parse_spread_line("Spread: Celtics (-6)") == 6.0


def test_spread_large_line():
    """'Spread: Warriors (-13.5)' → 13.5"""
    assert parse_spread_line("Spread: Warriors (-13.5)") == 13.5


def test_spread_underdog_plus():
    """'Spread: Rockets (+5.5)' → 5.5 (absolute value)"""
    assert parse_spread_line("Spread: Rockets (+5.5)") == 5.5


def test_spread_group_item_title():
    """groupItemTitle format: 'Lakers (-5.5)' → 5.5"""
    assert parse_spread_line("Lakers (-5.5)") == 5.5


def test_spread_no_match_returns_none():
    """Tanımlanamayan format → None"""
    assert parse_spread_line("Lakers vs Rockets moneyline") is None


def test_spread_empty_returns_none():
    assert parse_spread_line("") is None


# ── parse_total_line ──────────────────────────────────────────────
def test_total_standard_format():
    """'Lakers vs Rockets: O/U 220.5' → (220.5, 'over')"""
    result = parse_total_line("Lakers vs Rockets: O/U 220.5")
    assert result == (220.5, "over")


def test_total_games_total_format():
    """Esports: 'Games Total: O/U 2.5' → (2.5, 'over')"""
    result = parse_total_line("Games Total: O/U 2.5")
    assert result == (2.5, "over")


def test_total_group_item_title():
    """groupItemTitle: 'O/U 215.5' → (215.5, 'over')"""
    result = parse_total_line("O/U 215.5")
    assert result == (215.5, "over")


def test_total_case_insensitive():
    """'o/u 220.5' (küçük harf) → (220.5, 'over')"""
    result = parse_total_line("o/u 220.5")
    assert result == (220.5, "over")


def test_total_integer_line():
    """'O/U 220' → (220.0, 'over')"""
    result = parse_total_line("O/U 220")
    assert result == (220.0, "over")


def test_total_no_match_returns_none():
    """Tanımlanamayan format → None"""
    assert parse_total_line("Lakers vs Rockets moneyline") is None


def test_total_empty_returns_none():
    assert parse_total_line("") is None
```

- [ ] **Step 2: Testi çalıştır, fail ettiğini doğrula**

```
pytest tests/unit/domain/matching/test_market_line_parser.py -v
```
Beklenen: `ModuleNotFoundError`.

- [ ] **Step 3: Parser'ı implement et**

```python
# src/domain/matching/market_line_parser.py
"""Polymarket market title'ından spread/total line parse eder.

Desteklenen formatlar (gerçek Gamma API data'sına dayanarak):
  Spread : "Spread: TEAM_NAME (-X.5)"  veya  "TEAM_NAME (-X.5)"
  Totals : "TEAM1 vs TEAM2: O/U X.5"  veya  "Games Total: O/U X.5"

Tanımlanamayan format → None döner → ilgili exit logic devre dışı.
Polymarket konvansiyonu: totals YES token = OVER.
"""
from __future__ import annotations

import re
from typing import Literal

# Spread: parantez içi ±X.5 (1-30 puan arası NBA spreads için yeterli)
_SPREAD_RE = re.compile(r'\([+-]?(\d{1,2}(?:\.\d)?)\)')

# Totals: "O/U X.5" veya "o/u X"
_TOTAL_RE = re.compile(r'[Oo]/[Uu]\s+(\d+(?:\.\d+)?)')


def parse_spread_line(question: str) -> float | None:
    """Spread line'ı parçalar.

    "Spread: Lakers (-5.5)" → 5.5
    "Lakers (-5.5)"         → 5.5
    Eşleşme yoksa → None (exit devre dışı).
    """
    m = _SPREAD_RE.search(question)
    if m:
        return float(m.group(1))
    return None


def parse_total_line(question: str) -> tuple[float, Literal["over", "under"]] | None:
    """Total line ve side'ı parçalar.

    "Lakers vs Rockets: O/U 220.5" → (220.5, "over")
    "Games Total: O/U 2.5"         → (2.5, "over")
    Polymarket konvansiyonu: YES token = OVER.
    Eşleşme yoksa → None (exit devre dışı).
    """
    m = _TOTAL_RE.search(question)
    if m:
        return float(m.group(1)), "over"
    return None
```

- [ ] **Step 4: Testi çalıştır, pass ettiğini doğrula**

```
pytest tests/unit/domain/matching/test_market_line_parser.py -v
```
Beklenen: 13 PASSED.

- [ ] **Step 5: Tüm testler hâlâ geçiyor mu**

```
pytest tests/ -q --tb=short 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
git add src/domain/matching/market_line_parser.py tests/unit/domain/matching/test_market_line_parser.py
git commit -m "feat(domain): market_line_parser — spread/total line parse from Polymarket question format"
```

---

## Task 3: safe_lead.py Extensions

**Files:**
- Modify: `src/domain/math/safe_lead.py`
- Modify: `tests/unit/domain/math/test_safe_lead.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing testleri yaz** (mevcut `test_safe_lead.py` dosyasına EKLE):

```python
# test_safe_lead.py dosyasının SONUNA ekle — mevcut import'ları değiştirme
from src.domain.math.safe_lead import is_spread_dead, is_total_dead

_SM = 0.861   # spread multiplier (moneyline ile aynı)
_TM = 1.218   # total multiplier (0.861 × sqrt(2))

# ── is_spread_dead ────────────────────────────────────────────────
def test_spread_dead_8pts_60s():
    # 0.861 * sqrt(60) = 6.67 → 8 >= 6.67 → True
    assert is_spread_dead(margin_to_cover=8.0, seconds_remaining=60, multiplier=_SM) is True


def test_spread_alive_8pts_240s():
    # 0.861 * sqrt(240) = 13.33 → 8 < 13.33 → False
    assert is_spread_dead(margin_to_cover=8.0, seconds_remaining=240, multiplier=_SM) is False


def test_spread_dead_5pts_30s():
    # 0.861 * sqrt(30) = 4.71 → 5 >= 4.71 → True
    assert is_spread_dead(margin_to_cover=5.0, seconds_remaining=30, multiplier=_SM) is True


def test_spread_zero_margin_alive():
    # Margin ≤ 0 → zaten cover'dayız → False
    assert is_spread_dead(margin_to_cover=0.0, seconds_remaining=60, multiplier=_SM) is False


def test_spread_negative_margin_alive():
    assert is_spread_dead(margin_to_cover=-3.0, seconds_remaining=120, multiplier=_SM) is False


def test_spread_zero_seconds_positive_margin():
    # Oyun bitti, gerideyiz → True
    assert is_spread_dead(margin_to_cover=1.0, seconds_remaining=0, multiplier=_SM) is True


def test_spread_zero_seconds_zero_margin():
    # Exactly at the spread — NOT covering (need STRICTLY more) → True
    assert is_spread_dead(margin_to_cover=0.1, seconds_remaining=0, multiplier=_SM) is True


# ── is_total_dead ─────────────────────────────────────────────────
def test_total_dead_over_not_enough_pace():
    # target=220, current=200, 240s, "over"
    # points_needed=20, threshold=1.218*sqrt(240)=18.87 → 20>18.87 → True
    assert is_total_dead(
        target_total=220.0, current_total=200, seconds_remaining=240, side="over", multiplier=_TM,
    ) is True


def test_total_alive_over_reachable():
    # target=220, current=210, 360s, "over"
    # points_needed=10, threshold=1.218*sqrt(360)=23.1 → 10<23.1 → False
    assert is_total_dead(
        target_total=220.0, current_total=210, seconds_remaining=360, side="over", multiplier=_TM,
    ) is False


def test_total_dead_under_exceeded():
    # target=220, current=245, 60s, "under"
    # points_needed=220-245=-25 → -(-25)=25>threshold(9.42) → True
    assert is_total_dead(
        target_total=220.0, current_total=245, seconds_remaining=60, side="under", multiplier=_TM,
    ) is True


def test_total_alive_under_not_exceeded():
    # target=220, current=230, 240s, "under"
    # points_needed=-10 → -(-10)=10 < threshold(18.87) → False
    assert is_total_dead(
        target_total=220.0, current_total=230, seconds_remaining=240, side="under", multiplier=_TM,
    ) is False


def test_total_dead_over_zero_seconds():
    # Oyun bitti, total ulaşılamadı
    assert is_total_dead(
        target_total=220.0, current_total=215, seconds_remaining=0, side="over", multiplier=_TM,
    ) is True


def test_total_dead_under_zero_seconds_exceeded():
    assert is_total_dead(
        target_total=220.0, current_total=225, seconds_remaining=0, side="under", multiplier=_TM,
    ) is True


def test_total_alive_over_zero_seconds_reached():
    # Total'e ulaşıldı, over kazandı → dead for over? Hayır — over WIN, not dead
    # current >= target → over kazandı → NOT dead (margin_to_cover <= 0)
    assert is_total_dead(
        target_total=220.0, current_total=221, seconds_remaining=0, side="over", multiplier=_TM,
    ) is False


def test_total_invalid_side_raises():
    import pytest
    with pytest.raises(ValueError, match="side"):
        is_total_dead(220.0, 200, 120, "both", _TM)
```

- [ ] **Step 2: Testi çalıştır, fail ettiğini doğrula**

```
pytest tests/unit/domain/math/test_safe_lead.py -v -k "spread or total"
```
Beklenen: `ImportError`.

- [ ] **Step 3: safe_lead.py'e yeni fonksiyonları ekle**

```python
# src/domain/math/safe_lead.py — mevcut is_mathematically_dead'ın ALTINA ekle

def is_spread_dead(
    margin_to_cover: float,
    seconds_remaining: int,
    multiplier: float = 0.861,
) -> bool:
    """NBA spread cover için Bill James %99 confidence.

    margin_to_cover: spread'i kapatmak için gereken puan.
    Pozitif = cover edemiyoruz. Negatif veya sıfır = zaten cover'dayız.
    """
    if margin_to_cover <= 0:
        return False
    if seconds_remaining <= 0:
        return margin_to_cover > 0
    return margin_to_cover >= multiplier * sqrt(seconds_remaining)


def is_total_dead(
    target_total: float,
    current_total: int,
    seconds_remaining: int,
    side: str,
    multiplier: float = 1.218,
) -> bool:
    """NBA totals için Poisson-based dead check.

    multiplier 1.218 = 0.861 × sqrt(2) — toplam variance daha yüksek.
    side="over": target'a yetişemeyeceksek dead.
    side="under": target'ı kesinlikle geçeceksek dead.
    """
    if side not in ("over", "under"):
        raise ValueError(f"side must be 'over' or 'under', got {side!r}")

    points_needed = target_total - current_total  # over için pozitif = iyi; under için negatif = iyi

    if seconds_remaining <= 0:
        if side == "over":
            return points_needed > 0   # total'e ulaşılamamış
        else:
            return points_needed < 0   # total geçilmiş

    threshold = multiplier * sqrt(seconds_remaining)

    if side == "over":
        return points_needed > threshold
    else:
        return -points_needed > threshold  # under: -(negative) = positive when exceeded
```

- [ ] **Step 4: Testi çalıştır, pass ettiğini doğrula**

```
pytest tests/unit/domain/math/test_safe_lead.py -v
```
Beklenen: Tüm testler PASSED (mevcut 7 + yeni 15 = 22 test).

- [ ] **Step 5: Commit**

```bash
git add src/domain/math/safe_lead.py tests/unit/domain/math/test_safe_lead.py
git commit -m "feat(domain): is_spread_dead + is_total_dead — Bill James spread/totals extensions"
```

---

## Task 4: Config Extensions

**Files:**
- Modify: `src/config/settings.py`
- Modify: `config.yaml`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

EntryConfig FLAT kalır — yeni alanlar eklenir. GateConfig da flat kalır.
BasketballExitConfig'e totals_multiplier + 2 yeni empirical sub-model eklenir.

- [ ] **Step 1: settings.py güncellemesi**

`src/config/settings.py`'de şu değişiklikleri yap:

**a) EntryConfig'e yeni alanlar ekle** (mevcut alanların ALTINA, `min_bet_usd`'den sonra):

```python
class EntryConfig(BaseModel):
    # ... mevcut tüm alanlar değişmez ...
    min_bet_usd: float = field(default=5.0)  # mevcut son alan
    # Spread-specific filters
    spread_min_price: float = 0.20
    spread_max_price: float = 0.80
    spread_large_threshold: float = 10.0   # bu veya üstü spread → gap_bonus ekle
    spread_gap_bonus: float = 0.02         # büyük spread için ek gap gereksinimi
    # Totals-specific filters
    totals_min_price: float = 0.20
    totals_max_price: float = 0.80
    totals_min_target_total: float = 200.0  # NBA totals için minimum
```

**b) Yeni empirical sub-model'ler ekle** (EmpiricalExitConfig'ın ALTINA):

```python
class SpreadEmpiricalConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    q4_late_seconds: int = 360
    q4_late_margin: int = 7
    q4_final_seconds: int = 180
    q4_final_margin: int = 4
    q4_endgame_seconds: int = 60
    q4_endgame_margin: int = 3


class TotalsEmpiricalConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    q4_late_seconds: int = 360
    q4_late_gap: int = 20
    q4_final_seconds: int = 180
    q4_final_gap: int = 12
    q4_endgame_seconds: int = 60
    q4_endgame_gap: int = 6
    ot_over_scale_pct: float = 0.75
```

**c) BasketballExitConfig'e yeni alanlar ekle**:

```python
class BasketballExitConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    bill_james_multiplier: float = 0.861
    totals_multiplier: float = 1.218           # YENİ: 0.861 × sqrt(2)
    structural_damage_ratio: float = 0.30
    empirical: EmpiricalExitConfig = EmpiricalExitConfig()
    overtime: OvertimeExitConfig = OvertimeExitConfig()
    spread_empirical: SpreadEmpiricalConfig = SpreadEmpiricalConfig()   # YENİ
    totals_empirical: TotalsEmpiricalConfig = TotalsEmpiricalConfig()   # YENİ
```

- [ ] **Step 2: config.yaml güncellemesi**

`config.yaml`'de `entry:` bloğuna ekle:

```yaml
entry:
  # ... mevcut alanlar değişmez ...
  min_bet_usd: 5.0
  # Spread-specific
  spread_min_price: 0.20
  spread_max_price: 0.80
  spread_large_threshold: 10.0
  spread_gap_bonus: 0.02
  # Totals-specific
  totals_min_price: 0.20
  totals_max_price: 0.80
  totals_min_target_total: 200.0
```

`config.yaml`'de `exit_basketball:` bloğunu güncelle:

```yaml
exit_basketball:
  bill_james_multiplier: 0.861
  totals_multiplier: 1.218
  structural_damage_ratio: 0.30
  empirical:
    q4_blowout_seconds: 720
    q4_blowout_deficit: 20
    q4_late_seconds: 360
    q4_late_deficit: 15
    q4_final_seconds: 180
    q4_final_deficit: 10
    q4_endgame_seconds: 60
    q4_endgame_deficit: 6
  overtime:
    seconds: 60
    deficit: 8
  spread_empirical:
    q4_late_seconds: 360
    q4_late_margin: 7
    q4_final_seconds: 180
    q4_final_margin: 4
    q4_endgame_seconds: 60
    q4_endgame_margin: 3
  totals_empirical:
    q4_late_seconds: 360
    q4_late_gap: 20
    q4_final_seconds: 180
    q4_final_gap: 12
    q4_endgame_seconds: 60
    q4_endgame_gap: 6
    ot_over_scale_pct: 0.75
```

- [ ] **Step 3: Testler hâlâ geçiyor mu**

```
pytest tests/ -q --tb=short 2>&1 | tail -5
```
Beklenen: Tüm mevcut testler PASSED (yeni field'lar default'lu, geriye dönük uyumlu).

- [ ] **Step 4: Commit**

```bash
git add src/config/settings.py config.yaml
git commit -m "feat(config): spread/totals entry filters + basketball exit empirical configs"
```

---

## Task 5: nba_spread_exit.py

**Files:**
- Create: `src/strategy/exit/nba_spread_exit.py`
- Create: `tests/unit/strategy/exit/test_nba_spread_exit.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

**Mimari not:** NEAR_RESOLVE ve SCALE_OUT monitor.py'de priority 1-2 olarak işlenir — bu modüle GELMEZ.
Spread exit priority sırası (bu modül içinde):
1. STRUCTURAL_DAMAGE (fiyat çöküşü + math dead)
2. SPREAD_MATH_DEAD (Bill James)
3. EMPIRICAL_DEAD (key numbers: 3, 7 puan)
4. Q1-Q3 → None
5. OT check

**margin_to_cover hesabı:**
```
actual_diff = our_score - opp_score  (= -deficit, çünkü deficit = opp - our)
BUY_YES (favorite covers): margin_to_cover = spread_line - actual_diff
BUY_NO  (underdog covers): margin_to_cover = -actual_diff - spread_line
```

- [ ] **Step 1: Failing test yaz**

```python
# tests/unit/strategy/exit/test_nba_spread_exit.py
"""nba_spread_exit.check() unit testleri."""
from __future__ import annotations

import pytest
from src.strategy.exit.nba_spread_exit import check
from src.models.enums import ExitReason


def _si(
    period_number: int = 4,
    clock_seconds: int = 300,
    our_score: int = 95,
    opp_score: int = 100,
    available: bool = True,
) -> dict:
    return {
        "available": available,
        "period_number": period_number,
        "clock_seconds": clock_seconds,
        "our_score": our_score,
        "opp_score": opp_score,
        "deficit": opp_score - our_score,
    }


_M = 0.861


def test_period_3_always_hold():
    """Q1-Q3 → None."""
    result = check(
        score_info=_si(period_number=3, clock_seconds=60, our_score=90, opp_score=105),
        spread_line=5.5,
        direction="BUY_YES",
        bid_price=0.30,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_unavailable_score_hold():
    result = check(
        score_info={"available": False},
        spread_line=5.5,
        direction="BUY_YES",
        bid_price=0.30,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_math_dead_buy_yes_q4():
    """BUY_YES, trailing by 12 with 5.5 spread, 60s left → margin=17.5 > threshold(6.67) → dead."""
    # our_score=88, opp_score=100 → actual_diff=-12
    # margin_to_cover = 5.5 - (-12) = 17.5
    # 0.861 * sqrt(60) = 6.67 → 17.5 >= 6.67 → True
    result = check(
        score_info=_si(period_number=4, clock_seconds=60, our_score=88, opp_score=100),
        spread_line=5.5,
        direction="BUY_YES",
        bid_price=0.20,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "SPREAD_MATH_DEAD" in result.detail
    assert result.sell_pct == 1.0
    assert result.partial is False


def test_math_dead_buy_no_q4():
    """BUY_NO underdog, favorite leading by 15 with 7.5 spread, 120s left → dead."""
    # our_score=85, opp_score=100 → actual_diff=-15
    # BUY_NO: margin_to_cover = -actual_diff - spread_line = 15 - 7.5 = 7.5
    # 0.861 * sqrt(120) = 9.43 → 7.5 < 9.43 → False (not dead by math)
    # ... but with more spread:
    # our=80, opp=100 → actual_diff=-20, BUY_NO: margin=20-7.5=12.5
    # 0.861 * sqrt(120) = 9.43 → 12.5 >= 9.43 → True
    result = check(
        score_info=_si(period_number=4, clock_seconds=120, our_score=80, opp_score=100),
        spread_line=7.5,
        direction="BUY_NO",
        bid_price=0.20,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "SPREAD_MATH_DEAD" in result.detail


def test_empirical_q4_endgame_key_number_3():
    """Q4 son 60s, margin_to_cover=3 → EMPIRICAL_DEAD."""
    # BUY_YES, our=97, opp=100 → actual_diff=-3, spread_line=0 (no spread needed)
    # margin=0 - (-3) = 3 >= q4_endgame_margin=3 AND clock<=60 → True
    result = check(
        score_info=_si(period_number=4, clock_seconds=60, our_score=97, opp_score=100),
        spread_line=0.0,
        direction="BUY_YES",
        bid_price=0.30,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "EMPIRICAL" in result.detail


def test_empirical_q4_late_key_number_7():
    """Q4 360s kala, margin_to_cover=7 → EMPIRICAL_DEAD."""
    # BUY_YES, our=89, opp=100 → actual_diff=-11, spread_line=4
    # margin=4-(-11)=15... yüksek (q4_late_margin=7 şartını sağlıyor ama
    # let us use a simpler scenario: our=93, opp=100, spread=4 → margin=4+7=11 ≥ 7 → empirical
    result = check(
        score_info=_si(period_number=4, clock_seconds=360, our_score=93, opp_score=100),
        spread_line=4.0,
        direction="BUY_YES",
        bid_price=0.25,
        entry_price=0.60,
        bill_james_multiplier=_M,
        q4_late_margin=7,
    )
    assert result is not None
    assert "EMPIRICAL" in result.detail


def test_structural_damage_q4():
    """Q4, fiyat entry'nin %30'unun altı + math dead → STRUCTURAL_DAMAGE."""
    # entry=0.60, bid=0.17 → ratio=0.283 < 0.30
    # our=85, opp=100, spread=5.5, 120s
    # margin=5.5-(-15)=20.5 → 0.861*sqrt(120)=9.43 → dead
    result = check(
        score_info=_si(period_number=4, clock_seconds=120, our_score=85, opp_score=100),
        spread_line=5.5,
        direction="BUY_YES",
        bid_price=0.17,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "STRUCTURAL" in result.detail


def test_covering_spread_alive():
    """Cover'dayız (margin_to_cover < 0) → None."""
    # our=106, opp=100, spread=5.5 → actual_diff=6 → margin=5.5-6=-0.5 < 0 → alive
    result = check(
        score_info=_si(period_number=4, clock_seconds=300, our_score=106, opp_score=100),
        spread_line=5.5,
        direction="BUY_YES",
        bid_price=0.60,
        entry_price=0.50,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_ot_spread_dead():
    """OT, son 60s, margin_to_cover >= 8 → OT_DEAD."""
    # our=90, opp=100, spread=0 → margin=10, period=5
    result = check(
        score_info=_si(period_number=5, clock_seconds=60, our_score=90, opp_score=100),
        spread_line=0.0,
        direction="BUY_YES",
        bid_price=0.15,
        entry_price=0.60,
        bill_james_multiplier=_M,
        ot_seconds=60,
        ot_margin=8,
    )
    assert result is not None
    assert "OT_DEAD" in result.detail
```

- [ ] **Step 2: Testi çalıştır, fail ettiğini doğrula**

```
pytest tests/unit/strategy/exit/test_nba_spread_exit.py -v
```
Beklenen: `ModuleNotFoundError`.

- [ ] **Step 3: nba_spread_exit.py implement et**

```python
# src/strategy/exit/nba_spread_exit.py
"""NBA spread exit — Bill James cover math + empirical key numbers."""
from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.math.safe_lead import is_spread_dead
from src.models.enums import ExitReason


@dataclass
class NbaSpreadCheckResult:
    reason: ExitReason
    detail: str
    sell_pct: float = 1.0
    partial: bool = False


def check(
    score_info: dict,
    spread_line: float,
    direction: str,
    bid_price: float = 0.0,
    entry_price: float = 0.0,
    bill_james_multiplier: float = 0.861,
    structural_damage_ratio: float = 0.30,
    ot_seconds: int = 60,
    ot_margin: int = 8,
    q4_late_seconds: int = 360,
    q4_late_margin: int = 7,
    q4_final_seconds: int = 180,
    q4_final_margin: int = 4,
    q4_endgame_seconds: int = 60,
    q4_endgame_margin: int = 3,
) -> NbaSpreadCheckResult | None:
    """NBA spread cover exit kararı.

    Near-resolve ve scale-out monitor.py'de önce çalışır — burada yok.
    Return None → HOLD. Return NbaSpreadCheckResult → exit.

    BUY_YES (favorite covers): margin_to_cover = spread_line - (our_score - opp_score)
    BUY_NO  (underdog covers): margin_to_cover = -(our_score - opp_score) - spread_line
    """
    if not score_info.get("available"):
        return None

    period: int = score_info.get("period_number") or 0
    clock: int = score_info.get("clock_seconds") or 0
    our_score: int = score_info.get("our_score") or 0
    opp_score: int = score_info.get("opp_score") or 0

    actual_diff = our_score - opp_score

    if direction == "BUY_YES":
        margin_to_cover = spread_line - actual_diff
    else:
        margin_to_cover = -actual_diff - spread_line

    is_ot = period > 4

    # Q1-Q3: hold
    if not is_ot and period < 4:
        return None

    # OT exit
    if is_ot and clock <= ot_seconds and margin_to_cover >= ot_margin:
        return NbaSpreadCheckResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"OT_DEAD period={period} clock={clock}s margin={margin_to_cover:.1f}",
        )

    if period == 4:
        # 1. Structural damage — fiyat çöküşü + math dead
        if (
            entry_price > 0
            and bid_price > 0
            and (bid_price / entry_price) < structural_damage_ratio
            and is_spread_dead(margin_to_cover, clock, bill_james_multiplier)
        ):
            return NbaSpreadCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"STRUCTURAL_DAMAGE price_ratio={bid_price/entry_price:.2f} margin={margin_to_cover:.1f}",
            )

        # 2. Bill James spread dead
        if is_spread_dead(margin_to_cover, clock, bill_james_multiplier):
            return NbaSpreadCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"SPREAD_MATH_DEAD margin={margin_to_cover:.1f} clock={clock}s",
            )

        # 3. Empirical key numbers (NBA spread: 3 ve 7 kritik)
        if _empirical_spread_dead(
            clock, margin_to_cover,
            q4_late_seconds, q4_late_margin,
            q4_final_seconds, q4_final_margin,
            q4_endgame_seconds, q4_endgame_margin,
        ):
            return NbaSpreadCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"EMPIRICAL_DEAD margin={margin_to_cover:.1f} clock={clock}s",
            )

    return None


def _empirical_spread_dead(
    clock: int,
    margin: float,
    late_sec: int,
    late_mar: int,
    final_sec: int,
    final_mar: int,
    endgame_sec: int,
    endgame_mar: int,
) -> bool:
    return (
        (clock <= late_sec and margin >= late_mar)
        or (clock <= final_sec and margin >= final_mar)
        or (clock <= endgame_sec and margin >= endgame_mar)
    )
```

- [ ] **Step 4: Testi çalıştır, pass ettiğini doğrula**

```
pytest tests/unit/strategy/exit/test_nba_spread_exit.py -v
```
Beklenen: 9 PASSED.

- [ ] **Step 5: Tam test suite**

```
pytest tests/ -q --tb=short 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
git add src/strategy/exit/nba_spread_exit.py tests/unit/strategy/exit/test_nba_spread_exit.py
git commit -m "feat(exit): nba_spread_exit — Bill James spread cover + empirical key numbers (3, 7)"
```

---

## Task 6: nba_totals_exit.py

**Files:**
- Create: `src/strategy/exit/nba_totals_exit.py`
- Create: `tests/unit/strategy/exit/test_nba_totals_exit.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

**OT logic:**
- `side="over"` + OT → `OT_OVER_WINDFALL`: sell_pct=0.75, partial=True (kâr kilitle)
- `side="under"` + OT → `OT_UNDER_DEAD`: full exit

**current_total** = `our_score + opp_score` (score_info'dan, direction-agnostic toplam skor)

- [ ] **Step 1: Failing test yaz**

```python
# tests/unit/strategy/exit/test_nba_totals_exit.py
"""nba_totals_exit.check() unit testleri."""
from __future__ import annotations

from src.strategy.exit.nba_totals_exit import check
from src.models.enums import ExitReason


def _si(
    period_number: int = 4,
    clock_seconds: int = 300,
    our_score: int = 110,
    opp_score: int = 108,
    available: bool = True,
) -> dict:
    return {
        "available": available,
        "period_number": period_number,
        "clock_seconds": clock_seconds,
        "our_score": our_score,
        "opp_score": opp_score,
        "deficit": opp_score - our_score,
    }


_TM = 1.218


def test_period_3_always_hold():
    result = check(
        score_info=_si(period_number=3, our_score=90, opp_score=85),
        target_total=225.0,
        side="over",
        bid_price=0.45,
        entry_price=0.50,
        totals_multiplier=_TM,
    )
    assert result is None


def test_unavailable_score_hold():
    result = check(
        score_info={"available": False},
        target_total=220.0,
        side="over",
        bid_price=0.40,
        entry_price=0.50,
        totals_multiplier=_TM,
    )
    assert result is None


def test_over_math_dead():
    """Over bet, total ulaşılamayacak → TOTALS_MATH_DEAD."""
    # our=90, opp=95 → current_total=185, target=220, points_needed=35
    # 1.218 * sqrt(240) = 18.87 → 35 > 18.87 → dead
    result = check(
        score_info=_si(period_number=4, clock_seconds=240, our_score=90, opp_score=95),
        target_total=220.0,
        side="over",
        bid_price=0.20,
        entry_price=0.55,
        totals_multiplier=_TM,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "TOTALS_MATH_DEAD" in result.detail
    assert result.sell_pct == 1.0
    assert result.partial is False


def test_under_math_dead():
    """Under bet, total aşıldı → TOTALS_MATH_DEAD."""
    # our=115, opp=115 → current=230, target=220
    # points_needed=220-230=-10 → -(-10)=10 > 1.218*sqrt(60)=9.44 → dead
    result = check(
        score_info=_si(period_number=4, clock_seconds=60, our_score=115, opp_score=115),
        target_total=220.0,
        side="under",
        bid_price=0.15,
        entry_price=0.55,
        totals_multiplier=_TM,
    )
    assert result is not None
    assert "TOTALS_MATH_DEAD" in result.detail


def test_over_empirical_dead_q4_late():
    """Over, Q4 360s, points_needed=20 → EMPIRICAL_DEAD."""
    result = check(
        score_info=_si(period_number=4, clock_seconds=360, our_score=90, opp_score=90),
        target_total=220.0,
        side="over",
        bid_price=0.20,
        entry_price=0.55,
        totals_multiplier=_TM,
        q4_late_gap=20,
    )
    assert result is not None
    assert "EMPIRICAL" in result.detail


def test_under_empirical_dead_q4_late():
    """Under, Q4 360s, current-target=20 → EMPIRICAL_DEAD."""
    # current=240, target=220 → excess=20 ≥ q4_late_gap=20
    result = check(
        score_info=_si(period_number=4, clock_seconds=360, our_score=120, opp_score=120),
        target_total=220.0,
        side="under",
        bid_price=0.15,
        entry_price=0.55,
        totals_multiplier=_TM,
        q4_late_gap=20,
    )
    assert result is not None
    assert "EMPIRICAL" in result.detail


def test_ot_over_windfall():
    """OT + side=over → OT_OVER_WINDFALL (partial, sell 75%)."""
    result = check(
        score_info=_si(period_number=5, clock_seconds=250, our_score=110, opp_score=110),
        target_total=215.0,
        side="over",
        bid_price=0.80,
        entry_price=0.50,
        totals_multiplier=_TM,
    )
    assert result is not None
    assert "OT_OVER_WINDFALL" in result.detail
    assert result.partial is True
    assert result.sell_pct == 0.75


def test_ot_under_dead():
    """OT + side=under → OT_UNDER_DEAD (full exit)."""
    result = check(
        score_info=_si(period_number=5, clock_seconds=250, our_score=108, opp_score=108),
        target_total=210.0,
        side="under",
        bid_price=0.10,
        entry_price=0.55,
        totals_multiplier=_TM,
    )
    assert result is not None
    assert "OT_UNDER_DEAD" in result.detail
    assert result.partial is False
    assert result.sell_pct == 1.0


def test_structural_damage_over():
    """Fiyat çöküşü + math dead → STRUCTURAL_DAMAGE."""
    # entry=0.60, bid=0.17 → ratio=0.28 < 0.30
    # current=180, target=225, points_needed=45, 240s → 45 > 18.87 → dead
    result = check(
        score_info=_si(period_number=4, clock_seconds=240, our_score=90, opp_score=90),
        target_total=225.0,
        side="over",
        bid_price=0.17,
        entry_price=0.60,
        totals_multiplier=_TM,
    )
    assert result is not None
    assert "STRUCTURAL" in result.detail


def test_alive_over_reachable():
    """Over, Q4, points_needed küçük → None."""
    # current=210, target=215, points_needed=5, 360s → 5 < 23.1 → alive
    result = check(
        score_info=_si(period_number=4, clock_seconds=360, our_score=105, opp_score=105),
        target_total=215.0,
        side="over",
        bid_price=0.60,
        entry_price=0.50,
        totals_multiplier=_TM,
    )
    assert result is None
```

- [ ] **Step 2: Testi çalıştır, fail ettiğini doğrula**

```
pytest tests/unit/strategy/exit/test_nba_totals_exit.py -v
```

- [ ] **Step 3: nba_totals_exit.py implement et**

```python
# src/strategy/exit/nba_totals_exit.py
"""NBA totals exit — Poisson-based scoring pace + empirical backup."""
from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.math.safe_lead import is_total_dead
from src.models.enums import ExitReason


@dataclass
class NbaTotalsCheckResult:
    reason: ExitReason
    detail: str
    sell_pct: float = 1.0
    partial: bool = False


def check(
    score_info: dict,
    target_total: float,
    side: str,
    bid_price: float = 0.0,
    entry_price: float = 0.0,
    totals_multiplier: float = 1.218,
    structural_damage_ratio: float = 0.30,
    ot_over_scale_pct: float = 0.75,
    q4_late_seconds: int = 360,
    q4_late_gap: int = 20,
    q4_final_seconds: int = 180,
    q4_final_gap: int = 12,
    q4_endgame_seconds: int = 60,
    q4_endgame_gap: int = 6,
) -> NbaTotalsCheckResult | None:
    """NBA totals exit kararı.

    Near-resolve ve scale-out monitor.py'de önce çalışır — burada yok.
    side: "over" (YES=over konvansiyonu) veya "under" (BUY_NO=under).
    Return None → HOLD. Return NbaTotalsCheckResult → exit.
    """
    if not score_info.get("available"):
        return None

    period: int = score_info.get("period_number") or 0
    clock: int = score_info.get("clock_seconds") or 0
    our_score: int = score_info.get("our_score") or 0
    opp_score: int = score_info.get("opp_score") or 0
    current_total = our_score + opp_score

    is_ot = period > 4

    # Q1-Q3: hold
    if not is_ot and period < 4:
        return None

    # OT — totals için özel
    if is_ot:
        if side == "over":
            return NbaTotalsCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"OT_OVER_WINDFALL period={period} current={current_total} target={target_total}",
                sell_pct=ot_over_scale_pct,
                partial=True,
            )
        else:
            return NbaTotalsCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"OT_UNDER_DEAD period={period} current={current_total} target={target_total}",
            )

    if period == 4:
        # 1. Structural damage
        if (
            entry_price > 0
            and bid_price > 0
            and (bid_price / entry_price) < structural_damage_ratio
            and is_total_dead(target_total, current_total, clock, side, totals_multiplier)
        ):
            return NbaTotalsCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"STRUCTURAL_DAMAGE price_ratio={bid_price/entry_price:.2f}",
            )

        # 2. Math dead
        if is_total_dead(target_total, current_total, clock, side, totals_multiplier):
            return NbaTotalsCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"TOTALS_MATH_DEAD current={current_total} target={target_total} clock={clock}s side={side}",
            )

        # 3. Empirical backup
        if _empirical_totals_dead(clock, current_total, target_total, side,
                                   q4_late_seconds, q4_late_gap,
                                   q4_final_seconds, q4_final_gap,
                                   q4_endgame_seconds, q4_endgame_gap):
            return NbaTotalsCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"EMPIRICAL_DEAD current={current_total} target={target_total} clock={clock}s side={side}",
            )

    return None


def _empirical_totals_dead(
    clock: int,
    current_total: int,
    target_total: float,
    side: str,
    late_sec: int,
    late_gap: int,
    final_sec: int,
    final_gap: int,
    endgame_sec: int,
    endgame_gap: int,
) -> bool:
    if side == "over":
        points_needed = target_total - current_total
        return (
            (clock <= late_sec and points_needed >= late_gap)
            or (clock <= final_sec and points_needed >= final_gap)
            or (clock <= endgame_sec and points_needed >= endgame_gap)
        )
    else:  # under
        excess = current_total - target_total
        return (
            (clock <= late_sec and excess >= late_gap)
            or (clock <= endgame_sec and excess >= endgame_gap)
        )
```

- [ ] **Step 4: Testi çalıştır, pass ettiğini doğrula**

```
pytest tests/unit/strategy/exit/test_nba_totals_exit.py -v
```
Beklenen: 9 PASSED.

- [ ] **Step 5: Tam test suite**

```
pytest tests/ -q --tb=short 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
git add src/strategy/exit/nba_totals_exit.py tests/unit/strategy/exit/test_nba_totals_exit.py
git commit -m "feat(exit): nba_totals_exit — Poisson totals math + OT windfall/danger + empirical"
```

---

## Task 7: NbaScoreCheckResult Interface Unification

**Files:**
- Modify: `src/strategy/exit/nba_score_exit.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

Tüm NBA check result tipleri aynı interface'e uysun: `reason`, `sell_pct`, `partial`.
monitor.py uniform şekilde okuyabilsin.

- [ ] **Step 1: NbaCheckResult'u güncelle**

`src/strategy/exit/nba_score_exit.py`'deki `NbaCheckResult` dataclass'ını değiştir:

```python
@dataclass
class NbaCheckResult:
    reason: ExitReason
    detail: str
    sell_pct: float = 1.0   # YENİ — default full exit
    partial: bool = False    # YENİ — default full exit
```

- [ ] **Step 2: Mevcut testler hâlâ geçiyor mu**

```
pytest tests/unit/strategy/exit/test_nba_score_exit.py -v
```
Beklenen: Tüm testler PASSED (yeni alanlar default'lu, geriye uyumlu).

- [ ] **Step 3: Commit**

```bash
git add src/strategy/exit/nba_score_exit.py
git commit -m "refactor(exit): NbaCheckResult add sell_pct + partial fields — uniform interface"
```

---

## Task 8: Monitor.py NBA Market-Type Routing

**Files:**
- Modify: `src/strategy/exit/monitor.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

**Satır sayısı kontrolü:** monitor.py şu an 341 satır. Yeni routing ~35 satır ekler → ~376 satır (400 altı ✓).

- [ ] **Step 1: Import ekle**

`monitor.py`'deki import satırına ekle:

```python
from src.strategy.exit import (
    market_flip, baseball_score_exit, favored, nba_score_exit,
    nba_spread_exit, nba_totals_exit,  # YENİ
    near_resolve, nfl_score_exit, price_cap, scale_out, hockey_score_exit,
    soccer_score_exit, tennis_score_exit,
)
from src.config.settings import ExitMonitorConfig, BasketballExitConfig  # BasketballExitConfig ekle
```

- [ ] **Step 2: evaluate() signature'ına basketball_exit_cfg ekle**

```python
def evaluate(
    pos: Position,
    score_info: dict | None = None,
    near_resolve_threshold_cents: int = 94,
    near_resolve_guard_min: int = 10,
    scale_out_tiers: list[dict] | None = None,
    monitor_cfg: ExitMonitorConfig | None = None,
    sl_params: SLParams | None = None,
    scale_out_min_realized_usd: float = 0.0,
    basketball_exit_cfg: BasketballExitConfig | None = None,   # YENİ
) -> MonitorResult:
```

- [ ] **Step 3: NBA routing bloğunu değiştir**

Mevcut NBA bloğunu (satır ~278-291) şu şekilde değiştir:

```python
    if _normalize(pos.sport_tag) == "nba" and score_info.get("available"):
        _bk = basketball_exit_cfg or BasketballExitConfig()
        mtype = pos.sports_market_type or "moneyline"

        if mtype == "spreads" and pos.spread_line is not None:
            sp_result = nba_spread_exit.check(
                score_info=score_info,
                spread_line=pos.spread_line,
                direction=pos.direction,
                bid_price=pos.bid_price,
                entry_price=pos.entry_price,
                bill_james_multiplier=_bk.bill_james_multiplier,
                structural_damage_ratio=_bk.structural_damage_ratio,
                ot_seconds=_bk.overtime.seconds,
                ot_margin=_bk.overtime.deficit,
                q4_late_seconds=_bk.spread_empirical.q4_late_seconds,
                q4_late_margin=_bk.spread_empirical.q4_late_margin,
                q4_final_seconds=_bk.spread_empirical.q4_final_seconds,
                q4_final_margin=_bk.spread_empirical.q4_final_margin,
                q4_endgame_seconds=_bk.spread_empirical.q4_endgame_seconds,
                q4_endgame_margin=_bk.spread_empirical.q4_endgame_margin,
            )
            if sp_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(
                        reason=sp_result.reason, detail=sp_result.detail,
                        partial=sp_result.partial, sell_pct=sp_result.sell_pct,
                    ),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )

        elif mtype == "totals" and pos.total_line is not None:
            effective_side = pos.total_side or "over"
            tot_result = nba_totals_exit.check(
                score_info=score_info,
                target_total=pos.total_line,
                side=effective_side,
                bid_price=pos.bid_price,
                entry_price=pos.entry_price,
                totals_multiplier=_bk.totals_multiplier,
                structural_damage_ratio=_bk.structural_damage_ratio,
                ot_over_scale_pct=_bk.totals_empirical.ot_over_scale_pct,
                q4_late_seconds=_bk.totals_empirical.q4_late_seconds,
                q4_late_gap=_bk.totals_empirical.q4_late_gap,
                q4_final_seconds=_bk.totals_empirical.q4_final_seconds,
                q4_final_gap=_bk.totals_empirical.q4_final_gap,
                q4_endgame_seconds=_bk.totals_empirical.q4_endgame_seconds,
                q4_endgame_gap=_bk.totals_empirical.q4_endgame_gap,
            )
            if tot_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(
                        reason=tot_result.reason, detail=tot_result.detail,
                        partial=tot_result.partial, sell_pct=tot_result.sell_pct,
                    ),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )

        else:  # moneyline (veya spread_line/total_line eksik → devre dışı)
            nba_result = nba_score_exit.check(
                score_info=score_info,
                elapsed_pct=elapsed_pct,
                sport_tag=pos.sport_tag,
                bid_price=pos.bid_price,
                entry_price=pos.entry_price,
                bill_james_multiplier=_bk.bill_james_multiplier,
                structural_damage_ratio=_bk.structural_damage_ratio,
                ot_seconds=_bk.overtime.seconds,
                ot_deficit=_bk.overtime.deficit,
                q4_blowout_seconds=_bk.empirical.q4_blowout_seconds,
                q4_blowout_deficit=_bk.empirical.q4_blowout_deficit,
                q4_late_seconds=_bk.empirical.q4_late_seconds,
                q4_late_deficit=_bk.empirical.q4_late_deficit,
                q4_final_seconds=_bk.empirical.q4_final_seconds,
                q4_final_deficit=_bk.empirical.q4_final_deficit,
                q4_endgame_seconds=_bk.empirical.q4_endgame_seconds,
                q4_endgame_deficit=_bk.empirical.q4_endgame_deficit,
            )
            if nba_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(
                        reason=nba_result.reason, detail=nba_result.detail,
                        partial=nba_result.partial, sell_pct=nba_result.sell_pct,
                    ),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )
```

**Not:** Mevcut moneyline bloğunda `nba_score_exit.check()` parametreleri hardcode'du (default'lara bırakılmıştı). Bu değişiklikle config'den okunuyor. mevcut default değerler aynı olduğu için davranış değişmez.

- [ ] **Step 4: Tüm testler geçiyor mu**

```
pytest tests/ -q --tb=short 2>&1 | tail -5
```
Beklenen: Tüm testler PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/strategy/exit/monitor.py
git commit -m "feat(monitor): NBA routing by sports_market_type — spread/totals/moneyline dispatch"
```

---

## Task 9: Scanner — NBA için Spreads/Totals Aç

**Files:**
- Modify: `src/orchestration/scanner.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

Şu an scanner tüm non-moneyline marketleri filtreler. NBA için "spreads" ve "totals" de kabul edilmeli.

- [ ] **Step 1: scanner.py'deki SMT filtresi**

Mevcut satır (≈167):
```python
if m.sports_market_type != "moneyline":
    return False
```

Değiştir:
```python
_NBA_TAGS = frozenset({"basketball_nba", "nba"})
_NBA_ALLOWED_SMT = frozenset({"moneyline", "spreads", "totals"})

# Sports market type filter
if _normalize(m.sport_tag) in _NBA_TAGS:
    if m.sports_market_type not in _NBA_ALLOWED_SMT:
        return False
elif m.sports_market_type != "moneyline":
    return False
```

Bu iki sabit dosyanın module-level'ına (class dışına) taşın.

- [ ] **Step 2: Mevcut testler geçiyor mu**

```
pytest tests/ -q --tb=short 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add src/orchestration/scanner.py
git commit -m "feat(scanner): allow spreads + totals sportsMarketType for NBA markets"
```

---

## Task 10: Entry Gate — Market Line Propagation + Spread/Totals Filters

**Files:**
- Modify: `src/strategy/entry/gate.py`
- Modify: `tests/unit/strategy/entry/test_gate.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

**gate.py şu an 202 satır.** Yeni eklemeler ~50 satır → ~252 satır (400 altı ✓).

GateConfig'e yeni flat alanlar ekle. gate.run()'da market_type'a göre farklı filtre uygula.
market_line bilgisini Signal'e yaz.

- [ ] **Step 1: GateConfig'e yeni alanlar ekle**

`src/strategy/entry/gate.py`'deki `GateConfig` dataclass'ına ekle:

```python
@dataclass
class GateConfig:
    # ... mevcut tüm alanlar değişmez ...
    min_bet_usd: float = field(default=5.0)  # mevcut son alan
    # Spread filters
    spread_min_price: float = field(default=0.20)
    spread_max_price: float = field(default=0.80)
    spread_large_threshold: float = field(default=10.0)
    spread_gap_bonus: float = field(default=0.02)
    # Totals filters
    totals_min_price: float = field(default=0.20)
    totals_max_price: float = field(default=0.80)
    totals_min_target_total: float = field(default=200.0)
```

- [ ] **Step 2: _passes_filters'e market_type parametresi ekle**

```python
def _passes_filters(
    gap: float,
    polymarket_price: float,
    bookmaker_prob: float,
    volume: float,
    cfg: GateConfig,
    market_type: str = "moneyline",
    spread_line: float | None = None,
    total_line: float | None = None,
) -> str | None:
    """Tüm filtrelerden geç. None = geçti, string = skip sebebi."""
    # Efektif gap eşiği — büyük spread için artırılır
    effective_gap_threshold = cfg.min_gap_threshold
    if market_type == "spreads" and spread_line is not None and spread_line >= cfg.spread_large_threshold:
        effective_gap_threshold += cfg.spread_gap_bonus

    if gap < effective_gap_threshold:
        return "GAP_TOO_LOW"

    # Fiyat aralığı (market_type'a göre)
    if market_type == "spreads":
        if polymarket_price < cfg.spread_min_price or polymarket_price > cfg.spread_max_price:
            return "PRICE_OUT_OF_RANGE"
    elif market_type == "totals":
        if polymarket_price < cfg.totals_min_price or polymarket_price > cfg.totals_max_price:
            return "PRICE_OUT_OF_RANGE"
        if total_line is not None and total_line < cfg.totals_min_target_total:
            return "TOTAL_TOO_LOW"
    else:  # moneyline
        if polymarket_price < cfg.min_polymarket_price or polymarket_price > cfg.max_entry_price:
            return "PRICE_OUT_OF_RANGE"

    if bookmaker_prob < cfg.min_favorite_probability:
        return "BOOKMAKER_PROB_TOO_LOW"
    if volume < cfg.min_market_volume:
        return "VOLUME_TOO_LOW"
    return None
```

- [ ] **Step 3: gate.run()'a parser çağrısı ve Signal propagation ekle**

`src/strategy/entry/gate.py`'nin başına import ekle:

```python
from src.domain.matching.market_line_parser import parse_spread_line, parse_total_line
```

`gate.run()` içindeki market loop'una ekle (enrich sonrası, `skip = _passes_filters(...)` öncesi):

```python
            # Market line parse (spread/totals için; moneyline'da None kalır)
            market_type = market.sports_market_type or "moneyline"
            spread_line: float | None = None
            total_line: float | None = None
            total_side_val: str | None = None

            if market_type == "spreads":
                spread_line = parse_spread_line(market.question)
                if spread_line is None:
                    results.append(GateResult(cid, skipped_reason="SPREAD_UNPARSEABLE"))
                    continue

            elif market_type == "totals":
                parsed = parse_total_line(market.question)
                if parsed is None:
                    results.append(GateResult(cid, skipped_reason="TOTAL_UNPARSEABLE"))
                    continue
                total_line, yes_side = parsed
                # total_side: direction'a göre ayarla (BUY_YES=over konvansiyonu, BUY_NO=under)
                # direction henüz belirlenmedi; default BUY_YES için yes_side kullan
                # (direction belirlendikten sonra total_side ayarlanacak)
                total_side_val = yes_side  # BUY_YES için; BUY_NO için aşağıda flip
```

`_passes_filters` çağrısını güncelle:

```python
            skip = _passes_filters(
                gap, polymarket_price, prob.prob, market.volume_24h, self.config,
                market_type=market_type,
                spread_line=spread_line,
                total_line=total_line,
            )
```

Signal oluştururken yeni alanları ekle:

```python
            # BUY_NO totals için side flip
            actual_total_side = total_side_val
            if market_type == "totals" and direction == Direction.BUY_NO and total_side_val:
                actual_total_side = "under" if total_side_val == "over" else "over"

            signal = Signal(
                condition_id=cid,
                direction=direction,
                anchor_probability=prob.prob,
                market_price=polymarket_price,
                confidence=confidence,
                size_usdc=stake,
                entry_reason=EntryReason.NORMAL,
                bookmaker_prob=prob.prob,
                num_bookmakers=prob.num_bookmakers,
                has_sharp=prob.has_sharp,
                sport_tag=market.sport_tag,
                event_id=market.event_id or "",
                sports_market_type=market_type,     # YENİ
                spread_line=spread_line,             # YENİ
                total_line=total_line,               # YENİ
                total_side=actual_total_side,        # YENİ
            )
```

- [ ] **Step 4: test_gate.py'e yeni filter testleri ekle**

`tests/unit/strategy/entry/test_gate.py` dosyasının SONUNA ekle:

```python
# ── Spread filter tests ──────────────────────────────────────────
def test_filters_spread_price_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.15, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="spreads",
    )
    assert reason == "PRICE_OUT_OF_RANGE"


def test_filters_spread_price_in_range():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.50, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="spreads",
    )
    assert reason is None


def test_filters_spread_large_spread_needs_gap_bonus():
    """spread_line >= 10 → efektif gap_threshold 0.08+0.02=0.10 olur."""
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.09, polymarket_price=0.50, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="spreads",
        spread_line=10.5,   # büyük spread
    )
    assert reason == "GAP_TOO_LOW"


def test_filters_spread_small_spread_normal_gap():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.09, polymarket_price=0.50, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="spreads",
        spread_line=5.5,    # normal spread, gap bonus yok
    )
    assert reason is None


# ── Totals filter tests ──────────────────────────────────────────
def test_filters_totals_price_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.15, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="totals",
    )
    assert reason == "PRICE_OUT_OF_RANGE"


def test_filters_totals_target_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.50, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="totals",
        total_line=150.0,  # < 200
    )
    assert reason == "TOTAL_TOO_LOW"


def test_filters_totals_pass():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.50, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
        market_type="totals",
        total_line=220.5,
    )
    assert reason is None
```

- [ ] **Step 5: Testleri çalıştır**

```
pytest tests/unit/strategy/entry/test_gate.py -v
```
Beklenen: Mevcut + yeni testler PASSED.

- [ ] **Step 6: Tam test suite**

```
pytest tests/ -q --tb=short 2>&1 | tail -5
```

- [ ] **Step 7: Commit**

```bash
git add src/strategy/entry/gate.py tests/unit/strategy/entry/test_gate.py
git commit -m "feat(gate): spread/totals filters + market_line propagation to Signal"
```

---

## Task 11: Entry Processor — Position'a Propagation

**Files:**
- Modify: `src/orchestration/entry_processor.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Position oluşturma bloğunu güncelle**

`src/orchestration/entry_processor.py`'deki `Position(...)` çağrısına ekle:

```python
        pos = Position(
            condition_id=market.condition_id,
            token_id=token_id,
            direction=signal.direction.value,
            entry_price=fill_price,
            size_usdc=signal.size_usdc,
            shares=shares,
            current_price=fill_price,
            anchor_probability=signal.anchor_probability,
            entry_reason=signal.entry_reason.value,
            confidence=signal.confidence,
            sport_tag=market.sport_tag,
            event_id=market.event_id or "",
            match_start_iso=market.match_start_iso,
            match_live=market.event_live,
            question=market.question,
            match_title=market.match_title,
            end_date_iso=market.end_date_iso,
            slug=market.slug,
            bookmaker_prob=signal.bookmaker_prob,
            # YENİ — market type propagation
            sports_market_type=signal.sports_market_type,
            spread_line=signal.spread_line,
            total_line=signal.total_line,
            total_side=signal.total_side,
        )
```

- [ ] **Step 2: Tüm testler geçiyor mu**

```
pytest tests/ -q --tb=short 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add src/orchestration/entry_processor.py
git commit -m "feat(entry_processor): propagate sports_market_type + spread/total fields to Position"
```

---

## Task 12: Factory.py — GateConfig + Monitor Güncelleme

**Files:**
- Modify: `src/orchestration/factory.py`

### Arch check
`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: GateConfig'e yeni alanlar ekle**

`factory.py`'deki `gate_cfg = GateConfig(...)` bloğuna ekle:

```python
    gate_cfg = GateConfig(
        # ... mevcut alanlar değişmez ...
        min_bet_usd=cfg.entry.min_bet_usd,
        # YENİ — spread/totals filters
        spread_min_price=cfg.entry.spread_min_price,
        spread_max_price=cfg.entry.spread_max_price,
        spread_large_threshold=cfg.entry.spread_large_threshold,
        spread_gap_bonus=cfg.entry.spread_gap_bonus,
        totals_min_price=cfg.entry.totals_min_price,
        totals_max_price=cfg.entry.totals_max_price,
        totals_min_target_total=cfg.entry.totals_min_target_total,
    )
```

- [ ] **Step 2: monitor.evaluate() çağrısına basketball_exit_cfg ekle**

Agent'ın monitor.evaluate() çağrılarını bulup (agent.py'de muhtemelen), basketball_exit_cfg geçir:

```python
monitor.evaluate(
    pos=pos,
    score_info=score_info,
    # ... diğer parametreler ...
    basketball_exit_cfg=cfg.exit_basketball,   # YENİ
)
```

Not: Eğer agent.py'de multiple çağrı varsa hepsini güncelle.

- [ ] **Step 3: Tüm testler geçiyor mu**

```
pytest tests/ -q --tb=short 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
git add src/orchestration/factory.py
git commit -m "feat(factory): wire spread/totals GateConfig + basketball_exit_cfg to monitor"
```

---

## Task 13: DECISIONS.md Update

**Files:**
- Modify: `DECISIONS.md`

- [ ] **Step 1: NBA Spread bölümü ekle**

`DECISIONS.md`'ye NBA Spread bölümü ekle:

```markdown
## NBA Spread

**Entry:**
- Gap threshold moneyline ile aynı (0.08). Spread ≥ 10 → +0.02 bonus (garbage time blowout riski).
- Fiyat aralığı 0.20-0.80 (moneyline'dan dar: uç noktalar daha volatil).
- Polymarket format: "Spread: TEAM_NAME (-X.5)" — SMT='spreads'.

**Exit — Math:**
- Bill James multiplier 0.861 (moneyline ile aynı — spread Poisson dağılımı identik).
- margin_to_cover = spread_line - (our_score - opp_score) [BUY_YES / favorite].
- margin_to_cover = -(our_score - opp_score) - spread_line [BUY_NO / underdog].
- Q1-Q3 her zaman HOLD (spread variance Q4'te kristalleşir).

**Exit — Empirical key numbers:**
- 360s kala, margin ≥ 7: 1 possession farkı kritik threshold.
- 180s kala, margin ≥ 4: ~2 dakika, 4 puan geri dönüş zorlaşır.
- 60s kala, margin ≥ 3: "key number 3" — NBA spread'de kritik.
- Kaynak: 14 yıl NBA spread kapama verisi.
```

- [ ] **Step 2: NBA Totals bölümü ekle**

```markdown
## NBA Totals

**Entry:**
- Min target total: 200 (likidite + edge optimum zone — düşük totals thin market).
- Fiyat aralığı 0.20-0.80.
- Polymarket format: "TEAM vs TEAM: O/U X.5" — SMT='totals'. YES=over konvansiyonu.

**Exit — Math:**
- Multiplier 1.218 = 0.861 × √2 (toplam variance = iki takım toplamı → √2 factor).
- Over: is_total_dead(target, current, clock, "over") → points_needed > 1.218*sqrt(clock).
- Under: is_total_dead(target, current, clock, "under") → excess > 1.218*sqrt(clock).

**Exit — OT:**
- Over + OT → OT_OVER_WINDFALL: %75 sat (her OT ~25 puan ekler, kâr kilitle).
- Under + OT → OT_UNDER_DEAD: tam çıkış (total kesinlikle artar, under kaybetti).

**Exit — Empirical:**
- Over: 360s kala points_needed ≥ 20 / 180s kala ≥ 12 / 60s kala ≥ 6.
- Under: 360s kala excess ≥ 20 / 60s kala excess ≥ 6.
```

- [ ] **Step 3: Commit**

```bash
git add DECISIONS.md
git commit -m "docs(DECISIONS): NBA Spread + Totals — math rationale, empirical thresholds, OT rules"
```

---

## Task 14: Final Validation

- [ ] **Step 1: Tam test suite**

```
pytest tests/ -q 2>&1 | tail -10
```
Beklenen: 863 + yeni testler, 0 failed.
Tahmini yeni test sayısı: +12 (models) +13 (parser) +15 (safe_lead) +9 (spread_exit) +9 (totals_exit) +7 (gate) = **+65 → ~928 test**

- [ ] **Step 2: Mimari kontrol**

```bash
# 400+ satır dosya var mı?
find src -name "*.py" | xargs wc -l | sort -rn | head -10

# Domain'de I/O var mı?
grep -r "import requests\|import os\|open(" src/domain/ --include="*.py"

# Magic number kaldı mı? (safe_lead, spread_exit, totals_exit)
grep -E "[0-9]{2,}\.[0-9]" src/domain/math/safe_lead.py src/strategy/exit/nba_spread_exit.py src/strategy/exit/nba_totals_exit.py
```

- [ ] **Step 3: Drift kontrol**

```bash
# DECISIONS.md NBA Spread + Totals bölümleri var mı?
grep -c "NBA Spread\|NBA Totals" DECISIONS.md

# config.yaml spread/totals alanları var mı?
grep -c "spread_min_price\|totals_multiplier" config.yaml
```

---

## Özet — Beklenen Durum Sonunda

| Metrik | Önce | Sonra |
|---|---|---|
| Test sayısı | 863 | ~928 |
| NBA market tipleri | moneyline | moneyline + spreads + totals |
| Yeni dosyalar | - | market_line_parser, nba_spread_exit, nba_totals_exit |
| Config alanları | 17 entry flat | 17 + 7 yeni flat |
| Math fonksiyonları | is_mathematically_dead | + is_spread_dead, is_total_dead |
