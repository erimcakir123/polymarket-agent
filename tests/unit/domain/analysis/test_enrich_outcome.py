"""EnrichResult + EnrichFailReason için birim testler."""
from __future__ import annotations

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.analysis.probability import BookmakerProbability
from src.models.enums import TotalSide


def test_enrich_result_ok_has_probability_and_null_fail_reason() -> None:
    prob = BookmakerProbability(
        probability=0.62, confidence="B",
        bookmaker_prob=0.62, num_bookmakers=3.0, has_sharp=True,
    )
    result = EnrichResult(probability=prob, fail_reason=None)
    assert result.probability is prob
    assert result.fail_reason is None


def test_enrich_result_fail_has_null_probability_and_fail_reason() -> None:
    result = EnrichResult(probability=None, fail_reason=EnrichFailReason.EMPTY_EVENTS)
    assert result.probability is None
    assert result.fail_reason == EnrichFailReason.EMPTY_EVENTS


def test_enrich_fail_reason_values_match_spec() -> None:
    expected = {
        "sport_key_unresolved",
        "team_extract_failed",
        "empty_events",
        "event_no_match",
        "empty_bookmakers",
        "bookmaker_no_spread",
        "bookmaker_no_totals",
    }
    actual = {r.value for r in EnrichFailReason}
    assert actual == expected


# --- SPEC-K: spread/totals fields default to None ---


def test_enrich_result_default_spread_totals_fields_are_none() -> None:
    """Moneyline path için spread_line/total_line/total_side default None."""
    prob = BookmakerProbability(
        probability=0.62, confidence="B",
        bookmaker_prob=0.62, num_bookmakers=3.0, has_sharp=True,
    )
    result = EnrichResult(probability=prob, fail_reason=None)
    assert result.spread_line is None
    assert result.total_line is None
    assert result.total_side is None


def test_enrich_result_spread_line_can_be_set() -> None:
    prob = BookmakerProbability(
        probability=0.55, confidence="B",
        bookmaker_prob=0.55, num_bookmakers=3.0, has_sharp=True,
    )
    result = EnrichResult(probability=prob, fail_reason=None, spread_line=7.5)
    assert result.spread_line == 7.5
    assert result.total_line is None
    assert result.total_side is None


def test_enrich_result_totals_fields_can_be_set() -> None:
    prob = BookmakerProbability(
        probability=0.50, confidence="B",
        bookmaker_prob=0.50, num_bookmakers=3.0, has_sharp=True,
    )
    result = EnrichResult(
        probability=prob, fail_reason=None,
        total_line=215.5, total_side=TotalSide.OVER,
    )
    assert result.total_line == 215.5
    assert result.total_side == TotalSide.OVER
    assert result.spread_line is None


def test_enrich_fail_reason_bookmaker_no_spread_exists() -> None:
    assert EnrichFailReason.BOOKMAKER_NO_SPREAD.value == "bookmaker_no_spread"


def test_enrich_fail_reason_bookmaker_no_totals_exists() -> None:
    assert EnrichFailReason.BOOKMAKER_NO_TOTALS.value == "bookmaker_no_totals"
