"""Paper-mode executor — composes ClobBook + paper_fill + audit + fee/gas.

Orchestration layer: coordinates infra (book fetch + audit) and domain
(walk_buy/walk_sell). Returns dict result compatible with Executor.place_order
contract (order_id, status, filled_size_usdc, etc.).
"""
from __future__ import annotations

import datetime
import logging
import uuid
from pathlib import Path
from typing import Any, Callable

from src.config.settings import PaperConfig
from src.domain.execution.paper_fill import FillStatus, walk_buy, walk_sell
from src.infrastructure.apis.clob_book import ClobBook
from src.infrastructure.apis.clob_client import choose_order_strategy
from src.infrastructure.audit.paper_executions import PaperExecutionsLogger

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _top3(levels: list[dict]) -> list[dict]:
    # Polymarket asks DESC / bids ASC. Best at end. Take top 3 best.
    return [
        {"p": float(l.get("price", 0)), "s": float(l.get("size", 0))}
        for l in (levels or [])[-3:][::-1]
    ]


class PaperExecutor:
    """Realistic paper fill against live Polymarket orderbook."""

    def __init__(
        self,
        config: PaperConfig,
        audit_path: Path | str = "logs/audit/paper_executions.jsonl",
        http_get: Callable[..., Any] | None = None,
    ) -> None:
        self.cfg = config
        self._book = ClobBook(http_get=http_get, cache_ttl_sec=config.book_cache_ttl_sec)
        self._audit = PaperExecutionsLogger(Path(audit_path))

    def place_buy(self, token_id: str, target_price: float, target_size_usdc: float) -> dict:
        target_price = round(target_price, 2)
        if target_size_usdc < self.cfg.min_order_usdc:
            return self._rejected(token_id, "BUY", target_price, target_size_usdc, "below_min_order_usdc", {})
        book = self._book.fetch(token_id)
        strategy = choose_order_strategy(book, "BUY", target_price, target_size_usdc)
        result = walk_buy(
            asks=book.get("asks", []),
            target_price=strategy["price"],
            target_size_usdc=target_size_usdc,
            max_slippage_pct=self.cfg.max_buy_slippage_pct,
            min_fill_ratio=self.cfg.min_fill_ratio,
        )
        return self._record_and_return(token_id, "BUY", strategy, target_price, target_size_usdc, result, book)

    def place_sell(self, token_id: str, target_price: float, shares: float) -> dict:
        target_price = round(target_price, 2)
        notional = shares * target_price
        if notional < self.cfg.min_order_usdc:
            return self._rejected(token_id, "SELL", target_price, notional, "below_min_order_usdc", {})
        book = self._book.fetch(token_id)
        strategy = choose_order_strategy(book, "SELL", target_price, notional)
        result = walk_sell(
            bids=book.get("bids", []),
            target_price=strategy["price"],
            shares=shares,
            max_slippage_pct=self.cfg.max_sell_slippage_pct,
        )
        return self._record_and_return(token_id, "SELL", strategy, target_price, notional, result, book, shares_in=shares)

    def _record_and_return(
        self, token_id: str, side: str, strategy: dict,
        target_price: float, target_size_usdc: float, result, book: dict,
        shares_in: float | None = None,
    ) -> dict:
        fee = result.filled_size_usdc * (
            self.cfg.taker_fee_pct if strategy.get("strategy") == "market" else self.cfg.maker_fee_pct
        )
        gas = self.cfg.polygon_gas_usdc if result.status != FillStatus.REJECTED else 0.0
        order_id = f"paper_{uuid.uuid4().hex[:8]}"
        rec = {
            "ts": _now_iso(),
            "order_id": order_id,
            "token_id": token_id,
            "side": side,
            "strategy": strategy.get("strategy"),
            "order_type": strategy.get("order_type"),
            "target_price": target_price,
            "strategy_price": strategy.get("price"),
            "target_size_usdc": round(target_size_usdc, 4),
            "result_status": result.status.value,
            "filled_size_usdc": round(result.filled_size_usdc, 4),
            "filled_shares": round(result.filled_shares, 6),
            "weighted_avg_price": round(result.weighted_avg_price, 6),
            "fee_paid": round(fee, 6),
            "gas_paid": round(gas, 6),
            "reason": result.reason,
            "book_snapshot": {
                "asks_top3": _top3(book.get("asks", [])),
                "bids_top3": _top3(book.get("bids", [])),
            },
        }
        if shares_in is not None:
            rec["shares_in"] = shares_in
        self._audit.write(rec)
        # 2026-05-29 (Phase 3 follow-up): tennis-paper-lab parity. Status
        # UPPERCASE (FILLED/PARTIAL_FILL/REJECTED), filled_shares/avg_price
        # standardize alanları. Entry/exit processor bu schema'ya göre çalışır.
        status_upper = {
            FillStatus.FILLED: "FILLED",
            FillStatus.PARTIAL_FILL: "PARTIAL_FILL",
            FillStatus.REJECTED: "REJECTED",
        }[result.status]
        return {
            "order_id": order_id,
            "status": status_upper,
            "mode": "paper",
            "token_id": token_id,
            "side": side,
            "filled_shares": result.filled_shares,
            "avg_price": result.weighted_avg_price,
            "price": result.weighted_avg_price,  # backward-compat alias
            "size_usdc": target_size_usdc,        # intended (alias)
            "intended_size_usdc": target_size_usdc,
            "actual_size_usdc": round(result.filled_size_usdc, 4),
            "filled_size_usdc": result.filled_size_usdc,
            "fee_paid": fee,
            "gas_paid": gas,
            "reason": result.reason,
        }

    def _rejected(self, token_id: str, side: str, target_price: float, target_size_usdc: float, reason: str, book: dict) -> dict:
        order_id = f"paper_rej_{uuid.uuid4().hex[:8]}"
        rec = {
            "ts": _now_iso(),
            "order_id": order_id,
            "token_id": token_id,
            "side": side,
            "target_price": target_price,
            "target_size_usdc": round(target_size_usdc, 4),
            "result_status": "rejected",
            "filled_size_usdc": 0.0,
            "filled_shares": 0.0,
            "reason": reason,
            "book_snapshot": {
                "asks_top3": _top3(book.get("asks", [])),
                "bids_top3": _top3(book.get("bids", [])),
            },
        }
        self._audit.write(rec)
        return {
            "order_id": order_id,
            "status": "REJECTED",
            "mode": "paper",
            "token_id": token_id,
            "side": side,
            "reason": reason,
            "filled_shares": 0.0,
            "avg_price": 0.0,
            "intended_size_usdc": target_size_usdc,
            "actual_size_usdc": 0.0,
            "filled_size_usdc": 0.0,
        }
