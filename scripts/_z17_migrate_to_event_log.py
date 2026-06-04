"""SPEC-Z17 one-shot: mevcut trade_history.jsonl + Z16 trade_exits.jsonl
event'lerini trade_events.jsonl'e dönüştür.

Çalıştırma sırası:
  1. trade_history kayıtlarından entry event'leri çıkar (entry_price set'li olanlar)
  2. Aynı kayıtlardan partial event'leri çıkar (partial_exits listesi)
  3. Aynı kayıtlardan final event'leri çıkar (exit_price set'li olanlar)
  4. Z16 trade_exits.jsonl event'lerini ekle (signature dedupe)
  5. Timestamp sırasıyla yaz
"""
from __future__ import annotations

import json
from pathlib import Path


SRC_HISTORY = Path("logs/audit/trade_history.jsonl")
SRC_EXITS_Z16 = Path("logs/audit/trade_exits.jsonl")
TARGET_AUDIT = Path("logs/audit/trade_events.jsonl")
TARGET_SESSION = Path("logs/session/trade_events.jsonl")


def _read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def main() -> None:
    history = _read_jsonl(SRC_HISTORY)
    z16 = _read_jsonl(SRC_EXITS_Z16)

    events: list[dict] = []
    for r in history:
        cid = r.get("condition_id")
        if not cid:
            continue
        meta = {
            "condition_id": cid,
            "slug": r.get("slug") or "",
            "question": r.get("question") or "",
            "sport_tag": r.get("sport_tag") or "",
            "source": r.get("source") or "",
        }
        if r.get("entry_price") is not None:
            events.append({**meta, "kind": "entry",
                           "direction": r.get("direction") or "",
                           "entry_price": r.get("entry_price"),
                           "entry_timestamp": r.get("entry_timestamp") or "",
                           "size_usdc": r.get("size_usdc") or 0.0,
                           "shares": r.get("shares") or 0.0,
                           "confidence": r.get("confidence") or "",
                           "bookmaker_prob": r.get("bookmaker_prob") or 0.0,
                           "anchor_probability": r.get("anchor_probability") or 0.0,
                           "num_bookmakers": r.get("num_bookmakers") or 0.0,
                           "has_sharp": r.get("has_sharp") or False,
                           "entry_reason": r.get("entry_reason") or ""})
        for p in (r.get("partial_exits") or []):
            events.append({**meta, "kind": "partial",
                           "tier": p.get("tier"),
                           "sell_pct": p.get("sell_pct"),
                           "realized_pnl_usdc": p.get("realized_pnl_usdc"),
                           "timestamp": p.get("timestamp"),
                           "price": p.get("price")})
        if r.get("exit_price") is not None:
            events.append({**meta, "kind": "final",
                           "exit_price": r.get("exit_price"),
                           "exit_reason": r.get("exit_reason") or "",
                           "exit_pnl_usdc": r.get("exit_pnl_usdc") or 0.0,
                           "exit_timestamp": r.get("exit_timestamp") or ""})

    # Z16 events — meta'yı buradan al
    for e in z16:
        events.append(e)

    # Dedupe by signature (kind + cid + ts + pnl)
    seen: set[tuple] = set()
    uniq: list[dict] = []
    for e in events:
        ts = (e.get("timestamp") or e.get("exit_timestamp")
              or e.get("entry_timestamp") or "")
        pnl_raw = (e.get("realized_pnl_usdc")
                   or e.get("exit_pnl_usdc") or 0)
        try:
            pnl = round(float(pnl_raw), 4)
        except (TypeError, ValueError):
            pnl = 0.0
        sig = (e.get("kind"), e.get("condition_id"), ts, pnl)
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(e)

    # Timestamp sırasıyla yaz
    def _ts(e: dict) -> str:
        return (e.get("entry_timestamp") or e.get("timestamp")
                or e.get("exit_timestamp") or "")
    uniq.sort(key=_ts)

    payload = "\n".join(json.dumps(e, ensure_ascii=False) for e in uniq) + "\n"
    for tgt in [TARGET_AUDIT, TARGET_SESSION]:
        tgt.parent.mkdir(parents=True, exist_ok=True)
        tgt.write_text(payload, encoding="utf-8")
    print(f"Z17 migration: {len(uniq)} event yazıldı ({len(events)} ham, "
          f"{len(events) - len(uniq)} duplicate atlandı)")


if __name__ == "__main__":
    main()
