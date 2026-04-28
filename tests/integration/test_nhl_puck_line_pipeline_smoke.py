"""NHL puck line pipeline smoke — gate filter + monitor dispatch."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.models.market import MarketData
from src.strategy.entry.gate import EntryGate, GateConfig


def _make_nhl_puck_line_market(
    yes_price: float = 0.50,
    volume_24h: float = 4000.0,
    condition_id: str = "nhl_pl_001",
) -> MarketData:
    return MarketData(
        condition_id=condition_id,
        question="Will the Boston Bruins cover -1.5 vs Buffalo Sabres?",
        slug=f"slug-{condition_id}",
        yes_token_id=f"tok_yes_{condition_id}",
        no_token_id=f"tok_no_{condition_id}",
        yes_price=yes_price,
        no_price=1.0 - yes_price,
        liquidity=5000.0,
        volume_24h=volume_24h,
        end_date_iso="2026-06-01T00:00:00Z",
        match_start_iso=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        event_id="evt_bos_buf",
        sport_tag="nhl",
        sports_market_type="spreads",
    )


def _make_gate() -> EntryGate:
    cfg = GateConfig(
        active_sports=["icehockey_nhl"],
        min_favorite_probability=0.50,
        max_entry_price=0.80,
        max_positions=10,
        max_exposure_pct=0.50,
        hard_cap_overflow_pct=0.02,
        min_entry_size_pct=0.015,
        confidence_bet_pct={"A": 0.05, "B": 0.03},
        max_single_bet_usdc=100.0,
        max_bet_pct=0.05,
        probability_weighted=True,
        min_bookmakers=1,
        min_sharps=0,
        min_gap_threshold=0.05,
        min_market_volume=3000.0,
        min_polymarket_price=0.20,
        nhl_puck_line_min_price=0.20,
        nhl_puck_line_max_price=0.80,
        nhl_puck_line_min_volume=3000.0,
    )
    portfolio = MagicMock()
    portfolio.positions = {}
    portfolio.bankroll = 1000.0

    odds_result = MagicMock()
    odds_result.probability = MagicMock(probability=0.62, has_sharp=True, num_bookmakers=18.0)
    odds_result.fail_reason = None
    odds_fn = MagicMock(return_value=odds_result)

    return EntryGate(
        config=cfg, portfolio=portfolio,
        circuit_breaker=None, cooldown=None, blacklist=None,
        odds_enricher=odds_fn, manipulation_checker=None,
        edge_enricher=None, nhl_edge_enricher=None,
    )


class TestNhlPuckLinePipelineSmoke:
    def test_nhl_puck_line_market_passes_filter(self):
        gate = _make_gate()
        market = _make_nhl_puck_line_market()
        results = gate.run([market])
        assert len(results) == 1
        assert results[0].skipped_reason not in ("INACTIVE_SPORT", "PRICE_OUT_OF_RANGE", "VOLUME_TOO_LOW")

    def test_nhl_puck_line_price_out_of_range_rejected(self):
        gate = _make_gate()
        market = _make_nhl_puck_line_market(yes_price=0.10)
        results = gate.run([market])
        assert results[0].skipped_reason == "PRICE_OUT_OF_RANGE"

    def test_nhl_puck_line_volume_too_low_rejected(self):
        gate = _make_gate()
        market = _make_nhl_puck_line_market(volume_24h=1000.0)
        results = gate.run([market])
        assert results[0].skipped_reason == "VOLUME_TOO_LOW"
