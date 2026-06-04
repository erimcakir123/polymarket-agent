"""SPEC-Z17 (2026-06-04): event replay — events -> trade records.

Pure function, deterministic, no I/O. Domain layer.

Event akisi (timestamp sirasi):
  entry -> partial+ -> final
  Ayni cid'e ikinci final gelirse IGNORE EDILIR (duplicate korumasi).
  Entry yokken partial/final geldiyse synth kayit yaratilir (orphan).
"""
from __future__ import annotations

from typing import Any


_SYNTH_REASON = "synth-from-event:Z17"


def replay_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Event listesini sirali uygula, trade record listesi dondur.

    Args:
      events: append-only event log'dan okunmus ham event dict'leri.

    Returns:
      Trade record dict'leri (TradeRecord schema uyumlu).
    """
    by_cid: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for ev in events:
        cid = ev.get("condition_id")
        if not cid:
            continue
        rec = by_cid.get(cid)
        kind = ev.get("kind")
        if kind == "entry":
            if rec is None:
                rec = _entry_record(cid, ev)
                by_cid[cid] = rec
                order.append(cid)
            # Ayni cid'e ikinci entry geldiyse atla (defansif)
            continue
        if rec is None:
            rec = _synth_record(cid, ev)
            by_cid[cid] = rec
            order.append(cid)
        if kind == "partial":
            _apply_partial(rec, ev)
        elif kind == "final":
            _apply_final(rec, ev)

    return [by_cid[c] for c in order]


def _entry_record(cid: str, ev: dict[str, Any]) -> dict[str, Any]:
    return {
        "condition_id": cid,
        "slug": ev.get("slug") or "",
        "question": ev.get("question") or "",
        "sport_tag": ev.get("sport_tag") or "",
        "source": ev.get("source") or "",
        "direction": ev.get("direction") or "",
        "entry_price": ev.get("entry_price"),
        "entry_timestamp": ev.get("entry_timestamp") or "",
        "entry_reason": ev.get("entry_reason") or "",
        "size_usdc": ev.get("size_usdc") or 0.0,
        "shares": ev.get("shares") or 0.0,
        "confidence": ev.get("confidence") or "",
        "bookmaker_prob": ev.get("bookmaker_prob") or 0.0,
        "anchor_probability": ev.get("anchor_probability") or 0.0,
        "num_bookmakers": ev.get("num_bookmakers") or 0.0,
        "has_sharp": ev.get("has_sharp") or False,
        "exit_price": None,
        "exit_pnl_usdc": 0.0,
        "exit_reason": "",
        "exit_timestamp": "",
        "partial_exits": [],
    }


def _synth_record(cid: str, ev: dict[str, Any]) -> dict[str, Any]:
    return {
        "condition_id": cid,
        "slug": ev.get("slug") or "",
        "question": ev.get("question") or "",
        "sport_tag": ev.get("sport_tag") or "",
        "source": ev.get("source") or "",
        "direction": "",
        "entry_price": None,
        "entry_timestamp": "",
        "entry_reason": _SYNTH_REASON,
        "size_usdc": 0.0, "shares": 0.0, "confidence": "",
        "bookmaker_prob": 0.0, "anchor_probability": 0.0,
        "num_bookmakers": 0.0, "has_sharp": False,
        "exit_price": None, "exit_pnl_usdc": 0.0,
        "exit_reason": "", "exit_timestamp": "",
        "partial_exits": [],
    }


def _apply_partial(rec: dict[str, Any], ev: dict[str, Any]) -> None:
    raw = rec.get("partial_exits")
    partials: list[dict[str, Any]] = raw if isinstance(raw, list) else []
    partials.append({
        "tier": ev.get("tier"),
        "sell_pct": ev.get("sell_pct"),
        "realized_pnl_usdc": ev.get("realized_pnl_usdc"),
        "timestamp": ev.get("timestamp"),
        "price": ev.get("price"),
    })
    rec["partial_exits"] = partials


def _apply_final(rec: dict[str, Any], ev: dict[str, Any]) -> None:
    # Ilk final wins — sonraki final'lar ATLANIR (duplicate korumasi).
    if rec.get("exit_price") is not None:
        return
    rec["exit_price"] = ev.get("exit_price")
    rec["exit_pnl_usdc"] = ev.get("exit_pnl_usdc")
    rec["exit_reason"] = ev.get("exit_reason") or ""
    rec["exit_timestamp"] = ev.get("exit_timestamp") or ""
