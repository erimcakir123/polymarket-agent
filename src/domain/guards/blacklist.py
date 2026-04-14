"""Blacklist — condition_id / event_id bazlı entry bloklayıcı.

Pure state: blacklist dict dışarıdan verilir veya içeride tutulur. Persistence
orkestrasyonda JsonStore ile yapılır (eski logs/blacklist.json rolü).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Blacklist:
    """condition_id ve event_id için iki ayrı set tutar."""
    condition_ids: set[str] = field(default_factory=set)
    event_ids: set[str] = field(default_factory=set)

    def is_blacklisted(self, condition_id: str = "", event_id: str = "") -> bool:
        if condition_id and condition_id in self.condition_ids:
            return True
        if event_id and event_id in self.event_ids:
            return True
        return False

    def add_condition(self, condition_id: str, reason: str = "") -> None:
        if condition_id:
            self.condition_ids.add(condition_id)

    def add_event(self, event_id: str, reason: str = "") -> None:
        if event_id:
            self.event_ids.add(event_id)

    def remove_condition(self, condition_id: str) -> None:
        self.condition_ids.discard(condition_id)

    def remove_event(self, event_id: str) -> None:
        self.event_ids.discard(event_id)

    def to_dict(self) -> dict:
        return {
            "condition_ids": sorted(self.condition_ids),
            "event_ids": sorted(self.event_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Blacklist":
        return cls(
            condition_ids=set(data.get("condition_ids", [])),
            event_ids=set(data.get("event_ids", [])),
        )
