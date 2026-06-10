"""Tennis market dispatch — bookmaker-first (ML), model fallback; alt market sadece model.

Karar matrisi:
  sport != tennis              → bookmaker fallback
  sport == tennis, ratings yok → bookmaker fallback (model çalışmaz)
  sport == tennis, player yok  → bookmaker fallback
  sport == tennis, model OK    → model döner (A confidence)
  sport == tennis, model fail VE moneyline → bookmaker fallback
  sport == tennis, model fail VE alt market → fail (bot trade etmez)

Alt market fallback YASAK — eski cascade bug (h2h fiyatını yapıştırma) bu modülün
çözdüğü asıl sorundur.

Surface (zemin): enjekte edilen SurfaceResolver'dan gelir (Sackmann harita →
Wikipedia → event-link). Çözülemezse default YOK — market atlanır + warning
loglanır (yanlış zemin riskini önlemek için). Diğer çıkarımlar question'dan:
- Best_of: 3 default; Grand Slam keyword'ü ile 5
- line/handicap: market_type'a göre slug + question regex (set/games/handicap)
"""
from __future__ import annotations

import logging
import re
from typing import Callable

logger = logging.getLogger(__name__)

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.pricing.tennis.surface_map import core_name as _core_name  # DRY
from src.domain.pricing.tennis.calibration import CalibrationCurve
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.models.market import MarketData
from src.strategy.enrichment.question_parser import extract_teams
from src.strategy.enrichment.tennis_anchor_enricher import enrich_tennis_from_model

_DEFAULT_BEST_OF = 3
_GRAND_SLAM_KEYWORDS = (
    "grand slam", "us open", "australian open", "wimbledon",
    "french open", "roland garros", "rolandgarros",
)
_MONEYLINE_TYPES = ("moneyline", "h2h", "")
_MIN_SUBSET_TOKEN_LEN = 4  # token-subset eşleşmede en az bu uzunlukta paylaşılan kelime (kısa şehir-token yanlış eşleşmesini önler)
# Default'lar config.yaml > tennis altında override edilebilir. Module-level
# sabitler sadece config geçirilmediği durumlarda (test, legacy) fallback.
# Gerçek değerler factory.py'de config'den geçirilir.
_DEFAULT_MAX_PHI_FOR_TRADE = 100.0
_DEFAULT_LOW_TIER_SLUG_PREFIXES: tuple[str, ...] = ("itf-", "challenger-", "futures-")
_DEFAULT_LOW_TIER_QUESTION_KEYWORDS: tuple[str, ...] = (
    "ITF", "Futures", "Challenger", "M15", "M25", "W15", "W25",
)


def _is_low_tier_tennis(
    slug: str,
    question: str,
    slug_prefixes: tuple[str, ...] = _DEFAULT_LOW_TIER_SLUG_PREFIXES,
    question_keywords: tuple[str, ...] = _DEFAULT_LOW_TIER_QUESTION_KEYWORDS,
) -> bool:
    """ITF/Challenger/Futures market'i mi? Yetki dışı.

    Prefix/keyword listeleri config'den geçirilir; default'lar geri uyumluluk için.
    """
    s = (slug or "").lower()
    if any(s.startswith(p) for p in slug_prefixes):
        return True
    q = question or ""
    return any(k in q for k in question_keywords)


def _infer_best_of(question: str) -> int:
    q_low = (question or "").lower()
    if any(k in q_low for k in _GRAND_SLAM_KEYWORDS):
        return 5
    return _DEFAULT_BEST_OF


def _normalize_player_name(name: str) -> str:
    """Tire/boşluk yazım farkını eşitle: 'Jan-Lennard' ≡ 'Jan Lennard'."""
    return name.replace("-", " ").lower().strip()


def _resolve_player_name(
    name: str,
    ratings: dict[str, PlayerSnapshot],
) -> str | None:
    """Polymarket name → Sackmann full name eşleme.

    Sıra: exact → normalize (case + tire) exact → last-name token (tek eşleşme)
    → token-alt-kümesi (kısa ad tam adın içinde, tek aday — 'Gabriela Ruse' →
    'Elena Gabriela Ruse', 2026-06-10 vakası).
    Ambiguous (2+ aday) → None (güvenli, atla).
    """
    if name in ratings:
        return name
    name_low = _normalize_player_name(name)
    ci_match = [k for k in ratings if _normalize_player_name(k) == name_low]
    if ci_match:
        return ci_match[0]
    parts_match = [k for k in ratings if name_low in _normalize_player_name(k).split()]
    if len(parts_match) == 1:
        return parts_match[0]
    name_tokens = set(name_low.split())
    if len(name_tokens) >= 2:
        subset_match = [
            k for k in ratings
            if name_tokens <= set(_normalize_player_name(k).split())
        ]
        if len(subset_match) == 1:
            return subset_match[0]
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
    if "first-set" in slug:
        return "tennis_first_set_winner"
    if "set-total" in slug or "number-of-sets" in slug or "total-sets" in slug:
        return "tennis_set_totals"
    if "match-total" in slug or "match-o-u" in slug or "over" in slug or "under" in slug:
        return "tennis_match_totals"
    return ""


# "winner"/"first set": "Set 1/2 Winner", "Match/Game Winner" market-tipi öneklerini
# reddeder (hiçbir gerçek tenis turnuvası adı "winner" içermez) — aksi halde
# turnuva sanılıp zemin çözülemez, sahte SURFACE_UNKNOWN alarmı + skip.
_NON_LOCATION_KEYWORDS = (
    "handicap", "total", "o/u", "over/under", "spread", "winner", "first set",
)


def _extract_location(question: str) -> str | None:
    """Başlıkta ilk ':' öncesi turnuva/şehir. 'X vs Y' veya market-tipi önekler → None."""
    if ":" not in (question or ""):
        return None
    loc = question.split(":", 1)[0].strip()
    low = loc.lower()
    if not loc or " vs" in low or any(k in low for k in _NON_LOCATION_KEYWORDS):
        return None
    return loc


def _match_surface(name: str, surface_map: dict[str, str]) -> str | None:
    """Turnuva ADINDAN zemin (çekirdek-şehir + token-subset, en uzun). PLAN-Z29 mantığı."""
    key = _core_name(name)
    if not key:
        return None
    if key in surface_map:
        return surface_map[key]
    kw = set(key.split())
    best_name = None
    best_surf = None
    for mname, surf in surface_map.items():
        cw = set(mname.split())
        if not cw or not (cw <= kw or kw <= cw):
            continue
        shared = cw & kw
        if not shared or max(len(t) for t in shared) < _MIN_SUBSET_TOKEN_LEN:
            continue
        if best_name is None or len(mname) > len(best_name):
            best_name, best_surf = mname, surf
    return best_surf


_HANDICAP_RE = re.compile(r"[+-]\d+\.?\d*", re.IGNORECASE)
# Question regex: "Over 22.5", "Total 22.5", "O/U 22.5" (Polymarket convention).
_OVER_LINE_RE = re.compile(
    r"(?:over|under|total|totals|o/u)\s+(\d+\.?\d*)", re.IGNORECASE,
)
# Slug regex (primary): "match-total-22pt5" → 22.5; "set-totals-4pt5" → 4.5;
# Polymarket "pt" decimal convention. 2026-06-02 fix — question'dan parse 1 Jun'da
# bozulmuştu çünkü Polymarket format "Match O/U 22.5" idi, regex "over/under"
# arıyordu → None → match-total/set-totals tüm trade'leri öldü (audit kanıtı).
_SLUG_TOTAL_RE = re.compile(
    r"-(?:match-total|set-totals?|first-set-total)-(\d+)(?:pt(\d+))?", re.IGNORECASE,
)
# Slug handicap: "set-handicap-away-1pt5" → 1.5; "set-handicap-home-2pt5" → 2.5
_SLUG_HANDICAP_RE = re.compile(
    r"-set-handicap-(?:away|home)-(\d+)(?:pt(\d+))?", re.IGNORECASE,
)


def _slug_decimal(int_part: str, frac_part: str | None) -> float | None:
    """Polymarket 'pt' decimal parse: ('22', '5') → 22.5."""
    try:
        return float(int_part) + (float(f"0.{frac_part}") if frac_part else 0.0)
    except ValueError:
        return None


def _extract_market_params(
    question: str,
    market_type: str,
    slug: str = "",
) -> tuple[float | None, float | None]:
    """Slug + question'dan line + handicap çıkar (market_type'a göre).

    Returns: (line, handicap). Bulamazsa None.

    Öncelik: slug regex (Polymarket 'pt' decimal convention, daha güvenilir) →
    question regex fallback. Slug yoksa veya pattern eşleşmiyorsa question'a düş.
    """
    q = question or ""
    s = slug or ""
    mt = market_type.lower()
    if mt == "tennis_set_handicap":
        # Önce slug: "-set-handicap-away-1pt5" → 1.5
        sm = _SLUG_HANDICAP_RE.search(s)
        if sm:
            line = _slug_decimal(sm.group(1), sm.group(2))
            if line is not None:
                return None, line
        # Question fallback
        m = _HANDICAP_RE.search(q)
        if m:
            try:
                return None, float(m.group(0))
            except ValueError:
                return None, None
        return None, None
    if mt in ("tennis_set_totals",):
        # Önce slug: "match-total-22pt5" → 22.5
        sm = _SLUG_TOTAL_RE.search(s)
        if sm:
            line = _slug_decimal(sm.group(1), sm.group(2))
            if line is not None:
                return line, None
        # Question fallback (over/under/total/totals/o/u)
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
    max_phi_for_trade: float = _DEFAULT_MAX_PHI_FOR_TRADE,
    low_tier_slug_prefixes: tuple[str, ...] = _DEFAULT_LOW_TIER_SLUG_PREFIXES,
    low_tier_question_keywords: tuple[str, ...] = _DEFAULT_LOW_TIER_QUESTION_KEYWORDS,
    surface_resolver=None,
) -> EnrichResult:
    """Tennis market enrichment — SPEC-Z14 (2026-06-03) BM-first, model fallback.

    Akış:
      - Non-tennis  → bookmaker (h2h)
      - Low-tier    → fail (yetki dışı)
      - ML + BM OK  → BM döner (BM-first)
      - ML + BM fail → model fallback (oyuncu/phi/rating tüm guard'lar)
      - Alt market  → sadece model (BM h2h dışı veri vermiyor; cascade bug önleme)

    Veri kanıtı (2026-06-03, n=11 ML): source=bookmaker %83 WR / +$28,
    source=model %40 WR / -$9 → BM önceliklendirildi.

    Yetki parametreleri (max_phi, low_tier_*) config.yaml > tennis altından
    factory.py üzerinden geçirilir; default'lar geri uyumluluk için.
    """
    sport = (market.sport_tag or "").lower()
    if sport != "tennis":
        return bookmaker_enricher(market)

    if _is_low_tier_tennis(
        market.slug or "", market.question or "",
        slug_prefixes=low_tier_slug_prefixes,
        question_keywords=low_tier_question_keywords,
    ):
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_PLAYER_NOT_IN_RATINGS,
        )

    market_type = _infer_market_type(market)
    is_moneyline = market_type in _MONEYLINE_TYPES

    # SPEC-Z14: ML → BM-first. BM data varsa onu kullan, yoksa model fallback.
    if is_moneyline:
        bm_result = bookmaker_enricher(market)
        if bm_result.probability is not None:
            return bm_result
        # BM yok → model fallback (aşağı düş).

    # Model akışı (alt market'ler buradan başlar; ML için BM fail fallback'i).
    if not ratings:
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.MODEL_DATA_MISSING)

    player_a, player_b = extract_teams(market.question)
    if not player_a or not player_b:
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.TEAM_EXTRACT_FAILED)

    # Polymarket genelde soyadı gönderir ("Hurkacz"), Sackmann full name
    # ("Hubert Hurkacz") saklar. Soyadı substring + ambiguity safety ile çöz.
    resolved_a = _resolve_player_name(player_a, ratings)
    resolved_b = _resolve_player_name(player_b, ratings)
    if resolved_a is None or resolved_b is None:
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_PLAYER_NOT_IN_RATINGS,
        )
    player_a, player_b = resolved_a, resolved_b

    # Yetki filtresi: Glicko RD (phi) çok yüksekse oyuncu yeterince oynamamış →
    # rating güvenilmez. phi < 100 = güvenilir (~30+ maç).
    snap_a = ratings[player_a]
    snap_b = ratings[player_b]
    if snap_a.rating.phi >= max_phi_for_trade or snap_b.rating.phi >= max_phi_for_trade:
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_PLAYER_NOT_IN_RATINGS,
        )

    best_of = _infer_best_of(market.question)
    surface = surface_resolver.resolve(market) if surface_resolver is not None else None
    if surface is None:
        logger.warning("Tenis zemin bilinmiyor, atlandı: %s", (market.question or "")[:60])
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.MODEL_DATA_MISSING)
    line, handicap = _extract_market_params(
        market.question, market_type, slug=market.slug or "",
    )
    return enrich_tennis_from_model(
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
