from src.domain.pricing.tennis.match_record import MatchRecord
from src.domain.pricing.tennis.surface_map import build_surface_map, normalize_name


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


def test_build_surface_map_excludes_ambiguous_city():
    # aynı çekirdek hem Grass hem Hard → belirsiz → dışlanır
    m = build_surface_map([_rec("Nottingham", "Grass"), _rec("Nottingham CH", "Hard")])
    assert "nottingham" not in m


def test_build_surface_map_strips_level_tags():
    m = build_surface_map([_rec("M25 Cattolica", "Clay"), _rec("Ilkley CH", "Grass")])
    assert m["cattolica"] == "Clay"
    assert m["ilkley"] == "Grass"


def test_normalize_strips_apostrophe():
    assert normalize_name("Queen's Club") == "queens club"


def test_build_surface_map_skips_unknown_surface():
    assert build_surface_map([_rec("Y", "Unknown")]) == {}


def test_build_surface_map_skips_empty_name():
    assert build_surface_map([_rec("", "Grass")]) == {}
