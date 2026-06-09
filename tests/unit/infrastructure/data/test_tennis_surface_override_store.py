from src.infrastructure.data.tennis_surface_override_store import load_overrides, save_overrides


def test_roundtrip(tmp_path):
    p = tmp_path / "o.json"
    save_overrides({"queens club": {"surface": "Grass", "checked_at": "2026-06-09T00:00:00"}}, p)
    assert load_overrides(p)["queens club"]["surface"] == "Grass"


def test_load_missing_returns_empty(tmp_path):
    assert load_overrides(tmp_path / "no.json") == {}


def test_load_corrupt_returns_empty(tmp_path):
    p = tmp_path / "bad.json"; p.write_text("{nope", encoding="utf-8")
    assert load_overrides(p) == {}
