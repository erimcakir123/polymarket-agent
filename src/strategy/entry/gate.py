"""Entry orchestrator — 3 entry stratejisini koordine eder (DECISIONS §11 Faz 3 + 6).

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

from src.domain.analysis.probability import BookmakerProbability
from src.domain.guards.blacklist import Blacklist
from src.domain.guards.manipulation import ManipulationCheck, adjust_position_size
from src.domain.portfolio.exposure import at_or_over_cap
from src.domain.portfolio.manager import PortfolioManager
from src.domain.risk.circuit_breaker import CircuitBreaker
from src.domain.risk.cooldown import CooldownTracker
from src.domain.risk.position_sizer import POLYMARKET_MIN_ORDER_USDC, confidence_position_size
from src.models.market import MarketData
from src.models.position import effective_price
from src.models.signal import Signal
from src.orchestration.portfolio_guards import (
    check_global_halts as _check_global_halts,
    check_per_market_guards as _check_per_market_guards,
)
from src.strategy.entry import (
    consensus as consensus_entry,
    early_entry,
    normal as normal_entry,
)

logger = logging.getLogger(__name__)


def _is_bimodal_market(market: MarketData) -> bool:
    """SPEC-W (2026-05-23): sport-aware bimodal dispatch.

    sport_rules.is_bimodal_market(sport_tag, market_type) → True = SL
    yakalayamaz, anlık çakılan market → küçük sizing cap ($15/$10).
    """
    from src.config.sport_rules import is_bimodal_market
    t = market.sports_market_type
    if t is None:
        return False
    if hasattr(t, "value"):
        t = t.value
    return is_bimodal_market(market.sport_tag or "", str(t))


def _is_bimodal_market_type(market: MarketData) -> bool:
    """SPEC-X (2026-05-24): bimodal market type check — market_type only.

    Independent of SPEC-W's sport-aware bimodal sizing classifier.
    SPEC-X floor + LIVE rules apply to ALL totals/spread markets regardless of sport,
    because the asymmetric-risk concern (in-game scoring collapse) is market-shape
    driven, not sport-driven.
    """
    t = market.sports_market_type
    if t is None:
        return False
    if hasattr(t, "value"):
        t = t.value
    return str(t) in ("totals", "spreads", "spread")


@dataclass
class GateConfig:
    """Entry gate parametreleri (config.yaml'dan gelir)."""
    min_edge: float = 0.06
    max_positions: int = 50
    max_positions_per_event: int = 3  # SPEC-J/K: ARCH Kural 8 gevşedi (max N / event_id)
    max_exposure_pct: float = 0.50  # SPEC-P: yumuşak cap, clipping yok
    # SPEC-U (2026-05-23): bimodal-aware sizing.
    # Non-bimodal (moneyline) = fixed_bet_usdc; bimodal (totals + spreads) = bimodal_bet_usdc.
    fixed_bet_usdc: dict[str, float] = field(default_factory=lambda: {"A": 50.0, "B": 30.0})
    bimodal_bet_usdc: dict[str, float] = field(default_factory=lambda: {"A": 15.0, "B": 10.0})
    max_entry_price: float = 0.88
    # SPEC-X (2026-05-24): bimodal market'lerde (totals + spreads) entry alt sınır.
    # Bu fiyatın altındaki entry'ler "piyasa kararını vermiş" sayılır — ultra-low guard
    # zaten anında tetikleneceği için baştan reddedilir.
    bimodal_min_entry_price: float = 0.20
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
        global_skip = _check_global_halts(
            breaker=self.breaker,
            cooldown=self.cooldown,
            portfolio=self.portfolio,
            max_positions=self.config.max_positions,
        )
        if global_skip is not None:
            logger.info("Entry gate halted: %s", global_skip.reason)
            return [
                GateResult(m.condition_id, None, global_skip.reason, skip_detail=global_skip.detail)
                for m in markets
            ]

        return [self._evaluate_one(m) for m in markets]

    def _evaluate_one(self, market: MarketData) -> GateResult:
        cid = market.condition_id

        # 1+2. event_cap + blacklist — portfolio_guards (DRY, SPEC-R)
        per_market_skip = _check_per_market_guards(
            market=market,
            portfolio=self.portfolio,
            blacklist=self.blacklist,
            max_positions_per_event=self.config.max_positions_per_event,
        )
        if per_market_skip is not None:
            return GateResult(
                cid, None, per_market_skip.reason,
                skip_detail=per_market_skip.detail,
            )

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
        if enrich_result.probability is None:
            detail = enrich_result.fail_reason.value if enrich_result.fail_reason else ""
            return GateResult(cid, None, "no_bookmaker_data", skip_detail=detail)
        bm_prob = enrich_result.probability
        if bm_prob.confidence == "C":
            return GateResult(cid, None, "confidence_C",
                              skip_detail=f"num_bookmakers={bm_prob.num_bookmakers:.1f}")

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

        # 6b. Bimodal entry floor (SPEC-X 2026-05-24) — totals/spread market'lerde
        # 20¢ altı entry "piyasa kararını vermiş" sayılır; ultra-low guard zaten
        # anında tetikleneceği için baştan reddet. _is_bimodal_market_type market_type'a
        # bakar (sport bağımsız); SPEC-W'nin sport-aware sizing classifier'ından farklı.
        if _is_bimodal_market_type(market) and entry_price < self.config.bimodal_min_entry_price:
            detail = f"price={entry_price:.3f}, min={self.config.bimodal_min_entry_price}"
            return GateResult(cid, None, "bimodal_entry_below_floor", skip_detail=detail, manipulation=manip)

        # 6c. Bimodal LIVE yasağı (SPEC-X 2026-05-24) — bimodal market'lerde
        # AI/model olasılığı pre-match hesaplanır; LIVE'da market durumu değişmiş
        # olur → tahmin bayatlamış → asimetrik risk. event_live default False.
        if _is_bimodal_market_type(market) and market.event_live:
            return GateResult(
                cid, None, "bimodal_entry_live",
                skip_detail="market is live",
                manipulation=manip,
            )

        # 7. Position sizing (SPEC-P sabit-tier + SPEC-U bimodal-aware).
        # Bimodal = totals + spreads (SL muaf, anlık çakılma riski) → küçük cap.
        # Non-bimodal = moneyline → eski sizing.
        bet_dict = (
            self.config.bimodal_bet_usdc
            if _is_bimodal_market(market)
            else self.config.fixed_bet_usdc
        )
        raw_size = confidence_position_size(
            confidence=signal.confidence,
            fixed_bet_usdc=bet_dict,
        )

        # Manipulation medium risk → halve
        adjusted_size = adjust_position_size(raw_size, manip)
        if adjusted_size < POLYMARKET_MIN_ORDER_USDC:
            detail = f"size={adjusted_size:.2f}, min={POLYMARKET_MIN_ORDER_USDC:.2f}"
            return GateResult(cid, None, "size_below_min", skip_detail=detail, manipulation=manip)

        # 8. Exposure cap — yumuşak: exposure < cap iken tam trade alınır, ≥ cap → blok.
        total_portfolio = self.portfolio.bankroll + self.portfolio.total_invested()
        if at_or_over_cap(
            self.portfolio.positions, total_portfolio, self.config.max_exposure_pct,
        ):
            invested = self.portfolio.total_invested()
            cap = total_portfolio * self.config.max_exposure_pct
            detail = f"invested={invested:.2f}, cap={cap:.2f}"
            return GateResult(cid, None, "exposure_cap_reached", skip_detail=detail, manipulation=manip)

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
