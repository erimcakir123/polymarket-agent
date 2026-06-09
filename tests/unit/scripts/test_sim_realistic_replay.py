"""SPEC-SIM: replay_position çıkış motoru testleri (ağsız, saf).

Gerçek bot çıkış beynini (monitor.evaluate + tick_position_state) sentetik fiyat
serilerine karşı oynatır; kademeli kâr-alma / partial-SL olaylarının doğru
tetiklendiğini ve realized formülünün (_book_sale ile birebir) tuttuğunu doğrular.
"""
from __future__ import annotations

import pathlib
import sys
from datetime import datetime

import pytest

# scripts/ paket değil → import için yola ekle
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))

from sim_realistic_replay import replay_position  # noqa: E402

from src.config.settings import PartialSlTier, ScaleOutTier  # noqa: E402
from src.models.enums import ExitReason  # noqa: E402
from src.models.position import Position  # noqa: E402

_SCALE_OUT = [
    ScaleOutTier(threshold=0.40, sell_pct=0.40),
    ScaleOutTier(threshold=0.70, sell_pct=0.50),
]
_PARTIAL_SL = [
    PartialSlTier(loss_threshold=0.20, sell_pct=0.30),
    PartialSlTier(loss_threshold=0.35, sell_pct=0.50),
    PartialSlTier(loss_threshold=0.50, sell_pct=1.00),
]
_MATCH_START = "2026-06-08T10:00:00+00:00"


def _series(prices, start_iso="2026-06-08T11:00:00+00:00", step_s=60):
    base = datetime.fromisoformat(start_iso).timestamp()
    return [(base + i * step_s, p) for i, p in enumerate(prices)]


def _pos(entry, shares, size, direction="BUY_YES", anchor=0.50):
    return Position(
        condition_id="0xtest", token_id="tok", direction=direction,
        entry_price=entry, size_usdc=size, shares=shares,
        anchor_probability=anchor, current_price=entry,
        match_start_iso=_MATCH_START, sport_tag="tennis",
    )


def _kw(**over):
    base = dict(
        scale_out_tiers=_SCALE_OUT, partial_sl_tiers=_PARTIAL_SL,
        partial_sl_enabled=True, graduated_sl_enabled=False,
    )
    base.update(over)
    return base


def test_replay_rising_curve_triggers_scaleout_then_near_resolve():
    pos = _pos(0.50, 100.0, 50.0)
    series = _series([0.50, 0.60, 0.72, 0.86, 0.96])
    res = replay_position(pos, series, **_kw())
    kinds = [(e.kind, e.tier) for e in res.events]
    assert kinds == [
        (ExitReason.SCALE_OUT.value, 1),
        (ExitReason.SCALE_OUT.value, 2),
        (ExitReason.NEAR_RESOLVE.value, None),
    ]
    assert res.closed is True


def test_replay_realized_matches_book_sale_formula():
    pos = _pos(0.50, 100.0, 50.0)
    series = _series([0.50, 0.72])
    res = replay_position(pos, series, **_kw())
    assert len(res.events) == 1
    e = res.events[0]
    # tier1: kalan 100 hissenin %40'ı = 40 hisse @0.72 → 40*(0.72-0.50)
    assert e.shares_sold == pytest.approx(40.0)
    assert e.realized == pytest.approx(40.0 * (0.72 - 0.50))


def test_replay_winner_staged_sum_not_greater_than_single_dump():
    pos = _pos(0.50, 100.0, 50.0)
    series = _series([0.50, 0.60, 0.72, 0.86, 0.96])
    res = replay_position(pos, series, **_kw())
    single_dump = 100.0 * (0.96 - 0.50)
    assert res.realized_total <= single_dump


def test_replay_falling_curve_triggers_partial_sl_tiers_in_order():
    pos = _pos(0.50, 100.0, 50.0)
    series = _series([0.50, 0.38, 0.28, 0.18])
    res = replay_position(pos, series, **_kw())
    kinds = [(e.kind, e.tier) for e in res.events]
    assert kinds == [
        (ExitReason.PARTIAL_SL.value, 1),
        (ExitReason.PARTIAL_SL.value, 2),
        (ExitReason.PARTIAL_SL.value, 3),
    ]
    assert res.closed is True


def test_replay_flat_curve_near_entry_no_exit():
    pos = _pos(0.50, 100.0, 50.0)
    series = _series([0.50, 0.51, 0.49, 0.50])
    res = replay_position(pos, series, **_kw())
    assert res.events == []
    assert res.closed is False


def test_loss_cut_below_liquidity_floor_holds_then_settles_at_resolution():
    """Fiyat tabanın altına düşünce stop-loss SATMAZ (boş defter) → çözümde yerleşir."""
    pos = _pos(0.50, 100.0, 50.0)
    # 0.30 → tier1 dolar; 0.05 & 0.001 taban altı → dolum yok; 0.001 çözüm (kaybetti)
    series = _series([0.50, 0.30, 0.05, 0.001])
    res = replay_position(pos, series, liquidity_floor=0.10, **_kw())
    kinds = [(e.kind, e.tier) for e in res.events]
    assert kinds == [
        (ExitReason.PARTIAL_SL.value, 1),
        ("settlement", None),
    ]
    assert res.closed is True
    expected = 30.0 * (0.30 - 0.50) + 70.0 * (0.001 - 0.50)
    assert res.realized_total == pytest.approx(expected)


def test_unresolved_end_does_not_settle_remains_open():
    """Maç bitmemiş (son fiyat çözüm değil) → kalan hisse açık kalır, yerleşme yok."""
    pos = _pos(0.50, 100.0, 50.0)
    series = _series([0.50, 0.72])  # tier1 dolar, 0.72'de biter (çözüm değil)
    res = replay_position(pos, series, liquidity_floor=0.10, **_kw())
    assert [e.kind for e in res.events] == [ExitReason.SCALE_OUT.value]
    assert res.closed is False
    assert res.remaining_shares == pytest.approx(60.0)
