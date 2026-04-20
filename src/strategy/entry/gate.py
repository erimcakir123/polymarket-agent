"""Entry orchestrator — directional entry (SPEC-017).

Directional entry: bookmaker konsensüs favorisi + fiyat aralığında giriş.
Edge hesabı yok.

Common pipeline (her market için):
  event_guard → blacklist → manipulation → enrich → directional →
  exposure → sizing → result.

İş mantığı YOK — sadece pipeline koordinasyonu.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.config.sport_rules import _normalize, is_cricket_sport
from src.domain.analysis.probability import BookmakerProbability
from src.orchestration.event_grouper import EventGroup, group_markets_by_event
from src.strategy.entry import three_way as three_way_entry
from src.strategy.entry.directional import evaluate_directional
from src.domain.guards.blacklist import Blacklist
from src.domain.guards.manipulation import ManipulationCheck, adjust_position_size
from src.domain.portfolio.exposure import available_under_cap
from src.domain.portfolio.manager import PortfolioManager
from src.domain.risk.circuit_breaker import CircuitBreaker
from src.domain.risk.cooldown import CooldownTracker
from src.domain.risk.position_sizer import (
    POLYMARKET_MIN_ORDER_USDC,
    confidence_position_size,
)
from src.models.enums import Direction
from src.models.market import MarketData
from src.models.position import effective_price, effective_win_prob
from src.models.signal import Signal

logger = logging.getLogger(__name__)

# MVP disi sporlar — entry gate'te reddedilir (TODO-002 MMA, TODO-003 Golf)
_NON_MVP_SPORTS: frozenset[str] = frozenset({"mma", "golf"})


@dataclass
class GateConfig:
    """Entry gate parametreleri (config.yaml'dan gelir)."""
    min_favorite_probability: float = 0.60    # directional: bookmaker favori eşiği (tek gerçek filtre)
    max_entry_price: float = 0.80             # directional: pahalı outlier cap (alt taban YOK)
    max_positions: int = 50
    max_exposure_pct: float = 0.50
    hard_cap_overflow_pct: float = 0.02
    min_entry_size_pct: float = 0.015
    confidence_bet_pct: dict[str, float] = field(default_factory=lambda: {"A": 0.05, "B": 0.04})
    max_single_bet_usdc: float = 75.0
    max_bet_pct: float = 0.05
    # SPEC-016: stake = base × win_prob (direction-adjusted)
    probability_weighted: bool = True


@dataclass
class GateResult:
    """Market başına kararın sonucu — entered veya skip sebebi."""
    condition_id: str
    signal: Signal | None
    skipped_reason: str = ""
    skip_detail: str = ""
    manipulation: ManipulationCheck | None = None


class EntryGate:
    """Market listesi → Signal listesi orchestrator."""

    def __init__(
        self,
        config: GateConfig,
        portfolio: PortfolioManager,
        circuit_breaker: CircuitBreaker,
        cooldown: CooldownTracker,
        blacklist: Blacklist,
        odds_enricher,
        manipulation_checker,
        cricket_client=None,  # SPEC-011
    ) -> None:
        self.config = config
        self.portfolio = portfolio
        self.breaker = circuit_breaker
        self.cooldown = cooldown
        self.blacklist = blacklist
        self._enricher = odds_enricher
        self._manip_check = manipulation_checker
        self._cricket_client = cricket_client

    def run(self, markets: list[MarketData]) -> list[GateResult]:
        """Tüm marketleri değerlendir. Her biri için GateResult döner.

        2-way sporlar: _evaluate_one (mevcut akış).
        3-way event grupları: _evaluate_three_way (event_grouper + three_way strategy).
        event_id olmayan market'ler: _evaluate_one (ungrouped pass-through).
        """
        # Global halts — her market için tekrar kontrol etmek yerine bir kez
        total_portfolio = self.portfolio.bankroll + self.portfolio.total_invested()
        halt, reason = self.breaker.should_halt_entries(portfolio_value=total_portfolio)
        if halt:
            logger.info("Entry gate halted: %s", reason)
            detail = reason[len("breaker: "):] if reason.startswith("breaker: ") else reason
            return [GateResult(m.condition_id, None, "circuit_breaker", skip_detail=detail) for m in markets]

        remaining = self.cooldown.state.cooldown_remaining
        if self.cooldown.is_active():
            detail = f"cycles_remaining={remaining}"
            return [GateResult(m.condition_id, None, "cooldown_active", skip_detail=detail) for m in markets]

        count = self.portfolio.count()
        if count >= self.config.max_positions:
            detail = f"count={count}/{self.config.max_positions}"
            return [GateResult(m.condition_id, None, "max_positions_reached", skip_detail=detail) for m in markets]

        results: list[GateResult] = []
        groups = group_markets_by_event(markets)

        # event_id'ye sahip tüm market'lerin condition_id seti
        grouped_cids: set[str] = {m.condition_id for g in groups for m in g.markets}

        # event_id olmayan market'ler → mevcut _evaluate_one akışı
        for m in markets:
            if m.condition_id not in grouped_cids:
                results.append(self._evaluate_one(m))

        # Gruplanmış event'ler
        for g in groups:
            if g.market_type == "THREE_WAY":
                tw_result = self._evaluate_three_way(g)
                if tw_result is not None:
                    results.append(tw_result)
                else:
                    # 3-way grubu signal üretmedi → her market için price_out_of_range
                    for m in g.markets:
                        results.append(GateResult(m.condition_id, None, "price_out_of_range"))
            else:
                # BINARY group: her market _evaluate_one
                for m in g.markets:
                    results.append(self._evaluate_one(m))

        return results

    def _evaluate_one(self, market: MarketData) -> GateResult:
        cid = market.condition_id

        # 0. MVP disi sporlar erken reddi (TODO-002 MMA, TODO-003 Golf)
        if _normalize(market.sport_tag) in _NON_MVP_SPORTS:
            return GateResult(cid, None, "sport_not_in_mvp", skip_detail=f"sport={market.sport_tag}")

        # 1. Event-level guard (ARCH Kural 8)
        if market.event_id and self.portfolio.has_event(market.event_id):
            return GateResult(cid, None, "event_already_held", skip_detail=f"event_id={market.event_id}")

        # 2. Blacklist — split checks to know which matched
        if self.blacklist.is_blacklisted(condition_id=cid):
            return GateResult(cid, None, "blacklisted", skip_detail="match=condition_id")
        if market.event_id and self.blacklist.is_blacklisted(event_id=market.event_id):
            return GateResult(cid, None, "blacklisted", skip_detail="match=event_id")

        # 3. Manipulation guard
        manip = self._manip_check(
            question=market.question,
            liquidity=market.liquidity,
        )
        if not manip.safe:
            manip_detail = ", ".join(manip.flags) if manip.flags else "unknown"
            return GateResult(cid, None, "manipulation_high_risk",
                              skip_detail=manip_detail, manipulation=manip)

        # 4. Enrichment (Odds API)
        enrich_result = self._enricher(market)
        # Gamma event.startTime per-match doğru saati veriyor; Odds API
        # commence_time UFC'de kart saati (3-4h yanlış), MLB'de seri maçı
        # karışıklığı yapıyor. Override kaldırıldı — Gamma saati korunur.
        if enrich_result.probability is None:
            detail = enrich_result.fail_reason.value if enrich_result.fail_reason else ""
            return GateResult(cid, None, "no_bookmaker_data", skip_detail=detail)
        bm_prob = enrich_result.probability
        if bm_prob.confidence == "C":
            return GateResult(cid, None, "confidence_C",
                              skip_detail=f"num_bookmakers={bm_prob.num_bookmakers:.1f}")

        # SPEC-011: Cricket entries need CricAPI availability
        if is_cricket_sport(market.sport_tag) and self._cricket_client is not None:
            if self._cricket_client.quota.exhausted:
                detail = f"quota={self._cricket_client.quota.used_today}/{self._cricket_client.quota.daily_limit}"
                return GateResult(cid, None, "cricapi_unavailable", skip_detail=detail, manipulation=manip)

        # 5. Directional entry evaluation (SPEC-017)
        signal = evaluate_directional(
            market=market,
            anchor=bm_prob.probability,
            confidence=bm_prob.confidence,
            min_favorite_probability=self.config.min_favorite_probability,
            max_entry_price=self.config.max_entry_price,
        )
        if signal is None:
            return self._directional_skip_result(cid, market, bm_prob, manip)

        # Patch bookmaker metadata onto signal (directional doesn't receive these)
        signal = signal.model_copy(update={
            "num_bookmakers": bm_prob.num_bookmakers,
            "has_sharp": bm_prob.has_sharp,
        })

        # 6. Position sizing
        win_prob = (
            effective_win_prob(signal.anchor_probability, signal.direction)
            if self.config.probability_weighted
            else 1.0
        )
        raw_size = confidence_position_size(
            confidence=signal.confidence,
            bankroll=self.portfolio.bankroll,
            confidence_bet_pct=self.config.confidence_bet_pct,
            max_bet_usdc=self.config.max_single_bet_usdc,
            max_bet_pct=self.config.max_bet_pct,
            win_probability=win_prob,
        )

        # Manipulation medium risk → halve
        adjusted_size = adjust_position_size(raw_size, manip)
        if adjusted_size < POLYMARKET_MIN_ORDER_USDC:
            detail = f"size={adjusted_size:.2f}, min={POLYMARKET_MIN_ORDER_USDC:.2f}"
            return GateResult(cid, None, "size_below_min", skip_detail=detail, manipulation=manip)

        # 7. Exposure cap — soft + hard buffer + size clipping.
        total_portfolio = self.portfolio.bankroll + self.portfolio.total_invested()
        available = available_under_cap(
            self.portfolio.positions, total_portfolio,
            self.config.max_exposure_pct, self.config.hard_cap_overflow_pct,
        )
        min_size = self.portfolio.bankroll * self.config.min_entry_size_pct
        if available < min_size:
            detail = f"available={available:.2f}, min={min_size:.2f}"
            return GateResult(cid, None, "exposure_cap_reached", skip_detail=detail, manipulation=manip)

        final_size = min(adjusted_size, available)
        if final_size < POLYMARKET_MIN_ORDER_USDC:
            detail = f"size={final_size:.2f}, min={POLYMARKET_MIN_ORDER_USDC:.2f}"
            return GateResult(cid, None, "size_below_min", skip_detail=detail, manipulation=manip)

        approved = signal.model_copy(update={"size_usdc": round(final_size, 2)})
        return GateResult(cid, approved, "", manipulation=manip)

    def _directional_skip_result(
        self,
        cid: str,
        market: MarketData,
        bm_prob: BookmakerProbability,
        manip: ManipulationCheck,
    ) -> GateResult:
        """Directional skip sebebini belirle: fav_prob yetersiz mi, fiyat pahalı outlier mı."""
        anchor = bm_prob.probability
        direction = Direction.BUY_YES if anchor >= 0.50 else Direction.BUY_NO
        win_prob = effective_win_prob(anchor, direction.value)
        if win_prob < self.config.min_favorite_probability:
            detail = (
                f"win_prob={win_prob:.3f}, min={self.config.min_favorite_probability}, "
                f"bm={anchor:.2f}"
            )
            return GateResult(cid, None, "below_fav_prob", skip_detail=detail, manipulation=manip)
        # Price above max (pahalı outlier)
        ep = (
            market.yes_price if direction == Direction.BUY_YES
            else 1.0 - market.yes_price
        )
        detail = f"price={ep:.3f}, max={self.config.max_entry_price}"
        return GateResult(cid, None, "price_out_of_range", skip_detail=detail, manipulation=manip)

    def _evaluate_three_way(self, group: EventGroup) -> GateResult | None:
        """3-way event değerlendirmesi (SPEC-015).

        1. classify_outcomes → home/draw/away market'leri
        2. Her market için enricher → BookmakerProbability
        3. three_way.evaluate → Signal (veya None)
        4. Signal varsa: event_guard + blacklist + sizing + exposure → GateResult
        """
        home, draw, away = group.classify_outcomes()
        if home is None or draw is None or away is None:
            return None  # inkomplet grup

        # Her market için bookmaker prob enrich
        probs: dict[str, BookmakerProbability] = {}
        for outcome, m in (("home", home), ("draw", draw), ("away", away)):
            enrich_result = self._enricher(m)
            if enrich_result.probability is None:
                return None
            probs[outcome] = enrich_result.probability

        # 3-way signal değerlendirmesi (edge-free, SPEC-017)
        signal = three_way_entry.evaluate(
            home_market=home,
            draw_market=draw,
            away_market=away,
            probs=probs,
            favorite_threshold=0.40,
            favorite_margin=0.07,
            max_entry_price=self.config.max_entry_price,
        )
        if signal is None:
            return None

        # Signal'deki condition_id ile favori market'i bul
        fav_market = next(
            (m for m in group.markets if m.condition_id == signal.condition_id),
            None,
        )
        if fav_market is None:
            return None

        # Event guard (ARCH Kural 8)
        if fav_market.event_id and self.portfolio.has_event(fav_market.event_id):
            return GateResult(fav_market.condition_id, None, "event_already_held",
                              skip_detail=f"event_id={fav_market.event_id}")

        # Blacklist
        if self.blacklist.is_blacklisted(condition_id=fav_market.condition_id):
            return GateResult(fav_market.condition_id, None, "blacklisted",
                              skip_detail="match=condition_id")
        if fav_market.event_id and self.blacklist.is_blacklisted(event_id=fav_market.event_id):
            return GateResult(fav_market.condition_id, None, "blacklisted",
                              skip_detail="match=event_id")

        # Sizing
        win_prob_3w = (
            effective_win_prob(signal.anchor_probability, signal.direction)
            if self.config.probability_weighted
            else 1.0
        )
        raw_size = confidence_position_size(
            confidence=signal.confidence,
            bankroll=self.portfolio.bankroll,
            confidence_bet_pct=self.config.confidence_bet_pct,
            max_bet_usdc=self.config.max_single_bet_usdc,
            max_bet_pct=self.config.max_bet_pct,
            win_probability=win_prob_3w,
        )
        if raw_size < POLYMARKET_MIN_ORDER_USDC:
            return GateResult(fav_market.condition_id, None, "size_below_min",
                              skip_detail=f"size={raw_size:.2f}")

        # Exposure cap
        total_portfolio = self.portfolio.bankroll + self.portfolio.total_invested()
        available = available_under_cap(
            self.portfolio.positions, total_portfolio,
            self.config.max_exposure_pct, self.config.hard_cap_overflow_pct,
        )
        min_size = self.portfolio.bankroll * self.config.min_entry_size_pct
        if available < min_size:
            return GateResult(fav_market.condition_id, None, "exposure_cap_reached",
                              skip_detail=f"available={available:.2f}, min={min_size:.2f}")

        final_size = min(raw_size, available)
        if final_size < POLYMARKET_MIN_ORDER_USDC:
            return GateResult(fav_market.condition_id, None, "size_below_min",
                              skip_detail=f"size={final_size:.2f}")

        approved = signal.model_copy(update={"size_usdc": round(final_size, 2)})
        return GateResult(fav_market.condition_id, approved, "")
