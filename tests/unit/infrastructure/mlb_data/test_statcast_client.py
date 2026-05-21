"""Unit tests for StatcastClient — pybaseball wrapper.

SPEC-R Plan 3 T2. Mocks pybaseball.statcast_batter / statcast_pitcher.
"""
import pytest
from pathlib import Path
from unittest.mock import patch
import pandas as pd

from src.infrastructure.mlb_data.statcast_client import StatcastClient, StatcastError


def _df(events: list[str]) -> pd.DataFrame:
    """Build minimal Statcast DataFrame from list of event strings."""
    return pd.DataFrame({"events": events})


def test_get_batter_rates_basic_aggregation() -> None:
    events = (
        ["strikeout"] * 22
        + ["walk"] * 8
        + ["home_run"] * 3
        + ["single"] * 14
        + ["double"] * 4
        + ["field_out"] * 49
    )
    df = _df(events)  # 100 PAs total
    with patch(
        "src.infrastructure.mlb_data.statcast_client.pybaseball.statcast_batter",
        return_value=df,
    ):
        rates = StatcastClient().get_batter_rates(12345, 2024)
    assert abs(rates["K"] - 0.22) < 1e-9
    assert abs(rates["BB"] - 0.08) < 1e-9
    assert abs(rates["HR"] - 0.03) < 1e-9
    assert abs(rates["1B"] - 0.14) < 1e-9
    assert abs(rates["2B"] - 0.04) < 1e-9
    assert abs(rates["OUT_IN_PLAY"] - 0.49) < 1e-9
    assert abs(sum(rates.values()) - 1.0) < 1e-9


def test_get_batter_rates_unknown_events_to_out_in_play() -> None:
    events = ["strikeout"] * 5 + ["fielders_choice"] * 5
    df = _df(events)
    with patch(
        "src.infrastructure.mlb_data.statcast_client.pybaseball.statcast_batter",
        return_value=df,
    ):
        rates = StatcastClient().get_batter_rates(12345, 2024)
    assert rates["K"] == 0.5
    assert rates["OUT_IN_PLAY"] == 0.5


def test_get_batter_rates_empty_returns_empty_dict() -> None:
    with patch(
        "src.infrastructure.mlb_data.statcast_client.pybaseball.statcast_batter",
        return_value=pd.DataFrame({"events": []}),
    ):
        rates = StatcastClient().get_batter_rates(12345, 2024)
    assert rates == {}


def test_get_batter_rates_nan_events_filtered() -> None:
    """Statcast returns one row per pitch; rows with NaN events are non-AB-ending pitches."""
    df = pd.DataFrame({"events": ["strikeout", None, None, "walk", None]})
    with patch(
        "src.infrastructure.mlb_data.statcast_client.pybaseball.statcast_batter",
        return_value=df,
    ):
        rates = StatcastClient().get_batter_rates(12345, 2024)
    assert rates["K"] == 0.5
    assert rates["BB"] == 0.5


def test_pybaseball_error_raises_statcast_error() -> None:
    with patch(
        "src.infrastructure.mlb_data.statcast_client.pybaseball.statcast_batter",
        side_effect=Exception("API down"),
    ):
        with pytest.raises(StatcastError):
            StatcastClient().get_batter_rates(12345, 2024)


def test_get_pitcher_rates_uses_statcast_pitcher() -> None:
    df = _df(["strikeout"] * 10)
    with patch(
        "src.infrastructure.mlb_data.statcast_client.pybaseball.statcast_pitcher",
        return_value=df,
    ):
        rates = StatcastClient().get_pitcher_rates(12345, 2024)
    assert rates["K"] == 1.0


def test_cache_skips_second_call(tmp_path: Path) -> None:
    df = _df(["strikeout"] * 10)
    with patch(
        "src.infrastructure.mlb_data.statcast_client.pybaseball.statcast_batter",
        return_value=df,
    ) as m:
        client = StatcastClient(cache_dir=tmp_path)
        rates_1 = client.get_batter_rates(12345, 2024)
        rates_2 = client.get_batter_rates(12345, 2024)  # should hit cache
    assert rates_1 == rates_2
    assert m.call_count == 1  # only called once


def test_no_cache_dir_always_fetches() -> None:
    df = _df(["strikeout"] * 10)
    with patch(
        "src.infrastructure.mlb_data.statcast_client.pybaseball.statcast_batter",
        return_value=df,
    ) as m:
        client = StatcastClient(cache_dir=None)
        client.get_batter_rates(12345, 2024)
        client.get_batter_rates(12345, 2024)
    assert m.call_count == 2  # called twice — no cache
