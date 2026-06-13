"""tennis_results_store — taze sonuç jsonl yaz/oku/dedupe testleri."""
from src.domain.pricing.tennis.harvested_result import HarvestedResult
from src.infrastructure.data.tennis_results_store import (
    append_results,
    harvested_keys,
    load_results,
)


def _r(w, l, d="20260612", s="Clay"):
    return HarvestedResult(winner=w, loser=l, surface=s, date=d)


def test_append_then_load_roundtrip(tmp_path):
    p = tmp_path / "res.jsonl"
    append_results([_r("Alice", "Bob"), _r("Carol", "Dave")], p)
    out = load_results(p)
    assert len(out) == 2
    assert out[0].winner == "Alice" and out[0].surface == "Clay"


def test_append_dedupes_same_match_key(tmp_path):
    p = tmp_path / "res.jsonl"
    append_results([_r("Alice", "Bob")], p)
    append_results([_r("Alice", "Bob"), _r("Eve", "Frank")], p)
    out = load_results(p)
    assert len(out) == 2  # Alice/Bob tekrar yazılmadı


def test_harvested_keys_returns_existing_match_keys(tmp_path):
    p = tmp_path / "res.jsonl"
    append_results([_r("Alice", "Bob", d="20260610")], p)
    keys = harvested_keys(p)
    assert "20260610|Alice|Bob" in keys


def test_load_missing_file_returns_empty(tmp_path):
    assert load_results(tmp_path / "yok.jsonl") == []


def test_load_skips_corrupt_line(tmp_path):
    p = tmp_path / "res.jsonl"
    p.write_text('{"winner":"A","loser":"B","surface":"Clay","date":"20260612"}\nBOZUK\n', encoding="utf-8")
    out = load_results(p)
    assert len(out) == 1 and out[0].winner == "A"
