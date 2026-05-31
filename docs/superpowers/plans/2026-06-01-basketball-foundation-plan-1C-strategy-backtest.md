# Basketball Foundation — Plan 1.C: Strategy Integration + Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development veya superpowers:executing-plans.

**Goal:** Plan 1.A (veri) + Plan 1.B (model) entegrasyonunu strateji katmanında tamamla. Basketball anchor enricher tenis pattern'ini birebir kopyalar (Odds API'siz, model → P(YES) → BookmakerProbability sarmal). factory.py dispatcher genişletilir. Son adım: backtest doğrulama (≥%66 moneyline hedefi).

**Architecture:** Strategy layer'da `basketball_anchor_enricher` + `basketball_model_anchor` + `basketball_dispatch` üçlüsü — tenis muadili. factory.py'da sport_tag → enricher seçimi. gate.py dokunulmaz (sarmal sayesinde otomatik çalışır). Backtest scripti son 1 NBA sezonu için.

**Tech Stack:** Python 3.12+, mevcut Pydantic/dataclass, pytest. Backtest için nba_api (zaten yüklü).

---

## File Structure

### Yeni dosyalar

| Dosya | Sorumluluk | Tahmini satır |
|---|---|---|
| `src/strategy/enrichment/basketball_model_anchor.py` | Market type → match_pricer dispatch (tennis_model_anchor paraleli) | ~80 |
| `src/strategy/enrichment/basketball_anchor_enricher.py` | Wrapper: model → BookmakerProbability + fail_reason (tennis_anchor_enricher paraleli) | ~100 |
| `scripts/basketball_backtest_2024.py` | NBA 2024 sezonu backtest — Brier + accuracy raporu | ~150 |

### Yeni test dosyaları

| Dosya | Test edilen |
|---|---|
| `tests/unit/strategy/enrichment/test_basketball_model_anchor.py` | Market type dispatch + None yolları |
| `tests/unit/strategy/enrichment/test_basketball_anchor_enricher.py` | Eksik takım, eksik veri, A confidence sarmalı |

### Modifiye edilecek

| Dosya | Değişiklik |
|---|---|
| `src/orchestration/factory.py` | Sport_tag dispatcher: tennis_anchor_enricher veya basketball_anchor_enricher seçimi (mevcut tennis dispatch'in yanına ekle) |
| `src/domain/analysis/enrich_outcome.py` | `EnrichFailReason` enum'una `MODEL_TEAM_NOT_IN_RATINGS` + `MODEL_BASKETBALL_DATA_MISSING` ekle |

---

## Tasks

### Task 1: `basketball_model_anchor.py`

**Files:**
- Create: `src/strategy/enrichment/basketball_model_anchor.py`
- Test: `tests/unit/strategy/enrichment/test_basketball_model_anchor.py`

- [ ] **Step 1.1: Test**

```python
# tests/unit/strategy/enrichment/test_basketball_model_anchor.py
"""Basketball model anchor — market type dispatch."""
from __future__ import annotations
from src.domain.pricing.basketball.team_elo import EloRating
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.strategy.enrichment.basketball_model_anchor import compute_model_anchor


def test_moneyline_strong_home_returns_high_probability():
    home_elo = EloRating(rating=1600.0)
    away_elo = EloRating(rating=1400.0)
    home_eff = TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0)
    away_eff = TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0)
    p = compute_model_anchor(
        market_type="moneyline",
        home_elo=home_elo, away_elo=away_elo,
        home_eff=home_eff, away_eff=away_eff,
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert p is not None and p > 0.7


def test_unknown_market_returns_none():
    eff = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    p = compute_model_anchor(
        market_type="alley_oop", home_elo=EloRating(), away_elo=EloRating(),
        home_eff=eff, away_eff=eff, home_advantage=0.0, blend_elo=0.55, line=None,
    )
    assert p is None


def test_totals_requires_line():
    eff = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    p = compute_model_anchor(
        market_type="totals", home_elo=EloRating(), away_elo=EloRating(),
        home_eff=eff, away_eff=eff, home_advantage=0.0, blend_elo=0.55, line=None,
    )
    assert p is None
```

- [ ] **Step 1.2: FAIL**

- [ ] **Step 1.3: Implementasyon**

```python
# src/strategy/enrichment/basketball_model_anchor.py
"""Basketball model anchor — Polymarket market_type → pricer dispatch.

Strategy layer. Tennis model_anchor paralel pattern (compute_model_anchor).
Eksik veride None (caller bookmaker'a düşer veya skip eder).
"""
from __future__ import annotations

from typing import Optional

from src.domain.pricing.basketball.match_pricer import compute_market_anchor
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.team_elo import EloRating


def compute_model_anchor(
    market_type: str,
    home_elo: EloRating, away_elo: EloRating,
    home_eff: TeamEfficiency, away_eff: TeamEfficiency,
    home_advantage: float, blend_elo: float,
    line: Optional[float] = None,
) -> Optional[float]:
    """P(YES) from model. Eksik veri (market_type bilinmiyor, line gerek) → None."""
    return compute_market_anchor(
        market_type=market_type,
        home_elo=home_elo, away_elo=away_elo,
        home_eff=home_eff, away_eff=away_eff,
        home_advantage=home_advantage, blend_elo=blend_elo, line=line,
    )
```

- [ ] **Step 1.4: PASS**

- [ ] **Step 1.5: Commit**

```bash
git add src/strategy/enrichment/basketball_model_anchor.py tests/unit/strategy/enrichment/test_basketball_model_anchor.py
git commit -m "feat(basketball/strategy): model anchor — market dispatch (Plan 1.C Task 1)"
```

---

### Task 2: `EnrichFailReason` Genişletme

**Files:**
- Modify: `src/domain/analysis/enrich_outcome.py`

- [ ] **Step 2.1: Mevcut enum'a iki yeni değer ekle**

Read mevcut dosya, sonra ekle:

```python
# Mevcut MODEL_PLAYER_NOT_IN_RATINGS / MODEL_DATA_MISSING benzeri:
MODEL_TEAM_NOT_IN_RATINGS = "model_team_not_in_ratings"
MODEL_BASKETBALL_DATA_MISSING = "model_basketball_data_missing"
```

- [ ] **Step 2.2: Mevcut testler çalışır mı?**

Run: `python -m pytest tests/unit/domain/analysis/ -q`
Expected: PASS.

- [ ] **Step 2.3: Commit**

```bash
git add src/domain/analysis/enrich_outcome.py
git commit -m "feat(basketball/strategy): EnrichFailReason genişletmesi (Plan 1.C Task 2)"
```

---

### Task 3: `basketball_anchor_enricher.py`

**Files:**
- Create: `src/strategy/enrichment/basketball_anchor_enricher.py`
- Test: `tests/unit/strategy/enrichment/test_basketball_anchor_enricher.py`

- [ ] **Step 3.1: Test**

```python
# tests/unit/strategy/enrichment/test_basketball_anchor_enricher.py
"""Basketball anchor enricher — model → BookmakerProbability sarmalı."""
from __future__ import annotations
from src.domain.pricing.basketball.team_elo import EloRating
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.analysis.enrich_outcome import EnrichFailReason
from src.strategy.enrichment.basketball_anchor_enricher import (
    enrich_basketball_from_model,
)


def test_enrich_complete_data_returns_a_confidence():
    ratings = {
        "LAL": EloRating(rating=1600.0, games=50),
        "GSW": EloRating(rating=1400.0, games=50),
    }
    efficiencies = {
        "LAL": TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0),
        "GSW": TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0),
    }
    res = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline",
        league="nba",
        ratings=ratings, efficiencies=efficiencies,
        home_advantage=100.0, blend_elo=0.55,
        line=None,
    )
    assert res.probability is not None
    assert res.probability.confidence == "A"
    assert res.fail_reason is None


def test_enrich_missing_team_returns_fail_reason():
    res = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings={}, efficiencies={},
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert res.probability is None
    assert res.fail_reason == EnrichFailReason.MODEL_TEAM_NOT_IN_RATINGS


def test_enrich_missing_efficiency_returns_data_missing():
    """Takımlar var ama efficiency yoksa data missing."""
    ratings = {
        "LAL": EloRating(rating=1500.0),
        "GSW": EloRating(rating=1500.0),
    }
    res = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings=ratings, efficiencies={},
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert res.probability is None
    assert res.fail_reason == EnrichFailReason.MODEL_BASKETBALL_DATA_MISSING
```

- [ ] **Step 3.2: FAIL**

- [ ] **Step 3.3: Implementasyon**

```python
# src/strategy/enrichment/basketball_anchor_enricher.py
"""Basketball market'ler için model-anchored enrichment.

Sport_tag basketball ise odds_enricher (bookmaker h2h) yerine bu modül çağrılır.
Tennis_anchor_enricher pattern'inin birebir kopyası.

Model çıktısı BookmakerProbability'ye sarılır — confidence grading mevcut
pipeline ile uyumlu kalır. Plan 1.B model layer hazır → A confidence.
"""
from __future__ import annotations

from typing import Optional

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.analysis.probability import calculate_bookmaker_probability
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.team_elo import EloRating
from src.strategy.enrichment.basketball_model_anchor import compute_model_anchor

_MODEL_EQUIV_BOOKMAKERS = 5.0
_MODEL_HAS_SHARP = True


def enrich_basketball_from_model(
    home_team: str, away_team: str,
    market_type: str, league: str,
    ratings: dict[str, EloRating],
    efficiencies: dict[str, TeamEfficiency],
    home_advantage: float, blend_elo: float,
    line: Optional[float] = None,
) -> EnrichResult:
    """Basketball market → model probability → EnrichResult.

    Eksik takım veya eksik veri → fail_reason. Plan 1.C kalibrasyon eğrisi
    sonraki faza ertelenmiş (Plan 1.B sonu kanıt sonrası).
    """
    home_elo = ratings.get(home_team)
    away_elo = ratings.get(away_team)
    if home_elo is None or away_elo is None:
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_TEAM_NOT_IN_RATINGS,
        )
    home_eff = efficiencies.get(home_team)
    away_eff = efficiencies.get(away_team)
    if home_eff is None or away_eff is None:
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_BASKETBALL_DATA_MISSING,
        )
    model_p = compute_model_anchor(
        market_type=market_type,
        home_elo=home_elo, away_elo=away_elo,
        home_eff=home_eff, away_eff=away_eff,
        home_advantage=home_advantage, blend_elo=blend_elo, line=line,
    )
    if model_p is None:
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_BASKETBALL_DATA_MISSING,
        )
    prob = calculate_bookmaker_probability(
        bookmaker_prob=model_p,
        num_bookmakers=_MODEL_EQUIV_BOOKMAKERS,
        has_sharp=_MODEL_HAS_SHARP,
        source="model",
    )
    return EnrichResult(probability=prob, fail_reason=None)
```

- [ ] **Step 3.4: PASS**

- [ ] **Step 3.5: Commit**

```bash
git add src/strategy/enrichment/basketball_anchor_enricher.py tests/unit/strategy/enrichment/test_basketball_anchor_enricher.py
git commit -m "feat(basketball/strategy): anchor enricher — tennis pattern paraleli (Plan 1.C Task 3)"
```

---

### Task 4: `factory.py` Dispatcher Genişletme

**Files:**
- Modify: `src/orchestration/factory.py`

Mevcut tennis dispatch'inin yanında basketball dispatch'i ekle. Sport_tag basketball ise basketball_anchor_enricher kullanılır.

- [ ] **Step 4.1: Test (integration)**

Bu integration testi sport_tag dispatch'ini doğrular. Konum: `tests/unit/orchestration/test_factory_basketball_dispatch.py`.

```python
"""factory.py sport_tag dispatch — basketball → basketball_anchor_enricher."""
from __future__ import annotations
import pytest


def test_basketball_tag_routes_to_model_anchor():
    """Sport_tag 'nba' → basketball_anchor_enricher kullanılır."""
    # Bu test factory'nin dispatch fonksiyonunu izole eder. Implementation
    # Task 4.3'te belirlenecek dispatcher sinyali.
    from src.orchestration.factory import _select_enricher_for_sport
    enricher_kind = _select_enricher_for_sport("nba")
    assert enricher_kind == "basketball_model"


def test_wnba_tag_routes_to_model_anchor():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("wnba") == "basketball_model"


def test_tennis_tag_still_routes_to_tennis_model():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("atp") == "tennis_model"
    assert _select_enricher_for_sport("wta") == "tennis_model"


def test_unsupported_sport_falls_back_to_bookmaker():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("nfl") == "bookmaker"
```

- [ ] **Step 4.2: FAIL**

- [ ] **Step 4.3: factory.py'a `_select_enricher_for_sport` fonksiyonu ekle**

```python
# src/orchestration/factory.py — uygun yere ekle

_TENNIS_SPORT_TAGS = frozenset({"tennis", "atp", "wta"})
_BASKETBALL_SPORT_TAGS = frozenset({"nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl"})


def _select_enricher_for_sport(sport_tag: str) -> str:
    """Sport_tag → enricher tipi. 'bookmaker' fallback (Odds API)."""
    s = sport_tag.lower()
    if s in _TENNIS_SPORT_TAGS:
        return "tennis_model"
    if s in _BASKETBALL_SPORT_TAGS:
        return "basketball_model"
    return "bookmaker"
```

- [ ] **Step 4.4: PASS**

- [ ] **Step 4.5: Commit**

```bash
git add src/orchestration/factory.py tests/unit/orchestration/test_factory_basketball_dispatch.py
git commit -m "feat(basketball/orchestration): sport_tag dispatcher (Plan 1.C Task 4)"
```

---

### Task 5: Backtest Scripti

**Files:**
- Create: `scripts/basketball_backtest_2024.py`

- [ ] **Step 5.1: Backtest scripti yaz**

```python
# scripts/basketball_backtest_2024.py
"""NBA 2024 sezonu backtest — model_p vs gerçek sonuç.

Plan 1.C son adımı. Hedef: ≥%66 moneyline doğruluk (FiveThirtyEight referans).

Akış:
  1. nba_api üzerinden 2024 regular season + playoff game-log çek
  2. Tarihsel sırayla maçları işle (data leakage yok)
  3. Her maç başında: önceki maçlardan Elo + Efficiency hesapla
  4. Model_p (moneyline) üret, gerçek sonuçla karşılaştır
  5. Brier score + accuracy raporla

Çıktı:
  - Toplam maç sayısı, doğru tahmin sayısı, accuracy
  - Brier score (düşük iyidir, 0.25 = rastgele)
  - Eşik kontrolü: ≥%66 → PASS, altı → FAIL (kalibrasyon revize)
"""
from __future__ import annotations

import sys
from collections import defaultdict
from typing import Optional

try:
    from nba_api.stats.endpoints import leaguegamelog
except ImportError:
    print("ERROR: nba_api paketi yüklü değil")
    sys.exit(2)

from src.infrastructure.data.basketball.nba_api_refresher import (
    fetch_game_log_via_nba_api,
)
from src.infrastructure.data.basketball.schemas import GameRecord
from src.domain.pricing.basketball.team_elo import EloRating, update_elo, expected_win_prob
from src.domain.pricing.basketball.efficiency_metrics import compute_team_efficiency
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.match_pricer import compute_market_anchor


HOME_ADVANTAGE = 100.0
K_FACTOR = 20.0
BLEND_ELO = 0.55
MIN_GAMES_BEFORE_PREDICT = 10   # Erken sezonda rating volatile, ilk N maçı skip


def main():
    print("[BACKTEST] Fetching NBA 2024 regular season game log...")
    games = fetch_game_log_via_nba_api(
        league="nba", season="2024",
        endpoint_factory=lambda **kwargs: leaguegamelog.LeagueGameLog(
            season=kwargs["season"], league_id=kwargs["league_id"],
            season_type_all_star="Regular Season",
        ),
    )
    if not games:
        print("[BACKTEST] FAIL: zero games fetched")
        sys.exit(1)
    print(f"[BACKTEST] Fetched {len(games)} games")
    games.sort(key=lambda g: g.game_date_utc)

    elo: dict[str, EloRating] = defaultdict(EloRating)
    history: list[GameRecord] = []
    correct = 0
    total = 0
    brier_sum = 0.0

    for g in games:
        home_elo = elo[g.home_team]
        away_elo = elo[g.away_team]
        home_eff = compute_team_efficiency(history, g.home_team)
        away_eff = compute_team_efficiency(history, g.away_team)
        eligible = (
            home_elo.games >= MIN_GAMES_BEFORE_PREDICT
            and away_elo.games >= MIN_GAMES_BEFORE_PREDICT
            and home_eff is not None and away_eff is not None
        )
        if eligible:
            p_home_win = compute_market_anchor(
                market_type="moneyline",
                home_elo=home_elo, away_elo=away_elo,
                home_eff=home_eff, away_eff=away_eff,
                home_advantage=HOME_ADVANTAGE, blend_elo=BLEND_ELO, line=None,
            )
            if p_home_win is not None:
                actual = 1.0 if g.home_score > g.away_score else 0.0
                pred = 1 if p_home_win > 0.5 else 0
                if (pred == 1 and actual == 1) or (pred == 0 and actual == 0):
                    correct += 1
                brier_sum += (p_home_win - actual) ** 2
                total += 1
        # Update ratings + history
        home_won = g.home_score > g.away_score
        new_home, new_away = update_elo(
            home_elo, away_elo, home_won=home_won,
            k_factor=K_FACTOR, home_advantage=HOME_ADVANTAGE,
        )
        elo[g.home_team] = new_home
        elo[g.away_team] = new_away
        history.append(g)

    if total == 0:
        print("[BACKTEST] FAIL: no eligible predictions")
        sys.exit(1)
    accuracy = correct / total
    brier = brier_sum / total
    print(f"[BACKTEST] Predictions: {total}/{len(games)}")
    print(f"[BACKTEST] Correct: {correct} ({accuracy:.1%})")
    print(f"[BACKTEST] Brier score: {brier:.4f} (0.25=random, lower=better)")
    threshold = 0.66
    if accuracy >= threshold:
        print(f"[BACKTEST] PASS — accuracy {accuracy:.1%} ≥ {threshold:.0%}")
    else:
        print(f"[BACKTEST] BELOW THRESHOLD — accuracy {accuracy:.1%} < {threshold:.0%}")
        print("[BACKTEST] Recommendation: kalibrasyon eğrisi ve/veya home_advantage tuning gerekli")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5.2: Çalıştır**

```
PYTHONPATH=. python scripts/basketball_backtest_2024.py
```

Beklenen sonuçlar:
- **≥%66 → PASS** → Plan 1.C done, Faz 1 yayın
- **Altı → BELOW THRESHOLD** → kalibrasyon eğrisi gerek (sonraki sprint)

- [ ] **Step 5.3: Commit (sonuca göre)**

```bash
git add scripts/basketball_backtest_2024.py
git commit -m "feat(basketball/backtest): NBA 2024 sezonu — [accuracy %X.X, Brier 0.XXXX] (Plan 1.C Task 5)"
```

---

### Task 6: Regresyon ve Plan 1.C Closure

- [ ] **Step 6.1: Tüm test'leri çalıştır**

```
python -m pytest tests/unit -q
```
Expected: 1568+ PASS.

- [ ] **Step 6.2: Plan 1.C done işaretlemek için bu plan dosyasının başına ekle:**

```markdown
> **STATUS:** ✅ DONE (2026-06-01). Backtest accuracy: %X.X. Faz 1 yayında.
```

- [ ] **Step 6.3: Commit**

```bash
git add docs/superpowers/plans/2026-06-01-basketball-foundation-plan-1C-strategy-backtest.md
git commit -m "docs(plan): Plan 1.C DONE — Faz 1 yayın kararı"
```

---

## Self-Review

**Spec coverage (basketball-model-foundation-design.md §5 Strateji Entegrasyon):**
- factory.py dispatcher → Task 4 ✓
- basketball_anchor_enricher → Task 3 ✓
- basketball_model_anchor → Task 1 ✓
- gate.py dokunulmaz → ✓ (sarmal sayesinde)
- Backtest doğrulama → Task 5 ✓

**Placeholder scan:** Yok.

**Type consistency:**
- `EloRating`, `TeamEfficiency` — Plan 1.B'den, Task 3'te kullanılıyor ✓
- `EnrichFailReason.MODEL_TEAM_NOT_IN_RATINGS` — Task 2'de eklendi, Task 3'te kullanılıyor ✓
- `EnrichResult` — mevcut domain, Task 3'te döndürülüyor ✓

---

## Execution Handoff

Subagent-Driven veya inline execution. Plan 1.C tasks daha sıralı (her biri öncekine bağlı), seri uygulamak doğru.
