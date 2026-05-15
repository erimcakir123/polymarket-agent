"""NBA dispatch router — Position'a göre totals exit'e yönlendirir.

NOT: SPREADS dispatch dalı 2026-05-15 rollback ile silindi (0 trade dead code).
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
        total_line=total_line,
        total_side=total_side,
    )


# ── Routing tests ──────────────────────────────────────────────────────────


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
        _elapsed_pct=0.95,
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
        _elapsed_pct=0.95,
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert result is None


def test_spreads_returns_none() -> None:
    # SPREADS artık dispatch scope dışı (2026-05-15 rollback) — None döner.
    pos = _make_position(
        slug="nba-game-2026-05-10-spread-home-team-cover-7p5",
        sports_market_type=SportsMarketType.SPREADS,
    )
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(period=4, clock=30, home=100, away=108),
        _elapsed_pct=0.95,
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
        _elapsed_pct=0.95,
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
        _elapsed_pct=0.95,
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert result is None


def test_basketball_exit_cfg_none_uses_defaults() -> None:
    # cfg=None → BasketballExitConfig() defaults; totals dispatch trigger.
    pos = _make_position(
        slug="nba-game-totals-over-220",
        sports_market_type=SportsMarketType.TOTALS,
        total_line=220.0,
        total_side=TotalSide.OVER,
    )
    result = check_nba_exit(
        pos=pos,
        score_info=_score_info(period=4, clock=30, home=100, away=100),
        _elapsed_pct=0.95,
        basketball_exit_cfg=None,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
