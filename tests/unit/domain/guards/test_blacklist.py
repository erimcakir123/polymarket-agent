"""blacklist.py için birim testler."""
from __future__ import annotations

from src.domain.guards.blacklist import Blacklist


def test_empty_not_blacklisted() -> None:
    bl = Blacklist()
    assert bl.is_blacklisted(condition_id="c1") is False
    assert bl.is_blacklisted(event_id="e1") is False


def test_add_condition_blocks() -> None:
    bl = Blacklist()
    bl.add_condition("c1")
    assert bl.is_blacklisted(condition_id="c1") is True
    # Farklı condition → OK
    assert bl.is_blacklisted(condition_id="c2") is False


def test_add_event_blocks() -> None:
    bl = Blacklist()
    bl.add_event("e1")
    assert bl.is_blacklisted(event_id="e1") is True


def test_condition_and_event_independent() -> None:
    bl = Blacklist()
    bl.add_condition("c1")
    # c1 blocked ama e1 değil
    assert bl.is_blacklisted(condition_id="c1", event_id="e1") is True  # c1 hit
    assert bl.is_blacklisted(condition_id="", event_id="e1") is False


def test_remove_condition() -> None:
    bl = Blacklist()
    bl.add_condition("c1")
    bl.remove_condition("c1")
    assert bl.is_blacklisted(condition_id="c1") is False


def test_remove_event() -> None:
    bl = Blacklist()
    bl.add_event("e1")
    bl.remove_event("e1")
    assert bl.is_blacklisted(event_id="e1") is False


def test_empty_inputs_not_blacklisted() -> None:
    bl = Blacklist()
    bl.add_condition("c1")
    assert bl.is_blacklisted(condition_id="") is False


def test_to_dict_from_dict_roundtrip() -> None:
    bl = Blacklist()
    bl.add_condition("c1")
    bl.add_condition("c2")
    bl.add_event("e1")
    data = bl.to_dict()
    restored = Blacklist.from_dict(data)
    assert restored.is_blacklisted(condition_id="c1") is True
    assert restored.is_blacklisted(condition_id="c2") is True
    assert restored.is_blacklisted(event_id="e1") is True


def test_add_empty_noop() -> None:
    bl = Blacklist()
    bl.add_condition("")
    bl.add_event("")
    assert bl.condition_ids == set()
    assert bl.event_ids == set()
