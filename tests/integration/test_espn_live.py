"""ESPN API smoke test — gerçek API çağrısı, CI'da skip."""
from __future__ import annotations

import pytest

from src.infrastructure.apis.espn_client import fetch_scoreboard


@pytest.mark.skip(reason="Manuel: pytest tests/integration/test_espn_live.py -v -p no:skip")
def test_espn_nhl_scoreboard_returns_data() -> None:
    scores = fetch_scoreboard("hockey", "nhl")
    assert isinstance(scores, list)


@pytest.mark.skip(reason="Manuel: pytest tests/integration/test_espn_live.py -v -p no:skip")
def test_espn_tennis_atp_scoreboard() -> None:
    scores = fetch_scoreboard("tennis", "atp")
    assert isinstance(scores, list)
