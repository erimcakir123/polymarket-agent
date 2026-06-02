"""One-off: manually resolve 2 stuck WNBA total positions Polymarket'in resolve
ettigi ama bot'un yakalayamadigi positionlar icin.

Polymarket Gamma'dan dogrulandi:
- wnba-tor-chi-2026-05-27-total-169pt5: Over kazandi (total 215 > 169.5). Bot BUY_NO -> kaybetti.
- wnba-conn-por-2026-05-27-total-166pt5: Under kazandi (total 132 < 166.5). Bot BUY_NO -> kazandi.

Bu script ana bot CALISIRKEN CALISTIRILMAMALI. reboot.py reload oncesi calistir.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0")
POSITIONS = ROOT / "data" / "positions.json"
AUDIT_TH = ROOT / "logs" / "audit" / "trade_history.jsonl"
SESSION_TH = ROOT / "logs" / "session" / "trade_history.jsonl"

RESOLUTIONS = [
    # condition_id -> (owned_exit_price, winner_label)
    ("0xf65557b92b70e4983cdf6e6cfc0c75322ebdcaed557e488a7da834a8abdc30c7",
     0.0, "Over 169.5 (total 215) - NO (Under) lost"),
    ("0x76c43f1af348636a0b2f08c206bb82ab1223d91dfdcfcbc4034c6ea62264d499",
     1.0, "Under 166.5 (total 132) - NO (Under) won"),
]


def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.bak.manual_resolve_{stamp}")
    shutil.copy2(path, bak)
    return bak


def main() -> None:
    print("=== Manual resolve scripti ===\n")

    # Backup
    print("1. Backup:")
    for p in (POSITIONS, AUDIT_TH, SESSION_TH):
        bak = backup(p)
        print(f"   {p.name} -> {bak.name}")

    # Load positions
    with POSITIONS.open(encoding="utf-8") as f:
        port = json.load(f)
    print(f"\n2. Mevcut realized_pnl: ${port['realized_pnl']:+.2f}")
    print(f"   Acik pozisyon: {len(port['positions'])}")

    now_iso = datetime.now(timezone.utc).isoformat()
    total_new_realized = 0.0
    audit_records = []
    session_records = []

    print(f"\n3. Resolution kayitlari hesaplaniyor:")
    for cid, owned_exit, label in RESOLUTIONS:
        pos = port["positions"].get(cid)
        if pos is None:
            print(f"   [SKIP] {cid[:30]}: pozisyon yok")
            continue

        # Bot'un trade_history sema'siyla tutarli:
        # exit_price = owned-side resolution price (BUY_NO icin NO token)
        # exit_pnl_pct = (exit - entry) / entry
        # exit_pnl_usdc = size_usdc * pct (kalan size'a uygulanir)
        entry_price = pos["entry_price"]
        size = pos["size_usdc"]
        pct = (owned_exit - entry_price) / entry_price
        realized = size * pct
        total_new_realized += realized

        record = dict(pos)
        record["exit_price"] = owned_exit
        record["exit_pnl_pct"] = round(pct, 4)
        record["exit_pnl_usdc"] = round(realized, 2)
        record["exit_reason"] = "resolved"
        record["exit_timestamp"] = now_iso
        record["final_outcome"] = label
        record["resolution_source"] = "polymarket_gamma_manual"
        record["resolution_timestamp"] = now_iso

        audit_records.append(record)
        session_records.append(record)
        print(f"   {pos['slug']:<55} pct={pct:+.4f} realized=${realized:+.2f}")
        print(f"     -> {label}")

    if not audit_records:
        print("\n   Hicbir pozisyon resolve edilmedi. Cikiliyor.")
        return

    # Append trade records (preserve existing audit + session JSONL)
    print(f"\n4. Trade records yaziliyor:")
    with AUDIT_TH.open("a", encoding="utf-8") as f:
        for r in audit_records:
            f.write(json.dumps(r) + "\n")
    print(f"   {AUDIT_TH.name}: +{len(audit_records)} kayit")

    with SESSION_TH.open("a", encoding="utf-8") as f:
        for r in session_records:
            f.write(json.dumps(r) + "\n")
    print(f"   {SESSION_TH.name}: +{len(session_records)} kayit")

    # Remove positions + update realized_pnl
    for cid, _, _ in RESOLUTIONS:
        port["positions"].pop(cid, None)
    port["realized_pnl"] = round(port["realized_pnl"] + total_new_realized, 2)

    with POSITIONS.open("w", encoding="utf-8") as f:
        json.dump(port, f, indent=2, ensure_ascii=False)

    print(f"\n5. positions.json guncellendi:")
    print(f"   Yeni realized_pnl: ${port['realized_pnl']:+.2f}")
    print(f"   Net yeni realize: ${total_new_realized:+.2f}")
    print(f"   Kalan acik pozisyon: {len(port['positions'])}")

    print(f"\n=== Tamamlandi ===")
    print(f"Simdi: python scripts/reboot.py reload")


if __name__ == "__main__":
    main()
