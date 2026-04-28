"""NHL totals dispatch wiring tests."""
from __future__ import annotations

from types import SimpleNamespace

from src.models.enums import ExitReason
from src.strategy.exit._nhl_totals_dispatch import check_nhl_totals_exit
from src.strategy.exit.nhl_totals_exit import NHLTotalsExitConfig


def _pos(**kw):
    defaults = dict(
        entry_price=0.45, current_price=0.52, bid_price=0.50,
        scaled_out_50=False, sport_tag="nhl", direction="BUY_YES",
        total_line=5.5, total_side="over",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_returns_none_when_score_info_missing():
    sig = check_nhl_totals_exit(_pos(), {}, 0.5, NHLTotalsExitConfig(), {})
    assert sig is None


def test_returns_none_when_total_line_missing():
    pos = _pos(total_line=None)
    score_info = {"available": True, "period": 3, "clock_seconds": 300, "our_score": 3, "opp_score": 2}
    sig = check_nhl_totals_exit(pos, score_info, 0.5, NHLTotalsExitConfig(), {})
    assert sig is None


def test_near_resolve_when_bid_high():
    pos = _pos(bid_price=0.95)
    score_info = {"available": True, "period": 3, "clock_seconds": 300, "our_score": 4, "opp_score": 2}
    sig = check_nhl_totals_exit(pos, score_info, 0.5, NHLTotalsExitConfig(), {})
    assert sig is not None
    assert sig.reason == ExitReason.NHL_TOTALS_NEAR_RESOLVE


def test_predictive_dead_under_when_too_many_goals():
    """Under 5.5, current 6 → over zaten gerçekleşti, p_under=0 → PREDICTIVE_DEAD."""
    pos = _pos(total_side="under", bid_price=0.20, total_line=5.5)
    score_info = {"available": True, "period": 3, "clock_seconds": 300, "our_score": 3, "opp_score": 3}
    sig = check_nhl_totals_exit(pos, score_info, 0.5, NHLTotalsExitConfig(), {})
    assert sig is not None
    assert sig.reason == ExitReason.NHL_TOTALS_PREDICTIVE_DEAD


def test_uses_current_total_from_scores():
    """current_total = our_score + opp_score doğru hesaplanır, hold beklenir."""
    pos = _pos(total_side="over", bid_price=0.40, total_line=5.5)
    score_info = {"available": True, "period": 3, "clock_seconds": 600, "our_score": 5, "opp_score": 0}
    # current_total=5, target 5.5, kalan 10dk → p_over yüksek
    sig = check_nhl_totals_exit(pos, score_info, 0.5, NHLTotalsExitConfig(), {})
    assert sig is None
