"""trade_logger.py için birim testler."""
from __future__ import annotations

from pathlib import Path

from src.infrastructure.persistence.trade_logger import (
    TradeHistoryLogger,
    TradeRecord,
    _split_sport_tag,
)


def _valid_record(**overrides) -> TradeRecord:
    base = dict(
        slug="lakers-vs-celtics",
        condition_id="0xabc",
        event_id="evt_1",
        token_id="tokY",
        sport_tag="basketball_nba",
        sport_category="basketball",
        league="nba",
        direction="BUY_YES",
        entry_price=0.45,
        size_usdc=40.0,
        shares=88.88,
        confidence="B",
        bookmaker_prob=0.58,
        anchor_probability=0.58,
        num_bookmakers=12.0,
        has_sharp=True,
        entry_reason="normal",
        entry_timestamp="2026-04-13T20:00:00Z",
    )
    base.update(overrides)
    return TradeRecord(**base)


def test_split_sport_tag_basketball_nba() -> None:
    assert _split_sport_tag("basketball_nba") == ("basketball", "nba")


def test_split_sport_tag_tennis_dynamic() -> None:
    assert _split_sport_tag("tennis_atp_french_open") == ("tennis", "atp_french_open")


def test_split_sport_tag_empty_returns_empty() -> None:
    assert _split_sport_tag("") == ("", "")


def test_split_sport_tag_no_underscore() -> None:
    assert _split_sport_tag("basketball") == ("basketball", "")


def test_trade_record_entry_fields() -> None:
    r = _valid_record()
    assert r.slug == "lakers-vs-celtics"
    assert r.entry_price == 0.45
    assert r.sport_category == "basketball"
    assert r.league == "nba"
    assert r.confidence == "B"


def test_trade_record_bookmaker_fields() -> None:
    r = _valid_record(num_bookmakers=15.5, has_sharp=True)
    assert r.num_bookmakers == 15.5
    assert r.has_sharp is True


def test_trade_record_match_timeline_default_empty() -> None:
    r = _valid_record()
    assert r.match_timeline == []


def test_trade_record_resolution_default_unresolved() -> None:
    r = _valid_record()
    assert r.final_outcome == "unresolved"
    assert r.we_were_right is None
    assert r.resolution_timestamp == ""


def test_trade_record_exit_defaults() -> None:
    r = _valid_record()
    assert r.exit_price is None
    assert r.exit_reason == ""
    assert r.exit_pnl_usdc == 0.0


def test_trade_record_full_lifecycle_json_roundtrip() -> None:
    r = _valid_record(
        match_timeline=[
            {"ts": "2026-04-13T20:15:00Z", "score": "12-8", "period": "Q1", "current_price": 0.48, "pnl_pct": 0.067},
            {"ts": "2026-04-13T20:45:00Z", "score": "45-40", "period": "Q2", "current_price": 0.55, "pnl_pct": 0.222},
        ],
        exit_price=0.52,
        exit_reason="scale_out",
        exit_pnl_usdc=6.22,
        exit_pnl_pct=0.155,
        exit_timestamp="2026-04-13T21:00:00Z",
        final_outcome="YES",
        we_were_right=True,
        resolution_timestamp="2026-04-13T22:30:00Z",
        resolution_source="gamma",
    )
    data = r.model_dump(mode="json")
    restored = TradeRecord(**data)
    assert restored.match_timeline[0]["score"] == "12-8"
    assert restored.final_outcome == "YES"
    assert restored.we_were_right is True


def test_logger_log_appends_jsonl_line(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "trade_history.jsonl"))
    log.log(_valid_record(slug="a-b"))
    log.log(_valid_record(slug="c-d"))
    rows = log.read_recent(10)
    assert len(rows) == 2
    assert rows[0]["slug"] == "a-b"
    assert rows[1]["slug"] == "c-d"


def test_logger_read_recent_last_n(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "t.jsonl"))
    for i in range(20):
        log.log(_valid_record(slug=f"m-{i}"))
    recent = log.read_recent(5)
    assert len(recent) == 5
    assert recent[-1]["slug"] == "m-19"
    assert recent[0]["slug"] == "m-15"


def test_logger_read_all(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "t.jsonl"))
    log.log(_valid_record(slug="x"))
    log.log(_valid_record(slug="y"))
    rows = log.read_all()
    assert len(rows) == 2


def test_logger_missing_file_returns_empty(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "nope.jsonl"))
    assert log.read_recent(10) == []
    assert log.read_all() == []


def test_logger_creates_parent_dir(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "deep" / "nested" / "t.jsonl"))
    log.log(_valid_record())
    assert (tmp_path / "deep" / "nested" / "t.jsonl").exists()


def test_update_on_exit_fills_exit_fields(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "t.jsonl"))
    log.log(_valid_record(slug="match-1", condition_id="c1"))
    ok = log.update_on_exit("c1", {
        "exit_price": 0.72, "exit_reason": "scale_out",
        "exit_pnl_usdc": 12.5, "exit_pnl_pct": 0.18,
        "exit_timestamp": "2026-04-14T23:00:00Z",
    })
    assert ok is True
    rows = log.read_all()
    assert len(rows) == 1
    assert rows[0]["exit_price"] == 0.72
    assert rows[0]["exit_reason"] == "scale_out"


def test_update_on_exit_only_touches_open_record(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "t.jsonl"))
    # Aynı condition_id için kapalı + açık iki kayıt (re-entry senaryosu)
    log.log(_valid_record(condition_id="c1"))
    log.update_on_exit("c1", {"exit_price": 0.5, "exit_pnl_usdc": 1.0})
    log.log(_valid_record(condition_id="c1"))  # ikinci (açık) pozisyon
    log.update_on_exit("c1", {"exit_price": 0.8, "exit_pnl_usdc": 5.0})
    rows = log.read_all()
    assert rows[0]["exit_price"] == 0.5
    assert rows[1]["exit_price"] == 0.8


def test_update_on_exit_no_match_returns_false(tmp_path: Path) -> None:
    log = TradeHistoryLogger(str(tmp_path / "t.jsonl"))
    log.log(_valid_record(condition_id="c1"))
    assert log.update_on_exit("nonexistent", {"exit_price": 0.5}) is False


def test_trade_record_default_partial_exits_is_empty_list():
    """Yeni TradeRecord oluşturulduğunda partial_exits varsayılan boş liste."""
    from src.infrastructure.persistence.trade_logger import TradeRecord
    record = TradeRecord(
        slug="x", condition_id="cid", event_id="e", token_id="t",
        sport_tag="mlb", sport_category="mlb", league="",
        direction="BUY_YES", entry_price=0.5, size_usdc=50.0, shares=100.0,
        confidence="A", bookmaker_prob=0.6, anchor_probability=0.6,
        entry_reason="consensus", entry_timestamp="2026-04-15T00:00:00Z",
    )
    assert record.partial_exits == []


def test_trade_record_accepts_partial_exits():
    """TradeRecord partial_exits listesi kabul etmeli."""
    from src.infrastructure.persistence.trade_logger import TradeRecord
    pe_data = [{"tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0,
                "timestamp": "2026-04-15T01:00:00Z"}]
    record = TradeRecord(
        slug="x", condition_id="cid", event_id="e", token_id="t",
        sport_tag="mlb", sport_category="mlb", league="",
        direction="BUY_YES", entry_price=0.5, size_usdc=50.0, shares=100.0,
        confidence="A", bookmaker_prob=0.6, anchor_probability=0.6,
        entry_reason="consensus", entry_timestamp="2026-04-15T00:00:00Z",
        partial_exits=pe_data,
    )
    assert record.partial_exits == pe_data
