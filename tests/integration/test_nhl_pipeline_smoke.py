"""NHL pipeline smoke test — Task 4A.

Scanner → Gate akışı: gerçek API yok, mock data.
Crash yok + NHL path dispatch doğrulama.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from src.models.market import MarketData
from src.strategy.entry.gate import EntryGate, GateConfig


def _make_nhl_market(
    condition_id: str = "nhl_cid_001",
    yes_price: float = 0.42,
    volume_24h: float = 8_000.0,
) -> MarketData:
    match_start = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    return MarketData(
        condition_id=condition_id,
        question="Will the Boston Bruins beat the Buffalo Sabres?",
        slug=f"slug-{condition_id}",
        yes_token_id=f"tok_yes_{condition_id}",
        no_token_id=f"tok_no_{condition_id}",
        yes_price=yes_price,
        no_price=1.0 - yes_price,
        liquidity=6_000.0,
        volume_24h=volume_24h,
        end_date_iso="2026-06-01T00:00:00Z",
        match_start_iso=match_start,
        event_id="evt_bos_buf",
        sport_tag="nhl",
        sports_market_type="moneyline",
    )


def _make_nhl_gate(bankroll: float = 1000.0) -> EntryGate:
    cfg = GateConfig(
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
        active_sports=["basketball_nba", "icehockey_nhl"],
        min_gap_threshold=0.05,
        min_market_volume=5_000.0,
        min_polymarket_price=0.10,
        nhl_b2b_opponent_gap_bonus=0.02,
        nhl_b2b_opponent_size_mult=1.10,
        nhl_b2b_self_gap_bonus=0.02,
        nhl_require_goalie_confirmation=True,
    )

    mock_portfolio = MagicMock()
    mock_portfolio.positions = {}
    mock_portfolio.bankroll = bankroll

    mock_prob = MagicMock()
    mock_prob.probability = 0.62
    mock_prob.has_sharp = True
    mock_prob.num_bookmakers = 18.0

    mock_result = MagicMock()
    mock_result.probability = mock_prob
    mock_result.fail_reason = None

    mock_odds_fn = MagicMock(return_value=mock_result)

    return EntryGate(
        config=cfg,
        portfolio=mock_portfolio,
        circuit_breaker=None,
        cooldown=None,
        blacklist=None,
        odds_enricher=mock_odds_fn,
        manipulation_checker=None,
        edge_enricher=None,
        nhl_edge_enricher=None,
    )


class TestNhlPipelineSmoke:
    def test_nhl_market_passes_active_sports_filter(self):
        """icehockey_nhl active_sports'ta → gate INACTIVE_SPORT vermez."""
        gate = _make_nhl_gate()
        market = _make_nhl_market()
        results = gate.run([market])
        assert len(results) == 1
        assert results[0].condition_id == "nhl_cid_001"
        assert results[0].skipped_reason != "INACTIVE_SPORT"

    def test_nhl_gate_dispatches_nhl_edge_path(self):
        """NHL market → _apply_edge_modifiers NHL branch çağrılır (apply_nhl_edge_modifiers)."""
        gate = _make_nhl_gate()
        market = _make_nhl_market()
        with patch("src.strategy.entry.gate.apply_nhl_edge_modifiers", return_value=(0.0, 1.0)) as mock_nhl:
            gate.run([market])
        mock_nhl.assert_called_once()

    def test_nhl_gate_produces_decision_without_crash(self):
        """NHL market end-to-end: gate karar üretiyor, exception yok."""
        gate = _make_nhl_gate()
        market = _make_nhl_market()
        results = gate.run([market])
        assert len(results) == 1
        r = results[0]
        # Ya entry signal ya skip — ikisi de geçerli, crash olmadı
        assert r.condition_id == "nhl_cid_001"
        assert r.skipped_reason is not None or r.signal is not None

    def test_nba_market_still_passes_alongside_nhl(self):
        """NBA + NHL birlikte active_sports'ta → her ikisi de gate'ten geçer."""
        gate = _make_nhl_gate()
        nhl_market = _make_nhl_market(condition_id="nhl_001")
        nba_market = MarketData(
            condition_id="nba_001",
            question="Will the Lakers beat the Celtics?",
            slug="slug-nba-001",
            yes_token_id="tok_yes_nba",
            no_token_id="tok_no_nba",
            yes_price=0.55,
            no_price=0.45,
            liquidity=8_000.0,
            volume_24h=12_000.0,
            end_date_iso="2026-06-01T00:00:00Z",
            match_start_iso=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            event_id="evt_lal_bos",
            sport_tag="basketball_nba",
            sports_market_type="moneyline",
        )
        results = gate.run([nhl_market, nba_market])
        cids = {r.condition_id for r in results}
        assert "nhl_001" in cids
        assert "nba_001" in cids
        # NBA INACTIVE_SPORT almamalı
        nba_result = next(r for r in results if r.condition_id == "nba_001")
        assert nba_result.skipped_reason != "INACTIVE_SPORT"
