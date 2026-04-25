"""Entry gate — gap-based NBA entry kararı."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.config.sport_rules import _normalize
from src.models.enums import Direction, EntryReason
from src.models.signal import Signal

if TYPE_CHECKING:
    from src.models.market import MarketData


@dataclass
class GateConfig:
    min_favorite_probability: float
    max_entry_price: float
    max_positions: int
    max_exposure_pct: float
    confidence_bet_pct: dict
    max_single_bet_usdc: float
    max_bet_pct: float
    probability_weighted: bool
    min_bookmakers: int
    min_sharps: int
    hard_cap_overflow_pct: float = field(default=0.02)
    min_entry_size_pct: float = field(default=0.015)
    active_sports: list[str] = field(default_factory=list)
    min_gap_threshold: float = field(default=0.08)
    gap_high_zone: float = field(default=0.15)
    gap_extreme_zone: float = field(default=0.25)
    min_polymarket_price: float = field(default=0.15)
    min_market_volume: float = field(default=5000.0)
    max_match_start_hours: float = field(default=6.0)
    confidence_a_pct: float = field(default=0.05)
    confidence_b_pct: float = field(default=0.03)
    high_gap_multiplier: float = field(default=1.2)
    extreme_gap_multiplier: float = field(default=1.3)
    min_bet_usd: float = field(default=5.0)


@dataclass
class GateResult:
    condition_id: str
    signal: Signal | None = None
    skipped_reason: str | None = None
    skip_detail: str | None = None


# ── Pure helpers (tested directly) ──────────────────────────────

def _classify_confidence(has_sharp: bool, bm_weight: float) -> str:
    """Bookmaker kalitesine göre A/B/C tier."""
    if bm_weight < 5.0:
        return "C"
    return "A" if has_sharp else "B"


def _gap_multiplier(gap: float, cfg: GateConfig) -> float:
    """Gap büyüklüğüne göre stake çarpanı."""
    if gap >= cfg.gap_extreme_zone:
        return cfg.extreme_gap_multiplier
    if gap >= cfg.gap_high_zone:
        return cfg.high_gap_multiplier
    return 1.0


def _passes_filters(
    gap: float,
    polymarket_price: float,
    bookmaker_prob: float,
    volume: float,
    cfg: GateConfig,
) -> str | None:
    """Tüm filtrelerden geç. None = geçti, string = skip sebebi."""
    if gap < cfg.min_gap_threshold:
        return "GAP_TOO_LOW"
    if polymarket_price < cfg.min_polymarket_price or polymarket_price > cfg.max_entry_price:
        return "PRICE_OUT_OF_RANGE"
    if bookmaker_prob < cfg.min_favorite_probability:
        return "BOOKMAKER_PROB_TOO_LOW"
    if volume < cfg.min_market_volume:
        return "VOLUME_TOO_LOW"
    return None


def _compute_stake(
    bankroll: float,
    confidence: str,
    gap: float,
    win_prob: float,
    cfg: GateConfig,
) -> float:
    """stake = bankroll × confidence_pct × gap_mult × win_prob, hard cap."""
    base_pct = cfg.confidence_a_pct if confidence == "A" else cfg.confidence_b_pct
    mult = _gap_multiplier(gap, cfg)
    raw = bankroll * base_pct * mult * win_prob
    cap = bankroll * cfg.max_bet_pct
    return min(raw, cap, cfg.max_single_bet_usdc)


def _check_event_guard(
    event_id: str | None,
    direction: Direction,
    positions: dict,
    max_per_event: int = 2,
) -> str | None:
    """Aynı event'te pozisyon guard. None = geçti."""
    if not event_id:
        return None
    same_event = [p for p in positions.values() if p.event_id == event_id]
    if len(same_event) >= max_per_event:
        return "EVENT_GUARD_MAX_POSITIONS"
    for pos in same_event:
        if pos.direction == direction:
            return "EVENT_GUARD_SAME_DIRECTION"
    return None


# ── EntryGate orchestration ──────────────────────────────────────

class EntryGate:
    def __init__(
        self,
        config: GateConfig,
        portfolio: Any,
        circuit_breaker: Any,
        cooldown: Any,
        blacklist: Any,
        odds_enricher: Any,
        manipulation_checker: Any,
        cricket_client: Any = None,
    ) -> None:
        self.config = config
        self._portfolio = portfolio
        self._enricher = odds_enricher

    def run(self, markets: list[MarketData]) -> list[GateResult]:
        if not markets:
            return []
        results: list[GateResult] = []
        active = {_normalize(s) for s in self.config.active_sports}
        positions = self._portfolio.positions if self._portfolio else {}
        bankroll = self._portfolio.bankroll() if self._portfolio else 0.0

        for market in markets:
            cid = market.condition_id

            if _normalize(market.sport_tag) not in active:
                results.append(GateResult(cid, skipped_reason="INACTIVE_SPORT"))
                continue

            enrich = self._enricher(market)
            if enrich.probability is None:
                results.append(GateResult(cid, skipped_reason=str(enrich.fail_reason)))
                continue

            prob = enrich.probability
            polymarket_price = market.yes_price
            gap = prob.prob - polymarket_price
            confidence = _classify_confidence(prob.has_sharp, prob.num_bookmakers)

            if confidence == "C":
                results.append(GateResult(cid, skipped_reason="CONFIDENCE_C"))
                continue

            skip = _passes_filters(gap, polymarket_price, prob.prob, market.volume_24h, self.config)
            if skip:
                results.append(GateResult(cid, skipped_reason=skip))
                continue

            direction = Direction.BUY_YES
            guard = _check_event_guard(market.event_id, direction, positions)
            if guard:
                results.append(GateResult(cid, skipped_reason=guard))
                continue

            win_prob = prob.prob if self.config.probability_weighted else 1.0
            stake = _compute_stake(bankroll, confidence, gap, win_prob, self.config)

            if stake < self.config.min_bet_usd:
                results.append(GateResult(cid, skipped_reason="BELOW_MIN_BET"))
                continue

            signal = Signal(
                condition_id=cid,
                direction=direction,
                anchor_probability=prob.prob,
                market_price=polymarket_price,
                confidence=confidence,
                size_usdc=stake,
                entry_reason=EntryReason.NORMAL,
                bookmaker_prob=prob.prob,
                num_bookmakers=prob.num_bookmakers,
                has_sharp=prob.has_sharp,
                sport_tag=market.sport_tag,
                event_id=market.event_id or "",
            )
            results.append(GateResult(cid, signal=signal))

        return results
