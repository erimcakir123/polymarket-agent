"""Bitmiş ama açık kalmış pozisyonları manuel kapat (one-shot recovery).

Senaryo: Windows update zorla reboot/uyku botu durdurdu; dönüş sonrası
ESPN scoreboard "today/upcoming" gösterdiği için bot bitmiş maçları
göremiyor ve pozisyonlar `data/positions.json`'da açık kalıyor.

Bu script:
1. Hardcoded condition_id listesi alır (yanlış silme önlemi)
2. Polymarket CLOB API'den her market'in resolved durumunu çeker
3. closed=True + accepting_orders=False + winner field dolu olanlar için
   exit_price = kazanan token'ın price'ı (0.0 veya 1.0)
4. PnL hesabı: (exit_price - entry_price) * shares
5. `build_trade_logger()` ile audit + session mirror'a yazar
6. PortfolioManager.remove_position ile düşer
7. positions.json'a snapshot yazar

ÖNKOŞUL: Bot durmuş olmalı (process_lock çakışmasın). Önerilen sıra:
    1. taskkill /PID <bot_pid> /F  (veya manuel kapat)
    2. python scripts/recover_resolved_positions.py
    3. python scripts/reboot.py reload

DRY-RUN: --dry-run flag'i ile sadece raporlama (yazma yok).
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# src/ imports — script root'tan çalıştırılır
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.config.settings import load_config  # noqa: E402
from src.domain.portfolio import snapshot as portfolio_snapshot  # noqa: E402
from src.domain.portfolio.manager import PortfolioManager  # noqa: E402
from src.infrastructure.persistence.json_store import JsonStore  # noqa: E402
from src.orchestration._factory_loggers import build_trade_logger  # noqa: E402

logger = logging.getLogger("recover_resolved")

_CLOB_BASE = "https://clob.polymarket.com"
_CLOB_TIMEOUT = 15
_VALID_RESOLVED_PRICES = (0.0, 1.0)

# Hardcoded kurtarma hedefleri — script SADECE bu condition_id'lere dokunur.
# Yanlış pozisyon silmemek için isim+açıklama ile beraber tutuluyor.
RECOVERY_TARGETS: dict[str, str] = {
    "0xeb59b6d9a9f3e22c5eaa943b4b0f0184e73f005e7f30e2337abd71d1fa69d4ec": "Lynx vs Mercury (WNBA, end 13 May 02:00 UTC)",
    "0x7cebcda1d84a906a7093d3b67c2ddd618c7f342713864a9a454c2f475df9b1ec": "Ducks vs Golden Knights (NHL, end 13 May 01:30 UTC)",
}


def _fetch_clob_market(condition_id: str) -> dict | None:
    """Polymarket CLOB'dan market metadata. Hata → None (loglar)."""
    try:
        r = requests.get(f"{_CLOB_BASE}/markets/{condition_id}", timeout=_CLOB_TIMEOUT)
    except requests.RequestException as e:
        logger.error("CLOB fetch failed for %s: %s", condition_id[:24], e)
        return None
    if not r.ok:
        logger.error("CLOB HTTP %d for %s", r.status_code, condition_id[:24])
        return None
    return r.json()


def _resolved_exit_price(market: dict, direction: str) -> float | None:
    """Bot'un side'ı için resolved exit price (0.0 veya 1.0).

    direction='BUY_YES' → tokens[0] (YES) price
    direction='BUY_NO'  → tokens[1] (NO) price

    None döner: market henüz resolve olmadıysa, fiyat 0/1 değilse, format hatalıysa.
    """
    if not market.get("closed"):
        return None
    if market.get("accepting_orders"):
        # Closed ama hâlâ order kabul ediyorsa Polymarket henüz settle etmemiş.
        return None
    tokens = market.get("tokens") or []
    if len(tokens) < 2:
        return None
    idx = 0 if direction == "BUY_YES" else 1
    tok = tokens[idx]
    price = tok.get("price")
    if price is None:
        return None
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if p not in _VALID_RESOLVED_PRICES:
        return None
    return p


def _build_exit_data(exit_price: float, entry_price: float, shares: float,
                     size_usdc: float, now_iso: str) -> dict:
    """trade_logger.update_on_exit'in beklediği exit alanları."""
    pnl = (exit_price - entry_price) * shares
    pnl_pct = (pnl / size_usdc) if size_usdc else 0.0
    return {
        "exit_price": round(exit_price, 4),
        "exit_reason": "manual_recovery_resolved",
        "exit_pnl_usdc": round(pnl, 2),
        "exit_pnl_pct": round(pnl_pct, 4),
        "exit_timestamp": now_iso,
    }


def _process_target(
    cid: str, name: str, portfolio: PortfolioManager,
    trade_logger, dry_run: bool, now_iso: str,
) -> tuple[bool, float]:
    """Tek hedef için tüm akış. Return (success, pnl)."""
    pos = portfolio.positions.get(cid)
    if pos is None:
        logger.info("SKIP %s — already closed (not in positions.json)", name)
        return False, 0.0

    market = _fetch_clob_market(cid)
    if market is None:
        return False, 0.0

    exit_price = _resolved_exit_price(market, pos.direction)
    if exit_price is None:
        logger.warning(
            "ABORT %s — not yet resolved (closed=%s accepting_orders=%s)",
            name, market.get("closed"), market.get("accepting_orders"),
        )
        return False, 0.0

    exit_data = _build_exit_data(
        exit_price, pos.entry_price, pos.shares, pos.size_usdc, now_iso,
    )
    pnl = exit_data["exit_pnl_usdc"]

    if dry_run:
        logger.info(
            "DRY-RUN %s: entry=%.4f exit=%.1f shares=%.4f pnl=%+.2f",
            name, pos.entry_price, exit_price, pos.shares, pnl,
        )
        return True, pnl

    ok = trade_logger.update_on_exit(cid, exit_data)
    if not ok:
        logger.warning("FAIL %s — no matching open audit record (orphan?)", name)
        return False, 0.0

    portfolio.remove_position(cid, realized_pnl_usdc=pnl)
    logger.info(
        "RECOVERED %s: entry=%.4f exit=%.1f pnl=%+.2f",
        name, pos.entry_price, exit_price, pnl,
    )
    return True, pnl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="Sadece raporla, hiçbir dosyaya yazma")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    cfg = load_config()
    positions_store = JsonStore(ROOT / "data" / "positions.json")
    data = positions_store.load(default=None)
    if not isinstance(data, dict):
        logger.error("positions.json empty/invalid — abort")
        return 1

    portfolio = portfolio_snapshot.from_dict(data, initial_bankroll=cfg.initial_bankroll)
    trade_logger = build_trade_logger()
    now_iso = datetime.now(timezone.utc).isoformat()

    summary: list[tuple[str, float]] = []
    for cid, name in RECOVERY_TARGETS.items():
        ok, pnl = _process_target(cid, name, portfolio, trade_logger, args.dry_run, now_iso)
        if ok:
            summary.append((name, pnl))

    if args.dry_run:
        logger.info("--- DRY-RUN done, no files written ---")
        return 0

    if not summary:
        logger.info("Nothing to recover; positions.json unchanged")
        return 0

    positions_store.save(portfolio_snapshot.to_dict(portfolio))
    total = sum(pnl for _, pnl in summary)
    logger.info("--- RECOVERY DONE: %d positions, total PnL %+.2f USDC ---",
                len(summary), total)
    logger.info("Next step: python scripts/reboot.py reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
