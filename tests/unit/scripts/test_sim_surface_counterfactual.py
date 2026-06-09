"""SPEC-SIM2 testleri — saf fonksiyonlar, ağ/disk yok."""
from __future__ import annotations

import pytest

from src.domain.pricing.tennis.match_record import MatchRecord

from scripts.sim_surface_counterfactual import (
    GateDecision,
    build_cutoff_snapshots,
    decide_gate,
    invert_series,
    link_token_ids,
    load_tennis_entries,
    synth_event_links,
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
    flat, by_surface = build_cutoff_snapshots(
        matches, cutoff_yyyymmdd="20260606", surface_phi_fallback=1000.0,
    )
    assert by_surface["Hard"]["Alice A"].rating.mu > by_surface["Hard"]["Bob B"].rating.mu
    assert by_surface["Clay"]["Bob B"].rating.mu > by_surface["Clay"]["Alice A"].rating.mu
    # Serve verisi her iki yüzeyde de oyuncuya bağlanmış (model fallback'i için)
    assert "Hard" in by_surface["Hard"]["Alice A"].serve_by_surface
    # KRİTİK (canlı pariteyi taklit): hiç çim maçı olmayan oyuncu çim listesinde
    # YİNE DE var — genel (overall) reytingine düşer (load_surface_ratings davranışı)
    assert "Alice A" in by_surface["Grass"]
    assert by_surface["Grass"]["Alice A"].rating.mu == pytest.approx(flat["Alice A"].rating.mu)


def test_event_link_set_handicap_gets_tournament_from_moneyline_same_players():
    entries = [
        {"question": "Birmingham: Alexandra Eala vs Rebeka Masarova",
         "slug": "wta-eala-masarov-2026-06-06"},
        {"question": "Set Handicap: Eala (-1.5) vs Masarova (+1.5)",
         "slug": "wta-eala-masarov-2026-06-06-set-handicap-home-1pt5"},
        # Slug'da oyuncu sırası ters olsa da aynı maça bağlanmalı
        {"question": "Set Handicap: Masarova (-1.5) vs Eala (+1.5)",
         "slug": "wta-masarov-eala-2026-06-06-set-handicap-away-1pt5"},
        # Başka maç — moneyline'ı yok → turnuva eşlenmez
        {"question": "Set Handicap: Sonego (-1.5) vs Alkaya (+1.5)",
         "slug": "atp-sonego-alkaya-2026-06-06-set-handicap-home-1pt5"},
    ]
    idx_to_event, event_tournaments = synth_event_links(entries)
    assert idx_to_event[0] == idx_to_event[1] == idx_to_event[2]
    assert event_tournaments[idx_to_event[1]] == "Birmingham"
    assert idx_to_event[3] != idx_to_event[0]
    assert idx_to_event[3] not in event_tournaments


def test_invert_series_no_side_prices_and_entry():
    assert invert_series([(100.0, 0.61), (160.0, 0.97)]) == [
        (100.0, 0.39), (160.0, 0.03),
    ]


def _jsonl(tmp_path, name, rows):
    import json
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return p


def test_load_tennis_entries_filters_kind_and_sport(tmp_path):
    p = _jsonl(tmp_path, "events.jsonl", [
        {"kind": "entry", "sport_tag": "tennis", "slug": "b",
         "entry_timestamp": "2026-06-07T10:00:00+00:00"},
        {"kind": "final", "sport_tag": "tennis", "slug": "x"},
        {"kind": "entry", "sport_tag": "basketball", "slug": "y"},
        {"kind": "entry", "sport_tag": "tennis", "slug": "a",
         "entry_timestamp": "2026-06-06T09:00:00+00:00"},
    ])
    out = load_tennis_entries(p)
    assert [e["slug"] for e in out] == ["a", "b"]  # kronolojik


def test_link_token_id_matches_buy_exec_by_time_and_size(tmp_path):
    entries = [
        {"entry_timestamp": "2026-06-06T10:58:36+00:00", "size_usdc": 50.0},
        {"entry_timestamp": "2026-06-06T12:00:00+00:00", "size_usdc": 15.0},
    ]
    execs = _jsonl(tmp_path, "execs.jsonl", [
        {"ts": "2026-06-06T10:58:37+00:00", "side": "BUY",
         "target_size_usdc": 50.0, "token_id": "tokA"},
        {"ts": "2026-06-06T10:59:00+00:00", "side": "SELL",
         "target_size_usdc": 50.0, "token_id": "tokSELL"},
        {"ts": "2026-06-06T18:00:00+00:00", "side": "BUY",
         "target_size_usdc": 15.0, "token_id": "tokFAR"},  # pencere dışı
    ])
    links = link_token_ids(entries, execs, window_sec=180)
    assert links[0] == "tokA"
    assert links[1] is None
