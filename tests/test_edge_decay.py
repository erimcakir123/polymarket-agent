# tests/test_edge_decay.py
import pytest


class TestEdgeDecay:
    def test_full_strength_early(self):
        from src.edge_decay import get_edge_decay_factor
        assert get_edge_decay_factor(0.10) == 1.0

    def test_quarter_strength_late(self):
        from src.edge_decay import get_edge_decay_factor
        assert get_edge_decay_factor(0.90) == 0.25

    def test_decayed_target_early_match(self):
        from src.edge_decay import get_decayed_ai_target
        # At 10% elapsed, decay=1.0, target = current + (ai - current) * 1.0 = ai
        target = get_decayed_ai_target(0.70, 0.50, 0.10)
        assert abs(target - 0.70) < 0.01

    def test_decayed_target_late_match(self):
        from src.edge_decay import get_decayed_ai_target
        # At 90% elapsed, decay=0.25, target = 0.50 + (0.70 - 0.50) * 0.25 = 0.55
        target = get_decayed_ai_target(0.70, 0.50, 0.90)
        assert abs(target - 0.55) < 0.01
