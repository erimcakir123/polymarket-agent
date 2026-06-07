"""Dashboard state readers — stdlib-only JSON/JSONL okuyucuları.

ARCH_GUARD Kural 1 (katman atlama yasağı): dashboard ayrı process'tir, infra
import etmez. State'e `logs/*.json|jsonl` dosyaları üzerinden erişir.

Sadece `json` ve `pathlib` kullanılır. Pydantic, infra ya da domain import YOK.

Her fonksiyon tek dosya okur, dict/list döner. Dosya yoksa veya bozuksa default.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# JSONL satır boyutu tahminleri (bytes) — tail okumada yeterli pencere için.
_BYTES_TRADES = 1000    # match_timeline dahil → geniş
_BYTES_EQUITY = 256     # küçük snapshot
_BYTES_SKIPPED = 512


# ── JSON helpers ──

def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Read JSON failed %s: %s", path, e)
        return default


def _read_jsonl_tail(path: Path, n: int, bytes_per_line: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk_size = min(size, n * bytes_per_line)
            f.seek(size - chunk_size)
            raw = f.read().decode("utf-8", errors="replace")
        lines = [l for l in raw.strip().split("\n") if l.strip()]
        if chunk_size < size and lines:
            lines = lines[1:]
        out: list[dict[str, Any]] = []
        for l in lines[-n:]:
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        return out
    except OSError as e:
        logger.warning("Read JSONL tail failed %s: %s", path, e)
        return []


# ── Public reader functions (her biri tek dosya) ──

def read_positions(logs_dir: Path) -> dict[str, Any]:
    """positions.json → {positions, realized_pnl, high_water_mark}."""
    return _read_json(logs_dir.parent / "data" / "positions.json", {"positions": {}, "realized_pnl": 0.0, "high_water_mark": 0.0})


def read_force_close_alerts(logs_dir: Path) -> set[str]:
    """data/force_close_alerts.json → kırmızı border isteyen condition_id seti.

    2026-06-01 kullanıcı kararı: force-close otomatik exit YAPMAZ — sadece
    alarm + dashboard'da kırmızı border. Bu dosya alert flag'lerini tutar.
    """
    raw = _read_json(logs_dir.parent / "data" / "force_close_alerts.json", {})
    return set(raw.keys()) if isinstance(raw, dict) else set()


def read_realistic_exit_estimates(logs_dir: Path) -> dict[str, Any]:
    """data/realistic_exit_estimates.json → condition_id → {realistic_pnl_usdc, note}.

    Takılı kalmış (zarar-kes likidite/donma yüzünden çalışamamış) pozisyonlar için
    'gerçekçi satış olsaydı' tek-seferlik tahmin notu. Dashboard kartta gösterir.
    Dosya yoksa {} → kart notu çizilmez.
    """
    raw = _read_json(logs_dir.parent / "data" / "realistic_exit_estimates.json", {})
    return raw if isinstance(raw, dict) else {}


def read_model_health(logs_dir: Path) -> dict[str, Any]:
    """data/model_health.json → {computed_at_utc, sports} ya da {} (yok/bozuk).

    Plan 1.D Task 4. `scripts/calibration_health_report.py` üretir; dashboard
    cycle başına okur, branş kartı isabet alt-satırını oluşturur.
    """
    return _read_json(logs_dir.parent / "data" / "model_health.json", {})


def read_session_start(logs_dir: Path) -> str:
    """data/session_start.json -> ISO timestamp string ("" if missing/corrupt).

    Bootstrap reboot sonrasi bu dosyayi olusturur (current UTC). Reload korur,
    reboot siler. Dashboard topbar'inda "28 May · 14:30" formatinda gosterilir.
    """
    data = _read_json(logs_dir.parent / "data" / "session_start.json", {})
    iso = data.get("iso") if isinstance(data, dict) else None
    return str(iso) if iso else ""


def read_trades(logs_dir: Path, n: int = 100) -> list[dict[str, Any]]:
    """SPEC-Z17 (2026-06-04): trade kayıtları event log replay sonucu.

    Dosya: audit/trade_events.jsonl (tek truth — SPEC-Z18, session aynası yok).
    Event'ler signature ile dedupe edilir (kind + condition_id + timestamp +
    pnl), sonra domain.trade.event_replay.replay_events ile trade record
    listesine dönüştürülür.

    Trade_history.jsonl artık OKUNMAZ (Z15/Z16 legacy).
    """
    from src.domain.trade.event_replay import replay_events

    paths = [
        logs_dir / "audit" / "trade_events.jsonl",
    ]
    seen: set[tuple] = set()
    events: list[dict[str, Any]] = []
    for p in paths:
        if not p.exists():
            continue
        for ev in _read_jsonl_tail(p, n, _BYTES_TRADES):
            kind = ev.get("kind")
            cid = ev.get("condition_id")
            ts = (ev.get("timestamp") or ev.get("exit_timestamp")
                  or ev.get("entry_timestamp") or "")
            pnl_raw = (ev.get("realized_pnl_usdc")
                       or ev.get("exit_pnl_usdc") or 0)
            try:
                pnl = round(float(pnl_raw), 4)
            except (TypeError, ValueError):
                pnl = 0.0
            sig = (kind, cid, ts, pnl)
            if sig in seen:
                continue
            seen.add(sig)
            events.append(ev)
    return replay_events(events)


def read_trades_by_week(
    logs_dir: Path, week_offset: int = 0,
) -> tuple[list[dict[str, Any]], str, bool]:
    """ISO-week-aligned trade pagination.

    week_offset=0 → current week (Mon 00:00 UTC – Sun 23:59 UTC).
    week_offset=1 → previous week, etc.

    Returns (trades_in_week, week_label, has_older_data).
    """
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    current_monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    week_start = current_monday - timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=7)

    buffer_weeks = week_offset + 2
    n = 150 * buffer_weeks
    # SPEC-Z17: kaynak event log; read_trades replay sonucunu döndürür.
    all_trades = read_trades(logs_dir, n=n)

    week_trades: list[dict[str, Any]] = []
    has_older = False
    start_ts = week_start.isoformat()
    end_ts = week_end.isoformat()

    for t in all_trades:
        # Trade'in hafta içinde olup olmadığını belirlemek için hem tam-close
        # exit_timestamp'i hem partial_exits[*].timestamp'lerini kontrol et.
        # Sadece tam-close bakılırsa, partial-only açık pozisyonlar haftadan
        # dışarı düşüyor → Trade History modal boş gözüküyor.
        timestamps = []
        top_ts = t.get("exit_timestamp") or ""
        if top_ts:
            timestamps.append(top_ts)
        for pe in (t.get("partial_exits") or []):
            pe_ts = pe.get("timestamp") or ""
            if pe_ts:
                timestamps.append(pe_ts)
        if not timestamps:
            continue
        latest = max(timestamps)
        if latest < start_ts:
            has_older = True
        elif latest < end_ts:
            week_trades.append(t)

    _MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    sun = week_start + timedelta(days=6)
    if week_start.month == sun.month:
        label = (f"{week_start.day} - {sun.day} "
                 f"{_MONTHS[week_start.month - 1]} {week_start.year}")
    else:
        label = (f"{week_start.day} {_MONTHS[week_start.month - 1]} - "
                 f"{sun.day} {_MONTHS[sun.month - 1]} {week_start.year}")

    return week_trades, label, has_older


def read_equity_history(logs_dir: Path, n: int = 100) -> list[dict[str, Any]]:
    """equity_history.jsonl son N snapshot — audit/ (tek truth, SPEC-Z18)."""
    return _read_jsonl_tail(logs_dir / "audit" / "equity_history.jsonl", n, _BYTES_EQUITY)


def read_skipped(logs_dir: Path, n: int = 100) -> list[dict[str, Any]]:
    """skipped_trades.jsonl son N skip."""
    return _read_jsonl_tail(logs_dir / "runtime" / "skipped_trades.jsonl", n, _BYTES_SKIPPED)


def read_eligible_queue(logs_dir: Path) -> list[dict[str, Any]]:
    """stock_queue.json snapshot — dashboard Stock sekmesi.

    Ad backward-compat için korundu; kaynak StockQueue.save() çıktısı.
    Dashboard'un beklediği flat schema'ya projekte edilir:
      {slug, sport_tag, question, yes_price, no_price, liquidity, volume_24h,
       match_start_iso, first_seen_iso, last_skip_reason}
    """
    raw = _read_json(logs_dir.parent / "data" / "stock_queue.json", [])
    if not isinstance(raw, list):
        return []
    flat: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        market = row.get("market") or {}
        if not isinstance(market, dict):
            market = {}
        # Backward-compat: eski flat format (sadece market fields)
        if "slug" in row and "market" not in row:
            flat.append(row)
            continue
        flat.append({
            "slug": market.get("slug", ""),
            "sport_tag": market.get("sport_tag", ""),
            "question": market.get("question", ""),
            "yes_price": market.get("yes_price", 0.0),
            "no_price": market.get("no_price", 0.0),
            "liquidity": market.get("liquidity", 0.0),
            "volume_24h": market.get("volume_24h", 0.0),
            "match_start_iso": market.get("match_start_iso", ""),
            "first_seen_iso": row.get("first_seen_iso", ""),
            "last_skip_reason": row.get("last_skip_reason", ""),
        })
    return flat


def read_breaker(logs_dir: Path) -> dict[str, Any]:
    """circuit_breaker_state.json."""
    return _read_json(logs_dir.parent / "data" / "circuit_breaker_state.json", {})


def read_bot_status(logs_dir: Path) -> dict[str, Any]:
    """bot_status.json — {mode, last_cycle, last_cycle_at, reason}."""
    return _read_json(logs_dir.parent / "data" / "bot_status.json", {})


def read_balance_from_session(logs_dir: Path) -> dict[str, Any]:
    """audit/equity_history.jsonl son entry'sinden balance widget metrikleri.

    Dashboard balance, realized P&L, open P&L ve peak balance hesabı için
    kaynak. positions.json'a bakılmaz (lifetime kirlilik koruması —
    test_summary_reboot_scenario).

    SPEC-Z18 (2026-06-05): tek dosya (audit). Z11 session+audit çift-yedek
    fallback'i kaldırıldı — ayrışacak ikinci kopya yok. Reboot dosyayı arşive
    taşır → widget gerçek 0 noktasından başlar. Fonksiyon ismi geriye-uyum
    için korundu (çağıranlar + testler).

    Returns dict with keys:
      bankroll, realized_pnl, unrealized_pnl, invested,
      open_positions, peak_bankroll (session max), has_data.
    """
    _EMPTY: dict[str, Any] = {
        "bankroll": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "invested": 0.0,
        "open_positions": 0,
        "peak_bankroll": 0.0,
        "has_data": False,
    }
    # SPEC-Z18: tek dosya (audit). Çift-yedek fallback kaldırıldı.
    candidate_paths = [
        logs_dir / "audit" / "equity_history.jsonl",
    ]
    path = None
    last_entries: list[dict[str, Any]] = []
    for p in candidate_paths:
        if not p.exists():
            continue
        last_entries = _read_jsonl_tail(p, n=1, bytes_per_line=_BYTES_EQUITY)
        if last_entries:
            path = p
            break
    if path is None or not last_entries:
        return _EMPTY

    last = last_entries[-1]

    # Peak hesabı için daha geniş pencere oku (aynı dosyadan).
    all_entries = _read_jsonl_tail(path, n=500, bytes_per_line=_BYTES_EQUITY)
    peak = max(
        (float(e.get("bankroll", 0.0)) for e in all_entries),
        default=float(last.get("bankroll", 0.0)),
    )

    return {
        "bankroll": float(last.get("bankroll", 0.0)),
        "realized_pnl": float(last.get("realized_pnl", 0.0)),
        "unrealized_pnl": float(last.get("unrealized_pnl", 0.0)),
        "invested": float(last.get("invested", 0.0)),
        "open_positions": int(last.get("open_positions", 0)),
        "peak_bankroll": peak,
        "has_data": True,
    }


def bot_is_alive(logs_dir: Path) -> bool:
    """agent.pid dosyasında bulunan PID hala çalışıyor mu?

    Windows: ctypes.kernel32.OpenProcess ile subprocess açmadan kontrol eder.
    POSIX: os.kill(pid, 0) güvenli existence check.
    """
    pid_file = logs_dir / "agent.pid"
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    if sys.platform == "win32":
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False
