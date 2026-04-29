"""Tennis paper logger tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.orchestration.tennis_paper_logger import (
    InMatchSnapshot,
    PaperMatchRecord,
    PreMatchPrediction,
    TennisPaperLogger,
)


def test_log_pre_match_creates_record(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    logger = TennisPaperLogger(log_path=log_path)
    pre_match = PreMatchPrediction(
        model_p_win_a=0.628,
        model_p_win_b=0.372,
        polymarket_a_price=0.55,
        polymarket_b_price=0.45,
        edge=0.078,
        would_enter=True,
        would_size_usdc=35.0,
    )
    logger.log_pre_match(
        match_id="atp-medvedev-cobolli-2026-04-28",
        tournament="Madrid Open ATP",
        surface="clay",
        format="BO3",
        player_a="Daniil Medvedev",
        player_b="Flavio Cobolli",
        pre_match=pre_match,
    )

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["match_id"] == "atp-medvedev-cobolli-2026-04-28"
    assert record["pre_match"]["model_p_win_a"] == 0.628
    assert record["in_match_log"] == []
    assert record["actual_outcome"] is None


def test_append_in_match_snapshot(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    logger = TennisPaperLogger(log_path=log_path)
    pre_match = PreMatchPrediction(
        model_p_win_a=0.62, model_p_win_b=0.38,
        polymarket_a_price=0.55, polymarket_b_price=0.45,
        edge=0.07, would_enter=True, would_size_usdc=35.0,
    )
    logger.log_pre_match("m1", "Madrid", "clay", "BO3", "A", "B", pre_match)
    snap = InMatchSnapshot(
        timestamp_iso="2026-04-28T19:00:00Z",
        game_n=1,
        set_score="0-0",
        game_score="1-0",
        server="A",
        model_p_win_a=0.65,
        bid_a=0.56,
        would_action="HOLD",
    )
    logger.append_in_match("m1", snap)

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert len(record["in_match_log"]) == 1
    assert record["in_match_log"][0]["model_p_win_a"] == 0.65


def test_finalize_match_writes_outcome(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    logger = TennisPaperLogger(log_path=log_path)
    pre_match = PreMatchPrediction(
        model_p_win_a=0.62, model_p_win_b=0.38,
        polymarket_a_price=0.55, polymarket_b_price=0.45,
        edge=0.07, would_enter=True, would_size_usdc=35.0,
    )
    logger.log_pre_match("m1", "Madrid", "clay", "BO3", "A", "B", pre_match)
    logger.finalize_match(
        match_id="m1",
        winner="a",
        final_score="6-4 6-3",
        match_duration_min=95,
    )

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["actual_outcome"]["winner"] == "a"
    assert record["actual_outcome"]["final_score"] == "6-4 6-3"


def test_multiple_matches_separate_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    logger = TennisPaperLogger(log_path=log_path)
    pre = PreMatchPrediction(
        model_p_win_a=0.6, model_p_win_b=0.4,
        polymarket_a_price=0.55, polymarket_b_price=0.45,
        edge=0.05, would_enter=True, would_size_usdc=35.0,
    )
    logger.log_pre_match("m1", "T1", "clay", "BO3", "A", "B", pre)
    logger.log_pre_match("m2", "T2", "hard", "BO3", "C", "D", pre)
    lines = log_path.read_text().splitlines()
    assert len(lines) == 2
