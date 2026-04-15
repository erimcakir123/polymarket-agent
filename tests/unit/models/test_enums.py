"""enums.py için birim testler."""
from __future__ import annotations

import json

from src.models.enums import Confidence, Direction, EntryReason, ExitReason


def test_direction_values() -> None:
    assert Direction.BUY_YES.value == "BUY_YES"
    assert Direction.BUY_NO.value == "BUY_NO"
    assert Direction.SKIP.value == "SKIP"


def test_confidence_values() -> None:
    assert Confidence.A.value == "A"
    assert Confidence.B.value == "B"
    assert Confidence.C.value == "C"


def test_entry_reason_values() -> None:
    assert EntryReason.NORMAL.value == "normal"
    assert EntryReason.EARLY.value == "early"
    assert EntryReason.CONSENSUS.value == "consensus"


def test_exit_reason_values() -> None:
    assert ExitReason.STOP_LOSS.value == "stop_loss"
    assert ExitReason.SCALE_OUT.value == "scale_out"
    assert ExitReason.GRADUATED_SL.value == "graduated_sl"
    assert ExitReason.NEVER_IN_PROFIT.value == "never_in_profit"
    assert ExitReason.MARKET_FLIP.value == "market_flip"
    assert ExitReason.NEAR_RESOLVE.value == "near_resolve"
    assert ExitReason.HOLD_REVOKED.value == "hold_revoked"
    assert ExitReason.ULTRA_LOW_GUARD.value == "ultra_low_guard"
    assert ExitReason.CIRCUIT_BREAKER.value == "circuit_breaker"
    assert ExitReason.MANUAL.value == "manual"


def test_enum_str_mixin_json_serializable() -> None:
    payload = {
        "direction": Direction.BUY_YES,
        "confidence": Confidence.A,
        "entry_reason": EntryReason.NORMAL,
        "exit_reason": ExitReason.NEAR_RESOLVE,
    }
    encoded = json.dumps(payload)
    assert "BUY_YES" in encoded
    assert '"A"' in encoded
    assert "normal" in encoded
    assert "near_resolve" in encoded
