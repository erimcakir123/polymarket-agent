"""SPEC-Z17: Trade event types — pure literals."""
from typing import Literal

EventKind = Literal["entry", "partial", "final"]

ENTRY: EventKind = "entry"
PARTIAL: EventKind = "partial"
FINAL: EventKind = "final"
