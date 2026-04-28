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
Margin sign convention: home perspektifi (build-time heuristik).
  current_margin > 0 → home önde
  current_margin < 0 → home geride
  current_margin = 0 → berabere

Runtime'da bot Pinnacle line'ından favori belirler ve sign convention'ı kendi ayarlar.
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
_OUTPUT_PATH = Path("data/nhl_empirical_puck_line_table.json")

_TIME_BUCKET_SEC: int = 30       # seconds_remaining bucket width
_MARGIN_CAP: int = 5             # |margin| > 5 → bucket ±5 (rare, blowout)
_REGULATION_SECONDS: int = 3600  # 3 periods × 20 min × 60 s
_Z: float = 1.96                 # Wilson CI 95% z-score
_MIN_N: int = 30                 # min samples for a reliable estimate
_PUCK_LINE: float = 1.5          # Polymarket NHL standart puck line

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

def reconstruct_game_states_with_final_margin(shots_df: pd.DataFrame) -> pd.DataFrame:
    """30sn tick'ler + her oyunun final marjı (regulation + OT goal varsa + SO winner +1).

    Final margin convention (home perspective):
      home_won=1, regulation finish diff=2 → final_margin=2
      home_won=1, OT finish (last_period=4) → margin = home_final - away_final (1 olur)
      home_won=1, SO finish (last_period>=5) → final_margin=1 (regulation tied, SO winner +1)
      home_won=0 → analoji ile negatif

    Karar 3: SO winner için +1 gol konvansiyonu (Polymarket -1.5 SO winner cover etmez).

    Returns:
        DataFrame: game_id, period (1-3), seconds_remaining (0-3600),
        current_margin (home - away, int), final_margin (int).
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
        home_won=("homeTeamWon", "first"),
    ).to_dict("index")

    def compute_final_margin(gid: str) -> int:
        info = game_finals[gid]
        last_period = int(info["last_period"])
        home_final = int(info["home_final"])
        away_final = int(info["away_final"])
        home_won = int(info["home_won"])

        # Regulation veya OT goal — direct skor farkı (last_period 1-4)
        if last_period <= 4:
            return home_final - away_final
        # SO: regulation tied, winner +1 (Karar 3)
        return 1 if home_won == 1 else -1

    final_margins = {gid: compute_final_margin(gid) for gid in game_finals}

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

        # current_margin = home - away (home favori varsayımı, build-time)
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


def aggregate_puck_line_cover(states_df: pd.DataFrame, puck_line: float = _PUCK_LINE) -> dict:
    """Her (period, current_margin_clamped, time_bucket) için home -puck_line cover olasılığı.

    Cover condition: final_margin >= puck_line + 0.5 (line .5 olduğu için >= 2 gol fark).
    Polymarket -1.5 home cover: final_margin >= 2.

    Wilson CI 95%, min_sample=30.
    """
    df = states_df.copy()
    df["current_margin_clamped"] = df["current_margin"].clip(
        lower=-_MARGIN_CAP, upper=_MARGIN_CAP
    ).astype(int)
    df["time_bucket"] = (
        (df["seconds_remaining"] // _TIME_BUCKET_SEC) * _TIME_BUCKET_SEC
    ).astype(int)

    # Cover bool: final margin home favoriyi -1.5'i geçirdi mi
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


def print_sanity_summary(table: dict) -> None:
    """Kritik noktalarda puck-line cover olasılıklarını stdout'a yaz."""
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
    print("-" * 70 + "\n")


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build NHL puck line empirical table from MoneyPuck shot data"
    )
    parser.add_argument(
        "--seasons", type=int, nargs="+", default=_DEFAULT_SEASONS,
        help="MoneyPuck season start years (default: 2022 2023 2024)",
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

    logger.info("Reconstructing game states with final margin (30s ticks)...")
    states = reconstruct_game_states_with_final_margin(all_shots)
    logger.info("States table: %d rows", len(states))

    logger.info("Aggregating puck-line cover frequencies...")
    table = aggregate_puck_line_cover(states, puck_line=_PUCK_LINE)
    non_null = sum(1 for v in table.values() if v is not None)
    logger.info(
        "Table: %d entries (%d with sufficient samples, %d null)",
        len(table), non_null, len(table) - non_null,
    )

    print_sanity_summary(table)

    metadata = {
        "seasons": args.seasons,
        "time_bucket_sec": _TIME_BUCKET_SEC,
        "margin_cap": _MARGIN_CAP,
        "puck_line": _PUCK_LINE,
        "min_sample_size": _MIN_N,
        "wilson_z": _Z,
        "total_games": total_games,
        "favorite_assumption": "home (heuristic; runtime uses Pinnacle line)",
        "key_format": "period_currentMargin_secondsRemaining",
    }

    output = {"metadata": metadata, "puck_line_cover": table}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info("Saved → %s (%d entries)", args.output, len(table))


if __name__ == "__main__":
    main()
