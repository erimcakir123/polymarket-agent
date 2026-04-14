"""Graduated stop-loss — elapsed-aware (TDD §6.8).

max_loss = base_tier × price_mult × score_adj (momentum_tighten ek ayar).
Pure; score_info dict dışarıdan verilir.

Base tiers (elapsed_pct → max_loss):
  0.85+ : 0.15 (final phase)
  0.65+ : 0.20 (late)
  0.40+ : 0.30 (mid)
  0.00+ : 0.40 (early)
  <0    : 0.40 (pre-match — erken davran)

Price multipliers (entry_price → width):
  <0.20  : 1.50 (underdog, daha geniş tolerans)
  <0.35  : 1.25
  ≤0.50  : 1.00
  <0.70  : 0.85
  ≥0.70  : 0.70 (favori, daha dar)

Score adjustment:
  score_info.available + map_diff > 0 → 1.25 (önde, gevşet)
  score_info.available + map_diff < 0 → 0.75 (geride, sıkıştır)

Momentum tighten (graduated SL içinde):
  consecutive_down ≥ 5 AND cumulative_drop ≥ 0.10 → max_loss × 0.60
  consecutive_down ≥ 3 AND cumulative_drop ≥ 0.05 → max_loss × 0.75

Sonuç [0.05, 0.70] aralığına clamp.
"""
from __future__ import annotations

from dataclasses import dataclass

# (elapsed_pct threshold, max_loss) — yüksekten aşağıya, ilk eşleşen kullanılır
_BASE_TIERS: list[tuple[float, float]] = [
    (0.85, 0.15),
    (0.65, 0.20),
    (0.40, 0.30),
    (0.00, 0.40),
]

_PREMATCH_BASE = 0.40

_MOMENTUM_DEEP_MULT = 0.60   # consecutive_down ≥ 5 AND drop ≥ 0.10
_MOMENTUM_MILD_MULT = 0.75   # consecutive_down ≥ 3 AND drop ≥ 0.05


def get_entry_price_multiplier(entry_price: float) -> float:
    """Düşük giriş (underdog) → geniş tolerans; yüksek giriş (favori) → dar."""
    if entry_price < 0.20:
        return 1.50
    if entry_price < 0.35:
        return 1.25
    if entry_price <= 0.50:
        return 1.00
    if entry_price < 0.70:
        return 0.85
    return 0.70


def _base_tier(elapsed_pct: float) -> float:
    if elapsed_pct < 0:
        return _PREMATCH_BASE
    for threshold, loss in _BASE_TIERS:
        if elapsed_pct >= threshold:
            return loss
    return _BASE_TIERS[-1][1]


def _score_adjustment(score_info: dict) -> float:
    if not score_info.get("available"):
        return 1.0
    md = score_info.get("map_diff", 0)
    if md > 0:
        return 1.25
    if md < 0:
        return 0.75
    return 1.0


@dataclass
class MomentumResult:
    tighten: bool
    multiplier: float  # 1.0 = tighten yok, < 1.0 = sıkıştır


def compute_momentum_multiplier(consecutive_down: int, cumulative_drop: float) -> MomentumResult:
    """Ardışık düşüş sayısı + toplam düşüşe göre momentum tighten seviyesi."""
    # DEEP ilk (5+ aynı zamanda 3+'ın supersetidir)
    if consecutive_down >= 5 and cumulative_drop >= 0.10:
        return MomentumResult(tighten=True, multiplier=_MOMENTUM_DEEP_MULT)
    if consecutive_down >= 3 and cumulative_drop >= 0.05:
        return MomentumResult(tighten=True, multiplier=_MOMENTUM_MILD_MULT)
    return MomentumResult(tighten=False, multiplier=1.0)


def get_graduated_max_loss(
    elapsed_pct: float,
    entry_price: float,
    score_info: dict,
) -> float:
    """Max izin verilen kayıp yüzdesi [0.05, 0.70]."""
    base = _base_tier(elapsed_pct)
    price_mult = get_entry_price_multiplier(entry_price)
    score_adj = _score_adjustment(score_info)
    result = base * price_mult * score_adj
    return max(0.05, min(0.70, result))


def check(
    pos,
    elapsed_pct: float,
    effective_entry: float,
    score_info: dict | None = None,
) -> tuple[bool, float]:
    """Graduated SL tetiklendi mi? Returns (exit?, effective_max_loss).

    effective_max_loss = base × price_mult × score_adj × momentum_mult.
    exit? = unrealized_pnl_pct < -effective_max_loss.
    """
    score_info = score_info or {}
    max_loss = get_graduated_max_loss(elapsed_pct, effective_entry, score_info)
    momentum = compute_momentum_multiplier(
        consecutive_down=pos.consecutive_down_cycles,
        cumulative_drop=pos.cumulative_drop,
    )
    if momentum.tighten:
        max_loss = max(0.05, max_loss * momentum.multiplier)
    exit_now = pos.unrealized_pnl_pct < -max_loss
    return exit_now, max_loss
