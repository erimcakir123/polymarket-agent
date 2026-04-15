"""stock_queue.py için birim testler."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.models.market import MarketData
from src.orchestration.stock_queue import StockConfig, StockEntry, StockQueue


def _market(cid: str = "c1", ms_offset_hours: float = 2.0, volume: float = 100.0) -> MarketData:
    start = datetime.now(timezone.utc) + timedelta(hours=ms_offset_hours)
    return MarketData(
        condition_id=cid,
        question="Q", slug=f"s-{cid}",
        yes_token_id="y", no_token_id="n",
        yes_price=0.5, no_price=0.5,
        liquidity=10000.0, volume_24h=volume,
        end_date_iso=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        match_start_iso=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        sport_tag="mlb",
        event_id=f"ev-{cid}",
    )


def test_add_new_market_creates_entry() -> None:
    sq = StockQueue(StockConfig())
    assert sq.add(_market("c1"), "exposure_cap_reached") is True
    assert sq.count() == 1
    assert sq.has("c1")


def test_add_non_pushable_reason_rejected() -> None:
    sq = StockQueue(StockConfig())
    assert sq.add(_market("c1"), "blacklisted") is False
    assert sq.count() == 0


def test_add_existing_updates_not_duplicates() -> None:
    sq = StockQueue(StockConfig())
    sq.add(_market("c1"), "exposure_cap_reached")
    sq.add(_market("c1"), "no_edge")
    assert sq.count() == 1
    entry = sq.all_entries()[0]
    assert entry.last_skip_reason == "no_edge"
    assert entry.no_edge_attempts == 1


def test_no_edge_attempts_reset_on_other_reason() -> None:
    sq = StockQueue(StockConfig())
    sq.add(_market("c1"), "no_edge")
    sq.add(_market("c1"), "no_edge")
    sq.add(_market("c1"), "exposure_cap_reached")  # reset
    entry = sq.all_entries()[0]
    assert entry.no_edge_attempts == 0


def test_remove() -> None:
    sq = StockQueue(StockConfig())
    sq.add(_market("c1"), "no_edge")
    sq.remove("c1")
    assert sq.count() == 0


def test_top_n_by_match_start_ascending() -> None:
    sq = StockQueue(StockConfig())
    sq.add(_market("far", ms_offset_hours=12), "no_edge")
    sq.add(_market("near", ms_offset_hours=1), "no_edge")
    sq.add(_market("mid", ms_offset_hours=6), "no_edge")
    top = sq.top_n_by_match_start(2)
    assert [m.condition_id for m in top] == ["near", "mid"]


def test_top_n_zero_returns_empty() -> None:
    sq = StockQueue(StockConfig())
    sq.add(_market("c1"), "no_edge")
    assert sq.top_n_by_match_start(0) == []


def test_refresh_from_scan_updates_market_and_drops_delisted() -> None:
    sq = StockQueue(StockConfig())
    sq.add(_market("c1"), "no_edge")
    sq.add(_market("c2"), "no_edge")

    # Fresh scan: c1 price changed, c2 not in scan
    fresh_c1 = _market("c1")
    fresh_c1 = fresh_c1.model_copy(update={"yes_price": 0.75})

    refreshed = sq.refresh_from_scan({"c1": fresh_c1})
    assert refreshed == 1
    assert not sq.has("c2")  # delisted
    assert sq.all_entries()[0].market.yes_price == 0.75


def test_evict_ttl_by_first_seen() -> None:
    cfg = StockConfig(ttl_hours=1.0)
    sq = StockQueue(cfg)
    sq.add(_market("c1"), "no_edge")
    # Simulate 2h passage
    now = datetime.now(timezone.utc) + timedelta(hours=2)
    sq.evict_expired(now=now)
    assert sq.count() == 0


def test_evict_pre_match_cutoff() -> None:
    cfg = StockConfig(pre_match_cutoff_min=30.0)
    sq = StockQueue(cfg)
    # Match 15 min ahead — inside cutoff → evict
    m = _market("c1", ms_offset_hours=0.25)
    sq.add(m, "no_edge")
    sq.evict_expired()
    assert sq.count() == 0


def test_evict_no_edge_attempts_cap() -> None:
    cfg = StockConfig(max_no_edge_attempts=2)
    sq = StockQueue(cfg)
    sq.add(_market("c1"), "no_edge")
    sq.add(_market("c1"), "no_edge")  # 2 attempts
    sq.evict_expired()
    assert sq.count() == 0


def test_evict_event_already_open() -> None:
    sq = StockQueue(StockConfig())
    sq.add(_market("c1"), "no_edge")
    # c1'in event_id'si "ev-c1"
    sq.evict_expired(open_event_ids=frozenset({"ev-c1"}))
    assert sq.count() == 0


def test_persistence_save_load_roundtrip(tmp_path) -> None:
    from src.infrastructure.persistence.stock_snapshot import StockSnapshot
    snap = StockSnapshot(str(tmp_path / "stock.json"))
    sq1 = StockQueue(StockConfig(), snapshot=snap)
    sq1.add(_market("c1"), "no_edge")
    sq1.add(_market("c2"), "exposure_cap_reached")
    sq1.save()

    sq2 = StockQueue(StockConfig(), snapshot=snap)
    loaded = sq2.load()
    assert loaded == 2
    assert sq2.has("c1")
    assert sq2.has("c2")
