"""Fixed-tier position sizing (DECISIONS §6.5, SPEC-P 2026-05-21) — pure, no I/O.

Sabit-tier sizing: tier'e göre dolar miktarı sabittir, bankroll dalgalanmasından
bağımsız (SPEC-P). C → 0 (entry bloklanır).

`fixed_bet_usdc` caller'dan parametre olarak gelir (config.yaml > risk.fixed_bet_usdc).
Tek doğruluk kaynağı: config.
"""
from __future__ import annotations

POLYMARKET_MIN_ORDER_USDC = 5.0


def confidence_position_size(
    confidence: str,
    fixed_bet_usdc: dict[str, float],
) -> float:
    """Confidence tier bazlı sabit dolar bahis. C → 0.

    `fixed_bet_usdc`: tier → USDC miktarı (config.yaml > risk.fixed_bet_usdc).
    """
    if confidence == "C":
        return 0.0

    size = fixed_bet_usdc.get(confidence, 0.0)
    return max(0.0, round(size, 2))
