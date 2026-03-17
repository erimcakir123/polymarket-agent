import pytest


def test_track_win_loss():
    from src.performance_tracker import PerformanceTracker
    pt = PerformanceTracker()
    pt.record_trade("politics", won=True, edge=0.10)
    pt.record_trade("politics", won=True, edge=0.08)
    pt.record_trade("politics", won=False, edge=0.07)
    assert pt.win_rate("politics") == pytest.approx(2 / 3)
    assert pt.overall_win_rate() == pytest.approx(2 / 3)


def test_category_underperformance():
    from src.performance_tracker import PerformanceTracker
    pt = PerformanceTracker()
    for _ in range(10):
        pt.record_trade("crypto", won=False, edge=0.05)
    assert pt.win_rate("crypto") == 0.0
    recs = pt.get_recommendations(min_win_rate=0.50, min_trades=5)
    assert "crypto" in recs.get("exclude_categories", [])


def test_edge_accuracy():
    from src.performance_tracker import PerformanceTracker
    pt = PerformanceTracker()
    pt.record_trade("politics", won=True, edge=0.10, ai_prob=0.70, actual_resolved_yes=True)
    pt.record_trade("politics", won=False, edge=0.08, ai_prob=0.65, actual_resolved_yes=False)
    brier = pt.brier_score()
    assert 0 <= brier <= 1
