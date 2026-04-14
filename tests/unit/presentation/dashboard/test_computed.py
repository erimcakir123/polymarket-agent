"""computed.py için birim testler — pure derivations."""
from __future__ import annotations

from pathlib import Path

from src.presentation.dashboard import computed


# ── Katman ihlali kontrolü ──

def test_computed_module_has_no_layer_imports() -> None:
    path = Path(computed.__file__)
    source = path.read_text(encoding="utf-8")
    for forbidden in (
        "from src.infrastructure", "import src.infrastructure",
        "from src.domain", "import src.domain",
        "from src.strategy", "import src.strategy",
        "from src.orchestration", "import src.orchestration",
    ):
        assert forbidden not in source, f"Layer violation: {forbidden}"


# ── equity_summary ──

def test_equity_summary_empty_positions() -> None:
    blob = {"positions": {}, "realized_pnl": 0.0, "high_water_mark": 1000.0}
    out = computed.equity_summary(blob, initial_bankroll=1000.0)
    assert out["bankroll"] == 1000.0
    assert out["open_pnl"] == 0.0
    assert out["locked"] == 0.0
    assert out["peak_balance"] == 1000.0
    assert out["position_count"] == 0


def test_equity_summary_single_buy_yes_position_profit() -> None:
    blob = {
        "positions": {
            "k1": {
                "direction": "BUY_YES", "entry_price": 0.40,
                "current_price": 0.60, "shares": 100.0, "size_usdc": 40.0,
            }
        },
        "realized_pnl": 50.0,
    }
    # history'deki en yüksek total_equity = 1100
    history = [{"bankroll": 1060.0, "invested": 0.0, "unrealized_pnl": 40.0}]
    out = computed.equity_summary(blob, initial_bankroll=1000.0, equity_history=history)
    # shares * eff - size = 100 * 0.60 - 40 = 20
    assert out["open_pnl"] == 20.0
    assert out["locked"] == 40.0
    assert out["realized_pnl"] == 50.0
    assert out["peak_balance"] == 1100.0
    assert out["bankroll"] == 1010.0


def test_equity_summary_buy_no_token_native() -> None:
    blob = {
        "positions": {
            "k1": {
                "direction": "BUY_NO", "entry_price": 0.55,
                "current_price": 0.40, "shares": 100.0, "size_usdc": 45.0,
            }
        },
        "realized_pnl": 0.0,
        "high_water_mark": 1000.0,
    }
    out = computed.equity_summary(blob, initial_bankroll=1000.0)
    # Token-native: NO token 0.55'te satın alındı (45$ = 45/0.55=81.8 share), şimdi 0.40.
    # open_pnl = shares * current_price - size = 100 * 0.40 - 45 = -5
    assert out["open_pnl"] == -5.0


def test_equity_summary_drawdown_calculation() -> None:
    blob = {"positions": {}, "realized_pnl": -100.0}
    # Geçmişte total_equity 1100 olmuş; şimdi 900 → dd = 200/1100 = 18.18%
    history = [{"bankroll": 1100.0, "invested": 0.0, "unrealized_pnl": 0.0}]
    out = computed.equity_summary(blob, initial_bankroll=1000.0, equity_history=history)
    assert round(out["drawdown_pct"], 2) == 18.18


def test_equity_summary_drawdown_zero_when_at_peak() -> None:
    blob = {"positions": {}, "realized_pnl": 0.0, "high_water_mark": 1000.0}
    out = computed.equity_summary(blob, initial_bankroll=1000.0)
    assert out["drawdown_pct"] == 0.0


# ── slots_summary ──

def test_slots_summary_empty() -> None:
    blob = {"positions": {}}
    out = computed.slots_summary(blob, max_positions=20)
    assert out == {"current": 0, "max": 20, "by_reason": {}}


def test_slots_summary_counts_by_entry_reason() -> None:
    blob = {
        "positions": {
            "a": {"entry_reason": "normal"},
            "b": {"entry_reason": "normal"},
            "c": {"entry_reason": "consensus"},
            "d": {"entry_reason": "volatility_swing"},
        }
    }
    out = computed.slots_summary(blob, max_positions=20)
    assert out["current"] == 4
    assert out["by_reason"]["normal"] == 2
    assert out["by_reason"]["consensus"] == 1
    assert out["by_reason"]["volatility_swing"] == 1


def test_slots_summary_missing_reason_defaults_to_normal() -> None:
    blob = {"positions": {"a": {}}}
    out = computed.slots_summary(blob, max_positions=10)
    assert out["by_reason"] == {"normal": 1}


# ── loss_protection ──

def test_loss_protection_safe_when_drawdown_small() -> None:
    blob = {"positions": {}, "realized_pnl": -20.0, "high_water_mark": 1000.0}
    out = computed.loss_protection(blob, initial_bankroll=1000.0, stop_at_pct=50.0)
    assert out["status"] == "Safe"
    assert out["stop_at_pct"] == 50.0


def test_loss_protection_caution_at_medium_drawdown() -> None:
    blob = {"positions": {}, "realized_pnl": -160.0, "high_water_mark": 1000.0}
    out = computed.loss_protection(blob, initial_bankroll=1000.0, stop_at_pct=50.0)
    assert out["status"] == "Caution"  # 16% >= 15%


def test_loss_protection_warning_at_heavy_drawdown() -> None:
    blob = {"positions": {}, "realized_pnl": -350.0, "high_water_mark": 1000.0}
    out = computed.loss_protection(blob, initial_bankroll=1000.0, stop_at_pct=50.0)
    assert out["status"] == "Warning"  # 35% >= 30%


def test_loss_protection_stopped_at_threshold() -> None:
    blob = {"positions": {}, "realized_pnl": -520.0, "high_water_mark": 1000.0}
    out = computed.loss_protection(blob, initial_bankroll=1000.0, stop_at_pct=50.0)
    assert out["status"] == "Stopped"


def test_loss_protection_risk_pct_relative_to_stop() -> None:
    blob = {"positions": {}, "realized_pnl": -100.0, "high_water_mark": 1000.0}
    out = computed.loss_protection(blob, initial_bankroll=1000.0, stop_at_pct=50.0)
    # down = 10% of 1000; risk = 10/50 = 20%
    assert out["down_pct"] == 10.0
    assert out["risk_pct"] == 20.0


def test_loss_protection_honors_custom_safe_warn_thresholds() -> None:
    # 10% drawdown ile default (15/30) → Safe; ama safe=5 verilirse Caution
    blob = {"positions": {}, "realized_pnl": -100.0}
    out = computed.loss_protection(
        blob, initial_bankroll=1000.0, stop_at_pct=50.0,
        safe_drawdown_pct=5.0, warn_drawdown_pct=25.0,
    )
    assert out["status"] == "Caution"  # 10% >= 5% safe → Caution


def test_loss_protection_honors_custom_warn_threshold() -> None:
    blob = {"positions": {}, "realized_pnl": -220.0}
    out = computed.loss_protection(
        blob, initial_bankroll=1000.0, stop_at_pct=50.0,
        safe_drawdown_pct=10.0, warn_drawdown_pct=20.0,
    )
    assert out["status"] == "Warning"  # 22% >= 20% warn → Warning


# ── closed_trades ──

def test_closed_trades_filters_open() -> None:
    trades = [
        {"slug": "a", "exit_price": 0.60, "exit_timestamp": "2026-04-14T10:00Z"},
        {"slug": "b", "exit_price": None, "exit_timestamp": ""},
        {"slug": "c", "exit_price": 0.45, "exit_timestamp": "2026-04-14T12:00Z"},
    ]
    out = computed.closed_trades(trades)
    assert len(out) == 2
    assert out[0]["slug"] == "c"  # newest first
    assert out[1]["slug"] == "a"


# ── _position_unrealized (token-native, direction-agnostic) ──

def test_position_unrealized_buy_yes_profit() -> None:
    """BUY_YES: shares × current_price − size."""
    pos = {"shares": 100.0, "current_price": 0.50, "size_usdc": 40.0, "direction": "BUY_YES"}
    assert computed._position_unrealized(pos) == 10.0


def test_position_unrealized_buy_yes_loss() -> None:
    """BUY_YES: current_price azalınca loss."""
    pos = {"shares": 100.0, "current_price": 0.30, "size_usdc": 40.0, "direction": "BUY_YES"}
    assert computed._position_unrealized(pos) == -10.0


def test_position_unrealized_buy_no_profit_when_no_rises() -> None:
    """BUY_NO token fiyatı yükselince profit (NO dolar değeri artıyor)."""
    pos = {"shares": 100.0, "current_price": 0.60, "size_usdc": 40.0, "direction": "BUY_NO"}
    assert computed._position_unrealized(pos) == 20.0


def test_position_unrealized_buy_no_loss_when_no_drops() -> None:
    """BUY_NO token fiyatı düşünce loss."""
    pos = {"shares": 100.0, "current_price": 0.30, "size_usdc": 40.0, "direction": "BUY_NO"}
    assert computed._position_unrealized(pos) == -10.0


def test_position_unrealized_buy_yes_zero_at_entry() -> None:
    """Entry fiyatında PnL=0."""
    pos = {"shares": 100.0, "current_price": 0.40, "size_usdc": 40.0, "direction": "BUY_YES"}
    assert computed._position_unrealized(pos) == 0.0


def test_position_unrealized_buy_no_zero_at_entry() -> None:
    """BUY_NO da entry fiyatında PnL=0."""
    pos = {"shares": 100.0, "current_price": 0.40, "size_usdc": 40.0, "direction": "BUY_NO"}
    assert computed._position_unrealized(pos) == 0.0
