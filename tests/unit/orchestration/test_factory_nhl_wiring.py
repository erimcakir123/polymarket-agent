"""Smoke tests — factory NHL wiring (Task 2C-1).

EspnHockeyScheduleClient + NHLEdgeEnricher inşa edilebilir ve
schedule_client doğru inject edilmiş olmalı.
"""
from __future__ import annotations

from src.infrastructure.apis.espn_hockey_schedule_client import EspnHockeyScheduleClient
from src.orchestration.nhl_edge_enricher import NHLEdgeEnricher


def test_nhl_schedule_client_constructs() -> None:
    client = EspnHockeyScheduleClient()
    assert client is not None


def test_nhl_edge_enricher_constructs() -> None:
    sched = EspnHockeyScheduleClient()
    enricher = NHLEdgeEnricher(schedule_client=sched)
    assert enricher is not None


def test_nhl_enricher_schedule_client_wired() -> None:
    """factory pattern: NHLEdgeEnricher(schedule_client=_nhl_schedule_client)."""
    sched = EspnHockeyScheduleClient()
    enricher = NHLEdgeEnricher(schedule_client=sched)
    assert enricher._schedule_client is sched
