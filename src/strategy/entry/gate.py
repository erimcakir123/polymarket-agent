"""Entry gate — gap-based NBA entry kararı."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.config.sport_rules import _normalize
from src.domain.matching.market_line_parser import parse_spread_line, parse_total_line
from src.domain.matching.team_resolver import resolve_nba_espn_id
from src.models.enums import Direction, EntryReason
from src.models.signal import Signal
from src.strategy.enrichment.question_parser import extract_teams

if TYPE_CHECKING:
    from src.models.market import MarketData

logger = logging.getLogger(__name__)


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
    # Spread filters
    spread_min_price: float = field(default=0.20)
    spread_max_price: float = field(default=0.80)
    spread_large_threshold: float = field(default=10.0)
    spread_gap_bonus: float = field(default=0.02)
    # Totals filters
    totals_min_price: float = field(default=0.20)
    totals_max_price: float = field(default=0.80)
    totals_min_target_total: float = field(default=200.0)
    # Edge modifiers — injury + B2B gap adjustments
    injury_gap_threshold_drop: float = field(default=0.02)
    injury_size_multiplier: float = field(default=1.3)
    b2b_opponent_gap_bonus: float = field(default=0.03)
    b2b_self_gap_bonus: float = field(default=0.05)
    star_out_self_gap_bonus: float = field(default=0.05)


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
    market_type: str = "moneyline",
    spread_line: float | None = None,
    total_line: float | None = None,
    gap_threshold_adj: float = 0.0,
) -> str | None:
    """Tüm filtrelerden geç. None = geçti, string = skip sebebi."""
    effective_gap_threshold = max(0.0, cfg.min_gap_threshold + gap_threshold_adj)
    if market_type == "spreads" and spread_line is not None and spread_line >= cfg.spread_large_threshold:
        effective_gap_threshold += cfg.spread_gap_bonus

    if gap < effective_gap_threshold:
        return "GAP_TOO_LOW"

    if market_type == "spreads":
        if polymarket_price < cfg.spread_min_price or polymarket_price > cfg.spread_max_price:
            return "PRICE_OUT_OF_RANGE"
    elif market_type == "totals":
        if polymarket_price < cfg.totals_min_price or polymarket_price > cfg.totals_max_price:
            return "PRICE_OUT_OF_RANGE"
        if total_line is not None and total_line < cfg.totals_min_target_total:
            return "TOTAL_TOO_LOW"
    else:  # moneyline
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
    market_type: str,
    direction: Direction,
    positions: dict,
    max_per_event: int = 2,
) -> str | None:
    """Event-level pozisyon guard. None = geçti.

    Block: aynı market_type + aynı event.
    Block: ML + Spread aynı yön (yüksek korelasyon).
    Allow: ML + Totals veya Spread + Totals (bağımsız sonuçlar).
    """
    if not event_id:
        return None
    same_event = [p for p in positions.values() if p.event_id == event_id]
    if len(same_event) >= max_per_event:
        return "EVENT_GUARD_MAX_POSITIONS"
    norm_type = market_type or "moneyline"
    for pos in same_event:
        pos_type = pos.sports_market_type or "moneyline"
        if pos_type == norm_type:
            return "EVENT_GUARD_SAME_MARKET_TYPE"
        ml_spread = frozenset({"moneyline", "spreads"})
        if frozenset({pos_type, norm_type}) == ml_spread and pos.direction == direction:
            return "EVENT_GUARD_ML_SPREAD_CORRELATED"
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
        edge_enricher: Any = None,
    ) -> None:
        self.config = config
        self._portfolio = portfolio
        self._enricher = odds_enricher
        self._edge_enricher = edge_enricher

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

            # --- Edge context adjustments ---
            edge_ctx: Any = None
            if self._edge_enricher is not None:
                try:
                    _team_a, _team_b = extract_teams(market.question)
                    _our_id = resolve_nba_espn_id(_team_a or "")
                    _opp_id = resolve_nba_espn_id(_team_b or "")
                    edge_ctx = self._edge_enricher.enrich(market, our_team_id=_our_id, opp_team_id=_opp_id)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("EdgeEnricher failed for %s: %s", cid, exc)

            effective_gap_threshold_adj: float = 0.0
            size_multiplier_adj: float = 1.0

            if edge_ctx is not None:
                if edge_ctx.has_recent_injury:
                    if edge_ctx.is_own_team_injury:
                        effective_gap_threshold_adj += self.config.star_out_self_gap_bonus
                    else:
                        effective_gap_threshold_adj -= self.config.injury_gap_threshold_drop
                        size_multiplier_adj *= self.config.injury_size_multiplier

                if edge_ctx.is_opponent_back_to_back:
                    effective_gap_threshold_adj += self.config.b2b_opponent_gap_bonus

                if edge_ctx.is_our_back_to_back:
                    effective_gap_threshold_adj += self.config.b2b_self_gap_bonus

            # Market line parse (spread/totals için; moneyline'da None kalır)
            market_type = market.sports_market_type or "moneyline"
            spread_line: float | None = None
            total_line: float | None = None
            total_side_val: str | None = None

            if market_type == "spreads":
                spread_line = parse_spread_line(market.question)
                if spread_line is None:
                    results.append(GateResult(cid, skipped_reason="SPREAD_UNPARSEABLE"))
                    continue

            elif market_type == "totals":
                parsed = parse_total_line(market.question)
                if parsed is None:
                    results.append(GateResult(cid, skipped_reason="TOTAL_UNPARSEABLE"))
                    continue
                total_line, yes_side = parsed
                total_side_val = yes_side

            skip = _passes_filters(
                gap, polymarket_price, prob.prob, market.volume_24h, self.config,
                market_type=market_type,
                spread_line=spread_line,
                total_line=total_line,
                gap_threshold_adj=effective_gap_threshold_adj,
            )
            if skip:
                results.append(GateResult(cid, skipped_reason=skip))
                continue

            direction = Direction.BUY_YES
            guard = _check_event_guard(market.event_id, market_type, direction, positions)
            if guard:
                results.append(GateResult(cid, skipped_reason=guard))
                continue

            win_prob = prob.prob if self.config.probability_weighted else 1.0
            stake = _compute_stake(bankroll, confidence, gap, win_prob, self.config)
            stake = min(stake * size_multiplier_adj, self.config.max_single_bet_usdc)

            if stake < self.config.min_bet_usd:
                results.append(GateResult(cid, skipped_reason="BELOW_MIN_BET"))
                continue

            # BUY_NO totals → side flip (YES=over convention, BUY_NO=under)
            actual_total_side = total_side_val
            if market_type == "totals" and direction == Direction.BUY_NO and total_side_val:
                actual_total_side = "under" if total_side_val == "over" else "over"

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
                sports_market_type=market_type,
                spread_line=spread_line,
                total_line=total_line,
                total_side=actual_total_side,
            )
            results.append(GateResult(cid, signal=signal))

        return results
