"""Replay engine — retroactive simülasyon kuralları + öncelik testleri.

Engine pure; sabitler dışarıdan ExitRulesConfig ile verilir. Testler için
canonical tennis profili kullanılır (scale_out.TIER1/2 + resolved + tennis SL).
"""
from __future__ import annotations

from src.domain.replay.replay_engine import (
    ExitRulesConfig,
    replay_position,
)
from src.strategy.exit.resolved import LOST_THRESHOLD, WON_THRESHOLD
from src.strategy.exit.scale_out import (
    TIER1_SELL_PCT,
    TIER1_TRIGGER_PNL,
    TIER2_SELL_PCT,
    TIER2_TRIGGER_PNL,
)
from src.config.sport_rules import get_stop_loss


def _tennis_rules() -> ExitRulesConfig:
    return ExitRulesConfig(
        tier1_trigger_pnl=TIER1_TRIGGER_PNL,
        tier1_sell_pct=TIER1_SELL_PCT,
        tier2_trigger_pnl=TIER2_TRIGGER_PNL,
        tier2_sell_pct=TIER2_SELL_PCT,
        lost_threshold=LOST_THRESHOLD,
        won_threshold=WON_THRESHOLD,
        near_resolve_threshold=0.94,
        near_resolve_guard_minutes=5,
        stop_loss_pct=get_stop_loss("tennis"),
        match_duration_hours=1.75,
    )


def _hist(*ticks: tuple[str, float]) -> list[dict]:
    return [{"timestamp_iso": ts, "price": p} for ts, p in ticks]


# ── 1) BUY_YES, fiyat dümdüz tırmanışla resolved (won) — tek RESOLVED ─────────

def test_replay_buy_yes_full_resolution_no_intermediate_exits():
    # entry=0.45, fiyat asla 0.25 üzeri sıçramayı yapamadan direkt 1.0'a kapansa
    # (yani tier1 trigger %25 hiç görülmeden) sadece RESOLVED tetiklenir.
    rules = _tennis_rules()
    rules2 = ExitRulesConfig(
        tier1_trigger_pnl=10.0,   # imkansız trigger → scale-out yok
        tier1_sell_pct=rules.tier1_sell_pct,
        tier2_trigger_pnl=10.0,
        tier2_sell_pct=rules.tier2_sell_pct,
        lost_threshold=rules.lost_threshold,
        won_threshold=rules.won_threshold,
        near_resolve_threshold=0.99,  # NEAR_RESOLVE de tetiklenmesin → sadece RESOLVED
        near_resolve_guard_minutes=5,
        stop_loss_pct=rules.stop_loss_pct,
    )
    history = _hist(
        ("2026-05-20T16:00:00+00:00", 0.45),
        ("2026-05-20T16:05:00+00:00", 0.50),
        ("2026-05-20T16:10:00+00:00", 0.60),
        ("2026-05-20T16:15:00+00:00", 1.00),  # resolved (won)
    )
    res = replay_position(
        entry_price=0.45, direction="BUY_YES",
        size_usdc=45.0, shares=100.0,
        match_start_iso="2026-05-20T16:00:00+00:00",
        price_history=history,
        rules=rules2,
    )
    assert res.closed is True
    assert len(res.exits) == 1
    assert res.exits[0].reason == "resolved"
    assert "won" in res.exits[0].detail
    # P&L = 100 * 1.00 - 45 = 55
    assert abs(res.exits[0].realized_pnl_usdc - 55.0) < 1e-6


# ── 2) Tier 1 scale_out tetiklenir, pozisyon %60'a düşer ──────────────────────

def test_replay_buy_yes_scale_out_tier_1():
    rules = _tennis_rules()
    # entry=0.40, tick=0.52 → pnl=+30% → tier1 net trigger (float epsilon güvenli)
    history = _hist(
        ("2026-05-20T16:30:00+00:00", 0.40),
        ("2026-05-20T16:40:00+00:00", 0.52),  # +30% → tier1
        ("2026-05-20T16:50:00+00:00", 0.55),  # +37.5% (tier2 değil)
    )
    res = replay_position(
        entry_price=0.40, direction="BUY_YES",
        size_usdc=40.0, shares=100.0,
        match_start_iso="2026-05-20T16:00:00+00:00",
        price_history=history,
        rules=rules,
    )
    assert res.closed is False
    assert len(res.exits) == 1
    assert res.exits[0].reason == "scale_out"
    assert res.exits[0].tier == 1
    assert res.exits[0].sell_pct == TIER1_SELL_PCT
    # Tier1: 40% sat → kalan %60. realized = (100*0.52 - 40) * 0.40 = 4.8
    assert abs(res.exits[0].realized_pnl_usdc - 4.8) < 1e-6
    assert abs(res.final_remaining_pct - 0.60) < 1e-6
    assert abs(res.final_size_usdc - 24.0) < 1e-6  # 40 * 0.6
    assert res.final_scale_out_tier == 1


# ── 3) Tier1 + Tier2 + RESOLVED birlikte ──────────────────────────────────────

def test_replay_buy_yes_scale_out_both_tiers_then_resolved():
    rules = _tennis_rules()
    # entry=0.40 → tier1@0.52 (+30%) → tier2@0.62 (+55%) → resolved@0.98 (won)
    history = _hist(
        ("2026-05-20T16:30:00+00:00", 0.40),
        ("2026-05-20T16:40:00+00:00", 0.52),  # tier1
        ("2026-05-20T16:50:00+00:00", 0.62),  # tier2 (sonraki tick'te)
        ("2026-05-20T17:00:00+00:00", 0.98),  # resolved
    )
    res = replay_position(
        entry_price=0.40, direction="BUY_YES",
        size_usdc=40.0, shares=100.0,
        match_start_iso="2026-05-20T16:00:00+00:00",
        price_history=history,
        rules=rules,
    )
    assert res.closed is True
    assert len(res.exits) == 3
    assert res.exits[0].reason == "scale_out" and res.exits[0].tier == 1
    assert res.exits[1].reason == "scale_out" and res.exits[1].tier == 2
    assert res.exits[2].reason == "resolved"
    # Toplam P&L pozitif olmalı (entry 0.40, kapanış 0.98)
    assert res.realized_pnl_total > 0
    # Tier1 sonrası kalan %60, tier2 (kalanın %50'i) sonrası → %30 → resolved'da hepsi.
    assert res.final_remaining_pct == 0.0


# ── 4) STOP_LOSS — fiyat -%30+ düşüş ──────────────────────────────────────────

def test_replay_buy_yes_stop_loss_only():
    rules = _tennis_rules()
    # entry=0.50, fiyat 0.34'e düşse (-32%) → tennis SL (%30) tetiklenir
    history = _hist(
        ("2026-05-20T16:30:00+00:00", 0.50),
        ("2026-05-20T16:40:00+00:00", 0.45),
        ("2026-05-20T16:50:00+00:00", 0.34),  # -32% → SL
    )
    res = replay_position(
        entry_price=0.50, direction="BUY_YES",
        size_usdc=50.0, shares=100.0,
        match_start_iso="2026-05-20T16:00:00+00:00",
        price_history=history,
        rules=rules,
    )
    assert res.closed is True
    assert len(res.exits) == 1
    assert res.exits[0].reason == "stop_loss"
    # realized = 100*0.34 - 50 = -16
    assert abs(res.exits[0].realized_pnl_usdc - (-16.0)) < 1e-6


# ── 5) BUY_NO — YES fiyat ≤0.03 düşerse NO token ≥0.97 → resolved (won) ───────

def test_replay_buy_no_resolved_won():
    rules = _tennis_rules()
    # BUY_NO entry=0.40 (yani YES@0.60'tan girilmiş, NO token=0.40).
    # YES fiyatı 0.02'ye düşerse NO token 0.98 → RESOLVED won.
    history = _hist(
        ("2026-05-20T17:00:00+00:00", 0.60),   # YES; NO=0.40 (entry)
        ("2026-05-20T17:10:00+00:00", 0.30),   # NO=0.70
        ("2026-05-20T17:20:00+00:00", 0.02),   # NO=0.98 → resolved (won)
    )
    res = replay_position(
        entry_price=0.40, direction="BUY_NO",
        size_usdc=40.0, shares=100.0,
        match_start_iso="2026-05-20T16:00:00+00:00",
        price_history=history,
        rules=rules,
    )
    assert res.closed is True
    # Sondan önce tier1@NO=0.70 ve tier2@NO=??? tetiklenmeli — NO token 0.70 = +75% from 0.40
    # tier1@NO=0.50 (+25%) görülmeden 0.70'e atlandığı için ilk tick'te tier1 doğrudan tetiklenir.
    reasons = [e.reason for e in res.exits]
    assert "resolved" in reasons
    last = res.exits[-1]
    assert last.reason == "resolved"
    assert "won" in last.detail


# ── 6) Aynı tick: tier1 trigger + resolved → RESOLVED kazanır ─────────────────

def test_replay_priority_resolved_over_scale_out():
    rules = _tennis_rules()
    # entry=0.50, ilk tick 0.98 → hem +96% (tier1+tier2 olabilir) hem ≥0.97 → RESOLVED öncelik
    history = _hist(
        ("2026-05-20T17:00:00+00:00", 0.98),
    )
    res = replay_position(
        entry_price=0.50, direction="BUY_YES",
        size_usdc=50.0, shares=100.0,
        match_start_iso="2026-05-20T16:00:00+00:00",
        price_history=history,
        rules=rules,
    )
    assert res.closed is True
    assert len(res.exits) == 1
    assert res.exits[0].reason == "resolved"


# ── 7) Pre-match pozisyon, fiyat geçmişi boş → no-op ─────────────────────────

def test_replay_pre_match_position_no_history():
    rules = _tennis_rules()
    res = replay_position(
        entry_price=0.45, direction="BUY_YES",
        size_usdc=45.0, shares=100.0,
        match_start_iso="2026-05-21T16:00:00+00:00",  # gelecekte
        price_history=[],
        rules=rules,
    )
    assert res.closed is False
    assert res.fired_any is False
    assert res.final_remaining_pct == 1.0
    # Hiç tick işlenmedi → engine giriş size/shares'i geri verir (pozisyon değişmemiş).
    assert res.final_size_usdc == 45.0
    assert res.final_shares == 100.0


# ── 8) Golden: tennis pozisyonu bot SL davranışıyla aynı sonuç vermeli ────────

def test_replay_results_match_actual_bot_behavior_for_simple_case():
    """Wawrinka benzeri SL: entry=0.41, fiyat 0.28'e düşer → bot tennis SL (%30) ile çıkar.

    Bot davranışı: stop_loss.check tennis için stop_loss_pct=0.30 verir;
    pnl=(0.28-0.41)/0.41 = -31.7% → tetiklenir, full exit.
    Replay engine aynı sonucu üretmeli.
    """
    rules = _tennis_rules()
    history = _hist(
        ("2026-05-20T14:30:00+00:00", 0.41),
        ("2026-05-20T15:00:00+00:00", 0.35),
        ("2026-05-20T15:30:00+00:00", 0.28),  # -31.7% → SL
    )
    res = replay_position(
        entry_price=0.41, direction="BUY_YES",
        size_usdc=40.0, shares=97.56,
        match_start_iso="2026-05-20T14:19:51+00:00",
        price_history=history,
        rules=rules,
    )
    assert res.closed is True
    assert len(res.exits) == 1
    assert res.exits[0].reason == "stop_loss"
    expected = 97.56 * 0.28 - 40.0
    assert abs(res.exits[0].realized_pnl_usdc - expected) < 0.01
