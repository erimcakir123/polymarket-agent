"""Phase 5 doğrulama: tennis-lab açık pozisyonları için bot fiyatı vs
Polymarket gerçeği karşılaştırması.

Her açık pozisyon için:
  - Bot'un kayıtlı current_price + unrealized_pnl_usdc (positions.json)
  - Polymarket gerçeği:
      Gamma /markets → outcomePrices[0] (kapanmış market için kesin değer)
      CLOB /book → mid/ask/bid (canlı market için piyasa fiyatı)
  - Drift = |bot - reality|
  - PASS: drift < $1.00 VEYA Gamma extreme (bot bir sonraki light cycle'da exit)

Kullanım:
  python scripts/verify_position_truth.py

Çıkış kodu: 0 = tüm pozisyonlar PASS, 1 = herhangi biri FAIL.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

CLOB_BOOK_URL = "https://clob.polymarket.com/book"
GAMMA_URL = "https://gamma-api.polymarket.com/markets"
TIMEOUT_SEC = 8.0
DRIFT_PASS_USD = 1.00

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POSITIONS_PATH = PROJECT_ROOT / "data" / "positions.json"


def _best_ask(asks: list) -> float:
    prices = [float(a.get("price", 0)) for a in (asks or [])
              if a.get("price") and float(a.get("price", 0)) > 0]
    return min(prices) if prices else 0.0


def _best_bid(bids: list) -> float:
    prices = [float(b.get("price", 0)) for b in (bids or [])
              if b.get("price") and float(b.get("price", 0)) > 0]
    return max(prices) if prices else 0.0


def _fetch_book(token_id: str) -> tuple[float, float] | None:
    try:
        resp = requests.get(CLOB_BOOK_URL, params={"token_id": token_id}, timeout=TIMEOUT_SEC)
        if resp.status_code != 200:
            return None
        d = resp.json()
        return _best_bid(d.get("bids") or []), _best_ask(d.get("asks") or [])
    except (requests.RequestException, ValueError):
        return None


def _fetch_gamma_yes(condition_id: str) -> float | None:
    try:
        resp = requests.get(GAMMA_URL, params={"condition_ids": condition_id},
                            timeout=TIMEOUT_SEC)
        if resp.status_code != 200:
            return None
        items = resp.json() or []
        if not items:
            return None
        raw = items[0].get("outcomePrices")
        if isinstance(raw, str):
            raw = json.loads(raw)
        if isinstance(raw, list) and raw:
            return float(raw[0])
    except (requests.RequestException, ValueError):
        return None
    return None


def _effective_truth_price(direction: str, gamma_yes: float | None,
                           book: tuple[float, float] | None) -> tuple[float | None, str]:
    """Pozisyon-tarafında gerçek fiyat + kaynak etiketi."""
    if gamma_yes is not None and (gamma_yes <= 0.03 or gamma_yes >= 0.97):
        # RESOLVED — direction-aware token price
        side_yes = gamma_yes if direction == "BUY_YES" else (1.0 - gamma_yes)
        return side_yes, "gamma-resolved"
    if book is not None:
        bid, ask = book
        if bid > 0 and ask > 0:
            mid = (bid + ask) / 2.0
            return mid, "clob-mid"
        if ask > 0:
            return ask, "clob-ask-only"
        if bid > 0:
            return bid, "clob-bid-only"
    return None, "no-data"


def main() -> int:
    if not POSITIONS_PATH.exists():
        print(f"FAIL: {POSITIONS_PATH} missing")
        return 1

    pos_data = json.loads(POSITIONS_PATH.read_text(encoding="utf-8"))
    positions = pos_data.get("positions", {})
    if not positions:
        print("PASS: no open positions")
        return 0

    all_pass = True
    print(f"=== Open position verification ({len(positions)} positions) ===\n")

    for cid, pos in positions.items():
        slug = pos.get("slug", cid[:24])
        direction = pos.get("direction", "?")
        token_id = pos.get("token_id", "")
        bot_price = float(pos.get("current_price", 0.0))
        bot_unrealized = float(pos.get("unrealized_pnl_usdc", 0.0))
        size = float(pos.get("size_usdc", 0.0))
        shares = float(pos.get("shares", 0.0))

        gamma_yes = _fetch_gamma_yes(cid)
        book = _fetch_book(token_id)
        truth_price, source = _effective_truth_price(direction, gamma_yes, book)

        if truth_price is None:
            print(f"[FAIL] {slug[:50]:50} | NO DATA from Gamma or CLOB")
            all_pass = False
            continue

        true_unrealized = shares * truth_price - size
        drift = abs(true_unrealized - bot_unrealized)
        verdict = "PASS" if drift < DRIFT_PASS_USD else "FAIL"
        if verdict == "FAIL":
            all_pass = False

        print(f"[{verdict}] {slug[:50]:50}")
        print(f"   direction={direction} size=${size:.2f} shares={shares:.2f}")
        print(f"   bot price={bot_price:.3f}  unrealized=${bot_unrealized:+.2f}")
        print(f"   truth price={truth_price:.3f} ({source})  unrealized=${true_unrealized:+.2f}")
        print(f"   drift=${drift:.2f}\n")

    print("=" * 50)
    print(f"{'PASS' if all_pass else 'FAIL'} overall")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
