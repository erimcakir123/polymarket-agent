"""Tennis market dispatch — model anchor öncelik, moneyline fallback.

Karar matrisi:
  sport != tennis              → bookmaker fallback
  sport == tennis, ratings yok → bookmaker fallback (model çalışmaz)
  sport == tennis, player yok  → bookmaker fallback
  sport == tennis, model OK    → model döner (A confidence)
  sport == tennis, model fail VE moneyline → bookmaker fallback
  sport == tennis, model fail VE alt market → fail (bot trade etmez)

Alt market fallback YASAK — eski cascade bug (h2h fiyatını yapıştırma) bu modülün
çözdüğü asıl sorundur.

Tahminler (Polymarket veri yetersizliği nedeniyle question stringinden):
- Surface: Hard default; Clay/Grass keyword'leri turnuva ismi geçerse
- Best_of: 3 default; Grand Slam keyword'ü ile 5
- line/handicap: market_type'a göre question regex (set/games/handicap)
"""
from __future__ import annotations

import re
from typing import Callable

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.pricing.tennis.calibration import CalibrationCurve
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.models.market import MarketData
from src.strategy.enrichment.question_parser import extract_teams
from src.strategy.enrichment.tennis_anchor_enricher import enrich_tennis_from_model

_DEFAULT_SURFACE = "Hard"
_DEFAULT_BEST_OF = 3
_GRAND_SLAM_KEYWORDS = (
    "grand slam", "us open", "australian open", "wimbledon",
    "french open", "roland garros", "rolandgarros",
)
# Surface inference — turnuva keyword → kort tipi. Sackmann naming convention.
_CLAY_KEYWORDS = (
    "french open", "roland garros", "rolandgarros", "monte carlo",
    "madrid open", "rome", "italian open", "barcelona", "hamburg",
    "estoril", "houston",
)
_GRASS_KEYWORDS = (
    "wimbledon", "queen's", "queens club", "halle", "eastbourne",
    "stuttgart", "mallorca", "newport",
)
_MONEYLINE_TYPES = ("moneyline", "h2h", "")
# Glicko-2 phi (rating deviation) yetki eşiği. Default phi=350 (hiç maç),
# 30+ maç sonrası phi ~50-80'e iner. 100 eşik = ~25+ maç = güvenilir.
# 2026-06-01 kullanıcı kararı: yetkimiz olmayan oyuncuya bahis YOK.
_MAX_PHI_FOR_TRADE = 100.0

# 2026-06-01 BUG FIX: phi filtresi tek başına yetersiz. ITF'de düzenli
# oynayan oyuncuların maç sayısı 30+, phi düşük → "güvenilir" sayıldı
# ama lig kalitesi düşük (Sackmann ITF/Challenger için %50-60 doğruluk).
# Polymarket slug prefix ile düşük-tier turnuvaları ELE.
_LOW_TIER_SLUG_PREFIXES = ("itf-", "challenger-", "futures-")
# Question metninde geçerse low-tier — bazen Polymarket slug "atp-" / "wta-"
# yazıp question'da gerçek tier'ı belirtiyor.
_LOW_TIER_QUESTION_KEYWORDS = (
    "ITF", "Futures", "Challenger", "M15", "M25", "W15", "W25",
)


def _is_low_tier_tennis(slug: str, question: str) -> bool:
    """ITF/Challenger/Futures market'i mi? Yetki dışı."""
    s = (slug or "").lower()
    if any(s.startswith(p) for p in _LOW_TIER_SLUG_PREFIXES):
        return True
    q = question or ""
    return any(k in q for k in _LOW_TIER_QUESTION_KEYWORDS)


def _infer_best_of(question: str) -> int:
    q_low = (question or "").lower()
    if any(k in q_low for k in _GRAND_SLAM_KEYWORDS):
        return 5
    return _DEFAULT_BEST_OF


def _resolve_player_name(
    name: str,
    ratings: dict[str, PlayerSnapshot],
) -> str | None:
    """Polymarket name → Sackmann full name eşleme.

    Sıra: exact → case-insensitive exact → last-name substring (tek eşleşme).
    Ambiguous (2+ aynı soyad) → None (güvenli, atla).
    """
    if name in ratings:
        return name
    name_low = name.lower().strip()
    ci_match = [k for k in ratings if k.lower() == name_low]
    if ci_match:
        return ci_match[0]
    parts_match = [k for k in ratings if name_low in k.lower().split()]
    if len(parts_match) == 1:
        return parts_match[0]
    return None


def _infer_market_type(market: MarketData) -> str:
    """Polymarket bazen sports_market_type'ı boş bırakır; slug'tan çıkar.

    Boş market_type cascade bug riski — moneyline sanıp h2h modeli ile
    yanlış market fiyatlanır. Slug keyword'leri ile doğru pricer'a yönlendir.
    """
    declared = (market.sports_market_type or "").strip().lower()
    if declared:
        return declared
    slug = (market.slug or "").lower()
    if "set-handicap" in slug:
        return "tennis_set_handicap"
    if "first-set" in slug and any(k in slug for k in ("over", "under", "total")):
        return "tennis_first_set_totals"
    if "first-set" in slug:
        return "tennis_first_set_winner"
    if "set-total" in slug or "number-of-sets" in slug or "total-sets" in slug:
        return "tennis_set_totals"
    if "match-total" in slug or "match-o-u" in slug or "over" in slug or "under" in slug:
        return "tennis_match_totals"
    return ""


def _infer_surface(question: str) -> str:
    q_low = (question or "").lower()
    if any(k in q_low for k in _CLAY_KEYWORDS):
        return "Clay"
    if any(k in q_low for k in _GRASS_KEYWORDS):
        return "Grass"
    return _DEFAULT_SURFACE


_HANDICAP_RE = re.compile(r"[+-]\d+\.?\d*", re.IGNORECASE)
_OVER_LINE_RE = re.compile(r"(?:over|under|total|totals)\s+(\d+\.?\d*)", re.IGNORECASE)


def _extract_market_params(
    question: str,
    market_type: str,
) -> tuple[float | None, float | None]:
    """Question stringinden line + handicap çıkar (market_type'a göre).

    Returns: (line, handicap). Bulamazsa None.
    """
    q = question or ""
    mt = market_type.lower()
    if mt == "tennis_set_handicap":
        m = _HANDICAP_RE.search(q)
        if m:
            try:
                return None, float(m.group(0))
            except ValueError:
                return None, None
        return None, None
    if mt in ("tennis_match_totals", "tennis_first_set_totals", "tennis_set_totals"):
        m = _OVER_LINE_RE.search(q)
        if m:
            try:
                return float(m.group(1)), None
            except ValueError:
                return None, None
        return None, None
    return None, None


def enrich_with_tennis_dispatch(
    market: MarketData,
    bookmaker_enricher: Callable[[MarketData], EnrichResult],
    ratings: dict[str, PlayerSnapshot],
    calibration_curves: dict[str, CalibrationCurve] | None = None,
    glicko_weight: float = 0.6,
) -> EnrichResult:
    """Tennis ise model, değilse veya yetersiz veri ise bookmaker fallback.

    Alt market'lerde fallback YASAK — cascade bug (h2h fiyatını her marketa
    yapıştırma) tam burada kapanır.
    """
    sport = (market.sport_tag or "").lower()
    if sport != "tennis":
        return bookmaker_enricher(market)

    # YETKİ FİLTRESİ (2026-06-01 bug fix): ITF/Challenger/Futures → SUS.
    # phi tek başına yetersizdi (ITF düzenli oyuncuların maç sayısı yüksek
    # ama lig kalitesi düşük). Slug + question keyword bazlı filtre.
    if _is_low_tier_tennis(market.slug or "", market.question or ""):
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_PLAYER_NOT_IN_RATINGS,
        )

    market_type = _infer_market_type(market)
    is_moneyline = market_type in _MONEYLINE_TYPES

    if not ratings:
        if is_moneyline:
            return bookmaker_enricher(market)
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.MODEL_DATA_MISSING)

    player_a, player_b = extract_teams(market.question)
    if not player_a or not player_b:
        if is_moneyline:
            return bookmaker_enricher(market)
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.TEAM_EXTRACT_FAILED)

    # Polymarket genelde soyadı gönderir ("Hurkacz"), Sackmann full name
    # ("Hubert Hurkacz") saklar. Soyadı substring + ambiguity safety ile çöz.
    resolved_a = _resolve_player_name(player_a, ratings)
    resolved_b = _resolve_player_name(player_b, ratings)
    if resolved_a is None or resolved_b is None:
        if is_moneyline:
            return bookmaker_enricher(market)
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_PLAYER_NOT_IN_RATINGS,
        )
    player_a, player_b = resolved_a, resolved_b

    # Yetki filtresi (2026-06-01 kullanıcı kararı):
    # Glicko RD (phi) çok yüksekse oyuncu yeterince oynamamış → rating güvenilmez
    # (Pieri-Bosio gibi ITF gençleri tarihçesi 5-15 maç → phi 150+). Pratik eşik:
    # phi < 100 = güvenilir tanınıyor (~30+ maç). Aksi halde model konuşmamalı.
    snap_a = ratings[player_a]
    snap_b = ratings[player_b]
    if snap_a.rating.phi >= _MAX_PHI_FOR_TRADE or snap_b.rating.phi >= _MAX_PHI_FOR_TRADE:
        if is_moneyline:
            return bookmaker_enricher(market)
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_PLAYER_NOT_IN_RATINGS,
        )

    best_of = _infer_best_of(market.question)
    surface = _infer_surface(market.question)
    line, handicap = _extract_market_params(market.question, market_type)
    model_result = enrich_tennis_from_model(
        player_a=player_a,
        player_b=player_b,
        market_type=market_type,
        surface=surface,
        best_of=best_of,
        ratings=ratings,
        calibration_curves=calibration_curves,
        line=line,
        handicap=handicap,
        glicko_weight=glicko_weight,
    )
    if model_result.probability is not None:
        return model_result

    # Model fail — moneyline için bookmaker fallback OK; alt market için fail.
    if is_moneyline:
        return bookmaker_enricher(market)
    return model_result
