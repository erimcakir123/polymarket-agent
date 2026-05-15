"""EnrichResult + EnrichFailReason için birim testler."""
from __future__ import annotations

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.analysis.probability import BookmakerProbability


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
    }
    actual = {r.value for r in EnrichFailReason}
    assert actual == expected
