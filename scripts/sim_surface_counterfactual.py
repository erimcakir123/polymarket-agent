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

from collections import defaultdict
from dataclasses import dataclass

from src.domain.pricing.tennis.glicko import Rating, update_rating
from src.domain.pricing.tennis.match_record import MatchRecord
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats, aggregate_serve_stats

_SURFACES = ("Hard", "Clay", "Grass")

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


def _fit_glicko(matches: list[MatchRecord]) -> dict[str, Rating]:
    """Kronolojik Glicko fit (build_tennis_ratings.build_ratings ile aynı döngü)."""
    ratings: dict[str, Rating] = defaultdict(Rating)
    for m in matches:
        w, loser_r = ratings[m.winner_name], ratings[m.loser_name]
        ratings[m.winner_name] = update_rating(w, [loser_r], [1.0])
        ratings[m.loser_name] = update_rating(loser_r, [w], [0.0])
    return dict(ratings)


def build_cutoff_snapshots(
    matches: list[MatchRecord],
    cutoff_yyyymmdd: str,
    surface_phi_fallback: float,
) -> tuple[dict[str, PlayerSnapshot], dict[str, dict[str, PlayerSnapshot]]]:
    """Cutoff öncesi maçlarla flat + yüzeye-özgü PlayerSnapshot'lar (lookahead yok).

    Yüzeye-özgü reyting phi >= surface_phi_fallback ise overall'a düşer
    (tennis_surface_ratings_store.load_surface_ratings davranışının aynısı).
    """
    kept = sorted(
        (m for m in matches if m.tourney_date and m.tourney_date < cutoff_yyyymmdd),
        key=lambda m: m.tourney_date,
    )
    serve_by_player: dict[str, dict[str, PlayerServeStats]] = defaultdict(dict)
    for (player, surface), stats in aggregate_serve_stats(kept).items():
        serve_by_player[player][surface] = stats

    overall = _fit_glicko(kept)
    flat = {
        name: PlayerSnapshot(rating=r, serve_by_surface=dict(serve_by_player.get(name, {})))
        for name, r in overall.items()
    }
    by_surface: dict[str, dict[str, PlayerSnapshot]] = {}
    for surf in _SURFACES:
        fitted = _fit_glicko([m for m in kept if m.surface == surf])
        by_surface[surf] = {
            name: PlayerSnapshot(
                rating=overall[name] if r.phi >= surface_phi_fallback else r,
                serve_by_surface=dict(serve_by_player.get(name, {})),
            )
            for name, r in fitted.items()
        }
    return flat, by_surface
