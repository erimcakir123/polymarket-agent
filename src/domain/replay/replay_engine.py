"""Retroactive replay engine — pozisyonu fiyat geçmişine karşı simüle eder.

ARCH Kural 1: Domain Strategy import etmez. Bu engine, exit kurallarının sabitlerini
DIŞARIDAN `ExitRulesConfig` dataclass'ı olarak alır (script wire'lar). Böylece
domain saf kalır, "EXACT same logic" garantisi sayısal sabitlerin script
seviyesinde scale_out/resolved/sport_rules modüllerinden okunmasıyla sağlanır.

Çıkış zinciri (her tick'te öncelik sırasıyla değerlendirilir, ilk tetiklenen kazanır):
  0. RESOLVED       (price ≤ lost_threshold veya ≥ won_threshold)        → full
  1. NEAR_RESOLVE   (price ≥ near_resolve_threshold AND elapsed ≥ guard) → full
  2. SCALE_OUT t1   (progress ≥ tier1_threshold, scale_out_tier == 0)    → partial
  3. SCALE_OUT t2   (progress ≥ tier2_threshold, scale_out_tier == 1)    → partial
  4. STOP_LOSS      (pnl_pct ≤ -stop_loss_pct)                           → full
  5. GRADUATED_SL   (elapsed gated, score_info=available=False varsayılır)→ full

Scale-out distance-based: progress = (current_price - entry_price) / (1 - entry_price).
Bu, üretim `src/strategy/exit/scale_out.py` ile aynı semantiği taşır.

Pozisyonun başlangıç state'i (entry_price, direction, shares, size_usdc,
scale_out_tier) caller tarafından sağlanır. Engine state'i ilerletir, partial
exit'ler shares/size'ı küçültür ve scale_out_tier ilerler. Aynı pozisyon birden
fazla scale-out + sonra resolved/stop_loss yaşayabilir.

Direction handling (DECISIONS §6.1):
  - BUY_YES: pozisyon fiyatı = YES price (raw)
  - BUY_NO:  pozisyon fiyatı = (1 - YES price), shares = NO token
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ExitRulesConfig:
    """Replay için exit eşikleri. Script bu değerleri strategy modüllerinden okur.

    Eşiklerin tek doğruluk kaynağı yine `src/strategy/exit/*.py` ve
    `src/config/sport_rules.py` — script wire'lar, engine pure kalır.

    Scale-out distance-based: tier threshold = (current-entry)/(1-entry) hedefi.
    """
    tier1_threshold: float            # scale_out tier1 progress threshold (0.40)
    tier1_sell_pct: float             # scale_out tier1 sell_pct          (0.40)
    tier2_threshold: float            # scale_out tier2 progress threshold (0.70)
    tier2_sell_pct: float             # scale_out tier2 sell_pct          (0.50)
    lost_threshold: float             # resolved.LOST_THRESHOLD           (0.03)
    won_threshold: float              # resolved.WON_THRESHOLD            (0.97)
    near_resolve_threshold: float     # 0.94 (cents/100)
    near_resolve_guard_minutes: int   # 5–10 (sport_rules tennis: 5)
    stop_loss_pct: float              # sport_rules.tennis.stop_loss_pct  (0.30)
    graduated_sl_enabled: bool = False  # replay'de score_info yok → varsayılan kapalı
    match_duration_hours: float = 1.75  # tennis default


@dataclass
class SimulatedExit:
    """Engine tarafından tetiklenen kısmi veya tam exit."""
    timestamp_iso: str
    price: float            # token-native fiyat (entry_price ile aynı taban)
    reason: str             # "resolved" | "near_resolve" | "scale_out" | "stop_loss" | "graduated_sl"
    tier: Optional[int]     # scale_out için 1/2, diğerlerinde None
    sell_pct: float         # 0–1; tam exit'te 1.0, scale_out'ta tier1=0.40 / tier2=0.50
    sell_pct_of_original: float  # OG shares'in yüzdesi (scale_out tier2 = 0.30)
    realized_pnl_usdc: float     # bu kısmi/tam exit'in P&L'si (USDC)
    detail: str = ""


@dataclass
class ReplayResult:
    """Bir pozisyon için replay sonucu."""
    exits: list[SimulatedExit] = field(default_factory=list)
    closed: bool = False              # tam kapanış (resolved/stop_loss/near_resolve) tetiklendi mi
    final_remaining_pct: float = 1.0  # orijinal pozisyonun yüzde kaçı hala açık
    final_size_usdc: float = 0.0      # kalan size
    final_shares: float = 0.0         # kalan shares
    final_scale_out_tier: int = 0     # son tier
    realized_pnl_total: float = 0.0   # tüm exit'lerin toplam P&L'i

    @property
    def fired_any(self) -> bool:
        return len(self.exits) > 0


def _position_price_at(yes_price: float, direction: str) -> float:
    """BUY_YES → YES; BUY_NO → 1-YES. (DECISIONS §6.1: token-native)."""
    if direction == "BUY_NO":
        return 1.0 - yes_price
    return yes_price


def _pnl_pct(current_price: float, entry_price: float) -> float:
    if entry_price <= 0:
        return 0.0
    return (current_price - entry_price) / entry_price


def _distance_progress(current_price: float, entry_price: float) -> float:
    """Distance-based scale-out progress (same formula as production scale_out).

    progress = (current_price - entry_price) / (1.0 - entry_price)
    Returns -inf for entry_price >= 1.0 (defensive, no scale-out fires).
    """
    distance = 1.0 - entry_price
    if distance <= 0.0:
        return float("-inf")
    return (current_price - entry_price) / distance


def _parse_ts(iso: str) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _elapsed_pct(tick_iso: str, match_start_iso: str, duration_hours: float) -> float:
    """Maç başlangıcından bu tick'e kadar elapsed yüzdesi. Pre-match → -1.0."""
    start = _parse_ts(match_start_iso)
    tick = _parse_ts(tick_iso)
    if start is None or tick is None or duration_hours <= 0:
        return -1.0
    elapsed_min = (tick - start).total_seconds() / 60.0
    duration_min = duration_hours * 60.0
    if elapsed_min < 0:
        return -1.0
    return min(elapsed_min / duration_min, 1.0)


def replay_position(
    entry_price: float,
    direction: str,
    size_usdc: float,
    shares: float,
    match_start_iso: str,
    price_history: list[dict],
    rules: ExitRulesConfig,
    initial_scale_out_tier: int = 0,
    initial_partial_exits: list[dict] | None = None,
) -> ReplayResult:
    """Pozisyonu fiyat geçmişine karşı simüle et.

    Args:
        entry_price: Token-native giriş fiyatı (BUY_NO ise 1-yes ile geçirilmiş).
        direction: "BUY_YES" | "BUY_NO".
        size_usdc: Orijinal nominal yatırım.
        shares: Orijinal shares sayısı.
        match_start_iso: Maç başlangıç ISO (graduated_sl ve near_resolve guard).
        price_history: [{"timestamp_iso", "price": yes_price}, ...] — kronolojik.
        rules: Exit eşikleri (script tarafından strategy modüllerinden topuz).
        initial_scale_out_tier: Mevcut state (pozisyon zaten tier1 yaptıysa 1).
        initial_partial_exits: Bilinen partial exit'ler (tekrar saymayalım).

    Returns:
        ReplayResult — exits listesi + final remaining state.
    """
    result = ReplayResult()
    if shares <= 0 or size_usdc <= 0:
        result.final_remaining_pct = 0.0
        return result

    # Başlangıç state — pozisyonu küçültecek mutable copy.
    remaining_shares = shares
    remaining_size = size_usdc
    scale_out_tier = initial_scale_out_tier
    # Önceki partial'ları say (final_remaining_pct doğru olsun).
    prev_partials = initial_partial_exits or []
    remaining_pct = 1.0
    for pe in prev_partials:
        try:
            remaining_pct *= (1.0 - float(pe.get("sell_pct") or 0.0))
        except (TypeError, ValueError):
            continue
    # ↑ Bu pre-existing kısımları DİKKAT: script bunları tekrar saymayacak.
    # remaining_shares/size zaten "post-prev-partials" durumu olarak verilmeli.

    for point in price_history:
        tick_iso = point.get("timestamp_iso", "")
        yes_price = float(point.get("price", 0.0))
        pos_price = _position_price_at(yes_price, direction)
        pnl_pct = _pnl_pct(pos_price, entry_price)
        progress = _distance_progress(pos_price, entry_price)

        # 0. RESOLVED — fiyat settled (≤lost veya ≥won)
        if pos_price <= rules.lost_threshold or pos_price >= rules.won_threshold:
            realized = remaining_shares * pos_price - remaining_size
            outcome = "lost" if pos_price <= rules.lost_threshold else "won"
            sell_pct_orig = remaining_pct
            result.exits.append(SimulatedExit(
                timestamp_iso=tick_iso,
                price=pos_price,
                reason="resolved",
                tier=None,
                sell_pct=1.0,
                sell_pct_of_original=sell_pct_orig,
                realized_pnl_usdc=realized,
                detail=f"{outcome} (price={pos_price:.3f})",
            ))
            result.realized_pnl_total += realized
            result.closed = True
            result.final_remaining_pct = 0.0
            result.final_size_usdc = 0.0
            result.final_shares = 0.0
            result.final_scale_out_tier = scale_out_tier
            return result

        # 1. NEAR_RESOLVE — pre-match guard: maç başlamadıysa veya guard < dakika reddet
        if pos_price >= rules.near_resolve_threshold:
            start = _parse_ts(match_start_iso)
            tick = _parse_ts(tick_iso)
            guard_ok = True
            if start is not None and tick is not None:
                if tick < start:
                    guard_ok = False
                else:
                    minutes_since = (tick - start).total_seconds() / 60.0
                    if minutes_since < rules.near_resolve_guard_minutes:
                        guard_ok = False
            if guard_ok:
                realized = remaining_shares * pos_price - remaining_size
                sell_pct_orig = remaining_pct
                result.exits.append(SimulatedExit(
                    timestamp_iso=tick_iso,
                    price=pos_price,
                    reason="near_resolve",
                    tier=None,
                    sell_pct=1.0,
                    sell_pct_of_original=sell_pct_orig,
                    realized_pnl_usdc=realized,
                    detail=f"eff>={rules.near_resolve_threshold:.2f}",
                ))
                result.realized_pnl_total += realized
                result.closed = True
                result.final_remaining_pct = 0.0
                result.final_size_usdc = 0.0
                result.final_shares = 0.0
                result.final_scale_out_tier = scale_out_tier
                return result

        # 2-3. SCALE_OUT tiers — distance-based partial. Boundary equality:
        # math.isclose absorbs IEEE-754 rounding (same as production scale_out).
        if scale_out_tier == 0 and (
            progress >= rules.tier1_threshold
            or math.isclose(progress, rules.tier1_threshold)
        ):
            sell_pct = rules.tier1_sell_pct
            shares_to_sell = remaining_shares * sell_pct
            basis_returned = remaining_size * sell_pct
            realized = (remaining_shares * pos_price - remaining_size) * sell_pct
            sell_pct_orig = remaining_pct * sell_pct
            remaining_shares -= shares_to_sell
            remaining_size -= basis_returned
            remaining_pct *= (1.0 - sell_pct)
            scale_out_tier = 1
            result.exits.append(SimulatedExit(
                timestamp_iso=tick_iso,
                price=pos_price,
                reason="scale_out",
                tier=1,
                sell_pct=sell_pct,
                sell_pct_of_original=sell_pct_orig,
                realized_pnl_usdc=realized,
                detail=f"tier 1 at progress {progress:.2f}",
            ))
            result.realized_pnl_total += realized
            # Tick'i bitirmeyip aynı tick'te tier2 trigger olmasın — DEVAM (sonraki tick'te tier2'ye bakılır)
            continue

        if scale_out_tier == 1 and (
            progress >= rules.tier2_threshold
            or math.isclose(progress, rules.tier2_threshold)
        ):
            sell_pct = rules.tier2_sell_pct
            shares_to_sell = remaining_shares * sell_pct
            basis_returned = remaining_size * sell_pct
            realized = (remaining_shares * pos_price - remaining_size) * sell_pct
            sell_pct_orig = remaining_pct * sell_pct
            remaining_shares -= shares_to_sell
            remaining_size -= basis_returned
            remaining_pct *= (1.0 - sell_pct)
            scale_out_tier = 2
            result.exits.append(SimulatedExit(
                timestamp_iso=tick_iso,
                price=pos_price,
                reason="scale_out",
                tier=2,
                sell_pct=sell_pct,
                sell_pct_of_original=sell_pct_orig,
                realized_pnl_usdc=realized,
                detail=f"tier 2 at progress {progress:.2f}",
            ))
            result.realized_pnl_total += realized
            continue

        # 4. STOP_LOSS — flat SL (sport-spesifik)
        if pnl_pct <= -rules.stop_loss_pct:
            realized = remaining_shares * pos_price - remaining_size
            sell_pct_orig = remaining_pct
            result.exits.append(SimulatedExit(
                timestamp_iso=tick_iso,
                price=pos_price,
                reason="stop_loss",
                tier=None,
                sell_pct=1.0,
                sell_pct_of_original=sell_pct_orig,
                realized_pnl_usdc=realized,
                detail=f"pnl_pct={pnl_pct:.2%} <= -{rules.stop_loss_pct:.0%}",
            ))
            result.realized_pnl_total += realized
            result.closed = True
            result.final_remaining_pct = 0.0
            result.final_size_usdc = 0.0
            result.final_shares = 0.0
            result.final_scale_out_tier = scale_out_tier
            return result

        # 5. GRADUATED_SL — opsiyonel (score_info yok varsayımı: replay genelde kapalı tutar)
        # NOT: graduated SL elapsed-aware + sport-specific. Replay sırasında score yoktur,
        # bu yüzden engine'in varsayılanı disabled. Caller wire'larsa basit elapsed gate
        # eklenebilir — şimdilik kapsam dışı.

    # Tüm tick'ler bitti, pozisyon hala açık.
    result.final_remaining_pct = remaining_pct
    result.final_size_usdc = remaining_size
    result.final_shares = remaining_shares
    result.final_scale_out_tier = scale_out_tier
    return result
