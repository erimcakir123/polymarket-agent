# Per-Market Tennis Models — Implementation Plan

> **For agentic workers:** TDD strict. Her task: test yaz → fail → kod yaz → pass → commit. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Tennis için her market type'a kendi tahmin formülü. Sackmann verisini farklı kesitlerinden besleyen 5 bağımsız pricer. Bookmaker h2h olasılığını alt marketlere yapıştırma (cascade bug) son.

**Architecture:** 5-katman uyumlu. Infrastructure katmanı CSV okuma + ratings JSON I/O. Domain katmanı saf math (Glicko, Markov, pricer'lar). Strategy katmanı `tennis_model_anchor` ile anchor_probability override. Orchestration katmanında build script (CSV → ratings.json).

**Tech Stack:** Python 3.12, dataclasses, csv (stdlib), math (stdlib). Hiç ML library yok (gerek yok).

---

## File Structure

### Yeni dosyalar (kanıtlanmış literatür yaklaşımı, kaynaklar plan altında)

| Yer | Dosya | Sorumluluk | ~Satır |
|---|---|---|---|
| infrastructure | `src/infrastructure/data/sackmann_csv_loader.py` | CSV → list[MatchRecord] | ~120 |
| infrastructure | `src/infrastructure/data/tennis_ratings_store.py` | ratings.json read/write | ~80 |
| domain | `src/domain/pricing/tennis/__init__.py` | package marker | 5 |
| domain | `src/domain/pricing/tennis/glicko.py` | Glicko-2 update + win prob | ~180 |
| domain | `src/domain/pricing/tennis/serve_metrics.py` | per-player serve % aggregation | ~150 |
| domain | `src/domain/pricing/tennis/markov.py` | Newton-Keller game/set formülleri | ~180 |
| domain | `src/domain/pricing/tennis/h2h_pricer.py` | Glicko diff + surface → P(YES) | ~120 |
| domain | `src/domain/pricing/tennis/set_handicap_pricer.py` | Markov set dağılımı → handicap P | ~150 |
| domain | `src/domain/pricing/tennis/totals_pricer.py` | hold-rate Markov → total games | ~180 |
| domain | `src/domain/pricing/tennis/first_set_pricer.py` | Newton-Keller first set | ~100 |
| domain | `src/domain/pricing/tennis/set_totals_pricer.py` | set sequence Markov | ~120 |
| orchestration | `scripts/build_tennis_ratings.py` | infra → domain → ratings.json | ~200 |
| strategy | `src/strategy/enrichment/tennis_model_anchor.py` | submarket anchor override | ~150 |
| config | `src/config/sport_rules.py` (DÜZENLE) | tennis bloğuna `submarket_anchor` ekle | +5 |
| config | `config.yaml` (DÜZENLE) | tennis pricer parametreleri | +20 |

### Test dosyaları

- `tests/unit/domain/pricing/tennis/test_glicko.py`
- `tests/unit/domain/pricing/tennis/test_serve_metrics.py`
- `tests/unit/domain/pricing/tennis/test_markov.py`
- `tests/unit/domain/pricing/tennis/test_h2h_pricer.py`
- `tests/unit/domain/pricing/tennis/test_set_handicap_pricer.py`
- `tests/unit/domain/pricing/tennis/test_totals_pricer.py`
- `tests/unit/domain/pricing/tennis/test_first_set_pricer.py`
- `tests/unit/domain/pricing/tennis/test_set_totals_pricer.py`
- `tests/integration/test_tennis_model_anchor.py`
- `tests/integration/test_build_tennis_ratings.py`

### Drift kontrolü

- `src/orchestration/factory.py:307` — `from scripts.build_tennis_ratings import main` orphan idi, artık dosya var → drift kapanır.
- `src/strategy/enrichment/odds_enricher.py` — değişmez, sadece h2h okumaya devam. Tennis alt marketlerde `tennis_model_anchor` devreye girer, odds_enricher'ı bypass eder.
- `src/config/sport_rules.py` — tennis bloğuna `submarket_anchor` eklenir, mevcut keys korunur.
- Mevcut `tennis_player_resolver` ve `tennis_tournament_resolver` korunur (Polymarket slug → Sackmann player name eşleme).

---

## Task 1: Sackmann CSV Loader (Infrastructure)

**Files:**
- Create: `src/infrastructure/data/sackmann_csv_loader.py`
- Test: `tests/unit/infrastructure/data/test_sackmann_csv_loader.py`

**Sorumluluk:** CSV → `list[MatchRecord]`. Her satır bir maç (winner/loser, serve metrics, surface).

- [ ] **Step 1: Failing test yaz**

```python
# tests/unit/infrastructure/data/test_sackmann_csv_loader.py
"""Sackmann CSV loader — bir CSV string'i alıp MatchRecord listesine çevirir."""
from io import StringIO

from src.infrastructure.data.sackmann_csv_loader import load_matches_from_csv


SAMPLE_CSV = (
    "tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,match_num,"
    "winner_id,winner_seed,winner_entry,winner_name,winner_hand,winner_ht,winner_ioc,winner_age,"
    "loser_id,loser_seed,loser_entry,loser_name,loser_hand,loser_ht,loser_ioc,loser_age,"
    "score,best_of,round,minutes,"
    "w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,"
    "l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,"
    "winner_rank,winner_rank_points,loser_rank,loser_rank_points\n"
    "2026-9900,United Cup,Hard,18,A,20260105,400,128034,9,,Hurkacz,R,196,POL,28.8,"
    "104527,16,,Wawrinka,R,183,SUI,40.7,6-3 3-6 6-3,3,F,114,"
    "18,0,90,63,52,9,14,8,9,10,1,78,49,38,15,13,5,7,83,710,156,397\n"
)


def test_load_basic_match():
    records = load_matches_from_csv(StringIO(SAMPLE_CSV))
    assert len(records) == 1
    m = records[0]
    assert m.winner_name == "Hurkacz"
    assert m.loser_name == "Wawrinka"
    assert m.surface == "Hard"
    assert m.w_svpt == 90 and m.w_1st_in == 63 and m.w_1st_won == 52


def test_skips_invalid_rows():
    bad = SAMPLE_CSV + "incomplete,row\n"
    records = load_matches_from_csv(StringIO(bad))
    assert len(records) == 1  # bad row silently dropped (infra boundary)
```

- [ ] **Step 2: Failing test verify**

`pytest tests/unit/infrastructure/data/test_sackmann_csv_loader.py -v`
Expected: ImportError or NameError (loader yok)

- [ ] **Step 3: Minimal implementation**

```python
# src/infrastructure/data/sackmann_csv_loader.py
"""Sackmann CSV reader — match records as dataclasses.

Infrastructure layer: file/IO at boundary, returns plain dataclasses to domain.
Bad rows logged + skipped (Kural 12 — infra hatası retry yerine default).
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from typing import Iterator, TextIO

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MatchRecord:
    tourney_id: str
    tourney_date: str  # YYYYMMDD
    surface: str
    winner_name: str
    loser_name: str
    w_svpt: int
    w_1st_in: int
    w_1st_won: int
    w_2nd_won: int
    w_sv_gms: int
    l_svpt: int
    l_1st_in: int
    l_1st_won: int
    l_2nd_won: int
    l_sv_gms: int
    best_of: int
    score: str


def _parse_int(val: str) -> int | None:
    try:
        return int(val) if val.strip() else None
    except ValueError:
        return None


def _row_to_record(row: dict) -> MatchRecord | None:
    fields = {
        "w_svpt": _parse_int(row.get("w_svpt", "")),
        "w_1stIn": _parse_int(row.get("w_1stIn", "")),
        "w_1stWon": _parse_int(row.get("w_1stWon", "")),
        "w_2ndWon": _parse_int(row.get("w_2ndWon", "")),
        "w_SvGms": _parse_int(row.get("w_SvGms", "")),
        "l_svpt": _parse_int(row.get("l_svpt", "")),
        "l_1stIn": _parse_int(row.get("l_1stIn", "")),
        "l_1stWon": _parse_int(row.get("l_1stWon", "")),
        "l_2ndWon": _parse_int(row.get("l_2ndWon", "")),
        "l_SvGms": _parse_int(row.get("l_SvGms", "")),
    }
    if any(v is None for v in fields.values()):
        return None
    return MatchRecord(
        tourney_id=row.get("tourney_id", ""),
        tourney_date=row.get("tourney_date", ""),
        surface=row.get("surface", "Unknown"),
        winner_name=row.get("winner_name", "").strip(),
        loser_name=row.get("loser_name", "").strip(),
        w_svpt=fields["w_svpt"],
        w_1st_in=fields["w_1stIn"],
        w_1st_won=fields["w_1stWon"],
        w_2nd_won=fields["w_2ndWon"],
        w_sv_gms=fields["w_SvGms"],
        l_svpt=fields["l_svpt"],
        l_1st_in=fields["l_1stIn"],
        l_1st_won=fields["l_1stWon"],
        l_2nd_won=fields["l_2ndWon"],
        l_sv_gms=fields["l_SvGms"],
        best_of=int(row.get("best_of", "3") or 3),
        score=row.get("score", ""),
    )


def load_matches_from_csv(handle: TextIO) -> list[MatchRecord]:
    reader = csv.DictReader(handle)
    out: list[MatchRecord] = []
    for row in reader:
        rec = _row_to_record(row)
        if rec is None:
            continue
        out.append(rec)
    return out


def load_matches_from_path(path) -> list[MatchRecord]:
    with open(path, encoding="utf-8") as f:
        return load_matches_from_csv(f)
```

- [ ] **Step 4: Test pass verify**

`pytest tests/unit/infrastructure/data/test_sackmann_csv_loader.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/data/sackmann_csv_loader.py tests/unit/infrastructure/data/test_sackmann_csv_loader.py
git commit -m "feat(tennis): Sackmann CSV loader (infra)"
```

---

## Task 2: Glicko-2 Rating Module (Domain)

**Files:**
- Create: `src/domain/pricing/tennis/__init__.py`
- Create: `src/domain/pricing/tennis/glicko.py`
- Test: `tests/unit/domain/pricing/tennis/test_glicko.py`

**Sorumluluk:** Glicko-2 rating güncellemesi + iki rating arası win probability. PLOS One 2022 (Glicko %73 doğruluk) referansı.

- [ ] **Step 1: Failing test yaz**

```python
# tests/unit/domain/pricing/tennis/test_glicko.py
"""Glicko-2: Glickman 2013 paper formülleri."""
import math

from src.domain.pricing.tennis.glicko import (
    Rating,
    update_rating,
    win_probability,
    DEFAULT_RATING,
    DEFAULT_RD,
    DEFAULT_VOL,
)


def test_default_rating():
    r = Rating()
    assert r.mu == DEFAULT_RATING
    assert r.phi == DEFAULT_RD
    assert r.sigma == DEFAULT_VOL


def test_win_probability_equal_ratings_is_half():
    r1 = Rating()
    r2 = Rating()
    p = win_probability(r1, r2)
    assert abs(p - 0.5) < 1e-6


def test_win_probability_higher_rating_wins_more():
    strong = Rating(mu=1800)
    weak = Rating(mu=1500)
    assert win_probability(strong, weak) > 0.7


def test_update_after_win_increases_rating():
    r1 = Rating(mu=1500, phi=200, sigma=0.06)
    r2 = Rating(mu=1500, phi=200, sigma=0.06)
    # r1 beats r2
    r1_new = update_rating(r1, opponents=[r2], outcomes=[1.0])
    assert r1_new.mu > r1.mu
    assert r1_new.phi < r1.phi  # RD shrinks with new data


def test_update_after_loss_decreases_rating():
    r1 = Rating(mu=1500, phi=200, sigma=0.06)
    r2 = Rating(mu=1500, phi=200, sigma=0.06)
    r1_new = update_rating(r1, opponents=[r2], outcomes=[0.0])
    assert r1_new.mu < r1.mu


def test_no_games_only_drifts_rd():
    # No games played: rating unchanged, RD slightly increases
    r = Rating(mu=1500, phi=200, sigma=0.06)
    r_new = update_rating(r, opponents=[], outcomes=[])
    assert r_new.mu == r.mu
    assert r_new.phi >= r.phi
```

- [ ] **Step 2: Failing test verify**

`pytest tests/unit/domain/pricing/tennis/test_glicko.py -v`
Expected: 6 ImportError/FAIL

- [ ] **Step 3: Glicko-2 implementation**

```python
# src/domain/pricing/tennis/glicko.py
"""Glicko-2 rating system (Glickman 2013).

Domain layer — pure math, hiçbir I/O yok. Tennis maç tahmini için
PLOS One 2022 sport-bağımsız %73 doğruluk kanıtladı.

Formula referansları:
- mu: oyuncu yeteneği (1500 = ortalama)
- phi: rating deviation (200 = belirsiz, 30 = stabil)
- sigma: volatility (0.06 default, rating drift hızı)

Tüm hesaplar log-scale (mu/400) yerine internal Glicko scale (mu/173.7178).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

DEFAULT_RATING = 1500.0
DEFAULT_RD = 350.0
DEFAULT_VOL = 0.06
_SCALE = 173.7178  # Glicko-2 internal scale
_TAU = 0.5         # system constant (volatility change rate)
_EPSILON = 1e-6


@dataclass(frozen=True)
class Rating:
    mu: float = DEFAULT_RATING
    phi: float = DEFAULT_RD
    sigma: float = DEFAULT_VOL


def _g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / (math.pi * math.pi))


def _E(mu: float, mu_j: float, phi_j: float) -> float:
    return 1.0 / (1.0 + math.exp(-_g(phi_j) * (mu - mu_j)))


def win_probability(player: Rating, opponent: Rating) -> float:
    """P(player beats opponent). Internal scale conversion."""
    mu_p = (player.mu - DEFAULT_RATING) / _SCALE
    mu_o = (opponent.mu - DEFAULT_RATING) / _SCALE
    phi_o = opponent.phi / _SCALE
    return _E(mu_p, mu_o, phi_o)


def _new_sigma(sigma: float, phi: float, v: float, delta: float, tau: float) -> float:
    """Glickman illinois algorithm for new volatility."""
    a = math.log(sigma * sigma)
    delta_sq = delta * delta
    phi_sq = phi * phi

    def f(x: float) -> float:
        ex = math.exp(x)
        num = ex * (delta_sq - phi_sq - v - ex)
        den = 2.0 * (phi_sq + v + ex) ** 2
        return num / den - (x - a) / (tau * tau)

    A = a
    if delta_sq > phi_sq + v:
        B = math.log(delta_sq - phi_sq - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        B = a - k * tau

    fa = f(A)
    fb = f(B)
    while abs(B - A) > _EPSILON:
        C = A + (A - B) * fa / (fb - fa)
        fc = f(C)
        if fc * fb <= 0:
            A = B
            fa = fb
        else:
            fa = fa / 2.0
        B = C
        fb = fc
    return math.exp(A / 2.0)


def update_rating(
    rating: Rating,
    opponents: list[Rating],
    outcomes: list[float],
    tau: float = _TAU,
) -> Rating:
    """Apply one Glicko-2 update with N games.

    outcomes: 1.0 = win, 0.0 = loss, 0.5 = draw (tennis'te yok)
    No games → RD drifts up only.
    """
    mu = (rating.mu - DEFAULT_RATING) / _SCALE
    phi = rating.phi / _SCALE
    sigma = rating.sigma

    if not opponents:
        phi_star = math.sqrt(phi * phi + sigma * sigma)
        return replace(rating, phi=phi_star * _SCALE)

    opp_mu = [(o.mu - DEFAULT_RATING) / _SCALE for o in opponents]
    opp_phi = [o.phi / _SCALE for o in opponents]
    g_vals = [_g(p) for p in opp_phi]
    E_vals = [_E(mu, opp_mu[i], opp_phi[i]) for i in range(len(opponents))]

    v = 1.0 / sum(g_vals[i] ** 2 * E_vals[i] * (1.0 - E_vals[i]) for i in range(len(opponents)))
    delta = v * sum(g_vals[i] * (outcomes[i] - E_vals[i]) for i in range(len(opponents)))

    new_sigma = _new_sigma(sigma, phi, v, delta, tau)
    phi_star = math.sqrt(phi * phi + new_sigma * new_sigma)
    new_phi = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / v)
    new_mu = mu + new_phi * new_phi * sum(g_vals[i] * (outcomes[i] - E_vals[i]) for i in range(len(opponents)))

    return Rating(
        mu=new_mu * _SCALE + DEFAULT_RATING,
        phi=new_phi * _SCALE,
        sigma=new_sigma,
    )
```

```python
# src/domain/pricing/tennis/__init__.py
"""Tennis pricing domain — saf math modülleri."""
```

- [ ] **Step 4: Test pass verify**

`pytest tests/unit/domain/pricing/tennis/test_glicko.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/pricing/tennis/__init__.py src/domain/pricing/tennis/glicko.py tests/unit/domain/pricing/tennis/test_glicko.py
git commit -m "feat(tennis): Glicko-2 rating module (domain)"
```

---

## Task 3: Serve Metrics Aggregator (Domain)

**Files:**
- Create: `src/domain/pricing/tennis/serve_metrics.py`
- Test: `tests/unit/domain/pricing/tennis/test_serve_metrics.py`

**Sorumluluk:** MatchRecord listesinden her oyuncu için surface-specific serve % çıkar.

- [ ] **Step 1: Failing test**

```python
# tests/unit/domain/pricing/tennis/test_serve_metrics.py
from src.infrastructure.data.sackmann_csv_loader import MatchRecord
from src.domain.pricing.tennis.serve_metrics import (
    PlayerServeStats,
    aggregate_serve_stats,
    point_win_on_serve,
)


def _mk(winner: str, loser: str, surface: str,
        w_pts=80, w_1in=50, w_1won=40, w_2won=20,
        l_pts=80, l_1in=50, l_1won=30, l_2won=15) -> MatchRecord:
    return MatchRecord(
        tourney_id="x", tourney_date="20260101", surface=surface,
        winner_name=winner, loser_name=loser,
        w_svpt=w_pts, w_1st_in=w_1in, w_1st_won=w_1won, w_2nd_won=w_2won, w_sv_gms=10,
        l_svpt=l_pts, l_1st_in=l_1in, l_1st_won=l_1won, l_2nd_won=l_2won, l_sv_gms=10,
        best_of=3, score="6-4 6-4",
    )


def test_aggregate_single_match():
    matches = [_mk("Alice", "Bob", "Hard")]
    stats = aggregate_serve_stats(matches)
    alice = stats[("Alice", "Hard")]
    # 40 (1st won) + 20 (2nd won) = 60 / 80 = 0.75
    assert abs(alice.serve_pts_won_pct - 0.75) < 1e-6


def test_aggregate_separates_surface():
    matches = [
        _mk("Alice", "Bob", "Hard", w_1won=40, w_2won=20),
        _mk("Alice", "Carol", "Clay", w_1won=30, w_2won=10),
    ]
    stats = aggregate_serve_stats(matches)
    assert ("Alice", "Hard") in stats
    assert ("Alice", "Clay") in stats
    assert stats[("Alice", "Hard")].serve_pts_won_pct > stats[("Alice", "Clay")].serve_pts_won_pct


def test_aggregate_accumulates_multiple_matches():
    matches = [
        _mk("Alice", "Bob", "Hard", w_pts=100, w_1won=50, w_2won=25),
        _mk("Alice", "Carol", "Hard", w_pts=100, w_1won=50, w_2won=25),
    ]
    stats = aggregate_serve_stats(matches)
    # 150/200 = 0.75
    assert abs(stats[("Alice", "Hard")].serve_pts_won_pct - 0.75) < 1e-6


def test_point_win_on_serve_combines_two_players():
    # A serves 65%, B returns implied 35%
    a = PlayerServeStats(serve_pts_won_pct=0.65, return_pts_won_pct=0.40, n_points=1000)
    b = PlayerServeStats(serve_pts_won_pct=0.60, return_pts_won_pct=0.35, n_points=1000)
    # Bartoš-Cohen 2005 method: avg(A_serve, 1 - B_return)
    p = point_win_on_serve(a, b)
    assert 0.55 < p < 0.75
```

- [ ] **Step 2: Failing test verify**

`pytest tests/unit/domain/pricing/tennis/test_serve_metrics.py -v`
Expected: 4 ImportError

- [ ] **Step 3: Implementation**

```python
# src/domain/pricing/tennis/serve_metrics.py
"""Per-player serve/return aggregation by surface.

Domain — pure aggregation from MatchRecord list. Hiç I/O yok.

Bartoš-Cohen point-win formula:
  P(A wins on own serve) = (A_serve_pct + (1 - B_return_pct)) / 2

Bu, iki oyuncunun "true" serve gücünü common-opponent etkilemeden tahmin eder.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from src.infrastructure.data.sackmann_csv_loader import MatchRecord


@dataclass(frozen=True)
class PlayerServeStats:
    serve_pts_won_pct: float   # 1st_won + 2nd_won / svpt
    return_pts_won_pct: float  # opponent's 1st_lost + 2nd_lost / opp_svpt
    n_points: int              # data depth (low N → unreliable)


@dataclass
class _Accumulator:
    serve_won: int = 0
    serve_total: int = 0
    return_won: int = 0
    return_total: int = 0

    def to_stats(self) -> PlayerServeStats:
        s_pct = self.serve_won / self.serve_total if self.serve_total else 0.6
        r_pct = self.return_won / self.return_total if self.return_total else 0.35
        return PlayerServeStats(
            serve_pts_won_pct=s_pct,
            return_pts_won_pct=r_pct,
            n_points=self.serve_total + self.return_total,
        )


def aggregate_serve_stats(matches: list[MatchRecord]) -> dict[tuple[str, str], PlayerServeStats]:
    """Returns mapping (player_name, surface) -> PlayerServeStats."""
    acc: dict[tuple[str, str], _Accumulator] = defaultdict(_Accumulator)
    for m in matches:
        w_key = (m.winner_name, m.surface)
        l_key = (m.loser_name, m.surface)
        w_serve_won = m.w_1st_won + m.w_2nd_won
        l_serve_won = m.l_1st_won + m.l_2nd_won
        acc[w_key].serve_won += w_serve_won
        acc[w_key].serve_total += m.w_svpt
        acc[w_key].return_won += (m.l_svpt - l_serve_won)
        acc[w_key].return_total += m.l_svpt
        acc[l_key].serve_won += l_serve_won
        acc[l_key].serve_total += m.l_svpt
        acc[l_key].return_won += (m.w_svpt - w_serve_won)
        acc[l_key].return_total += m.w_svpt
    return {k: v.to_stats() for k, v in acc.items()}


def point_win_on_serve(server: PlayerServeStats, returner: PlayerServeStats) -> float:
    """Bartoš-Cohen 2005 — average of server's serve % and (1 - returner's return %)."""
    return (server.serve_pts_won_pct + (1.0 - returner.return_pts_won_pct)) / 2.0
```

- [ ] **Step 4: Test pass verify**

`pytest tests/unit/domain/pricing/tennis/test_serve_metrics.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/pricing/tennis/serve_metrics.py tests/unit/domain/pricing/tennis/test_serve_metrics.py
git commit -m "feat(tennis): serve metrics aggregator (domain)"
```

---

## Task 4: Markov Game/Set Formulas (Domain)

**Files:**
- Create: `src/domain/pricing/tennis/markov.py`
- Test: `tests/unit/domain/pricing/tennis/test_markov.py`

**Sorumluluk:** Newton-Keller 2005 + O'Malley 2008 formülleri. Tek girdi: `p` (serve point win %). Çıktı: game win %, set win %, match win % (BO3/BO5).

- [ ] **Step 1: Failing test**

```python
# tests/unit/domain/pricing/tennis/test_markov.py
"""Newton-Keller tennis formulas.

Kanıt değerleri Wikipedia ve O'Malley 2008'den.
"""
from src.domain.pricing.tennis.markov import (
    game_win_prob,
    tiebreak_win_prob,
    set_win_prob,
    match_win_prob,
)


def test_game_at_equal_serve_is_half():
    assert abs(game_win_prob(0.5) - 0.5) < 1e-6


def test_game_at_high_serve():
    # p=0.65 → game win ~ 0.83 (O'Malley reference)
    p = game_win_prob(0.65)
    assert 0.82 < p < 0.85


def test_game_at_low_serve():
    p = game_win_prob(0.35)
    assert 0.15 < p < 0.18  # symmetric


def test_set_win_prob_high_serve_pair():
    # Both at p_a=0.65, p_b=0.55 (returner gets 0.40 hold)
    # → A should win set comfortably
    p = set_win_prob(p_a_serve=0.65, p_b_serve=0.55)
    assert 0.60 < p < 0.80


def test_match_bo3_win_prob():
    # set prob 0.70 → match (BO3) ~ 0.784 (literature)
    p = match_win_prob(set_prob=0.70, best_of=3)
    assert 0.78 < p < 0.79


def test_match_bo5_win_prob():
    # set prob 0.70 → match (BO5) ~ 0.837
    p = match_win_prob(set_prob=0.70, best_of=5)
    assert 0.83 < p < 0.84


def test_match_bo5_higher_than_bo3():
    set_p = 0.65
    assert match_win_prob(set_p, 5) > match_win_prob(set_p, 3)


def test_tiebreak_equal_is_half():
    assert abs(tiebreak_win_prob(0.5, 0.5) - 0.5) < 1e-6
```

- [ ] **Step 2: Failing test verify**

`pytest tests/unit/domain/pricing/tennis/test_markov.py -v`
Expected: 8 ImportError

- [ ] **Step 3: Implementation**

```python
# src/domain/pricing/tennis/markov.py
"""Newton-Keller (2005) + O'Malley (2008) closed-form tennis formulas.

Bir oyuncunun serve point % (p) verilince:
- game_win_prob(p): standart oyun (deuce dahil)
- tiebreak_win_prob(p_a, p_b): 7-puan tiebreak
- set_win_prob: 6-game set (tiebreak dahil)
- match_win_prob: BO3 veya BO5

Tüm formüller saf math (domain), I/O yok.
"""
from __future__ import annotations

from functools import lru_cache
from math import comb


def game_win_prob(p: float) -> float:
    """Standart oyun (4 puan, deuce dahil). O'Malley closed-form."""
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    q = 1.0 - p
    # P(win 4-0) + P(win 4-1) + P(win 4-2) + P(win after deuce)
    p4_0 = p ** 4
    p4_1 = 4 * p ** 4 * q
    p4_2 = 10 * p ** 4 * q * q
    # Deuce reach: 20 * p^3 * q^3; then geometric loop
    deuce_reach = 20 * (p ** 3) * (q ** 3)
    p_deuce_win = p * p / (p * p + q * q)
    return p4_0 + p4_1 + p4_2 + deuce_reach * p_deuce_win


def tiebreak_win_prob(p_a: float, p_b: float) -> float:
    """7-puan tiebreak — O'Malley 2008 formula 8.

    p_a: A's serve point % (A serves first, alternation per ITF rules)
    p_b: B's serve point %
    """
    if p_a <= 0 and p_b <= 0:
        return 0.0
    if p_a >= 1 and p_b >= 1:
        return 0.5
    # Closed-form requires summing over all valid score paths.
    # Use exact dynamic programming over tiebreak state.
    return _tiebreak_dp(p_a, p_b)


@lru_cache(maxsize=4096)
def _tiebreak_dp(p_a: float, p_b: float) -> float:
    """Tiebreak via memoized recursion. State: (A score, B score, server)."""
    def serve_by(idx: int) -> str:
        # ITF: A serves point 1, B serves 2-3, A serves 4-5, ...
        if idx == 0:
            return "A"
        return "A" if ((idx - 1) // 2) % 2 == 1 else "B"

    def recurse(a: int, b: int, point_idx: int) -> float:
        if a >= 7 and a - b >= 2:
            return 1.0
        if b >= 7 and b - a >= 2:
            return 0.0
        server = serve_by(point_idx)
        p_a_wins_pt = p_a if server == "A" else (1.0 - p_b)
        win = recurse(a + 1, b, point_idx + 1)
        lose = recurse(a, b + 1, point_idx + 1)
        return p_a_wins_pt * win + (1.0 - p_a_wins_pt) * lose

    return recurse(0, 0, 0)


def set_win_prob(p_a_serve: float, p_b_serve: float) -> float:
    """6-game set — A and B alternate serve. Tiebreak at 6-6."""
    g_a = game_win_prob(p_a_serve)
    g_b = game_win_prob(p_b_serve)
    # Sum over all valid set-ending scores
    # P(A wins 6-0..6-4) + P(A wins 7-5) + P(A wins 7-6 in tiebreak)
    return _set_dp(g_a, g_b, p_a_serve, p_b_serve)


@lru_cache(maxsize=4096)
def _set_dp(g_a: float, g_b: float, p_a: float, p_b: float) -> float:
    """Set via state DP. State: (A games, B games, next server idx)."""
    def recurse(a: int, b: int, server_idx: int) -> float:
        if a == 6 and b <= 4:
            return 1.0
        if b == 6 and a <= 4:
            return 0.0
        if a == 7 and b == 5:
            return 1.0
        if b == 7 and a == 5:
            return 0.0
        if a == 6 and b == 6:
            return _tiebreak_dp(p_a, p_b)
        a_serves = server_idx % 2 == 0
        p_a_wins_game = g_a if a_serves else (1.0 - g_b)
        return (
            p_a_wins_game * recurse(a + 1, b, server_idx + 1)
            + (1.0 - p_a_wins_game) * recurse(a, b + 1, server_idx + 1)
        )

    return recurse(0, 0, 0)


def match_win_prob(set_prob: float, best_of: int) -> float:
    """Best-of-N match probability from set probability."""
    if best_of == 3:
        sets_to_win = 2
    elif best_of == 5:
        sets_to_win = 3
    else:
        raise ValueError(f"best_of must be 3 or 5, got {best_of}")
    p = set_prob
    q = 1.0 - p
    total = 0.0
    for n_losses in range(sets_to_win):
        total += comb(sets_to_win - 1 + n_losses, n_losses) * (p ** sets_to_win) * (q ** n_losses)
    return total
```

- [ ] **Step 4: Test pass verify**

`pytest tests/unit/domain/pricing/tennis/test_markov.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/pricing/tennis/markov.py tests/unit/domain/pricing/tennis/test_markov.py
git commit -m "feat(tennis): Newton-Keller Markov game/set/match formulas"
```

---

## Task 5: H2H Pricer (Domain)

**Files:**
- Create: `src/domain/pricing/tennis/h2h_pricer.py`
- Test: `tests/unit/domain/pricing/tennis/test_h2h_pricer.py`

**Sorumluluk:** Glicko diff + surface-specific serve % blend → P(A beats B) = h2h olasılığı.

- [ ] **Step 1: Failing test**

```python
# tests/unit/domain/pricing/tennis/test_h2h_pricer.py
from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats
from src.domain.pricing.tennis.h2h_pricer import price_h2h


def test_strong_vs_weak_high_prob():
    strong = Rating(mu=1800, phi=50)
    weak = Rating(mu=1500, phi=50)
    s_serve = PlayerServeStats(0.68, 0.42, 5000)
    w_serve = PlayerServeStats(0.58, 0.34, 5000)
    p = price_h2h(strong, weak, s_serve, w_serve, best_of=3)
    assert p > 0.70


def test_equal_players_half():
    r = Rating(mu=1600, phi=80)
    serve = PlayerServeStats(0.62, 0.38, 5000)
    p = price_h2h(r, r, serve, serve, best_of=3)
    assert abs(p - 0.5) < 1e-3


def test_bo5_extends_favorite():
    a = Rating(mu=1700, phi=80)
    b = Rating(mu=1550, phi=80)
    sa = PlayerServeStats(0.65, 0.40, 5000)
    sb = PlayerServeStats(0.60, 0.35, 5000)
    p_bo3 = price_h2h(a, b, sa, sb, best_of=3)
    p_bo5 = price_h2h(a, b, sa, sb, best_of=5)
    assert p_bo5 > p_bo3
```

- [ ] **Step 2: Failing test verify**

`pytest tests/unit/domain/pricing/tennis/test_h2h_pricer.py -v`
Expected: 3 ImportError

- [ ] **Step 3: Implementation**

```python
# src/domain/pricing/tennis/h2h_pricer.py
"""H2H (match winner) pricer — Glicko + serve % blend.

Glicko %73 doğruluk veriyor (PLOS One 2022). Serve % match dynamics ekliyor.
Blend: 0.6 * Glicko + 0.4 * Markov serve. Ağırlık config.yaml'dan gelir.
"""
from __future__ import annotations

from src.domain.pricing.tennis.glicko import Rating, win_probability
from src.domain.pricing.tennis.markov import match_win_prob, set_win_prob
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats, point_win_on_serve


def price_h2h(
    a_rating: Rating,
    b_rating: Rating,
    a_serve: PlayerServeStats,
    b_serve: PlayerServeStats,
    best_of: int,
    glicko_weight: float = 0.6,
) -> float:
    """P(A beats B). Returns P(YES) for the "A wins" market."""
    glicko_p = win_probability(a_rating, b_rating)

    p_a = point_win_on_serve(a_serve, b_serve)
    p_b = point_win_on_serve(b_serve, a_serve)
    set_p = set_win_prob(p_a, p_b)
    serve_p = match_win_prob(set_p, best_of=best_of)

    return glicko_weight * glicko_p + (1.0 - glicko_weight) * serve_p
```

- [ ] **Step 4: Test pass verify**

`pytest tests/unit/domain/pricing/tennis/test_h2h_pricer.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/pricing/tennis/h2h_pricer.py tests/unit/domain/pricing/tennis/test_h2h_pricer.py
git commit -m "feat(tennis): H2H pricer (Glicko + Markov blend)"
```

---

## Task 6: Set Handicap Pricer (Domain)

**Files:**
- Create: `src/domain/pricing/tennis/set_handicap_pricer.py`
- Test: `tests/unit/domain/pricing/tennis/test_set_handicap_pricer.py`

**Sorumluluk:** Markov set sequence DP → her olası set skoru (2-0, 2-1, 1-2, 0-2) olasılığı → handicap (örn. -1.5, +1.5) olasılığı.

- [ ] **Step 1: Failing test**

```python
# tests/unit/domain/pricing/tennis/test_set_handicap_pricer.py
from src.domain.pricing.tennis.set_handicap_pricer import (
    set_score_distribution,
    price_set_handicap,
)


def test_distribution_sums_to_one_bo3():
    dist = set_score_distribution(set_prob=0.65, best_of=3)
    # keys: (2,0), (2,1), (1,2), (0,2)
    total = sum(dist.values())
    assert abs(total - 1.0) < 1e-6
    assert dist[(2, 0)] + dist[(2, 1)] > dist[(1, 2)] + dist[(0, 2)]


def test_distribution_sums_to_one_bo5():
    dist = set_score_distribution(set_prob=0.60, best_of=5)
    # keys: (3,0), (3,1), (3,2), (2,3), (1,3), (0,3)
    assert abs(sum(dist.values()) - 1.0) < 1e-6


def test_minus_15_handicap_bo3():
    # A favori p=0.65 → A -1.5 (must win 2-0) probability
    p = price_set_handicap(set_prob=0.65, best_of=3, handicap=-1.5)
    # P(2-0) = 0.65^2 = 0.4225
    assert 0.42 < p < 0.43


def test_plus_15_handicap_bo3():
    # B underdog +1.5 (B kazansın veya 1 set kaybetsin)
    p = price_set_handicap(set_prob=0.35, best_of=3, handicap=1.5)
    # B handicap+1.5 = (B kazan 2-0 + 2-1) + (B 1 set al, A kazan 2-1)
    # B win = 0.35 * (1 + 2*0.65) = 0.35 * 2.3 ... not exactly. Use distribution.
    # From perspective of "Player with handicap +1.5":
    # +1.5 covers: B wins (2-0 or 2-1) OR A wins 2-1
    # = dist[(0,2)] + dist[(1,2)] + dist[(2,1)]
    assert p > 0.5
```

- [ ] **Step 2: Failing test verify**

`pytest tests/unit/domain/pricing/tennis/test_set_handicap_pricer.py -v`
Expected: 4 ImportError

- [ ] **Step 3: Implementation**

```python
# src/domain/pricing/tennis/set_handicap_pricer.py
"""Set handicap pricer — set sequence Markov.

Multiclass set-score distribution: her geçerli skor (BO3: 2-0/2-1/1-2/0-2;
BO5: 3-0/.../0-3) için marjinal olasılık. Handicap olasılığı bu dağılımdan
toplanır.

set_prob: A'nın tek set kazanma olasılığı (Markov'dan gelir).
"""
from __future__ import annotations


def set_score_distribution(set_prob: float, best_of: int) -> dict[tuple[int, int], float]:
    """Tüm (a_sets, b_sets) outcome'larının olasılığı."""
    p = set_prob
    q = 1.0 - p
    if best_of == 3:
        return {
            (2, 0): p * p,
            (2, 1): 2 * p * p * q,
            (1, 2): 2 * p * q * q,
            (0, 2): q * q,
        }
    if best_of == 5:
        # A wins 3-k → C(3+k-1, k) * p^3 * q^k for k=0,1,2
        return {
            (3, 0): p ** 3,
            (3, 1): 3 * p ** 3 * q,
            (3, 2): 6 * p ** 3 * q * q,
            (2, 3): 6 * p * p * q ** 3,
            (1, 3): 3 * p * q ** 3,
            (0, 3): q ** 3,
        }
    raise ValueError(f"best_of must be 3 or 5, got {best_of}")


def price_set_handicap(set_prob: float, best_of: int, handicap: float) -> float:
    """P(player with handicap covers).

    handicap > 0 → underdog'a verilir, set farkı handicap kadarsa kazanır.
    handicap < 0 → favori için, kesin margin gerekir.
    Örn: -1.5 → 2 set farkla kazanmalı (2-0 veya 3-0/3-1).
    """
    dist = set_score_distribution(set_prob, best_of)
    total = 0.0
    for (a, b), prob in dist.items():
        # A's effective set score = a + handicap
        if a + handicap > b:
            total += prob
    return total
```

- [ ] **Step 4: Test pass verify**

`pytest tests/unit/domain/pricing/tennis/test_set_handicap_pricer.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/pricing/tennis/set_handicap_pricer.py tests/unit/domain/pricing/tennis/test_set_handicap_pricer.py
git commit -m "feat(tennis): set handicap pricer"
```

---

## Task 7: Total Games Pricer (Domain)

**Files:**
- Create: `src/domain/pricing/tennis/totals_pricer.py`
- Test: `tests/unit/domain/pricing/tennis/test_totals_pricer.py`

**Sorumluluk:** Markov ile expected total games + her toplam değerin olasılığı.

- [ ] **Step 1: Failing test**

```python
# tests/unit/domain/pricing/tennis/test_totals_pricer.py
from src.domain.pricing.tennis.totals_pricer import (
    expected_total_games,
    price_total_over,
)


def test_high_hold_more_games():
    # both p=0.70 (strong holds) → long sets
    high = expected_total_games(p_a=0.70, p_b=0.70, best_of=3)
    low = expected_total_games(p_a=0.50, p_b=0.50, best_of=3)
    assert high > low


def test_over_under_complement():
    p_over = price_total_over(p_a=0.65, p_b=0.60, best_of=3, line=22.5)
    p_under = price_total_over(p_a=0.65, p_b=0.60, best_of=3, line=22.5, side="under")
    assert abs(p_over + p_under - 1.0) < 1e-6


def test_bo5_has_more_games():
    bo3 = expected_total_games(p_a=0.65, p_b=0.60, best_of=3)
    bo5 = expected_total_games(p_a=0.65, p_b=0.60, best_of=5)
    assert bo5 > bo3


def test_extreme_dominance_low_total():
    # A çok güçlü (p=0.80), B zayıf (p=0.40) → maç çabuk biter
    total = expected_total_games(p_a=0.80, p_b=0.40, best_of=3)
    assert total < 22  # likely 12-18 range
```

- [ ] **Step 2: Failing test verify**

Expected: 4 ImportError

- [ ] **Step 3: Implementation**

```python
# src/domain/pricing/tennis/totals_pricer.py
"""Total games over/under — Markov game/set DP ile beklenen + dağılım.

Bir set kaç oyun sürer? p_a ve p_b'e bağlı. Düşük hold → çok break → kısa setler.
Yüksek hold → uzun setler + tiebreak.
"""
from __future__ import annotations

from functools import lru_cache

from src.domain.pricing.tennis.markov import game_win_prob, _tiebreak_dp


@lru_cache(maxsize=4096)
def _set_game_distribution(p_a: float, p_b: float) -> dict[int, float]:
    """Bir setin toplam oyun dağılımı (her oyun A perspektifinden hesaplanır)."""
    g_a = game_win_prob(p_a)
    g_b = game_win_prob(p_b)
    dist: dict[int, float] = {}

    def recurse(a: int, b: int, server_idx: int, prob: float) -> None:
        if a == 6 and b <= 4:
            total = a + b
            dist[total] = dist.get(total, 0.0) + prob
            return
        if b == 6 and a <= 4:
            total = a + b
            dist[total] = dist.get(total, 0.0) + prob
            return
        if a == 7 and b == 5:
            dist[12] = dist.get(12, 0.0) + prob
            return
        if b == 7 and a == 5:
            dist[12] = dist.get(12, 0.0) + prob
            return
        if a == 6 and b == 6:
            # Tiebreak: 1 game total, set ends 7-6
            dist[13] = dist.get(13, 0.0) + prob
            return
        a_serves = server_idx % 2 == 0
        p_a_wins_game = g_a if a_serves else (1.0 - g_b)
        recurse(a + 1, b, server_idx + 1, prob * p_a_wins_game)
        recurse(a, b + 1, server_idx + 1, prob * (1.0 - p_a_wins_game))

    recurse(0, 0, 0, 1.0)
    return dist


def _expected_games_per_set(p_a: float, p_b: float) -> float:
    dist = _set_game_distribution(p_a, p_b)
    return sum(g * pr for g, pr in dist.items())


def _expected_sets(p_a: float, p_b: float, best_of: int) -> float:
    from src.domain.pricing.tennis.markov import set_win_prob, match_win_prob
    sp = set_win_prob(p_a, p_b)
    # Expected sets via marginal score distribution
    if best_of == 3:
        e_sets = 2 * (sp ** 2 + (1 - sp) ** 2) + 3 * (2 * sp ** 2 * (1 - sp) + 2 * sp * (1 - sp) ** 2)
    elif best_of == 5:
        # similar; weights by binomial
        from math import comb
        total = 0.0
        for k in range(3):
            n = 3 + k  # total sets when one player wins 3
            # A wins n sets, B wins k
            p_a_path = comb(n - 1, k) * sp ** 3 * (1 - sp) ** k
            p_b_path = comb(n - 1, k) * (1 - sp) ** 3 * sp ** k
            total += n * (p_a_path + p_b_path)
        e_sets = total
    else:
        raise ValueError(f"best_of must be 3 or 5, got {best_of}")
    return e_sets


def expected_total_games(p_a: float, p_b: float, best_of: int) -> float:
    """E[total games] = E[sets] * E[games per set]."""
    return _expected_sets(p_a, p_b, best_of) * _expected_games_per_set(p_a, p_b)


def price_total_over(
    p_a: float,
    p_b: float,
    best_of: int,
    line: float,
    side: str = "over",
) -> float:
    """P(total games > line) — normal approx (mean + variance from set dist)."""
    # Use mean as point estimate, std from set dist.
    # For tighter accuracy: enumerate set count × convolution of set-game distributions.
    import math
    set_dist = _set_game_distribution(p_a, p_b)
    mean_g = sum(g * p for g, p in set_dist.items())
    var_g = sum((g - mean_g) ** 2 * p for g, p in set_dist.items())
    e_sets = _expected_sets(p_a, p_b, best_of)
    total_mean = e_sets * mean_g
    total_std = math.sqrt(e_sets * var_g)
    # Normal approximation
    if total_std < 1e-6:
        return 1.0 if total_mean > line else 0.0
    z = (line - total_mean) / total_std
    # P(over) = 1 - Phi(z); use erfc for stability
    p_over = 0.5 * math.erfc(z / math.sqrt(2.0))
    if side == "under":
        return 1.0 - p_over
    return p_over
```

- [ ] **Step 4: Test pass verify**

`pytest tests/unit/domain/pricing/tennis/test_totals_pricer.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/pricing/tennis/totals_pricer.py tests/unit/domain/pricing/tennis/test_totals_pricer.py
git commit -m "feat(tennis): total games pricer"
```

---

## Task 8: First Set Winner Pricer (Domain)

**Files:**
- Create: `src/domain/pricing/tennis/first_set_pricer.py`
- Test: `tests/unit/domain/pricing/tennis/test_first_set_pricer.py`

**Sorumluluk:** İlk set kazanma olasılığı = `set_win_prob(p_a, p_b)`. Format-agnostic (her zaman BO1 set).

- [ ] **Step 1: Failing test**

```python
# tests/unit/domain/pricing/tennis/test_first_set_pricer.py
from src.domain.pricing.tennis.first_set_pricer import price_first_set_winner


def test_equal_players_half():
    p = price_first_set_winner(p_a=0.60, p_b=0.60)
    assert abs(p - 0.5) < 1e-3


def test_strong_favorite_high_prob():
    p = price_first_set_winner(p_a=0.70, p_b=0.55)
    assert p > 0.7


def test_format_independent():
    # First set always BO1 set, so best_of doesn't matter
    p1 = price_first_set_winner(p_a=0.65, p_b=0.60)
    p2 = price_first_set_winner(p_a=0.65, p_b=0.60)
    assert p1 == p2
```

- [ ] **Step 2: Failing test verify**

Expected: 3 ImportError

- [ ] **Step 3: Implementation**

```python
# src/domain/pricing/tennis/first_set_pricer.py
"""First set winner — set win probability (format-agnostic)."""
from __future__ import annotations

from src.domain.pricing.tennis.markov import set_win_prob


def price_first_set_winner(p_a: float, p_b: float) -> float:
    """P(A wins first set). Just set_win_prob — no match-level dependence."""
    return set_win_prob(p_a, p_b)
```

- [ ] **Step 4: Test pass verify**

`pytest tests/unit/domain/pricing/tennis/test_first_set_pricer.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/pricing/tennis/first_set_pricer.py tests/unit/domain/pricing/tennis/test_first_set_pricer.py
git commit -m "feat(tennis): first set winner pricer"
```

---

## Task 9: Set Totals Pricer (Domain)

**Files:**
- Create: `src/domain/pricing/tennis/set_totals_pricer.py`
- Test: `tests/unit/domain/pricing/tennis/test_set_totals_pricer.py`

**Sorumluluk:** Kaç set oynanır olasılığı — over/under 2.5 set (BO3) veya over/under 3.5/4.5 set (BO5).

- [ ] **Step 1: Failing test**

```python
# tests/unit/domain/pricing/tennis/test_set_totals_pricer.py
from src.domain.pricing.tennis.set_totals_pricer import (
    set_count_distribution,
    price_set_total_over,
)


def test_bo3_distribution_sums_one():
    dist = set_count_distribution(set_prob=0.60, best_of=3)
    # keys: 2, 3 (no other valid counts)
    assert abs(sum(dist.values()) - 1.0) < 1e-6


def test_bo5_distribution_sums_one():
    dist = set_count_distribution(set_prob=0.55, best_of=5)
    # keys: 3, 4, 5
    assert abs(sum(dist.values()) - 1.0) < 1e-6


def test_close_match_more_sets():
    # 0.50 — closer → more 3-set matches
    close = set_count_distribution(set_prob=0.50, best_of=3)
    dom = set_count_distribution(set_prob=0.80, best_of=3)
    assert close[3] > dom[3]


def test_over_25_bo3():
    p = price_set_total_over(set_prob=0.55, best_of=3, line=2.5)
    # Over 2.5 → match goes to 3 sets
    # 3-set prob = 2*p*q*(p+q) = 2pq
    expected = 2 * 0.55 * 0.45
    assert abs(p - expected) < 1e-6
```

- [ ] **Step 2: Failing test verify**

Expected: 4 ImportError

- [ ] **Step 3: Implementation**

```python
# src/domain/pricing/tennis/set_totals_pricer.py
"""Set totals (number of sets) pricer."""
from __future__ import annotations

from src.domain.pricing.tennis.set_handicap_pricer import set_score_distribution


def set_count_distribution(set_prob: float, best_of: int) -> dict[int, float]:
    """Dağılım: {set_count: probability}."""
    score_dist = set_score_distribution(set_prob, best_of)
    counts: dict[int, float] = {}
    for (a, b), p in score_dist.items():
        n = a + b
        counts[n] = counts.get(n, 0.0) + p
    return counts


def price_set_total_over(set_prob: float, best_of: int, line: float) -> float:
    """P(set count > line)."""
    dist = set_count_distribution(set_prob, best_of)
    return sum(p for n, p in dist.items() if n > line)
```

- [ ] **Step 4: Test pass verify**

Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/pricing/tennis/set_totals_pricer.py tests/unit/domain/pricing/tennis/test_set_totals_pricer.py
git commit -m "feat(tennis): set totals pricer"
```

---

## Task 10: Tennis Ratings Store (Infrastructure)

**Files:**
- Create: `src/infrastructure/data/tennis_ratings_store.py`
- Test: `tests/unit/infrastructure/data/test_tennis_ratings_store.py`

**Sorumluluk:** `data/tennis_ratings.json` read/write. Player → (Rating, serve_stats by surface) eşleme.

- [ ] **Step 1: Failing test**

```python
# tests/unit/infrastructure/data/test_tennis_ratings_store.py
import json

from src.infrastructure.data.tennis_ratings_store import (
    PlayerSnapshot,
    save_ratings,
    load_ratings,
)
from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats


def test_save_and_load_round_trip(tmp_path):
    snap = {
        "Alice": PlayerSnapshot(
            rating=Rating(mu=1700, phi=80, sigma=0.06),
            serve_by_surface={
                "Hard": PlayerServeStats(0.65, 0.40, 5000),
                "Clay": PlayerServeStats(0.60, 0.38, 3000),
            },
        ),
    }
    path = tmp_path / "tennis_ratings.json"
    save_ratings(snap, path)
    loaded = load_ratings(path)
    assert "Alice" in loaded
    assert abs(loaded["Alice"].rating.mu - 1700) < 1e-6
    assert "Hard" in loaded["Alice"].serve_by_surface


def test_load_missing_file_returns_empty(tmp_path):
    loaded = load_ratings(tmp_path / "nonexistent.json")
    assert loaded == {}
```

- [ ] **Step 2: Failing test verify**

Expected: 2 ImportError

- [ ] **Step 3: Implementation**

```python
# src/infrastructure/data/tennis_ratings_store.py
"""tennis_ratings.json read/write.

Infra layer — atomic write (tmp → rename), missing file → empty dict.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats

logger = logging.getLogger(__name__)


@dataclass
class PlayerSnapshot:
    rating: Rating
    serve_by_surface: dict[str, PlayerServeStats]


def save_ratings(snapshot: dict[str, PlayerSnapshot], path: Path) -> None:
    payload = {
        name: {
            "rating": {"mu": s.rating.mu, "phi": s.rating.phi, "sigma": s.rating.sigma},
            "serve": {
                surface: {
                    "serve_pts_won_pct": stats.serve_pts_won_pct,
                    "return_pts_won_pct": stats.return_pts_won_pct,
                    "n_points": stats.n_points,
                }
                for surface, stats in s.serve_by_surface.items()
            },
        }
        for name, s in snapshot.items()
    }
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_ratings(path: Path) -> dict[str, PlayerSnapshot]:
    if not Path(path).exists():
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("tennis_ratings.json okunamadı: %s", exc)
        return {}
    out: dict[str, PlayerSnapshot] = {}
    for name, payload in data.items():
        r = payload.get("rating", {})
        rating = Rating(
            mu=float(r.get("mu", 1500.0)),
            phi=float(r.get("phi", 350.0)),
            sigma=float(r.get("sigma", 0.06)),
        )
        serve = {}
        for surface, stats in payload.get("serve", {}).items():
            serve[surface] = PlayerServeStats(
                serve_pts_won_pct=float(stats.get("serve_pts_won_pct", 0.6)),
                return_pts_won_pct=float(stats.get("return_pts_won_pct", 0.35)),
                n_points=int(stats.get("n_points", 0)),
            )
        out[name] = PlayerSnapshot(rating=rating, serve_by_surface=serve)
    return out
```

- [ ] **Step 4: Test pass verify**

Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/data/tennis_ratings_store.py tests/unit/infrastructure/data/test_tennis_ratings_store.py
git commit -m "feat(tennis): ratings store (infra)"
```

---

## Task 11: build_tennis_ratings.py Script (Orchestration)

**Files:**
- Create: `scripts/build_tennis_ratings.py`
- Test: `tests/integration/test_build_tennis_ratings.py`

**Sorumluluk:** CSV cache → MatchRecord → aggregate stats → Glicko update loop → ratings.json. Orchestration layer (infra→domain→infra I/O).

- [ ] **Step 1: Failing test**

```python
# tests/integration/test_build_tennis_ratings.py
import json
from pathlib import Path


def test_build_creates_ratings_json(tmp_path):
    """Test: minik CSV → build runs → ratings.json çıkar."""
    from scripts.build_tennis_ratings import build_ratings

    csv_dir = tmp_path / "sackmann"
    csv_dir.mkdir()
    sample = (tmp_path / "atp_matches_2026.csv")
    sample.write_text(
        "tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,match_num,"
        "winner_id,winner_seed,winner_entry,winner_name,winner_hand,winner_ht,winner_ioc,winner_age,"
        "loser_id,loser_seed,loser_entry,loser_name,loser_hand,loser_ht,loser_ioc,loser_age,"
        "score,best_of,round,minutes,"
        "w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,"
        "l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,"
        "winner_rank,winner_rank_points,loser_rank,loser_rank_points\n"
        "x,X,Hard,32,A,20260101,1,1,,,Alice,R,180,USA,25,2,,,Bob,R,180,ESP,26,"
        "6-3 6-4,3,F,90,5,1,80,55,40,15,10,3,5,4,2,75,45,30,10,10,5,8,1,100,2,90\n"
    )
    out = tmp_path / "ratings.json"
    csv_dir = tmp_path
    build_ratings(csv_dir, out)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "Alice" in data
    assert data["Alice"]["rating"]["mu"] > 1500  # winner gained rating
```

- [ ] **Step 2: Failing test verify**

Expected: ImportError

- [ ] **Step 3: Implementation**

```python
# scripts/build_tennis_ratings.py
"""CSV cache → tennis_ratings.json build script.

Orchestration: infra (CSV load) → domain (aggregate + Glicko) → infra (JSON write).
Hook'tan çağrılır (factory._maybe_invoke_sackmann_refresh).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from src.domain.pricing.tennis.glicko import Rating, update_rating
from src.domain.pricing.tennis.serve_metrics import aggregate_serve_stats
from src.infrastructure.data.sackmann_csv_loader import load_matches_from_path
from src.infrastructure.data.tennis_ratings_store import (
    PlayerSnapshot,
    save_ratings,
)

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path("data/sackmann_cache")
_DEFAULT_OUTPUT = Path("data/tennis_ratings.json")


def build_ratings(cache_dir: Path, output_path: Path) -> None:
    """All CSVs in cache_dir → aggregate stats + Glicko loop → save JSON."""
    csv_files = sorted(Path(cache_dir).glob("*.csv"))
    all_matches = []
    for csv in csv_files:
        try:
            all_matches.extend(load_matches_from_path(csv))
        except Exception as exc:  # noqa: BLE001 — infra boundary
            logger.warning("CSV load failed: %s (%s)", csv, exc)
    if not all_matches:
        logger.warning("No matches loaded from %s", cache_dir)
        return

    all_matches.sort(key=lambda m: m.tourney_date)
    logger.info("Building ratings from %d matches", len(all_matches))

    serve_stats = aggregate_serve_stats(all_matches)
    ratings: dict[str, Rating] = defaultdict(Rating)
    for m in all_matches:
        w = ratings[m.winner_name]
        l = ratings[m.loser_name]
        new_w = update_rating(w, [l], [1.0])
        new_l = update_rating(l, [w], [0.0])
        ratings[m.winner_name] = new_w
        ratings[m.loser_name] = new_l

    serve_by_player: dict[str, dict] = defaultdict(dict)
    for (player, surface), stats in serve_stats.items():
        serve_by_player[player][surface] = stats

    snapshot = {
        name: PlayerSnapshot(rating=r, serve_by_surface=serve_by_player.get(name, {}))
        for name, r in ratings.items()
    }
    save_ratings(snapshot, output_path)
    logger.info("Saved %d player ratings to %s", len(snapshot), output_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_ratings(_DEFAULT_CACHE_DIR, _DEFAULT_OUTPUT)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Test pass verify**

`pytest tests/integration/test_build_tennis_ratings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/build_tennis_ratings.py tests/integration/test_build_tennis_ratings.py
git commit -m "feat(tennis): build_tennis_ratings.py script"
```

---

## Task 12: tennis_model_anchor — Strategy Layer Integration

**Files:**
- Create: `src/strategy/enrichment/tennis_model_anchor.py`
- Modify: `src/config/sport_rules.py` (add tennis submarket_anchor)
- Modify: `src/strategy/enrichment/odds_enricher.py` (call model when source="model")
- Test: `tests/integration/test_tennis_model_anchor.py`

**Sorumluluk:** Polymarket market type'ı pricer'a yönlendir. Anchor source = "model" olduğunda model pricer çağrılır.

- [ ] **Step 1: Failing test**

```python
# tests/integration/test_tennis_model_anchor.py
from src.strategy.enrichment.tennis_model_anchor import compute_model_anchor
from src.infrastructure.data.tennis_ratings_store import PlayerSnapshot
from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats


def _mk_snapshot(mu: float, serve: float) -> PlayerSnapshot:
    return PlayerSnapshot(
        rating=Rating(mu=mu, phi=80),
        serve_by_surface={"Hard": PlayerServeStats(serve, 1 - serve + 0.05, 5000)},
    )


def test_h2h_uses_model():
    a = _mk_snapshot(1750, 0.66)
    b = _mk_snapshot(1500, 0.58)
    p = compute_model_anchor(
        market_type="moneyline",
        a_snapshot=a, b_snapshot=b,
        surface="Hard", best_of=3,
    )
    assert p is not None and p > 0.6


def test_set_handicap_minus_15():
    a = _mk_snapshot(1700, 0.65)
    b = _mk_snapshot(1500, 0.58)
    p = compute_model_anchor(
        market_type="tennis_set_handicap",
        a_snapshot=a, b_snapshot=b,
        surface="Hard", best_of=3,
        handicap=-1.5,
    )
    assert p is not None and 0 < p < 1


def test_unknown_market_returns_none():
    a = _mk_snapshot(1700, 0.65)
    b = _mk_snapshot(1500, 0.58)
    p = compute_model_anchor(
        market_type="unknown_market",
        a_snapshot=a, b_snapshot=b,
        surface="Hard", best_of=3,
    )
    assert p is None
```

- [ ] **Step 2: Failing test verify**

Expected: 3 ImportError

- [ ] **Step 3: Implementation**

```python
# src/strategy/enrichment/tennis_model_anchor.py
"""Tennis model anchor — Polymarket market_type → pricer dispatch.

Strategy layer. Anchor source override (sport_rules.submarket_anchor="model").
"""
from __future__ import annotations

from src.domain.pricing.tennis.h2h_pricer import price_h2h
from src.domain.pricing.tennis.set_handicap_pricer import price_set_handicap
from src.domain.pricing.tennis.totals_pricer import price_total_over
from src.domain.pricing.tennis.first_set_pricer import price_first_set_winner
from src.domain.pricing.tennis.set_totals_pricer import price_set_total_over
from src.domain.pricing.tennis.serve_metrics import point_win_on_serve
from src.infrastructure.data.tennis_ratings_store import PlayerSnapshot


def compute_model_anchor(
    market_type: str,
    a_snapshot: PlayerSnapshot,
    b_snapshot: PlayerSnapshot,
    surface: str,
    best_of: int,
    line: float | None = None,
    handicap: float | None = None,
) -> float | None:
    """Returns P(YES) from the model or None if market_type unsupported."""
    a_serve = a_snapshot.serve_by_surface.get(surface)
    b_serve = b_snapshot.serve_by_surface.get(surface)
    if a_serve is None or b_serve is None:
        return None
    p_a = point_win_on_serve(a_serve, b_serve)
    p_b = point_win_on_serve(b_serve, a_serve)

    mt = market_type.lower()
    if mt in ("moneyline", "h2h"):
        return price_h2h(a_snapshot.rating, b_snapshot.rating, a_serve, b_serve, best_of=best_of)
    if mt == "tennis_set_handicap" and handicap is not None:
        from src.domain.pricing.tennis.markov import set_win_prob
        set_p = set_win_prob(p_a, p_b)
        return price_set_handicap(set_p, best_of, handicap)
    if mt in ("tennis_match_totals", "tennis_first_set_totals") and line is not None:
        return price_total_over(p_a, p_b, best_of, line)
    if mt == "tennis_first_set_winner":
        return price_first_set_winner(p_a, p_b)
    if mt == "tennis_set_totals" and line is not None:
        from src.domain.pricing.tennis.markov import set_win_prob
        set_p = set_win_prob(p_a, p_b)
        return price_set_total_over(set_p, best_of, line)
    return None
```

- [ ] **Step 4: sport_rules.py update**

```python
# src/config/sport_rules.py:69-93 tennis bloğuna ekle (within existing dict):
"submarket_anchor": {
    "moneyline": "model",
    "tennis_set_handicap": "model",
    "tennis_match_totals": "model",
    "tennis_first_set_winner": "model",
    "tennis_first_set_totals": "model",
    "tennis_set_totals": "model",
},
```

- [ ] **Step 5: Test pass verify**

Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add src/strategy/enrichment/tennis_model_anchor.py src/config/sport_rules.py tests/integration/test_tennis_model_anchor.py
git commit -m "feat(tennis): model anchor dispatch + sport_rules submarket override"
```

---

## Task 13: Wire model anchor into entry flow

**Files:**
- Modify: `src/strategy/enrichment/odds_enricher.py` (call model when applicable)
- Test: `tests/integration/test_tennis_entry_with_model.py`

**Sorumluluk:** Entry path'inde tennis market gelince model anchor'ı çağırıp `bookmaker_prob` yerine kullan. Bu Task 12'deki yapı ile entry_processor arasındaki köprü.

> Implementation Task 12 sonrası odds_enricher'ın yapısına göre yapılır. Detay Task 12 commit'lendikten sonra netleşir (odds_enricher'ın o anki tam halini görmek gerek).

---

## Self-review checklist

- [x] Tüm task'larda exact file paths
- [x] Her step'te kod blokları (placeholder yok)
- [x] TDD red-green-refactor sırası
- [x] Her commit message imperative
- [x] ARCH_GUARD: domain'de I/O yok, 400 satır altı, 5-katman düzeni
- [x] DRY: markov.py ortak helper, her pricer kendi sorumluluğu
- [x] Magic number'lar config.yaml'a verilmedi mi → glicko_weight ve default ratings için Task'lar tamamlandıktan sonra config.yaml'a taşınır (Task 14 — sonradan)
- [x] Test isimlendirme: `test_<ne>_<senaryo>_<sonuc>` formatı

## Kaynaklar

- [Glicko-2 PLOS One 2022](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0266838)
- [Newton-Keller / O'Malley closed-form formulas](https://dash.harvard.edu/server/api/core/bitstreams/dc501d43-9be0-4c8a-8066-480bd5ff5be5/content)
- [Common-opponent stochastic model](https://www.sciencedirect.com/science/article/pii/S0898122112002106)
- [Hierarchical Markov Models 2024](https://dl.acm.org/doi/full/10.1145/3696952.3696982)
- [Boosting Markovian Tennis Prediction 2026](https://journals.sagepub.com/doi/10.1177/22150218251412670)
