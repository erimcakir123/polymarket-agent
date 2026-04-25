"""Unit tests for EdgeEnricher — injury + B2B context enrichment.

All external clients are replaced with MagicMock; no real HTTP calls.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.infrastructure.apis.espn_injury_client import InjuryEvent
from src.orchestration.edge_enricher import EdgeContext, EdgeEnricher


# ── Helpers ─────────────────────────────────────────────────────────────────

def _inj(
    name: str,
    status: str,
    team_id: str,
    is_starter: bool = True,
    hours_ago: float = 1,
) -> InjuryEvent:
    return InjuryEvent(
        athlete_name=name,
        status=status,  # type: ignore[arg-type]
        reported_at=datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago),
        team_id=team_id,
        is_starter=is_starter,
    )


def _make_market(match_start_iso: str = "") -> MagicMock:
    market = MagicMock()
    market.match_start_iso = match_start_iso
    return market


def _make_enricher(
    injuries: dict | None = None,
    b2b_map: dict | None = None,
    b2b_side_effect: Exception | None = None,
) -> EdgeEnricher:
    """Build an EdgeEnricher with mocked clients.

    injuries: dict[team_id → list[InjuryEvent]] returned by get_recent_injuries
    b2b_map:  dict[(team_id, season) → bool] or dict[team_id → bool] for is_back_to_back
    b2b_side_effect: if set, is_back_to_back raises this exception
    """
    injury_client = MagicMock()
    injury_client.get_recent_injuries.return_value = injuries or {}

    schedule_client = MagicMock()
    if b2b_side_effect is not None:
        schedule_client.is_back_to_back.side_effect = b2b_side_effect
    elif b2b_map is not None:
        def _b2b(team_id: str, game_date: datetime, season: int) -> bool:
            return b2b_map.get(team_id, False)
        schedule_client.is_back_to_back.side_effect = _b2b
    else:
        schedule_client.is_back_to_back.return_value = False

    return EdgeEnricher(
        injury_client=injury_client,
        schedule_client=schedule_client,
        injury_window_hours=2,
    )


# ── Tests ────────────────────────────────────────────────────────────────────

class TestEdgeEnricherNoInjuries:
    def test_enrich_no_injuries_no_b2b_returns_empty_context(self) -> None:
        """Both clients return empty / False → EdgeContext is all defaults."""
        enricher = _make_enricher()
        market = _make_market("2026-04-25T20:00:00Z")

        ctx = enricher.enrich(market, our_team_id="1", opp_team_id="2")

        assert ctx.has_recent_injury is False
        assert ctx.injured_starter_name is None
        assert ctx.injury_reported_at is None
        assert ctx.injury_team_id is None
        assert ctx.is_our_back_to_back is False
        assert ctx.is_opponent_back_to_back is False


class TestInjuryDetection:
    def test_enrich_injury_on_our_team_flagged(self) -> None:
        """Our team has an 'Out' starter → injury_team_id == our_team_id."""
        injury = _inj("LeBron James", "Out", team_id="1")
        enricher = _make_enricher(injuries={"1": [injury]})
        market = _make_market("2026-04-25T20:00:00Z")

        ctx = enricher.enrich(market, our_team_id="1", opp_team_id="2")

        assert ctx.has_recent_injury is True
        assert ctx.injury_team_id == "1"
        assert ctx.injured_starter_name == "LeBron James"
        assert ctx.injury_reported_at == injury.reported_at

    def test_enrich_injury_on_opponent_team_flagged(self) -> None:
        """Opponent team has 'Out' starter → injury_team_id == opp_team_id."""
        injury = _inj("Steph Curry", "Out", team_id="2")
        enricher = _make_enricher(injuries={"2": [injury]})
        market = _make_market("2026-04-25T20:00:00Z")

        ctx = enricher.enrich(market, our_team_id="1", opp_team_id="2")

        assert ctx.has_recent_injury is True
        assert ctx.injury_team_id == "2"
        assert ctx.injured_starter_name == "Steph Curry"

    def test_enrich_priority_out_over_doubtful(self) -> None:
        """Team has both 'Doubtful' and 'Out' starters → 'Out' is selected."""
        doubtful_player = _inj("Player A", "Doubtful", team_id="1")
        out_player = _inj("Player B", "Out", team_id="1")
        enricher = _make_enricher(injuries={"1": [doubtful_player, out_player]})
        market = _make_market("2026-04-25T20:00:00Z")

        ctx = enricher.enrich(market, our_team_id="1", opp_team_id="2")

        assert ctx.injured_starter_name == "Player B"

    def test_enrich_priority_starter_over_non_starter(self) -> None:
        """'Out' non-starter and 'Out' starter in same team → starter selected."""
        non_starter = _inj("Bench Player", "Out", team_id="1", is_starter=False)
        starter = _inj("Starting Guard", "Out", team_id="1", is_starter=True)
        # non_starter listed first to verify priority logic overrides order
        enricher = _make_enricher(injuries={"1": [non_starter, starter]})
        market = _make_market("2026-04-25T20:00:00Z")

        ctx = enricher.enrich(market, our_team_id="1", opp_team_id="2")

        assert ctx.injured_starter_name == "Starting Guard"

    def test_enrich_our_team_checked_before_opponent(self) -> None:
        """When both teams have injuries, our_team_id takes priority."""
        our_injury = _inj("Our Star", "Out", team_id="1")
        opp_injury = _inj("Opp Star", "Out", team_id="2")
        enricher = _make_enricher(injuries={"1": [our_injury], "2": [opp_injury]})
        market = _make_market("2026-04-25T20:00:00Z")

        ctx = enricher.enrich(market, our_team_id="1", opp_team_id="2")

        assert ctx.injury_team_id == "1"
        assert ctx.injured_starter_name == "Our Star"


class TestB2BDetection:
    def test_enrich_our_team_b2b_true(self) -> None:
        """schedule_client returns True for our_team_id → is_our_back_to_back=True."""
        enricher = _make_enricher(b2b_map={"1": True, "2": False})
        market = _make_market("2026-04-25T20:00:00Z")

        ctx = enricher.enrich(market, our_team_id="1", opp_team_id="2")

        assert ctx.is_our_back_to_back is True
        assert ctx.is_opponent_back_to_back is False

    def test_enrich_opponent_b2b_true(self) -> None:
        """schedule_client returns True for opp_team_id → is_opponent_back_to_back=True."""
        enricher = _make_enricher(b2b_map={"1": False, "2": True})
        market = _make_market("2026-04-25T20:00:00Z")

        ctx = enricher.enrich(market, our_team_id="1", opp_team_id="2")

        assert ctx.is_our_back_to_back is False
        assert ctx.is_opponent_back_to_back is True


class TestEdgeCases:
    def test_enrich_empty_team_id_skips_checks(self) -> None:
        """Both team IDs empty → no client method calls, all defaults."""
        injury_client = MagicMock()
        injury_client.get_recent_injuries.return_value = {}
        schedule_client = MagicMock()
        enricher = EdgeEnricher(
            injury_client=injury_client,
            schedule_client=schedule_client,
            injury_window_hours=2,
        )
        market = _make_market("2026-04-25T20:00:00Z")

        ctx = enricher.enrich(market, our_team_id="", opp_team_id="")

        schedule_client.is_back_to_back.assert_not_called()
        assert ctx.is_our_back_to_back is False
        assert ctx.is_opponent_back_to_back is False
        assert ctx.has_recent_injury is False

    def test_enrich_schedule_error_does_not_crash(self) -> None:
        """schedule_client.is_back_to_back raises → ctx stays False (graceful)."""
        enricher = _make_enricher(b2b_side_effect=RuntimeError("ESPN down"))
        market = _make_market("2026-04-25T20:00:00Z")

        ctx = enricher.enrich(market, our_team_id="1", opp_team_id="2")

        assert ctx.is_our_back_to_back is False
        assert ctx.is_opponent_back_to_back is False

    def test_enrich_game_date_from_market_match_start_iso(self) -> None:
        """market.match_start_iso "2025-10-20T..." → season=2026 (month>=10)."""
        injury_client = MagicMock()
        injury_client.get_recent_injuries.return_value = {}
        schedule_client = MagicMock()
        schedule_client.is_back_to_back.return_value = False

        enricher = EdgeEnricher(
            injury_client=injury_client,
            schedule_client=schedule_client,
            injury_window_hours=2,
        )
        market = _make_market("2025-10-20T19:00:00Z")

        enricher.enrich(market, our_team_id="1", opp_team_id="2")

        # Verify schedule_client was called with season=2026 for both teams
        calls = schedule_client.is_back_to_back.call_args_list
        assert len(calls) == 2
        for call in calls:
            _team_id, _game_date, season = call.args
            assert season == 2026, f"Expected season=2026, got {season}"
