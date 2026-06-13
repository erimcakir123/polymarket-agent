"""Taze maç sonucu — saf domain dataclass + çözülmüş market'ten kazanan çıkarımı.

Polymarket question "Tournament: A vs B" → YES=A (ilk), NO=B (ikinci).
outcomePrices=['1','0'] → A kazandı; ['0','1'] → B kazandı; ['0.5','0.5'] → void (None).
Glicko reytingi için skor gerekmez — sadece (kazanan, kaybeden, zemin, tarih).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

_VOID_PAYOUT = 0.5
_VOID_TOL = 0.01


@dataclass(frozen=True)
class HarvestedResult:
    winner: str
    loser: str
    surface: str  # "Hard" | "Clay" | "Grass" | "Unknown"
    date: str     # YYYYMMDD
    condition_id: str = ""  # Polymarket condition_id — dedupe anahtarı (boşsa match_key'e düşer)

    def match_key(self) -> str:
        return f"{self.date}|{self.winner}|{self.loser}"


def winner_loser_from_resolution(
    market: dict, player_a: str, player_b: str
) -> tuple[str, str] | None:
    """Çözülmüş market + oyuncu adları → (kazanan, kaybeden). Çözülmemiş/void → None.

    player_a = YES tarafı (ilk isim), player_b = NO tarafı (ikinci isim).
    """
    if not player_a or not player_b:
        return None
    if not market.get("closed") or market.get("umaResolutionStatus") != "resolved":
        return None
    prices = market.get("outcomePrices", "[]")
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except json.JSONDecodeError:
            return None
    if not isinstance(prices, list) or len(prices) < 2:
        return None
    try:
        yes_payout = float(prices[0])
        no_payout = float(prices[1])
    except (ValueError, TypeError):
        return None
    if abs(yes_payout - _VOID_PAYOUT) < _VOID_TOL:
        return None  # void/iptal
    if yes_payout >= 0.99:
        return (player_a, player_b)
    if no_payout >= 0.99:
        return (player_b, player_a)
    return None
