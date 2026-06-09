from src.infrastructure.data.tennis_surface_map_store import save_surface_map, load_surface_map


def test_save_then_load_roundtrip(tmp_path):
    p = tmp_path / "surf.json"
    save_surface_map({"ilkley": "Grass", "cattolica": "Clay"}, p)
    assert load_surface_map(p) == {"ilkley": "Grass", "cattolica": "Clay"}


def test_load_missing_file_returns_empty(tmp_path):
    assert load_surface_map(tmp_path / "nope.json") == {}


def test_load_corrupt_file_returns_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert load_surface_map(p) == {}
