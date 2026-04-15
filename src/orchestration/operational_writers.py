"""Operasyonel disk yazıcıları — snapshot/log fonksiyonları (TDD §4 thin orchestration).

Agent.py'nin 400 satır limiti altında kalması için ayrıştırıldı. Tek sorumluluk:
gate skip / eligible queue / equity snapshot disk yazımları.

Tüm fonksiyonlar OSError'ı yakalar + warning log atar (sessiz hata yok).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.domain.portfolio.manager import PortfolioManager
from src.infrastructure.persistence.equity_history import EquityHistoryLogger, EquitySnapshot
from src.infrastructure.persistence.skipped_trade_logger import (
    SkippedTradeLogger,
    SkippedTradeRecord,
)
from src.models.market import MarketData

logger = logging.getLogger(__name__)


def log_skip(skipped_logger: SkippedTradeLogger, market: MarketData, reason: str) -> None:
    """Gate skip kaydı → SkippedTradeLogger."""
    record = SkippedTradeRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        slug=market.slug,
        sport_tag=market.sport_tag,
        question=market.question,
        event_id=market.event_id or "",
        entry_price=market.yes_price,
        skip_reason=reason or "unknown",
    )
    try:
        skipped_logger.log(record)
    except OSError as e:
        logger.warning("Skipped logger write failed: %s", e)


def log_equity_snapshot(portfolio: PortfolioManager,
                        equity_logger: EquityHistoryLogger) -> None:
    """Heavy cycle sonu bankroll/equity snapshot → EquityHistoryLogger."""
    unrealized = 0.0
    invested = 0.0
    for pos in portfolio.positions.values():
        invested += pos.size_usdc
        unrealized += pos.unrealized_pnl_usdc
    snap = EquitySnapshot(
        timestamp=datetime.now(timezone.utc).isoformat(),
        bankroll=portfolio.bankroll,
        realized_pnl=portfolio.realized_pnl,
        unrealized_pnl=unrealized,
        invested=invested,
        open_positions=len(portfolio.positions),
    )
    try:
        equity_logger.log(snap)
    except OSError as e:
        logger.warning("Equity snapshot write failed: %s", e)
