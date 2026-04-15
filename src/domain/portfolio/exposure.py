"""Exposure guard — pure function (TDD §6.15 cap).

Exposure cap ölçüsü = (toplam_yatırılan + aday) / TOPLAM_PORTFÖY_DEĞERİ.
TOPLAM_PORTFÖY_DEĞERİ = nakit (portfolio.bankroll) + toplam_yatırılan.

Yalnız `bankroll` (nakit) paydada kullanılırsa pozisyon açıldıkça payda küçülür
ve gerçek exposure'a göre yüksek gösterir → cap erken tetiklenir. Caller bu
yüzden `total_portfolio_value` geçmelidir.
"""
from __future__ import annotations


def exceeds_exposure_limit(
    positions: dict,
    candidate_size: float,
    total_portfolio_value: float,
    max_exposure_pct: float,
) -> bool:
    """True: candidate_size eklendiğinde exposure cap aşılır.

    positions: Position objects dict (her biri .size_usdc'ye sahip).
    total_portfolio_value: nakit + açık pozisyonların toplam size'ı.
    """
    if total_portfolio_value <= 0:
        return True
    total_invested = sum(getattr(p, "size_usdc", 0.0) for p in positions.values())
    return (total_invested + candidate_size) / total_portfolio_value > max_exposure_pct


def fill_ratio(positions: dict, total_portfolio_value: float) -> float:
    """Pozisyon doluluk oranı = toplam yatırılan / toplam portföy değeri. 0.0-1.0+."""
    if total_portfolio_value <= 0:
        return 0.0
    total_invested = sum(getattr(p, "size_usdc", 0.0) for p in positions.values())
    return total_invested / total_portfolio_value
