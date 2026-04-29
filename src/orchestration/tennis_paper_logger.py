"""Tennis paper logger — JSONL records of would-be predictions/decisions.

Append-only file. Each match starts as one line on pre_match call,
in-match snapshots appended to its in_match_log, finalize writes outcome.
Re-reads + re-writes file for updates (Phase 0 small-scale, fine).
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreMatchPrediction:
    model_p_win_a: float
    model_p_win_b: float
    polymarket_a_price: float
    polymarket_b_price: float
    edge: float
    would_enter: bool
    would_size_usdc: float


@dataclass(frozen=True)
class InMatchSnapshot:
    timestamp_iso: str
    game_n: int
    set_score: str
    game_score: str
    server: str  # "A" or "B"
    model_p_win_a: float
    bid_a: float
    would_action: Literal["HOLD", "SELL_25", "SELL_50", "SELL_75", "SELL_ALL"]


@dataclass
class ActualOutcome:
    winner: Literal["a", "b"]
    final_score: str
    match_duration_min: int


@dataclass
class PaperMatchRecord:
    match_id: str
    tournament: str
    surface: str
    format: str
    player_a: str
    player_b: str
    pre_match: PreMatchPrediction
    in_match_log: list[dict] = field(default_factory=list)
    actual_outcome: dict | None = None


class TennisPaperLogger:
    """JSONL paper trade logger. One record per match."""

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_pre_match(
        self,
        match_id: str,
        tournament: str,
        surface: str,
        format: str,
        player_a: str,
        player_b: str,
        pre_match: PreMatchPrediction,
    ) -> None:
        """Create a new match record."""
        record = PaperMatchRecord(
            match_id=match_id,
            tournament=tournament,
            surface=surface,
            format=format,
            player_a=player_a,
            player_b=player_b,
            pre_match=pre_match,
        )
        self._append_record(record)

    def append_in_match(self, match_id: str, snapshot: InMatchSnapshot) -> None:
        """Append snapshot to in_match_log of existing match record."""
        records = self._read_all_records()
        target = self._find_record(records, match_id)
        if target is None:
            logger.warning("paper_log: match_id %s not found for in-match append", match_id)
            return
        target["in_match_log"].append(asdict(snapshot))
        self._write_all_records(records)

    def finalize_match(
        self,
        match_id: str,
        winner: Literal["a", "b"],
        final_score: str,
        match_duration_min: int,
    ) -> None:
        """Write actual outcome to existing match record."""
        records = self._read_all_records()
        target = self._find_record(records, match_id)
        if target is None:
            logger.warning("paper_log: match_id %s not found for finalize", match_id)
            return
        target["actual_outcome"] = {
            "winner": winner,
            "final_score": final_score,
            "match_duration_min": match_duration_min,
        }
        self._write_all_records(records)

    def _append_record(self, record: PaperMatchRecord) -> None:
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def _read_all_records(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        records: list[dict] = []
        with open(self._log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _write_all_records(self, records: list[dict]) -> None:
        tmp_path = self._log_path.with_suffix(self._log_path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        os.replace(tmp_path, self._log_path)

    @staticmethod
    def _find_record(records: list[dict], match_id: str) -> dict | None:
        for r in records:
            if r.get("match_id") == match_id:
                return r
        return None
