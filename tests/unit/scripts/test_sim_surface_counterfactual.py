"""SPEC-SIM2 testleri — saf fonksiyonlar, ağ/disk yok."""
from __future__ import annotations

import pytest

from src.domain.pricing.tennis.match_record import MatchRecord

from scripts.sim_surface_counterfactual import (
    GateDecision,
    build_cutoff_snapshots,
    decide_gate,
)


def _match(date: str, surface: str, winner: str, loser: str) -> MatchRecord:
    return MatchRecord(
        tourney_id="t1", tourney_name="Test Open", tourney_date=date,
        surface=surface, winner_name=winner, loser_name=loser,
        w_svpt=80, w_1st_in=50, w_1st_won=40, w_2nd_won=15, w_sv_gms=12,
        l_svpt=80, l_1st_in=48, l_1st_won=33, l_2nd_won=12, l_sv_gms=12,
        best_of=3, score="6-4 6-4",
    )


def _gate(**over):
    """decide_gate için makul defaultlar; test ilgili alanı override eder."""
    kw = dict(
        market_type="moneyline",
        new_prob=0.70,
        yes_price=0.61,
        confidence="A",
        has_sharp=True,
        actual_direction="BUY_YES",
        min_edge=0.06,
        bimodal_floor=0.20,
        ml_size_a=50.0,
        bimodal_size_a=15.0,
        event_key="ev1",
        event_positions={},
    )
    kw.update(over)
    return decide_gate(**kw)


def test_decide_totals_market_always_skipped():
    d = _gate(market_type="tennis_match_totals")
    assert d.action == "SKIP"
    assert d.reason == "ou_removed"


def test_decide_surface_unknown_skipped():
    d = _gate(new_prob=None)
    assert d.action == "SKIP"
    assert d.reason == "surface_or_model"


def test_decide_same_direction_when_edge_holds():
    d = _gate(new_prob=0.70, yes_price=0.61, actual_direction="BUY_YES")
    assert d == GateDecision(
        action="SAME", reason="", direction="BUY_YES",
        eff_entry=0.61, size_usdc=50.0,
    )


def test_decide_flips_direction_when_model_favors_other_side():
    d = _gate(new_prob=0.40, yes_price=0.61, actual_direction="BUY_YES")
    assert d.action == "FLIP"
    assert d.direction == "BUY_NO"
    assert d.eff_entry == pytest.approx(0.39)
    assert d.size_usdc == 50.0


def test_decide_below_min_edge_skipped():
    d = _gate(new_prob=0.64, yes_price=0.61)
    assert d.action == "SKIP"
    assert d.reason == "edge"


def test_bimodal_floor_blocks_low_price_entry():
    d = _gate(
        market_type="tennis_set_handicap",
        new_prob=0.30, yes_price=0.15, actual_direction="BUY_YES",
    )
    assert d.action == "SKIP"
    assert d.reason == "bimodal_floor"


def test_decide_non_a_confidence_skipped():
    assert _gate(confidence="B").reason == "confidence"
    assert _gate(has_sharp=False).reason == "confidence"
    assert _gate(confidence="B").action == "SKIP"


def test_decide_event_guard_same_type_blocks():
    d = _gate(event_positions={"ev1": {"moneyline"}})
    assert d.action == "SKIP"
    assert d.reason == "event_guard"
    # Farklı event → engel yok
    d2 = _gate(event_positions={"baska_ev": {"moneyline"}})
    assert d2.action == "SAME"
    # Aynı event 3 farklı tip dolu → cap
    d3 = _gate(
        market_type="tennis_set_handicap", new_prob=0.70, yes_price=0.45,
        event_positions={"ev1": {"moneyline", "tennis_first_set_winner", "tennis_set_totals"}},
    )
    assert d3.action == "SKIP"
    assert d3.reason == "event_guard"


def test_decide_bimodal_size_used_for_set_handicap():
    d = _gate(market_type="tennis_set_handicap", new_prob=0.70, yes_price=0.45)
    assert d.action == "SAME"
    assert d.size_usdc == 15.0


def test_ratings_cutoff_excludes_matches_on_or_after_date():
    matches = [
        _match("20260601", "Hard", "Alice A", "Bob B"),
        _match("20260607", "Hard", "Carol C", "Dave D"),  # cutoff sonrası — fit'e girmez
    ]
    flat, by_surface = build_cutoff_snapshots(
        matches, cutoff_yyyymmdd="20260606", surface_phi_fallback=1000.0,
    )
    assert "Alice A" in flat and "Bob B" in flat
    assert "Carol C" not in flat and "Dave D" not in flat
    assert "Carol C" not in by_surface["Hard"]
    # Kazanan reytingi kaybedenden yüksek
    assert flat["Alice A"].rating.mu > flat["Bob B"].rating.mu


def test_cutoff_snapshots_surface_split_separate_ratings():
    # Alice Hard'da kazanır, Clay'de kaybeder → yüzeye özgü reytingler zıt yönde
    matches = [
        _match("20260501", "Hard", "Alice A", "Bob B"),
        _match("20260510", "Clay", "Bob B", "Alice A"),
    ]
    _, by_surface = build_cutoff_snapshots(
        matches, cutoff_yyyymmdd="20260606", surface_phi_fallback=1000.0,
    )
    assert by_surface["Hard"]["Alice A"].rating.mu > by_surface["Hard"]["Bob B"].rating.mu
    assert by_surface["Clay"]["Bob B"].rating.mu > by_surface["Clay"]["Alice A"].rating.mu
    # Serve verisi her iki yüzeyde de oyuncuya bağlanmış (model fallback'i için)
    assert "Hard" in by_surface["Hard"]["Alice A"].serve_by_surface
