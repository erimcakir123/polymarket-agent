"""SPEC-Z24 check_loss_reentry guard birim testleri."""
from __future__ import annotations

from types import SimpleNamespace

import src.orchestration.entry_guards as g
from src.orchestration.entry_guards import check_loss_reentry


def _market(cid="X"):
    return SimpleNamespace(
        condition_id=cid, slug="wnba-a-b-2026", sport_tag="wnba",
        sports_market_type="moneyline", question="A vs B", event_id="1",
    )


def _deps(closed):
    portfolio = SimpleNamespace(closed_at_loss=closed)
    state = SimpleNamespace(portfolio=portfolio)
    stock = SimpleNamespace(add=lambda m, r: None)
    return SimpleNamespace(state=state, stock=stock, skipped_logger=SimpleNamespace())


def test_check_loss_reentry_blocks_when_cid_closed_at_loss(monkeypatch):
    monkeypatch.setattr(g.operational_writers, "log_skip", lambda *a, **k: None)
    assert check_loss_reentry(_deps({"X"}), _market("X")) is True


def test_check_loss_reentry_allows_when_not_closed(monkeypatch):
    monkeypatch.setattr(g.operational_writers, "log_skip", lambda *a, **k: None)
    assert check_loss_reentry(_deps({"Y"}), _market("X")) is False


def test_check_loss_reentry_allows_when_set_empty(monkeypatch):
    monkeypatch.setattr(g.operational_writers, "log_skip", lambda *a, **k: None)
    assert check_loss_reentry(_deps(set()), _market("X")) is False
