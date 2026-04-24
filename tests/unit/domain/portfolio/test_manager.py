"""portfolio/manager.py için birim testler."""
from __future__ import annotations

from src.domain.portfolio import snapshot as portfolio_snapshot
from src.domain.portfolio.lifecycle import tick_position_state
from src.domain.portfolio.manager import PortfolioManager
from src.models.position import Position


def _pos(cid: str = "c1", event_id: str = "evt_1", size: float = 40.0) -> Position:
    return Position(
        condition_id=cid,
        token_id="tok_" + cid,
        direction="BUY_YES",
        entry_price=0.40,
        size_usdc=size,
        shares=size / 0.40,
        current_price=0.40,
        anchor_probability=0.55,
        event_id=event_id,
        slug=f"s-{cid}",
    )


def test_initial_state() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    assert m.bankroll == 1000.0
    assert m.count() == 0
    assert m.realized_pnl == 0.0


def test_add_position_reduces_bankroll() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    assert m.add_position(_pos(size=40)) is True
    assert m.bankroll == 960.0
    assert m.count() == 1


def test_add_duplicate_condition_blocked() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    assert m.add_position(_pos(cid="c1")) is False
    assert m.count() == 1


def test_event_level_guard_blocks_second_position(caplog) -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1", event_id="evt_42"))
    # Farklı condition_id ama aynı event_id → BLOCKED (ARCH Kural 8)
    assert m.add_position(_pos(cid="c2", event_id="evt_42")) is False
    assert m.count() == 1


def test_empty_event_id_does_not_block() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1", event_id=""))
    # Boş event_id → guard tetiklenmez
    assert m.add_position(_pos(cid="c2", event_id="")) is True
    assert m.count() == 2


def test_remove_position_profit() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(size=40))
    # Çıkışta pnl=+10 → bankroll = 960 + 40 + 10 = 1010
    m.remove_position("c1", realized_pnl_usdc=10.0)
    assert m.bankroll == 1010.0
    assert m.realized_pnl == 10.0
    assert m.high_water_mark == 1010.0
    assert m.count() == 0


def test_remove_position_loss() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(size=40))
    m.remove_position("c1", realized_pnl_usdc=-15.0)
    assert m.bankroll == 985.0
    assert m.realized_pnl == -15.0
    # HWM 1000 (başlangıç) — düşüş sonrası değişmez
    assert m.high_water_mark == 1000.0


def test_remove_missing_returns_none() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    assert m.remove_position("nonexistent") is None


def test_apply_partial_exit_credits_basis_and_realized() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(size=40))  # bankroll = 960
    # 30% partial: caller returns basis 12 (= 40*0.3) + realized 8
    m.apply_partial_exit("c1", basis_returned_usdc=12.0, realized_usdc=8.0)
    # Pozisyon hala duruyor, bankroll +12+8=+20
    assert m.count() == 1
    assert m.bankroll == 980.0
    assert m.realized_pnl == 8.0


def test_apply_partial_exit_preserves_identity() -> None:
    """Identity: bankroll + invested == initial + realized_pnl (TDD §5.7.7)."""
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(size=40))
    # Caller (orchestration) önce basis'i kapar, sonra pos.size_usdc'yi küçültür.
    basis_returned = 40.0 * 0.3
    m.positions["c1"].size_usdc = 40.0 * 0.7  # 28
    m.apply_partial_exit("c1", basis_returned_usdc=basis_returned, realized_usdc=8.0)
    invested = sum(p.size_usdc for p in m.positions.values())
    assert m.bankroll + invested == 1000.0 + m.realized_pnl


def test_apply_partial_exit_missing_condition_noop() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.apply_partial_exit("nonexistent", basis_returned_usdc=5.0, realized_usdc=1.0)
    assert m.bankroll == 1000.0
    assert m.realized_pnl == 0.0


def test_snapshot_roundtrip() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1", event_id="evt_1"))
    m.add_position(_pos(cid="c2", event_id="evt_2"))
    m.remove_position("c1", realized_pnl_usdc=5.0)

    snap = portfolio_snapshot.to_dict(m)
    restored = portfolio_snapshot.from_dict(snap, initial_bankroll=1000.0)
    assert restored.count() == 1
    assert restored.realized_pnl == 5.0
    assert "c2" in restored.positions
    # Bankroll = 1000 + 5 − 40 (yatırılan c2)
    assert restored.bankroll == 965.0


def test_has_event() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1", event_id="evt_x"))
    assert m.has_event("evt_x") is True
    assert m.has_event("evt_nonexistent") is False
    assert m.has_event("") is False


def test_total_invested() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1", event_id="e1", size=40))
    m.add_position(_pos(cid="c2", event_id="e2", size=60))
    assert m.total_invested() == 100.0


def test_get() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    assert m.get("c1") is not None
    assert m.get("nonexistent") is None


# ── WS price update + cycle state tick ──

def test_update_position_price_updates_current_and_bid() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    # Position's token_id = "tok_c1"
    found = m.update_position_price("tok_c1", yes_price=0.55, bid_price=0.54)
    assert found is True
    pos = m.positions["c1"]
    assert pos.current_price == 0.55
    assert pos.bid_price == 0.54


def test_update_position_price_unknown_token_returns_false() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    assert m.update_position_price("unknown_token", 0.50, 0.49) is False


def test_update_position_price_zero_price_ignored() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    assert m.update_position_price("tok_c1", 0.0, 0.0) is False
    # current_price değişmemiş
    assert m.positions["c1"].current_price == 0.40


def test_tick_position_state_updates_peak_and_ever_in_profit() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))  # entry 0.40, shares=100, size=40
    pos = m.positions["c1"]

    # Fiyat yükseldi → peak update, ever_in_profit flag
    pos.current_price = 0.50  # pnl_pct = (100*0.50-40)/40 = 25%
    tick_position_state(pos)
    assert pos.peak_pnl_pct == 0.25
    assert pos.peak_price == 0.50
    assert pos.ever_in_profit is True


def test_tick_position_state_tracks_momentum_down() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    pos = m.positions["c1"]
    pos.previous_cycle_price = 0.45

    # Fiyat düştü: 0.45 → 0.40
    pos.current_price = 0.40
    tick_position_state(pos)
    assert pos.consecutive_down_cycles == 1
    assert abs(pos.cumulative_drop - 0.05) < 1e-9
    assert pos.previous_cycle_price == 0.40

    # Tekrar düştü: 0.40 → 0.35
    pos.current_price = 0.35
    tick_position_state(pos)
    assert pos.consecutive_down_cycles == 2
    assert abs(pos.cumulative_drop - 0.10) < 1e-9


def test_tick_position_state_resets_on_up_move() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    pos = m.positions["c1"]
    pos.previous_cycle_price = 0.35
    pos.consecutive_down_cycles = 3
    pos.cumulative_drop = 0.10

    # Fiyat yükseldi → reset
    pos.current_price = 0.40
    tick_position_state(pos)
    assert pos.consecutive_down_cycles == 0
    assert pos.cumulative_drop == 0.0


def test_tick_position_state_increments_cycles_held() -> None:
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    pos = m.positions["c1"]
    tick_position_state(pos)
    tick_position_state(pos)
    tick_position_state(pos)
    assert pos.cycles_held == 3


# ── recalculate_bankroll (DRY extract: from_snapshot + reconcile) ──

def test_recalculate_bankroll_no_positions() -> None:
    """Hiç pozisyon yok: bankroll = initial + realized."""
    mgr = PortfolioManager(initial_bankroll=1000.0)
    mgr.realized_pnl = -50.0
    mgr.recalculate_bankroll(1000.0)
    assert mgr.bankroll == 950.0


def test_recalculate_bankroll_with_invested_positions() -> None:
    """Açık pozisyon size_usdc'leri çıkarılır: bankroll = initial + realized - invested."""
    mgr = PortfolioManager(initial_bankroll=1000.0)
    mgr.realized_pnl = -20.0
    mgr.positions["a"] = _pos(cid="a", event_id="e1", size=100.0)
    mgr.recalculate_bankroll(1000.0)
    # 1000 - 20 - 100 = 880
    assert mgr.bankroll == 880.0


# ── FIX-A: bid_price=0 resolve fallback (PLAN-024) ──

def test_ws_bid_zero_fallback_uses_yes_price() -> None:
    """Polymarket resolve olunca bid=0 gönderir; bid_price yes_price'a fall-back etmeli.

    Regresyon: PLAN-023 bid_price'a geçişten sonra near_resolve 94¢ kuralı
    çalışmıyordu — bid=0 gelince 0 >= 0.94 = False → pozisyon satılmıyordu.
    """
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    # Polymarket resolve sonrası gelen mesaj: ask=1.0, bid=0.0
    m.update_position_price("tok_c1", yes_price=1.0, bid_price=0.0)
    pos = m.positions["c1"]
    assert pos.current_price == 1.0
    # Fallback: bid_price 0 değil, yes_price (1.0) olmalı
    assert pos.bid_price == 1.0, (
        f"bid_price=0 fallback çalışmadı, bid_price={pos.bid_price}"
    )


def test_ws_normal_bid_not_overridden() -> None:
    """Normal WS tick: bid_price > 0 ise olduğu gibi korunmalı."""
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    m.update_position_price("tok_c1", yes_price=0.70, bid_price=0.69)
    pos = m.positions["c1"]
    assert pos.bid_price == 0.69


def test_ws_bid_zero_at_low_price_uses_yes_price() -> None:
    """Düşük fiyatta da bid=0 gelirse yes_price kullan (liquid olmayan market)."""
    m = PortfolioManager(initial_bankroll=1000.0)
    m.add_position(_pos(cid="c1"))
    m.update_position_price("tok_c1", yes_price=0.30, bid_price=0.0)
    pos = m.positions["c1"]
    assert pos.bid_price == 0.30
