"""Force-close strategy tests — saf karar mantığı.

Position.sports_market_type bir Enum (SportsMarketType) ve sınırlı set kabul
ediyor. check() ise market_type'ı ayrı bir str argüman alır — bu çağıran
katmanın (exit_processor) Position üzerinden string elde edip iletmesini
sağlar. Test'te de aynı düzen: Position'a güvenli bir default enum koy,
market_type'ı testin amaçladığı stringle doğrudan check()'e ver.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.infrastructure.apis.espn_client import MatchStatus
from src.models.enums import SportsMarketType
from src.models.position import Position
from src.strategy.exit.time_force_close import ForceCloseSignal, check


def _make_position(started_minutes_ago: int) -> Position:
    """Minimum alan setiyle bir Position üret — test factory.

    sports_market_type için güvenli enum default (MONEYLINE) kullan;
    test edilen market_type string'i check()'e doğrudan verilir.
    """
    start = datetime.now(timezone.utc) - timedelta(minutes=started_minutes_ago)
    return Position(
        condition_id="0xabc",
        token_id="123",
        direction="BUY_YES",
        entry_price=0.5,
        size_usdc=35.0,
        shares=70.0,
        slug="test-match",
        entry_timestamp=start,
        entry_reason="test",
        confidence="B",
        anchor_probability=0.5,
        current_price=0.05,
        bid_price=0.04,
        match_start_iso=start.isoformat(),
        event_id="401234",
        sports_market_type=SportsMarketType.MONEYLINE,
    )


def test_espn_final_returns_signal() -> None:
    pos = _make_position(100)
    espn = MatchStatus(state="post", period=3, is_completed=True)
    now = datetime.now(timezone.utc)
    result = check(
        pos, espn, now, timeouts={"tennis_match_winner": 200},
        market_type="tennis_match_winner",
    )
    assert isinstance(result, ForceCloseSignal)
    assert result.reason == "espn_event_ended"


def test_espn_set_2_for_first_set_market_returns_signal() -> None:
    pos = _make_position(70)
    espn = MatchStatus(state="in", period=2, is_completed=False)
    now = datetime.now(timezone.utc)
    result = check(
        pos, espn, now, timeouts={"tennis_first_set_winner": 60},
        market_type="tennis_first_set_winner",
    )
    assert result is not None
    assert result.reason == "espn_event_ended"


def test_espn_still_in_set_1_returns_none() -> None:
    pos = _make_position(30)
    espn = MatchStatus(state="in", period=1, is_completed=False)
    now = datetime.now(timezone.utc)
    result = check(
        pos, espn, now, timeouts={"tennis_first_set_winner": 60},
        market_type="tennis_first_set_winner",
    )
    assert result is None


def test_no_espn_elapsed_exceeds_timeout_returns_signal() -> None:
    pos = _make_position(90)
    now = datetime.now(timezone.utc)
    result = check(
        pos, espn_status=None, now=now,
        timeouts={"tennis_first_set_winner": 60},
        market_type="tennis_first_set_winner",
    )
    assert result is not None
    assert result.reason == "time_expired"


def test_no_espn_elapsed_under_timeout_returns_none() -> None:
    pos = _make_position(30)
    now = datetime.now(timezone.utc)
    result = check(
        pos, espn_status=None, now=now,
        timeouts={"tennis_first_set_winner": 60},
        market_type="tennis_first_set_winner",
    )
    assert result is None


def test_missing_match_start_returns_none() -> None:
    pos = _make_position(90)
    pos.match_start_iso = ""
    now = datetime.now(timezone.utc)
    result = check(
        pos, espn_status=None, now=now,
        timeouts={"tennis_first_set_winner": 60},
        market_type="tennis_first_set_winner",
    )
    assert result is None


def test_unknown_market_type_uses_default() -> None:
    pos = _make_position(400)
    now = datetime.now(timezone.utc)
    result = check(
        pos, espn_status=None, now=now, timeouts={"default": 300},
        market_type="unknown_market_xyz",
    )
    assert result is not None
    assert result.reason == "time_expired"


def test_unknown_market_type_no_default_returns_none() -> None:
    pos = _make_position(400)
    now = datetime.now(timezone.utc)
    result = check(
        pos, espn_status=None, now=now, timeouts={},
        market_type="unknown_market_xyz",
    )
    assert result is None
