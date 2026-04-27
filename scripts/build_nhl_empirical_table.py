#!/usr/bin/env python3
"""
scripts/build_nhl_empirical_table.py

MoneyPuck shot-level play-by-play (son 3 sezon: 2022-23, 2023-24, 2024-25) →
NHL empirical in-game win probability lookup table.

Standalone, tek seferlik çalışır. src/ koduna dokunmaz.
Çıktı: data/nhl_empirical_win_table.json

Kullanım:
    python scripts/build_nhl_empirical_table.py
    python scripts/build_nhl_empirical_table.py --seasons 2022 2023 2024
    python scripts/build_nhl_empirical_table.py --output data/nhl_table.json

MoneyPuck URL formatı: shots_{SEASON_START_YEAR}.csv
  2022 → 2022-23 sezonu, 2023 → 2023-24, 2024 → 2024-25

Kolon isimlerini build sırasında verify edildi (2026-04-27):
  game_id, period, time, homeTeamGoals, awayTeamGoals,
  homeTeamWon, goal, isPlayoffGame — hepsi mevcut.
  'goal' = binary 0/1 flag; spec'teki event=='GOAL' ile eşdeğer.

Gereksinimler (proje bağımlılıkları dışında):
    pip install pandas numpy
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_DEFAULT_SEASONS: list[int] = [2022, 2023, 2024]
_BASE_URL = "https://moneypuck.com/moneypuck/playerData/shots/shots_{season}.csv"
_UA = "Mozilla/5.0 (compatible; NHL-empirical-builder/1.0)"

_DATA_DIR = Path("data/nhl_shots")
_OUTPUT_PATH = Path("data/nhl_empirical_win_table.json")

_TIME_BUCKET_SEC: int = 30       # seconds_remaining bucket width
_DEFICIT_CAP: int = 4            # score diffs > 4 treated as 4 (rare, noisy)
_REGULATION_SECONDS: int = 3600  # 3 periods × 20 min × 60 s
_Z: float = 1.96                 # Wilson CI 95% z-score
_MIN_N: int = 30                 # min samples for a reliable estimate

_NEEDED_COLS = [
    "game_id", "period", "time",
    "homeTeamGoals", "awayTeamGoals",
    "homeTeamWon", "goal", "isPlayoffGame",
]


# ── I/O helpers ──────────────────────────────────────────────────────────────

def download_if_missing(url: str, dest: Path) -> Path:
    """Dosya yoksa URL'den indir, varsa önbellekten kullan.

    MoneyPuck sunucusu User-Agent gerektirdiğinden Request nesnesi kullanılır;
    urlretrieve doğrudan header desteği sunmadığından urlopen + write tercih edildi.

    Returns:
        dest: İndirilen (veya mevcut) dosyanın Path'i.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        logger.info("Cache hit: %s", dest.name)
        return dest
    logger.info("Downloading %s → %s", url, dest)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())
    logger.info("Saved %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
    return dest


def load_shots_csv(csv_path: Path) -> pd.DataFrame:
    """Shots CSV'yi yükle, yalnızca gerekli kolonları oku.

    Returns:
        DataFrame kolonları: game_id (str), period (int), time (float),
        homeTeamGoals (int), awayTeamGoals (int), homeTeamWon (int),
        goal (int), isPlayoffGame (int).
    """
    df = pd.read_csv(csv_path, usecols=_NEEDED_COLS, low_memory=False)
    df = df.dropna(subset=["game_id", "period", "time", "homeTeamWon"])
    df = df.astype({
        "game_id": str,
        "period": int,
        "time": float,
        "homeTeamGoals": int,
        "awayTeamGoals": int,
        "homeTeamWon": int,
        "goal": int,
        "isPlayoffGame": int,
    })
    return df


# ── Core computation ─────────────────────────────────────────────────────────

def reconstruct_game_states(shots_df: pd.DataFrame) -> pd.DataFrame:
    """Shot satırlarından 30 saniyelik tick'ler üret; her tick'te anlık skoru belirle.

    1. Yalnızca regulation period'ları (1, 2, 3) filtrele.
    2. game_seconds = (period-1)*1200 + time (saniye cinsinden).
    3. game_id + game_seconds'a göre sırala.
    4. Her oyun için game_id → homeTeamWon eşlemesini çıkar (oyun-düzeyinde sabit).
    5. Tüm oyunlar için 0, 30, ..., 3600 tick noktaları üret.
    6. pd.merge_asof(by='game_id', direction='backward') ile her tick'e en son
       önceki shot'ın skorunu birleştir (ilk shot'tan önceki tick'ler 0-0).
    7. abs_score_diff ve leading_team_won hesapla; berabere (diff==0) → NaN.

    Returns:
        DataFrame kolonları: game_id, period (1-3), seconds_remaining (oyun toplamı,
        0-3600), abs_score_diff, leading_team_won (0.0/1.0/NaN).
    """
    # 1. Regulation only
    reg = shots_df[shots_df["period"].isin([1, 2, 3])].copy()

    # 2. Game-seconds elapsed
    reg["game_seconds"] = (reg["period"] - 1) * 1200 + reg["time"]

    # 3. Sort for merge_asof requirement
    reg = reg.sort_values(["game_id", "game_seconds"]).reset_index(drop=True)

    # 4. Game-level winner map (homeTeamWon is constant per game)
    game_results = (
        reg.groupby("game_id", sort=False)["homeTeamWon"]
        .first()
        .reset_index()
    )

    # Score timeline: one row per unique (game_id, game_seconds); keep last score
    score_tl = (
        reg[["game_id", "game_seconds", "homeTeamGoals", "awayTeamGoals"]]
        .drop_duplicates(subset=["game_id", "game_seconds"], keep="last")
    )

    # 5. Tick table: all (game_id, tick_seconds) combinations
    tick_times = np.arange(0, _REGULATION_SECONDS + _TIME_BUCKET_SEC, _TIME_BUCKET_SEC)
    game_ids = reg["game_id"].unique()
    ticks = (
        pd.DataFrame({
            "game_id": np.repeat(game_ids, len(tick_times)),
            "tick_seconds": np.tile(tick_times, len(game_ids)).astype(float),
        })
        .sort_values(["game_id", "tick_seconds"])
        .reset_index(drop=True)
    )

    # 6. Vectorized score lookup via merge_asof (no per-row iteration)
    merged = pd.merge_asof(
        ticks,
        score_tl,
        left_on="tick_seconds",
        right_on="game_seconds",
        by="game_id",
        direction="backward",
    )

    # Fill ticks before the first shot in a game (score = 0-0)
    merged["homeTeamGoals"] = merged["homeTeamGoals"].fillna(0).astype(int)
    merged["awayTeamGoals"] = merged["awayTeamGoals"].fillna(0).astype(int)

    # Attach game result
    merged = merged.merge(game_results, on="game_id", how="left")

    # Derived fields
    score_diff = merged["homeTeamGoals"] - merged["awayTeamGoals"]
    merged["abs_score_diff"] = score_diff.abs()
    merged["seconds_remaining"] = _REGULATION_SECONDS - merged["tick_seconds"]
    merged["period"] = ((merged["tick_seconds"] // 1200) + 1).clip(upper=3).astype(int)

    # 7. leading_team_won: home leading → homeTeamWon; away leading → 1-homeTeamWon; tied → NaN
    merged["leading_team_won"] = np.where(
        score_diff > 0, merged["homeTeamWon"],
        np.where(score_diff < 0, 1 - merged["homeTeamWon"], np.nan),
    )

    return merged[[
        "game_id", "period", "seconds_remaining",
        "abs_score_diff", "leading_team_won",
    ]].reset_index(drop=True)


def aggregate_win_frequencies(states_df: pd.DataFrame) -> dict:
    """Her (period, deficit, seconds) bucket için empirical kazanma olasılığı hesapla.

    Gruplar:    (period, abs_score_diff_clamped, time_bucket)
    Wilson CI:  centre = (wins + z²/2) / (n + z²)
                margin = z/(1+z²/n) * sqrt(p*(1-p)/n + z²/(4n²))

    Returns:
        Nested dict, key format "period_deficit_seconds_remaining".
        Değer: {"win_prob": float, "ci_low": float, "ci_high": float, "n": int}
               veya None (n < MIN_N → güvenilmez).
    """
    df = states_df.dropna(subset=["leading_team_won"]).copy()

    df["abs_score_diff_clamped"] = df["abs_score_diff"].clip(upper=_DEFICIT_CAP).astype(int)
    df["time_bucket"] = (
        (df["seconds_remaining"] // _TIME_BUCKET_SEC) * _TIME_BUCKET_SEC
    ).astype(int)

    grouped = (
        df.groupby(["period", "abs_score_diff_clamped", "time_bucket"], sort=True)
        ["leading_team_won"]
        .agg(wins="sum", n="count")
        .reset_index()
    )

    z2 = _Z ** 2
    table: dict[str, dict | None] = {}

    for row in grouped.itertuples(index=False):
        period = int(row.period)
        deficit = int(row.abs_score_diff_clamped)
        seconds = int(row.time_bucket)
        wins = float(row.wins)
        n = int(row.n)
        key = f"{period}_{deficit}_{seconds}"

        if n < _MIN_N:
            table[key] = None
            continue

        p_hat = wins / n
        centre = (p_hat + z2 / (2 * n)) / (1 + z2 / n)
        margin = (_Z / (1 + z2 / n)) * math.sqrt(
            p_hat * (1 - p_hat) / n + z2 / (4 * n ** 2)
        )
        table[key] = {
            "win_prob": round(centre, 4),
            "ci_low": round(max(0.0, centre - margin), 4),
            "ci_high": round(min(1.0, centre + margin), 4),
            "n": n,
        }

    return table


def compute_avg_goals_per_game(
    states_df: pd.DataFrame,
    raw_shots_dfs: list[pd.DataFrame],
) -> float:
    """Ortalama gol/maç hesapla; tüm sezonlar birleştirilir.

    Spec notu: event=='GOAL' yerine goal==1 flag'ı kullanılır — ikisi eşdeğer
    ama binary flag daha hızlı ve güvenilir.

    Args:
        states_df:     Kullanılmaz; signature tutarlılığı için tutulmuştur.
        raw_shots_dfs: Her sezon için tam ham shot DataFrame'leri.

    Returns:
        Ortalama gol sayısı (float). Hiç maç yoksa 0.0.
    """
    goal_counts: list[pd.Series] = []
    game_id_cols: list[pd.Series] = []

    for df in raw_shots_dfs:
        goal_counts.append(df.loc[df["goal"] == 1, "game_id"])
        game_id_cols.append(df["game_id"])

    total_goals = sum(len(s) for s in goal_counts)
    unique_games = pd.concat(game_id_cols).nunique() if game_id_cols else 0

    if unique_games == 0:
        return 0.0
    return round(total_goals / unique_games, 3)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build NHL empirical win probability table from MoneyPuck data"
    )
    parser.add_argument(
        "--seasons", nargs="+", type=int, default=_DEFAULT_SEASONS,
        help="MoneyPuck season start years (default: 2022 2023 2024)",
    )
    parser.add_argument("--output", type=Path, default=_OUTPUT_PATH)
    parser.add_argument("--data-dir", type=Path, default=_DATA_DIR)
    args = parser.parse_args()

    raw_dfs: list[pd.DataFrame] = []
    for season in args.seasons:
        url = _BASE_URL.format(season=season)
        dest = args.data_dir / f"shots_{season}.csv"
        csv_path = download_if_missing(url, dest)
        logger.info("Loading season %d…", season)
        df = load_shots_csv(csv_path)
        logger.info("  %d rows, %d games", len(df), df["game_id"].nunique())
        raw_dfs.append(df)

    combined = pd.concat(raw_dfs, ignore_index=True)
    logger.info(
        "Combined: %d rows, %d games across %d seasons",
        len(combined), combined["game_id"].nunique(), len(args.seasons),
    )

    logger.info("Reconstructing game states (30s ticks)…")
    states = reconstruct_game_states(combined)
    logger.info("States table: %d rows", len(states))

    logger.info("Aggregating win frequencies…")
    table = aggregate_win_frequencies(states)
    non_null = sum(1 for v in table.values() if v is not None)
    logger.info("Table: %d entries (%d with sufficient samples)", len(table), non_null)

    avg_goals = compute_avg_goals_per_game(states, raw_dfs)
    logger.info("Average goals/game: %.3f", avg_goals)

    output = {
        "meta": {
            "seasons": args.seasons,
            "time_bucket_sec": _TIME_BUCKET_SEC,
            "deficit_cap": _DEFICIT_CAP,
            "min_sample_size": _MIN_N,
            "wilson_z": _Z,
            "avg_goals_per_game": avg_goals,
            "total_games": int(combined["game_id"].nunique()),
            "key_format": "period_deficit_seconds_remaining",
        },
        "table": table,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info("Saved → %s", args.output)


if __name__ == "__main__":
    main()
