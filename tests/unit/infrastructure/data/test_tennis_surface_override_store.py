from src.infrastructure.data.tennis_surface_override_store import load_overrides, save_overrides, is_stale


def test_roundtrip(tmp_path):
    p = tmp_path / "o.json"
    save_overrides({"queens club": {"surface": "Grass", "checked_at": "2026-06-09T00:00:00"}}, p)
    assert load_overrides(p)["queens club"]["surface"] == "Grass"


def test_load_missing_returns_empty(tmp_path):
    assert load_overrides(tmp_path / "no.json") == {}


def test_load_corrupt_returns_empty(tmp_path):
    p = tmp_path / "bad.json"; p.write_text("{nope", encoding="utf-8")
    assert load_overrides(p) == {}


def test_is_stale_true_when_old():
    assert is_stale("2026-06-01T00:00:00", "2026-06-09T00:00:00", 3) is True


def test_is_stale_false_when_recent():
    assert is_stale("2026-06-08T00:00:00", "2026-06-09T00:00:00", 3) is False


def test_is_stale_true_on_bad_timestamp():
    assert is_stale("garbage", "2026-06-09T00:00:00", 3) is True
