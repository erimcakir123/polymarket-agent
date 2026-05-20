"""Sahte tennis pozisyonunu kapat — Stage 9 dashboard "Exited" widget doğrulaması.

inject_fake_tennis_position.py'nin açtığı FAKE_CONDITION_ID pozisyonunu kapatır:
  - trade_history.jsonl'deki open record'a exit alanlarını yazar (audit + session)
  - positions.json'dan kaldırır
  - logs/session/+audit/equity_history.jsonl'a yeni snapshot yazar (bankroll güncel)

Idempotent: pozisyon zaten yoksa hata vermeden çıkar.

Kullanım:
    python scripts/close_fake_tennis_position.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows cp1252 console Turkish karakter çıktısında crash eder; UTF-8 zorla.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.infrastructure.persistence.equity_history import EquityHistoryLogger, EquitySnapshot
from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from scripts.inject_fake_tennis_position import FAKE_CONDITION_ID

FAKE_EXIT_PRICE = 0.75
FAKE_EXIT_REASON = "manual_test"


def main() -> int:
    data_dir = _ROOT / "data"
    logs_dir = _ROOT / "logs"
    positions_store = JsonStore(data_dir / "positions.json")
    blob = positions_store.load({"positions": {}, "realized_pnl": 0.0, "high_water_mark": 0.0})

    fake = blob.get("positions", {}).get(FAKE_CONDITION_ID)
    if fake is None:
        print(f"[close] Skip — fake pozisyon yok (condition_id={FAKE_CONDITION_ID[:24]}...)")
        return 0

    shares = float(fake["shares"])
    entry_price = float(fake["entry_price"])
    size_usdc = float(fake["size_usdc"])

    realized_pnl_usdc = shares * (FAKE_EXIT_PRICE - entry_price)
    realized_pnl_pct = realized_pnl_usdc / size_usdc if size_usdc > 0 else 0.0
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1) Trade history exit alanlarını güncelle (audit + session mirror).
    audit_logger = TradeHistoryLogger(
        str(logs_dir / "audit" / "trade_history.jsonl"),
        mirror_path=str(logs_dir / "session" / "trade_history.jsonl"),
    )
    updated = audit_logger.update_on_exit(
        FAKE_CONDITION_ID,
        {
            "exit_price": FAKE_EXIT_PRICE,
            "exit_reason": FAKE_EXIT_REASON,
            "exit_pnl_usdc": round(realized_pnl_usdc, 4),
            "exit_pnl_pct": round(realized_pnl_pct, 4),
            "exit_timestamp": now_iso,
        },
    )
    if not updated:
        print(f"[close] WARN — trade_history'de matching open record bulunamadı (orphan?)")

    # 2) positions.json'dan kaldır + realized_pnl artır.
    blob["positions"].pop(FAKE_CONDITION_ID, None)
    blob["realized_pnl"] = float(blob.get("realized_pnl", 0.0)) + realized_pnl_usdc
    positions_store.save(blob)

    # 3) Yeni equity snapshot (bankroll'a realized eklenmiş).
    invested = sum(float(p.get("size_usdc", 0.0)) for p in blob["positions"].values())
    open_pnl = sum(
        float(p.get("shares", 0.0)) * float(p.get("current_price", 0.0))
        - float(p.get("size_usdc", 0.0))
        for p in blob["positions"].values()
    )
    # Bankroll formülü = initial - invested + realized (dashboard computed ile aynı)
    # initial_bankroll config'den okumak script'i ağırlaştırır; positions.json'daki
    # high_water_mark'i taban kabul ediyoruz (gerçek bot equity_history yazıyor).
    base_bankroll = float(blob.get("high_water_mark", 0.0)) or 500.0
    bankroll = base_bankroll - invested + float(blob["realized_pnl"])

    snapshot = EquitySnapshot(
        timestamp=now_iso,
        bankroll=round(bankroll, 4),
        realized_pnl=round(float(blob["realized_pnl"]), 4),
        unrealized_pnl=round(open_pnl, 4),
        invested=round(invested, 4),
        open_positions=len(blob["positions"]),
    )
    equity_logger = EquityHistoryLogger(
        str(logs_dir / "audit" / "equity_history.jsonl"),
        mirror_path=str(logs_dir / "session" / "equity_history.jsonl"),
    )
    equity_logger.log(snapshot)

    print(
        f"[close] OK — condition_id={FAKE_CONDITION_ID[:24]}... "
        f"exit_price={FAKE_EXIT_PRICE:.2f} pnl=${realized_pnl_usdc:+.2f} "
        f"({realized_pnl_pct*100:+.1f}%)",
    )
    print(f"[close] positions.json: -1 entry (kalan {len(blob['positions'])})")
    print(f"[close] equity snapshot: bankroll=${bankroll:.2f} realized=${blob['realized_pnl']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
