"""Bot başlangıç akışı — state restore (DECISIONS §11 Faz 5).

Akış:
  1. Process lock al
  2. Config yükle
  3. Persistence layer hazırla (JsonStore)
  4. Portfolio restore (data/positions.json)
  5. Circuit breaker restore (data/circuit_breaker_state.json)
  6. Blacklist restore (data/blacklist.json)
  7. (Opsiyonel) Wallet bağla — LIVE/PAPER mode

Bu modül state'i kurup döner; ana döngü agent.py'de.

SPEC-Z17 (2026-06-04): legacy trade_history.jsonl reconciliation path tamamen
kaldırıldı. Append-only event log (trade_events.jsonl) tek truth — atomic
rewrite + phantom-restore + reconcile sınıfı bug'lar artık imkansız.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import AppConfig
from src.domain.guards.blacklist import Blacklist
from src.domain.portfolio import snapshot as portfolio_snapshot
from src.domain.portfolio.manager import PortfolioManager
from src.domain.risk.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState
from src.infrastructure.persistence.json_store import JsonStore

logger = logging.getLogger(__name__)

_POSITIONS_FILE = "data/positions.json"
_BREAKER_FILE = "data/circuit_breaker_state.json"
_BLACKLIST_FILE = "data/blacklist.json"
_SESSION_START_FILE = "session_start.json"  # logs_dir-relative


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


def bootstrap(
    config: AppConfig,
    logs_dir: Path | str = "data",
    trade_history_path: Path | str | None = None,  # noqa: ARG001 — geri-uyumluluk
) -> RuntimeState:
    """State'i kur, restore et, RuntimeState döner.

    LIVE mode için wallet/CLOB client bağlama bu dosyada YAPILMAZ — main.py'de
    yapılır; startup sadece domain + persistence durumunu kurar.

    Args:
        config: App config.
        logs_dir: State dosyaları (positions/breaker/blacklist) için dizin.
            Production: data/. Test: tmp_path.
        trade_history_path: SPEC-Z17 sonrası kullanılmıyor (geriye-uyumluluk için
            kabul edilir, eski test çağrıları bozulmasın). Yeni truth kaynağı
            logs/audit/trade_events.jsonl event log'udur, reconcile path tamamen
            kaldırıldı.
    """
    logs = Path(logs_dir)
    logs.mkdir(parents=True, exist_ok=True)

    _ensure_session_start(logs)

    positions_store = JsonStore(logs / "positions.json")
    breaker_store = JsonStore(logs / "circuit_breaker_state.json")
    blacklist_store = JsonStore(logs / "blacklist.json")

    portfolio = _restore_portfolio(positions_store, config.initial_bankroll)
    breaker = _restore_breaker(breaker_store, config)
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


def _ensure_session_start(logs: Path) -> None:
    """Reboot sonrasi data/session_start.json yoksa olustur (current UTC).

    Reload mevcut dosyayi korur (varsa dokunmaz) -> dashboard topbar'inda
    session basladi zamani sabit kalir. Reboot.py bu dosyayi siler -> bir
    sonraki bootstrap'ta yeniden olusur.
    """
    from datetime import datetime, timezone  # noqa: PLC0415 - lazy stdlib import
    p = logs / _SESSION_START_FILE
    if p.exists():
        return
    iso = datetime.now(timezone.utc).isoformat()
    try:
        p.write_text(json.dumps({"iso": iso}), encoding="utf-8")
    except OSError as e:
        logger.warning("session_start.json write failed: %s", e)


def _restore_portfolio(store: JsonStore, initial_bankroll: float) -> PortfolioManager:
    data = store.load(default=None)
    if not data or not isinstance(data, dict):
        return PortfolioManager(initial_bankroll=initial_bankroll)
    try:
        return portfolio_snapshot.from_dict(data, initial_bankroll=initial_bankroll)
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
    state.positions_store.save(portfolio_snapshot.to_dict(state.portfolio))
    state.breaker_store.save(state.circuit_breaker.state.to_dict())
    state.blacklist_store.save(state.blacklist.to_dict())
