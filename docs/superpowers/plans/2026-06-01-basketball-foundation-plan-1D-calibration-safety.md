# Basketball Foundation — Plan 1.D: Calibration + Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development veya superpowers:executing-plans.

**Goal:** Profesyonel sportsbook standardını yakala — modelin gerçek para için güvenli olması için 5 madde: anormal veri reddi, sezon başı rating reset, spor-bağımsız kalibrasyon altyapısı + haftalık otomatik update, dashboard isabet göstergesi + alarm, model çıktısı güvenlik kemeri.

**Architecture:** Tenis calibration.py spor-bağımsız → `src/domain/calibration/` altına taşı. Basket de aynı altyapıyı kullanır. Haftalık update orchestration katmanında scheduler hook (Sackmann refresh paralel). Branches kartı (dashboard.html) PnL altına "% isabet" alt-satır + bozulma alarmı (Telegram + kart kırmızı).

**Tech Stack:** Python 3.12+, stdlib, mevcut Pydantic + dataclass, pytest. Dashboard: HTML+JS (Flask render).

---

## File Structure

### Yeni dosyalar

| Dosya | Sorumluluk |
|---|---|
| `src/domain/calibration/__init__.py` | Paket başlatıcı |
| `src/domain/calibration/curve.py` | Spor-bağımsız calibration (tennis/calibration.py kopyası) |
| `src/domain/calibration/sanity.py` | Output cliprange (P %5-%95 güvenlik kemeri) |
| `src/domain/pricing/basketball/season_reset.py` | Sezon başı rating mean-reversion logic |
| `src/orchestration/calibration_refresher.py` | Haftalık kalibrasyon update orchestrator (Sackmann refresh paralel) |
| `scripts/calibration_health_report.py` | Son N maç model isabet raporu (dashboard veri kaynağı) |

### Yeni test dosyaları

| Dosya | Test edilen |
|---|---|
| `tests/unit/domain/calibration/__init__.py` | (boş) |
| `tests/unit/domain/calibration/test_curve.py` | Generic curve (tennis testlerinden kopya, sport-tag bağımsız) |
| `tests/unit/domain/calibration/test_sanity.py` | Cliprange [0.05, 0.95] |
| `tests/unit/domain/pricing/basketball/test_season_reset.py` | %25 mean-reversion + edge cases |
| `tests/unit/orchestration/test_calibration_refresher.py` | Haftalık update tetik mantığı |

### Modifiye edilecek

| Dosya | Değişiklik |
|---|---|
| `src/domain/pricing/tennis/calibration.py` | **Sil** — yeni `src/domain/calibration/curve.py` import et |
| Tennis import noktaları (3 dosya) | Yeni location'a redirect |
| `src/domain/pricing/basketball/efficiency_metrics.py` | Outlier guard ekle (possessions 60-130) |
| `src/strategy/enrichment/basketball_anchor_enricher.py` | Calibration curve param + apply_calibration çağrısı + sanity cliprange |
| `src/orchestration/factory.py` | `_maybe_invoke_calibration_refresh` hook (haftalık + boot stale check) |
| `src/presentation/dashboard/computed.py` | Per-sport accuracy + Brier hesabı |
| `src/presentation/dashboard/static/js/dashboard.js` | Branches kartına "% isabet" alt-satır render |
| `src/presentation/dashboard/templates/dashboard.html` | Branches kartına isabet placeholder |
| `config.yaml` | Calibration eşikleri (n_bins, weekly_refresh_days, accuracy_alarm_threshold) |

---

## Tasks

### Task 1: Anormal Veri Reddi (Outlier Guard)

**Files:**
- Modify: `src/domain/pricing/basketball/efficiency_metrics.py`
- Test: `tests/unit/domain/pricing/basketball/test_efficiency_metrics.py` (extend)

- [ ] **Step 1.1: Test ekle**

Mevcut `test_efficiency_metrics.py`'a ekle:

```python
def test_outlier_pace_filtered_out():
    """Anormal possessions (10) içeren maç AdjO hesabına dahil edilmez."""
    from src.infrastructure.data.basketball.schemas import GameRecord
    games = [
        _game("LAL", "GSW", 110, 100, 100.0, 100.0),  # normal
        _game("LAL", "PHX", 110, 100, 10.0, 10.0),   # outlier (impossible pace)
    ]
    eff = compute_team_efficiency(games, team="LAL")
    # Sadece normal maç sayılır
    assert abs(eff.adj_pace - 100.0) < 0.01
    assert abs(eff.adj_o - 110.0) < 0.01


def test_outlier_too_high_pace_filtered():
    """200 possessions = imkansız, filtre."""
    from src.infrastructure.data.basketball.schemas import GameRecord
    games = [
        _game("LAL", "GSW", 110, 100, 100.0, 100.0),
        _game("LAL", "PHX", 250, 100, 200.0, 200.0),  # outlier
    ]
    eff = compute_team_efficiency(games, team="LAL")
    assert abs(eff.adj_pace - 100.0) < 0.01
```

- [ ] **Step 1.2: Implementation güncelle**

`efficiency_metrics.py`'da `compute_team_efficiency` içine `_POSS_MIN` ve `_POSS_MAX` sabitleri + filtre ekle:

```python
# Üst sabitler kısmına:
_POSS_MIN = 60.0   # Tarihsel NBA minimum
_POSS_MAX = 130.0  # Tarihsel NBA maximum

# Loop içinde:
for g in games:
    if team not in (g.home_team, g.away_team):
        continue
    off, dfn, pace = _raw_efficiency_per_game(g, team)
    if pace < _POSS_MIN or pace > _POSS_MAX:
        logger.warning("outlier game skipped: %s pace=%.1f", g.game_id, pace)
        continue
    off_vals.append(off)
    def_vals.append(dfn)
    pace_vals.append(pace)
```

Logger import et üste.

- [ ] **Step 1.3: Test PASS**

Run: `python -m pytest tests/unit/domain/pricing/basketball/test_efficiency_metrics.py -v`

- [ ] **Step 1.4: Commit**

```bash
git add src/domain/pricing/basketball/efficiency_metrics.py tests/unit/domain/pricing/basketball/test_efficiency_metrics.py
git commit -m "feat(basketball/domain): outlier pace filter (60-130) — Plan 1.D Task 1"
```

---

### Task 2: Sezon Başı Rating Reset

**Files:**
- Create: `src/domain/pricing/basketball/season_reset.py`
- Test: `tests/unit/domain/pricing/basketball/test_season_reset.py`

- [ ] **Step 2.1: Test**

```python
"""Sezon başı rating reset — FiveThirtyEight paterni (%25 mean reversion)."""
from __future__ import annotations
from src.domain.pricing.basketball.team_elo import EloRating, DEFAULT_RATING
from src.domain.pricing.basketball.season_reset import (
    revert_to_mean, REVERT_FRACTION,
)


def test_revert_to_mean_strong_team_loses_quarter():
    """%25 ortalamaya çekiş: 1700 → 1500 + 0.75 × (1700-1500) = 1650."""
    pre = EloRating(rating=1700.0, games=80)
    post = revert_to_mean(pre)
    assert abs(post.rating - 1650.0) < 0.01
    # Sezon başında games=0 sıfırlanmaz (rating gücü korunur, RD ile değil)
    assert post.games == pre.games  # games sayacı korunur


def test_revert_to_mean_weak_team_gains_quarter():
    """1300 → 1500 - 0.75 × (1500-1300) = 1350."""
    pre = EloRating(rating=1300.0, games=80)
    post = revert_to_mean(pre)
    assert abs(post.rating - 1350.0) < 0.01


def test_revert_to_mean_average_team_unchanged():
    pre = EloRating(rating=DEFAULT_RATING, games=80)
    post = revert_to_mean(pre)
    assert abs(post.rating - DEFAULT_RATING) < 0.01


def test_revert_fraction_is_quarter():
    """FiveThirtyEight standardı: %25 reversion."""
    assert abs(REVERT_FRACTION - 0.25) < 0.001
```

- [ ] **Step 2.2: Implementation**

```python
# src/domain/pricing/basketball/season_reset.py
"""Sezon başı rating mean-reversion — FiveThirtyEight paterni.

Yeni sezonda takım roster'ı önemli ölçüde değişebilir (trade, sakatlık,
emeklilik, draft). Tarihsel rating'leri tam carry-over yapmak yanlış
tahminlere yol açar. Çözüm: %25 ortalamaya çekiş.

  post = pre × (1 - 0.25) + DEFAULT_RATING × 0.25

Domain layer — saf math, I/O yok.
"""
from __future__ import annotations

from dataclasses import replace

from src.domain.pricing.basketball.team_elo import DEFAULT_RATING, EloRating

REVERT_FRACTION = 0.25


def revert_to_mean(rating: EloRating) -> EloRating:
    """Sezon başında rating'i %25 ortalamaya çek (games sayacı korunur)."""
    new_rating = rating.rating * (1 - REVERT_FRACTION) + DEFAULT_RATING * REVERT_FRACTION
    return replace(rating, rating=new_rating)
```

- [ ] **Step 2.3: PASS**

- [ ] **Step 2.4: Commit**

```bash
git add src/domain/pricing/basketball/season_reset.py tests/unit/domain/pricing/basketball/test_season_reset.py
git commit -m "feat(basketball/domain): sezon başı rating reset %25 — Plan 1.D Task 2"
```

---

### Task 3: Calibration Generic Refactor + Basket Entegrasyon + Cliprange

**Files:**
- Create: `src/domain/calibration/__init__.py`
- Create: `src/domain/calibration/curve.py` (tennis/calibration.py'in birebir kopyası)
- Create: `src/domain/calibration/sanity.py`
- Modify: `src/domain/pricing/tennis/calibration.py` → re-export wrapper (geriye uyumluluk)
- Modify: `src/strategy/enrichment/basketball_anchor_enricher.py` (calibration_curves param)
- Test: `tests/unit/domain/calibration/test_curve.py`
- Test: `tests/unit/domain/calibration/test_sanity.py`

- [ ] **Step 3.1: Generic curve modülü oluştur**

```python
# src/domain/calibration/__init__.py
"""Spor-bağımsız kalibrasyon altyapısı (Plan 1.D)."""
```

```python
# src/domain/calibration/curve.py
# Tennis/calibration.py içeriğinin birebir kopyası — kod zaten sport-agnostic.
# Sadece konumu domain'in genel kalibrasyon klasörüne taşındı.
```

(tennis/calibration.py'in tam içeriğini kopyala)

- [ ] **Step 3.2: Sanity (cliprange) modülü**

```python
# src/domain/calibration/sanity.py
"""Model output güvenlik kemeri — P(YES) [%5, %95] aralığına kırp.

Sapıtan model "%100 kazanır" derse:
  - Polymarket fiyat 50¢ olsa edge = 0.5 → büyük bahis
  - Gerçek tahmin %50 olsaymış, %0.50 ortalamadan büyük sapma → büyük kayıp

Cliprange tüm probability anchor'ların geçtiği son katman.
Domain — saf math, I/O yok.
"""
from __future__ import annotations

# %5-%95 aralığı FiveThirtyEight + Pinnacle standart safety net.
PROB_FLOOR = 0.05
PROB_CEILING = 0.95


def cliprange(prob: float) -> float:
    """P(YES) → [%5, %95] aralığında kırp."""
    return max(PROB_FLOOR, min(PROB_CEILING, prob))
```

Test:

```python
# tests/unit/domain/calibration/test_sanity.py
from src.domain.calibration.sanity import cliprange, PROB_FLOOR, PROB_CEILING


def test_cliprange_lower_bound():
    assert cliprange(0.0) == PROB_FLOOR
    assert cliprange(0.01) == PROB_FLOOR


def test_cliprange_upper_bound():
    assert cliprange(1.0) == PROB_CEILING
    assert cliprange(0.99) == PROB_CEILING


def test_cliprange_normal_passthrough():
    assert cliprange(0.5) == 0.5
    assert cliprange(0.7) == 0.7
```

- [ ] **Step 3.3: Tennis re-export (backwards compat)**

`src/domain/pricing/tennis/calibration.py` içeriğini değiştir — sadece re-export:

```python
"""Geriye uyumluluk shim — yeni location: src/domain/calibration/curve.py.

Plan 1.D refactor: calibration spor-bağımsız hale getirildi.
Mevcut tennis import'ları bu shim üzerinden çalışmaya devam eder.
"""
from src.domain.calibration.curve import (
    CalibrationCurve, identity_curve, fit_calibration, apply_calibration,
)

__all__ = ["CalibrationCurve", "identity_curve", "fit_calibration", "apply_calibration"]
```

- [ ] **Step 3.4: Basketball enricher genişlet**

`basketball_anchor_enricher.py`'a `calibration_curves` ve `apply_cliprange` ekle (tennis_anchor_enricher pattern):

```python
# imports:
from src.domain.calibration.curve import CalibrationCurve, apply_calibration
from src.domain.calibration.sanity import cliprange

# fonksiyon imzasına:
calibration_curves: dict[str, CalibrationCurve] | None = None,

# model_p hesabından sonra:
if calibration_curves:
    curve = calibration_curves.get(market_type.lower())
    if curve is not None:
        model_p = apply_calibration(model_p, curve)

# son satırdan önce:
model_p = cliprange(model_p)
```

- [ ] **Step 3.5: Test (kalibrasyon + cliprange entegrasyon)**

```python
# tests/unit/strategy/enrichment/test_basketball_anchor_enricher.py'a ekle:

def test_enrich_applies_calibration_curve_when_provided():
    from src.domain.calibration.curve import fit_calibration
    # %70 dediği yerlerde gerçekte %60 olan kalibrasyon eğrisi
    preds = [0.7] * 100
    outs = [1] * 60 + [0] * 40
    curve = fit_calibration(preds, outs, n_bins=10)
    ratings = {
        "LAL": EloRating(rating=1600.0),
        "GSW": EloRating(rating=1400.0),
    }
    efficiencies = {
        "LAL": TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0),
        "GSW": TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0),
    }
    res_uncal = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings=ratings, efficiencies=efficiencies,
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    res_cal = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings=ratings, efficiencies=efficiencies,
        home_advantage=100.0, blend_elo=0.55, line=None,
        calibration_curves={"moneyline": curve},
    )
    # Kalibrasyon eğrisi %70 → %60 → calibrated < uncalibrated
    assert res_cal.probability.probability < res_uncal.probability.probability


def test_enrich_clips_extreme_model_output():
    """Aşırı yüksek rating farkı → model %99+ verebilir; cliprange %95'e kırp."""
    ratings = {
        "LAL": EloRating(rating=2200.0),  # imkansız güç
        "GSW": EloRating(rating=1000.0),
    }
    efficiencies = {
        "LAL": TeamEfficiency(adj_o=140.0, adj_d=80.0, adj_pace=100.0),
        "GSW": TeamEfficiency(adj_o=80.0, adj_d=140.0, adj_pace=100.0),
    }
    res = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings=ratings, efficiencies=efficiencies,
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert res.probability.probability <= 0.95
```

- [ ] **Step 3.6: Tüm test'leri çalıştır — regresyon**

Run: `python -m pytest tests/unit -q`

- [ ] **Step 3.7: Commit**

```bash
git add src/domain/calibration src/domain/pricing/tennis/calibration.py \
        src/strategy/enrichment/basketball_anchor_enricher.py \
        tests/unit/domain/calibration tests/unit/strategy/enrichment/test_basketball_anchor_enricher.py
git commit -m "feat(calibration): generic refactor + basket entegrasyon + cliprange — Plan 1.D Task 3+5"
```

(Task 3 ve Task 5 birleştirildi — cliprange basket_anchor_enricher'ın ayrılmaz parçası, beraber commit)

---

### Task 4: Branches Kartı — "% İsabet" Alt-Satır + Alarm

**Files:**
- Modify: `src/presentation/dashboard/computed.py`
- Modify: `src/presentation/dashboard/static/js/dashboard.js`
- Modify: `src/presentation/dashboard/templates/dashboard.html` (yalnız placeholder)
- Create: `scripts/calibration_health_report.py`

- [ ] **Step 4.1: Health report scripti (veri kaynağı)**

```python
# scripts/calibration_health_report.py
"""Per-sport model isabet + Brier raporu — dashboard veri kaynağı.

Son N kapanmış trade pozisyonu için:
  - model_p (kayıt edilmiş enricher çıktısı)
  - gerçek sonuç (resolution)
Brier score + accuracy hesapla, JSON dosyaya yaz.

Branches kartı bu JSON'dan okur (cycle başına otomatik).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime, timezone


_OUTPUT_PATH = Path("data/model_health.json")
_LOOKBACK_TRADES = 50


def compute_health(trades: list[dict]) -> dict[str, dict]:
    """Trade listesinden per-sport accuracy + Brier."""
    by_sport: dict[str, list[tuple[float, int]]] = {}
    for t in trades[-_LOOKBACK_TRADES * 5:]:  # son ~250 trade taramaya yetecek
        sport = t.get("sport_tag", "").lower()
        model_p = t.get("anchor_probability")
        outcome = t.get("resolved_outcome")  # 1=YES kazandı, 0=NO
        if sport and model_p is not None and outcome is not None:
            by_sport.setdefault(sport, []).append((float(model_p), int(outcome)))
    out: dict[str, dict] = {}
    for sport, samples in by_sport.items():
        if len(samples) < 10:
            continue
        last = samples[-_LOOKBACK_TRADES:]
        correct = sum(1 for p, o in last if (p > 0.5) == (o == 1))
        brier = sum((p - o) ** 2 for p, o in last) / len(last)
        out[sport] = {
            "accuracy": correct / len(last),
            "brier": brier,
            "n_trades": len(last),
        }
    return out


def main():
    trades_path = Path("logs/audit/trade_history.jsonl")
    if not trades_path.exists():
        print("[HEALTH] trade history not found")
        return 0
    trades = []
    with trades_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                trades.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    health = compute_health(trades)
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "sports": health,
    }
    tmp = _OUTPUT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(_OUTPUT_PATH)
    print(f"[HEALTH] computed for {len(health)} sports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4.2: computed.py'a sport_health ekle**

`src/presentation/dashboard/computed.py` içine `read_sport_health()` fonksiyonu ekle (JSON dosyasından oku, dashboard JSON payload'ına dahil).

(detay implementation görece basit JSON read, file path config'den)

- [ ] **Step 4.3: dashboard.html branches kartına placeholder**

Mevcut branches kart template'ine her bir spor öğesine ek satır:

```html
<!-- Mevcut "+18% / 8 trades" altına ekle: -->
<div class="branch-accuracy" data-sport="tennis">--</div>
```

- [ ] **Step 4.4: dashboard.js branch render güncelleme**

JS'de branches render'ına health JSON'undan accuracy oku:

```javascript
function renderBranchAccuracy(sport, data) {
    const el = document.querySelector(`.branch-accuracy[data-sport="${sport}"]`);
    if (!el || !data.sports[sport]) return;
    const acc = data.sports[sport].accuracy;
    const pct = (acc * 100).toFixed(1);
    el.textContent = `${pct}% isabet (${data.sports[sport].n_trades} maç)`;
    if (acc < 0.55) {
        el.classList.add('alarm');
        document.querySelector(`.branch[data-sport="${sport}"]`).classList.add('alarm');
    }
}
```

CSS: `.branch.alarm` kırmızı arka plan, `.branch-accuracy.alarm` kırmızı yazı.

- [ ] **Step 4.5: Telegram alarm hook**

`telegram_notifier.py` (mevcutsa) içine `alert_model_degraded(sport, accuracy)` ekle:

```python
def alert_model_degraded(sport: str, accuracy: float) -> None:
    msg = f"⚠️ Model sağlık uyarısı\n{sport.upper()} son 50 maç isabet: {accuracy:.1%}\nKalibrasyon eğrisi update gerekebilir."
    _send_message(msg)
```

`computed.py`'dan accuracy %55 altına düşerse çağrılır (rate limit: günde 1 kez aynı spor için).

- [ ] **Step 4.6: Commit**

```bash
git add scripts/calibration_health_report.py \
        src/presentation/dashboard/computed.py \
        src/presentation/dashboard/static/js/dashboard.js \
        src/presentation/dashboard/templates/dashboard.html
git commit -m "feat(dashboard): branches isabet alt-satırı + bozulma alarmı — Plan 1.D Task 4"
```

---

### Task 5: Calibration Refresh Hook (Haftalık Otomatik Update)

**Files:**
- Create: `src/orchestration/calibration_refresher.py`
- Modify: `src/orchestration/factory.py`
- Test: `tests/unit/orchestration/test_calibration_refresher.py`

- [ ] **Step 5.1: Test**

```python
"""Calibration refresher — haftalık stale check + fit."""
from pathlib import Path
import pytest
from src.orchestration.calibration_refresher import (
    is_calibration_stale, REFRESH_INTERVAL_DAYS,
)


def test_missing_file_is_stale(tmp_path: Path):
    assert is_calibration_stale(tmp_path / "missing.json") is True


def test_recent_file_not_stale(tmp_path: Path):
    p = tmp_path / "cal.json"
    p.write_text("{}", encoding="utf-8")
    assert is_calibration_stale(p) is False


def test_old_file_is_stale(tmp_path: Path):
    import time
    p = tmp_path / "cal.json"
    p.write_text("{}", encoding="utf-8")
    old_ts = time.time() - (REFRESH_INTERVAL_DAYS + 1) * 86400
    import os
    os.utime(p, (old_ts, old_ts))
    assert is_calibration_stale(p) is True
```

- [ ] **Step 5.2: Implementation**

```python
# src/orchestration/calibration_refresher.py
"""Haftalık kalibrasyon eğrisi update orchestrator.

Sackmann refresh paralel: bot başlangıçta stale check → stale ise
fit_calibration çağır → calibration_store'a yaz.

Stale: dosya son 7 günden eski. Kayıt: data/calibration_curves.json.
ARCH_GUARD §12 — try/except sadece infra, log + degrade.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

REFRESH_INTERVAL_DAYS = 7

logger = logging.getLogger(__name__)


def is_calibration_stale(path: Path) -> bool:
    if not path.exists():
        return True
    age_days = (time.time() - path.stat().st_mtime) / 86400.0
    return age_days > REFRESH_INTERVAL_DAYS


def refresh_calibration_if_stale(
    path: Path,
    trades_path: Path,
) -> bool:
    """Stale ise calibration fit + save. Returns True if refresh ran."""
    if not is_calibration_stale(path):
        logger.info("calibration fresh — skip refresh")
        return False
    if not trades_path.exists():
        logger.warning("calibration refresh: trade history not found")
        return False
    logger.info("calibration stale — fitting new curves from trade history")
    # Implementation: load trade history, group by sport+market_type,
    # fit_calibration per group, save via calibration_store.
    # (detay tek fonksiyon, ~30 satır — implementation aşamasında yazılır)
    return True
```

- [ ] **Step 5.3: factory.py hook**

`_maybe_invoke_sackmann_refresh` ve `_maybe_invoke_basketball_refresh`'in yanına:

```python
def _maybe_invoke_calibration_refresh(cfg: AppConfig) -> None:
    """Haftalık kalibrasyon update (Plan 1.D Task 5)."""
    from src.orchestration.calibration_refresher import refresh_calibration_if_stale
    refresh_calibration_if_stale(
        path=Path("data/calibration_curves.json"),
        trades_path=Path("logs/audit/trade_history.jsonl"),
    )
```

`build_agent`'da çağır:

```python
_maybe_invoke_calibration_refresh(cfg)
```

- [ ] **Step 5.4: Commit**

```bash
git add src/orchestration/calibration_refresher.py src/orchestration/factory.py tests/unit/orchestration/test_calibration_refresher.py
git commit -m "feat(orchestration): haftalık calibration refresh hook — Plan 1.D Task 5"
```

---

### Task 6: Full Regresyon + Backtest Tekrar

- [ ] **Step 6.1: Tüm testleri çalıştır**

Run: `python -m pytest tests/unit -q`
Expected: 1580+ PASS.

- [ ] **Step 6.2: Backtest tekrar (Plan 1.D düzeltmeleri etkisi)**

Run: `PYTHONPATH=. python scripts/basketball_backtest_2024.py`

Beklenen:
- %65.8 → kalibrasyon + outlier guard + sezon reset SONRASI **%67-68**
- Brier: 0.21 → ~0.20 (daha düşük = daha iyi)

- [ ] **Step 6.3: Commit (rapor)**

```bash
git commit --allow-empty -m "report(basketball): Plan 1.D sonrası backtest — accuracy %X.X (önceki %65.8 → %X.X)"
```

---

## Self-Review

**Pro standardı kapsama:**
- Outlier guard (KenPom/538/EPM standardı) → Task 1 ✓
- Sezon reset (538 official) → Task 2 ✓
- Spor-bağımsız calibration + auto refresh (FiveThirtyEight haftalık) → Task 3 + 5 ✓
- Model health monitor (endüstri standardı) → Task 4 ✓
- Cliprange safety net (FiveThirtyEight + Pinnacle) → Task 3 ✓

**Spor-bağımsızlık:**
- `src/domain/calibration/` — generic
- Tenis backward-compat shim (mevcut import noktaları çalışır)
- Basket entegrasyonu yeni

**Dashboard kart kararı:**
- Peak Balance KALIR (kullanıcı geri bildirimi)
- Branches kartına alt-satır + alarm renk

**YAGNI:**
- Dinamik K-factor YOK (kalibrasyon zaten halleder)
- Confidence kademe YOK (kalibrasyon yapar)
- Ayrı health kart YOK (Branches yeterli)

---

## Execution Handoff

Subagent-Driven veya inline execution. Plan 1.D Task 1-2 paralel mümkün, Task 3 sıralı (calibration refactor temel), Task 4-5 paralel.
