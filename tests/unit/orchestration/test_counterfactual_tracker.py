"""CounterfactualTracker unit testleri."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock


def _make_tracker(tmp_path: Path):
    from src.orchestration.counterfactual_tracker import CounterfactualTracker
    return CounterfactualTracker(audit_dir=tmp_path / "audit")


def _fake_gamma(token_prices: dict[str, float]) -> MagicMock:
    """token_id → price dönen sahte GammaClient."""
    client = MagicMock()
    client.get_markets_by_token_ids.side_effect = lambda ids: [
        {"tokenId": tid, "lastTradePrice": price}
        for tid, price in token_prices.items()
        if tid in ids
    ]
    return client


def test_add_starts_tracking(tmp_path: Path) -> None:
    """add() çağrısından sonra pending'de entry olmalı."""
    tracker = _make_tracker(tmp_path)
    tracker.add("trade-1", "token-1", "2026-04-26T20:00:00+00:00", 0.40, "predictive_dead")
    assert "trade-1" in tracker._pending


def test_tick_records_price_point(tmp_path: Path) -> None:
    """tick() price point'i trace'e ekler."""
    tracker = _make_tracker(tmp_path)
    tracker.add("trade-1", "token-1", "2026-04-26T20:00:00+00:00", 0.40, "predictive_dead")
    gamma = _fake_gamma({"token-1": 0.35})

    tracker.tick(gamma)

    assert len(tracker._pending["trade-1"].trace) == 1
    assert tracker._pending["trade-1"].trace[0]["price"] == 0.35


def test_tick_settles_at_high_price(tmp_path: Path) -> None:
    """≥0.98 fiyatta tracking_complete=True, final_settlement set edilir."""
    tracker = _make_tracker(tmp_path)
    tracker.add("trade-1", "token-1", "2026-04-26T20:00:00+00:00", 0.40, "predictive_dead")
    gamma = _fake_gamma({"token-1": 0.99})

    tracker.tick(gamma)

    assert "trade-1" not in tracker._pending
    jsonl = tmp_path / "audit" / "counterfactual.jsonl"
    assert jsonl.exists()
    import json
    record = json.loads(jsonl.read_text(encoding="utf-8").strip())
    assert record["final_settlement"] == 0.99
    assert record["tracking_complete"] is True


def test_tick_resolves_no_at_zero(tmp_path: Path) -> None:
    """≤0.02 fiyatta final_settlement=0.0 set edilir."""
    tracker = _make_tracker(tmp_path)
    tracker.add("trade-1", "token-1", "2026-04-26T20:00:00+00:00", 0.40, "predictive_dead")
    gamma = _fake_gamma({"token-1": 0.01})

    tracker.tick(gamma)

    assert "trade-1" not in tracker._pending
    import json
    record = json.loads((tmp_path / "audit" / "counterfactual.jsonl").read_text(encoding="utf-8").strip())
    assert record["final_settlement"] == 0.0


def test_flush_writes_incomplete_trace(tmp_path: Path) -> None:
    """flush() incomplete trace'i diske yazar."""
    tracker = _make_tracker(tmp_path)
    tracker.add("trade-1", "token-1", "2026-04-26T20:00:00+00:00", 0.40, "predictive_dead")

    tracker.flush()

    jsonl = tmp_path / "audit" / "counterfactual.jsonl"
    assert jsonl.exists()
    import json
    record = json.loads(jsonl.read_text(encoding="utf-8").strip())
    assert record["trade_id"] == "trade-1"
    assert record["tracking_complete"] is False


def test_restore_continues_incomplete_trace(tmp_path: Path) -> None:
    """Yeni tracker instance: flush() ile yazılan incomplete trace restore edilir."""
    from src.orchestration.counterfactual_tracker import CounterfactualTracker

    tracker = _make_tracker(tmp_path)
    tracker.add("trade-1", "token-1", "2026-04-26T20:00:00+00:00", 0.40, "predictive_dead")
    tracker.flush()

    tracker2 = CounterfactualTracker(audit_dir=tmp_path / "audit")
    assert "trade-1" in tracker2._pending
