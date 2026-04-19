"""archive_logger.py icin birim testler."""
from __future__ import annotations

import json
from pathlib import Path

from src.infrastructure.persistence.archive_logger import (
    ArchiveExitRecord,
    ArchiveLogger,
    ArchiveMatchResult,
    ArchiveScoreEvent,
)


def _make_exit_record() -> ArchiveExitRecord:
    return ArchiveExitRecord(
        slug="mlb-bos-nyy-2026-04-19",
        condition_id="0xabc",
        event_id="12345",
        token_id="token1",
        sport_tag="mlb",
        question="Boston Red Sox vs New York Yankees",
        direction="BUY_YES",
        entry_price=0.55,
        entry_timestamp="2026-04-19T14:00:00Z",
        size_usdc=50.0,
        shares=90.91,
        confidence="A",
        anchor_probability=0.60,
        entry_reason="consensus",
        exit_price=0.94,
        exit_pnl_usdc=35.50,
        exit_reason="near_resolve",
        exit_timestamp="2026-04-19T17:30:00Z",
        score_at_exit="5-2",
        period_at_exit="Top 9th",
        elapsed_pct_at_exit=0.95,
    )


def test_archive_dir_created_on_init(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    ArchiveLogger(str(archive_dir))
    assert archive_dir.exists()
    assert archive_dir.is_dir()


def test_log_exit_writes_jsonl_line(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    record = _make_exit_record()
    archive.log_exit(record)

    exits_file = tmp_path / "exits.jsonl"
    assert exits_file.exists()
    lines = exits_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["slug"] == "mlb-bos-nyy-2026-04-19"
    assert loaded["exit_pnl_usdc"] == 35.50
    assert loaded["score_at_exit"] == "5-2"


def test_log_score_event_writes_jsonl_line(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    event = ArchiveScoreEvent(
        event_id="12345",
        slug="mlb-bos-nyy-2026-04-19",
        sport_tag="mlb",
        timestamp="2026-04-19T15:30:00Z",
        prev_score="1-1",
        new_score="2-1",
        period="Top 5th",
    )
    archive.log_score_event(event)

    file = tmp_path / "score_events.jsonl"
    lines = file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["prev_score"] == "1-1"
    assert loaded["new_score"] == "2-1"


def test_log_match_result_writes_jsonl_line(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    result = ArchiveMatchResult(
        event_id="12345",
        slug="mlb-bos-nyy-2026-04-19",
        sport_tag="mlb",
        final_score="5-3",
        winner_home=True,
        completed_timestamp="2026-04-19T18:00:00Z",
        source="espn",
    )
    archive.log_match_result(result)

    file = tmp_path / "match_results.jsonl"
    lines = file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["final_score"] == "5-3"
    assert loaded["winner_home"] is True


def test_multiple_exits_append_only(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    archive.log_exit(_make_exit_record())
    archive.log_exit(_make_exit_record())
    archive.log_exit(_make_exit_record())

    lines = (tmp_path / "exits.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3


def test_load_logged_match_event_ids_empty(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    ids = archive.load_logged_match_event_ids()
    assert ids == set()


def test_load_logged_match_event_ids_with_existing(tmp_path: Path) -> None:
    archive = ArchiveLogger(str(tmp_path))
    archive.log_match_result(ArchiveMatchResult(
        event_id="E1", slug="a", sport_tag="mlb", final_score="1-0",
        winner_home=True, completed_timestamp="2026-04-19T18:00:00Z",
    ))
    archive.log_match_result(ArchiveMatchResult(
        event_id="E2", slug="b", sport_tag="nhl", final_score="3-2",
        winner_home=False, completed_timestamp="2026-04-19T19:00:00Z",
    ))

    archive2 = ArchiveLogger(str(tmp_path))
    ids = archive2.load_logged_match_event_ids()
    assert ids == {"E1", "E2"}
