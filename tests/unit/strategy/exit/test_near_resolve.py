"""near_resolve.py için birim testler (TDD §6.11)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.models.position import Position
from src.strategy.exit.near_resolve import check


def _pos(yes: float, direction: str = "BUY_YES", match_start_iso: str = "") -> Position:
    return Position(
        condition_id="c", token_id="t", direction=direction,
        entry_price=0.40, size_usdc=40, shares=100,
        current_price=yes, anchor_probability=0.55,
        match_start_iso=match_start_iso,
    )


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_below_threshold_no_exit() -> None:
    p = _pos(yes=0.90)
    assert check(p) is False


def test_at_threshold_with_no_match_start_exits() -> None:
    # match_start_iso boş → güven ver, threshold yeterli
    p = _pos(yes=0.94, match_start_iso="")
    assert check(p) is True


def test_above_threshold_well_into_match_exits() -> None:
    # Maç 30 dk önce başlamış
    start = datetime.now(timezone.utc) - timedelta(minutes=30)
    p = _pos(yes=0.95, match_start_iso=_iso(start))
    assert check(p) is True


def test_pre_match_rejects() -> None:
    # Maç 1 saat sonra başlayacak → pre-match, reddet
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    p = _pos(yes=0.95, match_start_iso=_iso(start))
    assert check(p) is False


def test_just_started_under_10min_rejects() -> None:
    # Maç 5 dk önce başlamış → WS spike riski
    start = datetime.now(timezone.utc) - timedelta(minutes=5)
    p = _pos(yes=0.98, match_start_iso=_iso(start))
    assert check(p) is False


def test_after_10min_accepts() -> None:
    start = datetime.now(timezone.utc) - timedelta(minutes=11)
    p = _pos(yes=0.95, match_start_iso=_iso(start))
    assert check(p) is True


def test_buy_no_owned_token_near_resolve() -> None:
    # BUY_NO: current_price = NO token fiyatı. 0.95 = NO token 95¢ → owned near-resolve → exit.
    start = datetime.now(timezone.utc) - timedelta(minutes=30)
    p = _pos(yes=0.95, direction="BUY_NO", match_start_iso=_iso(start))
    assert check(p) is True


def test_buy_no_losing_side_no_exit() -> None:
    # BUY_NO ama NO token 5¢ → kaybediyoruz, near_resolve tetiklenmez.
    start = datetime.now(timezone.utc) - timedelta(minutes=30)
    p = _pos(yes=0.05, direction="BUY_NO", match_start_iso=_iso(start))
    assert check(p) is False


def test_bad_iso_format_trusts_threshold() -> None:
    p = _pos(yes=0.95, match_start_iso="not-a-date")
    assert check(p) is True
