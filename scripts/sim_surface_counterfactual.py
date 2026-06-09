"""SPEC-SIM2: Önceki session'ı bugünkü kurallarla yeniden oynatma (zemin counterfactual).

Reboot ile arşivlenen 2026-06-06→09 session'ının 79 tenis trade'ini bugünkü karar
zincirinden geçirir: yeni zemin tespiti → model yeniden fiyatlama (cutoff reytingler,
lookahead yok) → bugünkü giriş kapısı → gerçek fiyat geçmişiyle çıkış beyni replay.

GÜVENLİK (DEMİR): Hiçbir bot-state dosyasına YAZMAZ. Odds API KULLANILMAZ.
Ağ erişimi yalnızca Polymarket prices-history + Wikipedia GET (ücretsiz).
SurfaceResolver save_fn=None ile kurulur → override dosyasına dahi yazmaz.

Çalıştırma:  python scripts/sim_surface_counterfactual.py
"""
from __future__ import annotations

from dataclasses import dataclass

# Bugünkü kurallarda Match O/U tamamen kaldırıldı (SPEC-Z28).
_REMOVED_MARKET_TYPES = ("tennis_match_totals",)
# Bimodal tipler (config risk.bimodal_bet_usdc + bimodal_min_entry_price kapsamı).
_BIMODAL_TYPES = ("tennis_set_handicap", "tennis_set_totals")
_MAX_POSITIONS_PER_EVENT = 3  # ARCH_GUARD Kural 8 (config risk.max_positions_per_event)


@dataclass(frozen=True)
class GateDecision:
    action: str          # "SKIP" | "SAME" | "FLIP"
    reason: str          # skip sebebi; girildiyse ""
    direction: str       # BUY_YES | BUY_NO | ""
    eff_entry: float     # girilen tarafın fiyatı (BUY_NO → 1-yes_price)
    size_usdc: float


def decide_gate(
    *,
    market_type: str,
    new_prob: float | None,
    yes_price: float,
    confidence: str,
    has_sharp: bool,
    actual_direction: str,
    min_edge: float,
    bimodal_floor: float,
    ml_size_a: float,
    bimodal_size_a: float,
    event_key: str,
    event_positions: dict[str, set[str]],
) -> GateDecision:
    """Bugünkü giriş kapısı, saf fonksiyon (SPEC-SIM2 kural 5). Mutasyon yapmaz."""
    if market_type in _REMOVED_MARKET_TYPES:
        return GateDecision("SKIP", "ou_removed", "", 0.0, 0.0)
    if new_prob is None:
        return GateDecision("SKIP", "surface_or_model", "", 0.0, 0.0)
    if confidence != "A" or not has_sharp:
        return GateDecision("SKIP", "confidence", "", 0.0, 0.0)

    edge_yes = new_prob - yes_price
    edge_no = yes_price - new_prob
    if edge_yes < min_edge and edge_no < min_edge:
        return GateDecision("SKIP", "edge", "", 0.0, 0.0)
    if edge_yes >= edge_no:
        direction, eff_entry = "BUY_YES", yes_price
    else:
        direction, eff_entry = "BUY_NO", round(1.0 - yes_price, 4)

    is_bimodal = market_type in _BIMODAL_TYPES
    if is_bimodal and eff_entry < bimodal_floor:
        return GateDecision("SKIP", "bimodal_floor", "", 0.0, 0.0)

    taken = event_positions.get(event_key, set())
    if market_type in taken or len(taken) >= _MAX_POSITIONS_PER_EVENT:
        return GateDecision("SKIP", "event_guard", "", 0.0, 0.0)

    size = bimodal_size_a if is_bimodal else ml_size_a
    action = "SAME" if direction == actual_direction else "FLIP"
    return GateDecision(action, "", direction, eff_entry, size)
