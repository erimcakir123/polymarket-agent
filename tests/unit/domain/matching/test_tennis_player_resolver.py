"""Tennis player name resolver tests."""
from __future__ import annotations

import pytest

from src.domain.matching.tennis_player_resolver import (
    PlayerRecord,
    PlayerRegistry,
    ResolutionFailure,
    build_registry,
    resolve_player,
)


@pytest.fixture
def sample_registry() -> PlayerRegistry:
    records = [
        PlayerRecord(sackmann_id="104925", first="Daniil", last="Medvedev", hand="R", country="RUS"),
        PlayerRecord(sackmann_id="207989", first="Jannik", last="Sinner", hand="R", country="ITA"),
        PlayerRecord(sackmann_id="208029", first="Carlos", last="Alcaraz Garfia", hand="R", country="ESP"),
        PlayerRecord(sackmann_id="208053", first="Felix", last="Auger-Aliassime", hand="R", country="CAN"),
        PlayerRecord(sackmann_id="207666", first="Stefanos", last="Tsitsipas", hand="R", country="GRE"),
        PlayerRecord(sackmann_id="206173", first="Alexander", last="Zverev", hand="R", country="GER"),
        PlayerRecord(sackmann_id="209968", first="Flavio", last="Cobolli", hand="R", country="ITA"),
    ]
    return build_registry(records)


def test_resolve_exact_full_name(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("Daniil Medvedev", sample_registry)
    assert record is not None
    assert record.sackmann_id == "104925"


def test_resolve_lowercase(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("daniil medvedev", sample_registry)
    assert record is not None
    assert record.sackmann_id == "104925"


def test_resolve_surname_only(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("Medvedev", sample_registry)
    assert record is not None
    assert record.sackmann_id == "104925"


def test_resolve_first_initial_surname(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("D. Medvedev", sample_registry)
    assert record is not None
    assert record.sackmann_id == "104925"


def test_resolve_diacritic_normalized(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("Stefanos Tsitsipás", sample_registry)
    assert record is not None
    assert record.sackmann_id == "207666"


def test_resolve_hyphenated_surname(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("Auger-Aliassime", sample_registry)
    assert record is not None
    assert record.sackmann_id == "208053"


def test_resolve_partial_surname_alcaraz(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("Alcaraz", sample_registry)
    assert record is not None
    assert record.sackmann_id == "208029"


def test_resolve_unknown_returns_none(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("John Doe Nobody", sample_registry)
    assert record is None


def test_resolve_empty_string_returns_none(sample_registry: PlayerRegistry) -> None:
    record = resolve_player("", sample_registry)
    assert record is None


def test_resolve_disambiguates_same_surname_via_first_initial() -> None:
    records = [
        PlayerRecord(sackmann_id="100001", first="Roger", last="Federer", hand="R", country="SUI"),
        PlayerRecord(sackmann_id="100002", first="Mischa", last="Federer", hand="R", country="SUI"),
    ]
    registry = build_registry(records)
    rec_r = resolve_player("R. Federer", registry)
    rec_m = resolve_player("M. Federer", registry)
    assert rec_r is not None and rec_r.sackmann_id == "100001"
    assert rec_m is not None and rec_m.sackmann_id == "100002"


def test_resolve_surname_only_ambiguous_returns_none() -> None:
    """Same surname, no first letter clue - cannot disambiguate."""
    records = [
        PlayerRecord(sackmann_id="100001", first="Roger", last="Federer", hand="R", country="SUI"),
        PlayerRecord(sackmann_id="100002", first="Mischa", last="Federer", hand="R", country="SUI"),
    ]
    registry = build_registry(records)
    assert resolve_player("Federer", registry) is None
