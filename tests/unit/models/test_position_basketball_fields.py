"""Position modeli — SPEC-J basketbol alanları (sports_market_type, spread_line, total_line, total_side)."""
from __future__ import annotations

from src.models.position import Position


def _valid(**overrides) -> dict:
    base = dict(
        condition_id="0x1",
        token_id="tok",
        direction="BUY_YES",
        entry_price=0.40,
        size_usdc=40.0,
        shares=100.0,
        current_price=0.40,
        anchor_probability=0.55,
    )
    base.update(overrides)
    return base


def test_position_default_market_type_is_moneyline() -> None:
    p = Position(**_valid())
    assert p.sports_market_type == "moneyline"
    assert p.spread_line is None
    assert p.total_line is None
    assert p.total_side is None


def test_position_loads_old_json_without_basketball_fields() -> None:
    # Pre-SPEC-J kalmış bir JSON kaydı: yeni 4 alan YOK.
    old_dict = dict(
        condition_id="0xabc",
        token_id="tk",
        direction="BUY_YES",
        entry_price=0.42,
        size_usdc=42.0,
        shares=100.0,
        current_price=0.42,
        anchor_probability=0.55,
        slug="nba-bos-mia-2026-04-15",
        confidence="A",
        sport_tag="nba",
    )
    p = Position.model_validate(old_dict)
    assert p.sports_market_type == "moneyline"
    assert p.spread_line is None
    assert p.total_line is None
    assert p.total_side is None
    assert p.confidence == "A"


def test_position_spread_fields_persist_through_dump_load() -> None:
    p = Position(
        **_valid(
            sports_market_type="spreads",
            spread_line=-7.5,
        )
    )
    raw = p.model_dump_json()
    restored = Position.model_validate_json(raw)
    assert restored.sports_market_type == "spreads"
    assert restored.spread_line == -7.5
    assert restored.total_line is None
    assert restored.total_side is None


def test_position_total_fields_persist_through_dump_load() -> None:
    p = Position(
        **_valid(
            sports_market_type="totals",
            total_line=215.5,
            total_side="over",
        )
    )
    raw = p.model_dump_json()
    restored = Position.model_validate_json(raw)
    assert restored.sports_market_type == "totals"
    assert restored.total_line == 215.5
    assert restored.total_side == "over"
    assert restored.spread_line is None


def test_position_explicit_extras_ignored() -> None:
    # extra="ignore" davranışı korunmalı: stray alan sessizce yutulur.
    payload = _valid(legacy_field=5, another_extra="x")
    p = Position(**payload)
    assert p.sports_market_type == "moneyline"
    assert not hasattr(p, "legacy_field")
