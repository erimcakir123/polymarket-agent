"""Entry gate — gap-based NBA entry kararı."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.config.sport_rules import _normalize
from src.strategy.entry._match_status import is_match_likely_finished
from src.domain.guards.manipulation import adjust_position_size
from src.domain.matching.market_line_parser import parse_home_away_side, parse_spread_line, parse_total_line
from src.domain.matching.team_resolver import resolve_nba_espn_id
from src.models.enums import Direction, EntryReason
from src.models.signal import Signal
from src.strategy.enrichment.question_parser import extract_teams
from src.strategy.entry._nhl_edge import apply_nhl_edge_modifiers
from src.strategy.entry._gate_helpers import (
    _classify_confidence,
    _gap_multiplier,
    _passes_filters,
    _compute_stake,
    _check_event_guard,
)

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
    # NHL-specific edge modifiers
    nhl_b2b_opponent_gap_bonus: float = field(default=0.02)
    nhl_b2b_opponent_size_mult: float = field(default=1.10)
    nhl_b2b_self_gap_bonus: float = field(default=0.02)
    nhl_require_goalie_confirmation: bool = field(default=True)
    # NHL Puck Line filters
    nhl_puck_line_min_price: float = field(default=0.20)
    nhl_puck_line_max_price: float = field(default=0.80)
    nhl_puck_line_min_volume: float = field(default=3000.0)
    # NHL Totals filters
    nhl_totals_min_price: float = field(default=0.20)
    nhl_totals_max_price: float = field(default=0.80)
    nhl_totals_min_target_total: float = field(default=4.5)
    nhl_totals_min_volume: float = field(default=3000.0)


@dataclass
class GateResult:
    condition_id: str
    signal: Signal | None = None
    skipped_reason: str | None = None
    skip_detail: str | None = None
    anchor_probability: float = 0.0
    gap: float | None = None


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
        edge_enricher: Any = None,
        nhl_edge_enricher: Any = None,
    ) -> None:
        self.config = config
        self._portfolio = portfolio
        self._circuit_breaker = circuit_breaker
        self._cooldown = cooldown
        self._blacklist = blacklist
        self._enricher = odds_enricher
        self._manipulation_checker = manipulation_checker
        self._edge_enricher = edge_enricher
        self._nhl_edge_enricher = nhl_edge_enricher

    def run(self, markets: list[MarketData]) -> list[GateResult]:
        if not markets:
            return []

        # Global safety: circuit breaker (PRD §270, DECISIONS.md soft block)
        if self._circuit_breaker is not None and self._portfolio is not None:
            portfolio_value = self._portfolio.bankroll + self._portfolio.total_invested()
            halt, halt_reason = self._circuit_breaker.should_halt_entries(portfolio_value=portfolio_value)
            if halt:
                return [
                    GateResult(m.condition_id, skipped_reason="CIRCUIT_BREAKER_ACTIVE", skip_detail=halt_reason)
                    for m in markets
                ]

        # Global safety: cooldown (consecutive losses)
        if self._cooldown is not None and self._cooldown.is_active():
            return [
                GateResult(m.condition_id, skipped_reason="COOLDOWN_ACTIVE")
                for m in markets
            ]

        results: list[GateResult] = []
        active = {_normalize(s) for s in self.config.active_sports}
        positions = self._portfolio.positions if self._portfolio else {}
        bankroll = self._portfolio.bankroll if self._portfolio else 0.0

        for market in markets:
            cid = market.condition_id

            # Bitmiş maç kontrolü — instant entry/exit pattern'ini engelle.
            # Bu kontrol ucuz ve INACTIVE_SPORT'tan önce çalışır (sport bağımsız).
            finished, finish_reason = is_match_likely_finished(
                market.match_start_iso or "", market.sport_tag,
            )
            if finished:
                results.append(GateResult(
                    cid, skipped_reason="MATCH_FINISHED", skip_detail=finish_reason,
                ))
                continue

            if _normalize(market.sport_tag) not in active:
                results.append(GateResult(cid, skipped_reason="INACTIVE_SPORT"))
                continue

            # Per-market safety: blacklist
            if self._blacklist is not None and self._blacklist.is_blacklisted(
                condition_id=cid, event_id=market.event_id or "",
            ):
                results.append(GateResult(cid, skipped_reason="BLACKLISTED"))
                continue

            # Per-market safety: manipulation check
            manip_check = None
            if self._manipulation_checker is not None:
                manip_check = self._manipulation_checker(
                    market.question, market.liquidity,
                )
                if manip_check.risk_level == "high":
                    results.append(GateResult(
                        cid, skipped_reason="MANIPULATION_HIGH",
                        skip_detail=", ".join(manip_check.flags),
                    ))
                    continue

            enrich = self._enricher(market)
            if enrich.probability is None:
                results.append(GateResult(cid, skipped_reason=str(enrich.fail_reason)))
                continue

            prob = enrich.probability
            polymarket_price = market.yes_price
            gap = prob.probability - polymarket_price
            confidence = _classify_confidence(prob.has_sharp, prob.num_bookmakers)

            if confidence == "C":
                results.append(GateResult(cid, skipped_reason="CONFIDENCE_C"))
                continue

            # --- Edge context adjustments ---
            effective_gap_threshold_adj, size_multiplier_adj = self._apply_edge_modifiers(market, cid)

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
                gap, polymarket_price, prob.probability, market.volume_24h, self.config,
                market_type=market_type,
                spread_line=spread_line,
                total_line=total_line,
                gap_threshold_adj=effective_gap_threshold_adj,
                sport_tag=market.sport_tag,
            )
            if skip:
                results.append(GateResult(
                    cid, skipped_reason=skip,
                    anchor_probability=prob.probability, gap=gap,
                ))
                continue

            direction = Direction.BUY_YES
            guard = _check_event_guard(market.event_id, market_type, direction, positions)
            if guard:
                results.append(GateResult(cid, skipped_reason=guard))
                continue

            win_prob = prob.probability if self.config.probability_weighted else 1.0
            stake = _compute_stake(bankroll, confidence, gap, win_prob, self.config)
            stake = min(stake * size_multiplier_adj, self.config.max_single_bet_usdc)

            # Manipulation medium → 50% reduce (high zaten skip edilmişti Task 1.5'te)
            if manip_check is not None and manip_check.risk_level == "medium":
                stake = adjust_position_size(stake, manip_check)

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
                anchor_probability=prob.probability,
                market_price=polymarket_price,
                confidence=confidence,
                size_usdc=stake,
                entry_reason=EntryReason.NORMAL,
                bookmaker_prob=prob.probability,
                num_bookmakers=prob.num_bookmakers,
                has_sharp=prob.has_sharp,
                sport_tag=market.sport_tag,
                event_id=market.event_id or "",
                sports_market_type=market_type,
                spread_line=spread_line,
                total_line=total_line,
                total_side=actual_total_side,
                home_away_side=parse_home_away_side(market.slug),
            )
            results.append(GateResult(cid, signal=signal))

        return results

    def _apply_edge_modifiers(
        self,
        market: Any,
        cid: str,
    ) -> tuple[float, float]:
        """Apply sport-specific edge modifiers to gap threshold and sizing multiplier.

        Returns (gap_threshold_adj, size_multiplier_adj).
        """
        sport_tag = (getattr(market, "sport_tag", "") or "").lower()
        if sport_tag == "nhl":
            return apply_nhl_edge_modifiers(market, self._nhl_edge_enricher, self.config)

        # NBA / default path — behaviour unchanged
        gap_threshold_adj: float = 0.0
        size_multiplier_adj: float = 1.0

        if self._edge_enricher is None:
            return gap_threshold_adj, size_multiplier_adj

        try:
            _team_a, _team_b = extract_teams(market.question)
            _our_id = resolve_nba_espn_id(_team_a or "")
            _opp_id = resolve_nba_espn_id(_team_b or "")
            edge_ctx = self._edge_enricher.enrich(market, our_team_id=_our_id, opp_team_id=_opp_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("EdgeEnricher failed for %s: %s", cid, exc)
            return gap_threshold_adj, size_multiplier_adj

        if edge_ctx is not None:
            if edge_ctx.has_recent_injury:
                if edge_ctx.is_own_team_injury:
                    gap_threshold_adj += self.config.star_out_self_gap_bonus
                else:
                    gap_threshold_adj -= self.config.injury_gap_threshold_drop
                    size_multiplier_adj *= self.config.injury_size_multiplier

            if edge_ctx.is_opponent_back_to_back:
                gap_threshold_adj += self.config.b2b_opponent_gap_bonus

            if edge_ctx.is_our_back_to_back:
                gap_threshold_adj += self.config.b2b_self_gap_bonus

        return gap_threshold_adj, size_multiplier_adj
