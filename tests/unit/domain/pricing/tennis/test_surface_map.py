from src.domain.pricing.tennis.match_record import MatchRecord
from src.domain.pricing.tennis.surface_map import build_surface_map


def _rec(name, surface):
    return MatchRecord(
        tourney_id="x", tourney_name=name, tourney_date="20250609", surface=surface,
        winner_name="A", loser_name="B", w_svpt=1, w_1st_in=1, w_1st_won=1, w_2nd_won=1,
        w_sv_gms=1, l_svpt=1, l_1st_in=1, l_1st_won=1, l_2nd_won=1, l_sv_gms=1,
        best_of=3, score="6-4 6-4",
    )


def test_build_surface_map_normalizes_and_picks():
    m = build_surface_map([_rec("Ilkley", "Grass"), _rec("Ilkley", "Grass"),
                           _rec("Cattolica", "Clay"), _rec("ROME", "Clay")])
    assert m["ilkley"] == "Grass"
    assert m["cattolica"] == "Clay"
    assert m["rome"] == "Clay"


def test_build_surface_map_majority_when_mixed():
    assert build_surface_map([_rec("X Open", "Hard"), _rec("X Open", "Hard"),
                              _rec("X Open", "Clay")])["x open"] == "Hard"


def test_build_surface_map_skips_unknown_surface():
    assert build_surface_map([_rec("Y", "Unknown")]) == {}


def test_build_surface_map_skips_empty_name():
    assert build_surface_map([_rec("", "Grass")]) == {}
