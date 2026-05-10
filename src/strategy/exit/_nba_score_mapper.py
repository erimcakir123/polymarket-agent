"""NBA spread exit için our/opp skor map'i (SPEC-J Group 2B).

Slug suffix `-spread-home-` veya `-spread-away-` ile spread'in hangi takıma
ait olduğu bilinir; direction (BUY_YES / BUY_NO) ile bu spread'in cover'ına
bahis mi yoksa karşıtına mı yapıldığı belirlenir. Sonuç: "biz" hangi takım?

Saf fonksiyon — I/O yok, dış bağımlılık yok.
"""
from __future__ import annotations


def map_our_opp_scores(
    home_score: int,
    away_score: int,
    direction: str,
    spread_side: str,
) -> tuple[int, int]:
    """ESPN home/away skorlarını pozisyon perspektifine çevir.

    BUY_YES on home spread → "biz" = home → (home, away)
    BUY_NO  on home spread → "biz" = away → (away, home)  (home cover'a karşı)
    BUY_YES on away spread → "biz" = away → (away, home)
    BUY_NO  on away spread → "biz" = home → (home, away)
    """
    if direction not in {"BUY_YES", "BUY_NO"}:
        raise ValueError(f"direction must be BUY_YES or BUY_NO, got {direction!r}")
    if spread_side not in {"home", "away"}:
        raise ValueError(f"spread_side must be 'home' or 'away', got {spread_side!r}")

    we_are_home = (direction == "BUY_YES" and spread_side == "home") or (
        direction == "BUY_NO" and spread_side == "away"
    )
    if we_are_home:
        return (home_score, away_score)
    return (away_score, home_score)
