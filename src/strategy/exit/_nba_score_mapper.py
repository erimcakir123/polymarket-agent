"""NBA spread exit için our/opp skor map'i (SPEC-J Group 2B).

Slug suffix `-spread-home-` veya `-spread-away-` ile spread'in hangi takıma
ait olduğu bilinir; direction (BUY_YES / BUY_NO) ile bu spread'in cover'ına
bahis mi yoksa karşıtına mı yapıldığı belirlenir. Sonuç: "biz" hangi takım?

Saf fonksiyon — I/O yok, dış bağımlılık yok.
"""
from __future__ import annotations

from typing import Literal

from src.models.enums import Direction


def map_our_opp_scores(
    home_score: int,
    away_score: int,
    direction: str,                              # Direction enum veya raw "BUY_YES"/"BUY_NO" string
    spread_side: Literal["home", "away"],
) -> tuple[int, int]:
    """ESPN home/away skorlarını pozisyon perspektifine çevir.

    BUY_YES on home spread → "biz" = home → (home, away)
    BUY_NO  on home spread → "biz" = away → (away, home)  (home cover'a karşı)
    BUY_YES on away spread → "biz" = away → (away, home)
    BUY_NO  on away spread → "biz" = home → (home, away)
    """
    valid_directions = {Direction.BUY_YES.value, Direction.BUY_NO.value}
    if direction not in valid_directions:
        raise ValueError(
            f"direction must be one of {sorted(valid_directions)}, got {direction!r}"
        )
    if spread_side not in {"home", "away"}:
        raise ValueError(
            f"spread_side must be 'home' or 'away', got {spread_side!r}"
        )

    we_are_home = (
        direction == Direction.BUY_YES.value and spread_side == "home"
    ) or (
        direction == Direction.BUY_NO.value and spread_side == "away"
    )
    if we_are_home:
        return (home_score, away_score)
    return (away_score, home_score)
