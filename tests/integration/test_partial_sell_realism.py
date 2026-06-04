"""2026-05-30 fix: scale-out partial exit'in GERÇEK satım yapması.

Tennis-paper-lab paritesi. Önceki davranış: bot defterine "sattım +$X" yazıyor
ama Polymarket'e emir gitmiyordu. Bu test partial_sell zincirinin uçtan uca
gerçek defter çağrısı yaptığını + REJECT durumunda pozisyonu KORUDUĞUNU
doğrular.
"""
from pathlib import Path
from unittest.mock import MagicMock

from src.config.settings import Mode, PaperConfig
from src.infrastructure.executor import Executor
from src.orchestration.paper_executor import PaperExecutor


def _book_resp(asks, bids):
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status = MagicMock()
    m.json.return_value = {"asks": asks, "bids": bids}
    return m


def _ask(p, s):
    return {"price": str(p), "size": str(s)}


def _bid(p, s):
    return _ask(p, s)


# ─── PaperExecutor.partial_sell — 3 senaryo ────────────────────────────────

def test_paper_partial_sell_full_fill(tmp_path):
    """Bid book yeterli → FILLED, gerçek avg_price döner."""
    book = _book_resp(asks=[], bids=[_bid(0.85, 1000)])
    px = PaperExecutor(
        config=PaperConfig(),
        audit_path=tmp_path / "exec.jsonl",
        http_get=MagicMock(return_value=book),
    )
    result = px.partial_sell(token_id="tok1", shares=20, target_price=0.85)
    assert result["status"] == "FILLED"
    assert result["filled_shares"] == 20
    assert abs(result["avg_price"] - 0.85) < 1e-9
    assert result["reason"] == "scale_out"


def test_paper_partial_sell_partial_when_bids_insufficient(tmp_path):
    """Bid book kısmi → PARTIAL_FILL, kalan share kayda eklenmez."""
    book = _book_resp(asks=[], bids=[_bid(0.85, 12)])  # sadece 12 share talep
    px = PaperExecutor(
        config=PaperConfig(),
        audit_path=tmp_path / "exec.jsonl",
        http_get=MagicMock(return_value=book),
    )
    result = px.partial_sell(token_id="tok1", shares=20, target_price=0.85)
    assert result["status"] == "PARTIAL_FILL"
    assert result["filled_shares"] == 12


def test_paper_partial_sell_rejected_no_bids(tmp_path):
    """Bid yok → REJECTED, gerçek live'da satım yapamayız."""
    book = _book_resp(asks=[], bids=[])
    px = PaperExecutor(
        config=PaperConfig(),
        audit_path=tmp_path / "exec.jsonl",
        http_get=MagicMock(return_value=book),
    )
    result = px.partial_sell(token_id="tok1", shares=20, target_price=0.85)
    assert result["status"] == "REJECTED"
    assert result["filled_shares"] == 0.0


# ─── Executor.partial_sell mode dispatch — 3 mode ────────────────────────

def test_executor_dry_run_partial_sell_simulated():
    ex = Executor(mode=Mode.DRY_RUN)
    result = ex.partial_sell(token_id="t", shares=10.0, target_price=0.8)
    assert result["status"] == "simulated"
    assert result["mode"] == "dry_run"
    assert result["filled_shares"] == 10.0
    assert result["avg_price"] == 0.8


def test_executor_paper_partial_sell_delegates(tmp_path):
    book = _book_resp(asks=[], bids=[_bid(0.85, 1000)])
    ex = Executor(
        mode=Mode.PAPER,
        http_get=MagicMock(return_value=book),
        paper_audit_path=tmp_path / "exec.jsonl",
    )
    result = ex.partial_sell(token_id="t", shares=20.0, target_price=0.85)
    assert result["status"] == "FILLED"
    assert result["mode"] == "paper"


def test_executor_live_partial_sell_calls_market_sell():
    clob = MagicMock()
    clob.place_market_sell.return_value = {
        "order_id": "live_x", "status": "placed",
        "filled_shares": 10.0, "avg_price": 0.85,
    }
    ex = Executor(mode=Mode.LIVE, http_get=MagicMock(), clob_client=clob)
    result = ex.partial_sell(token_id="t", shares=10.0, target_price=0.85)
    assert result["mode"] == "live"
    assert result["filled_shares"] == 10.0
    clob.place_market_sell.assert_called_once_with(token_id="t", shares=10.0)


# ─── Integration: exit_processor REJECT → pozisyon değişmez ───────────────

def test_exit_processor_partial_exit_rejected_keeps_position(tmp_path):
    """En kritik senaryo: paper executor REJECTED → pozisyon AYNEN kalır,
    bankroll'a sahte kâr yazılmaz, trade_history'ye partial kayıt YAPILMAZ.

    Live davranışı bu olur: Polymarket'e emir gitti, fill alınamadı, pozisyon
    açık kalır, defter olduğu gibi durur.
    """
    from src.models.position import Position
    from src.models.enums import ExitReason
    from src.strategy.exit.monitor import ExitSignal

    # Mock executor — PAPER REJECTED dönecek
    rejecting_executor = MagicMock()
    rejecting_executor.partial_sell.return_value = {
        "order_id": "rej1",
        "status": "REJECTED",
        "mode": "paper",
        "reason": "no_bids_above_slippage",
        "filled_shares": 0.0,
        "avg_price": 0.0,
    }

    # Mock portfolio — apply_partial_exit ÇAĞRILMAMALI
    portfolio = MagicMock()
    trade_event_log = MagicMock()

    # Mock deps
    deps = MagicMock()
    deps.executor = rejecting_executor
    deps.state.portfolio = portfolio
    deps.trade_event_log = trade_event_log

    from src.orchestration.exit_processor import ExitProcessor
    ep = ExitProcessor.__new__(ExitProcessor)
    ep.deps = deps

    # Pozisyon
    pos = MagicMock(spec=Position)
    pos.token_id = "tok1"
    pos.condition_id = "0xabc"
    pos.shares = 100.0
    pos.size_usdc = 50.0
    pos.entry_price = 0.50
    pos.current_price = 0.80
    pos.unrealized_pnl_usdc = 30.0
    pos.scale_out_tier = 0
    pos.scale_out_realized_usdc = 0.0
    pos.slug = "test-vs-test"

    signal = ExitSignal(
        reason=ExitReason.SCALE_OUT, partial=True,
        sell_pct=0.40, tier=1, detail="tier 1",
    )

    # ÇAĞIR
    ep._execute_partial_exit(pos, signal)

    # ASSERT
    # executor.partial_sell ÇAĞRILMIŞ olmalı
    rejecting_executor.partial_sell.assert_called_once()
    # apply_partial_exit ÇAĞRILMAMIŞ olmalı (REJECTED → defter dokunmaz)
    portfolio.apply_partial_exit.assert_not_called()
    # SPEC-Z17: trade_event_log.append_partial ÇAĞRILMAMIŞ olmalı
    trade_event_log.append_partial.assert_not_called()
    # Pozisyon shares + size_usdc AYNI kalmalı
    assert pos.shares == 100.0
    assert pos.size_usdc == 50.0
    assert pos.scale_out_realized_usdc == 0.0


def test_exit_processor_partial_exit_filled_uses_actual_price(tmp_path):
    """FILLED durumunda actual filled_shares + actual avg_price kullanılmalı
    (book'a göre gerçek satım fiyatı, current_price değil)."""
    from src.models.position import Position
    from src.models.enums import ExitReason
    from src.strategy.exit.monitor import ExitSignal

    # Mock executor — FILLED dönecek, avg_price gerçekçi (slippage)
    executor = MagicMock()
    executor.partial_sell.return_value = {
        "order_id": "p1",
        "status": "FILLED",
        "mode": "paper",
        "filled_shares": 40.0,      # intended 40
        "avg_price": 0.78,           # current_price 0.80'den slippage ile düşük
    }
    portfolio = MagicMock()
    trade_event_log = MagicMock()

    deps = MagicMock()
    deps.executor = executor
    deps.state.portfolio = portfolio
    deps.trade_event_log = trade_event_log

    from src.orchestration.exit_processor import ExitProcessor
    ep = ExitProcessor.__new__(ExitProcessor)
    ep.deps = deps

    pos = MagicMock(spec=Position)
    pos.token_id = "tok1"
    pos.condition_id = "0xabc"
    pos.shares = 100.0
    pos.size_usdc = 50.0
    pos.entry_price = 0.50
    pos.current_price = 0.80
    pos.unrealized_pnl_usdc = 30.0
    pos.scale_out_tier = 0
    pos.scale_out_realized_usdc = 0.0
    pos.slug = "test"
    pos.question = ""
    pos.sport_tag = ""
    pos.source = "model"

    signal = ExitSignal(
        reason=ExitReason.SCALE_OUT, partial=True,
        sell_pct=0.40, tier=1, detail="tier 1",
    )

    ep._execute_partial_exit(pos, signal)

    # executor çağrıldı
    executor.partial_sell.assert_called_once()
    # Pozisyon 40 share azaldı (gerçek filled_shares)
    assert pos.shares == 60.0
    # apply_partial_exit gerçek realized ile çağrıldı
    portfolio.apply_partial_exit.assert_called_once()
    call_kw = portfolio.apply_partial_exit.call_args.kwargs
    # realized = 40 × (0.78 - 0.50) = 11.20
    assert abs(call_kw["realized_usdc"] - 11.20) < 0.01
    # SPEC-Z17: event log gerçek price ile çağrıldı (0.78, current_price 0.80 değil)
    log_kw = trade_event_log.append_partial.call_args.kwargs
    assert log_kw["price"] == 0.78
