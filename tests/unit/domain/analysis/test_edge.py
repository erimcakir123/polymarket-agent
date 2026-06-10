"""edge.py için birim testler (DECISIONS §6.3)."""
from __future__ import annotations

from src.domain.analysis.edge import DEFAULT_CONFIDENCE_MULTIPLIERS, calculate_edge
from src.models.enums import Direction


def test_buy_yes_edge_above_threshold() -> None:
    # anchor 0.70, market 0.55 → raw=0.15, threshold=0.06 → BUY_YES, edge=0.15
    d, edge = calculate_edge(anchor_prob=0.70, market_yes_price=0.55, min_edge=0.06, confidence="B")
    assert d == Direction.BUY_YES
    assert abs(edge - 0.15) < 1e-9


def test_buy_no_edge_above_threshold() -> None:
    # anchor 0.30, market 0.55 → raw=-0.25, abs=0.25 → BUY_NO
    d, edge = calculate_edge(anchor_prob=0.30, market_yes_price=0.55, min_edge=0.06, confidence="B")
    assert d == Direction.BUY_NO
    assert abs(edge - 0.25) < 1e-9


def test_edge_below_threshold_returns_hold() -> None:
    # raw 0.03 < threshold 0.06 → SKIP
    d, edge = calculate_edge(anchor_prob=0.53, market_yes_price=0.50, min_edge=0.06, confidence="B")
    assert d == Direction.SKIP
    assert edge == 0.0


def test_confidence_A_same_threshold_as_B() -> None:
    """2026-05-15 rollback: A çarpanı 1.00 (ceza yok) — 2026-06-10'da koda eşitlendi.

    threshold = 0.05 × 1.00 = 0.05; raw 0.055 → BUY_YES (eski 1.25 ile SKIP olurdu).
    """
    d, _ = calculate_edge(anchor_prob=0.555, market_yes_price=0.50, min_edge=0.05, confidence="A")
    assert d == Direction.BUY_YES
    # raw 0.03 < 0.05 → eşik hâlâ çalışıyor
    d2, _ = calculate_edge(anchor_prob=0.53, market_yes_price=0.50, min_edge=0.05, confidence="A")
    assert d2 == Direction.SKIP


def test_spread_and_slippage_reduce_edge() -> None:
    # raw 0.10, spread+slippage 0.03, effective 0.07 > threshold 0.06 → BUY_YES
    d, edge = calculate_edge(
        anchor_prob=0.60, market_yes_price=0.50,
        min_edge=0.06, confidence="B",
        spread=0.02, slippage=0.01,
    )
    assert d == Direction.BUY_YES
    assert abs(edge - 0.07) < 1e-9


def test_spread_makes_edge_insufficient() -> None:
    # raw 0.08, cost 0.05, effective 0.03 < threshold 0.06 → HOLD
    d, edge = calculate_edge(
        anchor_prob=0.58, market_yes_price=0.50,
        min_edge=0.06, confidence="B",
        spread=0.03, slippage=0.02,
    )
    assert d == Direction.SKIP
    assert edge == 0.0


def test_raw_zero_returns_hold() -> None:
    d, _ = calculate_edge(anchor_prob=0.50, market_yes_price=0.50, min_edge=0.06, confidence="B")
    assert d == Direction.SKIP


def test_default_multipliers_only_A_and_B() -> None:
    assert "A" in DEFAULT_CONFIDENCE_MULTIPLIERS
    assert "B" in DEFAULT_CONFIDENCE_MULTIPLIERS
    # 2026-05-15 rollback: A cezası kaldırıldı (1.25 → 1.00), DECISIONS §6.3
    assert DEFAULT_CONFIDENCE_MULTIPLIERS["A"] == 1.00
    assert DEFAULT_CONFIDENCE_MULTIPLIERS["B"] == 1.00
    # C blocked — no multiplier
    assert "C" not in DEFAULT_CONFIDENCE_MULTIPLIERS
