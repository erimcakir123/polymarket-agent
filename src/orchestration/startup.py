"""Bot başlangıç akışı — state restore (TDD §11 Faz 5).

Akış:
  1. Process lock al
  2. Config yükle
  3. Persistence layer hazırla (JsonStore)
  4. Portfolio restore (logs/positions.json)
  5. Circuit breaker restore (logs/circuit_breaker_state.json)
  6. Blacklist restore (logs/blacklist.json)
  7. (Opsiyonel) Wallet bağla — LIVE/PAPER mode

Bu modül state'i kurup döner; ana döngü agent.py'de.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import AppConfig, Mode
from src.domain.guards.blacklist import Blacklist
from src.domain.portfolio.manager import PortfolioManager
from src.domain.risk.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState
from src.infrastructure.persistence.json_store import JsonStore

logger = logging.getLogger(__name__)

_POSITIONS_FILE = "logs/positions.json"
_BREAKER_FILE = "logs/circuit_breaker_state.json"
_BLACKLIST_FILE = "logs/blacklist.json"


@dataclass
class RuntimeState:
    """Agent'ın ana döngüsünün üzerinde çalışacağı tüm state."""
    config: AppConfig
    portfolio: PortfolioManager
    circuit_breaker: CircuitBreaker
    blacklist: Blacklist
    positions_store: JsonStore
    breaker_store: JsonStore
    blacklist_store: JsonStore


def bootstrap(config: AppConfig, logs_dir: Path | str = "logs") -> RuntimeState:
    """State'i kur, restore et, RuntimeState döner.

    LIVE mode için wallet/CLOB client bağlama bu dosyada YAPILMAZ — main.py'de
    yapılır; startup sadece domain + persistence durumunu kurar.
    """
    logs = Path(logs_dir)
    logs.mkdir(parents=True, exist_ok=True)

    positions_store = JsonStore(logs / "positions.json")
    breaker_store = JsonStore(logs / "circuit_breaker_state.json")
    blacklist_store = JsonStore(logs / "blacklist.json")

    # Portfolio restore
    portfolio = _restore_portfolio(positions_store, config.initial_bankroll)

    # Circuit breaker restore
    breaker = _restore_breaker(breaker_store, config)

    # Blacklist restore
    blacklist = _restore_blacklist(blacklist_store)

    logger.info(
        "Bootstrap complete: mode=%s bankroll=$%.2f positions=%d realized=$%.2f "
        "breaker_active=%s blacklist_conditions=%d",
        config.mode.value, portfolio.bankroll, portfolio.count(), portfolio.realized_pnl,
        breaker.state.breaker_active_until is not None,
        len(blacklist.condition_ids),
    )

    return RuntimeState(
        config=config,
        portfolio=portfolio,
        circuit_breaker=breaker,
        blacklist=blacklist,
        positions_store=positions_store,
        breaker_store=breaker_store,
        blacklist_store=blacklist_store,
    )


def _restore_portfolio(store: JsonStore, initial_bankroll: float) -> PortfolioManager:
    data = store.load(default=None)
    if not data or not isinstance(data, dict):
        return PortfolioManager(initial_bankroll=initial_bankroll)
    try:
        return PortfolioManager.from_snapshot(data, initial_bankroll=initial_bankroll)
    except Exception as e:
        logger.warning("Portfolio restore failed (%s), starting fresh", e)
        return PortfolioManager(initial_bankroll=initial_bankroll)


def _restore_breaker(store: JsonStore, config: AppConfig) -> CircuitBreaker:
    cb_cfg = CircuitBreakerConfig(
        daily_max_loss_pct=config.circuit_breaker.daily_max_loss_pct,
        hourly_max_loss_pct=config.circuit_breaker.hourly_max_loss_pct,
        consecutive_loss_limit=config.circuit_breaker.consecutive_loss_limit,
        cooldown_after_daily_min=config.circuit_breaker.cooldown_after_daily_min,
        cooldown_after_hourly_min=config.circuit_breaker.cooldown_after_hourly_min,
        cooldown_after_consecutive_min=config.circuit_breaker.cooldown_after_consecutive_min,
        entry_block_threshold=config.circuit_breaker.entry_block_threshold,
    )
    data = store.load(default=None)
    if isinstance(data, dict):
        try:
            state = CircuitBreakerState.from_dict(data)
            return CircuitBreaker(config=cb_cfg, state=state)
        except Exception as e:
            logger.warning("Breaker restore failed (%s), starting fresh", e)
    return CircuitBreaker(config=cb_cfg)


def _restore_blacklist(store: JsonStore) -> Blacklist:
    data = store.load(default=None)
    if isinstance(data, dict):
        try:
            return Blacklist.from_dict(data)
        except Exception as e:
            logger.warning("Blacklist restore failed (%s), starting fresh", e)
    return Blacklist()


def persist(state: RuntimeState) -> None:
    """Tüm state'i diske yaz. Light cycle sonunda çağrılır."""
    state.positions_store.save(state.portfolio.to_snapshot())
    state.breaker_store.save(state.circuit_breaker.state.to_dict())
    state.blacklist_store.save(state.blacklist.to_dict())
