"""SPEC-Z17: append-only event log — tek kaynak, asla rewrite."""
import json
from pathlib import Path

from src.infrastructure.persistence.trade_event_log import TradeEventLog


def test_append_entry_writes_line(tmp_path: Path) -> None:
    log = TradeEventLog(str(tmp_path / "events.jsonl"))
    log.append_entry(
        condition_id="c1", slug="s", question="q",
        sport_tag="tennis", source="model", direction="BUY_YES",
        entry_price=0.45, entry_timestamp="t1",
        size_usdc=50.0, shares=100.0, confidence="A",
        bookmaker_prob=0.5, anchor_probability=0.5,
        num_bookmakers=5.0, has_sharp=True, entry_reason="normal",
    )
    events = log.read_events()
    assert len(events) == 1
    assert events[0]["kind"] == "entry"
    assert events[0]["entry_price"] == 0.45


def test_append_partial_writes_line(tmp_path: Path) -> None:
    log = TradeEventLog(str(tmp_path / "events.jsonl"))
    log.append_partial(
        condition_id="c1", slug="s", question="q",
        sport_tag="tennis", source="model",
        tier=1, sell_pct=0.4,
        realized_pnl_usdc=-2.5, timestamp="t", price=0.45,
    )
    events = log.read_events()
    assert events[0]["kind"] == "partial"


def test_append_final_writes_line(tmp_path: Path) -> None:
    log = TradeEventLog(str(tmp_path / "events.jsonl"))
    log.append_final(
        condition_id="c1", slug="s", question="q",
        sport_tag="tennis", source="model",
        exit_price=1.0, exit_reason="near_resolve",
        exit_pnl_usdc=12.5, exit_timestamp="t",
    )
    events = log.read_events()
    assert events[0]["kind"] == "final"


def test_append_only_preserves_history(tmp_path: Path) -> None:
    """KRITIK: append asla mevcut veriyi silemez."""
    log = TradeEventLog(str(tmp_path / "events.jsonl"))
    for i in range(5):
        log.append_partial(
            condition_id=f"c{i}", slug="s", question="q",
            sport_tag="tennis", source="model",
            tier=1, sell_pct=0.3,
            realized_pnl_usdc=float(i), timestamp=f"t{i}", price=0.5,
        )
    # Yeni instance ile başka event ekle
    log2 = TradeEventLog(str(tmp_path / "events.jsonl"))
    log2.append_final(
        condition_id="new", slug="s", question="q",
        sport_tag="tennis", source="model",
        exit_price=1.0, exit_reason="r",
        exit_pnl_usdc=5.0, exit_timestamp="t",
    )
    assert len(log2.read_events()) == 6  # 5 eski + 1 yeni


def test_mirror_dual_write(tmp_path: Path) -> None:
    primary = tmp_path / "audit" / "events.jsonl"
    mirror = tmp_path / "session" / "events.jsonl"
    log = TradeEventLog(str(primary), mirror_path=str(mirror))
    log.append_entry(
        condition_id="c", slug="s", question="q",
        sport_tag="tennis", source="model", direction="BUY_YES",
        entry_price=0.5, entry_timestamp="t",
        size_usdc=50.0, shares=100.0, confidence="A",
        bookmaker_prob=0.5, anchor_probability=0.5,
        num_bookmakers=5.0, has_sharp=False, entry_reason="normal",
    )
    assert primary.exists()
    assert mirror.exists()
    assert primary.read_text(encoding="utf-8") == mirror.read_text(encoding="utf-8")


def test_corrupt_line_skipped_on_read(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    p.write_text(
        json.dumps({"kind": "entry", "condition_id": "ok"}) + "\n"
        + "BOZUK\n"
        + json.dumps({"kind": "partial", "condition_id": "ok2"}) + "\n",
        encoding="utf-8",
    )
    log = TradeEventLog(str(p))
    assert len(log.read_events()) == 2


def test_no_rewrite_method_exists() -> None:
    """KRITIK: TradeEventLog'da rewrite/update API yok — sadece append."""
    log = TradeEventLog("dummy")
    assert not hasattr(log, "update_on_exit")
    assert not hasattr(log, "_rewrite_matching")
    assert not hasattr(log, "log_partial_exit")
    # Sadece append + read API:
    assert hasattr(log, "append_entry")
    assert hasattr(log, "append_partial")
    assert hasattr(log, "append_final")
    assert hasattr(log, "read_events")
