"""Position modeli — SPEC-J basketbol totals alanları (sports_market_type, total_line, total_side).

NOT: spread_line alanı 2026-05-15 rollback (Faz 4/10) ile silindi —
NBA spread exit modülü Faz 3'te silinmişti, alan orphan kaldı.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.enums import SportsMarketType, TotalSide
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
    assert p.sports_market_type == SportsMarketType.MONEYLINE
    assert p.total_line is None
    assert p.total_side is None


def test_position_loads_old_json_without_basketball_fields() -> None:
    # Pre-SPEC-J kalmış bir JSON kaydı: yeni alanlar YOK.
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
    assert p.sports_market_type == SportsMarketType.MONEYLINE
    assert p.total_line is None
    assert p.total_side is None
    assert p.confidence == "A"


def test_position_sports_market_type_string_coerced_to_enum() -> None:
    # Eski JSON/dict'te bare string "moneyline" varsa pydantic enum'a coerce etmeli.
    p = Position.model_validate({**_valid(), "sports_market_type": "moneyline"})
    assert p.sports_market_type == SportsMarketType.MONEYLINE
    assert isinstance(p.sports_market_type, SportsMarketType)


def test_position_sports_market_type_invalid_string_rejected() -> None:
    # Enum gerçek doğrulama yapıyor: tanımsız değer reject edilmeli.
    with pytest.raises(ValidationError):
        Position(**_valid(sports_market_type="random_value"))


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
    assert restored.sports_market_type == SportsMarketType.TOTALS
    assert restored.total_line == 215.5
    assert restored.total_side == TotalSide.OVER


def test_position_explicit_extras_ignored() -> None:
    # extra="ignore" davranışı korunmalı: stray alan sessizce yutulur.
    # Eski JSON'da spread_line varsa da problem değil — pydantic ignore.
    payload = _valid(legacy_field=5, another_extra="x", spread_line=-7.5)
    p = Position(**payload)
    assert p.sports_market_type == SportsMarketType.MONEYLINE
    assert not hasattr(p, "legacy_field")
    assert not hasattr(p, "spread_line")
