"""
NHL Skellam math tests + cross-validation against MoneyPuck empirical table.
"""
from __future__ import annotations

import pytest
from src.domain.math.nhl_skellam import (
    trailing_team_win_probability,
    leading_team_win_probability,
    comeback_probability_to_tie,
    ot_3v3_coin_flip_probability,
    NHL_REGULATION_LAMBDA_PER_SEC,
    NHL_OT_3V3_LAMBDA_PER_SEC,
    NHL_OT_DURATION_SEC,
)
from src.domain.math.nhl_empirical_wp import (
    leading_team_win_probability_empirical,
    TABLE_PATH,
)


class TestSkellamSemantics:
    def test_deficit_zero_returns_one(self):
        assert trailing_team_win_probability(0, 600) == 1.0

    def test_zero_seconds_returns_zero(self):
        assert trailing_team_win_probability(2, 0) == 0.0

    def test_lead_zero_returns_zero(self):
        assert leading_team_win_probability(0, 600) == 0.0

    def test_lead_at_zero_seconds_returns_one(self):
        assert leading_team_win_probability(2, 0) == 1.0

    def test_leading_plus_trailing_equals_one(self):
        for d, s in [(1, 600), (2, 1200), (3, 1800)]:
            p_lead = leading_team_win_probability(d, s)
            p_trail = trailing_team_win_probability(d, s)
            assert abs(p_lead + p_trail - 1.0) < 1e-9


class TestSkellamMonotonicity:
    def test_more_time_more_comeback(self):
        d = 2
        p_300 = trailing_team_win_probability(d, 300)
        p_600 = trailing_team_win_probability(d, 600)
        p_1200 = trailing_team_win_probability(d, 1200)
        assert p_300 < p_600 < p_1200

    def test_bigger_deficit_lower_comeback(self):
        s = 600
        p1 = trailing_team_win_probability(1, s)
        p2 = trailing_team_win_probability(2, s)
        p3 = trailing_team_win_probability(3, s)
        assert p1 > p2 > p3

    def test_tie_prob_higher_than_win_prob(self):
        for d, s in [(1, 300), (2, 600), (3, 1200)]:
            p_tie = comeback_probability_to_tie(d, s)
            p_win = trailing_team_win_probability(d, s)
            assert p_tie > p_win


class TestOTLambda:
    def test_ot_lambda_higher_than_reg(self):
        assert NHL_OT_3V3_LAMBDA_PER_SEC > NHL_REGULATION_LAMBDA_PER_SEC
        ratio = NHL_OT_3V3_LAMBDA_PER_SEC / NHL_REGULATION_LAMBDA_PER_SEC
        assert 1.5 < ratio < 1.8

    def test_ot_lambda_yields_higher_comeback(self):
        d, s = 1, 180
        p_reg = trailing_team_win_probability(d, s, NHL_REGULATION_LAMBDA_PER_SEC)
        p_ot = trailing_team_win_probability(d, s, NHL_OT_3V3_LAMBDA_PER_SEC)
        assert p_ot > p_reg

    def test_ot_coin_flip_returns_half(self):
        assert ot_3v3_coin_flip_probability() == 0.5


class TestPublishedGroundTruth:
    def test_3_gol_p3_basi_tsn_2015(self):
        """TSN 2015: 'down 3 goals start of P3' = ~2.5%."""
        p = trailing_team_win_probability(3, 1200)
        assert 0.005 < p < 0.06, f"Got {p:.4f}, TSN published ~2.5%"


@pytest.mark.skipif(
    not TABLE_PATH.exists(),
    reason="Empirical table missing — run scripts/build_nhl_empirical_table.py"
)
class TestCrossValidationAgainstEmpirical:
    """
    Skellam vs empirical (MoneyPuck) tolerance:
    - +/-10pp mid-game / P3 start
    - +/-15pp last 5min (EN effect begins)
    - +/-25pp last 60s (EN heavy, Skellam underestimate expected)
    """

    @pytest.mark.parametrize("period,deficit,seconds,tolerance_pp", [
        (3, 3, 1200, 10),
        (3, 2, 1200, 10),
        (3, 1, 1200, 10),
        (3, 1, 600,  10),
        (3, 1, 300,  15),
        (3, 1, 60,   25),
        (3, 2, 300,  10),
        (3, 2, 60,   10),
    ])
    def test_skellam_within_tolerance_of_empirical(
        self, period: int, deficit: int, seconds: int, tolerance_pp: int
    ) -> None:
        p_emp_lead = leading_team_win_probability_empirical(period, deficit, seconds)
        if p_emp_lead is None:
            pytest.skip("Insufficient empirical sample")

        p_emp_trail = 1.0 - p_emp_lead
        p_skel = trailing_team_win_probability(deficit, seconds)

        diff_pp = abs(p_skel - p_emp_trail) * 100
        assert diff_pp <= tolerance_pp, (
            f"period={period}, deficit={deficit}, seconds={seconds}: "
            f"empirical={p_emp_trail*100:.1f}%, skellam={p_skel*100:.1f}%, "
            f"diff={diff_pp:.1f}pp > tolerance {tolerance_pp}pp"
        )
