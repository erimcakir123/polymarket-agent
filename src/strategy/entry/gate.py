"""Entry orchestrator — 3 entry stratejisini koordine eder (TDD §11 Faz 3 + 6).

Strateji öncelik sırası (ilk Signal kazanır):
  1. Consensus  — book + market aynı favori (≥65¢) → 99¢ payout edge
  2. Early      — match_start 6h+ önce, yüksek edge (≥10%)
  3. Normal     — bookmaker P(YES) vs market YES, edge ≥6%

Common pipeline (her market için):
  event_guard → blacklist → manipulation → enrich → strategies →
  exposure → sizing → result.

Iş mantığı YOK — sadece "hangi sırada" koordinasyonu.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.config.sport_rules import is_cricket_sport
from src.domain.analysis.probability import BookmakerProbability
from src.orchestration.event_grouper import EventGroup, group_markets_by_event
from src.strategy.entry import three_way as three_way_entry
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
from src.models.market import MarketData
from src.models.position import effective_price
from src.models.signal import Signal
from src.strategy.entry import (
    consensus as consensus_entry,
    early_entry,
    normal as normal_entry,
)

logger = logging.getLogger(__name__)


@dataclass
class GateConfig:
    """Entry gate parametreleri (config.yaml'dan gelir)."""
    min_edge: float = 0.06
    confidence_multipliers: dict[str, float] = field(
        default_factory=lambda: {"A": 1.00, "B": 1.00},
    )
    min_favorite_probability: float = 0.52    # SPEC-013 rev: normal entry underdog filter (%55 -> %52 DET-BOS fix)
    max_positions: int = 50
    max_exposure_pct: float = 0.50
    hard_cap_overflow_pct: float = 0.02
    min_entry_size_pct: float = 0.015
    confidence_bet_pct: dict[str, float] = field(default_factory=lambda: {"A": 0.05, "B": 0.04})
    max_single_bet_usdc: float = 50.0    # SPEC-010: bet tavani
    max_bet_pct: float = 0.05
    max_entry_price: float = 0.88
    # Consensus
    consensus_enabled: bool = True
    consensus_min_price: float = 0.65
    consensus_max_price: float = 0.80    # 80¢ cap — EV guard Spurs 84¢'yi bloklar
    # Early entry
    early_enabled: bool = True
    early_min_edge: float = 0.10
    early_min_favorite_probability: float = 0.52    # SPEC-013 rev: early entry underdog filter (%52)
    early_min_confidence: str = "B"
    early_max_entry_price: float = 0.70
    early_min_hours_to_start: float = 6.0
    early_max_hours_to_start: float = 24.0


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
                    # 3-way grubu signal üretmedi → her market için no_edge
                    for m in g.markets:
                        results.append(GateResult(m.condition_id, None, "no_edge"))
            else:
                # BINARY group: her market _evaluate_one
                for m in g.markets:
                    results.append(self._evaluate_one(m))

        return results

    def _evaluate_one(self, market: MarketData) -> GateResult:
        cid = market.condition_id

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

        # 5. Strateji önceliği — ilk Signal üreten kazanır
        signal = self._evaluate_strategies(market, bm_prob)
        if signal is None:
            edge_raw = abs(bm_prob.probability - market.yes_price)
            no_edge_detail = (
                f"edge={edge_raw:.3f}, min={self.config.min_edge}, "
                f"bm={bm_prob.probability:.2f}, yes={market.yes_price:.2f}"
            )
            return GateResult(cid, None, "no_edge", skip_detail=no_edge_detail)

        # 6. Entry price cap — 88¢+ girişlerde R/R kötü (max payout 0.99-entry)
        entry_price = effective_price(signal.market_price, signal.direction)
        if entry_price >= self.config.max_entry_price:
            detail = f"price={entry_price:.3f}, cap={self.config.max_entry_price}"
            return GateResult(cid, None, "entry_price_cap", skip_detail=detail, manipulation=manip)

        # 7. Position sizing
        raw_size = confidence_position_size(
            confidence=signal.confidence,
            bankroll=self.portfolio.bankroll,
            confidence_bet_pct=self.config.confidence_bet_pct,
            max_bet_usdc=self.config.max_single_bet_usdc,
            max_bet_pct=self.config.max_bet_pct,
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

    def _evaluate_three_way(self, group: EventGroup) -> GateResult | None:
        """3-way event değerlendirmesi (SPEC-015).

        1. classify_outcomes → home/draw/away market'leri
        2. Her market için enricher → BookmakerProbability
        3. three_way.evaluate → Signal (veya None)
        4. Signal varsa: event_guard + blacklist + entry_price_cap + sizing + exposure → GateResult
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

        # 3-way signal değerlendirmesi
        signal = three_way_entry.evaluate(
            home_market=home,
            draw_market=draw,
            away_market=away,
            probs=probs,
            min_edge=self.config.min_edge,
            favorite_threshold=0.40,
            favorite_margin=0.07,
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

        # Entry price cap — 88c+ girişlerde R/R kötü
        entry_price = effective_price(signal.market_price, signal.direction)
        if entry_price >= self.config.max_entry_price:
            return GateResult(fav_market.condition_id, None, "entry_price_cap",
                              skip_detail=f"price={entry_price:.3f}, cap={self.config.max_entry_price}")

        # Sizing
        raw_size = confidence_position_size(
            confidence=signal.confidence,
            bankroll=self.portfolio.bankroll,
            confidence_bet_pct=self.config.confidence_bet_pct,
            max_bet_usdc=self.config.max_single_bet_usdc,
            max_bet_pct=self.config.max_bet_pct,
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

    def _evaluate_strategies(self, market: MarketData, bm_prob: BookmakerProbability) -> Signal | None:
        """3 stratejiyi öncelik sırasıyla dene. İlk Signal kazanır.

        Sıra: Consensus (en güçlü) → Early (yüksek edge) → Normal.
        """
        # 1. Consensus — book + market aynı favori, ≥65¢
        if self.config.consensus_enabled:
            sig = consensus_entry.evaluate(
                market, bm_prob,
                min_price=self.config.consensus_min_price,
                max_price=self.config.consensus_max_price,
            )
            if sig is not None:
                return sig

        # 2. Early entry — match_start ≥6h önce, yüksek edge
        if self.config.early_enabled:
            sig = early_entry.evaluate(
                market, bm_prob,
                min_edge=self.config.early_min_edge,
                min_favorite_probability=self.config.early_min_favorite_probability,
                min_confidence=self.config.early_min_confidence,
                max_entry_price=self.config.early_max_entry_price,
                min_hours_to_start=self.config.early_min_hours_to_start,
                max_hours_to_start=self.config.early_max_hours_to_start,
                confidence_multipliers=self.config.confidence_multipliers,
            )
            if sig is not None:
                return sig

        # 3. Normal — bookmaker P(YES) vs market YES, edge ≥6%
        return normal_entry.evaluate(
            market, bm_prob,
            min_edge=self.config.min_edge,
            confidence_multipliers=self.config.confidence_multipliers,
            min_favorite_probability=self.config.min_favorite_probability,
        )
