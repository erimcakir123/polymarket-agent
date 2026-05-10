"""NBA dispatch router — Position'a göre spread/totals exit'e yönlendirir.

Real exit fonksiyonları kullanılır (mock yok), integration-style.
"""
from __future__ import annotations

from src.config.settings import BasketballExitConfig
from src.models.enums import Direction, ExitReason, SportsMarketType, TotalSide
from src.models.position import Position
from src.strategy.exit._nba_dispatch import check_nba_exit


# ── helpers ────────────────────────────────────────────────────────────────


def _score_info(
    *,
    available: bool = True,
    period: int = 4,
    clock: int = 30,
    home: int = 100,
    away: int = 108,
) -> dict:
    return {
        "available": available,
        "period_number": period,
        "clock_seconds": clock,
        "home_score": home,
        "away_score": away,
    }


def _make_position(
    *,
    slug: str,
    sports_market_type: SportsMarketType,
    spread_line: float | None = None,
    total_line: float | None = None,
    total_side: TotalSide | None = None,
    direction: str = Direction.BUY_YES.value,
) -> Position:
    return Position(
        condition_id="cond-1",
        token_id="tok-1",
        direction=direction,
        entry_price=0.50,
        size_usdc=10.0,
        shares=20.0,
        slug=slug,
        anchor_probability=0.55,
        current_price=0.40,
        bid_price=0.10,
        sport_tag="nba",
        sports_market_type=sports_market_type,
        spread_line=spread_line,
        total_line=total_line,
        total_side=total_side,
    )


# ── Routing tests ──────────────────────────────────────────────────────────


def test_spreads_routes_to_spread_exit_and_returns_score_exit() -> None:
    # BUY_YES on home spread, Q4, clock=30s, 8 sayı geride → SPREAD_MATH_DEAD.
    pos = _make_position(
        slug="nba-game-2026-05-10-spread-home-team-cover-7p5",
        sports_market_type=SportsMarketType.SPREADS,
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
    )
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(period=4, clock=30, home=100, away=108),
        elapsed_pct=0.95,
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT


def test_totals_routes_to_totals_exit_and_returns_score_exit() -> None:
    # OVER, Q4, clock=30s, target=220, current=200 → TOTALS_MATH_DEAD.
    pos = _make_position(
        slug="nba-game-2026-05-10-totals-over-220",
        sports_market_type=SportsMarketType.TOTALS,
        total_line=220.0,
        total_side=TotalSide.OVER,
    )
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(period=4, clock=30, home=100, away=100),
        elapsed_pct=0.95,
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT


def test_moneyline_returns_none() -> None:
    # Moneyline NBA pos → bu dispatch için scope dışı, None.
    pos = _make_position(
        slug="nba-game-2026-05-10-team-wins",
        sports_market_type=SportsMarketType.MONEYLINE,
    )
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(period=4, clock=30, home=100, away=108),
        elapsed_pct=0.95,
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert result is None


def test_spreads_with_none_spread_line_returns_none() -> None:
    pos = _make_position(
        slug="nba-game-spread-home-team",
        sports_market_type=SportsMarketType.SPREADS,
        spread_line=None,
    )
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(),
        elapsed_pct=0.95,
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert result is None


def test_totals_with_none_total_line_returns_none() -> None:
    pos = _make_position(
        slug="nba-game-totals-over",
        sports_market_type=SportsMarketType.TOTALS,
        total_line=None,
        total_side=TotalSide.OVER,
    )
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(),
        elapsed_pct=0.95,
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert result is None


def test_totals_with_none_total_side_returns_none() -> None:
    pos = _make_position(
        slug="nba-game-totals",
        sports_market_type=SportsMarketType.TOTALS,
        total_line=220.0,
        total_side=None,
    )
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(),
        elapsed_pct=0.95,
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert result is None


def test_spread_slug_without_home_or_away_marker_returns_none() -> None:
    # Slug'da -spread-home- veya -spread-away- yoksa defensively None döner.
    pos = _make_position(
        slug="nba-game-2026-05-10-cover-line",
        sports_market_type=SportsMarketType.SPREADS,
        spread_line=-7.5,
    )
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(),
        elapsed_pct=0.95,
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert result is None


def test_basketball_exit_cfg_none_uses_defaults() -> None:
    # cfg=None → BasketballExitConfig() defaults; spreads SPREAD_MATH_DEAD trigger.
    pos = _make_position(
        slug="nba-game-spread-home-team",
        sports_market_type=SportsMarketType.SPREADS,
        spread_line=0.0,
    )
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(period=4, clock=30, home=100, away=108),
        elapsed_pct=0.95,
        basketball_exit_cfg=None,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT


def test_spread_away_slug_routes_correctly() -> None:
    # BUY_YES away spread, away takım önde → cover'dayız → no exit.
    pos = _make_position(
        slug="nba-game-2026-05-10-spread-away-team-cover",
        sports_market_type=SportsMarketType.SPREADS,
        spread_line=-3.5,
        direction=Direction.BUY_YES.value,
    )
    # away=110, home=100; mapper BUY_YES away → our=away=110, opp=home=100 → diff=10.
    # margin = -3.5 - 10 = -13.5 → cover'dayız → None.
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(period=4, clock=30, home=100, away=110),
        elapsed_pct=0.95,
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert result is None
