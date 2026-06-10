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

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.pricing.tennis.glicko import Rating, fit_ratings
from src.domain.pricing.tennis.match_record import MatchRecord
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats, aggregate_serve_stats
from src.models.market import MarketData
from src.strategy.enrichment.tennis_dispatch import _extract_location, _infer_market_type

logger = logging.getLogger(__name__)

_SURFACES = ("Hard", "Clay", "Grass")
# Slug tabanı: atp|wta - oyuncu token'ları - YYYY-MM-DD (sonrası market eki).
_SLUG_MATCH_RE = re.compile(r"^(?:atp|wta)-(.+?)-(\d{4}-\d{2}-\d{2})")

# Reboot (2026-06-09 20:32) arşivi — önceki session'ın tamamı. Salt-okunur.
_ARCHIVE_EVENTS = Path("logs/audit/trade_events.archive.20260609_203215.jsonl")
_ARCHIVE_EXECS = Path("logs/audit/paper_executions.archive.20260609_203215.jsonl")
_CACHE_DIR = Path("data/sackmann_cache")
_SURFACE_MAP_PATH = Path("data/tennis_surface_map.json")
_OVERRIDES_PATH = Path("data/tennis_surface_overrides.json")
_CALIBRATION_PATH = Path("data/tennis_calibration.json")
# Session 2026-06-06'da başlar; bu tarihten itibaren oynanan maçlar fit'e GİRMEZ
# (lookahead yasağı — model maç sonucunu önceden 'bilemez').
_CUTOFF_DATE = "20260606"
_EXEC_WINDOW_SEC = 180
_PROB_CLAMP = (0.01, 0.99)  # Position.anchor_probability validator sınırı

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
    """Kronolojik Glicko fit — domain `fit_ratings`'e ince sarmalayıcı (DRY)."""
    return fit_ratings([(m.winner_name, m.loser_name) for m in matches])


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
        # Canlı parite (load_surface_ratings): TÜM oyuncular her yüzey listesinde;
        # yüzey-reytingi yok/phi yüksek → overall reytinge düşer.
        by_surface[surf] = {}
        for name, overall_r in overall.items():
            surf_r = fitted.get(name)
            chosen = surf_r if (surf_r is not None and surf_r.phi < surface_phi_fallback) else overall_r
            by_surface[surf][name] = PlayerSnapshot(
                rating=chosen, serve_by_surface=dict(serve_by_player.get(name, {})),
            )
    return flat, by_surface


def synth_event_links(entries: list[dict]) -> tuple[dict[int, str], dict[str, str]]:
    """idx→sentetik event_id + event_id→turnuva adı (SPEC-SIM2 görev 3).

    Botun cycle'daki karşılığı: moneyline marketlerden {event_id: turnuva} kurup
    resolver.set_event_tournaments çağırması. Sim aynı haritayı arşivden sentezler.
    Maç anahtarı sluglardan: oyuncu token'ları (sıra bağımsız) + tarih.
    Turnuva: gruptaki lokasyon-önekli sorudan (_extract_location — market-tipi
    öneklerini zaten reddeder, yani sadece moneyline'dan gelir).
    """
    idx_to_event: dict[int, str] = {}
    event_tournaments: dict[str, str] = {}
    for idx, e in enumerate(entries):
        m = _SLUG_MATCH_RE.match((e.get("slug") or "").lower())
        if not m:
            continue
        players, date = m.group(1), m.group(2)
        event_id = "evt-" + "-".join(sorted(players.split("-"))) + "-" + date
        idx_to_event[idx] = event_id
        loc = _extract_location(e.get("question") or "")
        if loc and event_id not in event_tournaments:
            event_tournaments[event_id] = loc
    return idx_to_event, event_tournaments


def invert_series(series: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Sahip olunan taraf YES değilse fiyat serisi karşı tarafa çevrilir (1−p yaklaşımı)."""
    return [(t, round(1.0 - p, 4)) for t, p in series]


# ── Arşiv yükleme (I/O — script seviyesi, salt-okunur) ──

def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # bozuk satır arşivde olabilir; sayım raporda görünür
    return rows


def load_tennis_entries(path: Path) -> list[dict]:
    """Arşivden tenis entry'leri, kronolojik (SPEC-SIM2 görev 4)."""
    entries = [
        ev for ev in _read_jsonl(path)
        if ev.get("kind") == "entry" and ev.get("sport_tag") == "tennis"
    ]
    entries.sort(key=lambda e: e.get("entry_timestamp") or "")
    return entries


def link_token_ids(
    entries: list[dict], execs_path: Path, window_sec: int,
) -> dict[int, str | None]:
    """Her entry'ye token_id: ±window içindeki, boyutu eşit BUY execution'dan.

    Eşleşmeyen → None (fiyat geçmişi çekilemez; rapor 'atlandı' listesine koyar).
    """
    buys = [
        (datetime.fromisoformat(r["ts"]), float(r.get("target_size_usdc") or 0.0),
         r.get("token_id"))
        for r in _read_jsonl(execs_path)
        if (r.get("side") or "").upper() == "BUY" and r.get("ts") and r.get("token_id")
    ]
    out: dict[int, str | None] = {}
    for idx, e in enumerate(entries):
        ts_raw = e.get("entry_timestamp")
        if not ts_raw:
            out[idx] = None
            continue
        entry_dt = datetime.fromisoformat(ts_raw)
        best: tuple[float, str] | None = None
        for ts, size, token in buys:
            if abs(float(e.get("size_usdc") or 0.0) - size) > 0.01:
                continue
            dt = abs((ts - entry_dt).total_seconds())
            if dt <= window_sec and (best is None or dt < best[0]):
                best = (dt, token)
        out[idx] = best[1] if best else None
    return out


# ── Orkestrasyon (I/O — script seviyesi) ──

def _load_sackmann_matches(cache_dir: Path) -> list[MatchRecord]:
    from src.infrastructure.data.sackmann_csv_loader import load_matches_from_path
    matches: list[MatchRecord] = []
    for csv in sorted(cache_dir.glob("*.csv")):
        try:
            matches.extend(load_matches_from_path(csv))
        except OSError as exc:
            logger.warning("CSV okunamadı: %s (%s)", csv, exc)
    return matches


def _build_resolver(cfg, event_tournaments: dict[str, str]):
    """Bugünkü zemin çözücü — factory.py ile birebir, AMA save_fn=None (salt-okunur)."""
    from src.infrastructure.apis.wikipedia_surface_client import WikipediaSurfaceClient
    from src.infrastructure.data.tennis_surface_map_store import load_surface_map
    from src.infrastructure.data.tennis_surface_override_store import load_overrides
    from src.strategy.enrichment.surface_resolver import SurfaceResolver
    resolver = SurfaceResolver(
        load_surface_map(_SURFACE_MAP_PATH),
        wiki=WikipediaSurfaceClient(),
        overrides=load_overrides(_OVERRIDES_PATH),
        save_fn=None,   # DEMİR: override dosyasına yazmaz
        reload_fn=None,
        ttl_days=cfg.tennis.surface_unknown_recheck_days,
    )
    resolver.set_event_tournaments(event_tournaments)
    return resolver


def _bm_unavailable(_market: MarketData) -> EnrichResult:
    """source=model trade'de o gün BM verisi yoktu → model yoluna zorla (SPEC kural 3)."""
    return EnrichResult(probability=None, fail_reason=EnrichFailReason.EMPTY_BOOKMAKERS)


def evaluate_entries(entries: list[dict], cfg, resolver, enrich_model, calib) -> list[dict]:
    """Her entry için yeni tahmin + kapı kararı (replay'siz). Kronolojik event-guard."""
    idx_to_event, _ = synth_event_links(entries)
    event_positions: dict[str, set[str]] = defaultdict(set)
    out: list[dict] = []
    for idx, e in enumerate(entries):
        yes_price = (
            float(e["entry_price"]) if e.get("direction") == "BUY_YES"
            else round(1.0 - float(e["entry_price"]), 4)
        )
        market = MarketData(
            condition_id=e.get("condition_id", ""), question=e.get("question", ""),
            slug=e.get("slug", ""), yes_token_id="", no_token_id="",
            yes_price=yes_price, no_price=round(1.0 - yes_price, 4),
            liquidity=0.0, volume_24h=0.0, end_date_iso="",
            event_id=idx_to_event.get(idx), sport_tag="tennis",
        )
        mtype = _infer_market_type(market) or "moneyline"
        # KRİTİK: canlıda Polymarket sports_market_type gönderir; sim'de boş kalırsa
        # model "tip bilinmiyor" deyip fiyatlamaz (2026-06-10 koşusunda 30 sahte skip).
        market = market.model_copy(update={"sports_market_type": mtype})
        surface = resolver.resolve(market)
        if e.get("source") == "bookmaker":
            # BM-first ML kuralları o gün = bugün → giriş kararı DEĞİŞMEZ (fill
            # fiyatından edge'i yeniden hesaplamak sahte kayma üretir). Ölçülen
            # tek fark bugünkü ÇIKIŞ beyni (replay).
            decision = GateDecision(
                "SAME", "", e.get("direction", ""),
                float(e["entry_price"]), cfg.risk.fixed_bet_usdc["A"],
            )
            event_positions[idx_to_event.get(idx, f"solo-{idx}")].add(mtype)
            out.append({
                "entry": e, "market_type": mtype, "yes_price": yes_price,
                "new_prob": e.get("bookmaker_prob") or e.get("anchor_probability"),
                "surface": "(bahisçi)", "decision": decision,
            })
            continue
        # Model yolu (source=model: o gün BM verisi yoktu, zemin etkisi burada).
        res = enrich_model(
            market, _bm_unavailable, {},  # ratings param dispatch'te surface'a göre seçilir
            calibration_curves=calib,
            glicko_weight=cfg.risk.tennis_h2h_glicko_weight,
            max_phi_for_trade=cfg.tennis.max_phi_for_trade,
            low_tier_slug_prefixes=tuple(cfg.tennis.low_tier_slug_prefixes),
            low_tier_question_keywords=tuple(cfg.tennis.low_tier_question_keywords),
            surface_resolver=resolver,
        )
        bp = res.probability  # BookmakerProbability | None — model kendi confidence üretir
        new_prob = bp.probability if bp is not None else None
        conf = bp.confidence if bp is not None else (e.get("confidence") or "")
        sharp = bp.has_sharp if bp is not None else bool(e.get("has_sharp"))
        surface_lbl = surface or "?"
        # Skip sebebi ayrıştırması (rapor için): zemin mi yok, model mi emin değil?
        if new_prob is None:
            if surface is None:
                fail_lbl = "zemin_yok"
            elif res.fail_reason is not None:
                fail_lbl = res.fail_reason.value
            else:
                fail_lbl = "model_fiyatlamadı"
        else:
            fail_lbl = ""
        decision = decide_gate(
            market_type=mtype, new_prob=new_prob, yes_price=yes_price,
            confidence=conf, has_sharp=sharp,
            actual_direction=e.get("direction", ""),
            min_edge=cfg.edge.min_edge,
            bimodal_floor=cfg.risk.bimodal_min_entry_price,
            ml_size_a=cfg.risk.fixed_bet_usdc["A"],
            bimodal_size_a=cfg.risk.bimodal_bet_usdc["A"],
            event_key=idx_to_event.get(idx, f"solo-{idx}"),
            event_positions=event_positions,
        )
        if decision.action != "SKIP":
            event_positions[idx_to_event.get(idx, f"solo-{idx}")].add(mtype)
        out.append({
            "entry": e, "market_type": mtype, "yes_price": yes_price,
            "new_prob": new_prob, "surface": surface_lbl, "decision": decision,
            "fail": fail_lbl,
        })
    return out
