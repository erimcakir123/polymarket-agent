"""24-state base/out encoding (SPEC-R Plan 2 T10).

State = (outs, runners on 1B/2B/3B). Encoded as integer 0-23.
INNING_ENDED = -1 is a sentinel for 3-out terminal state.

Encoding: state_idx = outs × 8 + runner_bits
runner_bits: 1B → 1, 2B → 2, 3B → 4 (bitfield)
"""
from __future__ import annotations

INITIAL_STATE: int = 0
INNING_ENDED: int = -1


def encode(outs: int, runners: tuple[bool, bool, bool]) -> int:
    """Encode (outs, (1B, 2B, 3B)) to state index 0-23."""
    if not 0 <= outs <= 2:
        raise ValueError(f"outs must be in [0,2], got {outs}")
    r1, r2, r3 = runners
    bits = (1 if r1 else 0) | (2 if r2 else 0) | (4 if r3 else 0)
    return outs * 8 + bits


def decode(state_idx: int) -> tuple[int, tuple[bool, bool, bool]]:
    """Decode state index 0-23 to (outs, (1B, 2B, 3B))."""
    if not 0 <= state_idx <= 23:
        raise ValueError(f"state_idx must be in [0,23], got {state_idx}")
    outs = state_idx // 8
    bits = state_idx % 8
    return outs, (bool(bits & 1), bool(bits & 2), bool(bits & 4))
