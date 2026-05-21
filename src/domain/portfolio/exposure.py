"""Exposure guard — pure function (DECISIONS §6.15, SPEC-P 2026-05-21).

Exposure cap ölçüsü = toplam_yatırılan / TOPLAM_PORTFÖY_DEĞERİ.
TOPLAM_PORTFÖY_DEĞERİ = nakit (portfolio.bankroll) + toplam_yatırılan
                     = initial + realized_pnl (kullanıcı tanımı: locked + non-lost).

Yumuşak cap kuralı (SPEC-P):
- Exposure < cap → yeni trade tam sabit-tier boyutunda alınır (sonuç cap'i geçse de OK).
- Exposure ≥ cap → yeni trade reddedilir.
- Size clipping uygulanmaz.
"""
from __future__ import annotations


def at_or_over_cap(
    positions: dict,
    total_portfolio_value: float,
    soft_cap_pct: float,
) -> bool:
    """True ise yeni trade alınmaz. Exposure ≥ soft_cap.

    positions: Position objects dict (her biri .size_usdc'ye sahip).
    total_portfolio_value: nakit + açık pozisyonların toplam size'ı.
    soft_cap_pct: max_exposure_pct (default %50).
    """
    if total_portfolio_value <= 0:
        return True
    total_invested = sum(getattr(p, "size_usdc", 0.0) for p in positions.values())
    return total_invested >= total_portfolio_value * soft_cap_pct


def fill_ratio(positions: dict, total_portfolio_value: float) -> float:
    """Pozisyon doluluk oranı = toplam yatırılan / toplam portföy değeri. 0.0-1.0+."""
    if total_portfolio_value <= 0:
        return 0.0
    total_invested = sum(getattr(p, "size_usdc", 0.0) for p in positions.values())
    return total_invested / total_portfolio_value
