"""Model output güvenlik kemeri — P(YES) [%5, %95] aralığına kırp.

Sapıtan model "%100 kazanır" derse:
  - Polymarket fiyat 50¢ olsa edge = 0.5 → büyük bahis
  - Gerçek tahmin %50 olsaymış, %0.50 ortalamadan büyük sapma → büyük kayıp

Cliprange tüm probability anchor'ların geçtiği son katman.
FiveThirtyEight + Pinnacle standart safety net.

Domain — saf math, I/O yok.
"""
from __future__ import annotations

# %5-%95 aralığı endüstri standardı (sportsbook risk limit'leri ile uyumlu).
PROB_FLOOR = 0.05
PROB_CEILING = 0.95


def cliprange(prob: float) -> float:
    """P(YES) → [%5, %95] aralığında kırp."""
    return max(PROB_FLOOR, min(PROB_CEILING, prob))
