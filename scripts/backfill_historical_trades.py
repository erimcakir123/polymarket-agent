"""bot.log'taki gecmis EXIT + SCALE-OUT olaylarini audit + session trade_history'e backfill et.

Kullanim:
    python scripts/backfill_historical_trades.py [--dry-run]

- Audit'te zaten o slug icin kayit varsa skip (dupe engelleme)
- Synthetic record: entry data placeholder (entry_price=0.5, size_usdc=PnL'den turetilir)
- Scale-out'lar parent record'un partial_exits listesine eklenir
- Audit + session ikisine de yazilir (trade_logger mirror'liyor zaten ama bu script kendi yazisini yapar)
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
BOT_LOG = ROOT / "logs" / "runtime" / "bot.log"
AUDIT = ROOT / "logs" / "audit" / "trade_history.jsonl"
SESSION = ROOT / "logs" / "session" / "trade_history.jsonl"

# Sport_tag tahmini slug prefix'inden
def _sport_tag_from_slug(slug: str) -> str:
    prefix = slug.split("-", 1)[0].lower() if slug else ""
    return prefix


def parse_bot_log() -> tuple[list[dict], list[dict]]:
    """bot.log'tan EXIT + SCALE-OUT olaylarini topla."""
    exits = []
    scaleouts = []
    if not BOT_LOG.exists():
        print(f"WARN: bot.log not found at {BOT_LOG}")
        return exits, scaleouts
    with open(BOT_LOG, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.search(r"(\d+-\d+-\d+ \d+:\d+:\d+).*EXIT (.+?): reason=(\w+) realized=\$(-?[\d.]+)", line)
            if m:
                ts, slug, reason, pnl = m.group(1), m.group(2).strip(), m.group(3), float(m.group(4))
                exits.append({"ts": ts, "slug": slug, "reason": reason, "pnl": pnl})
                continue
            m = re.search(r"(\d+-\d+-\d+ \d+:\d+:\d+).*SCALE-OUT (.+?): tier=(\d+) sold=([\d.]+) shares realized=\$(-?[\d.]+)", line)
            if m:
                ts, slug, tier, shares, pnl = m.group(1), m.group(2).strip(), int(m.group(3)), float(m.group(4)), float(m.group(5))
                scaleouts.append({"ts": ts, "slug": slug, "tier": tier, "shares_sold": shares, "pnl": pnl})
    return exits, scaleouts


def existing_audit_slugs() -> set[str]:
    """Audit'teki mevcut slug'lar (dupe engelleme icin)."""
    slugs: set[str] = set()
    if not AUDIT.exists():
        return slugs
    with open(AUDIT, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("slug"):
                    slugs.add(rec["slug"])
            except json.JSONDecodeError:
                continue
    return slugs


def to_iso(ts: str) -> str:
    """'2026-05-09 02:11:14' → '2026-05-09T02:11:14+00:00'."""
    try:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except (ValueError, TypeError):
        return ts


def _derive_prices(pnl: float, size: float, reason: str) -> tuple[float, float]:
    """exit_reason + PnL'den plausible entry/exit fiyatlari turet.

    Bot.log gercek fiyat saklamadigi icin tahmini deger uretir.
    near_resolve → exit ~94c, market_flip → exit ~30c, stop_loss → -%30 from entry.
    Diger durumlar: entry=50c, exit = entry*(1+pnl_pct).
    """
    pnl_pct = pnl / size if size > 0 else 0.0
    if reason == "near_resolve" and pnl_pct > 0:
        exit_price = 0.94
        entry_price = exit_price / (1.0 + pnl_pct)
    elif reason == "market_flip":
        exit_price = 0.30
        denom = 1.0 + pnl_pct
        entry_price = exit_price / denom if denom > 0.05 else 0.85
    elif reason == "stop_loss":
        entry_price = 0.50
        exit_price = entry_price * (1.0 + pnl_pct)
    else:
        entry_price = 0.50
        exit_price = entry_price * (1.0 + pnl_pct)
    entry_price = max(0.05, min(0.95, entry_price))
    exit_price = max(0.02, min(0.99, exit_price))
    return round(entry_price, 4), round(exit_price, 4)


def build_synthetic_record(exit_event: dict, scaleouts_for_slug: list[dict]) -> dict:
    """Tek slug icin tam kapali (synthetic) trade record olustur."""
    slug = exit_event["slug"]
    sport_tag = _sport_tag_from_slug(slug)
    pnl = exit_event["pnl"]
    size_usdc = 50.0  # backfill default size
    entry_price, exit_price = _derive_prices(pnl, size_usdc, exit_event["reason"])
    shares = size_usdc / entry_price if entry_price > 0 else size_usdc * 2.0
    # partial_exits listesi
    partials = []
    for so in scaleouts_for_slug:
        partials.append({
            "tier": so["tier"],
            "sell_pct": 0.4 if so["tier"] == 1 else 0.5,
            "realized_pnl_usdc": so["pnl"],
            "timestamp": to_iso(so["ts"]),
            "price": exit_price,
        })
    return {
        "slug": slug,
        "condition_id": f"backfill-{slug}",
        "event_id": "",
        "token_id": "",
        # question bos — UI alt basligi (subRowText) historical icin gosterilmeyecek
        "question": "",
        "match_title": "",
        "sport_tag": sport_tag,
        "sport_category": sport_tag,
        "league": sport_tag,
        "direction": "BUY_YES",
        "entry_price": entry_price,
        "size_usdc": size_usdc,
        "shares": shares,
        "confidence": "A",
        "bookmaker_prob": 0.55,
        "anchor_probability": 0.55,
        "num_bookmakers": 5,
        "has_sharp": True,
        "entry_reason": "historical-backfill",
        "entry_timestamp": to_iso(exit_event["ts"]),
        "exit_price": exit_price,
        "exit_reason": exit_event["reason"],
        "exit_pnl_usdc": round(pnl, 2),
        "exit_pnl_pct": round(pnl / size_usdc, 4),
        "exit_timestamp": to_iso(exit_event["ts"]),
        "partial_exits": partials,
    }


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    exits, scaleouts = parse_bot_log()
    print(f"Parsed: {len(exits)} exits, {len(scaleouts)} scale-outs")

    audit_slugs = existing_audit_slugs()
    print(f"Existing audit slugs: {len(audit_slugs)}")

    # Group scale-outs by slug
    so_by_slug: dict[str, list[dict]] = {}
    for so in scaleouts:
        so_by_slug.setdefault(so["slug"], []).append(so)

    new_records = []
    skipped_dupes = []
    for ex in exits:
        if ex["slug"] in audit_slugs:
            skipped_dupes.append(ex["slug"])
            continue
        so_list = so_by_slug.get(ex["slug"], [])
        record = build_synthetic_record(ex, so_list)
        new_records.append(record)

    print(f"To backfill: {len(new_records)} records")
    print(f"Skipped (already in audit): {len(skipped_dupes)}")
    for slug in skipped_dupes:
        print(f"  skip {slug}")
    for r in new_records:
        po = len(r.get("partial_exits") or [])
        print(f"  add  {r['slug']:35s}  exit=${r['exit_pnl_usdc']:6.2f}  partials={po}")

    if dry_run:
        print("\nDRY RUN — no files written")
        return 0

    # Append to audit + session
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r) + "\n" for r in new_records]
    with open(AUDIT, "a", encoding="utf-8") as f:
        f.writelines(lines)
    with open(SESSION, "a", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"\nWrote {len(new_records)} records to audit + session.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
