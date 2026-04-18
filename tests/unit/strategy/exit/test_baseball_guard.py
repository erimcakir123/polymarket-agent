"""Baseball inning guard testleri (SPEC-008)."""
from __future__ import annotations

from src.config.sport_rules import get_sport_rule
from src.strategy.exit.stop_loss import parse_baseball_inning


def test_mlb_comeback_thresholds_configured() -> None:
    thresholds = get_sport_rule("mlb", "comeback_thresholds")
    assert thresholds is not None
    assert thresholds[3] == 6   # inning 1-3: 6 run
    assert thresholds[5] == 5   # inning 4-5: 5 run
    assert thresholds[7] == 4   # inning 6-7: 4 run
    assert thresholds[8] == 3   # inning 8: 3 run
    assert thresholds[9] == 2   # inning 9: 2 run


def test_mlb_extra_inning_threshold_configured() -> None:
    assert get_sport_rule("mlb", "extra_inning_threshold") == 1


def test_parse_inning_top_1st_returns_1() -> None:
    assert parse_baseball_inning("Top 1st") == 1


def test_parse_inning_bot_5th_returns_5() -> None:
    assert parse_baseball_inning("Bot 5th") == 5


def test_parse_inning_mid_9th_returns_9() -> None:
    assert parse_baseball_inning("Mid 9th") == 9


def test_parse_inning_top_2nd_returns_2() -> None:
    assert parse_baseball_inning("Top 2nd") == 2


def test_parse_inning_bot_3rd_returns_3() -> None:
    assert parse_baseball_inning("Bot 3rd") == 3


def test_parse_inning_extra_11th_returns_11() -> None:
    assert parse_baseball_inning("Top 11th") == 11


def test_parse_inning_empty_returns_none() -> None:
    assert parse_baseball_inning("") is None


def test_parse_inning_final_returns_none() -> None:
    assert parse_baseball_inning("Final") is None


def test_parse_inning_in_progress_returns_none() -> None:
    assert parse_baseball_inning("In Progress") is None


from src.strategy.exit.stop_loss import is_baseball_alive


def test_alive_deficit_0_any_inning() -> None:
    """Eşit skor → her zaman canlı."""
    assert is_baseball_alive(inning=1, deficit=0) is True
    assert is_baseball_alive(inning=9, deficit=0) is True


def test_alive_leading_any_inning() -> None:
    """Önde → her zaman canlı."""
    assert is_baseball_alive(inning=9, deficit=-3) is True


def test_alive_inning_1_deficit_5() -> None:
    """1. inning, 5 run geride ama eşik 6 → canlı."""
    assert is_baseball_alive(inning=1, deficit=5) is True


def test_dead_inning_1_deficit_6() -> None:
    """1. inning, 6 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=1, deficit=6) is False


def test_dead_inning_3_deficit_7() -> None:
    """3. inning, 7 run geride > eşik 6 → ölü."""
    assert is_baseball_alive(inning=3, deficit=7) is False


def test_alive_inning_4_deficit_4() -> None:
    """4. inning, 4 run geride < eşik 5 → canlı."""
    assert is_baseball_alive(inning=4, deficit=4) is True


def test_dead_inning_5_deficit_5() -> None:
    """5. inning, 5 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=5, deficit=5) is False


def test_alive_inning_6_deficit_3() -> None:
    """6. inning, 3 run geride < eşik 4 → canlı."""
    assert is_baseball_alive(inning=6, deficit=3) is True


def test_dead_inning_7_deficit_4() -> None:
    """7. inning, 4 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=7, deficit=4) is False


def test_alive_inning_8_deficit_2() -> None:
    """8. inning, 2 run geride < eşik 3 → canlı."""
    assert is_baseball_alive(inning=8, deficit=2) is True


def test_dead_inning_8_deficit_3() -> None:
    """8. inning, 3 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=8, deficit=3) is False


def test_alive_inning_9_deficit_1() -> None:
    """9. inning, 1 run geride < eşik 2 → canlı."""
    assert is_baseball_alive(inning=9, deficit=1) is True


def test_dead_inning_9_deficit_2() -> None:
    """9. inning, 2 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=9, deficit=2) is False


def test_dead_extra_deficit_1() -> None:
    """Uzatma (10+), 1 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=10, deficit=1) is False
    assert is_baseball_alive(inning=12, deficit=1) is False


def test_alive_extra_deficit_0() -> None:
    """Uzatma, eşit → canlı."""
    assert is_baseball_alive(inning=10, deficit=0) is True


# ---------------------------------------------------------------------------
# Task 4 — compute_stop_loss_pct() + check() entegrasyon testleri (SPEC-008)
# ---------------------------------------------------------------------------
from src.models.position import Position
from src.strategy.exit.stop_loss import check, compute_stop_loss_pct


def _pos(**over) -> Position:
    base = dict(
        condition_id="c1", token_id="t", direction="BUY_YES",
        entry_price=0.40, size_usdc=40, shares=100,
        current_price=0.40, anchor_probability=0.55,
        confidence="B", sport_tag="mlb",
    )
    base.update(over)
    return Position(**base)


def test_baseball_alive_sl_disabled() -> None:
    """Canlı maç (1. inning, 0-0): %35 düşüş → SL tetiklenmez."""
    p = _pos(entry_price=0.40, current_price=0.26)  # pnl = -35%
    score_info = {"available": True, "deficit": 0, "period": "Top 1st"}
    assert compute_stop_loss_pct(p, score_info) is None
    assert check(p, score_info) is False


def test_baseball_alive_behind_under_threshold() -> None:
    """1. inning, 5 run geride ama eşik 6 → canlı → SL devre dışı."""
    p = _pos(entry_price=0.40, current_price=0.20)  # pnl = -50%
    score_info = {"available": True, "deficit": 5, "period": "Bot 3rd"}
    assert compute_stop_loss_pct(p, score_info) is None
    assert check(p, score_info) is False


def test_baseball_dead_sl_active() -> None:
    """Ölü maç (8. inning, 3 run geride): %35 düşüş → SL tetiklenir."""
    p = _pos(entry_price=0.40, current_price=0.26)  # pnl = -35%
    score_info = {"available": True, "deficit": 3, "period": "Top 8th"}
    sl = compute_stop_loss_pct(p, score_info)
    assert sl is not None
    assert sl == 0.30  # mlb default SL
    assert check(p, score_info) is True


def test_baseball_dead_but_pnl_above_sl() -> None:
    """Ölü maç ama PnL henüz SL'ye ulaşmadı → tetiklenmez."""
    p = _pos(entry_price=0.40, current_price=0.34)  # pnl = -15%
    score_info = {"available": True, "deficit": 3, "period": "Top 8th"}
    sl = compute_stop_loss_pct(p, score_info)
    assert sl == 0.30
    assert check(p, score_info) is False


def test_baseball_unknown_sl_fallback() -> None:
    """Veri yok → SL normal çalışır (fallback)."""
    p = _pos(entry_price=0.40, current_price=0.26)  # pnl = -35%
    assert check(p, None) is True
    assert check(p) is True  # geriye uyumlu


def test_baseball_unparseable_period_fallback() -> None:
    """Period parse edilemiyor → fallback, SL normal."""
    p = _pos(entry_price=0.40, current_price=0.26)  # pnl = -35%
    score_info = {"available": True, "deficit": 0, "period": "In Progress"}
    assert check(p, score_info) is True


def test_baseball_score_not_available_fallback() -> None:
    """available=False → fallback."""
    p = _pos(entry_price=0.40, current_price=0.26)
    score_info = {"available": False, "deficit": 0, "period": "Top 1st"}
    assert check(p, score_info) is True


def test_non_baseball_unaffected() -> None:
    """NBA → baseball guard atlanır → SL normal çalışır."""
    # current_price=0.25 → pnl = -37.5% > NBA SL %35 → tetiklenir
    p = _pos(entry_price=0.40, current_price=0.25, sport_tag="nba")
    score_info = {"available": True, "deficit": 0, "period": "Top 1st"}
    sl = compute_stop_loss_pct(p, score_info)
    assert sl == 0.35  # NBA SL, guard bypass
    assert check(p, score_info) is True
