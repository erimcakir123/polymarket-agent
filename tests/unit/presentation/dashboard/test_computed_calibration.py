"""computed_calibration.py spor filtresi için birim testler — SPEC 2026-06-07.

Pure derivation: trade listesi → bin başına calibration + available_sports.
30-trade eşiği değişmez; sport param "all"/branş süzme + dinamik sekme listesi.
"""
from __future__ import annotations

from typing import Any

from src.presentation.dashboard import computed_calibration


def _trade(sport_tag: str, anchor: float, pnl: float) -> dict[str, Any]:
    """Calibration'ın saydığı minimal resolved trade (exit_price + exit_pnl dolu)."""
    return {
        "sport_tag": sport_tag,
        "anchor_probability": anchor,
        "direction": "BUY_YES",
        "exit_price": 0.5,
        "exit_pnl_usdc": pnl,
    }


def test_calibration_report_sport_all_returns_available_sports() -> None:
    trades = (
        [_trade("tennis", 0.70, 1.0) for _ in range(3)]
        + [_trade("basketball_nba", 0.70, 1.0) for _ in range(2)]
    )
    out = computed_calibration.calibration_report(trades, sport="all")
    assert out["selected_sport"] == "all"
    assert out["available_sports"] == ["basketball", "tennis"]


def test_calibration_report_sport_filter_excludes_other_sports() -> None:
    # 30 tennis "net favori" win + 30 basketball "net favori" loss.
    trades = (
        [_trade("tennis", 0.70, 1.0) for _ in range(30)]
        + [_trade("basketball_nba", 0.70, -1.0) for _ in range(30)]
    )
    out = computed_calibration.calibration_report(trades, sport="tennis")
    net = next(b for b in out["bins"] if b["bin"] == "net_favori")
    assert net["n"] == 30  # sadece tennis sayıldı
    assert net["actual_pct"] == 100.0  # tennis hepsi win; basketball karışmadı


def test_calibration_report_unknown_sport_returns_empty_bins() -> None:
    trades = [_trade("tennis", 0.70, 1.0) for _ in range(30)]
    out = computed_calibration.calibration_report(trades, sport="cricket")
    assert all(b["n"] == 0 for b in out["bins"])
    assert out["total_trades"] == 0


def test_calibration_report_missing_sport_tag_excluded_from_available() -> None:
    trades = (
        [_trade("tennis", 0.70, 1.0) for _ in range(2)]
        + [_trade("", 0.70, 1.0) for _ in range(2)]
    )
    out = computed_calibration.calibration_report(trades, sport="all")
    assert "unknown" not in out["available_sports"]
    assert out["available_sports"] == ["tennis"]


def test_calibration_report_total_trades_counts_pending_bins() -> None:
    # 5 trade (30 esik altinda = pending) yine total_trades'e sayilir.
    trades = [_trade("tennis", 0.70, 1.0) for _ in range(5)]
    out = computed_calibration.calibration_report(trades, sport="all")
    assert out["total_trades"] == 5
    assert all(b["status"] == "pending" for b in out["bins"] if b["n"] > 0)


def test_calibration_report_default_sport_is_all() -> None:
    trades = [_trade("tennis", 0.70, 1.0) for _ in range(3)]
    out = computed_calibration.calibration_report(trades)
    assert out["selected_sport"] == "all"
