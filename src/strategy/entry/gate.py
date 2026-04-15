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
from dataclasses import dataclass

from src.domain.analysis.probability import BookmakerProbability
from src.domain.guards.blacklist import Blacklist
from src.domain.guards.manipulation import ManipulationCheck, adjust_position_size
from src.domain.portfolio.exposure import exceeds_exposure_limit
from src.domain.portfolio.manager import PortfolioManager
from src.domain.risk.circuit_breaker import CircuitBreaker
from src.domain.risk.cooldown import CooldownTracker
from src.domain.risk.position_sizer import POLYMARKET_MIN_ORDER_USDC, confidence_position_size
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
    max_positions: int = 50
    max_exposure_pct: float = 0.50
    max_single_bet_usdc: float = 75.0
    max_bet_pct: float = 0.05
    max_entry_price: float = 0.88
    # Consensus
    consensus_enabled: bool = True
    consensus_min_price: float = 0.65
    # Early entry
    early_enabled: bool = True
    early_min_edge: float = 0.10
    early_min_anchor_probability: float = 0.55
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
    ) -> None:
        self.config = config
        self.portfolio = portfolio
        self.breaker = circuit_breaker
        self.cooldown = cooldown
        self.blacklist = blacklist
        self._enricher = odds_enricher
        self._manip_check = manipulation_checker

    def run(self, markets: list[MarketData]) -> list[GateResult]:
        """Tüm marketleri değerlendir. Her biri için GateResult döner."""
        # Global halts — her market için tekrar kontrol etmek yerine bir kez
        halt, reason = self.breaker.should_halt_entries()
        if halt:
            logger.info("Entry gate halted: %s", reason)
            return [GateResult(m.condition_id, None, f"breaker: {reason}") for m in markets]

        if self.cooldown.is_active():
            return [GateResult(m.condition_id, None, "cooldown_active") for m in markets]

        if self.portfolio.count() >= self.config.max_positions:
            return [GateResult(m.condition_id, None, "max_positions_reached") for m in markets]

        results: list[GateResult] = []
        for m in markets:
            results.append(self._evaluate_one(m))
        return results

    def _evaluate_one(self, market: MarketData) -> GateResult:
        cid = market.condition_id

        # 1. Event-level guard (ARCH Kural 8)
        if market.event_id and self.portfolio.has_event(market.event_id):
            return GateResult(cid, None, "event_already_held")

        # 2. Blacklist
        if self.blacklist.is_blacklisted(condition_id=cid, event_id=market.event_id or ""):
            return GateResult(cid, None, "blacklisted")

        # 3. Manipulation guard
        manip = self._manip_check(
            question=market.question,
            liquidity=market.liquidity,
        )
        if not manip.safe:
            return GateResult(cid, None, "manipulation_high_risk", manipulation=manip)

        # 4. Enrichment (Odds API)
        bm_prob: BookmakerProbability | None = self._enricher(market)
        if bm_prob is None:
            return GateResult(cid, None, "no_bookmaker_data")
        if bm_prob.confidence == "C":
            return GateResult(cid, None, "confidence_C")

        # 5. Strateji önceliği — ilk Signal üreten kazanır
        signal = self._evaluate_strategies(market, bm_prob)
        if signal is None:
            return GateResult(cid, None, "no_edge")

        # 6. Entry price cap — 88¢+ girişlerde R/R kötü (max payout 0.99-entry)
        entry_price = effective_price(signal.market_price, signal.direction)
        if entry_price >= self.config.max_entry_price:
            return GateResult(cid, None, "entry_price_cap", manipulation=manip)

        # 7. Position sizing
        raw_size = confidence_position_size(
            confidence=signal.confidence,
            bankroll=self.portfolio.bankroll,
            max_bet_usdc=self.config.max_single_bet_usdc,
            max_bet_pct=self.config.max_bet_pct,
        )

        # Manipulation medium risk → halve
        adjusted_size = adjust_position_size(raw_size, manip)
        if adjusted_size < POLYMARKET_MIN_ORDER_USDC:
            return GateResult(cid, None,
                              f"size_below_min ({adjusted_size:.2f} < {POLYMARKET_MIN_ORDER_USDC})",
                              manipulation=manip)

        # 7. Exposure cap
        if exceeds_exposure_limit(
            self.portfolio.positions, adjusted_size,
            self.portfolio.bankroll, self.config.max_exposure_pct,
        ):
            return GateResult(cid, None, "exposure_cap_reached", manipulation=manip)

        # Signal'a size yaz ve onayla
        approved = signal.model_copy(update={"size_usdc": round(adjusted_size, 2)})
        return GateResult(cid, approved, "", manipulation=manip)

    def _evaluate_strategies(self, market: MarketData, bm_prob: BookmakerProbability) -> Signal | None:
        """3 stratejiyi öncelik sırasıyla dene. İlk Signal kazanır.

        Sıra: Consensus (en güçlü) → Early (yüksek edge) → Normal.
        """
        # 1. Consensus — book + market aynı favori, ≥65¢
        if self.config.consensus_enabled:
            sig = consensus_entry.evaluate(market, bm_prob, min_price=self.config.consensus_min_price)
            if sig is not None:
                return sig

        # 2. Early entry — match_start ≥6h önce, yüksek edge
        if self.config.early_enabled:
            sig = early_entry.evaluate(
                market, bm_prob,
                min_edge=self.config.early_min_edge,
                min_anchor_probability=self.config.early_min_anchor_probability,
                min_confidence=self.config.early_min_confidence,
                max_entry_price=self.config.early_max_entry_price,
                min_hours_to_start=self.config.early_min_hours_to_start,
                max_hours_to_start=self.config.early_max_hours_to_start,
            )
            if sig is not None:
                return sig

        # 3. Normal — bookmaker P(YES) vs market YES, edge ≥6%
        return normal_entry.evaluate(market, bm_prob, min_edge=self.config.min_edge)
