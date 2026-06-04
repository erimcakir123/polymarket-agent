"""SPEC-Z17 (2026-06-04): domain event types — pure data, no I/O."""
from src.domain.trade.event_types import (
    EventKind, ENTRY, PARTIAL, FINAL,
)


def test_event_kind_literals_match_strings() -> None:
    assert ENTRY == "entry"
    assert PARTIAL == "partial"
    assert FINAL == "final"


def test_event_kind_union_covers_all_three() -> None:
    valid: EventKind = "entry"
    valid = "partial"
    valid = "final"
    assert valid in (ENTRY, PARTIAL, FINAL)
