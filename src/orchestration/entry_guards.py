"""Pre-execution entry guards — EntryProcessor'dan ayrı modül (ARCH_GUARD §3).

guard'lar:
  - check_duplicate_condition: aynı condition_id'ye 2. pozisyon
  - check_exclude_combo: config'de tanımlı negatif-EV kombinasyonları (tour+market+conf)
  - check_correlated_bet: aynı event + market_type + direction birden fazla
  - check_loss_reentry: bu session'da zararla kapanan markete tekrar giriş (SPEC-Z26)
  - resolve_market_meta: market_type → (type, total_line, total_side)

True döner: BLOCKED, entry akışı durur.
False/0 değerleri: geçti, devam et.
"""
from __future__ import annotations

import logging

from src.domain.matching.market_line_parser import parse_total_line
from src.models.enums import SportsMarketType, TotalSide
from src.models.market import MarketData
from src.orchestration import operational_writers

logger = logging.getLogger(__name__)


def check_duplicate_condition(deps, market: MarketData) -> bool:
    """Aynı condition_id zaten portfolyoda mı? True → bloke (emir gönderme).

    2026-05-30 KRİTİK fix: place_order'dan ÖNCE check. Eski davranış: pozisyon
    zaten varsa _persist_filled_position defter kaydı yapmıyordu AMA
    executor.place_order ZATEN çağrılmıştı — paper'da görünmez ama live'da
    Polymarket'e gerçek emir gider, wallet boşalır, defter "duplicate" der
    → wallet ve defter çelişir.
    """
    if market.condition_id in deps.state.portfolio.positions:
        detail = f"condition_id={market.condition_id[:20]}..."
        operational_writers.log_skip(
            deps.skipped_logger, market,
            "duplicate_condition_id", detail=detail,
        )
        deps.stock.add(market, "duplicate_condition_id")
        return True
    return False


def check_exclude_combo(deps, market: MarketData, signal) -> bool:
    """2026-05-31 exclude_combos guard. Config'de tanımlı negatif-EV
    kombinasyonları (tennis_set_totals + tennis_first_set_winner, paper lab
    kanıtı -$63 ve -$162). True → blocklu, entry yok.
    """
    combos = (
        getattr(deps.state.config, "edge", None)
        and getattr(deps.state.config.edge, "exclude_combos", [])
        or []
    )
    if not (combos and market.slug):
        return False
    tour = market.slug.split("-")[0].lower()
    mt = market.sports_market_type
    conf = getattr(signal, "confidence", None)
    for combo in combos:
        if (combo.get("tour") == tour
                and combo.get("market_type") == mt
                and (combo.get("confidence") == conf or combo.get("confidence") is None)):
            detail = f"tour={tour} type={mt} confidence={conf}"
            operational_writers.log_skip(
                deps.skipped_logger, market,
                "exclude_combo_negative_ev", detail=detail,
            )
            deps.stock.add(market, "exclude_combo_negative_ev")
            return True
    return False


def check_correlated_bet(deps, market: MarketData, signal) -> bool:
    """2026-05-31 KORELASYON guard. Aynı event + market_type + direction birden
    fazla pozisyon = positively correlated bet, AVOID. True → blocklu.

    Farklı yön (over/under hedge) veya farklı market_type (moneyline + totals
    bağımsız) izinli.
    """
    if not market.event_id:
        return False
    same_combo = [
        p for p in deps.state.portfolio.positions.values()
        if p.event_id == market.event_id
        and p.sports_market_type == market.sports_market_type
        and p.direction == signal.direction.value
    ]
    if not same_combo:
        return False
    detail = (
        f"event={market.event_id} type={market.sports_market_type} "
        f"direction={signal.direction.value} existing={len(same_combo)}"
    )
    operational_writers.log_skip(
        deps.skipped_logger, market,
        "correlated_bet_guard", detail=detail,
    )
    deps.stock.add(market, "correlated_bet_guard")
    return True


def check_loss_reentry(deps, market: MarketData) -> bool:
    """SPEC-Z26: bu session'da zararla kapanan markete tekrar giriş yasağı.

    True → bloke. Kardeş guard'lar (duplicate/correlated) gibi her zaman açık —
    config flag yok. Liste `run_heavy`'de defterden türetilir (closed_at_loss_cids).

    Neden: bot canlı maçta stop'la çıkıp, yavaş bahisçi çapasına göre "fırsat
    büyüdü" sanıp aynı markete tekrar girip kaybı katlıyordu (ind-nyl −$35).
    """
    closed = getattr(deps.state.portfolio, "closed_at_loss", None)
    if not closed or market.condition_id not in closed:
        return False
    detail = f"condition_id={market.condition_id[:20]}..."
    operational_writers.log_skip(
        deps.skipped_logger, market,
        "loss_reentry_blocked", detail=detail,
    )
    deps.stock.add(market, "loss_reentry_blocked")
    return True


def resolve_market_meta(
    market: MarketData,
) -> tuple[SportsMarketType, float | None, TotalSide | None]:
    """market.sports_market_type'a göre Position ek alanlarını çıkar.

    Totals: question'dan (total_line, side); Polymarket YES = OVER.
    Spreads/Moneyline veya tanımsız: total alanları None.
    """
    market_type_raw = market.sports_market_type or SportsMarketType.MONEYLINE.value
    if market_type_raw == SportsMarketType.TOTALS.value:
        parsed = parse_total_line(market.question)
        if parsed is None:
            return SportsMarketType.TOTALS, None, None
        line, side = parsed
        return SportsMarketType.TOTALS, line, TotalSide(side)
    if market_type_raw == SportsMarketType.SPREADS.value:
        return SportsMarketType.SPREADS, None, None
    # 2026-05-31: tennis tipleri artık olduğu gibi korunur. Enum'da tanımlı
    # olmayan tipler MONEYLINE fallback (forward-compat).
    try:
        return SportsMarketType(market_type_raw), None, None
    except ValueError:
        return SportsMarketType.MONEYLINE, None, None
