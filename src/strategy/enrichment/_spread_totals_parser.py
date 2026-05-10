"""SPEC-K: Bookmaker spread/totals market parser — saf veri dönüşümü.

Odds API bookmaker market dict'inden (line, prob_a, prob_b) çıkarır.
Vig normalize + line tolerance + outlier reddetme tek yerden.

Pure function — I/O yok, logging yok. Çağıran katman (odds_enricher) toplar.
"""
from __future__ import annotations

# Vig sanity (2-way): tipik 1.02-1.08; outlier window aynı moneyline ile (TDD §6.1).
_VIG_TOTAL_MIN = 0.85
_VIG_TOTAL_MAX = 1.20


def parse_bookmaker_spread(
    spread_market: dict,
    home_team: str,
    away_team: str,
    target_line: float,
    line_tolerance: float = 0.5,
) -> tuple[float, float, float] | None:
    """Bookmaker'ın 'spreads' market'ından (bookmaker_abs_line, home_prob, away_prob).

    Outcomes:
      {"name": home_team, "price": 1.91, "point": -7.5}    # home favored
      {"name": away_team, "price": 1.91, "point": +7.5}    # away underdog

    target_line: Polymarket'in mutlak spread değeri (örn 7.5).
    line_tolerance: ±tolerance içinde line varsa kabul; bookmaker line dönülür.

    Vig normalize: home_implied + away_implied → toplam ≈ 1.05-1.10.
    [_VIG_TOTAL_MIN, _VIG_TOTAL_MAX] dışında ise outlier → None.
    """
    home_outcome = away_outcome = None
    for outcome in spread_market.get("outcomes", []):
        name = outcome.get("name", "")
        if name == home_team:
            home_outcome = outcome
        elif name == away_team:
            away_outcome = outcome

    if home_outcome is None or away_outcome is None:
        return None

    home_point = home_outcome.get("point")
    home_price = home_outcome.get("price", 0) or 0
    away_price = away_outcome.get("price", 0) or 0
    if home_point is None or home_price <= 1 or away_price <= 1:
        return None

    bookmaker_abs_line = abs(float(home_point))
    if abs(bookmaker_abs_line - target_line) > line_tolerance:
        return None

    home_implied = 1.0 / home_price
    away_implied = 1.0 / away_price
    total = home_implied + away_implied
    if not (_VIG_TOTAL_MIN <= total <= _VIG_TOTAL_MAX):
        return None

    return bookmaker_abs_line, home_implied / total, away_implied / total


def parse_bookmaker_totals(
    totals_market: dict,
    target_line: float,
    line_tolerance: float = 0.5,
) -> tuple[float, float, float] | None:
    """Bookmaker'ın 'totals' market'ından (bookmaker_line, over_prob, under_prob).

    Outcomes:
      {"name": "Over",  "price": 1.91, "point": 215.5}
      {"name": "Under", "price": 1.91, "point": 215.5}

    Aynı vig + tolerance kuralları. "Over"/"Under" name case-insensitive.
    """
    over_outcome = under_outcome = None
    for outcome in totals_market.get("outcomes", []):
        name = outcome.get("name", "").lower()
        if name == "over":
            over_outcome = outcome
        elif name == "under":
            under_outcome = outcome

    if over_outcome is None or under_outcome is None:
        return None

    over_point = over_outcome.get("point")
    over_price = over_outcome.get("price", 0) or 0
    under_price = under_outcome.get("price", 0) or 0
    if over_point is None or over_price <= 1 or under_price <= 1:
        return None

    bookmaker_line = float(over_point)
    if abs(bookmaker_line - target_line) > line_tolerance:
        return None

    over_implied = 1.0 / over_price
    under_implied = 1.0 / under_price
    total = over_implied + under_implied
    if not (_VIG_TOTAL_MIN <= total <= _VIG_TOTAL_MAX):
        return None

    return bookmaker_line, over_implied / total, under_implied / total
