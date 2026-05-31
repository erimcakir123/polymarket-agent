"""computed_sport_health.py için birim testler — Plan 1.D Task 4.

Pure derivation: model_health.json blob → branş kartı isabet payload'ı.
"""
from __future__ import annotations

from pathlib import Path

from src.presentation.dashboard import computed_sport_health


# ── Katman ihlali kontrolü ──

def test_module_has_no_layer_imports() -> None:
    path = Path(computed_sport_health.__file__)
    source = path.read_text(encoding="utf-8")
    for forbidden in (
        "from src.infrastructure", "import src.infrastructure",
        "from src.domain", "import src.domain",
        "from src.strategy", "import src.strategy",
        "from src.orchestration", "import src.orchestration",
    ):
        assert forbidden not in source, f"Layer violation: {forbidden}"


# ── compute_sport_health_for_dashboard ──

def test_empty_blob_returns_empty() -> None:
    out = computed_sport_health.compute_sport_health_for_dashboard({})
    assert out == {}


def test_none_blob_returns_empty() -> None:
    out = computed_sport_health.compute_sport_health_for_dashboard(None)  # type: ignore[arg-type]
    assert out == {}


def test_missing_sports_key_returns_empty() -> None:
    out = computed_sport_health.compute_sport_health_for_dashboard({"computed_at_utc": "x"})
    assert out == {}


def test_healthy_sport_no_alarm() -> None:
    blob = {
        "computed_at_utc": "2026-06-01T00:00:00+00:00",
        "sports": {"tennis": {"accuracy": 0.72, "brier": 0.18, "n_trades": 47}},
    }
    out = computed_sport_health.compute_sport_health_for_dashboard(blob)
    assert out["tennis"]["accuracy"] == 0.72
    assert out["tennis"]["n_trades"] == 47
    assert out["tennis"]["alarm"] is False


def test_degraded_sport_triggers_alarm() -> None:
    blob = {"sports": {"nba": {"accuracy": 0.54, "n_trades": 50}}}
    out = computed_sport_health.compute_sport_health_for_dashboard(blob)
    assert out["nba"]["alarm"] is True


def test_threshold_boundary_055_no_alarm() -> None:
    # accuracy == eşik (0.55) → alarm yok (strict <)
    blob = {"sports": {"nba": {"accuracy": 0.55, "n_trades": 50}}}
    out = computed_sport_health.compute_sport_health_for_dashboard(blob)
    assert out["nba"]["alarm"] is False


def test_threshold_boundary_just_below_alarm() -> None:
    blob = {"sports": {"nba": {"accuracy": 0.5499, "n_trades": 50}}}
    out = computed_sport_health.compute_sport_health_for_dashboard(blob)
    assert out["nba"]["alarm"] is True


def test_sport_key_lowercased() -> None:
    blob = {"sports": {"NBA": {"accuracy": 0.66, "n_trades": 50}}}
    out = computed_sport_health.compute_sport_health_for_dashboard(blob)
    assert "nba" in out
    assert "NBA" not in out


def test_malformed_sport_entry_skipped() -> None:
    blob = {
        "sports": {
            "tennis": {"accuracy": 0.72, "n_trades": 47},
            "broken": "not a dict",
            "no_accuracy": {"brier": 0.2, "n_trades": 30},
        }
    }
    out = computed_sport_health.compute_sport_health_for_dashboard(blob)
    assert "tennis" in out
    assert "broken" not in out
    assert "no_accuracy" not in out


def test_multiple_sports_independent_alarm_state() -> None:
    blob = {
        "sports": {
            "tennis": {"accuracy": 0.72, "n_trades": 47},
            "nba": {"accuracy": 0.48, "n_trades": 50},
            "soccer": {"accuracy": 0.61, "n_trades": 30},
        }
    }
    out = computed_sport_health.compute_sport_health_for_dashboard(blob)
    assert out["tennis"]["alarm"] is False
    assert out["nba"]["alarm"] is True
    assert out["soccer"]["alarm"] is False
