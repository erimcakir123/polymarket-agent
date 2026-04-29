"""Tennis Magnus predictor (composition of resolver + Sackmann + math)."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.matching.tennis_player_resolver import PlayerRecord, build_registry
from src.infrastructure.apis.sackmann_client import parse_matches_csv
from src.orchestration.tennis_magnus_predictor import (
    PredictionResult,
    TennisMagnusPredictor,
)


_FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "sackmann"


@pytest.fixture
def predictor() -> TennisMagnusPredictor:
    matches = parse_matches_csv(_FIXTURE_DIR / "atp_matches_2025_sample.csv")
    registry = build_registry([
        PlayerRecord(sackmann_id="207989", first="Jannik", last="Sinner", hand="R", country="ITA"),
        PlayerRecord(sackmann_id="208029", first="Carlos", last="Alcaraz Garfia", hand="R", country="ESP"),
        PlayerRecord(sackmann_id="209968", first="Flavio", last="Cobolli", hand="R", country="ITA"),
    ])
    surface_factors = {
        "atp": {"clay": 0.92, "hard": 1.00, "grass": 1.00},
        "wta": {"clay": 0.95, "hard": 1.05, "grass": 1.00},
    }
    return TennisMagnusPredictor(
        registry=registry,
        matches=matches,
        surface_factors=surface_factors,
        is_wta=False,
    )


def test_predict_pre_match_sinner_vs_cobolli_clay(predictor: TennisMagnusPredictor) -> None:
    result = predictor.predict_pre_match(
        player_a_query="Jannik Sinner",
        player_b_query="Flavio Cobolli",
        surface="clay",
        format="BO3",
    )
    assert result is not None
    # Sinner is heavy favorite
    assert result.p_win_a > 0.55
    assert 0 < result.p_win_a < 1


def test_predict_unknown_player_returns_none(predictor: TennisMagnusPredictor) -> None:
    result = predictor.predict_pre_match(
        player_a_query="Unknown Player X",
        player_b_query="Flavio Cobolli",
        surface="clay",
        format="BO3",
    )
    assert result is None


def test_predict_with_state_a_won_set1(predictor: TennisMagnusPredictor) -> None:
    pre = predictor.predict_pre_match("Jannik Sinner", "Flavio Cobolli", "clay", "BO3")
    assert pre is not None
    after = predictor.predict_with_state(
        player_a_query="Jannik Sinner",
        player_b_query="Flavio Cobolli",
        surface="clay",
        format="BO3",
        sets_won_a=1,
        sets_won_b=0,
        games_a=0,
        games_b=0,
        server_is_a=True,
    )
    assert after is not None
    assert after.p_win_a > pre.p_win_a
