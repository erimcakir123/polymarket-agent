"""match_start_refresh light-cycle helper tests.

Covers normalize_game_start re-export, in-place mutation when Polymarket
returns a different gameStartTime, no-op when unchanged, and skip paths
(missing market, empty condition_id, None gamma_client, every-N gating).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.orchestration.match_start_refresh import (
    maybe_refresh_match_start,
    refresh_match_start_for_open_positions,
)
from src.infrastructure.apis.gamma_client import normalize_game_start


# ── Test doubles ─────────────────────────────────────────────────────────────


@dataclass
class _FakePos:
    condition_id: str
    match_start_iso: str


@dataclass
class _FakePortfolio:
    positions: dict[str, _FakePos] = field(default_factory=dict)


class _FakeGamma:
    """Records calls + returns canned market dicts keyed by condition_id."""

    def __init__(self, by_cid: dict[str, dict | None]) -> None:
        self._by_cid = by_cid
        self.calls: list[str] = []

    def fetch_market_by_condition_id(self, cid: str):
        self.calls.append(cid)
        return self._by_cid.get(cid)


# ── normalize_game_start (re-exported public API) ─────────────────────────────


def test_normalize_polymarket_format() -> None:
    assert normalize_game_start("2026-05-26 09:00:00+00") == "2026-05-26T09:00:00Z"
    assert normalize_game_start("2026-05-26T09:00:00+00:00") == "2026-05-26T09:00:00Z"
    assert normalize_game_start("2026-05-26T09:00:00Z") == "2026-05-26T09:00:00Z"
    assert normalize_game_start("") == ""
    assert normalize_game_start(None) == ""


# ── refresh_match_start_for_open_positions ───────────────────────────────────


def test_refresh_updates_changed_match_start() -> None:
    """Polymarket returns a newer gameStartTime → Position mutated in-place."""
    pos = _FakePos(condition_id="0xABC", match_start_iso="2026-05-25T09:00:00Z")
    portfolio = _FakePortfolio({"0xABC": pos})
    gamma = _FakeGamma({"0xABC": {"gameStartTime": "2026-05-26 09:00:00+00"}})

    n = refresh_match_start_for_open_positions(portfolio, gamma)

    assert n == 1
    assert pos.match_start_iso == "2026-05-26T09:00:00Z"
    assert gamma.calls == ["0xABC"]


def test_refresh_no_change_when_already_current() -> None:
    """Returned gameStartTime matches cached value → counter stays 0."""
    pos = _FakePos(condition_id="0xABC", match_start_iso="2026-05-26T09:00:00Z")
    portfolio = _FakePortfolio({"0xABC": pos})
    gamma = _FakeGamma({"0xABC": {"gameStartTime": "2026-05-26 09:00:00+00"}})

    n = refresh_match_start_for_open_positions(portfolio, gamma)

    assert n == 0
    assert pos.match_start_iso == "2026-05-26T09:00:00Z"


def test_refresh_skips_missing_market() -> None:
    """Gamma returns None (market not found / network error) → no mutation."""
    pos = _FakePos(condition_id="0xABC", match_start_iso="2026-05-25T09:00:00Z")
    portfolio = _FakePortfolio({"0xABC": pos})
    gamma = _FakeGamma({"0xABC": None})

    n = refresh_match_start_for_open_positions(portfolio, gamma)

    assert n == 0
    assert pos.match_start_iso == "2026-05-25T09:00:00Z"


def test_refresh_skips_position_without_condition_id() -> None:
    """Empty cid → never call gamma, skip the position."""
    pos = _FakePos(condition_id="", match_start_iso="2026-05-25T09:00:00Z")
    portfolio = _FakePortfolio({"": pos})
    gamma = _FakeGamma({})

    n = refresh_match_start_for_open_positions(portfolio, gamma)

    assert n == 0
    assert gamma.calls == []


def test_refresh_handles_multiple_positions_mixed() -> None:
    """One position changes, another stays, third has no market."""
    pos1 = _FakePos("0xAAA", "2026-05-25T09:00:00Z")
    pos2 = _FakePos("0xBBB", "2026-05-26T10:00:00Z")
    pos3 = _FakePos("0xCCC", "2026-05-27T11:00:00Z")
    portfolio = _FakePortfolio({"0xAAA": pos1, "0xBBB": pos2, "0xCCC": pos3})
    gamma = _FakeGamma({
        "0xAAA": {"gameStartTime": "2026-05-26 09:00:00+00"},  # changed
        "0xBBB": {"gameStartTime": "2026-05-26 10:00:00+00"},  # unchanged
        "0xCCC": None,                                          # missing
    })

    n = refresh_match_start_for_open_positions(portfolio, gamma)

    assert n == 1
    assert pos1.match_start_iso == "2026-05-26T09:00:00Z"
    assert pos2.match_start_iso == "2026-05-26T10:00:00Z"
    assert pos3.match_start_iso == "2026-05-27T11:00:00Z"


# ── maybe_refresh_match_start (light-cycle trigger gate) ─────────────────────


def test_maybe_refresh_skips_when_disabled() -> None:
    """every_n_ticks=0 → never call gamma."""
    pos = _FakePos("0xAAA", "2026-05-25T09:00:00Z")
    portfolio = _FakePortfolio({"0xAAA": pos})
    gamma = _FakeGamma({"0xAAA": {"gameStartTime": "2026-05-26 09:00:00+00"}})

    n = maybe_refresh_match_start(tick_count=60, every_n_ticks=0,
                                  portfolio=portfolio, gamma_client=gamma)

    assert n == 0
    assert gamma.calls == []
    assert pos.match_start_iso == "2026-05-25T09:00:00Z"


def test_maybe_refresh_skips_when_gamma_none() -> None:
    """Test/legacy path: gamma_client=None bypasses refresh safely."""
    pos = _FakePos("0xAAA", "2026-05-25T09:00:00Z")
    portfolio = _FakePortfolio({"0xAAA": pos})

    n = maybe_refresh_match_start(tick_count=60, every_n_ticks=60,
                                  portfolio=portfolio, gamma_client=None)

    assert n == 0
    assert pos.match_start_iso == "2026-05-25T09:00:00Z"


def test_maybe_refresh_fires_on_nth_tick() -> None:
    """tick_count % N == 0 → refresh fires; otherwise skipped."""
    pos = _FakePos("0xAAA", "2026-05-25T09:00:00Z")
    portfolio = _FakePortfolio({"0xAAA": pos})
    gamma = _FakeGamma({"0xAAA": {"gameStartTime": "2026-05-26 09:00:00+00"}})

    # Off-cadence ticks: nothing happens
    for tick in (1, 30, 59, 61, 119):
        n = maybe_refresh_match_start(tick_count=tick, every_n_ticks=60,
                                      portfolio=portfolio, gamma_client=gamma)
        assert n == 0
    assert gamma.calls == []

    # On-cadence tick: fires
    n = maybe_refresh_match_start(tick_count=60, every_n_ticks=60,
                                  portfolio=portfolio, gamma_client=gamma)
    assert n == 1
    assert gamma.calls == ["0xAAA"]
    assert pos.match_start_iso == "2026-05-26T09:00:00Z"


def test_maybe_refresh_swallows_gamma_exceptions() -> None:
    """Light cycle must never crash if gamma raises unexpectedly."""
    pos = _FakePos("0xAAA", "2026-05-25T09:00:00Z")
    portfolio = _FakePortfolio({"0xAAA": pos})

    class _BrokenGamma:
        def fetch_market_by_condition_id(self, cid: str):
            raise RuntimeError("gamma down")

    n = maybe_refresh_match_start(tick_count=60, every_n_ticks=60,
                                  portfolio=portfolio, gamma_client=_BrokenGamma())

    assert n == 0
    assert pos.match_start_iso == "2026-05-25T09:00:00Z"
