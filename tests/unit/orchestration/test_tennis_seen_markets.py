"""tennis_seen_markets — loglardan görülen tenis (cid, question) toplama."""
import json

from src.orchestration.tennis_seen_markets import collect_seen_tennis_markets


def _write(p, rows):
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_collects_tennis_dedupes_by_condition_id(tmp_path):
    skip = tmp_path / "skipped.jsonl"
    trades = tmp_path / "trades.jsonl"
    _write(skip, [
        {"condition_id": "0xa", "question": "Lyon: A vs B", "sport_tag": "tennis", "timestamp": "2026-06-12T10:00:00+00:00"},
        {"condition_id": "0xb", "question": "NBA X vs Y", "sport_tag": "nba", "timestamp": "2026-06-12T10:00:00+00:00"},
    ])
    _write(trades, [
        {"kind": "entry", "condition_id": "0xa", "question": "Lyon: A vs B", "sport_tag": "tennis", "entry_timestamp": "2026-06-12T09:00:00+00:00"},
        {"kind": "entry", "condition_id": "0xc", "question": "Modena: C vs D", "sport_tag": "tennis", "entry_timestamp": "2026-06-12T11:00:00+00:00"},
    ])
    out = collect_seen_tennis_markets([skip, trades])
    cids = {m["condition_id"] for m in out}
    assert cids == {"0xa", "0xc"}  # nba elendi, 0xa dedupe edildi


def test_missing_files_return_empty(tmp_path):
    assert collect_seen_tennis_markets([tmp_path / "yok.jsonl"]) == []


def test_since_cutoff_filters_old_markets(tmp_path):
    skip = tmp_path / "skipped.jsonl"
    _write(skip, [
        {"condition_id": "0xold", "question": "Lyon: A vs B", "sport_tag": "tennis", "timestamp": "2026-05-20T10:00:00+00:00"},
        {"condition_id": "0xnew", "question": "Modena: C vs D", "sport_tag": "tennis", "timestamp": "2026-06-12T10:00:00+00:00"},
    ])
    out = collect_seen_tennis_markets([skip], since_yyyymmdd="20260601")
    cids = {m["condition_id"] for m in out}
    assert cids == {"0xnew"}  # 05-20 backfill penceresi dışı, elendi
