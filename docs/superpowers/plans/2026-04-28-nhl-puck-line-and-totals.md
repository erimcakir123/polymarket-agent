# NHL Puck Line + Totals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NHL trading'i puck line (-1.5 spread) ve totals (over/under) market tiplerini destekleyecek şekilde genişlet — empirical lookup tablolarını 4198 maç MoneyPuck verisinden üret, Skellam fallback ile hibrit kapsama olasılığı, dedicated exit logic, monitor.py NHL market_type routing.

**Architecture:** Mevcut 5-katman mimarisi, NBA spread/totals pattern'i paralel. NHL Moneyline'da kurulu altyapı (decide_nhl_exit, _nhl_exit_dispatch, hybrid wp wrapper) korunur. Yeni domain modülleri Skellam λ_5v5 kullanır; infrastructure katmanında @lru_cache repository'ler tablo I/O yapar; strategy/exit/ altında sport-specific exit modülleri eklenir; monitor.py `pos.sports_market_type` üzerinden moneyline / puck_line / totals route eder. Empty net + SO modifier'ları NHL'e özgü dinamik (NBA'da yok).

**Tech Stack:** Python 3.12+, pandas/numpy (table build), `re` stdlib, mevcut `ExitReason` enum, `math.sqrt`, `Literal` typing, scipy.stats.skellam (Skellam dağılımı).

**Önkoşul:** NHL Moneyline + dispatch + smoke test tamamlandı (commit `c803673`, 1365 test geçiyor, mode: dry_run).

---

## Tasarım Kararları (Erim Onayı)

Plan başında verilen kararlar — değiştirilecekse plan baştan yazılır.

### Karar 1: Puck Line Standart Sadece -1.5

**Durum:** Polymarket NHL puck line market'lerinde -1.5 standart line (~%95 örnekler). +2.5 (alternate) çok nadir, MVP'de skip.

**Sonuç:** Empirical tablo sadece -1.5 için optimize edilir. Parser +1.5 underdog cover'ı destekler (BUY_NO = underdog +1.5). Bu yeterli — sembolik olarak `spread_line=1.5` saklanır, BUY_YES=favori cover -1.5, BUY_NO=underdog cover +1.5.

### Karar 2: Totals Line Polymarket'te Ne Çıkarsa

**Durum:** NHL lig avg 6.142, Polymarket'te yaygın line 5.5 ve 6.5.

**Sonuç:** Empirical tablo `target_total ∈ {5.5, 6.5}` için 2 ayrı bucket. Diğer line'lar (4.5, 7.5) için Skellam fallback. Parser her line'ı handle eder.

### Karar 3: SO Resolution Kuralı

**Durum:** Polymarket NHL puck line/totals genellikle "incl. OT/SO" çözer. SO winner +1 gol sayılır.

**Sonuç:**
- Puck line: SO winner +1 gol → -1.5 KAPATMAZ (tek goal fark), +1.5 KAPATIR. SO durumunda BUY_YES (-1.5) → loss, BUY_NO (+1.5) → win.
- Totals: SO biterse current_total + 1 (winner +1). Build script bunu hesaba katar.

### Karar 4: Empty Net Modifier Saat Bazlı

**Durum:** ESPN raw_status'ta "empty_net" flag yok. Doğrudan bilemeyiz.

**Sonuç:** Heuristik — P3 son 180 saniye + skor farkı 1-2 gol → empty net olası. Bu durumda Skellam λ_5v5 yerine λ_empty_net (~×1.8) kullanılır. Fallback empirical tabloda da bu pattern içkin (gerçek maçlarda boş kale göl artışı yansır).

### Karar 5: NBA Pattern Paralel + NHL Spesifikleri

**Yapı:** NBA spread/totals pattern paralel, ama:
- Math: Bill James `0.861×√clock` yerine **Skellam dağılımı** (NHL Poisson düşük λ ile farklı)
- OT: NBA'da partial sat (her OT ~25 puan); NHL'de OT max +1 gol (3v3 sudden death) → full hold + erken exit yok
- Empirical key numbers: NBA'da 3, 7 (basketball domain); NHL'de 1, 2 (hockey low-scoring)

### Karar 6: 3-way ML Skip

**Durum:** Polymarket NHL'de 3-way market nadir (regulation winner only).

**Sonuç:** Task 8 SKIP. Task 5 dry-run verisinde sık görülürse sonradan eklenir.

---

## Gerçek Polymarket Market Format Örnekleri

**Puck Line** (`sportsMarketType='spreads'`):
- `"Will the Boston Bruins cover -1.5 vs Buffalo Sabres?"` — spread_line = 1.5, direction depends on team
- `"Bruins -1.5"` (groupItemTitle)
- BUY_YES = favori (-1.5) cover, BUY_NO = underdog (+1.5) cover

**Totals** (`sportsMarketType='totals'`):
- `"Boston Bruins vs. Buffalo Sabres: O/U 5.5"` — total_line = 5.5
- `"O/U 6.5"` (groupItemTitle)
- YES = OVER, NO = UNDER (Polymarket konvansiyonu, NBA ile aynı)

**Bilinmeyen format → parser None döner → exit devre dışı** (güvenli default).

---

## Dosya Haritası

| İşlem | Dosya | Neden |
|---|---|---|
| CREATE | `scripts/build_nhl_puck_line_table.py` | Empirical -1.5 cover tablosu üret (one-shot script) |
| CREATE | `scripts/build_nhl_totals_table.py` | Empirical over/under tablosu üret (5.5 ve 6.5 için) |
| CREATE | `data/nhl_empirical_puck_line_table.json` | Build script çıktısı, gitignored runtime data değil |
| CREATE | `data/nhl_empirical_totals_table.json` | Build script çıktısı |
| CREATE | `src/domain/math/nhl_puck_line.py` | Skellam-based p_cover_minus_1_5() |
| CREATE | `src/domain/math/nhl_totals.py` | Skellam-based p_over() |
| CREATE | `src/domain/math/nhl_puck_line_probability.py` | Hibrit wrapper (empirical→Skellam fallback) |
| CREATE | `src/domain/math/nhl_totals_probability.py` | Hibrit wrapper |
| CREATE | `src/infrastructure/repositories/nhl_puck_line_repository.py` | @lru_cache load_table() |
| CREATE | `src/infrastructure/repositories/nhl_totals_repository.py` | @lru_cache load_table() |
| CREATE | `src/strategy/exit/nhl_puck_line_exit.py` | decide_nhl_puck_line_exit() priority chain |
| CREATE | `src/strategy/exit/nhl_totals_exit.py` | decide_nhl_totals_exit() priority chain |
| CREATE | `src/strategy/exit/_nhl_puck_line_dispatch.py` | check_nhl_puck_line_exit() — score_info → NHLSignal |
| CREATE | `src/strategy/exit/_nhl_totals_dispatch.py` | check_nhl_totals_exit() — score_info → NHLSignal |
| MODIFY | `src/domain/matching/market_line_parser.py` | NHL puck line parser pattern (NBA pattern genişletme) |
| MODIFY | `src/strategy/exit/_nhl_exit_mapping.py` | +5 yeni reason mapping (NHL_PUCK_LINE_*, NHL_TOTALS_*) |
| MODIFY | `src/models/enums.py` | +ExitReason: NHL_PUCK_LINE_* + NHL_TOTALS_* (5+5 değer) |
| MODIFY | `src/strategy/exit/nhl_score_exit.py` | NHLExitConfig'e puck_line + totals threshold alanları (veya ayrı config) |
| MODIFY | `src/config/settings.py` | EntryConfig'e nhl_puck_line + nhl_totals filter alanları; ExitNhlConfig veya yeni ExitNhlPuckLineConfig + ExitNhlTotalsConfig |
| MODIFY | `config.yaml` | entry + exit_nhl_puck_line + exit_nhl_totals yeni değerler |
| MODIFY | `src/strategy/entry/gate.py` | NHL puck_line/totals filter (NBA pattern paralel) |
| MODIFY | `src/strategy/exit/monitor.py` | NHL market_type routing (moneyline / puck_line / totals) |
| MODIFY | `src/orchestration/exit_processor.py` | nhl_puck_line_table + nhl_totals_table helpers; monitor evaluate çağrısı güncelle |
| MODIFY | `src/orchestration/agent.py` | AgentDeps +nhl_puck_line_table, +nhl_totals_table |
| MODIFY | `src/orchestration/factory.py` | _load_nhl_puck_line_table() + _load_nhl_totals_table() helpers; AgentDeps inject |
| MODIFY | `src/orchestration/scanner.py` | NHL için spreads/totals SMT'ye izin (NBA pattern paralel) |
| CREATE | `tests/unit/domain/math/test_nhl_puck_line.py` | Skellam math tests |
| CREATE | `tests/unit/domain/math/test_nhl_totals.py` | Skellam math tests |
| CREATE | `tests/unit/domain/math/test_nhl_puck_line_probability.py` | Hybrid wrapper tests |
| CREATE | `tests/unit/domain/math/test_nhl_totals_probability.py` | Hybrid wrapper tests |
| CREATE | `tests/unit/strategy/exit/test_nhl_puck_line_exit.py` | Exit decision tests |
| CREATE | `tests/unit/strategy/exit/test_nhl_totals_exit.py` | Exit decision tests |
| CREATE | `tests/unit/strategy/exit/test_nhl_puck_line_dispatch.py` | Dispatch wiring tests |
| CREATE | `tests/unit/strategy/exit/test_nhl_totals_dispatch.py` | Dispatch wiring tests |
| CREATE | `tests/integration/test_nhl_puck_line_pipeline_smoke.py` | E2E smoke |
| CREATE | `tests/integration/test_nhl_totals_pipeline_smoke.py` | E2E smoke |
| MODIFY | `DECISIONS.md` | NHL Puck Line + NHL Totals bölümleri |

---

## ARCH Self-Check (her task öncesi yaz)

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

---

# TASK 6: NHL Puck Line

## Task 6A: Empirical Puck Line Table Builder

**Files:**
- Create: `scripts/build_nhl_puck_line_table.py`
- Output: `data/nhl_empirical_puck_line_table.json`

**Inputs:** `data/nhl_shots/shots_2022.csv`, `shots_2023.csv`, `shots_2024.csv` (mevcut)

**Mantık:** Her tick için (period, seconds_remaining, current_margin) → "favori son skorda -1.5'i kapattı mı?" empirical olasılığı. Build script `reconstruct_game_states()` mantığını mevcut `build_nhl_empirical_table.py`'dan ödünç alır + final_margin_at_resolve hesabı ekler.

- [ ] **Step 1: Script iskeleti — header, args, helpers**

`scripts/build_nhl_puck_line_table.py` (yeni dosya, ~250 satır beklenen):

```python
#!/usr/bin/env python3
"""
scripts/build_nhl_puck_line_table.py

MoneyPuck shot-level play-by-play (data/nhl_shots/) →
NHL empirical puck line cover probability lookup table.

Standalone, tek seferlik çalışır. src/ koduna dokunmaz.
Çıktı: data/nhl_empirical_puck_line_table.json

Kullanım:
    python scripts/build_nhl_puck_line_table.py
    python scripts/build_nhl_puck_line_table.py --seasons 2022 2023 2024

Spread line: -1.5 (Polymarket standart). +2.5 alternate atlandı (Karar 1).
SO resolution: winner +1 gol → puck line resolve includes OT/SO (Karar 3).

Key format: "period_currentMargin_secondsRemaining" → {p_favorite_covers, ci_low, ci_high, n_games}
Margin sign convention: favori bakış açısı.
  current_margin > 0 → favori önde
  current_margin < 0 → favori geride
  current_margin = 0 → berabere
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_SEASONS: list[int] = [2022, 2023, 2024]
_DATA_DIR = Path("data/nhl_shots")
_OUTPUT_PATH = Path("data/nhl_empirical_puck_line_table.json")

_TIME_BUCKET_SEC: int = 30
_MARGIN_CAP: int = 5     # |margin| > 5 → bucket 5 (rare, blowout)
_REGULATION_SECONDS: int = 3600
_Z: float = 1.96
_MIN_N: int = 30
_PUCK_LINE: float = 1.5  # Standart Polymarket NHL puck line

_NEEDED_COLS = [
    "game_id", "period", "time",
    "homeTeamGoals", "awayTeamGoals",
    "homeTeamWon", "goal", "isPlayoffGame",
]
```

- [ ] **Step 2: load_shots_csv + reconstruct helpers — mevcut script'ten ödünç al**

```python
def load_shots_csv(csv_path: Path, season_label: str) -> pd.DataFrame:
    """Aynı pattern src/scripts/build_nhl_empirical_table.py'da."""
    df = pd.read_csv(csv_path, usecols=_NEEDED_COLS, low_memory=False)
    df = df.dropna(subset=["game_id", "period", "time", "homeTeamWon"])
    df = df.astype({
        "game_id": str, "period": int, "time": float,
        "homeTeamGoals": int, "awayTeamGoals": int,
        "homeTeamWon": int, "goal": int, "isPlayoffGame": int,
    })
    df["game_id"] = season_label + "_" + df["game_id"]
    df["season"] = season_label
    return df


def determine_favorite(shots_df: pd.DataFrame) -> dict[str, str]:
    """Per-game favori belirle: en çok beraberlikten çıkış skorunu yapan = favori.

    Bu MoneyPuck data'sında doğrudan yok (line gerçek bahis line'ı, simülasyon edemiyoruz).
    Heuristik: home advantage nedeniyle home favori varsayalım (NHL'de home WP ~%55).

    NOT: Gerçek bahis için Pinnacle line'ı kullanılır (run-time'da).
    Build script'te sadece "favori = home" varsayımı (empirical tabloyu unbias için
    deficit-symmetric şekilde de saklayabiliriz; kararı Step 4'te ver).
    """
    return {gid: "home" for gid in shots_df["game_id"].unique()}
```

- [ ] **Step 3: reconstruct_game_states_with_final_margin**

```python
def reconstruct_game_states_with_final_margin(shots_df: pd.DataFrame) -> pd.DataFrame:
    """30sn tick'ler + her oyunun final marjı (regulation + OT goal varsa + SO winner +1).

    Final margin convention:
      home_won=1, ended in regulation diff=2 → final_margin=2 (home perspective)
      home_won=1, ended in OT regulation tied diff=0 → final_margin=1 (OT goal +1)
      home_won=1, ended in SO regulation tied diff=0 → final_margin=1 (SO winner +1)
      home_won=0 → negate

    SO/OT detection: shots_df last_period.
      last_period=3 → regulation finish
      last_period=4 → OT goal (margin = home_final - away_final from data)
      last_period=5 → SO (margin = winner +1, since regulation tied)
    """
    reg = shots_df[shots_df["period"].isin([1, 2, 3])].copy()
    reg["game_seconds"] = reg["time"]
    reg = reg.sort_values(["game_id", "game_seconds"]).reset_index(drop=True)

    # Per-game final scores from full data (including OT/SO)
    game_finals = shots_df.groupby("game_id").agg(
        last_period=("period", "max"),
        home_final=("homeTeamGoals", "max"),
        away_final=("awayTeamGoals", "max"),
        home_won=("homeTeamWon", "first"),
    ).to_dict("index")

    def compute_final_margin(gid: str) -> int:
        info = game_finals[gid]
        last_period = info["last_period"]
        home_final = info["home_final"]
        away_final = info["away_final"]
        home_won = info["home_won"]

        # Regulation veya OT goal — direct skor farkı
        if last_period <= 4:
            return int(home_final - away_final)
        # SO: regulation tied, winner +1 (Karar 3)
        return 1 if home_won else -1

    final_margins = {gid: compute_final_margin(gid) for gid in game_finals}

    # Tick reconstruction (mevcut pattern)
    tick_times = np.arange(0.0, _REGULATION_SECONDS + _TIME_BUCKET_SEC, _TIME_BUCKET_SEC)
    sec_rem_ticks = (_REGULATION_SECONDS - tick_times).astype(int)
    period_ticks = np.minimum((tick_times // 1200).astype(int) + 1, 3)

    chunks: list[pd.DataFrame] = []
    for gid, gdf in reg.groupby("game_id", sort=False):
        times = gdf["game_seconds"].values
        home_goals = gdf["homeTeamGoals"].values
        away_goals = gdf["awayTeamGoals"].values

        idxs = np.searchsorted(times, tick_times, side="right") - 1
        valid = idxs >= 0
        home = np.where(valid, home_goals[np.where(valid, idxs, 0)], 0)
        away = np.where(valid, away_goals[np.where(valid, idxs, 0)], 0)

        # current_margin = home - away (home favori varsayımı, Step 2 notu)
        current_margin = (home - away).astype(int)
        final_margin = np.full_like(current_margin, final_margins[gid])

        chunks.append(pd.DataFrame({
            "game_id": gid,
            "period": period_ticks,
            "seconds_remaining": sec_rem_ticks,
            "current_margin": current_margin,
            "final_margin": final_margin,
        }))

    return pd.concat(chunks, ignore_index=True)
```

- [ ] **Step 4: aggregate_puck_line_cover — empirical p_cover hesabı**

```python
def aggregate_puck_line_cover(states_df: pd.DataFrame, puck_line: float = _PUCK_LINE) -> dict:
    """Her (period, current_margin_clamped, seconds) bucket için home -puck_line cover olasılığı.

    Cover condition: final_margin >= puck_line + 1 (line .5 olduğu için >= 2 gol fark)
    Polymarket -1.5 favori cover: final_margin >= 2

    Wilson CI 95%, min_sample=30.
    """
    df = states_df.copy()
    df["current_margin_clamped"] = df["current_margin"].clip(
        lower=-_MARGIN_CAP, upper=_MARGIN_CAP
    ).astype(int)
    df["time_bucket"] = ((df["seconds_remaining"] // _TIME_BUCKET_SEC) * _TIME_BUCKET_SEC).astype(int)

    # Cover bool: final margin favoriyi -1.5'i geçirdi mi
    cover_threshold = int(puck_line + 0.5)  # 1.5 → 2 (>=2 cover)
    df["covered"] = (df["final_margin"] >= cover_threshold).astype(int)

    grouped = (
        df.groupby(["period", "current_margin_clamped", "time_bucket"], sort=True)
        ["covered"]
        .agg(covers="sum", n="count")
        .reset_index()
    )

    z2 = _Z ** 2
    table: dict[str, dict | None] = {}

    for row in grouped.itertuples(index=False):
        period = int(row.period)
        margin = int(row.current_margin_clamped)
        seconds = int(row.time_bucket)
        covers = float(row.covers)
        n = int(row.n)
        key = f"{period}_{margin}_{seconds}"

        if n < _MIN_N:
            table[key] = None
            continue

        p_hat = covers / n
        centre = (p_hat + z2 / (2 * n)) / (1 + z2 / n)
        margin_w = (_Z / (1 + z2 / n)) * math.sqrt(
            p_hat * (1 - p_hat) / n + z2 / (4 * n ** 2)
        )
        table[key] = {
            "p_favorite_covers": round(centre, 4),
            "ci_low": round(max(0.0, centre - margin_w), 4),
            "ci_high": round(min(1.0, centre + margin_w), 4),
            "n_games": n,
        }

    return table
```

- [ ] **Step 5: main() + sanity print + JSON write**

```python
def print_sanity_summary(table: dict) -> None:
    checkpoints = [
        ("3_3_1200", "+3 lead, P3 start"),
        ("3_2_1200", "+2 lead, P3 start"),
        ("3_1_1200", "+1 lead, P3 start"),
        ("3_0_1200", "tied, P3 start"),
        ("3_-1_1200", "-1 deficit, P3 start"),
        ("3_2_300",  "+2 lead, last 5 min"),
        ("3_1_300",  "+1 lead, last 5 min"),
        ("3_2_60",   "+2 lead, last 60s"),
    ]
    print("\n-- PUCK LINE -1.5 SANITY CHECK " + "-" * 38)
    print(f"{'Label':35s}  {'p_cover':>8s}  {'n':>5s}  CI")
    print("-" * 70)
    for key, label in checkpoints:
        entry = table.get(key)
        if entry:
            print(
                f"{label:35s}  {entry['p_favorite_covers']*100:6.1f}%  "
                f"{entry['n_games']:5d}  "
                f"[{entry['ci_low']*100:.1f}, {entry['ci_high']*100:.1f}]"
            )
        else:
            print(f"{label:35s}  NO_DATA")
    print("-" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NHL puck line empirical table")
    parser.add_argument("--seasons", type=int, nargs="+", default=_DEFAULT_SEASONS)
    parser.add_argument("--output", type=Path, default=_OUTPUT_PATH)
    args = parser.parse_args()

    dfs: list[pd.DataFrame] = []
    for season_start in args.seasons:
        season_label = f"{season_start}-{season_start+1-2000:02d}"
        csv_path = _DATA_DIR / f"shots_{season_start}.csv"
        if not csv_path.exists():
            logger.error("Missing %s — run build_nhl_empirical_table.py first to download.", csv_path)
            return
        df = load_shots_csv(csv_path, season_label)
        logger.info("Loaded %s: %d rows, %d games", season_label, len(df), df["game_id"].nunique())
        dfs.append(df)

    all_shots = pd.concat(dfs, ignore_index=True)
    states = reconstruct_game_states_with_final_margin(all_shots)
    table = aggregate_puck_line_cover(states, puck_line=_PUCK_LINE)

    metadata = {
        "seasons": args.seasons,
        "time_bucket_sec": _TIME_BUCKET_SEC,
        "margin_cap": _MARGIN_CAP,
        "puck_line": _PUCK_LINE,
        "min_sample_size": _MIN_N,
        "wilson_z": _Z,
        "total_games": all_shots["game_id"].nunique(),
        "favorite_assumption": "home (heuristic; runtime uses Pinnacle line)",
        "key_format": "period_currentMargin_secondsRemaining",
    }

    output = {"metadata": metadata, "puck_line_cover": table}
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info("Wrote %s (%d entries)", args.output, len(table))

    print_sanity_summary(table)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Build et, sanity check**

```bash
python scripts/build_nhl_puck_line_table.py
```

Beklenen sanity output:
- `+1 lead, P3 start` → ~%48-58 cover (1 gol önde, kapatma için 1+ gol gerekir)
- `+3 lead, P3 start` → ~%85-92 cover (zaten kapatmış)
- `tied, P3 start` → ~%30-40 cover (favori 2+ atmalı)

- [ ] **Step 7: Commit**

```bash
git add scripts/build_nhl_puck_line_table.py data/nhl_empirical_puck_line_table.json
git commit -m "feat(nhl): empirical puck line table builder + 4198-game lookup"
```

---

## Task 6B: NHL Puck Line Math (Skellam Fallback)

**Files:**
- Create: `src/domain/math/nhl_puck_line.py`
- Test: `tests/unit/domain/math/test_nhl_puck_line.py`

**Mantık:** Skellam dağılımı (iki Poisson farkı) — kalan sürede home-away skor farkı değişimi. P(final_margin >= 2 | current_margin) = P(diff_change >= 2 - current_margin).

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test yaz**

`tests/unit/domain/math/test_nhl_puck_line.py`:

```python
"""Skellam-based puck line cover probability tests."""
from __future__ import annotations

import pytest

from src.domain.math.nhl_puck_line import skellam_p_favorite_covers_minus_1_5


class TestSkellamPCovers:
    def test_already_covered_returns_high_prob(self):
        """+3 lead, P3 start → favori zaten -1.5'i geçti, %90+ cover."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=3, seconds_remaining=1200)
        assert p > 0.85

    def test_tied_at_p3_start(self):
        """0 lead, P3 start → favori 2+ atmalı, çok zor."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=0, seconds_remaining=1200)
        assert 0.10 < p < 0.30

    def test_one_goal_lead_p3_late(self):
        """+1 lead, son 60s → 1 gol farkı kalır → SO/OT olasılığı yüksek, cover düşük."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=1, seconds_remaining=60)
        assert 0.10 < p < 0.40

    def test_two_goal_lead_p3_late(self):
        """+2 lead, son 60s → cover olmuş gibi, %85+ kalan."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=2, seconds_remaining=60)
        assert p > 0.85

    def test_negative_margin_low_prob(self):
        """-1 deficit, P3 ortası → cover için 3+ farklı çevirmeli, çok düşük."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=-1, seconds_remaining=600)
        assert p < 0.10

    def test_zero_seconds_remaining_returns_actual(self):
        """Süre bitti, current_margin >= 2 → 1.0, değilse → 0.0."""
        assert skellam_p_favorite_covers_minus_1_5(current_margin=2, seconds_remaining=0) == 1.0
        assert skellam_p_favorite_covers_minus_1_5(current_margin=1, seconds_remaining=0) == 0.0
        assert skellam_p_favorite_covers_minus_1_5(current_margin=3, seconds_remaining=0) == 1.0

    def test_full_game_remaining_balanced(self):
        """3600 sec kala, current_margin=0 → ~%30-40 cover (favori avantajı + zaman)."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=0, seconds_remaining=3600)
        assert 0.20 < p < 0.45
```

- [ ] **Step 2: Test'i çalıştır, FAIL beklenen**

```bash
pytest tests/unit/domain/math/test_nhl_puck_line.py -v
```
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement nhl_puck_line.py**

`src/domain/math/nhl_puck_line.py`:

```python
"""NHL puck line (-1.5) cover probability via Skellam distribution.

Skellam = difference of two independent Poisson random variables.
Home goals ~ Poisson(λ_home × t), Away goals ~ Poisson(λ_away × t)
diff_change = home_new - away_new ~ Skellam(μ1=λ_home×t, μ2=λ_away×t)

Cover condition: final_margin >= 2 (Polymarket -1.5 favori convention).
final_margin = current_margin + diff_change → diff_change >= 2 - current_margin

P(cover) = P(Skellam(μ1, μ2) >= 2 - current_margin)
        = 1 - skellam.cdf(2 - current_margin - 1, μ1, μ2)
        = 1 - skellam.cdf(1 - current_margin, μ1, μ2)

NHL league avg: 6.142 gol/maç → per-team-per-second:
  λ_per_team = 6.142 / 2 / 3600 = 0.000853 (5v5 avg)
"""
from __future__ import annotations

from scipy.stats import skellam

# Per-team scoring rate (5v5 average, league avg 2026)
LAMBDA_5V5_PER_TEAM_PER_SECOND: float = 0.000853

# Empty net modifier — last 3 min + 1 goal deficit, λ ×1.8 (geri dönmeye çalışan takım)
LAMBDA_EMPTY_NET_MULT: float = 1.8


def skellam_p_favorite_covers_minus_1_5(
    current_margin: int,
    seconds_remaining: int,
    lambda_home: float = LAMBDA_5V5_PER_TEAM_PER_SECOND,
    lambda_away: float = LAMBDA_5V5_PER_TEAM_PER_SECOND,
) -> float:
    """P(home favori final_margin >= 2 | current_margin, seconds_remaining).

    Args:
      current_margin: home_score - away_score (favori bakış açısı)
      seconds_remaining: regulation kalan saniye (OT/SO ayrı handle)
      lambda_home/away: per-second per-team scoring rate

    Returns:
      Cover olasılığı [0, 1].
    """
    if seconds_remaining <= 0:
        return 1.0 if current_margin >= 2 else 0.0

    mu_home = lambda_home * seconds_remaining
    mu_away = lambda_away * seconds_remaining

    threshold = 2 - current_margin  # diff_change >= threshold için cover
    # P(X >= threshold) = 1 - P(X <= threshold - 1) = 1 - cdf(threshold - 1)
    p = 1.0 - skellam.cdf(threshold - 1, mu_home, mu_away)
    return float(max(0.0, min(1.0, p)))
```

- [ ] **Step 4: Test'i çalıştır, PASS bekle**

```bash
pytest tests/unit/domain/math/test_nhl_puck_line.py -v
```
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/domain/math/nhl_puck_line.py tests/unit/domain/math/test_nhl_puck_line.py
git commit -m "feat(nhl): skellam-based puck line cover probability (-1.5)"
```

---

## Task 6C: NHL Puck Line Repository (table loader)

**Files:**
- Create: `src/infrastructure/repositories/nhl_puck_line_repository.py`
- Test: `tests/unit/infrastructure/repositories/test_nhl_puck_line_repository.py`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test**

`tests/unit/infrastructure/repositories/test_nhl_puck_line_repository.py`:

```python
"""NHL puck line table loader tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.infrastructure.repositories import nhl_puck_line_repository as repo


def test_load_table_returns_dict(tmp_path, monkeypatch):
    """Table file varsa dict döner."""
    fake_table = {
        "metadata": {"total_games": 100},
        "puck_line_cover": {"3_1_300": {"p_favorite_covers": 0.42, "n_games": 80}},
    }
    fake_path = tmp_path / "nhl_empirical_puck_line_table.json"
    fake_path.write_text(json.dumps(fake_table), encoding="utf-8")
    monkeypatch.setattr(repo, "TABLE_PATH", fake_path)
    repo.load_table.cache_clear()

    result = repo.load_table()
    assert "puck_line_cover" in result
    assert result["puck_line_cover"]["3_1_300"]["p_favorite_covers"] == 0.42


def test_load_table_raises_when_missing(monkeypatch, tmp_path):
    """Dosya yoksa FileNotFoundError."""
    monkeypatch.setattr(repo, "TABLE_PATH", tmp_path / "nonexistent.json")
    repo.load_table.cache_clear()
    with pytest.raises(FileNotFoundError):
        repo.load_table()
```

- [ ] **Step 2: Implement**

`src/infrastructure/repositories/nhl_puck_line_repository.py`:

```python
"""NHL empirical puck line cover probability table loader.

Build the table first: python scripts/build_nhl_puck_line_table.py
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

TABLE_PATH: Path = Path("data/nhl_empirical_puck_line_table.json")


@lru_cache(maxsize=1)
def load_table() -> dict:
    """Load + cache NHL puck line cover lookup table from disk."""
    if not TABLE_PATH.exists():
        raise FileNotFoundError(
            f"Empirical puck line table not found at {TABLE_PATH}. "
            "Run scripts/build_nhl_puck_line_table.py first."
        )
    with open(TABLE_PATH, encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **Step 3: Test → PASS**

```bash
pytest tests/unit/infrastructure/repositories/test_nhl_puck_line_repository.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/infrastructure/repositories/nhl_puck_line_repository.py tests/unit/infrastructure/repositories/test_nhl_puck_line_repository.py
git commit -m "feat(nhl): puck line empirical table repository (lru_cache)"
```

---

## Task 6D: NHL Puck Line Hybrid Wrapper

**Files:**
- Create: `src/domain/math/nhl_puck_line_probability.py`
- Test: `tests/unit/domain/math/test_nhl_puck_line_probability.py`

**Mantık:** Empirical first, Skellam fallback. Tablo `(period, current_margin_clamped, time_bucket)` lookup, eksik → Skellam.

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test**

`tests/unit/domain/math/test_nhl_puck_line_probability.py`:

```python
"""Hybrid puck line probability wrapper tests."""
from __future__ import annotations

from src.domain.math.nhl_puck_line_probability import p_favorite_covers_hybrid


_FAKE_TABLE = {
    "puck_line_cover": {
        "3_1_300": {"p_favorite_covers": 0.55, "n_games": 200, "ci_low": 0.50, "ci_high": 0.60},
        "3_-2_600": None,  # insufficient sample
    }
}


def test_uses_empirical_when_available():
    """Empirical entry varsa onu döner, source='empirical'."""
    p, src = p_favorite_covers_hybrid(period=3, current_margin=1, seconds_remaining=300, table=_FAKE_TABLE)
    assert p == 0.55
    assert src == "empirical"


def test_falls_back_to_skellam_when_table_missing(monkeypatch):
    """Tablo entry yok → Skellam fallback."""
    p, src = p_favorite_covers_hybrid(period=3, current_margin=1, seconds_remaining=999, table=_FAKE_TABLE)
    assert 0.0 <= p <= 1.0
    assert src == "skellam_fallback"


def test_falls_back_when_table_entry_is_none():
    """Tablo entry None (insufficient sample) → Skellam fallback."""
    p, src = p_favorite_covers_hybrid(period=3, current_margin=-2, seconds_remaining=600, table=_FAKE_TABLE)
    assert 0.0 <= p <= 1.0
    assert src == "skellam_fallback"


def test_seconds_bucketed_to_30s():
    """seconds=315 → bucket 300 (table key match)."""
    p, src = p_favorite_covers_hybrid(period=3, current_margin=1, seconds_remaining=315, table=_FAKE_TABLE)
    assert p == 0.55
    assert src == "empirical"


def test_margin_clamped_to_5(monkeypatch):
    """|margin| > 5 → clamped to 5/-5."""
    table = {"puck_line_cover": {"3_5_600": {"p_favorite_covers": 0.95, "n_games": 50}}}
    p, src = p_favorite_covers_hybrid(period=3, current_margin=8, seconds_remaining=600, table=table)
    assert src == "empirical"
    assert p == 0.95
```

- [ ] **Step 2: Test FAIL**

```bash
pytest tests/unit/domain/math/test_nhl_puck_line_probability.py -v
```

- [ ] **Step 3: Implement**

`src/domain/math/nhl_puck_line_probability.py`:

```python
"""Hybrid puck line cover probability — empirical first, Skellam fallback.

Caller pattern:
    table = load_table()  # from infrastructure.repositories.nhl_puck_line_repository
    p, source = p_favorite_covers_hybrid(period, margin, seconds, table=table)
"""
from __future__ import annotations

from src.domain.math.nhl_puck_line import skellam_p_favorite_covers_minus_1_5

_TIME_BUCKET_SEC: int = 30
_MARGIN_CAP: int = 5


def p_favorite_covers_hybrid(
    period: int,
    current_margin: int,
    seconds_remaining: int,
    *,
    table: dict,
) -> tuple[float, str]:
    """P(home favori -1.5 cover) — empirical→Skellam hybrid.

    Returns:
        (probability, source) where source in {"empirical", "skellam_fallback"}.
    """
    margin_clamped = max(-_MARGIN_CAP, min(_MARGIN_CAP, current_margin))
    time_bucket = (seconds_remaining // _TIME_BUCKET_SEC) * _TIME_BUCKET_SEC
    key = f"{period}_{margin_clamped}_{time_bucket}"

    cover_table = table.get("puck_line_cover", {})
    entry = cover_table.get(key)
    if entry is not None and "p_favorite_covers" in entry:
        return float(entry["p_favorite_covers"]), "empirical"

    p = skellam_p_favorite_covers_minus_1_5(current_margin, seconds_remaining)
    return p, "skellam_fallback"
```

- [ ] **Step 4: Test → PASS, Commit**

```bash
pytest tests/unit/domain/math/test_nhl_puck_line_probability.py -v
git add src/domain/math/nhl_puck_line_probability.py tests/unit/domain/math/test_nhl_puck_line_probability.py
git commit -m "feat(nhl): hybrid puck line probability wrapper (empirical→skellam)"
```

---

## Task 6E: NHL Puck Line Exit Logic — Pure Decision

**Files:**
- Create: `src/strategy/exit/nhl_puck_line_exit.py`
- Test: `tests/unit/strategy/exit/test_nhl_puck_line_exit.py`

**Mantık:** `decide_nhl_exit` (Task 3A) pattern paralel. Priority chain:
1. NEAR_RESOLVE (bid >= 0.94) → SELL_ALL
2. SCALE_OUT (bid >= 0.85, ilk kez) → SELL_50
3. PREDICTIVE_DEAD (p_cover < bid + 0.03) → SELL_ALL
4. STRUCTURAL_DAMAGE (current_price/entry < 0.30) → SELL_ALL
5. HOLD

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test**

`tests/unit/strategy/exit/test_nhl_puck_line_exit.py`:

```python
"""NHL puck line exit decision tests — pure function, no I/O."""
from __future__ import annotations

import dataclasses

import pytest

from src.strategy.exit.nhl_puck_line_exit import (
    ExitAction,
    ExitReason,
    NHLPuckLineExitConfig,
    decide_nhl_puck_line_exit,
)


def _decide(**overrides):
    defaults = dict(
        cfg=NHLPuckLineExitConfig(),
        entry_price=0.45,
        current_bid=0.50,
        current_price=0.52,
        scaled_out_50=False,
        period=3,
        seconds_remaining=600,
        current_margin=1,
        p_cover_fn=lambda p, m, s: (0.55, "empirical"),
    )
    defaults.update(overrides)
    return decide_nhl_puck_line_exit(**defaults)


class TestNearResolve:
    def test_near_resolve_fires(self):
        d = _decide(current_bid=0.94)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.NEAR_RESOLVE

    def test_near_resolve_below_threshold_no_fire(self):
        d = _decide(current_bid=0.93)
        assert d.reason != ExitReason.NEAR_RESOLVE


class TestScaleOut:
    def test_scale_out_fires(self):
        d = _decide(current_bid=0.85, scaled_out_50=False)
        assert d.action == ExitAction.SELL_50
        assert d.reason == ExitReason.SCALE_OUT

    def test_scale_out_skipped_if_already_scaled(self):
        d = _decide(current_bid=0.87, scaled_out_50=True)
        assert d.reason != ExitReason.SCALE_OUT


class TestPredictiveDead:
    def test_predictive_dead_fires_when_p_cover_low(self):
        d = _decide(p_cover_fn=lambda p, m, s: (0.10, "skellam_fallback"), current_bid=0.20)
        assert d.reason == ExitReason.PREDICTIVE_DEAD
        assert d.p_cover == pytest.approx(0.10)

    def test_predictive_dead_does_not_fire_when_high(self):
        d = _decide(p_cover_fn=lambda p, m, s: (0.50, "empirical"), current_bid=0.30)
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_predictive_dead_skipped_when_fn_raises(self):
        def raising(p, m, s):
            raise RuntimeError("table miss")
        d = _decide(p_cover_fn=raising)
        assert d.reason != ExitReason.PREDICTIVE_DEAD


class TestStructuralDamage:
    def test_structural_damage_fires_when_price_collapsed(self):
        d = _decide(entry_price=0.60, current_price=0.10, current_bid=0.50)
        assert d.reason == ExitReason.STRUCTURAL_DAMAGE
        assert d.action == ExitAction.SELL_ALL

    def test_structural_damage_does_not_fire_above_ratio(self):
        d = _decide(entry_price=0.60, current_price=0.25)
        assert d.reason != ExitReason.STRUCTURAL_DAMAGE


class TestHold:
    def test_hold_default(self):
        d = _decide()
        assert d.action == ExitAction.HOLD
        assert d.reason == ExitReason.HOLD


class TestPriorityOrder:
    def test_near_resolve_beats_scale_out(self):
        d = _decide(current_bid=0.95, scaled_out_50=False)
        assert d.reason == ExitReason.NEAR_RESOLVE

    def test_scale_out_beats_predictive_dead(self):
        d = _decide(current_bid=0.86, scaled_out_50=False, p_cover_fn=lambda p,m,s: (0.05, "x"))
        assert d.reason == ExitReason.SCALE_OUT


class TestEdgeCases:
    def test_zero_entry_price_does_not_crash(self):
        d = _decide(entry_price=0.0)
        assert d.reason == ExitReason.HOLD

    def test_frozen_decision_is_immutable(self):
        d = _decide()
        with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
            d.action = ExitAction.SELL_ALL
```

- [ ] **Step 2: Test FAIL**

```bash
pytest tests/unit/strategy/exit/test_nhl_puck_line_exit.py -v
```

- [ ] **Step 3: Implement**

`src/strategy/exit/nhl_puck_line_exit.py`:

```python
"""NHL puck line (-1.5) exit logic — priority-chain pure function."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class ExitAction(str, Enum):
    HOLD = "HOLD"
    SELL_50 = "SELL_50"
    SELL_ALL = "SELL_ALL"


class ExitReason(str, Enum):
    NEAR_RESOLVE = "NEAR_RESOLVE"
    SCALE_OUT = "SCALE_OUT"
    PREDICTIVE_DEAD = "PREDICTIVE_DEAD"
    STRUCTURAL_DAMAGE = "STRUCTURAL_DAMAGE"
    HOLD = "HOLD"


@dataclass(frozen=True)
class NHLPuckLineExitDecision:
    action: ExitAction
    reason: ExitReason
    p_cover: float | None
    p_cover_source: str
    note: str


@dataclass(frozen=True)
class NHLPuckLineExitConfig:
    near_resolve_threshold: float = 0.94
    scale_out_threshold: float = 0.85
    structural_damage_ratio: float = 0.30
    predictive_safety_margin: float = 0.03


def decide_nhl_puck_line_exit(
    *,
    cfg: NHLPuckLineExitConfig,
    entry_price: float,
    current_bid: float,
    current_price: float,
    scaled_out_50: bool,
    period: int,
    seconds_remaining: int,
    current_margin: int,
    p_cover_fn: Callable[[int, int, int], tuple[float, str]],
) -> NHLPuckLineExitDecision:
    """NHL puck line (-1.5) exit kararı — priority chain.

    p_cover_fn signature: (period, current_margin, seconds_remaining) -> (p, source)
    Exception → p_cover=None, PREDICTIVE_DEAD skip.
    """
    # 1. NEAR_RESOLVE
    if current_bid >= cfg.near_resolve_threshold:
        return NHLPuckLineExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.NEAR_RESOLVE,
            p_cover=1.0,
            p_cover_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # 2. SCALE_OUT
    if not scaled_out_50 and current_bid >= cfg.scale_out_threshold:
        return NHLPuckLineExitDecision(
            action=ExitAction.SELL_50,
            reason=ExitReason.SCALE_OUT,
            p_cover=current_bid,
            p_cover_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # 3. PREDICTIVE_DEAD
    try:
        p_cover, p_cover_source = p_cover_fn(period, current_margin, seconds_remaining)
    except Exception:
        p_cover = None
        p_cover_source = "error"

    if p_cover is not None and p_cover < (current_bid + cfg.predictive_safety_margin):
        return NHLPuckLineExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.PREDICTIVE_DEAD,
            p_cover=p_cover,
            p_cover_source=p_cover_source,
            note=f"p_cover={p_cover:.3f} bid={current_bid:.3f}",
        )

    # 4. STRUCTURAL_DAMAGE
    if entry_price > 0 and (current_price / entry_price) < cfg.structural_damage_ratio:
        return NHLPuckLineExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.STRUCTURAL_DAMAGE,
            p_cover=p_cover,
            p_cover_source=p_cover_source,
            note=f"ratio={current_price/entry_price:.2f}",
        )

    # 5. HOLD
    return NHLPuckLineExitDecision(
        action=ExitAction.HOLD,
        reason=ExitReason.HOLD,
        p_cover=p_cover,
        p_cover_source=p_cover_source,
        note="",
    )
```

- [ ] **Step 4: Test → PASS**

```bash
pytest tests/unit/strategy/exit/test_nhl_puck_line_exit.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/strategy/exit/nhl_puck_line_exit.py tests/unit/strategy/exit/test_nhl_puck_line_exit.py
git commit -m "feat(nhl): puck line exit decision — priority chain pure function"
```

---

## Task 6F: NHL Puck Line Question Parser

**Files:**
- Modify: `src/domain/matching/market_line_parser.py`
- Test: extend `tests/unit/domain/matching/test_market_line_parser.py` (mevcut)

**Mantık:** NBA pattern (`"Spread: Lakers (-5.5)"`) NHL'de farklı format kullanabilir (`"Will Bruins cover -1.5?"`). Test ile gerçek Polymarket örnekleri çıkar; mevcut `_SPREAD_RE` parantez içi pattern'i muhtemelen yeterli ama NHL için ekstra pattern olabilir.

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test ekle**

`tests/unit/domain/matching/test_market_line_parser.py`'ye yeni test class:

```python
class TestNHLPuckLine:
    def test_parses_will_team_cover_pattern(self):
        from src.domain.matching.market_line_parser import parse_spread_line
        assert parse_spread_line("Will the Boston Bruins cover -1.5 vs Buffalo Sabres?") == 1.5

    def test_parses_simple_minus_pattern(self):
        from src.domain.matching.market_line_parser import parse_spread_line
        assert parse_spread_line("Bruins -1.5") == 1.5

    def test_parses_plus_underdog(self):
        from src.domain.matching.market_line_parser import parse_spread_line
        assert parse_spread_line("Sabres +1.5") == 1.5

    def test_returns_none_for_unparsable(self):
        from src.domain.matching.market_line_parser import parse_spread_line
        assert parse_spread_line("Bruins vs Sabres") is None
```

- [ ] **Step 2: Test çalıştır**

```bash
pytest tests/unit/domain/matching/test_market_line_parser.py::TestNHLPuckLine -v
```

İlk 3 test PASS olabilir (mevcut `_SPREAD_RE` parantez içi sayı arar — `-1.5` parantez yoksa fail). FAIL olanlar için pattern genişlet.

- [ ] **Step 3: Pattern güncelle**

`src/domain/matching/market_line_parser.py` `_SPREAD_RE` yanına ek regex:

```python
# NHL puck line: "Bruins -1.5" / "Bruins +1.5" / "cover -1.5" — parantez yok
_SPREAD_NO_PAREN_RE = re.compile(r'(?:cover\s+)?[+-](\d{1,2}(?:\.\d)?)\b')


def parse_spread_line(question: str) -> float | None:
    """Spread line'ı parçalar.

    NBA: "Spread: Lakers (-5.5)" → 5.5
    NHL: "Bruins -1.5" → 1.5; "Will Bruins cover -1.5 vs..." → 1.5
    """
    m = _SPREAD_RE.search(question)
    if m:
        return float(m.group(1))
    m2 = _SPREAD_NO_PAREN_RE.search(question)
    if m2:
        return float(m2.group(1))
    return None
```

- [ ] **Step 4: Test → PASS, Commit**

```bash
pytest tests/unit/domain/matching/test_market_line_parser.py -v
git add src/domain/matching/market_line_parser.py tests/unit/domain/matching/test_market_line_parser.py
git commit -m "feat(nhl): puck line parser pattern (no parens, cover keyword)"
```

---

## Task 6G: ExitReason Enum + Mapping Genişletme

**Files:**
- Modify: `src/models/enums.py`
- Modify: `src/strategy/exit/_nhl_exit_mapping.py`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: ExitReason'a 5 yeni değer ekle**

`src/models/enums.py` ExitReason class'ına ekle:

```python
NHL_PUCK_LINE_NEAR_RESOLVE = "nhl_puck_line_near_resolve"
NHL_PUCK_LINE_SCALE_OUT = "nhl_puck_line_scale_out"
NHL_PUCK_LINE_PREDICTIVE_DEAD = "nhl_puck_line_predictive_dead"
NHL_PUCK_LINE_STRUCTURAL_DAMAGE = "nhl_puck_line_structural_damage"
NHL_PUCK_LINE_HOLD = "nhl_puck_line_hold"  # opsiyonel, monitor None döner
```

- [ ] **Step 2: _nhl_exit_mapping.py'a puck line mapper ekle**

`src/strategy/exit/_nhl_exit_mapping.py` (mevcut dosya, yeni fonksiyon ekle):

```python
from src.strategy.exit.nhl_puck_line_exit import (
    NHLPuckLineExitDecision,
    ExitAction as PLExitAction,
    ExitReason as PLExitReason,
)

_PUCK_LINE_REASON_MAP = {
    PLExitReason.NEAR_RESOLVE: ExitReason.NHL_PUCK_LINE_NEAR_RESOLVE,
    PLExitReason.SCALE_OUT: ExitReason.NHL_PUCK_LINE_SCALE_OUT,
    PLExitReason.PREDICTIVE_DEAD: ExitReason.NHL_PUCK_LINE_PREDICTIVE_DEAD,
    PLExitReason.STRUCTURAL_DAMAGE: ExitReason.NHL_PUCK_LINE_STRUCTURAL_DAMAGE,
}


def map_nhl_puck_line_decision(decision: NHLPuckLineExitDecision) -> NHLSignal | None:
    if decision.action == PLExitAction.HOLD:
        return None
    reason = _PUCK_LINE_REASON_MAP.get(decision.reason, ExitReason.SCORE_EXIT)
    detail = decision.note
    if decision.p_cover is not None:
        detail += f" | p_cover={decision.p_cover:.3f} ({decision.p_cover_source})"
    partial = decision.action == PLExitAction.SELL_50
    return NHLSignal(
        reason=reason,
        partial=partial,
        sell_pct=0.50 if partial else 1.00,
        detail=detail,
    )
```

- [ ] **Step 3: Test (yeni veya mevcut mapping test'ine ekle)**

`tests/unit/strategy/exit/test_nhl_exit_mapping.py` (mevcut yoksa oluştur, yeni test class):

```python
class TestPuckLineMapping:
    def test_hold_returns_none(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_puck_line_decision
        from src.strategy.exit.nhl_puck_line_exit import (
            NHLPuckLineExitDecision, ExitAction, ExitReason,
        )
        d = NHLPuckLineExitDecision(
            action=ExitAction.HOLD, reason=ExitReason.HOLD,
            p_cover=0.5, p_cover_source="empirical", note="",
        )
        assert map_nhl_puck_line_decision(d) is None

    def test_near_resolve_maps_to_nhl_puck_line_reason(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_puck_line_decision
        from src.strategy.exit.nhl_puck_line_exit import (
            NHLPuckLineExitDecision, ExitAction, ExitReason,
        )
        from src.models.enums import ExitReason as GExitReason
        d = NHLPuckLineExitDecision(
            action=ExitAction.SELL_ALL, reason=ExitReason.NEAR_RESOLVE,
            p_cover=1.0, p_cover_source="price", note="bid=0.95",
        )
        sig = map_nhl_puck_line_decision(d)
        assert sig is not None
        assert sig.reason == GExitReason.NHL_PUCK_LINE_NEAR_RESOLVE
        assert sig.partial is False
        assert sig.sell_pct == 1.00

    def test_scale_out_partial_50(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_puck_line_decision
        from src.strategy.exit.nhl_puck_line_exit import (
            NHLPuckLineExitDecision, ExitAction, ExitReason,
        )
        d = NHLPuckLineExitDecision(
            action=ExitAction.SELL_50, reason=ExitReason.SCALE_OUT,
            p_cover=0.85, p_cover_source="price", note="bid=0.85",
        )
        sig = map_nhl_puck_line_decision(d)
        assert sig.partial is True
        assert sig.sell_pct == 0.50
```

- [ ] **Step 4: Test PASS → Commit**

```bash
pytest tests/unit/strategy/exit/test_nhl_exit_mapping.py -v
git add src/models/enums.py src/strategy/exit/_nhl_exit_mapping.py tests/unit/strategy/exit/test_nhl_exit_mapping.py
git commit -m "feat(nhl): exit reason enum + puck line decision mapping"
```

---

## Task 6H: NHL Puck Line Dispatch Helper

**Files:**
- Create: `src/strategy/exit/_nhl_puck_line_dispatch.py`
- Test: `tests/unit/strategy/exit/test_nhl_puck_line_dispatch.py`

**Mantık:** `_nhl_exit_dispatch.py` (Task 3C) pattern paralel. score_info → decide_nhl_puck_line_exit → NHLSignal.

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test**

`tests/unit/strategy/exit/test_nhl_puck_line_dispatch.py`:

```python
"""NHL puck line dispatch wiring tests."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.models.enums import ExitReason
from src.strategy.exit._nhl_puck_line_dispatch import check_nhl_puck_line_exit
from src.strategy.exit.nhl_puck_line_exit import NHLPuckLineExitConfig


def _pos(**kw):
    defaults = dict(
        entry_price=0.45, current_price=0.52, bid_price=0.50,
        scaled_out_50=False, sport_tag="nhl", direction="BUY_YES",
        spread_line=1.5,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_returns_none_when_score_info_missing():
    sig = check_nhl_puck_line_exit(_pos(), {}, 0.5, NHLPuckLineExitConfig(), {})
    assert sig is None


def test_returns_none_when_clock_seconds_missing():
    score_info = {
        "available": True, "period": 3, "our_score": 2, "opp_score": 1,
        "clock_seconds": None,
    }
    sig = check_nhl_puck_line_exit(_pos(), score_info, 0.5, NHLPuckLineExitConfig(), {})
    assert sig is None


def test_near_resolve_when_bid_high():
    pos = _pos(bid_price=0.95)
    score_info = {
        "available": True, "period": 3, "clock_seconds": 300,
        "our_score": 3, "opp_score": 1,  # +2 lead, covers -1.5
    }
    sig = check_nhl_puck_line_exit(pos, score_info, 0.5, NHLPuckLineExitConfig(), {})
    assert sig is not None
    assert sig.reason == ExitReason.NHL_PUCK_LINE_NEAR_RESOLVE


def test_scale_out_partial():
    pos = _pos(bid_price=0.87, scaled_out_50=False)
    score_info = {
        "available": True, "period": 3, "clock_seconds": 200,
        "our_score": 3, "opp_score": 1,
    }
    sig = check_nhl_puck_line_exit(pos, score_info, 0.5, NHLPuckLineExitConfig(), {})
    assert sig is not None
    assert sig.reason == ExitReason.NHL_PUCK_LINE_SCALE_OUT
    assert sig.partial is True


def test_buy_yes_uses_positive_margin_when_ahead():
    """BUY_YES (favori), our_score > opp_score → current_margin > 0."""
    pos = _pos(direction="BUY_YES", bid_price=0.50)
    score_info = {
        "available": True, "period": 3, "clock_seconds": 600,
        "our_score": 2, "opp_score": 1,  # +1 lead from favori perspective
    }
    sig = check_nhl_puck_line_exit(pos, score_info, 0.5, NHLPuckLineExitConfig(), {})
    # Tablo boş → Skellam fallback. p_cover ~ %38 → bid+margin (0.53), 0.38<0.53 → PREDICTIVE_DEAD
    assert sig is not None
    assert sig.reason == ExitReason.NHL_PUCK_LINE_PREDICTIVE_DEAD


def test_hold_returns_none():
    pos = _pos(bid_price=0.45, current_price=0.52)
    score_info = {
        "available": True, "period": 3, "clock_seconds": 600,
        "our_score": 3, "opp_score": 1,  # +2, covered, p_cover high → no exit
    }
    # Empty table, Skellam will give high p_cover for +2 lead → no PREDICTIVE_DEAD
    sig = check_nhl_puck_line_exit(pos, score_info, 0.5, NHLPuckLineExitConfig(), {})
    assert sig is None
```

- [ ] **Step 2: Test FAIL**

```bash
pytest tests/unit/strategy/exit/test_nhl_puck_line_dispatch.py -v
```

- [ ] **Step 3: Implement**

`src/strategy/exit/_nhl_puck_line_dispatch.py`:

```python
"""NHL puck line dispatch: score_info + Position → NHLSignal | None.

monitor.py import YOK (circular import önlemi).
Strategy katmanı: tablo dışarıdan inject edilir, I/O yok.
"""
from __future__ import annotations

from src.domain.math.nhl_puck_line_probability import p_favorite_covers_hybrid
from src.models.position import Position
from src.strategy.exit._nhl_exit_mapping import NHLSignal, map_nhl_puck_line_decision
from src.strategy.exit.nhl_puck_line_exit import NHLPuckLineExitConfig, decide_nhl_puck_line_exit


def check_nhl_puck_line_exit(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,
    nhl_puck_line_cfg: NHLPuckLineExitConfig,
    nhl_puck_line_table: dict,
) -> NHLSignal | None:
    """Decide NHL puck line exit signal. Returns None → HOLD."""
    period = score_info.get("period") or score_info.get("period_number")
    clock_seconds = score_info.get("clock_seconds")
    our_score = score_info.get("our_score")
    opp_score = score_info.get("opp_score")

    if any(v is None for v in (period, clock_seconds, our_score, opp_score)):
        return None

    # current_margin = favori bakış açısı.
    # BUY_YES = pozisyon favori cover bekler → margin = our - opp (favori önde +)
    # BUY_NO  = pozisyon underdog cover bekler → margin = opp - our (underdog bakış)
    direction = getattr(pos, "direction", "BUY_YES")
    if direction == "BUY_YES":
        current_margin = our_score - opp_score
    else:
        current_margin = opp_score - our_score

    def _p_fn(p: int, m: int, s: int) -> tuple[float, str]:
        return p_favorite_covers_hybrid(p, m, s, table=nhl_puck_line_table)

    decision = decide_nhl_puck_line_exit(
        cfg=nhl_puck_line_cfg,
        entry_price=pos.entry_price,
        current_bid=pos.bid_price,
        current_price=pos.current_price,
        scaled_out_50=pos.scaled_out_50,
        period=period,
        seconds_remaining=clock_seconds,
        current_margin=current_margin,
        p_cover_fn=_p_fn,
    )
    return map_nhl_puck_line_decision(decision)
```

- [ ] **Step 4: Test → PASS, Commit**

```bash
pytest tests/unit/strategy/exit/test_nhl_puck_line_dispatch.py -v
git add src/strategy/exit/_nhl_puck_line_dispatch.py tests/unit/strategy/exit/test_nhl_puck_line_dispatch.py
git commit -m "feat(nhl): puck line dispatch — score_info to NHLSignal"
```

---

## Task 6I: Config + Settings + Gate Filter

**Files:**
- Modify: `config.yaml`
- Modify: `src/config/settings.py`
- Modify: `src/strategy/entry/gate.py`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: config.yaml'a entry + exit config ekle**

`config.yaml` `entry:` bloğuna ekle:

```yaml
  # NHL Puck Line entry filters
  nhl_puck_line_min_price: 0.20
  nhl_puck_line_max_price: 0.80
  nhl_puck_line_threshold: 1.5
  nhl_puck_line_min_volume: 3000.0
```

`config.yaml` root level `exit_nhl_puck_line:` bloğu ekle (exit_nhl yanına):

```yaml
exit_nhl_puck_line:
  near_resolve_threshold: 0.94
  scale_out_threshold: 0.85
  structural_damage_ratio: 0.30
  predictive_safety_margin: 0.03
```

- [ ] **Step 2: settings.py'a Pydantic model ekle**

`src/config/settings.py`:

```python
class ExitNhlPuckLineConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    near_resolve_threshold: float = 0.94
    scale_out_threshold: float = 0.85
    structural_damage_ratio: float = 0.30
    predictive_safety_margin: float = 0.03


# AppConfig'e ekle:
    exit_nhl_puck_line: ExitNhlPuckLineConfig = ExitNhlPuckLineConfig()


# EntryConfig'e ekle:
    nhl_puck_line_min_price: float = 0.20
    nhl_puck_line_max_price: float = 0.80
    nhl_puck_line_threshold: float = 1.5
    nhl_puck_line_min_volume: float = 3000.0
```

- [ ] **Step 3: gate.py — NHL puck line filter ekle**

`src/strategy/entry/gate.py` `GateConfig` dataclass'a:

```python
    nhl_puck_line_min_price: float = field(default=0.20)
    nhl_puck_line_max_price: float = field(default=0.80)
    nhl_puck_line_min_volume: float = field(default=3000.0)
```

`_check_filters()` fonksiyonuna NHL puck_line branch ekle (mevcut `if market_type == "spreads":` bloğunu sport-aware yap):

```python
    if market_type == "spreads":
        # NHL spread = puck line, NBA spread = standart spread
        sport_low = (sport_tag or "").lower()
        if sport_low in ("nhl", "ahl", "icehockey_nhl"):
            if polymarket_price < cfg.nhl_puck_line_min_price or polymarket_price > cfg.nhl_puck_line_max_price:
                return "PRICE_OUT_OF_RANGE"
            if volume < cfg.nhl_puck_line_min_volume:
                return "VOLUME_TOO_LOW"
        else:
            # NBA pattern
            if polymarket_price < cfg.spread_min_price or polymarket_price > cfg.spread_max_price:
                return "PRICE_OUT_OF_RANGE"
```

NOT: `_check_filters()` mevcut signature'a `sport_tag: str = ""` eklemek gerek (yoksa caller'dan al). Mevcut çağrıyı bul:

```bash
grep -n "_check_filters(" src/strategy/entry/gate.py
```

Çağrıya `sport_tag=market.sport_tag` ekle.

- [ ] **Step 4: Test — gate NHL puck line filter pass case**

`tests/unit/strategy/entry/test_gate.py`'a yeni test (mevcut paterne uygun):

```python
def test_nhl_puck_line_market_passes_filter(make_gate, make_market):
    gate = make_gate(active_sports=["icehockey_nhl"])
    market = make_market(
        sport_tag="nhl",
        sports_market_type="spreads",
        yes_price=0.45,
        volume_24h=5000.0,
    )
    results = gate.run([market])
    # Gate karar üretmeli, INACTIVE_SPORT yok, PRICE_OUT_OF_RANGE yok
    assert results[0].skipped_reason not in ("INACTIVE_SPORT", "PRICE_OUT_OF_RANGE")
```

- [ ] **Step 5: Test çalıştır + commit**

```bash
pytest tests/unit/strategy/entry/test_gate.py -v
pytest -q | tail -5
git add config.yaml src/config/settings.py src/strategy/entry/gate.py tests/unit/strategy/entry/test_gate.py
git commit -m "feat(nhl): puck line entry filter (config + gate dispatch)"
```

---

## Task 6J: monitor.py + exit_processor + factory Wiring

**Files:**
- Modify: `src/strategy/exit/monitor.py`
- Modify: `src/orchestration/exit_processor.py`
- Modify: `src/orchestration/agent.py`
- Modify: `src/orchestration/factory.py`

**Mantık:** monitor.py NHL `pos.sports_market_type` üzerinden moneyline / puck_line dispatch eder. exit_processor.py yeni cfg + table helper'ları ile evaluate'a geçirir. factory.py table load + AgentDeps inject.

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: monitor.py — NHL hockey block'ta market_type dispatch**

Mevcut block (Task 3C'den):

```python
    if _is_hockey_family(pos.sport_tag) and score_info.get("available"):
        nhl_sig = check_nhl_exit(
            pos, score_info, elapsed_pct,
            nhl_exit_cfg if nhl_exit_cfg is not None else _DEFAULT_NHL_CFG,
            nhl_wp_table if nhl_wp_table is not None else {},
        )
        if nhl_sig is not None:
            return MonitorResult(...)
```

Bunu `pos.sports_market_type` ile market-aware yap:

```python
    if _is_hockey_family(pos.sport_tag) and score_info.get("available"):
        smt = (pos.sports_market_type or "moneyline").lower()
        if smt == "spreads":
            from src.strategy.exit._nhl_puck_line_dispatch import check_nhl_puck_line_exit
            nhl_sig = check_nhl_puck_line_exit(
                pos, score_info, elapsed_pct,
                nhl_puck_line_cfg if nhl_puck_line_cfg is not None else _DEFAULT_NHL_PUCK_LINE_CFG,
                nhl_puck_line_table if nhl_puck_line_table is not None else {},
            )
        else:
            nhl_sig = check_nhl_exit(
                pos, score_info, elapsed_pct,
                nhl_exit_cfg if nhl_exit_cfg is not None else _DEFAULT_NHL_CFG,
                nhl_wp_table if nhl_wp_table is not None else {},
            )
        if nhl_sig is not None:
            return MonitorResult(
                exit_signal=ExitSignal(reason=nhl_sig.reason, detail=nhl_sig.detail,
                                       partial=nhl_sig.partial, sell_pct=nhl_sig.sell_pct),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
```

`evaluate()` signature'a 2 yeni param ekle:

```python
    nhl_puck_line_cfg: "NHLPuckLineExitConfig | None" = None,
    nhl_puck_line_table: dict | None = None,
```

Module-level default ekle:

```python
from src.strategy.exit.nhl_puck_line_exit import NHLPuckLineExitConfig
_DEFAULT_NHL_PUCK_LINE_CFG = NHLPuckLineExitConfig()
```

monitor.py satır limit kontrolü:

```bash
wc -l src/strategy/exit/monitor.py
```

Şu an 398; +5-7 satır artacak → ~405. Limit aşımı olursa `_hold_revocation_should_revoke` veya `_never_in_profit_exit` fonksiyonlarından birini `src/strategy/exit/_guard_helpers.py` (yeni)'a taşı. Mini refactor scope-safe.

- [ ] **Step 2: exit_processor.py — yeni 2 helper + evaluate güncelle**

`src/orchestration/exit_processor.py` mevcut `_nhl_exit_cfg()` yanına ekle:

```python
def _nhl_puck_line_cfg(self):
    """exit_nhl_puck_line config → NHLPuckLineExitConfig."""
    from src.strategy.exit.nhl_puck_line_exit import NHLPuckLineExitConfig
    cfg = getattr(self.deps.state, "config", None)
    if cfg is None or not hasattr(cfg, "exit_nhl_puck_line"):
        return NHLPuckLineExitConfig()
    pc = cfg.exit_nhl_puck_line
    return NHLPuckLineExitConfig(
        near_resolve_threshold=pc.near_resolve_threshold,
        scale_out_threshold=pc.scale_out_threshold,
        structural_damage_ratio=pc.structural_damage_ratio,
        predictive_safety_margin=pc.predictive_safety_margin,
    )

def _nhl_puck_line_table(self) -> dict:
    """AgentDeps'ten NHL puck line tablosunu al."""
    return getattr(self.deps, "nhl_puck_line_table", {}) or {}
```

`evaluate()` çağrısına ekle:

```python
nhl_puck_line_cfg=self._nhl_puck_line_cfg(),
nhl_puck_line_table=self._nhl_puck_line_table(),
```

- [ ] **Step 3: agent.py — AgentDeps'e alan ekle**

`src/orchestration/agent.py` `AgentDeps` dataclass'a ekle:

```python
nhl_puck_line_table: dict = field(default_factory=dict)
```

- [ ] **Step 4: factory.py — table load + inject**

`src/orchestration/factory.py`'a ekle:

```python
from src.infrastructure.repositories.nhl_puck_line_repository import load_table as _load_nhl_puck_line_table_raw

def _load_nhl_puck_line_table() -> dict:
    try:
        return _load_nhl_puck_line_table_raw()
    except FileNotFoundError:
        logger.warning("NHL puck line table not found at data/nhl_empirical_puck_line_table.json — Skellam fallback only")
        return {}
```

`build_agent()` içinde:

```python
nhl_puck_line_table = _load_nhl_puck_line_table()
```

`AgentDeps(...)` constructor'a ekle:

```python
nhl_puck_line_table=nhl_puck_line_table,
```

- [ ] **Step 5: Tam suite + commit**

```bash
pytest -q | tail -5
# Beklenen: ~1380+ passed (1365 + ~15 yeni puck line testleri)
git add src/strategy/exit/monitor.py src/orchestration/exit_processor.py src/orchestration/agent.py src/orchestration/factory.py
git commit -m "feat(nhl): puck line wiring (monitor dispatch + factory inject)"
```

---

## Task 6K: Integration Smoke Test

**Files:**
- Create: `tests/integration/test_nhl_puck_line_pipeline_smoke.py`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Smoke test yaz**

`tests/integration/test_nhl_puck_line_pipeline_smoke.py`:

```python
"""NHL puck line pipeline smoke — gate filter + monitor dispatch."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from src.models.market import MarketData
from src.strategy.entry.gate import EntryGate, GateConfig


def _make_nhl_puck_line_market(yes_price: float = 0.50) -> MarketData:
    return MarketData(
        condition_id="nhl_pl_001",
        question="Will the Boston Bruins cover -1.5 vs Buffalo Sabres?",
        slug="bruins-cover-15",
        yes_token_id="tok_yes",
        no_token_id="tok_no",
        yes_price=yes_price,
        no_price=1.0 - yes_price,
        liquidity=5000.0,
        volume_24h=4000.0,
        end_date_iso="2026-06-01T00:00:00Z",
        match_start_iso=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        event_id="evt_bos_buf",
        sport_tag="nhl",
        sports_market_type="spreads",
    )


def _make_gate() -> EntryGate:
    cfg = GateConfig(
        active_sports=["icehockey_nhl"],
        min_favorite_probability=0.50,
        max_entry_price=0.80,
        max_positions=10,
        max_exposure_pct=0.50,
        hard_cap_overflow_pct=0.02,
        min_entry_size_pct=0.015,
        confidence_bet_pct={"A": 0.05, "B": 0.03},
        max_single_bet_usdc=100.0,
        max_bet_pct=0.05,
        probability_weighted=True,
        min_bookmakers=1,
        min_sharps=0,
        min_gap_threshold=0.05,
        min_market_volume=3000.0,
        min_polymarket_price=0.20,
        nhl_puck_line_min_price=0.20,
        nhl_puck_line_max_price=0.80,
        nhl_puck_line_min_volume=3000.0,
    )
    portfolio = MagicMock()
    portfolio.positions = {}
    portfolio.bankroll = 1000.0

    odds_result = MagicMock()
    odds_result.probability = MagicMock(probability=0.62, has_sharp=True, num_bookmakers=18.0)
    odds_result.fail_reason = None
    odds_fn = MagicMock(return_value=odds_result)

    return EntryGate(
        config=cfg, portfolio=portfolio,
        circuit_breaker=None, cooldown=None, blacklist=None,
        odds_enricher=odds_fn, manipulation_checker=None,
        edge_enricher=None, nhl_edge_enricher=None,
    )


class TestNhlPuckLinePipelineSmoke:
    def test_nhl_puck_line_market_passes_filter(self):
        gate = _make_gate()
        market = _make_nhl_puck_line_market()
        results = gate.run([market])
        assert len(results) == 1
        assert results[0].skipped_reason not in ("INACTIVE_SPORT", "PRICE_OUT_OF_RANGE", "VOLUME_TOO_LOW")

    def test_nhl_puck_line_price_out_of_range_rejected(self):
        gate = _make_gate()
        market = _make_nhl_puck_line_market(yes_price=0.10)  # below 0.20
        results = gate.run([market])
        assert results[0].skipped_reason == "PRICE_OUT_OF_RANGE"

    def test_nhl_puck_line_volume_too_low_rejected(self):
        gate = _make_gate()
        market = _make_nhl_puck_line_market()
        market = MarketData(**{**market.__dict__, "volume_24h": 1000.0})
        results = gate.run([market])
        assert results[0].skipped_reason == "VOLUME_TOO_LOW"
```

- [ ] **Step 2: Test → PASS, Commit**

```bash
pytest tests/integration/test_nhl_puck_line_pipeline_smoke.py -v
git add tests/integration/test_nhl_puck_line_pipeline_smoke.py
git commit -m "test(nhl): puck line pipeline smoke — filter + dispatch"
```

---

# TASK 7: NHL Totals

## Task 7A: Empirical Totals Table Builder

**Files:**
- Create: `scripts/build_nhl_totals_table.py`
- Output: `data/nhl_empirical_totals_table.json`

**Mantık:** `build_nhl_puck_line_table.py` paterne paralel; her tick için (period, current_total, seconds_remaining) → "final_total >= target_total + 1?" empirical olasılığı. **2 ayrı target_total bucket: 5.5 ve 6.5** (Karar 2).

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Script iskeleti — header + helpers**

`scripts/build_nhl_totals_table.py` (yeni dosya):

```python
#!/usr/bin/env python3
"""
scripts/build_nhl_totals_table.py

MoneyPuck shot-level play-by-play → NHL empirical totals (over/under) lookup table.

Standalone, tek seferlik. Çıktı: data/nhl_empirical_totals_table.json

Target lines: 5.5 ve 6.5 (Polymarket NHL standart).
SO resolution: winner +1 gol → totals includes OT/SO (Karar 3).

Key format: "period_currentTotal_secondsRemaining_targetTotal" → {p_over, ci_low, ci_high, n_games}
  Örn: "3_4_300_5.5" = P3, current 4 gol, 300sn kala, target 5.5 → p_over olasılığı
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_SEASONS: list[int] = [2022, 2023, 2024]
_DATA_DIR = Path("data/nhl_shots")
_OUTPUT_PATH = Path("data/nhl_empirical_totals_table.json")

_TIME_BUCKET_SEC: int = 30
_TOTAL_CAP: int = 12
_REGULATION_SECONDS: int = 3600
_Z: float = 1.96
_MIN_N: int = 30
_TARGET_TOTALS: list[float] = [5.5, 6.5]

_NEEDED_COLS = [
    "game_id", "period", "time",
    "homeTeamGoals", "awayTeamGoals",
    "homeTeamWon", "goal", "isPlayoffGame",
]
```

- [ ] **Step 2: load_shots_csv (Task 6A ile aynı, kopyala)**

(Step 6A Step 2'deki kod, aynısı)

- [ ] **Step 3: reconstruct_game_states_with_final_total**

```python
def reconstruct_game_states_with_final_total(shots_df: pd.DataFrame) -> pd.DataFrame:
    """30sn tick + final_total (regulation + OT goal varsa + SO winner +1).

    Final total convention:
      last_period=3 → home_final + away_final (regulation)
      last_period=4 → home_final + away_final (OT goal eklendi)
      last_period=5 → home_final + away_final + 1 (SO winner +1, Karar 3)
    """
    reg = shots_df[shots_df["period"].isin([1, 2, 3])].copy()
    reg["game_seconds"] = reg["time"]
    reg = reg.sort_values(["game_id", "game_seconds"]).reset_index(drop=True)

    game_finals = shots_df.groupby("game_id").agg(
        last_period=("period", "max"),
        home_final=("homeTeamGoals", "max"),
        away_final=("awayTeamGoals", "max"),
    ).to_dict("index")

    def compute_final_total(gid: str) -> int:
        info = game_finals[gid]
        base = int(info["home_final"] + info["away_final"])
        if info["last_period"] >= 5:
            return base + 1  # SO winner +1
        return base

    final_totals = {gid: compute_final_total(gid) for gid in game_finals}

    tick_times = np.arange(0.0, _REGULATION_SECONDS + _TIME_BUCKET_SEC, _TIME_BUCKET_SEC)
    sec_rem_ticks = (_REGULATION_SECONDS - tick_times).astype(int)
    period_ticks = np.minimum((tick_times // 1200).astype(int) + 1, 3)

    chunks: list[pd.DataFrame] = []
    for gid, gdf in reg.groupby("game_id", sort=False):
        times = gdf["game_seconds"].values
        home_goals = gdf["homeTeamGoals"].values
        away_goals = gdf["awayTeamGoals"].values

        idxs = np.searchsorted(times, tick_times, side="right") - 1
        valid = idxs >= 0
        home = np.where(valid, home_goals[np.where(valid, idxs, 0)], 0)
        away = np.where(valid, away_goals[np.where(valid, idxs, 0)], 0)

        current_total = (home + away).astype(int)
        final_total = np.full_like(current_total, final_totals[gid])

        chunks.append(pd.DataFrame({
            "game_id": gid,
            "period": period_ticks,
            "seconds_remaining": sec_rem_ticks,
            "current_total": current_total,
            "final_total": final_total,
        }))

    return pd.concat(chunks, ignore_index=True)
```

- [ ] **Step 4: aggregate_totals — her target için ayrı**

```python
def aggregate_totals_over(states_df: pd.DataFrame, target_totals: list[float]) -> dict:
    """Her (period, current_total, seconds, target) için P(over hits) hesapla."""
    df = states_df.copy()
    df["current_total_clamped"] = df["current_total"].clip(upper=_TOTAL_CAP).astype(int)
    df["time_bucket"] = ((df["seconds_remaining"] // _TIME_BUCKET_SEC) * _TIME_BUCKET_SEC).astype(int)

    z2 = _Z ** 2
    table: dict[str, dict | None] = {}

    for target in target_totals:
        # Over hits: final_total > target (line .5 olduğu için final >= target + 0.5 → final >= ceil)
        df["over_hit"] = (df["final_total"] > target).astype(int)

        grouped = (
            df.groupby(["period", "current_total_clamped", "time_bucket"], sort=True)
            ["over_hit"]
            .agg(overs="sum", n="count")
            .reset_index()
        )

        for row in grouped.itertuples(index=False):
            period = int(row.period)
            current = int(row.current_total_clamped)
            seconds = int(row.time_bucket)
            overs = float(row.overs)
            n = int(row.n)
            key = f"{period}_{current}_{seconds}_{target}"

            if n < _MIN_N:
                table[key] = None
                continue

            p_hat = overs / n
            centre = (p_hat + z2 / (2 * n)) / (1 + z2 / n)
            margin_w = (_Z / (1 + z2 / n)) * math.sqrt(
                p_hat * (1 - p_hat) / n + z2 / (4 * n ** 2)
            )
            table[key] = {
                "p_over": round(centre, 4),
                "ci_low": round(max(0.0, centre - margin_w), 4),
                "ci_high": round(min(1.0, centre + margin_w), 4),
                "n_games": n,
            }

    return table
```

- [ ] **Step 5: main() + sanity + JSON write**

```python
def print_sanity_summary(table: dict) -> None:
    checkpoints = [
        ("3_2_1200_5.5", "current 2, P3 start, target 5.5"),
        ("3_4_1200_5.5", "current 4, P3 start, target 5.5"),
        ("3_5_300_5.5",  "current 5, last 5 min, target 5.5"),
        ("3_4_60_5.5",   "current 4, last 60s, target 5.5"),
        ("3_3_1200_6.5", "current 3, P3 start, target 6.5"),
        ("3_5_600_6.5",  "current 5, P3 mid, target 6.5"),
        ("3_6_300_6.5",  "current 6, last 5 min, target 6.5"),
    ]
    print("\n-- TOTALS SANITY CHECK " + "-" * 45)
    print(f"{'Label':45s}  {'p_over':>7s}  {'n':>5s}  CI")
    print("-" * 80)
    for key, label in checkpoints:
        entry = table.get(key)
        if entry:
            print(
                f"{label:45s}  {entry['p_over']*100:5.1f}%  "
                f"{entry['n_games']:5d}  "
                f"[{entry['ci_low']*100:.1f}, {entry['ci_high']*100:.1f}]"
            )
        else:
            print(f"{label:45s}  NO_DATA")
    print("-" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NHL totals empirical table")
    parser.add_argument("--seasons", type=int, nargs="+", default=_DEFAULT_SEASONS)
    parser.add_argument("--targets", type=float, nargs="+", default=_TARGET_TOTALS)
    parser.add_argument("--output", type=Path, default=_OUTPUT_PATH)
    args = parser.parse_args()

    dfs: list[pd.DataFrame] = []
    for season_start in args.seasons:
        season_label = f"{season_start}-{season_start+1-2000:02d}"
        csv_path = _DATA_DIR / f"shots_{season_start}.csv"
        if not csv_path.exists():
            logger.error("Missing %s — run build_nhl_empirical_table.py first.", csv_path)
            return
        df = load_shots_csv(csv_path, season_label)
        logger.info("Loaded %s: %d rows, %d games", season_label, len(df), df["game_id"].nunique())
        dfs.append(df)

    all_shots = pd.concat(dfs, ignore_index=True)
    states = reconstruct_game_states_with_final_total(all_shots)
    table = aggregate_totals_over(states, args.targets)

    metadata = {
        "seasons": args.seasons,
        "time_bucket_sec": _TIME_BUCKET_SEC,
        "total_cap": _TOTAL_CAP,
        "target_totals": args.targets,
        "min_sample_size": _MIN_N,
        "wilson_z": _Z,
        "total_games": all_shots["game_id"].nunique(),
        "key_format": "period_currentTotal_secondsRemaining_targetTotal",
        "so_resolution": "winner +1 goal (Karar 3)",
    }

    output = {"metadata": metadata, "totals_over": table}
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info("Wrote %s (%d entries)", args.output, len(table))

    print_sanity_summary(table)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Build et, sanity, commit**

```bash
python scripts/build_nhl_totals_table.py
git add scripts/build_nhl_totals_table.py data/nhl_empirical_totals_table.json
git commit -m "feat(nhl): empirical totals table builder + lookup (5.5 + 6.5)"
```

---

## Task 7B: NHL Totals Math (Skellam Sum-of-Poissons)

**Files:**
- Create: `src/domain/math/nhl_totals.py`
- Test: `tests/unit/domain/math/test_nhl_totals.py`

**Mantık:** Future total goals = current_total + Poisson(λ_total × t). λ_total = 2 × λ_per_team. P(final > target) = P(Poisson(λ_total × t) > target - current_total).

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test**

`tests/unit/domain/math/test_nhl_totals.py`:

```python
"""Skellam-based totals over probability tests."""
from __future__ import annotations

from src.domain.math.nhl_totals import poisson_p_over


class TestPOverSkellam:
    def test_already_over_returns_one(self):
        """current=6 > target=5.5 → over zaten gerçekleşti."""
        p = poisson_p_over(current_total=6, target_total=5.5, seconds_remaining=300)
        assert p == 1.0

    def test_zero_seconds_uses_current_only(self):
        """Süre bitti, current >= target+0.5 → 1, değilse 0."""
        assert poisson_p_over(current_total=6, target_total=5.5, seconds_remaining=0) == 1.0
        assert poisson_p_over(current_total=5, target_total=5.5, seconds_remaining=0) == 0.0

    def test_p3_late_low_total_low_p_over(self):
        """current=2, target=5.5, son 5 dk → 4+ gol gerek, çok düşük."""
        p = poisson_p_over(current_total=2, target_total=5.5, seconds_remaining=300)
        assert p < 0.05

    def test_p3_late_close_to_target(self):
        """current=5, target=5.5, son 5 dk → 1 gol yeter, ~%25-50."""
        p = poisson_p_over(current_total=5, target_total=5.5, seconds_remaining=300)
        assert 0.10 < p < 0.50

    def test_full_game_balanced(self):
        """3600 sn, current=0, target=5.5 → ~%55-70 (lig avg 6.14)."""
        p = poisson_p_over(current_total=0, target_total=5.5, seconds_remaining=3600)
        assert 0.50 < p < 0.75

    def test_full_game_target_6_5(self):
        """3600 sn, current=0, target=6.5 → ~%40-55."""
        p = poisson_p_over(current_total=0, target_total=6.5, seconds_remaining=3600)
        assert 0.35 < p < 0.55
```

- [ ] **Step 2: FAIL**

```bash
pytest tests/unit/domain/math/test_nhl_totals.py -v
```

- [ ] **Step 3: Implement**

`src/domain/math/nhl_totals.py`:

```python
"""NHL totals (over/under) probability via Poisson distribution.

Total goals = home + away ~ Poisson(λ_total × t) where λ_total = λ_home + λ_away.
NHL avg: 6.142 / 3600 = 0.001706 total goals per second.

P(over X.5) = P(future_goals > X - current_total + 0.5)
            = P(Poisson(λ × t) >= ceil(X + 0.5 - current_total))
            = 1 - poisson.cdf(ceil(X + 0.5 - current_total) - 1, λ × t)
"""
from __future__ import annotations

import math

from scipy.stats import poisson

LAMBDA_TOTAL_PER_SECOND: float = 6.142 / 3600.0  # ≈ 0.001706


def poisson_p_over(
    current_total: int,
    target_total: float,
    seconds_remaining: int,
    lambda_total: float = LAMBDA_TOTAL_PER_SECOND,
) -> float:
    """P(final_total > target_total) given current state.

    Args:
      current_total: anlık toplam gol
      target_total: bahis line (örn 5.5)
      seconds_remaining: regulation kalan saniye

    Returns:
      Over olasılığı [0, 1].
    """
    # Already over (line .5'den dolayı current > target zaten over)
    if current_total > target_total:
        return 1.0

    if seconds_remaining <= 0:
        return 1.0 if current_total > target_total else 0.0

    mu = lambda_total * seconds_remaining
    goals_needed = math.ceil(target_total + 0.5 - current_total)  # min ek gol over için
    # P(X >= goals_needed) = 1 - cdf(goals_needed - 1)
    p = 1.0 - poisson.cdf(goals_needed - 1, mu)
    return float(max(0.0, min(1.0, p)))
```

- [ ] **Step 4: Test → PASS, Commit**

```bash
pytest tests/unit/domain/math/test_nhl_totals.py -v
git add src/domain/math/nhl_totals.py tests/unit/domain/math/test_nhl_totals.py
git commit -m "feat(nhl): poisson-based totals over probability"
```

---

## Task 7C: NHL Totals Repository

**Files:**
- Create: `src/infrastructure/repositories/nhl_totals_repository.py`
- Test: `tests/unit/infrastructure/repositories/test_nhl_totals_repository.py`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test (Task 6C pattern paralel)**

`tests/unit/infrastructure/repositories/test_nhl_totals_repository.py`:

```python
"""NHL totals table loader tests."""
from __future__ import annotations

import json

import pytest

from src.infrastructure.repositories import nhl_totals_repository as repo


def test_load_table_returns_dict(tmp_path, monkeypatch):
    fake = {"metadata": {"total_games": 100}, "totals_over": {"3_4_300_5.5": {"p_over": 0.42}}}
    fake_path = tmp_path / "nhl_empirical_totals_table.json"
    fake_path.write_text(json.dumps(fake), encoding="utf-8")
    monkeypatch.setattr(repo, "TABLE_PATH", fake_path)
    repo.load_table.cache_clear()
    result = repo.load_table()
    assert "totals_over" in result


def test_load_table_raises_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(repo, "TABLE_PATH", tmp_path / "missing.json")
    repo.load_table.cache_clear()
    with pytest.raises(FileNotFoundError):
        repo.load_table()
```

- [ ] **Step 2: Implement**

`src/infrastructure/repositories/nhl_totals_repository.py`:

```python
"""NHL empirical totals over/under probability table loader.

Build: python scripts/build_nhl_totals_table.py
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

TABLE_PATH: Path = Path("data/nhl_empirical_totals_table.json")


@lru_cache(maxsize=1)
def load_table() -> dict:
    if not TABLE_PATH.exists():
        raise FileNotFoundError(
            f"Empirical totals table not found at {TABLE_PATH}. "
            "Run scripts/build_nhl_totals_table.py first."
        )
    with open(TABLE_PATH, encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **Step 3: Test → PASS, Commit**

```bash
pytest tests/unit/infrastructure/repositories/test_nhl_totals_repository.py -v
git add src/infrastructure/repositories/nhl_totals_repository.py tests/unit/infrastructure/repositories/test_nhl_totals_repository.py
git commit -m "feat(nhl): totals empirical table repository"
```

---

## Task 7D: NHL Totals Hybrid Wrapper

**Files:**
- Create: `src/domain/math/nhl_totals_probability.py`
- Test: `tests/unit/domain/math/test_nhl_totals_probability.py`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test**

`tests/unit/domain/math/test_nhl_totals_probability.py`:

```python
"""Hybrid totals probability wrapper tests."""
from __future__ import annotations

from src.domain.math.nhl_totals_probability import p_over_hybrid


_FAKE_TABLE = {
    "totals_over": {
        "3_4_300_5.5": {"p_over": 0.35, "n_games": 200},
        "3_5_600_5.5": None,  # insufficient
    }
}


def test_uses_empirical_when_available():
    p, src = p_over_hybrid(period=3, current_total=4, seconds_remaining=300, target_total=5.5, table=_FAKE_TABLE)
    assert p == 0.35
    assert src == "empirical"


def test_falls_back_when_target_not_in_table():
    """Target 7.5 tabloda yok (sadece 5.5 + 6.5) → Skellam fallback."""
    p, src = p_over_hybrid(period=3, current_total=4, seconds_remaining=300, target_total=7.5, table=_FAKE_TABLE)
    assert 0.0 <= p <= 1.0
    assert src == "skellam_fallback"


def test_falls_back_when_entry_is_none():
    p, src = p_over_hybrid(period=3, current_total=5, seconds_remaining=600, target_total=5.5, table=_FAKE_TABLE)
    assert src == "skellam_fallback"


def test_seconds_bucketed_to_30s():
    p, src = p_over_hybrid(period=3, current_total=4, seconds_remaining=315, target_total=5.5, table=_FAKE_TABLE)
    assert p == 0.35
    assert src == "empirical"
```

- [ ] **Step 2: FAIL**

```bash
pytest tests/unit/domain/math/test_nhl_totals_probability.py -v
```

- [ ] **Step 3: Implement**

`src/domain/math/nhl_totals_probability.py`:

```python
"""Hybrid totals probability — empirical first, Poisson fallback."""
from __future__ import annotations

from src.domain.math.nhl_totals import poisson_p_over

_TIME_BUCKET_SEC: int = 30
_TOTAL_CAP: int = 12


def p_over_hybrid(
    period: int,
    current_total: int,
    seconds_remaining: int,
    target_total: float,
    *,
    table: dict,
) -> tuple[float, str]:
    """P(final > target_total) — empirical→Poisson hybrid.

    Returns:
        (probability, source) where source in {"empirical", "skellam_fallback"}.
    """
    current_clamped = min(_TOTAL_CAP, current_total)
    time_bucket = (seconds_remaining // _TIME_BUCKET_SEC) * _TIME_BUCKET_SEC
    key = f"{period}_{current_clamped}_{time_bucket}_{target_total}"

    over_table = table.get("totals_over", {})
    entry = over_table.get(key)
    if entry is not None and "p_over" in entry:
        return float(entry["p_over"]), "empirical"

    p = poisson_p_over(current_total, target_total, seconds_remaining)
    return p, "skellam_fallback"
```

- [ ] **Step 4: Test → PASS, Commit**

```bash
pytest tests/unit/domain/math/test_nhl_totals_probability.py -v
git add src/domain/math/nhl_totals_probability.py tests/unit/domain/math/test_nhl_totals_probability.py
git commit -m "feat(nhl): hybrid totals probability wrapper"
```

---

## Task 7E: NHL Totals Exit Logic — Pure Decision

**Files:**
- Create: `src/strategy/exit/nhl_totals_exit.py`
- Test: `tests/unit/strategy/exit/test_nhl_totals_exit.py`

**Mantık:** Puck line pattern paralel (Task 6E). Side handling: `BUY_YES = OVER`, `BUY_NO = UNDER`. UNDER için `1 - p_over` kullan.

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test**

`tests/unit/strategy/exit/test_nhl_totals_exit.py`:

```python
"""NHL totals exit decision tests — pure function."""
from __future__ import annotations

import dataclasses

import pytest

from src.strategy.exit.nhl_totals_exit import (
    ExitAction, ExitReason, NHLTotalsExitConfig, decide_nhl_totals_exit,
)


def _decide(**overrides):
    defaults = dict(
        cfg=NHLTotalsExitConfig(),
        entry_price=0.45,
        current_bid=0.50,
        current_price=0.52,
        scaled_out_50=False,
        period=3,
        seconds_remaining=600,
        current_total=4,
        target_total=5.5,
        side="over",
        p_over_fn=lambda p, c, s, t: (0.45, "empirical"),
    )
    defaults.update(overrides)
    return decide_nhl_totals_exit(**defaults)


class TestNearResolve:
    def test_fires_at_threshold(self):
        d = _decide(current_bid=0.94)
        assert d.action == ExitAction.SELL_ALL
        assert d.reason == ExitReason.NEAR_RESOLVE


class TestScaleOut:
    def test_fires_at_threshold(self):
        d = _decide(current_bid=0.85)
        assert d.action == ExitAction.SELL_50
        assert d.reason == ExitReason.SCALE_OUT


class TestPredictiveDeadOver:
    def test_over_low_p_fires(self):
        """Over bet, p_over=0.10, bid=0.20 → PREDICTIVE_DEAD."""
        d = _decide(side="over", p_over_fn=lambda p,c,s,t: (0.10, "x"), current_bid=0.20)
        assert d.reason == ExitReason.PREDICTIVE_DEAD

    def test_over_high_p_no_fire(self):
        d = _decide(side="over", p_over_fn=lambda p,c,s,t: (0.60, "x"), current_bid=0.40)
        assert d.reason != ExitReason.PREDICTIVE_DEAD


class TestPredictiveDeadUnder:
    def test_under_uses_inverse_prob(self):
        """Under bet, p_over=0.90 → p_under=0.10, bid=0.20 → PREDICTIVE_DEAD."""
        d = _decide(side="under", p_over_fn=lambda p,c,s,t: (0.90, "x"), current_bid=0.20)
        assert d.reason == ExitReason.PREDICTIVE_DEAD

    def test_under_high_p_under_no_fire(self):
        """Under bet, p_over=0.20 → p_under=0.80, bid=0.30 → no fire."""
        d = _decide(side="under", p_over_fn=lambda p,c,s,t: (0.20, "x"), current_bid=0.30)
        assert d.reason != ExitReason.PREDICTIVE_DEAD


class TestStructuralDamage:
    def test_fires_when_price_collapsed(self):
        d = _decide(entry_price=0.60, current_price=0.10)
        assert d.reason == ExitReason.STRUCTURAL_DAMAGE


class TestHold:
    def test_default(self):
        d = _decide()
        assert d.action == ExitAction.HOLD
        assert d.reason == ExitReason.HOLD


class TestEdgeCases:
    def test_fn_exception_skips_predictive(self):
        def raising(p,c,s,t):
            raise RuntimeError("table miss")
        d = _decide(p_over_fn=raising)
        assert d.reason != ExitReason.PREDICTIVE_DEAD

    def test_frozen_immutable(self):
        d = _decide()
        with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
            d.action = ExitAction.SELL_ALL
```

- [ ] **Step 2: FAIL**

```bash
pytest tests/unit/strategy/exit/test_nhl_totals_exit.py -v
```

- [ ] **Step 3: Implement**

`src/strategy/exit/nhl_totals_exit.py`:

```python
"""NHL totals (over/under) exit logic — priority chain pure function."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Literal


class ExitAction(str, Enum):
    HOLD = "HOLD"
    SELL_50 = "SELL_50"
    SELL_ALL = "SELL_ALL"


class ExitReason(str, Enum):
    NEAR_RESOLVE = "NEAR_RESOLVE"
    SCALE_OUT = "SCALE_OUT"
    PREDICTIVE_DEAD = "PREDICTIVE_DEAD"
    STRUCTURAL_DAMAGE = "STRUCTURAL_DAMAGE"
    HOLD = "HOLD"


@dataclass(frozen=True)
class NHLTotalsExitDecision:
    action: ExitAction
    reason: ExitReason
    p_side: float | None  # p_over for over, p_under for under
    p_source: str
    note: str


@dataclass(frozen=True)
class NHLTotalsExitConfig:
    near_resolve_threshold: float = 0.94
    scale_out_threshold: float = 0.85
    structural_damage_ratio: float = 0.30
    predictive_safety_margin: float = 0.03


def decide_nhl_totals_exit(
    *,
    cfg: NHLTotalsExitConfig,
    entry_price: float,
    current_bid: float,
    current_price: float,
    scaled_out_50: bool,
    period: int,
    seconds_remaining: int,
    current_total: int,
    target_total: float,
    side: Literal["over", "under"],
    p_over_fn: Callable[[int, int, int, float], tuple[float, str]],
) -> NHLTotalsExitDecision:
    """NHL totals over/under exit — priority chain.

    side: "over" (BUY_YES) veya "under" (BUY_NO).
    p_over_fn: (period, current_total, seconds_remaining, target_total) -> (p_over, source)
    Under için p_side = 1 - p_over.
    """
    # 1. NEAR_RESOLVE
    if current_bid >= cfg.near_resolve_threshold:
        return NHLTotalsExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.NEAR_RESOLVE,
            p_side=1.0, p_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # 2. SCALE_OUT
    if not scaled_out_50 and current_bid >= cfg.scale_out_threshold:
        return NHLTotalsExitDecision(
            action=ExitAction.SELL_50,
            reason=ExitReason.SCALE_OUT,
            p_side=current_bid, p_source="price",
            note=f"bid={current_bid:.3f}",
        )

    # 3. PREDICTIVE_DEAD
    try:
        p_over, p_source = p_over_fn(period, current_total, seconds_remaining, target_total)
    except Exception:
        p_over = None
        p_source = "error"

    p_side: float | None = None
    if p_over is not None:
        p_side = p_over if side == "over" else (1.0 - p_over)

    if p_side is not None and p_side < (current_bid + cfg.predictive_safety_margin):
        return NHLTotalsExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.PREDICTIVE_DEAD,
            p_side=p_side, p_source=p_source,
            note=f"p_{side}={p_side:.3f} bid={current_bid:.3f}",
        )

    # 4. STRUCTURAL_DAMAGE
    if entry_price > 0 and (current_price / entry_price) < cfg.structural_damage_ratio:
        return NHLTotalsExitDecision(
            action=ExitAction.SELL_ALL,
            reason=ExitReason.STRUCTURAL_DAMAGE,
            p_side=p_side, p_source=p_source,
            note=f"ratio={current_price/entry_price:.2f}",
        )

    # 5. HOLD
    return NHLTotalsExitDecision(
        action=ExitAction.HOLD,
        reason=ExitReason.HOLD,
        p_side=p_side, p_source=p_source,
        note="",
    )
```

- [ ] **Step 4: Test → PASS, Commit**

```bash
pytest tests/unit/strategy/exit/test_nhl_totals_exit.py -v
git add src/strategy/exit/nhl_totals_exit.py tests/unit/strategy/exit/test_nhl_totals_exit.py
git commit -m "feat(nhl): totals exit decision — over/under priority chain"
```

---

## Task 7F: NHL Totals Question Parser

**Files:**
- Modify: `src/domain/matching/market_line_parser.py`
- Test: extend `tests/unit/domain/matching/test_market_line_parser.py`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

NBA `parse_total_line()` zaten `O/U X.5` pattern'ini handle ediyor. NHL'de aynı format kullanılır → muhtemelen ek değişiklik gerekmez. Test ile doğrula.

- [ ] **Step 1: NHL totals test ekle**

`tests/unit/domain/matching/test_market_line_parser.py`'a:

```python
class TestNHLTotals:
    def test_parses_nhl_total_line(self):
        from src.domain.matching.market_line_parser import parse_total_line
        result = parse_total_line("Boston Bruins vs. Buffalo Sabres: O/U 5.5")
        assert result == (5.5, "over")

    def test_parses_short_nhl_total(self):
        from src.domain.matching.market_line_parser import parse_total_line
        result = parse_total_line("Bruins vs Sabres: O/U 6.5")
        assert result == (6.5, "over")

    def test_returns_none_for_unparsable(self):
        from src.domain.matching.market_line_parser import parse_total_line
        assert parse_total_line("Bruins win in regulation") is None
```

- [ ] **Step 2: Test → PASS (mevcut parser yeterli olacak)**

```bash
pytest tests/unit/domain/matching/test_market_line_parser.py::TestNHLTotals -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/unit/domain/matching/test_market_line_parser.py
git commit -m "test(nhl): totals parser NHL format coverage"
```

---

## Task 7G: ExitReason Enum + Totals Mapping

**Files:**
- Modify: `src/models/enums.py`
- Modify: `src/strategy/exit/_nhl_exit_mapping.py`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: ExitReason'a 5 yeni değer ekle**

`src/models/enums.py`:

```python
NHL_TOTALS_NEAR_RESOLVE = "nhl_totals_near_resolve"
NHL_TOTALS_SCALE_OUT = "nhl_totals_scale_out"
NHL_TOTALS_PREDICTIVE_DEAD = "nhl_totals_predictive_dead"
NHL_TOTALS_STRUCTURAL_DAMAGE = "nhl_totals_structural_damage"
NHL_TOTALS_HOLD = "nhl_totals_hold"
```

- [ ] **Step 2: _nhl_exit_mapping.py — totals mapper**

```python
from src.strategy.exit.nhl_totals_exit import (
    NHLTotalsExitDecision,
    ExitAction as TExitAction,
    ExitReason as TExitReason,
)

_TOTALS_REASON_MAP = {
    TExitReason.NEAR_RESOLVE: ExitReason.NHL_TOTALS_NEAR_RESOLVE,
    TExitReason.SCALE_OUT: ExitReason.NHL_TOTALS_SCALE_OUT,
    TExitReason.PREDICTIVE_DEAD: ExitReason.NHL_TOTALS_PREDICTIVE_DEAD,
    TExitReason.STRUCTURAL_DAMAGE: ExitReason.NHL_TOTALS_STRUCTURAL_DAMAGE,
}


def map_nhl_totals_decision(decision: NHLTotalsExitDecision) -> NHLSignal | None:
    if decision.action == TExitAction.HOLD:
        return None
    reason = _TOTALS_REASON_MAP.get(decision.reason, ExitReason.SCORE_EXIT)
    detail = decision.note
    if decision.p_side is not None:
        detail += f" | p_side={decision.p_side:.3f} ({decision.p_source})"
    partial = decision.action == TExitAction.SELL_50
    return NHLSignal(
        reason=reason,
        partial=partial,
        sell_pct=0.50 if partial else 1.00,
        detail=detail,
    )
```

- [ ] **Step 3: Test (mevcut test_nhl_exit_mapping.py'a)**

```python
class TestTotalsMapping:
    def test_hold_returns_none(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_totals_decision
        from src.strategy.exit.nhl_totals_exit import (
            NHLTotalsExitDecision, ExitAction, ExitReason,
        )
        d = NHLTotalsExitDecision(
            action=ExitAction.HOLD, reason=ExitReason.HOLD,
            p_side=0.5, p_source="x", note="",
        )
        assert map_nhl_totals_decision(d) is None

    def test_predictive_dead_maps_to_nhl_totals_reason(self):
        from src.strategy.exit._nhl_exit_mapping import map_nhl_totals_decision
        from src.strategy.exit.nhl_totals_exit import (
            NHLTotalsExitDecision, ExitAction, ExitReason,
        )
        from src.models.enums import ExitReason as GExitReason
        d = NHLTotalsExitDecision(
            action=ExitAction.SELL_ALL, reason=ExitReason.PREDICTIVE_DEAD,
            p_side=0.10, p_source="empirical", note="p_over=0.10",
        )
        sig = map_nhl_totals_decision(d)
        assert sig.reason == GExitReason.NHL_TOTALS_PREDICTIVE_DEAD
        assert sig.partial is False
```

- [ ] **Step 4: Test → PASS, Commit**

```bash
pytest tests/unit/strategy/exit/test_nhl_exit_mapping.py -v
git add src/models/enums.py src/strategy/exit/_nhl_exit_mapping.py tests/unit/strategy/exit/test_nhl_exit_mapping.py
git commit -m "feat(nhl): totals exit reason enum + decision mapping"
```

---

## Task 7H: NHL Totals Dispatch Helper

**Files:**
- Create: `src/strategy/exit/_nhl_totals_dispatch.py`
- Test: `tests/unit/strategy/exit/test_nhl_totals_dispatch.py`

**Mantık:** Position'da `total_line` ve `total_side` (NBA için Task 1'de eklendi, NHL aynı kullanır).

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Failing test**

`tests/unit/strategy/exit/test_nhl_totals_dispatch.py`:

```python
"""NHL totals dispatch wiring tests."""
from __future__ import annotations

from types import SimpleNamespace

from src.models.enums import ExitReason
from src.strategy.exit._nhl_totals_dispatch import check_nhl_totals_exit
from src.strategy.exit.nhl_totals_exit import NHLTotalsExitConfig


def _pos(**kw):
    defaults = dict(
        entry_price=0.45, current_price=0.52, bid_price=0.50,
        scaled_out_50=False, sport_tag="nhl", direction="BUY_YES",
        total_line=5.5, total_side="over",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_returns_none_when_score_info_missing():
    sig = check_nhl_totals_exit(_pos(), {}, 0.5, NHLTotalsExitConfig(), {})
    assert sig is None


def test_returns_none_when_total_line_missing():
    pos = _pos(total_line=None)
    score_info = {"available": True, "period": 3, "clock_seconds": 300, "our_score": 3, "opp_score": 2}
    sig = check_nhl_totals_exit(pos, score_info, 0.5, NHLTotalsExitConfig(), {})
    assert sig is None


def test_near_resolve_when_bid_high():
    pos = _pos(bid_price=0.95)
    score_info = {"available": True, "period": 3, "clock_seconds": 300, "our_score": 4, "opp_score": 2}
    sig = check_nhl_totals_exit(pos, score_info, 0.5, NHLTotalsExitConfig(), {})
    assert sig is not None
    assert sig.reason == ExitReason.NHL_TOTALS_NEAR_RESOLVE


def test_predictive_dead_under_when_too_many_goals():
    """Under 5.5, current 6 → over zaten gerçekleşti, p_under=0 → PREDICTIVE_DEAD."""
    pos = _pos(total_side="under", bid_price=0.20, total_line=5.5)
    score_info = {"available": True, "period": 3, "clock_seconds": 300, "our_score": 3, "opp_score": 3}
    sig = check_nhl_totals_exit(pos, score_info, 0.5, NHLTotalsExitConfig(), {})
    assert sig is not None
    assert sig.reason == ExitReason.NHL_TOTALS_PREDICTIVE_DEAD


def test_uses_current_total_from_scores():
    """current_total = our_score + opp_score doğru hesaplanır."""
    pos = _pos(total_side="over", bid_price=0.40, total_line=5.5)
    score_info = {"available": True, "period": 3, "clock_seconds": 600, "our_score": 5, "opp_score": 0}
    # current_total = 5, target 5.5, p_over = high (1 gol yeter, 10 dk var)
    sig = check_nhl_totals_exit(pos, score_info, 0.5, NHLTotalsExitConfig(), {})
    assert sig is None  # HOLD beklenir
```

- [ ] **Step 2: FAIL**

```bash
pytest tests/unit/strategy/exit/test_nhl_totals_dispatch.py -v
```

- [ ] **Step 3: Implement**

`src/strategy/exit/_nhl_totals_dispatch.py`:

```python
"""NHL totals dispatch: score_info + Position → NHLSignal | None.

Strategy katmanı, I/O yok, monitor.py import yok.
"""
from __future__ import annotations

from src.domain.math.nhl_totals_probability import p_over_hybrid
from src.models.position import Position
from src.strategy.exit._nhl_exit_mapping import NHLSignal, map_nhl_totals_decision
from src.strategy.exit.nhl_totals_exit import NHLTotalsExitConfig, decide_nhl_totals_exit


def check_nhl_totals_exit(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,
    nhl_totals_cfg: NHLTotalsExitConfig,
    nhl_totals_table: dict,
) -> NHLSignal | None:
    """Decide NHL totals exit signal. Returns None → HOLD."""
    period = score_info.get("period") or score_info.get("period_number")
    clock_seconds = score_info.get("clock_seconds")
    our_score = score_info.get("our_score")
    opp_score = score_info.get("opp_score")

    target_total = getattr(pos, "total_line", None)
    side = getattr(pos, "total_side", None) or "over"

    if any(v is None for v in (period, clock_seconds, our_score, opp_score, target_total)):
        return None

    current_total = int(our_score + opp_score)

    def _p_fn(p: int, c: int, s: int, t: float) -> tuple[float, str]:
        return p_over_hybrid(p, c, s, t, table=nhl_totals_table)

    decision = decide_nhl_totals_exit(
        cfg=nhl_totals_cfg,
        entry_price=pos.entry_price,
        current_bid=pos.bid_price,
        current_price=pos.current_price,
        scaled_out_50=pos.scaled_out_50,
        period=period,
        seconds_remaining=clock_seconds,
        current_total=current_total,
        target_total=float(target_total),
        side=side,
        p_over_fn=_p_fn,
    )
    return map_nhl_totals_decision(decision)
```

- [ ] **Step 4: Test → PASS, Commit**

```bash
pytest tests/unit/strategy/exit/test_nhl_totals_dispatch.py -v
git add src/strategy/exit/_nhl_totals_dispatch.py tests/unit/strategy/exit/test_nhl_totals_dispatch.py
git commit -m "feat(nhl): totals dispatch — score_info to NHLSignal"
```

---

## Task 7I: Config + Settings + Gate Filter (Totals)

**Files:**
- Modify: `config.yaml`, `src/config/settings.py`, `src/strategy/entry/gate.py`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: config.yaml ekle**

`entry:` bloğu:

```yaml
  nhl_totals_min_price: 0.20
  nhl_totals_max_price: 0.80
  nhl_totals_min_target_total: 4.5
  nhl_totals_min_volume: 3000.0
```

Root level:

```yaml
exit_nhl_totals:
  near_resolve_threshold: 0.94
  scale_out_threshold: 0.85
  structural_damage_ratio: 0.30
  predictive_safety_margin: 0.03
```

- [ ] **Step 2: settings.py**

```python
class ExitNhlTotalsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    near_resolve_threshold: float = 0.94
    scale_out_threshold: float = 0.85
    structural_damage_ratio: float = 0.30
    predictive_safety_margin: float = 0.03


# AppConfig'e ekle:
    exit_nhl_totals: ExitNhlTotalsConfig = ExitNhlTotalsConfig()


# EntryConfig'e ekle:
    nhl_totals_min_price: float = 0.20
    nhl_totals_max_price: float = 0.80
    nhl_totals_min_target_total: float = 4.5
    nhl_totals_min_volume: float = 3000.0
```

- [ ] **Step 3: gate.py — totals NHL filter**

`GateConfig` dataclass'a:

```python
    nhl_totals_min_price: float = field(default=0.20)
    nhl_totals_max_price: float = field(default=0.80)
    nhl_totals_min_target_total: float = field(default=4.5)
    nhl_totals_min_volume: float = field(default=3000.0)
```

`_check_filters()` `if market_type == "totals":` bloğunu sport-aware yap (Task 6I'da puck_line için yaptığımıza paralel):

```python
    elif market_type == "totals":
        sport_low = (sport_tag or "").lower()
        if sport_low in ("nhl", "ahl", "icehockey_nhl"):
            if polymarket_price < cfg.nhl_totals_min_price or polymarket_price > cfg.nhl_totals_max_price:
                return "PRICE_OUT_OF_RANGE"
            if total_line is not None and total_line < cfg.nhl_totals_min_target_total:
                return "TOTAL_TOO_LOW"
            if volume < cfg.nhl_totals_min_volume:
                return "VOLUME_TOO_LOW"
        else:
            # NBA pattern
            if polymarket_price < cfg.totals_min_price or polymarket_price > cfg.totals_max_price:
                return "PRICE_OUT_OF_RANGE"
            if total_line is not None and total_line < cfg.totals_min_target_total:
                return "TOTAL_TOO_LOW"
```

- [ ] **Step 4: Test (gate test'e ekle)**

```python
def test_nhl_totals_market_passes_filter(make_gate, make_market):
    gate = make_gate(active_sports=["icehockey_nhl"])
    market = make_market(
        sport_tag="nhl",
        sports_market_type="totals",
        yes_price=0.45,
        volume_24h=5000.0,
    )
    # total_line gate run() içinde Signal'a propagate edilir; market düzeyinde set
    results = gate.run([market])
    assert results[0].skipped_reason not in ("INACTIVE_SPORT", "PRICE_OUT_OF_RANGE", "VOLUME_TOO_LOW")
```

- [ ] **Step 5: Test → PASS, Commit**

```bash
pytest tests/unit/strategy/entry/test_gate.py -v
git add config.yaml src/config/settings.py src/strategy/entry/gate.py tests/unit/strategy/entry/test_gate.py
git commit -m "feat(nhl): totals entry filter (config + gate dispatch)"
```

---

## Task 7J: monitor.py + exit_processor + factory Wiring (Totals)

**Files:**
- Modify: `src/strategy/exit/monitor.py`, `src/orchestration/exit_processor.py`, `src/orchestration/agent.py`, `src/orchestration/factory.py`

**Mantık:** Task 6J'de eklenen `smt == "spreads"` branch'in yanına `smt == "totals"` ekle.

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: monitor.py — totals branch ekle**

```python
    if _is_hockey_family(pos.sport_tag) and score_info.get("available"):
        smt = (pos.sports_market_type or "moneyline").lower()
        if smt == "spreads":
            from src.strategy.exit._nhl_puck_line_dispatch import check_nhl_puck_line_exit
            nhl_sig = check_nhl_puck_line_exit(...)  # Task 6J'den
        elif smt == "totals":
            from src.strategy.exit._nhl_totals_dispatch import check_nhl_totals_exit
            nhl_sig = check_nhl_totals_exit(
                pos, score_info, elapsed_pct,
                nhl_totals_cfg if nhl_totals_cfg is not None else _DEFAULT_NHL_TOTALS_CFG,
                nhl_totals_table if nhl_totals_table is not None else {},
            )
        else:
            nhl_sig = check_nhl_exit(...)
```

`evaluate()` signature'a 2 yeni param:

```python
    nhl_totals_cfg: "NHLTotalsExitConfig | None" = None,
    nhl_totals_table: dict | None = None,
```

Module-level default:

```python
from src.strategy.exit.nhl_totals_exit import NHLTotalsExitConfig
_DEFAULT_NHL_TOTALS_CFG = NHLTotalsExitConfig()
```

monitor.py satır kontrolü — şu an ~405 (Task 6J sonrası). Totals eklemeleri ~5 satır → ~410. Limit aşımı: bir helper'ı `_guard_helpers.py`'a taşı (Task 6J'de planlanmıştı).

- [ ] **Step 2: exit_processor.py — totals helpers**

```python
def _nhl_totals_cfg(self):
    from src.strategy.exit.nhl_totals_exit import NHLTotalsExitConfig
    cfg = getattr(self.deps.state, "config", None)
    if cfg is None or not hasattr(cfg, "exit_nhl_totals"):
        return NHLTotalsExitConfig()
    tc = cfg.exit_nhl_totals
    return NHLTotalsExitConfig(
        near_resolve_threshold=tc.near_resolve_threshold,
        scale_out_threshold=tc.scale_out_threshold,
        structural_damage_ratio=tc.structural_damage_ratio,
        predictive_safety_margin=tc.predictive_safety_margin,
    )

def _nhl_totals_table(self) -> dict:
    return getattr(self.deps, "nhl_totals_table", {}) or {}
```

`evaluate()` çağrısına ekle:

```python
nhl_totals_cfg=self._nhl_totals_cfg(),
nhl_totals_table=self._nhl_totals_table(),
```

- [ ] **Step 3: agent.py — AgentDeps'e ekle**

```python
nhl_totals_table: dict = field(default_factory=dict)
```

- [ ] **Step 4: factory.py — table load + inject**

```python
from src.infrastructure.repositories.nhl_totals_repository import load_table as _load_nhl_totals_table_raw

def _load_nhl_totals_table() -> dict:
    try:
        return _load_nhl_totals_table_raw()
    except FileNotFoundError:
        logger.warning("NHL totals table not found — Skellam fallback only")
        return {}


# build_agent() içinde:
nhl_totals_table = _load_nhl_totals_table()


# AgentDeps(...) constructor'a ekle:
nhl_totals_table=nhl_totals_table,
```

- [ ] **Step 5: Tam suite + commit**

```bash
pytest -q | tail -5
# Beklenen: ~1395+ passed
git add src/strategy/exit/monitor.py src/orchestration/exit_processor.py src/orchestration/agent.py src/orchestration/factory.py
git commit -m "feat(nhl): totals wiring (monitor + exit_processor + factory)"
```

---

## Task 7K: Totals Integration Smoke Test

**Files:**
- Create: `tests/integration/test_nhl_totals_pipeline_smoke.py`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Smoke test (Task 6K paterne paralel)**

```python
"""NHL totals pipeline smoke."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.models.market import MarketData
from src.strategy.entry.gate import EntryGate, GateConfig


def _make_nhl_totals_market(yes_price: float = 0.50) -> MarketData:
    return MarketData(
        condition_id="nhl_t_001",
        question="Boston Bruins vs. Buffalo Sabres: O/U 5.5",
        slug="bruins-sabres-ou-5p5",
        yes_token_id="tok_yes",
        no_token_id="tok_no",
        yes_price=yes_price,
        no_price=1.0 - yes_price,
        liquidity=5000.0,
        volume_24h=4000.0,
        end_date_iso="2026-06-01T00:00:00Z",
        match_start_iso=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        event_id="evt_bos_buf",
        sport_tag="nhl",
        sports_market_type="totals",
    )


def _make_gate() -> EntryGate:
    cfg = GateConfig(
        active_sports=["icehockey_nhl"],
        min_favorite_probability=0.50,
        max_entry_price=0.80,
        max_positions=10, max_exposure_pct=0.50,
        hard_cap_overflow_pct=0.02, min_entry_size_pct=0.015,
        confidence_bet_pct={"A": 0.05, "B": 0.03},
        max_single_bet_usdc=100.0, max_bet_pct=0.05,
        probability_weighted=True,
        min_bookmakers=1, min_sharps=0,
        min_gap_threshold=0.05, min_market_volume=3000.0,
        min_polymarket_price=0.20,
        nhl_totals_min_price=0.20, nhl_totals_max_price=0.80,
        nhl_totals_min_target_total=4.5,
        nhl_totals_min_volume=3000.0,
    )
    portfolio = MagicMock()
    portfolio.positions = {}
    portfolio.bankroll = 1000.0
    odds_result = MagicMock()
    odds_result.probability = MagicMock(probability=0.62, has_sharp=True, num_bookmakers=18.0)
    odds_result.fail_reason = None
    odds_fn = MagicMock(return_value=odds_result)
    return EntryGate(
        config=cfg, portfolio=portfolio,
        circuit_breaker=None, cooldown=None, blacklist=None,
        odds_enricher=odds_fn, manipulation_checker=None,
        edge_enricher=None, nhl_edge_enricher=None,
    )


class TestNhlTotalsPipelineSmoke:
    def test_nhl_totals_market_passes_filter(self):
        gate = _make_gate()
        market = _make_nhl_totals_market()
        results = gate.run([market])
        assert results[0].skipped_reason not in ("INACTIVE_SPORT", "PRICE_OUT_OF_RANGE", "VOLUME_TOO_LOW", "TOTAL_TOO_LOW")
```

- [ ] **Step 2: Test → PASS, Commit**

```bash
pytest tests/integration/test_nhl_totals_pipeline_smoke.py -v
git add tests/integration/test_nhl_totals_pipeline_smoke.py
git commit -m "test(nhl): totals pipeline smoke"
```

---

## Task 7L: Scanner — NHL spreads/totals'a izin

**Files:**
- Modify: `src/orchestration/scanner.py`

NBA için scanner zaten `_NBA_TAGS in {basketball_nba}` için spreads/totals'a izin veriyor. NHL için aynı pattern.

- [ ] **Step 1: scanner.py'da NHL tag set + SMT check**

```bash
grep -n "_NBA_TAGS\|_NBA_ALLOWED_SMT" src/orchestration/scanner.py
```

Mevcut blok:

```python
if _normalize(m.sport_tag) in _NBA_TAGS:
    if m.sports_market_type not in _NBA_ALLOWED_SMT:
        return False
elif m.sports_market_type != "moneyline":
    return False
```

Yeni:

```python
_NHL_TAGS = frozenset({"nhl", "ahl"})
_NHL_ALLOWED_SMT = frozenset({"moneyline", "spreads", "totals"})

# ... içeride:
if _normalize(m.sport_tag) in _NBA_TAGS:
    if m.sports_market_type not in _NBA_ALLOWED_SMT:
        return False
elif _normalize(m.sport_tag) in _NHL_TAGS:
    if m.sports_market_type not in _NHL_ALLOWED_SMT:
        return False
elif m.sports_market_type != "moneyline":
    return False
```

- [ ] **Step 2: Scanner test ekle (mevcut paterne uygun)**

`tests/unit/orchestration/test_scanner.py` (varsa, yoksa skip):

```python
def test_nhl_spread_market_passes():
    # ... scanner with NHL spread market ...
    pass


def test_nhl_totals_market_passes():
    pass
```

- [ ] **Step 3: Test + commit**

```bash
pytest tests/unit/orchestration/ -v -k scanner
git add src/orchestration/scanner.py
git commit -m "feat(nhl): scanner allows NHL spreads + totals SMT"
```

---

# TASK 8: 3-way ML — SKIP

Polymarket NHL'de 3-way market nadir görülür. Task 5 (1 hafta dry-run) verisinde sıkça görülürse sonradan eklenir.

DECISIONS.md'e not düş:

```markdown
## NHL 3-way ML — Skip (v1)

**Karar (2026-04-28)**: NHL 3-way regulation winner market'i Task 6/7 kapsamı dışı bırakıldı. Polymarket NHL'de bu market type %5'ten az gözlemlendi (manuel inceleme). MVP scope odakta tutmak için skip; Task 5 dry-run verisinde sıkça yakalanırsa Task 8 olarak açılır.
```

---

# TASK 9: Final Cleanup

## Task 9A: DECISIONS.md NHL Özet

**Files:**
- Modify: `DECISIONS.md`

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: DECISIONS.md'a NHL Puck Line + NHL Totals bölümleri ekle**

```markdown
## NHL Puck Line (Task 6, 2026-04-28)

**Entry:**
- Standart line: -1.5 (Polymarket'te %95 örnekler).
- Fiyat aralığı 0.20-0.80, volume ≥ 3000 USDC.
- Gap threshold ana moneyline ile aynı (0.05).

**Exit (decide_nhl_puck_line_exit, priority sıralı):**
1. NEAR_RESOLVE — bid ≥ 0.94 → SELL_ALL
2. SCALE_OUT — bid ≥ 0.85 + ilk kez → SELL_50
3. PREDICTIVE_DEAD — p_cover < bid + 0.03 (hybrid: empirical → Skellam fallback) → SELL_ALL
4. STRUCTURAL_DAMAGE — current_price/entry < 0.30 → SELL_ALL
5. HOLD

**Math:**
- Skellam dağılımı: home-away skor farkı değişimi ~ Skellam(λ_home×t, λ_away×t).
- λ_5v5 = 0.000853 per-team-per-second (lig avg 6.142 / 2 / 3600).
- Cover threshold: final_margin >= 2 (favori -1.5 için).

**Empirical tablo:**
- 4198 maç, MoneyPuck 2022-2024 sezonları.
- Key: `period_currentMargin_secondsRemaining` → p_favorite_covers.
- Wilson CI %95, min_sample=30.
- SO winner +1 gol konvansiyonu (Polymarket "incl. OT/SO" resolution).

**Empty net:** Heuristik — ESPN raw_status'ta flag yok. P3 son 3dk + 1 gol fark → empirical tabloda inheresi yansır (modifier gereksiz).

---

## NHL Totals (Task 7, 2026-04-28)

**Entry:**
- Target lines: 5.5 ve 6.5 (Polymarket NHL standart).
- Fiyat aralığı 0.20-0.80, min target 4.5 (4.5 altı thin market).
- Volume ≥ 3000 USDC.
- YES = OVER, NO = UNDER (NBA konvansiyonu paralel).

**Exit (decide_nhl_totals_exit, priority sıralı):**
1. NEAR_RESOLVE — bid ≥ 0.94 → SELL_ALL
2. SCALE_OUT — bid ≥ 0.85 + ilk kez → SELL_50
3. PREDICTIVE_DEAD — p_side < bid + 0.03 (over: p_over; under: 1 - p_over) → SELL_ALL
4. STRUCTURAL_DAMAGE — current_price/entry < 0.30 → SELL_ALL
5. HOLD

**Math:**
- Poisson dağılımı: future_total_goals ~ Poisson(λ_total × t).
- λ_total = 6.142 / 3600 = 0.001706 per-second.
- P(over X.5) = P(future_goals >= ceil(X + 0.5 - current)).

**Empirical tablo:**
- Aynı 4198 maç, target 5.5 + 6.5 için ayrı bucket.
- Key: `period_currentTotal_secondsRemaining_targetTotal` → p_over.
- SO winner +1 gol konvansiyonu (Karar 3).

**OT/SO modifier:** OT'ye gidince Over yararı yansır (her OT goal +1, SO +1). Empirical tabloda final_total bu kuralla hesaplanmıştır.

---

## NHL 3-way ML — Skip (v1)

**Karar (2026-04-28)**: NHL 3-way regulation winner market'i Task 6/7 kapsamı dışı bırakıldı. Polymarket NHL'de bu market type %5'ten az gözlemlendi. MVP scope odakta tutmak için skip; Task 5 dry-run verisinde sıkça yakalanırsa Task 8 olarak açılır.
```

- [ ] **Step 2: Commit**

```bash
git add DECISIONS.md
git commit -m "docs(nhl): puck line + totals decision rationale"
```

---

## Task 9B: Final Smoke Test — Full NHL Suite

**Files:**
- Run: tüm NHL test'leri

`ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

- [ ] **Step 1: Tam NHL suite çalıştır**

```bash
pytest tests/ -k nhl -v 2>&1 | tail -30
pytest -q 2>&1 | tail -5
```

Beklenen:
- NHL spesifik testler: ~50-60 test PASS
- Tam suite: 1395+ passed

- [ ] **Step 2: NBA regression**

```bash
pytest tests/unit/strategy/exit/test_nba_score_exit.py tests/unit/strategy/exit/test_nba_spread_exit.py tests/unit/strategy/exit/test_nba_totals_exit.py -v 2>&1 | tail -10
```

Tüm NBA test'leri PASS olmalı.

- [ ] **Step 3: ARCH check**

```bash
wc -l src/strategy/exit/monitor.py
wc -l src/strategy/exit/nhl_*.py
wc -l src/strategy/exit/_nhl_*.py
wc -l src/domain/math/nhl_*.py
grep -nE "open\(|json\.load|requests" src/strategy/exit/_nhl_*.py src/domain/math/nhl_*.py
```

Beklenen: monitor.py < 400 (gerekirse helper extract), domain/strategy I/O yok.

- [ ] **Step 4: git status temiz mi**

```bash
git status --short
```

---

## Task 9C: README NHL Bölümü

**Files:**
- Modify: `README.md`

- [ ] **Step 1: README.md'da Sport Coverage bölümüne NHL ekle**

```markdown
### NHL (Ice Hockey)
- **Markets:** Moneyline, Puck Line (-1.5), Totals (Over/Under 5.5 + 6.5).
- **Math:** Skellam (puck line), Poisson (totals), 4198-game empirical lookup hybrid.
- **Special dynamics:** SO resolution (winner +1 goal), OT goal handling, empty-net heuristic embedded in empirical table.
- **Build empirical tables:**
  ```
  python scripts/build_nhl_empirical_table.py        # moneyline
  python scripts/build_nhl_puck_line_table.py        # puck line
  python scripts/build_nhl_totals_table.py            # totals
  ```
- **Active in:** `config.yaml entry.active_sports: [icehockey_nhl]`
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(nhl): readme NHL coverage section"
```

---

## Task 9D: Final Tag

**Files:** none

- [ ] **Step 1: Tüm commit'leri özetleyen tag**

```bash
git log --oneline c803673..HEAD
git tag -a nhl-v1 -m "NHL hockey package complete: ML + Puck Line + Totals"
git log --oneline -5
```

---

## Plan Sonu

**Toplam beklenen:**
- 11 yeni source file (script + math + repo + exit + dispatch)
- 11 yeni test file (~50-60 yeni test)
- 5 modified config/wiring file
- DECISIONS.md + README.md güncellemesi

**Test count target:** 1365 → ~1420-1430 passed

**ARCH:**
- monitor.py: yine < 400 satır (gerekirse `_guard_helpers.py` extract)
- Yeni dosyalar hep < 200 satır (NBA pattern paralel boy)
- Strategy + Domain katmanları I/O sıfır
- Magic number sıfır (tüm threshold config'den)

**Risk profili:**
- mode: dry_run aktif kalır → gerçek para riski yok
- Empirical tablo build script'leri standalone, bot çalışırken üretilebilir
- Hybrid wrapper graceful degradation (tablo yok → Skellam, fonksiyon hata → HOLD)

**Sonraki:** Task 5 (dry-run kalibrasyon) bu plan'dan sonra başlar.
