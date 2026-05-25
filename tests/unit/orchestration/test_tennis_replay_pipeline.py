"""tennis_replay.apply_pipeline — açık + kapalı kayıt simülasyon orchestration testleri."""
from __future__ import annotations

from datetime import datetime, timezone

from src.orchestration.tennis_replay.apply_pipeline import (
    process_closed_records,
    process_open_positions,
    rules_for,
)


class _FakeResp:
    def __init__(self, data: dict) -> None:
        self.status_code = 200
        self._data = data

    def json(self) -> dict:
        return self._data


def _http(history: list[dict]):
    def _call(url: str, params: dict, timeout: int):  # noqa: ARG001
        return _FakeResp({"history": history})
    return _call


def _ts(year: int, month: int, day: int, hh: int, mm: int = 0) -> int:
    return int(datetime(year, month, day, hh, mm, tzinfo=timezone.utc).timestamp())


def test_rules_for_tennis_uses_sport_rules_thresholds():
    rules = rules_for("tennis")
    assert rules.stop_loss_pct == 0.30
    assert rules.near_resolve_threshold == 0.94
    assert rules.near_resolve_guard_minutes == 5
    assert rules.match_duration_hours == 1.75
    # Distance-based scale-out (production ScaleOutConfig defaults)
    assert rules.tier1_threshold == 0.40
    assert rules.tier2_threshold == 0.70


def test_process_open_positions_with_stop_loss_trigger():
    # Açık pozisyon: entry=0.41, fiyat 0.28'e düşer → stop_loss.
    pos = {
        "condition_id": "cid1", "slug": "atp-test-totals",
        "token_id": "tok1", "direction": "BUY_YES",
        "entry_price": 0.41, "size_usdc": 40.0, "shares": 97.56,
        "entry_timestamp": "2026-05-20T14:00:00+00:00",
        "match_start_iso": "2026-05-20T14:00:00+00:00",
        "sport_tag": "tennis", "scale_out_tier": 0, "partial_exits": [],
    }
    state = {"positions": {"cid1": pos}, "realized_pnl": 0.0, "high_water_mark": 0.0}
    history = [
        {"t": _ts(2026, 5, 20, 14, 30), "p": 0.41},
        {"t": _ts(2026, 5, 20, 15, 0), "p": 0.35},
        {"t": _ts(2026, 5, 20, 15, 30), "p": 0.28},  # -31.7% SL
    ]
    outcome = process_open_positions(state, http_get=_http(history))
    assert len(outcome.summary_rows) == 1
    assert "stop_loss" in outcome.summary_rows[0].simulated_label
    assert len(outcome.new_audit_lines) == 1
    line = outcome.new_audit_lines[0]
    assert line["simulated"] is True
    assert line["exit_reason"] == "stop_loss"
    assert outcome.closed_condition_ids == ["cid1"]
    assert outcome.total_simulated_pnl < 0


def test_process_open_positions_with_no_history_returns_no_change():
    pos = {
        "condition_id": "cid2", "slug": "atp-pre-match",
        "token_id": "tok2", "direction": "BUY_YES",
        "entry_price": 0.45, "size_usdc": 45.0, "shares": 100.0,
        "entry_timestamp": "2026-05-21T14:00:00+00:00",
        "match_start_iso": "2026-05-21T16:00:00+00:00",
        "sport_tag": "tennis", "scale_out_tier": 0, "partial_exits": [],
    }
    state = {"positions": {"cid2": pos}}
    outcome = process_open_positions(state, http_get=_http([]))
    assert len(outcome.summary_rows) == 1
    assert "(no change)" in outcome.summary_rows[0].simulated_label
    assert outcome.new_audit_lines == []
    assert outcome.closed_condition_ids == []
    assert outcome.total_simulated_pnl == 0.0


def test_process_closed_records_skips_recent_entries():
    # Entry < 2h önce → korunmalı (yeni kayda dokunma).
    now = datetime(2026, 5, 20, 20, 0, tzinfo=timezone.utc)
    rec = {
        "slug": "recent-test", "condition_id": "cid3",
        "token_id": "tok3", "direction": "BUY_YES",
        "sport_tag": "tennis",
        "entry_price": 0.40, "size_usdc": 40.0, "shares": 100.0,
        "entry_timestamp": "2026-05-20T19:30:00+00:00",  # 30 dakika önce
        "exit_reason": "resolved", "exit_pnl_usdc": 60.0,
        "exit_timestamp": "2026-05-20T19:50:00+00:00",
        "partial_exits": [],
    }
    outcome = process_closed_records([rec], now, http_get=_http([]))
    assert outcome.rewritten_records == []
    assert outcome.summary_rows == []


def test_process_closed_records_rewrites_carabelli_style_resolved():
    # Eski 'resolved' kayıt: tek atışta +$42, replay tier1+tier2 partial bulur.
    now = datetime(2026, 5, 20, 22, 0, tzinfo=timezone.utc)
    rec = {
        "slug": "atp-carabel-tiafoe-2026-05-20-set-totals-2pt5",
        "condition_id": "cidCar", "token_id": "tokCar",
        "direction": "BUY_YES", "sport_tag": "tennis",
        "entry_price": 0.40, "size_usdc": 40.0, "shares": 100.0,
        "entry_timestamp": "2026-05-20T16:00:00+00:00",
        "exit_reason": "resolved", "exit_pnl_usdc": 60.0,
        "exit_price": 1.0,
        "exit_timestamp": "2026-05-20T19:00:00+00:00",
        "partial_exits": [],
    }
    history = [
        {"t": _ts(2026, 5, 20, 16, 30), "p": 0.40},
        {"t": _ts(2026, 5, 20, 17, 0), "p": 0.64},   # tier1 (progress=0.40)
        {"t": _ts(2026, 5, 20, 17, 30), "p": 0.82},  # tier2 (progress=0.70)
        {"t": _ts(2026, 5, 20, 18, 30), "p": 0.98},  # resolved
    ]
    outcome = process_closed_records([rec], now, http_get=_http(history))
    assert len(outcome.rewritten_records) == 1
    rewritten = outcome.rewritten_records[0]
    assert rewritten["simulated_correction"] is True
    assert len(rewritten["partial_exits"]) == 2
    assert rewritten["partial_exits"][0]["tier"] == 1
    assert rewritten["partial_exits"][1]["tier"] == 2
    # Yeni exit_pnl_usdc orijinalden farklı olmalı (replay scale-out P&L'yi böler).
    assert rewritten["exit_pnl_usdc"] != 60.0


def test_process_closed_records_no_partial_keeps_original():
    # Resolved kayıt ama partial tetiklenmedi (fiyat doğrusal 0.40 → 0 dustu)
    # — replay bulunan partial yok → rewrite YOK (orijinal korunur).
    now = datetime(2026, 5, 20, 22, 0, tzinfo=timezone.utc)
    rec = {
        "slug": "atp-lost-fast", "condition_id": "cidL",
        "token_id": "tokL", "direction": "BUY_YES",
        "sport_tag": "tennis",
        "entry_price": 0.40, "size_usdc": 40.0, "shares": 100.0,
        "entry_timestamp": "2026-05-20T16:00:00+00:00",
        "exit_reason": "resolved", "exit_pnl_usdc": -40.0,
        "exit_timestamp": "2026-05-20T18:00:00+00:00",
        "partial_exits": [],
    }
    history = [
        {"t": _ts(2026, 5, 20, 16, 30), "p": 0.40},
        {"t": _ts(2026, 5, 20, 17, 0), "p": 0.20},  # SL trigger (>-30%)
    ]
    outcome = process_closed_records([rec], now, http_get=_http(history))
    # SL = full exit, partial bulunmadığı için rewrite yok.
    assert outcome.rewritten_records == []
