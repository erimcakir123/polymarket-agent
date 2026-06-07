"""SPEC-Z26 tek-seferlik temizlik: kural-dışı 5 işlemi defterden çıkar +
equity eğrisini yeniden hesapla. Saf fonksiyonlar + I/O main().

KULLANIM:
  python scripts/cleanup_z24.py          # DRY-RUN, sadece rapor (dosya değişmez)
  python scripts/cleanup_z24.py --apply  # yedek al + uygula
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_AUDIT = Path("logs/audit")
_TRADES = _AUDIT / "trade_events.jsonl"
_EQUITY = _AUDIT / "equity_history.jsonl"

# Hedefler (spec onaylı — "tüm session, tutarlı"):
FULL_REMOVE_SLUGS = {
    "atp-poling-ilagan-2026-06-06",                        # 1. giriş 0.77 + tekrar giriş
    "wta-vekic-monnet-2026-06-06-set-handicap-home-1pt5",  # 0.79
    "wnba-wsh-atl-2026-06-06",                             # moneyline 0.81 (totals DEĞİL)
}
EPISODE_REMOVE = [
    ("wnba-ind-nyl-2026-06-06", "2026-06-07T00:59:07.768854+00:00"),  # 2. giriş (tekrar)
]


def remove_events(
    events: list[dict[str, Any]],
    full_slugs: set[str],
    episodes: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Hedef event'leri çıkar.

    full_slugs: tüm event'leri silinecek slug'lar (tam eşleşme).
    episodes: (slug, entry_timestamp) — o slug'da SADECE o episode silinir
    (entry'den kendi final'ine kadar; final dahil).
    """
    ep_targets = {(s, t) for s, t in episodes}
    ep_slugs = {s for s, _ in episodes}
    out: list[dict[str, Any]] = []
    dropping: dict[str, bool] = {}  # slug -> şu an silinen episode'un içinde miyiz
    for ev in events:
        slug = ev.get("slug") or ""
        if slug in full_slugs:
            continue
        if slug in ep_slugs:
            kind = ev.get("kind")
            if kind == "entry":
                dropping[slug] = (slug, ev.get("entry_timestamp")) in ep_targets
            if dropping.get(slug):
                if kind == "final":
                    dropping[slug] = False  # episode bitti; final de silinir, reset
                continue  # silinen episode'a ait event → at
        out.append(ev)
    return out


def removed_events(
    events: list[dict[str, Any]],
    full_slugs: set[str],
    episodes: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Silinen event'lerin listesi (equity rebuild için). Sıra korunur."""
    kept = remove_events(events, full_slugs, episodes)
    ki = 0
    dropped: list[dict[str, Any]] = []
    for ev in events:
        if ki < len(kept) and ev is kept[ki]:
            ki += 1
        else:
            dropped.append(ev)
    return dropped


def rebuild_equity(
    snapshots: list[dict[str, Any]],
    removed: list[dict[str, Any]],
    initial_bankroll: float,
) -> list[dict[str, Any]]:
    """Her snapshot'tan silinen işlemlerin realized + invested izini çıkar.

    unrealized (titreme) DOKUNULMAZ (kullanıcı onayı).
    realized_new = realized − removed_realized_by(T)
    bankroll_new = bankroll − removed_realized_by(T) + removed_invested_open_at(T)
    """
    def _ts(ev: dict[str, Any], key: str) -> str:
        return ev.get(key) or ""

    out: list[dict[str, Any]] = []
    for snap in snapshots:
        T = snap.get("timestamp") or ""
        removed_realized = 0.0
        removed_invested = 0.0
        removed_open = 0
        for ev in removed:
            kind = ev.get("kind")
            if kind == "partial" and _ts(ev, "timestamp") <= T:
                removed_realized += float(ev.get("realized_pnl_usdc") or 0.0)
            elif kind == "final":
                if _ts(ev, "exit_timestamp") <= T:
                    removed_realized += float(ev.get("exit_pnl_usdc") or 0.0)
                ent = _ts(ev, "entry_timestamp")
                fin = _ts(ev, "exit_timestamp")
                if ent and ent <= T < fin:
                    removed_invested += float(ev.get("size_usdc") or 0.0)
                    removed_open += 1
        new = dict(snap)
        new["realized_pnl"] = round(float(snap.get("realized_pnl", 0.0)) - removed_realized, 6)
        new["bankroll"] = round(
            float(snap.get("bankroll", 0.0)) - removed_realized + removed_invested, 6
        )
        new["invested"] = round(float(snap.get("invested", 0.0)) - removed_invested, 6)
        new["open_positions"] = max(0, int(snap.get("open_positions", 0)) - removed_open)
        out.append(new)
    return out


# ── I/O (main) ──

def _enrich_removed_finals(removed: list[dict], events: list[dict]) -> list[dict]:
    """removed final'lerine, aynı episode entry'sinden size_usdc + entry_timestamp ekle."""
    by_slug_entry: dict[str, dict] = {}
    out: list[dict] = []
    for ev in removed:
        slug = ev.get("slug") or ""
        if ev.get("kind") == "entry":
            by_slug_entry[slug] = ev
        if ev.get("kind") == "final":
            ent = by_slug_entry.get(slug, {})
            ev = {**ev, "size_usdc": ent.get("size_usdc"),
                  "entry_timestamp": ent.get("entry_timestamp")}
        out.append(ev)
    return out


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _realized_total(events: list[dict]) -> float:
    return (
        sum(float(e.get("exit_pnl_usdc") or 0.0) for e in events if e.get("kind") == "final")
        + sum(float(e.get("realized_pnl_usdc") or 0.0) for e in events if e.get("kind") == "partial")
    )


def main(apply: bool) -> None:
    events = _read_jsonl(_TRADES)
    snaps = _read_jsonl(_EQUITY)
    kept = remove_events(events, FULL_REMOVE_SLUGS, EPISODE_REMOVE)
    removed = _enrich_removed_finals(
        removed_events(events, FULL_REMOVE_SLUGS, EPISODE_REMOVE), events
    )
    new_snaps = rebuild_equity(snaps, removed, initial_bankroll=1000.0)

    print(f"events: {len(events)} -> {len(kept)} (silinen {len(events) - len(kept)})")
    print("silinen event tipleri:", end=" ")
    kinds: dict[str, int] = {}
    for e in removed:
        kinds[e.get("kind", "?")] = kinds.get(e.get("kind", "?"), 0) + 1
    print(kinds)
    print("silinen slug'lar:", sorted({e.get("slug", "?") for e in removed}))
    print(f"realized PnL: {_realized_total(events):.2f} -> {_realized_total(kept):.2f}")
    print(f"equity snapshots: {len(snaps)} (rebuild)")

    if not apply:
        print("\nDRY-RUN — hicbir dosya degismedi. Uygulamak icin: --apply")
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    _TRADES.rename(_TRADES.with_suffix(f".jsonl.bak.{ts}"))
    _EQUITY.rename(_EQUITY.with_suffix(f".jsonl.bak.{ts}"))
    _write_jsonl(_TRADES, kept)
    _write_jsonl(_EQUITY, new_snaps)
    print(f"\nYEDEK alindi (.bak.{ts}) + yeni dosyalar yazildi.")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
