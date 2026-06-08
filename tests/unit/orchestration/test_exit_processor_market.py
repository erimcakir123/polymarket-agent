"""Kayıp-tarafı (loss-cut) çıkışları market modunda satar; kâr/near-resolve satmaz.
Ayrıca: tam çıkış executor sonucunu onurlandırır (REJECTED→korur, FILLED→gerçek fiyat)."""
from unittest.mock import MagicMock

from src.models.enums import ExitReason
from src.models.position import Position
from src.orchestration.exit_processor import ExitProcessor, _is_loss_cut
from src.strategy.exit.monitor import ExitSignal


def test_loss_cut_reasons_true():
    for r in (ExitReason.STOP_LOSS, ExitReason.GRADUATED_SL, ExitReason.PARTIAL_SL,
              ExitReason.NEVER_IN_PROFIT, ExitReason.ULTRA_LOW_GUARD, ExitReason.HOLD_REVOKED):
        assert _is_loss_cut(r) is True


def test_non_loss_cut_reasons_false():
    for r in (ExitReason.NEAR_RESOLVE, ExitReason.SCALE_OUT):
        assert _is_loss_cut(r) is False


def _pos():
    pos = MagicMock(spec=Position)
    pos.token_id = "t"; pos.condition_id = "0xabc"
    pos.shares = 100.0; pos.size_usdc = 50.0
    pos.entry_price = 0.52; pos.current_price = 0.30
    pos.slug = "x"; pos.question = ""; pos.sport_tag = ""; pos.source = "model"
    return pos


def _deps(exit_return):
    executor = MagicMock()
    executor.exit_position.return_value = exit_return
    deps = MagicMock()
    deps.executor = executor
    deps.price_feed = None
    return deps


def test_full_exit_rejected_keeps_position():
    """Boş defter → REJECTED → pozisyon kapatılmaz (hayali fill yok)."""
    deps = _deps({"status": "REJECTED", "reason": "empty_book", "filled_shares": 0.0, "avg_price": 0.0})
    ep = ExitProcessor.__new__(ExitProcessor); ep.deps = deps
    pos = _pos()
    status = ep._execute_exit(pos, ExitSignal(reason=ExitReason.STOP_LOSS, partial=False, detail=""))
    assert status == "REJECTED"
    deps.state.portfolio.remove_position.assert_not_called()
    assert pos.shares == 100.0 and pos.size_usdc == 50.0


def test_full_exit_filled_uses_actual_avg_price():
    """FILLED → realized GERÇEK avg_price'tan (0.25), current_price'tan (0.30) DEĞİL."""
    deps = _deps({"status": "FILLED", "filled_shares": 100.0, "avg_price": 0.25})
    ep = ExitProcessor.__new__(ExitProcessor); ep.deps = deps
    pos = _pos()
    status = ep._execute_exit(pos, ExitSignal(reason=ExitReason.STOP_LOSS, partial=False, detail="sl"))
    assert status == "FILLED"
    deps.state.portfolio.remove_position.assert_called_once()
    kw = deps.state.portfolio.remove_position.call_args.kwargs
    assert abs(kw["realized_pnl_usdc"] - (-25.0)) < 0.01  # 100*0.25-50, ask 0.30 olsaydı -20 olurdu
    log_kw = deps.trade_event_log.append_final.call_args.kwargs
    assert log_kw["exit_price"] == 0.25
