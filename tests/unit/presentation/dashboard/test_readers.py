"""presentation/dashboard/readers.py için birim testler.

ARCH_GUARD Kural 1 kontrolü: bu modül infra import etmemeli.

Dizin yapısı (yeni):
  logs_dir/audit/trade_history.jsonl, equity_history.jsonl
  logs_dir/runtime/skipped_trades.jsonl
  logs_dir/../data/positions.json, circuit_breaker_state.json, stock_queue.json
"""
from __future__ import annotations

import json
from pathlib import Path

from src.presentation.dashboard import readers


# ── Dizin setup helper ───────────────────────────────────────────────────────

def _mk_logs(tmp_path: Path) -> tuple[Path, Path]:
    """logs_dir ve data_dir oluştur, döner."""
    logs_dir = tmp_path / "logs"
    data_dir = tmp_path / "data"
    (logs_dir / "audit").mkdir(parents=True)
    (logs_dir / "runtime").mkdir(parents=True)
    (logs_dir / "session").mkdir(parents=True)
    data_dir.mkdir()
    return logs_dir, data_dir


# ── Katman ihlali kontrolü ──

def test_readers_module_has_no_infra_imports() -> None:
    """readers.py infrastructure/strategy/orchestration import etmemeli.

    SPEC-Z17 (2026-06-04): presentation -> domain LEGAL (event_replay).
    Domain saf hesaplama; I/O ya da üst-katman bağımlılığı taşımaz.
    """
    path = Path(readers.__file__)
    source = path.read_text(encoding="utf-8")
    for forbidden in (
        "from src.infrastructure",
        "import src.infrastructure",
        "from src.strategy",
        "import src.strategy",
        "from src.orchestration",
        "import src.orchestration",
    ):
        assert forbidden not in source, f"Layer violation: {forbidden}"


# ── read_positions ──

def test_read_positions_missing_returns_default(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    out = readers.read_positions(logs_dir)
    assert out == {"positions": {}, "realized_pnl": 0.0, "high_water_mark": 0.0}


def test_read_positions_valid_file(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    data = {"positions": {"k1": {"slug": "a"}}, "realized_pnl": 42.0, "high_water_mark": 1200.0}
    (data_dir / "positions.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_positions(logs_dir)
    assert out["realized_pnl"] == 42.0
    assert "k1" in out["positions"]


def test_read_positions_corrupt_returns_default(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "positions.json").write_text("not json", encoding="utf-8")
    out = readers.read_positions(logs_dir)
    assert out["positions"] == {}


# ── read_session_start (topbar "session basladi" gosterimi) ──

def test_read_session_start_missing_returns_empty(tmp_path: Path) -> None:
    """Reboot sonrasi bootstrap henuz session_start.json yazmamissa boş string."""
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_session_start(logs_dir) == ""


def test_read_session_start_valid_returns_iso(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    iso = "2026-05-29T00:05:56+00:00"
    (data_dir / "session_start.json").write_text(
        json.dumps({"iso": iso}), encoding="utf-8",
    )
    assert readers.read_session_start(logs_dir) == iso


def test_read_session_start_corrupt_returns_empty(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "session_start.json").write_text("not json", encoding="utf-8")
    assert readers.read_session_start(logs_dir) == ""


# ── JSONL tail readers ──

def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for d in lines:
            f.write(json.dumps(d) + "\n")


# ── SPEC-Z17 event log fixture helpers ──

def _event(kind: str, condition_id: str, **fields) -> dict:
    """Z17 event log fixture: ortak alanlar + override."""
    base = {
        "kind": kind, "condition_id": condition_id, "slug": "s",
        "question": "q", "sport_tag": "tennis", "source": "model",
    }
    base.update(fields)
    return base


def _write_events(path: Path, events: list[dict]) -> None:
    """trade_events.jsonl yaz — append-only event log fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(e) for e in events) + "\n",
        encoding="utf-8",
    )


def test_read_trades_missing_returns_empty(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_trades(logs_dir) == []


def test_read_trades_tail(tmp_path: Path) -> None:
    """Z17: trade_events.jsonl son N event'i replay edilir.

    Tail penceresi event seviyesinde uygulanır. Her event tek bir
    "entry" olduğundan, son 10 cid trade record'a dönüşür.
    """
    logs_dir, _ = _mk_logs(tmp_path)
    events = [
        _event("entry", condition_id=f"cid-{i}", slug=f"m-{i}",
               entry_timestamp=f"2026-05-12T{i:02d}:00:00Z")
        for i in range(30)
    ]
    _write_events(logs_dir / "audit" / "trade_events.jsonl", events)
    out = readers.read_trades(logs_dir, n=10)
    assert len(out) == 10
    assert out[-1]["slug"] == "m-29"
    assert out[0]["slug"] == "m-20"


def test_read_trades_archive_files_are_ignored(tmp_path: Path) -> None:
    """Arşiv dosyaları (trade_history.archive.*.jsonl) dashboard tarafından OKUNMAZ.

    2026-05-23 kullanıcı kararı: reboot = gerçek 0 nokta. Eski SPEC-Q "archive'ları
    da oku" davranışı geri çevrildi. Archive dosyaları forensic için disk'te
    durur ama dashboard widget'larına sızmaz.
    """
    logs_dir, _ = _mk_logs(tmp_path)
    _write_jsonl(
        logs_dir / "audit" / "trade_history.archive.20260511_115858.jsonl",
        [{
            "slug": "archived-trade", "condition_id": "cid-old",
            "exit_price": 0.01, "exit_pnl_usdc": -40.93,
            "exit_timestamp": "2026-05-11T03:00:00Z",
            "entry_timestamp": "2026-05-10T20:00:00Z", "partial_exits": [],
        }],
    )

    out = readers.read_trades(logs_dir, n=100)
    assert out == []


def test_read_trades_archive_not_merged_with_current(tmp_path: Path) -> None:
    """Z17: sadece aktif trade_events.jsonl okunur; archive event log'ları atlanır."""
    logs_dir, _ = _mk_logs(tmp_path)
    # Eski archive event log'ları — dashboard görmezden gelmeli.
    _write_events(
        logs_dir / "audit" / "trade_events.archive.20260511_115858.jsonl",
        [_event("entry", condition_id="cid-1", slug="old-1",
                entry_timestamp="2026-05-10T20:00:00Z")],
    )
    _write_events(
        logs_dir / "audit" / "trade_events.archive.20260521_093516.jsonl",
        [_event("entry", condition_id="cid-2", slug="old-2",
                entry_timestamp="2026-05-20T22:40:00Z")],
    )
    # Aktif event log: tek entry.
    _write_events(
        logs_dir / "audit" / "trade_events.jsonl",
        [_event("entry", condition_id="cid-3", slug="current-1",
                entry_timestamp="2026-05-21T00:01:07Z")],
    )

    out = readers.read_trades(logs_dir, n=100)
    cids = {r["condition_id"] for r in out}
    # Sadece aktif current trade görünür; archive event log'ları değil.
    assert cids == {"cid-3"}


def test_read_trades_duplicate_events_dedupe_by_signature(
    tmp_path: Path,
) -> None:
    """SPEC-Z18: tek dosyada tekrarlı event → signature ile dedupe.

    Tek dosya (audit) — session aynası kaldırıldı. Aynı entry/partial event
    dosyada iki kez bulunsa bile (örn. çift append), readers signature dedupe
    sonrası replay tek trade record üretmeli, partial da tekilleşmeli.
    """
    logs_dir, _ = _mk_logs(tmp_path)
    cid = "0xabc123"
    ts = "2026-05-12T20:00:00Z"
    entry = _event(
        "entry", condition_id=cid, slug="match-a",
        entry_timestamp=ts, entry_price=0.40,
    )
    partial = _event(
        "partial", condition_id=cid, slug="match-a",
        tier=1, sell_pct=0.4, realized_pnl_usdc=5.0,
        timestamp="2026-05-12T20:30:00Z", price=0.70,
    )
    # Aynı event sequence tek dosyada iki kez (duplicate append senaryosu).
    _write_events(logs_dir / "audit" / "trade_events.jsonl",
                  [entry, partial, entry, partial])

    out = readers.read_trades(logs_dir, n=100)
    assert len(out) == 1
    # Partial event signature ile dedupe → tek partial bırakır.
    assert len(out[0]["partial_exits"]) == 1


def test_read_trades_same_condition_different_entry_kept_separately(
    tmp_path: Path,
) -> None:
    """Z17 replay invariant: aynı cid'e ikinci entry event ATLANIR.

    Event log append-only; aynı cid için ikinci entry defansif olarak yok
    sayılır (event_replay._apply). İlk entry + onun final event'i kalır;
    ikinci entry + final ile temsil edilen "ikinci giriş" Z17 modelinde
    yeni bir cid (yeniden açılış) ile temsil edilmek zorunda.
    Bu test invariant'ı pinler: tek record döner.
    """
    logs_dir, _ = _mk_logs(tmp_path)
    cid = "0xabc123"
    _write_events(logs_dir / "audit" / "trade_events.jsonl", [
        # 1. entry: SL ile kapandı
        _event("entry", condition_id=cid, slug="match-a",
               entry_timestamp="2026-05-12T20:00:00Z", entry_price=0.40),
        _event("final", condition_id=cid, slug="match-a",
               exit_price=0.21, exit_pnl_usdc=-16.62,
               exit_reason="stop_loss",
               exit_timestamp="2026-05-12T20:30:00Z"),
        # 2. entry: aynı cid → replay tarafından ATLANIR
        _event("entry", condition_id=cid, slug="match-a",
               entry_timestamp="2026-05-12T21:00:00Z", entry_price=0.23),
        # İkinci final: ilk final zaten yazıldı → ATLANIR
        _event("final", condition_id=cid, slug="match-a",
               exit_price=0.01, exit_pnl_usdc=-11.68,
               exit_reason="graduated_sl",
               exit_timestamp="2026-05-12T22:30:00Z"),
    ])

    out = readers.read_trades(logs_dir, n=100)
    assert len(out) == 1
    # İlk final kazanır (replay invariant).
    assert out[0]["exit_pnl_usdc"] == -16.62
    assert out[0]["exit_reason"] == "stop_loss"


def test_read_trades_includes_partial_exits_from_session(tmp_path: Path) -> None:
    """Z17: entry + partial event sequence → record partial_exits dolu döner."""
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "positions.json").write_text(
        json.dumps({"positions": {}, "realized_pnl": 7.66, "high_water_mark": 1000.0}),
        encoding="utf-8",
    )
    _write_events(logs_dir / "audit" / "trade_events.jsonl", [
        _event("entry", condition_id="cid-sabres", slug="sabres",
               entry_timestamp="2026-05-12T23:00:00Z", entry_price=0.40),
        _event("partial", condition_id="cid-sabres", slug="sabres",
               tier=1, sell_pct=0.4, realized_pnl_usdc=7.66,
               timestamp="2026-05-12T23:30:00Z", price=0.60),
    ])

    out = readers.read_trades(logs_dir, n=100)
    assert len(out) == 1
    assert out[0]["slug"] == "sabres"
    assert len(out[0]["partial_exits"]) == 1
    assert out[0]["partial_exits"][0]["realized_pnl_usdc"] == 7.66


def test_read_equity_history_tail(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    rows = [{"bankroll": 1000 + i} for i in range(5)]
    _write_jsonl(logs_dir / "audit" / "equity_history.jsonl", rows)
    out = readers.read_equity_history(logs_dir, n=100)
    assert len(out) == 5
    assert out[-1]["bankroll"] == 1004


def test_read_skipped_tail(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    rows = [{"slug": f"s-{i}", "skip_reason": "no_edge"} for i in range(3)]
    _write_jsonl(logs_dir / "runtime" / "skipped_trades.jsonl", rows)
    out = readers.read_skipped(logs_dir)
    assert len(out) == 3
    assert out[0]["skip_reason"] == "no_edge"


# ── read_eligible_queue ──

def test_read_eligible_queue_missing_empty(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_eligible_queue(logs_dir) == []


def test_read_eligible_queue_list(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    data = [{"slug": "a"}, {"slug": "b"}]
    (data_dir / "stock_queue.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_eligible_queue(logs_dir)
    assert len(out) == 2


def test_read_eligible_queue_non_list_returns_empty(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "stock_queue.json").write_text('{"not": "list"}', encoding="utf-8")
    assert readers.read_eligible_queue(logs_dir) == []


# ── read_breaker ──

def test_read_breaker_missing_returns_empty_dict(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_breaker(logs_dir) == {}


def test_read_breaker_valid(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    data = {"daily_realized_pnl_pct": -0.05, "consecutive_losses": 2}
    (data_dir / "circuit_breaker_state.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_breaker(logs_dir)
    assert out["consecutive_losses"] == 2


# ── bot_is_alive ──

def test_bot_is_alive_no_pid_file(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.bot_is_alive(logs_dir) is False


def test_bot_is_alive_invalid_pid_content(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    (logs_dir / "agent.pid").write_text("not a number", encoding="utf-8")
    assert readers.bot_is_alive(logs_dir) is False


def test_bot_is_alive_nonexistent_pid(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    (logs_dir / "agent.pid").write_text("999999", encoding="utf-8")
    assert readers.bot_is_alive(logs_dir) is False


# ── read_model_health (Plan 1.D Task 4) ──

def test_read_model_health_missing_file_returns_empty(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_model_health(logs_dir) == {}


def test_read_model_health_valid_json(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    payload = {
        "computed_at_utc": "2026-06-01T00:00:00+00:00",
        "sports": {"tennis": {"accuracy": 0.72, "n_trades": 47}},
    }
    (data_dir / "model_health.json").write_text(json.dumps(payload), encoding="utf-8")
    assert readers.read_model_health(logs_dir) == payload


def test_read_model_health_corrupt_json_returns_empty(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "model_health.json").write_text("{not valid", encoding="utf-8")
    assert readers.read_model_health(logs_dir) == {}
