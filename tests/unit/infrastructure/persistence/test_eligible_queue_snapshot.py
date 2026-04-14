"""eligible_queue_snapshot.py için birim testler."""
from __future__ import annotations

from pathlib import Path

from src.infrastructure.persistence.eligible_queue_snapshot import (
    EligibleQueueEntry,
    EligibleQueueSnapshot,
)


def _entry(**overrides) -> EligibleQueueEntry:
    base = dict(
        slug="lakers-vs-celtics",
        sport_tag="basketball_nba",
        question="Will Lakers beat Celtics?",
        yes_price=0.42,
        no_price=0.58,
        liquidity=5000.0,
        volume_24h=12000.0,
        match_start_iso="2026-04-14T22:00:00Z",
    )
    base.update(overrides)
    return EligibleQueueEntry(**base)


def test_dump_and_load_roundtrip(tmp_path: Path) -> None:
    snap = EligibleQueueSnapshot(str(tmp_path / "q.json"))
    snap.dump([_entry(slug="a"), _entry(slug="b")])
    rows = snap.load()
    assert len(rows) == 2
    assert rows[0]["slug"] == "a"
    assert rows[1]["slug"] == "b"


def test_dump_overwrites_previous(tmp_path: Path) -> None:
    snap = EligibleQueueSnapshot(str(tmp_path / "q.json"))
    snap.dump([_entry(slug="old1"), _entry(slug="old2")])
    snap.dump([_entry(slug="new1")])
    rows = snap.load()
    assert len(rows) == 1
    assert rows[0]["slug"] == "new1"


def test_dump_empty_list(tmp_path: Path) -> None:
    snap = EligibleQueueSnapshot(str(tmp_path / "q.json"))
    snap.dump([])
    assert snap.load() == []


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    snap = EligibleQueueSnapshot(str(tmp_path / "nope.json"))
    assert snap.load() == []


def test_corrupt_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "q.json"
    path.write_text("not json", encoding="utf-8")
    snap = EligibleQueueSnapshot(str(path))
    assert snap.load() == []


def test_creates_parent_dir(tmp_path: Path) -> None:
    snap = EligibleQueueSnapshot(str(tmp_path / "a" / "b" / "q.json"))
    snap.dump([_entry()])
    assert (tmp_path / "a" / "b" / "q.json").exists()
