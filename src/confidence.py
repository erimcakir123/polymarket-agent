"""Bookmaker-derived confidence tiers (A/B/C).

Replaces the old AI-based confidence system with a pure bookmaker signal:
  A = sharp book present (Pinnacle/Betfair Exchange)
  B = bookmaker weight >= 5
  C = insufficient data -> skip entry
"""


def derive_confidence(bm_weight: float | None, has_sharp: bool) -> str:
    """Derive confidence tier from bookmaker signal strength.

    Args:
        bm_weight: Total bookmaker weight (sum of individual weights).
        has_sharp: Whether a sharp book (Pinnacle/Betfair Exchange) is present.

    Returns:
        "A", "B", or "C".
    """
    if bm_weight is None or bm_weight < 5:
        return "C"
    if has_sharp:
        return "A"
    return "B"
