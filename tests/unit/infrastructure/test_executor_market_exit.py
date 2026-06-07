"""Executor PAPER dalında `market` bayrağı partial_sell/exit_position'a aktarılır.

Zarar-kes çıkışları gerçek piyasa emri gibi satsın diye eklenen market modunun
infrastructure dispatch katmanında doğru geçtiğini doğrular.
"""
from types import SimpleNamespace

from src.infrastructure.executor import Executor, Mode


def _paper_executor():
    ex = Executor.__new__(Executor)
    ex.mode = Mode.PAPER
    calls = {}

    def fake_partial_sell(token_id, shares, target_price, reason="scale_out", market=False):
        calls["partial"] = {"market": market}
        return {"status": "FILLED", "filled_shares": shares, "avg_price": target_price}

    def fake_place_sell(token_id, target_price, shares, market=False):
        calls["place"] = {"market": market}
        return {"status": "FILLED", "filled_shares": shares, "avg_price": target_price}

    ex._paper = SimpleNamespace(partial_sell=fake_partial_sell, place_sell=fake_place_sell)
    return ex, calls


def test_partial_sell_passes_market_flag():
    ex, calls = _paper_executor()
    ex.partial_sell("t", 10.0, 0.2, reason="partial_sl", market=True)
    assert calls["partial"]["market"] is True


def test_partial_sell_default_no_market():
    ex, calls = _paper_executor()
    ex.partial_sell("t", 10.0, 0.2)
    assert calls["partial"]["market"] is False


def test_exit_position_loss_uses_market():
    ex, calls = _paper_executor()
    pos = SimpleNamespace(slug="x", shares=10.0, token_id="t", bid_price=0.05, current_price=0.05)
    ex.exit_position(pos, reason="stop_loss", market=True)
    assert calls["place"]["market"] is True
