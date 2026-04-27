"""Unit tests for NHLEdgeEnricher — goalie + B2B context enrichment.

All external clients replaced with MagicMock; no real HTTP calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.orchestration.nhl_edge_enricher import NHLEdgeContext, NHLEdgeEnricher


# ── Constants ─────────────────────────────────────────────────────────────────

_GAME_DATE = datetime(2026, 4, 25, 20, 0, 0, tzinfo=timezone.utc)

_PROB_CONFIRMED = {
    "name": "probableStartingGoalie",
    "playerId": 4712036,
    "athlete": {"id": "4712036", "fullName": "Jeremy Swayman"},
}
_PROB_EXPECTED = {
    "name": "probableStartingGoalie",
    "playerId": 4712036,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sched(b2b_map: dict | None = None, b2b_exc: Exception | None = None) -> MagicMock:
    sc = MagicMock()
    if b2b_exc is not None:
        sc.is_back_to_back.side_effect = b2b_exc
    elif b2b_map is not None:
        def _b2b(team_id: str, game_date: datetime) -> bool:  # noqa: ARG001
            return b2b_map.get(team_id, False)
        sc.is_back_to_back.side_effect = _b2b
    else:
        sc.is_back_to_back.return_value = False
    return sc


def _make_enricher(
    b2b_map: dict | None = None,
    b2b_exc: Exception | None = None,
) -> NHLEdgeEnricher:
    return NHLEdgeEnricher(schedule_client=_sched(b2b_map, b2b_exc))


def _enrich(
    enricher: NHLEdgeEnricher,
    our: str = "BOS",
    opp: str = "TOR",
    we_home: bool = True,
    p_home: dict | None = None,
    p_away: dict | None = None,
) -> NHLEdgeContext:
    return enricher.enrich(
        our_team_id=our,
        opp_team_id=opp,
        game_date=_GAME_DATE,
        probables_home=p_home,
        probables_away=p_away,
        we_are_home=we_home,
    )


# ── _extract_goalie static tests ──────────────────────────────────────────────

class TestExtractGoalie:
    def test_none_returns_unknown(self) -> None:
        assert NHLEdgeEnricher._extract_goalie(None) == (None, "unknown")

    def test_empty_dict_returns_unknown(self) -> None:
        assert NHLEdgeEnricher._extract_goalie({}) == (None, "unknown")

    def test_non_dict_returns_unknown(self) -> None:
        assert NHLEdgeEnricher._extract_goalie("bad") == (None, "unknown")  # type: ignore[arg-type]

    def test_athlete_id_returns_confirmed(self) -> None:
        player_id, status = NHLEdgeEnricher._extract_goalie(_PROB_CONFIRMED)
        assert player_id == "4712036"
        assert status == "confirmed"

    def test_player_id_only_returns_expected(self) -> None:
        player_id, status = NHLEdgeEnricher._extract_goalie(_PROB_EXPECTED)
        assert player_id == "4712036"
        assert status == "expected"

    def test_athlete_present_but_no_id_falls_through_to_player_id(self) -> None:
        prob = {"athlete": {"fullName": "Jeremy Swayman"}, "playerId": 9999}
        player_id, status = NHLEdgeEnricher._extract_goalie(prob)
        assert player_id == "9999"
        assert status == "expected"

    def test_athlete_id_takes_priority_over_player_id(self) -> None:
        prob = {"athlete": {"id": "111"}, "playerId": 222}
        player_id, status = NHLEdgeEnricher._extract_goalie(prob)
        assert player_id == "111"
        assert status == "confirmed"

    def test_player_id_cast_to_str(self) -> None:
        prob = {"playerId": 12345}
        player_id, _ = NHLEdgeEnricher._extract_goalie(prob)
        assert player_id == "12345"
        assert isinstance(player_id, str)

    def test_athlete_not_a_dict_falls_through(self) -> None:
        prob = {"athlete": "Swayman", "playerId": 999}
        player_id, status = NHLEdgeEnricher._extract_goalie(prob)
        assert player_id == "999"
        assert status == "expected"

    def test_neither_field_returns_unknown(self) -> None:
        prob = {"name": "probableStartingGoalie"}
        assert NHLEdgeEnricher._extract_goalie(prob) == (None, "unknown")


# ── Goalie context in enrich() ────────────────────────────────────────────────

class TestGoalieContext:
    def test_home_confirmed_away_expected(self) -> None:
        enricher = _make_enricher()
        ctx = _enrich(enricher, p_home=_PROB_CONFIRMED, p_away=_PROB_EXPECTED)
        assert ctx.starting_goalie_home == "4712036"
        assert ctx.goalie_status_home == "confirmed"
        assert ctx.starting_goalie_away == "4712036"
        assert ctx.goalie_status_away == "expected"

    def test_both_none_probables_returns_unknown(self) -> None:
        enricher = _make_enricher()
        ctx = _enrich(enricher)
        assert ctx.starting_goalie_home is None
        assert ctx.starting_goalie_away is None
        assert ctx.goalie_status_home == "unknown"
        assert ctx.goalie_status_away == "unknown"

    def test_raw_probables_both_populated(self) -> None:
        enricher = _make_enricher()
        ctx = _enrich(enricher, p_home=_PROB_CONFIRMED, p_away=_PROB_EXPECTED)
        assert len(ctx.raw_probables) == 2

    def test_raw_probables_only_home(self) -> None:
        enricher = _make_enricher()
        ctx = _enrich(enricher, p_home=_PROB_CONFIRMED, p_away=None)
        assert len(ctx.raw_probables) == 1

    def test_raw_probables_both_none_empty(self) -> None:
        enricher = _make_enricher()
        ctx = _enrich(enricher)
        assert ctx.raw_probables == []


# ── we_are_home stored in context ─────────────────────────────────────────────

class TestWeAreHome:
    def test_we_are_home_true_stored(self) -> None:
        enricher = _make_enricher()
        ctx = _enrich(enricher, we_home=True)
        assert ctx.we_are_home is True

    def test_we_are_home_false_stored(self) -> None:
        enricher = _make_enricher()
        ctx = _enrich(enricher, we_home=False)
        assert ctx.we_are_home is False


# ── B2B context ───────────────────────────────────────────────────────────────

class TestB2BContext:
    def test_no_b2b_returns_all_false(self) -> None:
        enricher = _make_enricher()
        ctx = _enrich(enricher)
        assert ctx.is_our_back_to_back is False
        assert ctx.is_opponent_back_to_back is False

    def test_our_team_b2b(self) -> None:
        enricher = _make_enricher(b2b_map={"BOS": True})
        ctx = _enrich(enricher)
        assert ctx.is_our_back_to_back is True
        assert ctx.is_opponent_back_to_back is False

    def test_opponent_b2b(self) -> None:
        enricher = _make_enricher(b2b_map={"TOR": True})
        ctx = _enrich(enricher)
        assert ctx.is_opponent_back_to_back is True
        assert ctx.is_our_back_to_back is False

    def test_both_b2b(self) -> None:
        enricher = _make_enricher(b2b_map={"BOS": True, "TOR": True})
        ctx = _enrich(enricher)
        assert ctx.is_our_back_to_back is True
        assert ctx.is_opponent_back_to_back is True

    def test_b2b_failure_returns_defaults(self) -> None:
        enricher = _make_enricher(b2b_exc=RuntimeError("schedule down"))
        ctx = _enrich(enricher)
        assert ctx.is_our_back_to_back is False
        assert ctx.is_opponent_back_to_back is False

    def test_empty_team_ids_skip_b2b(self) -> None:
        sc = _sched(b2b_map={"BOS": True, "TOR": True})
        enricher = NHLEdgeEnricher(schedule_client=sc)
        ctx = _enrich(enricher, our="", opp="")
        assert ctx.is_our_back_to_back is False
        assert ctx.is_opponent_back_to_back is False
        sc.is_back_to_back.assert_not_called()


# ── B2B isolation ─────────────────────────────────────────────────────────────

class TestB2BIsolation:
    def test_our_b2b_failure_does_not_block_opp_b2b(self) -> None:
        call_count = 0

        def _b2b(team_id: str, game_date: datetime) -> bool:  # noqa: ARG001
            nonlocal call_count
            call_count += 1
            if team_id == "BOS":
                raise RuntimeError("BOS schedule unavailable")
            return True

        sc = MagicMock()
        sc.is_back_to_back.side_effect = _b2b
        enricher = NHLEdgeEnricher(schedule_client=sc)
        ctx = _enrich(enricher)

        assert ctx.is_our_back_to_back is False
        assert ctx.is_opponent_back_to_back is True
        assert call_count == 2


# ── Combined ──────────────────────────────────────────────────────────────────

class TestCombined:
    def test_all_defaults_when_no_data(self) -> None:
        enricher = _make_enricher()
        ctx = _enrich(enricher)
        assert ctx.starting_goalie_home is None
        assert ctx.goalie_status_home == "unknown"
        assert ctx.is_our_back_to_back is False
        assert ctx.is_opponent_back_to_back is False

    def test_goalie_confirmed_and_opp_b2b(self) -> None:
        enricher = _make_enricher(b2b_map={"TOR": True})
        ctx = _enrich(enricher, p_home=_PROB_CONFIRMED, p_away=_PROB_EXPECTED)
        assert ctx.goalie_status_home == "confirmed"
        assert ctx.starting_goalie_home == "4712036"
        assert ctx.is_opponent_back_to_back is True
        assert ctx.is_our_back_to_back is False
        assert ctx.we_are_home is True
