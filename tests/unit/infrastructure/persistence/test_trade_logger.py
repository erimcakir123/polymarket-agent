"""trade_logger.py için birim testler — sadece veri modeli + sport_tag ayrıştırıcı.

SPEC-Z17 (2026-06-04): TradeHistoryLogger sınıfı kaldırıldığı için ona ait
testler de silindi. Append-only event log testleri test_trade_event_log.py'de.
"""
from __future__ import annotations

from src.infrastructure.persistence.trade_logger import (
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


def test_trade_record_default_partial_exits_is_empty_list():
    """Yeni TradeRecord oluşturulduğunda partial_exits varsayılan boş liste."""
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
