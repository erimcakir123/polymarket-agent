"""NHL puck line dispatch wiring tests."""
from __future__ import annotations

from types import SimpleNamespace

from src.models.enums import ExitReason
from src.strategy.exit._nhl_puck_line_dispatch import check_nhl_puck_line_exit
from src.strategy.exit.nhl_puck_line_exit import NHLPuckLineExitConfig


def _pos(**kw):
    defaults = dict(
        entry_price=0.45, current_price=0.52, bid_price=0.50,
        scaled_out_50=False, sport_tag="nhl", direction="BUY_YES",
        spread_line=1.5,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_returns_none_when_score_info_missing():
    sig = check_nhl_puck_line_exit(_pos(), {}, 0.5, NHLPuckLineExitConfig(), {})
    assert sig is None


def test_returns_none_when_clock_seconds_missing():
    score_info = {
        "available": True, "period": 3, "our_score": 2, "opp_score": 1,
        "clock_seconds": None,
    }
    sig = check_nhl_puck_line_exit(_pos(), score_info, 0.5, NHLPuckLineExitConfig(), {})
    assert sig is None


def test_near_resolve_when_bid_high():
    pos = _pos(bid_price=0.95)
    score_info = {
        "available": True, "period": 3, "clock_seconds": 300,
        "our_score": 3, "opp_score": 1,
    }
    sig = check_nhl_puck_line_exit(pos, score_info, 0.5, NHLPuckLineExitConfig(), {})
    assert sig is not None
    assert sig.reason == ExitReason.NHL_PUCK_LINE_NEAR_RESOLVE


def test_scale_out_partial():
    pos = _pos(bid_price=0.87, scaled_out_50=False)
    score_info = {
        "available": True, "period": 3, "clock_seconds": 200,
        "our_score": 3, "opp_score": 1,
    }
    sig = check_nhl_puck_line_exit(pos, score_info, 0.5, NHLPuckLineExitConfig(), {})
    assert sig is not None
    assert sig.reason == ExitReason.NHL_PUCK_LINE_SCALE_OUT
    assert sig.partial is True


def test_buy_yes_predictive_dead_when_one_goal_lead_late():
    """BUY_YES, +1 lead, P3 600s → empirical p_cover 0.13, bid 0.50 → 0.13 < 0.53 → PREDICTIVE_DEAD.
    PREDICTIVE_DEAD yalnızca empirical kalibrasyon altında fire eder; mock table provide ediliyor."""
    pos = _pos(direction="BUY_YES", bid_price=0.50)
    score_info = {
        "available": True, "period": 3, "clock_seconds": 600,
        "our_score": 2, "opp_score": 1,  # +1 lead favori
    }
    table = {"puck_line_cover": {"3_1_600": {"p_favorite_covers": 0.13}}}
    sig = check_nhl_puck_line_exit(pos, score_info, 0.5, NHLPuckLineExitConfig(), table)
    assert sig is not None
    assert sig.reason == ExitReason.NHL_PUCK_LINE_PREDICTIVE_DEAD


def test_hold_when_two_goal_lead_high_p_cover():
    """+2 lead P3 600s → p_cover ~0.95 (Skellam), bid 0.45 → no PREDICTIVE_DEAD, no NEAR_RESOLVE."""
    pos = _pos(bid_price=0.45, current_price=0.52)
    score_info = {
        "available": True, "period": 3, "clock_seconds": 600,
        "our_score": 3, "opp_score": 1,  # +2 lead
    }
    sig = check_nhl_puck_line_exit(pos, score_info, 0.5, NHLPuckLineExitConfig(), {})
    assert sig is None


def test_period_1_predictive_dead_skipped_pre_p3_guard():
    """NBA Q4-only paraleli: NHL P1/P2'de PREDICTIVE_DEAD pasif. Empirical hit
    olsa ve p_cover bid'in altında olsa bile P3 başlamadan tetiklenmez —
    skor henüz 'geri dönülemez' değil. NEAR_RESOLVE/SCALE_OUT/STRUCTURAL_DAMAGE
    + dolar SL koruma sağlar."""
    pos = _pos(direction="BUY_YES", bid_price=0.39)
    score_info = {
        "available": True, "period_number": 1, "clock_seconds": 1140,
        "our_score": 0, "opp_score": 0,
    }
    # Clock dönüşümü çalışıyor: P1 + 1140s period clock → 3540s regulation.
    # Empirical key '1_0_3540' var ve p_cover 0.10, ama period<3 → skip.
    table = {"puck_line_cover": {"1_0_3540": {"p_favorite_covers": 0.10}}}
    sig = check_nhl_puck_line_exit(pos, score_info, 0.0, NHLPuckLineExitConfig(), table)
    assert sig is None
