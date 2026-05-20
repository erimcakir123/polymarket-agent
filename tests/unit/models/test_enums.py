"""enums.py için birim testler."""
from __future__ import annotations

import json

from src.models.enums import (
    Confidence,
    Direction,
    EntryReason,
    ExitReason,
    SportsMarketType,
    TotalSide,
)


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


def test_tennis_entry_reason_value() -> None:
    assert EntryReason.TENNIS.value == "tennis"


def test_tennis_entry_reason_member() -> None:
    assert EntryReason.TENNIS in EntryReason


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
    assert ExitReason.PREDICTIVE_DEAD.value == "predictive_dead"
    assert ExitReason.SCORE_EXIT.value == "score_exit"


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


def test_exit_reason_predictive_dead_score_exit_json_serializable() -> None:
    encoded_pd = json.dumps({"r": ExitReason.PREDICTIVE_DEAD})
    encoded_se = json.dumps({"r": ExitReason.SCORE_EXIT})
    assert "predictive_dead" in encoded_pd
    assert "score_exit" in encoded_se


def test_sports_market_type_values() -> None:
    assert SportsMarketType.MONEYLINE.value == "moneyline"
    assert SportsMarketType.SPREADS.value == "spreads"
    assert SportsMarketType.TOTALS.value == "totals"


def test_total_side_values() -> None:
    assert TotalSide.OVER.value == "over"
    assert TotalSide.UNDER.value == "under"


def test_sports_market_type_and_total_side_json_serializable() -> None:
    encoded_smt = json.dumps({"t": SportsMarketType.SPREADS})
    encoded_ts = json.dumps({"s": TotalSide.OVER})
    assert "spreads" in encoded_smt
    assert "over" in encoded_ts
