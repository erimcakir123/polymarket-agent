#!/usr/bin/env python3
"""
scripts/build_nhl_totals_table.py

MoneyPuck shot-level play-by-play (data/nhl_shots/) →
NHL empirical totals (over/under) lookup table.

Standalone, tek seferlik çalışır. src/ koduna dokunmaz.
Çıktı: data/nhl_empirical_totals_table.json

Kullanım:
    python scripts/build_nhl_totals_table.py
    python scripts/build_nhl_totals_table.py --seasons 2022 2023 2024
    python scripts/build_nhl_totals_table.py --targets 5.5 6.5

Target lines: 5.5 ve 6.5 (Polymarket NHL standart) — 2 ayrı bucket (Karar 2).
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

# ── Constants ────────────────────────────────────────────────────────────────

_DEFAULT_SEASONS: list[int] = [2022, 2023, 2024]
_DATA_DIR = Path("data/nhl_shots")
_OUTPUT_PATH = Path("data/nhl_empirical_totals_table.json")

_TIME_BUCKET_SEC: int = 30       # seconds_remaining bucket width
_TOTAL_CAP: int = 12             # current_total > 12 → bucket 12 (rare)
_REGULATION_SECONDS: int = 3600  # 3 periods × 20 min × 60 s
_Z: float = 1.96                 # Wilson CI 95% z-score
_MIN_N: int = 30                 # min samples for a reliable estimate
_TARGET_TOTALS: list[float] = [5.5, 6.5]  # Polymarket NHL standart line'ları

_NEEDED_COLS = [
    "game_id", "period", "time",
    "homeTeamGoals", "awayTeamGoals",
    "homeTeamWon", "goal", "isPlayoffGame",
]


# ── I/O helpers ──────────────────────────────────────────────────────────────

def load_shots_csv(csv_path: Path, season_label: str) -> pd.DataFrame:
    """Shots CSV'yi yükle, yalnızca gerekli kolonları oku.

    season_label (orn. "2022-23") game_id'ye prefix eklenir — sezonlar arası
    game_id çakışmasını önler (her sezon 20001'den başlar).

    Returns:
        DataFrame kolonları: game_id (str, season-prefixed), season (str),
        period (int), time (float), homeTeamGoals (int), awayTeamGoals (int),
        homeTeamWon (int), goal (int), isPlayoffGame (int).
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Shots CSV missing: {csv_path}. "
            "Run scripts/build_nhl_empirical_table.py first to download."
        )
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
    df["game_id"] = season_label + "_" + df["game_id"]
    df["season"] = season_label
    return df


# ── Core computation ─────────────────────────────────────────────────────────

def reconstruct_game_states_with_final_total(shots_df: pd.DataFrame) -> pd.DataFrame:
    """30sn tick'ler + her oyunun final totalı (regulation + OT goal varsa + SO winner +1).

    Final total convention:
      last_period=3 → home_final + away_final (regulation)
      last_period=4 → home_final + away_final (OT goal data'da zaten içerilir)
      last_period>=5 → home_final + away_final + 1 (SO winner +1, Karar 3)

    Returns:
        DataFrame: game_id, period (1-3), seconds_remaining (0-3600),
        current_total (home + away, int), final_total (int).
    """
    # 1. Regulation only (tick reconstruction için)
    reg = shots_df[shots_df["period"].isin([1, 2, 3])].copy()
    reg["game_seconds"] = reg["time"]
    reg = reg.sort_values(["game_id", "game_seconds"]).reset_index(drop=True)

    # 2. Per-game final scores (tüm period'lardan, OT/SO dahil)
    game_finals = shots_df.groupby("game_id").agg(
        last_period=("period", "max"),
        home_final=("homeTeamGoals", "max"),
        away_final=("awayTeamGoals", "max"),
    ).to_dict("index")

    def compute_final_total(gid: str) -> int:
        info = game_finals[gid]
        base = int(info["home_final"]) + int(info["away_final"])
        if int(info["last_period"]) >= 5:
            return base + 1  # SO winner +1 gol (Karar 3)
        return base

    final_totals = {gid: compute_final_total(gid) for gid in game_finals}

    # 3. Tick reconstruction (mevcut empirical pattern)
    tick_times = np.arange(0.0, _REGULATION_SECONDS + _TIME_BUCKET_SEC, _TIME_BUCKET_SEC)
    sec_rem_ticks = (_REGULATION_SECONDS - tick_times).astype(int)
    period_ticks = np.minimum((tick_times // 1200).astype(int) + 1, 3)

    chunks: list[pd.DataFrame] = []
    for gid, gdf in reg.groupby("game_id", sort=False):
        times = gdf["game_seconds"].values
        home_goals = gdf["homeTeamGoals"].values
        away_goals = gdf["awayTeamGoals"].values

        # searchsorted: index of last shot at or before each tick
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


def aggregate_totals_over(states_df: pd.DataFrame, target_totals: list[float]) -> dict:
    """Her (period, current_total_clamped, time_bucket, target) için P(over) hesapla.

    Over condition: final_total > target (line .5 olduğu için final >= target + 0.5).
    Polymarket OVER 5.5: final_total >= 6.

    Wilson CI 95%, min_sample=30, n<30 ise null.
    """
    df = states_df.copy()
    df["current_total_clamped"] = df["current_total"].clip(upper=_TOTAL_CAP).astype(int)
    df["time_bucket"] = (
        (df["seconds_remaining"] // _TIME_BUCKET_SEC) * _TIME_BUCKET_SEC
    ).astype(int)

    z2 = _Z ** 2
    table: dict[str, dict | None] = {}

    for target in target_totals:
        # Over hits: final_total > target (line .5 → final >= ceil(target))
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


def print_sanity_summary(table: dict) -> None:
    """Kritik noktalarda totals over olasılıklarını stdout'a yaz."""
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
    print("-" * 80 + "\n")


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build NHL totals empirical table from MoneyPuck shot data"
    )
    parser.add_argument(
        "--seasons", type=int, nargs="+", default=_DEFAULT_SEASONS,
        help="MoneyPuck season start years (default: 2022 2023 2024)",
    )
    parser.add_argument(
        "--targets", type=float, nargs="+", default=_TARGET_TOTALS,
        help="Target totals for over/under (default: 5.5 6.5)",
    )
    parser.add_argument("--output", type=Path, default=_OUTPUT_PATH)
    parser.add_argument("--data-dir", type=Path, default=_DATA_DIR)
    args = parser.parse_args()

    dfs: list[pd.DataFrame] = []
    for season_start in args.seasons:
        season_label = f"{season_start}-{(season_start + 1) % 100:02d}"
        csv_path = args.data_dir / f"shots_{season_start}.csv"
        df = load_shots_csv(csv_path, season_label)
        logger.info(
            "Loaded %s: %d rows, %d games",
            season_label, len(df), df["game_id"].nunique(),
        )
        dfs.append(df)

    all_shots = pd.concat(dfs, ignore_index=True)
    total_games = int(all_shots["game_id"].nunique())
    logger.info(
        "Combined: %d rows, %d games across %d seasons",
        len(all_shots), total_games, len(args.seasons),
    )

    logger.info("Reconstructing game states with final total (30s ticks)...")
    states = reconstruct_game_states_with_final_total(all_shots)
    logger.info("States table: %d rows", len(states))

    logger.info("Aggregating totals over frequencies for targets %s...", args.targets)
    table = aggregate_totals_over(states, args.targets)
    non_null = sum(1 for v in table.values() if v is not None)
    logger.info(
        "Table: %d entries (%d with sufficient samples, %d null)",
        len(table), non_null, len(table) - non_null,
    )

    print_sanity_summary(table)

    metadata = {
        "seasons": args.seasons,
        "time_bucket_sec": _TIME_BUCKET_SEC,
        "total_cap": _TOTAL_CAP,
        "target_totals": args.targets,
        "min_sample_size": _MIN_N,
        "wilson_z": _Z,
        "total_games": total_games,
        "key_format": "period_currentTotal_secondsRemaining_targetTotal",
        "so_resolution": "winner +1 goal (Karar 3)",
    }

    output = {"metadata": metadata, "totals_over": table}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info("Saved → %s (%d entries)", args.output, len(table))


if __name__ == "__main__":
    main()
