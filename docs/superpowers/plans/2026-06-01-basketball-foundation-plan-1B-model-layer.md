# Basketball Foundation — Plan 1.B: Model Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** NBA + WNBA için takım Elo rating + Pace × AdjO/AdjD efficiency hesabı + harman pricer kur. Domain katmanı saf math — I/O yok. Tenis Glicko + Markov pattern'inin basket muadili.

**Architecture:** `src/domain/pricing/basketball/` altında saf hesap modülleri. Veri parametre olarak dışarıdan verilir (Plan 1.A `GameRecord` + `TeamSnapshot` modelleri kullanılır). Match pricer market_type dispatcher'la moneyline / totals / spread için P(YES) üretir. Lig-spesifik parametreler `config.yaml` üzerinden okunur (magic number yasağı).

**Tech Stack:** Python 3.12+, stdlib (math, statistics), Pydantic v2 (sadece tip referansı için — Plan 1.A schemas'tan import).

---

## File Structure

### Yeni dosyalar

| Dosya | Sorumluluk | Tahmini satır |
|---|---|---|
| `src/domain/pricing/basketball/__init__.py` | Paket başlatıcı | 5 |
| `src/domain/pricing/basketball/team_elo.py` | Klasik Elo + home advantage + K-factor logic | ~120 |
| `src/domain/pricing/basketball/pace_efficiency.py` | Pace × AdjO/AdjD formülü → proj_total, proj_margin | ~130 |
| `src/domain/pricing/basketball/efficiency_metrics.py` | GameRecord listesi → her takım için AdjO/AdjD/Pace toplama | ~140 |
| `src/domain/pricing/basketball/match_pricer.py` | Market type dispatch → blend(elo, pace_eff) → P(YES) | ~150 |
| `src/domain/matching/basketball_team_resolver.py` | Polymarket slug → NBA team abbreviation | ~100 |

### Yeni test dosyaları

| Dosya | Test edilen |
|---|---|
| `tests/unit/domain/pricing/basketball/__init__.py` | (boş) |
| `tests/unit/domain/pricing/basketball/test_team_elo.py` | Elo update + home advantage + P(home wins) |
| `tests/unit/domain/pricing/basketball/test_pace_efficiency.py` | Projeksiyon formülü (KenPom örneği) |
| `tests/unit/domain/pricing/basketball/test_efficiency_metrics.py` | Toplama / normalize / SoS |
| `tests/unit/domain/pricing/basketball/test_match_pricer.py` | Moneyline/totals/spread market_type dispatch |
| `tests/unit/domain/matching/test_basketball_team_resolver.py` | Slug parsing + fuzzy match |

### Modifiye edilecek dosyalar

| Dosya | Değişiklik |
|---|---|
| `config.yaml` | `basketball.nba`, `basketball.wnba` lig-spesifik tuning değerleri |
| `src/config/settings.py` | `BasketballLeagueParams` + `BasketballConfig.leagues` dict |
| `src/orchestration/factory.py` | `_maybe_invoke_basketball_refresh` primary fetch'i gerçek nba_api endpoint'e bağla + rating update |

---

## Tasks

### Task 1: Klasör iskeleti

**Files:** Create `src/domain/pricing/basketball/__init__.py`, `tests/unit/domain/pricing/basketball/__init__.py`.

- [ ] **Step 1.1:** Klasörleri oluştur, boş `__init__.py` ekle:

```python
# src/domain/pricing/basketball/__init__.py
"""Basketball domain pricing — saf math, I/O yok.

Tenis Glicko + Markov pattern'inin basket muadili:
  team_elo.py        ← glicko.py
  pace_efficiency.py ← markov.py
  match_pricer.py    ← match_pricer.py (tennis)
"""
```

- [ ] **Step 1.2:** Commit:

```bash
git add src/domain/pricing/basketball/__init__.py tests/unit/domain/pricing/basketball/__init__.py
git commit -m "chore(basketball/domain): klasör iskeleti (Plan 1.B Task 1)"
```

---

### Task 2: `team_elo.py` — Klasik Elo + Home Advantage

**Files:**
- Create: `src/domain/pricing/basketball/team_elo.py`
- Test: `tests/unit/domain/pricing/basketball/test_team_elo.py`

- [ ] **Step 2.1: Test yaz**

```python
# tests/unit/domain/pricing/basketball/test_team_elo.py
"""Team Elo — update, home advantage, win probability."""
from __future__ import annotations
import pytest
from src.domain.pricing.basketball.team_elo import (
    EloRating, expected_win_prob, update_elo, DEFAULT_RATING,
)


def test_default_rating_equals_1500():
    r = EloRating()
    assert r.rating == DEFAULT_RATING
    assert r.games == 0


def test_expected_win_prob_equal_ratings_returns_half():
    home = EloRating(rating=1500.0)
    away = EloRating(rating=1500.0)
    p = expected_win_prob(home, away, home_advantage=0.0)
    assert abs(p - 0.5) < 1e-6


def test_expected_win_prob_home_advantage_boosts_home():
    home = EloRating(rating=1500.0)
    away = EloRating(rating=1500.0)
    p = expected_win_prob(home, away, home_advantage=100.0)
    assert p > 0.5  # home ev avantajı → daha yüksek


def test_expected_win_prob_higher_rating_wins_more():
    strong = EloRating(rating=1600.0)
    weak = EloRating(rating=1400.0)
    p = expected_win_prob(strong, weak, home_advantage=0.0)
    assert p > 0.7  # 200 puan fark → güçlü %75+ favori


def test_update_elo_winner_gains_loser_loses():
    home = EloRating(rating=1500.0, games=10)
    away = EloRating(rating=1500.0, games=10)
    new_home, new_away = update_elo(
        home, away, home_won=True, k_factor=20.0, home_advantage=0.0,
    )
    assert new_home.rating > home.rating
    assert new_away.rating < away.rating
    # Sum-zero check (klasik Elo)
    assert abs((new_home.rating + new_away.rating) - (home.rating + away.rating)) < 1e-6
    assert new_home.games == 11
    assert new_away.games == 11


def test_update_elo_upset_larger_swing():
    """Underdog'un kazanması → büyük rating hareketi."""
    strong = EloRating(rating=1700.0, games=20)
    weak = EloRating(rating=1300.0, games=20)
    # Beklenti: strong %91 favori. Eğer weak kazanırsa → büyük swing.
    new_strong, new_weak = update_elo(
        strong, weak, home_won=False, k_factor=20.0, home_advantage=0.0,
    )
    swing = new_weak.rating - weak.rating
    assert swing > 15  # Klasik Elo: K * (1 - expected) ≈ 20 * 0.91 = 18.2
```

- [ ] **Step 2.2: Test FAIL doğrula**

Run: `python -m pytest tests/unit/domain/pricing/basketball/test_team_elo.py -v`
Expected: ImportError

- [ ] **Step 2.3: Implementasyon**

```python
# src/domain/pricing/basketball/team_elo.py
"""Klasik Elo rating system — takım gücü, home advantage dahil.

Domain layer — saf math, hiçbir I/O yok. FiveThirtyEight pattern'i:
  E_home = 1 / (1 + 10^((R_away - R_home - H) / 400))
  R'_home = R_home + K * (S_home - E_home)

S_home ∈ {0, 1} (loss/win). K-factor lig-başına config'den verilir
(genellikle 20). H = home advantage (NBA ~100, WNBA ~95, NCAAB ~130).
"""
from __future__ import annotations

from dataclasses import dataclass, replace

DEFAULT_RATING = 1500.0
_ELO_DIVISOR = 400.0


@dataclass(frozen=True)
class EloRating:
    rating: float = DEFAULT_RATING
    games: int = 0


def expected_win_prob(
    home: EloRating, away: EloRating, home_advantage: float,
) -> float:
    """P(home wins) — klasik Elo logistic, home_advantage rating puanı olarak eklenir."""
    diff = away.rating - home.rating - home_advantage
    return 1.0 / (1.0 + 10.0 ** (diff / _ELO_DIVISOR))


def update_elo(
    home: EloRating, away: EloRating,
    home_won: bool, k_factor: float, home_advantage: float,
) -> tuple[EloRating, EloRating]:
    """Maç sonucundan yeni Elo'lar üret. Sum-zero (toplam puan korunur)."""
    e_home = expected_win_prob(home, away, home_advantage)
    s_home = 1.0 if home_won else 0.0
    delta = k_factor * (s_home - e_home)
    new_home = replace(home, rating=home.rating + delta, games=home.games + 1)
    new_away = replace(away, rating=away.rating - delta, games=away.games + 1)
    return new_home, new_away
```

- [ ] **Step 2.4: Test PASS**

Run: `python -m pytest tests/unit/domain/pricing/basketball/test_team_elo.py -v`
Expected: 6 passed

- [ ] **Step 2.5: Commit**

```bash
git add src/domain/pricing/basketball/team_elo.py tests/unit/domain/pricing/basketball/test_team_elo.py
git commit -m "feat(basketball/domain): team Elo + home advantage (Plan 1.B Task 2)"
```

---

### Task 3: `pace_efficiency.py` — KenPom Formülü

**Files:**
- Create: `src/domain/pricing/basketball/pace_efficiency.py`
- Test: `tests/unit/domain/pricing/basketball/test_pace_efficiency.py`

- [ ] **Step 3.1: Test**

```python
# tests/unit/domain/pricing/basketball/test_pace_efficiency.py
"""Pace × efficiency projeksiyon formülü."""
from __future__ import annotations
import pytest
from src.domain.pricing.basketball.pace_efficiency import (
    TeamEfficiency, project_game,
)


def test_project_game_average_teams_yields_league_average_total():
    """İki ortalama takım (AdjO=AdjD=110, Pace=100) → toplam ≈ 220 (NBA average)."""
    avg = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    proj = project_game(avg, avg)
    assert abs(proj.total - 220.0) < 0.5
    assert abs(proj.margin) < 0.5  # eşit takımlar → 0 margin


def test_project_game_offense_strong_home_outscores():
    home = TeamEfficiency(adj_o=120.0, adj_d=110.0, adj_pace=100.0)
    away = TeamEfficiency(adj_o=100.0, adj_d=110.0, adj_pace=100.0)
    proj = project_game(home, away)
    assert proj.home_score > proj.away_score
    assert proj.margin > 5.0  # home offense 10 puan üstün


def test_project_game_high_pace_inflates_total():
    """Pace 100 → 110 (%10 daha hızlı) → toplam +%10."""
    slow = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    fast = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=110.0)
    proj_slow = project_game(slow, slow)
    proj_fast = project_game(fast, fast)
    assert proj_fast.total > proj_slow.total
    # Yaklaşık %10 fark beklenir (yumuşak eşik)
    assert (proj_fast.total - proj_slow.total) / proj_slow.total > 0.08


def test_project_game_defense_strong_lowers_opponent_score():
    weak_def = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    strong_def = TeamEfficiency(adj_o=110.0, adj_d=100.0, adj_pace=100.0)
    proj_weak = project_game(weak_def, weak_def)
    proj_strong = project_game(strong_def, weak_def)
    # strong_def evde → weak_def deplasmanda → strong_def düşman skoru düşürür
    assert proj_strong.away_score < proj_weak.away_score
```

- [ ] **Step 3.2: FAIL**

- [ ] **Step 3.3: Implementasyon**

```python
# src/domain/pricing/basketball/pace_efficiency.py
"""Pace × Efficiency projeksiyon — KenPom formülü.

  proj_pace  = (pace_A + pace_B) / 2
  proj_score_A = proj_pace × (AdjO_A + AdjD_B) / 200
  proj_score_B = proj_pace × (AdjO_B + AdjD_A) / 200
  proj_total   = proj_score_A + proj_score_B
  proj_margin  = proj_score_A - proj_score_B (home perspective)

AdjO/AdjD/Pace değerleri Plan 1.B Task 4'te `efficiency_metrics`
modülünde tarihsel maç verisinden hesaplanır. Burada sadece projeksiyon.
"""
from __future__ import annotations

from dataclasses import dataclass


_EFFICIENCY_NORMALIZER = 200.0  # Possession başına = AdjO/100 + AdjD/100 = (AdjO+AdjD)/200


@dataclass(frozen=True)
class TeamEfficiency:
    """Bir takımın güncel AdjO / AdjD / Pace değerleri (KenPom-tarzı)."""
    adj_o: float   # offensive efficiency (puan / 100 poss)
    adj_d: float   # defensive efficiency (allowed puan / 100 poss)
    adj_pace: float  # possessions / 40 min


@dataclass(frozen=True)
class GameProjection:
    home_score: float
    away_score: float
    total: float
    margin: float  # home - away
    proj_pace: float


def project_game(home: TeamEfficiency, away: TeamEfficiency) -> GameProjection:
    """KenPom formülüyle beklenen skor + total + margin."""
    proj_pace = (home.adj_pace + away.adj_pace) / 2.0
    score_home = proj_pace * (home.adj_o + away.adj_d) / _EFFICIENCY_NORMALIZER
    score_away = proj_pace * (away.adj_o + home.adj_d) / _EFFICIENCY_NORMALIZER
    return GameProjection(
        home_score=score_home,
        away_score=score_away,
        total=score_home + score_away,
        margin=score_home - score_away,
        proj_pace=proj_pace,
    )
```

- [ ] **Step 3.4: PASS**

- [ ] **Step 3.5: Commit**

```bash
git add src/domain/pricing/basketball/pace_efficiency.py tests/unit/domain/pricing/basketball/test_pace_efficiency.py
git commit -m "feat(basketball/domain): pace × efficiency projeksiyon (KenPom formülü) (Plan 1.B Task 3)"
```

---

### Task 4: `efficiency_metrics.py` — GameRecord listesi → AdjO/AdjD/Pace

**Files:**
- Create: `src/domain/pricing/basketball/efficiency_metrics.py`
- Test: `tests/unit/domain/pricing/basketball/test_efficiency_metrics.py`

- [ ] **Step 4.1: Test**

```python
# tests/unit/domain/pricing/basketball/test_efficiency_metrics.py
"""Efficiency metrics — GameRecord listesi → her takımın AdjO/AdjD/Pace."""
from __future__ import annotations
import pytest
from src.infrastructure.data.basketball.schemas import GameRecord
from src.domain.pricing.basketball.efficiency_metrics import (
    compute_team_efficiency, _raw_efficiency_per_game,
)
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency


def _game(home: str, away: str, hs: int, as_: int, hp: float, ap: float) -> GameRecord:
    return GameRecord(
        game_id=f"{home}-{away}", season="2024-25",
        game_date_utc="2024-11-01T00:00:00Z",
        home_team=home, away_team=away,
        home_score=hs, away_score=as_,
        home_possessions=hp, away_possessions=ap,
        is_final=True, league="nba",
    )


def test_raw_efficiency_per_game_correct():
    g = _game("LAL", "GSW", 110, 100, 100.0, 100.0)
    lal_o, lal_d, lal_pace = _raw_efficiency_per_game(g, team="LAL")
    assert lal_o == 110.0  # 110 / 100 * 100
    assert lal_d == 100.0  # 100 / 100 * 100 (opp scored)
    assert lal_pace == 100.0


def test_compute_team_efficiency_averages_multiple_games():
    games = [
        _game("LAL", "GSW", 110, 100, 100.0, 100.0),
        _game("LAL", "PHX", 120, 90, 100.0, 100.0),
    ]
    eff = compute_team_efficiency(games, team="LAL")
    assert isinstance(eff, TeamEfficiency)
    # AdjO: (110 + 120) / 2 = 115
    assert abs(eff.adj_o - 115.0) < 0.01
    # AdjD: (100 + 90) / 2 = 95
    assert abs(eff.adj_d - 95.0) < 0.01
    # Pace: 100
    assert abs(eff.adj_pace - 100.0) < 0.01


def test_compute_team_efficiency_team_not_in_games_returns_none():
    games = [_game("LAL", "GSW", 110, 100, 100.0, 100.0)]
    assert compute_team_efficiency(games, team="BOS") is None


def test_compute_team_efficiency_empty_games_returns_none():
    assert compute_team_efficiency([], team="LAL") is None
```

- [ ] **Step 4.2: FAIL**

- [ ] **Step 4.3: Implementasyon**

```python
# src/domain/pricing/basketball/efficiency_metrics.py
"""Takım AdjO/AdjD/Pace hesabı — GameRecord listesinden.

Saf domain — I/O yok. Tarihsel maç verisini alır, takım başına
ortalama offensive / defensive / pace değerleri üretir.

Plan 1.B Faz 1 basit ortalama (NBA için ~%85 doğruluk veriyor).
Strength-of-schedule (SoS) adjustment Faz 2'de planlanır (KenPom
gerçek "Adj"ı SoS ile düzeltir, biz şimdilik raw).
"""
from __future__ import annotations

from typing import Iterable, Optional

from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.infrastructure.data.basketball.schemas import GameRecord


_POSS_PER_100 = 100.0


def _raw_efficiency_per_game(g: GameRecord, team: str) -> tuple[float, float, float]:
    """Bir maç → (offensive_eff_per_100, defensive_eff_per_100, pace_per_40)."""
    if g.home_team == team:
        my_score, opp_score = g.home_score, g.away_score
        my_poss, opp_poss = g.home_possessions, g.away_possessions
    elif g.away_team == team:
        my_score, opp_score = g.away_score, g.home_score
        my_poss, opp_poss = g.away_possessions, g.home_possessions
    else:
        raise ValueError(f"team {team} not in game {g.game_id}")
    off_eff = my_score / my_poss * _POSS_PER_100
    def_eff = opp_score / opp_poss * _POSS_PER_100
    # Pace: ortalama possessions (her iki takım için aynı varsayılır basket'te)
    pace = (my_poss + opp_poss) / 2.0
    return off_eff, def_eff, pace


def compute_team_efficiency(
    games: Iterable[GameRecord], team: str,
) -> Optional[TeamEfficiency]:
    """Tüm maçlardan team'in average AdjO/AdjD/Pace değerini çıkar.

    Takımın hiç maçı yoksa None döner (Plan 1.A Task 5 cache henüz boş
    olabilir — bot başlangıçta tarihsel veriyi çeker, ratings üretir).
    """
    off_vals: list[float] = []
    def_vals: list[float] = []
    pace_vals: list[float] = []
    for g in games:
        if team not in (g.home_team, g.away_team):
            continue
        off, dfn, pace = _raw_efficiency_per_game(g, team)
        off_vals.append(off)
        def_vals.append(dfn)
        pace_vals.append(pace)
    if not off_vals:
        return None
    return TeamEfficiency(
        adj_o=sum(off_vals) / len(off_vals),
        adj_d=sum(def_vals) / len(def_vals),
        adj_pace=sum(pace_vals) / len(pace_vals),
    )
```

- [ ] **Step 4.4: PASS**

- [ ] **Step 4.5: Commit**

```bash
git add src/domain/pricing/basketball/efficiency_metrics.py tests/unit/domain/pricing/basketball/test_efficiency_metrics.py
git commit -m "feat(basketball/domain): efficiency metrics — GameRecord → AdjO/AdjD/Pace (Plan 1.B Task 4)"
```

---

### Task 5: `match_pricer.py` — Market Type Dispatch + Blend

**Files:**
- Create: `src/domain/pricing/basketball/match_pricer.py`
- Test: `tests/unit/domain/pricing/basketball/test_match_pricer.py`

- [ ] **Step 5.1: Test**

```python
# tests/unit/domain/pricing/basketball/test_match_pricer.py
"""Match pricer — market_type dispatch → P(YES)."""
from __future__ import annotations
import pytest
from src.domain.pricing.basketball.team_elo import EloRating
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.match_pricer import compute_market_anchor


def test_moneyline_returns_elo_blended_probability():
    home_elo = EloRating(rating=1600.0)
    away_elo = EloRating(rating=1400.0)
    home_eff = TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0)
    away_eff = TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0)
    p = compute_market_anchor(
        market_type="moneyline",
        home_elo=home_elo, away_elo=away_elo,
        home_eff=home_eff, away_eff=away_eff,
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert p is not None
    assert p > 0.7  # güçlü ev sahibi


def test_totals_over_returns_probability_above_half_when_pace_high():
    home_elo = EloRating(rating=1500.0)
    away_elo = EloRating(rating=1500.0)
    fast = TeamEfficiency(adj_o=115.0, adj_d=110.0, adj_pace=105.0)
    p_over = compute_market_anchor(
        market_type="totals",
        home_elo=home_elo, away_elo=away_elo,
        home_eff=fast, away_eff=fast,
        home_advantage=0.0, blend_elo=0.55, line=215.0,
    )
    assert p_over is not None
    # proj_total ≈ 105 * 225 / 200 * 2 ≈ 236 > 215 → P(over) > 0.5
    assert p_over > 0.5


def test_unknown_market_type_returns_none():
    home_elo = EloRating()
    away_elo = EloRating()
    eff = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    p = compute_market_anchor(
        market_type="player_props",
        home_elo=home_elo, away_elo=away_elo,
        home_eff=eff, away_eff=eff,
        home_advantage=0.0, blend_elo=0.55, line=None,
    )
    assert p is None


def test_spreads_home_favorite_covers_likely_when_margin_exceeds_line():
    home_elo = EloRating(rating=1600.0)
    away_elo = EloRating(rating=1400.0)
    strong = TeamEfficiency(adj_o=120.0, adj_d=105.0, adj_pace=100.0)
    weak = TeamEfficiency(adj_o=105.0, adj_d=120.0, adj_pace=100.0)
    # spread line = -3.5 (home favored by 3.5) — beklenen margin ~15 > 3.5
    p = compute_market_anchor(
        market_type="spreads",
        home_elo=home_elo, away_elo=away_elo,
        home_eff=strong, away_eff=weak,
        home_advantage=0.0, blend_elo=0.55, line=-3.5,
    )
    assert p is not None
    assert p > 0.6  # home covers
```

- [ ] **Step 5.2: FAIL**

- [ ] **Step 5.3: Implementasyon**

```python
# src/domain/pricing/basketball/match_pricer.py
"""Market type dispatch → P(YES) anchor.

Per-market pricer'lar:
  moneyline → blend(Elo, P(score_diff>0))
  totals    → P(proj_total > line)  (normal approx, std dev sezon kalibrasyonu)
  spreads   → P(margin > line)

Lig-spesifik parametreler config'den gelir (home_advantage, blend_elo).
Saf domain — I/O yok.
"""
from __future__ import annotations

import math
from typing import Optional

from src.domain.pricing.basketball.pace_efficiency import (
    GameProjection, TeamEfficiency, project_game,
)
from src.domain.pricing.basketball.team_elo import (
    EloRating, expected_win_prob,
)


# NBA empirik margin std dev (regular season, FiveThirtyEight): ~11
# WNBA: ~9.5. Plan 1.C kalibrasyonunda lig-başına revize.
_MARGIN_STD_DEFAULT = 11.0
# NBA total std dev: ~20 (totals dağılımı margin'den daha geniş)
_TOTAL_STD_DEFAULT = 20.0


def _phi(z: float) -> float:
    """Standard normal CDF Φ(z) — math.erf üzerinden."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _moneyline_from_pace(proj: GameProjection) -> float:
    """Beklenen margin'in 0'dan büyük olma olasılığı (normal varsayım)."""
    return _phi(proj.margin / _MARGIN_STD_DEFAULT)


def compute_market_anchor(
    market_type: str,
    home_elo: EloRating, away_elo: EloRating,
    home_eff: TeamEfficiency, away_eff: TeamEfficiency,
    home_advantage: float, blend_elo: float,
    line: Optional[float],
) -> Optional[float]:
    """Market type'a göre P(YES) anchor üret.

    line: totals için over/under sayısı, spreads için home spread (negatif = home favored).
    moneyline için None.
    Bilinmeyen market_type veya gerekli parametre None → None.
    """
    mt = market_type.lower()
    proj = project_game(home_eff, away_eff)
    if mt == "moneyline":
        p_elo = expected_win_prob(home_elo, away_elo, home_advantage)
        p_pace = _moneyline_from_pace(proj)
        return blend_elo * p_elo + (1.0 - blend_elo) * p_pace
    if mt == "totals":
        if line is None:
            return None
        z = (proj.total - line) / _TOTAL_STD_DEFAULT
        return _phi(z)
    if mt == "spreads":
        if line is None:
            return None
        # Home spread negatif = home favored. Cover için margin > -line gerekir.
        # Örnek: line=-3.5 → home_cover ⇔ margin > 3.5.
        threshold = -line
        z = (proj.margin - threshold) / _MARGIN_STD_DEFAULT
        return _phi(z)
    return None
```

- [ ] **Step 5.4: PASS**

- [ ] **Step 5.5: Commit**

```bash
git add src/domain/pricing/basketball/match_pricer.py tests/unit/domain/pricing/basketball/test_match_pricer.py
git commit -m "feat(basketball/domain): match pricer — moneyline/totals/spreads (Plan 1.B Task 5)"
```

---

### Task 6: `basketball_team_resolver.py` — Slug → Team Abbreviation

**Files:**
- Create: `src/domain/matching/basketball_team_resolver.py`
- Test: `tests/unit/domain/matching/test_basketball_team_resolver.py`

- [ ] **Step 6.1: Test**

```python
# tests/unit/domain/matching/test_basketball_team_resolver.py
"""Basketball team resolver — Polymarket slug ↔ NBA team abbreviation."""
from __future__ import annotations
import pytest
from src.domain.matching.basketball_team_resolver import (
    resolve_team_pair, ResolveResult,
)


def test_resolve_nba_standard_slug():
    res = resolve_team_pair("nba-lal-gsw-2024-11-01", league="nba")
    assert res.home == "LAL"
    assert res.away == "GSW"
    assert res.ok is True


def test_resolve_handles_full_team_names():
    """Bazı Polymarket slug'larda "lakers-warriors" pattern var."""
    res = resolve_team_pair("nba-lakers-vs-warriors-2024-11-01", league="nba")
    assert res.home == "LAL"
    assert res.away == "GSW"


def test_resolve_wnba_abbreviation():
    res = resolve_team_pair("wnba-lva-nyl-2024-08-15", league="wnba")
    assert res.home == "LVA"
    assert res.away == "NYL"


def test_resolve_unknown_team_returns_not_ok():
    res = resolve_team_pair("nba-xxx-yyy-2024-11-01", league="nba")
    assert res.ok is False
    assert res.fail_reason is not None
```

- [ ] **Step 6.2: FAIL**

- [ ] **Step 6.3: Implementasyon**

```python
# src/domain/matching/basketball_team_resolver.py
"""Polymarket slug ↔ NBA/WNBA team abbreviation eşlemesi.

Tennis player resolver paraleli (src/domain/matching/tennis_player_resolver.py).
Saf domain — I/O yok, sabit lookup tabloları.

Polymarket slug pattern'leri:
  - "nba-lal-gsw-2024-11-01" (3-harf abbreviation)
  - "nba-lakers-vs-warriors-2024-11-01" (full team adı)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# NBA team abbreviations + alternate full-name kelimeleri.
_NBA_TEAMS: dict[str, str] = {
    "lal": "LAL", "lakers": "LAL",
    "gsw": "GSW", "warriors": "GSW",
    "bos": "BOS", "celtics": "BOS",
    "lac": "LAC", "clippers": "LAC",
    "phx": "PHX", "suns": "PHX", "phoenix": "PHX",
    "den": "DEN", "nuggets": "DEN",
    "mia": "MIA", "heat": "MIA",
    "nyk": "NYK", "knicks": "NYK",
    "bkn": "BKN", "nets": "BKN", "brooklyn": "BKN",
    "phi": "PHI", "76ers": "PHI", "sixers": "PHI",
    "mil": "MIL", "bucks": "MIL",
    "tor": "TOR", "raptors": "TOR",
    "chi": "CHI", "bulls": "CHI",
    "cle": "CLE", "cavaliers": "CLE", "cavs": "CLE",
    "det": "DET", "pistons": "DET",
    "ind": "IND", "pacers": "IND",
    "atl": "ATL", "hawks": "ATL",
    "cha": "CHA", "hornets": "CHA",
    "orl": "ORL", "magic": "ORL",
    "was": "WAS", "wizards": "WAS",
    "sas": "SAS", "spurs": "SAS",
    "hou": "HOU", "rockets": "HOU",
    "mem": "MEM", "grizzlies": "MEM",
    "nop": "NOP", "pelicans": "NOP",
    "dal": "DAL", "mavericks": "DAL", "mavs": "DAL",
    "okc": "OKC", "thunder": "OKC",
    "min": "MIN", "timberwolves": "MIN", "wolves": "MIN",
    "por": "POR", "blazers": "POR", "trail": "POR",
    "sac": "SAC", "kings": "SAC",
    "uta": "UTA", "jazz": "UTA",
}

# WNBA 12 takım.
_WNBA_TEAMS: dict[str, str] = {
    "atl": "ATL", "dream": "ATL",
    "chi": "CHI", "sky": "CHI",
    "con": "CON", "sun": "CON", "connecticut": "CON",
    "dal": "DAL", "wings": "DAL",
    "ind": "IND", "fever": "IND",
    "las": "LAS", "sparks": "LAS",
    "lva": "LVA", "aces": "LVA", "vegas": "LVA",
    "min": "MIN", "lynx": "MIN",
    "nyl": "NYL", "liberty": "NYL",
    "phx": "PHX", "mercury": "PHX",
    "sea": "SEA", "storm": "SEA",
    "was": "WAS", "mystics": "WAS",
}


@dataclass(frozen=True)
class ResolveResult:
    home: Optional[str]
    away: Optional[str]
    ok: bool
    fail_reason: Optional[str] = None


def _lookup(league: str) -> dict[str, str]:
    if league == "nba":
        return _NBA_TEAMS
    if league == "wnba":
        return _WNBA_TEAMS
    return {}


def resolve_team_pair(slug: str, league: str) -> ResolveResult:
    """Polymarket slug'undan home/away abbreviation çıkar."""
    tbl = _lookup(league)
    if not tbl:
        return ResolveResult(None, None, False, f"unknown_league:{league}")
    parts = [p for p in slug.lower().split("-") if p and p not in {"vs", "v"}]
    found: list[str] = []
    for p in parts:
        if p in tbl:
            abbr = tbl[p]
            if abbr not in found:
                found.append(abbr)
        if len(found) == 2:
            break
    if len(found) < 2:
        return ResolveResult(None, None, False, f"teams_not_found:{slug}")
    return ResolveResult(home=found[0], away=found[1], ok=True)
```

- [ ] **Step 6.4: PASS**

- [ ] **Step 6.5: Commit**

```bash
git add src/domain/matching/basketball_team_resolver.py tests/unit/domain/matching/test_basketball_team_resolver.py
git commit -m "feat(basketball/matching): team resolver — slug → abbreviation (Plan 1.B Task 6)"
```

---

### Task 7: `config.yaml` Lig-Spesifik Tuning + `BasketballLeagueParams`

**Files:**
- Modify: `config.yaml`
- Modify: `src/config/settings.py`

- [ ] **Step 7.1: `config.yaml` basketball bölümü genişlet**

`config.yaml`'da mevcut `basketball:` bölümünü değiştir:

```yaml
basketball:
  enabled_leagues:
    - nba
    - wnba
  cache_dir: data/basketball_cache
  health_file: data/basketball_cache/_health/sources_status.json
  primary_source: nba_api
  secondary_source: espn
  # Lig-spesifik model parametreleri (FiveThirtyEight + KenPom referansları)
  leagues:
    nba:
      home_advantage: 100.0
      k_factor: 20.0
      blend_elo: 0.55
    wnba:
      home_advantage: 95.0
      k_factor: 22.0
      blend_elo: 0.55
```

- [ ] **Step 7.2: `settings.py` `BasketballLeagueParams` ekle**

```python
# src/config/settings.py — BasketballConfig'in yanına ekle
class BasketballLeagueParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    home_advantage: float = 100.0
    k_factor: float = 20.0
    blend_elo: float = Field(0.55, ge=0.0, le=1.0)


# BasketballConfig'i güncelle:
class BasketballConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled_leagues: List[str] = Field(default_factory=lambda: ["nba"])
    cache_dir: str = "data/basketball_cache"
    health_file: str = "data/basketball_cache/_health/sources_status.json"
    primary_source: str = "nba_api"
    secondary_source: str = "espn"
    leagues: dict[str, BasketballLeagueParams] = Field(
        default_factory=lambda: {
            "nba": BasketballLeagueParams(home_advantage=100.0, k_factor=20.0),
            "wnba": BasketballLeagueParams(home_advantage=95.0, k_factor=22.0),
        }
    )
```

- [ ] **Step 7.3: Mevcut testleri çalıştır — regresyon**

Run: `python -m pytest tests/unit -x -q`
Expected: hepsi PASS (yeni alanlar default'lu, eski testler etkilenmez)

- [ ] **Step 7.4: Commit**

```bash
git add config.yaml src/config/settings.py
git commit -m "feat(basketball/config): lig-spesifik tuning (NBA + WNBA) (Plan 1.B Task 7)"
```

---

### Task 8: Tüm Plan 1.B Testleri Toplu + Regresyon

- [ ] **Step 8.1: Domain testlerini topla**

Run:
```
python -m pytest tests/unit/domain/pricing/basketball/ tests/unit/domain/matching/test_basketball_team_resolver.py -v
```
Expected: tüm test'ler PASS.

- [ ] **Step 8.2: Tüm bot test suite — regresyon**

Run: `python -m pytest tests/unit -q`
Expected: 1536+ test PASS (yeni eklenen ~25 test + mevcut).

- [ ] **Step 8.3: Commit yoksa skip; varsa son düzeltmeleri commit et.**

---

## Self-Review

**Spec coverage (basketball-model-foundation-design.md §4 Model Bilim):**
- Team Elo → Task 2 ✓
- Pace × AdjO/AdjD formülü → Task 3 ✓
- AdjO/AdjD hesabı → Task 4 ✓
- Blend logic → Task 5 ✓
- Slug → team resolver → Task 6 ✓
- Lig-başına config tuning → Task 7 ✓

**Placeholder scan:** Yok. Her step'te exact code.

**Type consistency:**
- `EloRating` — Task 2'de tanımlı, Task 5'te kullanılıyor ✓
- `TeamEfficiency` — Task 3'te tanımlı, Task 4 + Task 5 kullanıyor ✓
- `GameRecord` — Plan 1.A schemas'tan, Task 4'te kullanılıyor ✓
- `ResolveResult` — Task 6'da tanımlı ✓

**Faz 1.C'ye taşınanlar:** Strateji entegrasyon (`basketball_anchor_enricher`), factory dispatcher genişletme, kalibrasyon, backtest.

---

## Execution Handoff

Plan complete and saved.

**Subagent-Driven execution önerilir.** Task 2-6 schemas + Plan 1.A'ya bağlı, birbirinden bağımsız → paralel dispatch mümkün. Task 7-8 entegrasyon, sıralı.
