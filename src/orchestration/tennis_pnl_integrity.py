"""Tennis-lab light cycle PnL telemetry — REST price refresh + realized PnL
drift detector (audit log vs snapshot karşılaştırması).

Amaç: tennis_agent.run_light_cycle'da iki adımı tek call'da topla, böylece
tennis_agent boyutu artmadan integrity check eklenebilir (tennis_agent
400 satır cap'inde).

Adımlar (tek call):
  1. tennis_rest_refresh.refresh_open_positions — fiyat tazeleme + log.
  2. check_realized_pnl_drift — portfolio.realized_pnl (positions.json snapshot)
     ile audit log toplamı (trade_history.jsonl) arasındaki sapma görünür yap.

Otomatik düzeltme YAPMAZ — startup.py reconcile GUARD-4 phantom-restored
entry'ler varsa snapshot > audit'i koruyor (true PnL kaybı riski). Bu modül
sadece visibility için ERROR log basar; dashboard `realized_pnl` widget'ı
audit-trades'ten okuduğu için kullanıcı yan yana karşılaştırabilir.
"""
from __future__ import annotations

import logging
from typing import Optional

from src.domain.portfolio.manager import PortfolioManager
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.orchestration.tennis_rest_refresh import refresh_open_positions

logger = logging.getLogger(__name__)

# startup.py _reconcile_realized_pnl ile aynı floating noise eşiği.
DRIFT_TOLERANCE_USD = 0.10


def audit_realized_sum(trade_logger: TradeHistoryLogger) -> float:
    """trade_history.jsonl'dan true realized = full-exit + partial-exit toplamı.

    GUARD: corrupt_threshold geçildiyse 0.0 döner (sessiz sahte değer yerine).
    Caller, drift hesabını skip eder.
    """
    if trade_logger.corrupt_threshold_exceeded:
        return 0.0
    total = 0.0
    for rec in trade_logger.read_all():
        for pe in rec.get("partial_exits") or []:
            total += float(pe.get("realized_pnl_usdc", 0.0) or 0.0)
        if rec.get("exit_price") is not None:
            total += float(rec.get("exit_pnl_usdc", 0.0) or 0.0)
    return total


def check_realized_pnl_drift(
    portfolio: PortfolioManager,
    trade_logger: TradeHistoryLogger,
) -> float:
    """Returns: drift (snapshot - audit). Drift > tolerance ise ERROR log.

    Otomatik düzeltme YAPMAZ. Dashboard "Realized P&L" widget'ı audit-tarafından
    okuduğu için kullanıcı drift'i widget vs positions.json'da görür.
    """
    if trade_logger.corrupt_threshold_exceeded:
        return 0.0
    audit_total = audit_realized_sum(trade_logger)
    snapshot_total = portfolio.realized_pnl
    drift = snapshot_total - audit_total
    if abs(drift) > DRIFT_TOLERANCE_USD:
        logger.error(
            "PnL DRIFT: snapshot.realized=$%.2f audit.realized=$%.2f delta=$%+.2f "
            "— dashboard Realized P&L widget audit'ten okuyor; positions.json değeri "
            "phantom/orphan'lardan sızdı. startup reconcile GUARD-4 koruması "
            "auto-fix engelliyor (true PnL kaybı riski).",
            snapshot_total, audit_total, drift,
        )
    return drift


def run_light_telemetry(
    portfolio: PortfolioManager,
    trade_logger: Optional[TradeHistoryLogger],
) -> tuple[int, int]:
    """tennis_agent.run_light_cycle entrypoint: REST refresh + drift check.

    Returns (refreshed, resolved) — geriye uyumlu refresh_open_positions sayıları.
    trade_logger None ise drift check skip (test/legacy code path).
    """
    n_open = len(portfolio.positions)
    refreshed, resolved = refresh_open_positions(portfolio)
    logger.info(
        "Light cycle: refreshed %d/%d prices via REST (%d resolved)",
        refreshed, n_open, resolved,
    )
    if trade_logger is not None:
        check_realized_pnl_drift(portfolio, trade_logger)
    return refreshed, resolved
