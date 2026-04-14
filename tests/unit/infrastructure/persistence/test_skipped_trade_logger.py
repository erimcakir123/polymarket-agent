"""skipped_trade_logger.py için birim testler."""
from __future__ import annotations

from pathlib import Path

from src.infrastructure.persistence.skipped_trade_logger import (
    SkippedTradeLogger,
    SkippedTradeRecord,
)


def _record(**overrides) -> SkippedTradeRecord:
    base = dict(
        timestamp="2026-04-14T10:00:00Z",
        slug="lakers-vs-celtics",
        sport_tag="basketball_nba",
        event_id="evt_99",
        direction="BUY_YES",
        entry_price=0.42,
        anchor_probability=0.50,
        confidence="B",
        skip_reason="slot_full",
        skip_detail="20/20",
    )
    base.update(overrides)
    return SkippedTradeRecord(**base)


def test_record_fields_roundtrip() -> None:
    r = _record()
    data = r.model_dump(mode="json")
    restored = SkippedTradeRecord(**data)
    assert restored.slug == "lakers-vs-celtics"
    assert restored.skip_reason == "slot_full"


def test_record_defaults_for_minimal_skip() -> None:
    r = SkippedTradeRecord(
        timestamp="t",
        slug="s",
        sport_tag="tennis_atp",
        skip_reason="event_guard_duplicate",
    )
    assert r.direction == ""
    assert r.entry_price == 0.0
    assert r.confidence == ""


def test_log_appends_and_reads(tmp_path: Path) -> None:
    log = SkippedTradeLogger(str(tmp_path / "skipped.jsonl"))
    log.log(_record(slug="a"))
    log.log(_record(slug="b"))
    rows = log.read_recent(10)
    assert len(rows) == 2
    assert rows[0]["slug"] == "a"
    assert rows[1]["slug"] == "b"


def test_read_recent_returns_last_n(tmp_path: Path) -> None:
    log = SkippedTradeLogger(str(tmp_path / "s.jsonl"))
    for i in range(30):
        log.log(_record(slug=f"m-{i}"))
    rows = log.read_recent(10)
    assert len(rows) == 10
    assert rows[-1]["slug"] == "m-29"
    assert rows[0]["slug"] == "m-20"


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    log = SkippedTradeLogger(str(tmp_path / "nope.jsonl"))
    assert log.read_recent(10) == []


def test_creates_parent_dir(tmp_path: Path) -> None:
    log = SkippedTradeLogger(str(tmp_path / "a" / "b" / "s.jsonl"))
    log.log(_record())
    assert (tmp_path / "a" / "b" / "s.jsonl").exists()
