"""Sahte tennis pozisyonu üret — Stage 9 dashboard widget doğrulaması.

Tek amaç: dashboard'ın `/api/positions` + `/api/trades/history` widget'larında
gözükecek deterministik, idempotent sahte pozisyon yazmak. Real cycle açtığı
pozisyonlardan ayrı tutulur (condition_id farklı).

Yazılan dosyalar:
  - data/positions.json (mevcut entries korunur; FAKE_CONDITION_ID eklenir)
  - logs/session/trade_history.jsonl + logs/audit/trade_history.jsonl
    (TradeRecord — entry doldurulmuş, exit boş)

Idempotent: FAKE_CONDITION_ID positions.json'da zaten varsa hiçbir şey yazılmaz.

Kullanım:
    python scripts/inject_fake_tennis_position.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows cp1252 console Turkish karakter çıktısında crash eder; UTF-8 zorla.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger, TradeRecord
from src.models.position import Position

# Sabit sahte değerler — gerçek pozisyonlarla çakışmaz, deterministik.
FAKE_CONDITION_ID = "0xtest00000000000000000000000000000000000000000000000000000000fake"
FAKE_TOKEN_ID = "999999999999999999999999999999999999999999999999999999999999999999"
FAKE_EVENT_ID = "999000"
FAKE_QUESTION = "Sinner vs Test Player Set 1 Winner"
FAKE_SLUG = "atp-sinner-test-2026-05-20-first-set-winner"
FAKE_YES_PRICE = 0.65
FAKE_SIZE_USDC = 50.0
FAKE_CONFIDENCE = "A"
FAKE_SPORT_TAG = "tennis_atp"


def main() -> int:
    data_dir = _ROOT / "data"
    logs_dir = _ROOT / "logs"
    positions_store = JsonStore(data_dir / "positions.json")
    blob = positions_store.load({"positions": {}, "realized_pnl": 0.0, "high_water_mark": 0.0})

    if FAKE_CONDITION_ID in blob.get("positions", {}):
        print(f"[inject] Skip — fake pozisyon zaten mevcut (condition_id={FAKE_CONDITION_ID[:24]}...)")
        return 0

    now = datetime.now(timezone.utc)
    shares = FAKE_SIZE_USDC / FAKE_YES_PRICE

    position = Position(
        condition_id=FAKE_CONDITION_ID,
        token_id=FAKE_TOKEN_ID,
        direction="BUY_YES",
        entry_price=FAKE_YES_PRICE,
        size_usdc=FAKE_SIZE_USDC,
        shares=shares,
        slug=FAKE_SLUG,
        entry_timestamp=now,
        entry_reason="tennis",
        confidence=FAKE_CONFIDENCE,
        anchor_probability=FAKE_YES_PRICE,  # P(YES) anchor
        current_price=FAKE_YES_PRICE,
        sport_tag=FAKE_SPORT_TAG,
        event_id=FAKE_EVENT_ID,
        match_start_iso=now.isoformat(),
        question=FAKE_QUESTION,
    )

    blob.setdefault("positions", {})[FAKE_CONDITION_ID] = json.loads(position.model_dump_json())
    positions_store.save(blob)

    record = TradeRecord(
        slug=FAKE_SLUG,
        condition_id=FAKE_CONDITION_ID,
        event_id=FAKE_EVENT_ID,
        token_id=FAKE_TOKEN_ID,
        question=FAKE_QUESTION,
        sport_tag=FAKE_SPORT_TAG,
        sport_category="tennis",
        league="atp",
        direction="BUY_YES",
        entry_price=FAKE_YES_PRICE,
        size_usdc=FAKE_SIZE_USDC,
        shares=shares,
        confidence=FAKE_CONFIDENCE,
        bookmaker_prob=0.0,
        anchor_probability=FAKE_YES_PRICE,
        entry_reason="tennis_fake_inject",
        entry_timestamp=now.isoformat(),
    )

    # Dashboard read_trades hem session/ hem audit/ okur. Stage 9 reset session/audit
    # mirror'ları boşalttığı için ikisine de yazıyoruz — gerçek pipeline mirror'ı
    # equity_history.jsonl için zaten yapıyor ama tennis trade_logger sadece logs/
    # köküne yazıyor (factory wiring artifact). Dashboard görünürlüğü için
    # hedef paths burada explicit:
    audit_logger = TradeHistoryLogger(
        str(logs_dir / "audit" / "trade_history.jsonl"),
        mirror_path=str(logs_dir / "session" / "trade_history.jsonl"),
    )
    audit_logger.log(record)

    print(
        f"[inject] OK — condition_id={FAKE_CONDITION_ID[:24]}... "
        f"tier={FAKE_CONFIDENCE} size=${FAKE_SIZE_USDC:.2f} "
        f"price={FAKE_YES_PRICE:.2f}",
    )
    print(f"[inject] positions.json: +1 entry (total {len(blob['positions'])})")
    print(f"[inject] trade_history.jsonl: +1 open entry (audit + session mirror)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
