"""Bot başlangıç akışı — state restore (TDD §11 Faz 5).

Akış:
  1. Process lock al
  2. Config yükle
  3. Persistence layer hazırla (JsonStore)
  4. Portfolio restore (data/positions.json)
  5. Circuit breaker restore (data/circuit_breaker_state.json)
  6. Blacklist restore (data/blacklist.json)
  7. (Opsiyonel) Wallet bağla — LIVE/PAPER mode

Bu modül state'i kurup döner; ana döngü agent.py'de.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import AppConfig, Mode
from src.domain.guards.blacklist import Blacklist
from src.domain.portfolio import snapshot as portfolio_snapshot
from src.domain.portfolio.manager import PortfolioManager
from src.domain.risk.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState
from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger, TradeRecord

logger = logging.getLogger(__name__)

_POSITIONS_FILE = "data/positions.json"
_BREAKER_FILE = "data/circuit_breaker_state.json"
_BLACKLIST_FILE = "data/blacklist.json"
# Trade history audit ground truth — reboot dokunmaz, crash recovery için.
_TRADE_HISTORY_AUDIT = "logs/audit/trade_history.jsonl"


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
    trade_history_path: Path | str = _TRADE_HISTORY_AUDIT,
) -> RuntimeState:
    """State'i kur, restore et, RuntimeState döner.

    LIVE mode için wallet/CLOB client bağlama bu dosyada YAPILMAZ — main.py'de
    yapılır; startup sadece domain + persistence durumunu kurar.

    Args:
        config: App config.
        logs_dir: State dosyaları (positions/breaker/blacklist) için dizin.
            Production: data/. Test: tmp_path.
        trade_history_path: Realized PnL reconcile için ground-truth trade log.
            Production: logs/audit/trade_history.jsonl. Test: tmp_path/trade_history.jsonl
            (genelde dosya yok → reconcile no-op).
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

    # Reconcile realized PnL — audit trade_history.jsonl ground truth (crash recovery)
    trade_logger = TradeHistoryLogger(str(trade_history_path))

    # SPEC-D: orphan pozisyon tespiti — data/positions.json'da olup audit'te
    # entry'si olmayan pozisyonlar icin "phantom-restored" entry yaz; gelecek
    # scale-out'lar matching bulsun. Reconcile'dan ONCE.
    _detect_and_restore_orphans(portfolio, trade_logger)

    _reconcile_realized_pnl(portfolio, trade_logger, config.initial_bankroll)

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


def _detect_and_restore_orphans(
    portfolio: PortfolioManager,
    trade_logger: TradeHistoryLogger,
) -> int:
    """data/positions.json'da olup audit'te entry'si olmayan pozisyonlar icin
    "phantom-restored" entry yaz. Gelecek scale-out'larin _rewrite_matching
    çağrıları doğru kayda denk gelir.

    Reset/reboot sonrası audit silinmiş ama positions.json hayatta kalmışsa
    bu fonksiyon defteri yeniden açar. Geçmiş scale-out'lar geriye dönük
    yazılmaz — sadece ilerideki kayıtlar tutulur.

    Return: kaç orphan tespit edildi.
    """
    if not portfolio.positions:
        return 0

    records = trade_logger.read_all()
    audit_open_cids = {
        rec.get("condition_id") for rec in records
        if rec.get("exit_price") is None and rec.get("condition_id")
    }

    orphans = [
        (cid, pos) for cid, pos in portfolio.positions.items()
        if cid not in audit_open_cids
    ]

    if not orphans:
        return 0

    logger.warning(
        "Orphan positions detected: %d positions in data/positions.json have no "
        "audit entry. Writing phantom-restored entries so future scale-outs match.",
        len(orphans),
    )

    for cid, pos in orphans:
        try:
            original_reason = pos.entry_reason or "unknown"
            record = TradeRecord(
                slug=pos.slug or "",
                condition_id=cid,
                event_id=pos.event_id or "",
                token_id=pos.token_id or "",
                question=pos.question or "",
                sport_tag=pos.sport_tag or "",
                sport_category="",
                league="",
                direction=pos.direction,
                entry_price=pos.entry_price,
                size_usdc=pos.size_usdc,
                shares=pos.shares,
                confidence=pos.confidence or "",
                bookmaker_prob=pos.bookmaker_prob or 0.0,
                anchor_probability=pos.anchor_probability,
                num_bookmakers=0.0,
                has_sharp=False,
                # SPEC-D: prefix ile phantom işareti — schema değişikliği yok.
                entry_reason=f"phantom-restored:{original_reason}",
                entry_timestamp=pos.match_start_iso or "",
            )
            trade_logger.log(record)
            logger.info(
                "Phantom-restored audit entry for orphan position: %s",
                pos.slug[:35],
            )
        except Exception as e:
            logger.error(
                "Failed to write phantom-restored entry for %s: %s",
                cid[:24], e,
            )

    return len(orphans)


def _reconcile_realized_pnl(portfolio: PortfolioManager, trade_logger: TradeHistoryLogger,
                            initial_bankroll: float) -> None:
    """trade_history.jsonl'dan true realized hesapla, portfolio snapshot'ıyla
    uyumsuzsa düzelt + bankroll'u yeniden türet (crash recovery sonrası).

    True realized = sum(full_exit.exit_pnl_usdc) + sum(partial_exits.realized_pnl_usdc).

    GUARD-1 (SPEC-A): trade_history boş + snapshot.realized > 0 → "logging gap" senaryosu.
    Otomatik zerolama YAPMA (silent state corruption riski). Snapshot'a güven, WARN.

    GUARD-2 (SPEC-A3): trade_history corrupt threshold geçtiyse reconcile abort,
    snapshot'a güven (bozuk dosyadan eksik realized hesaplamak yerine).
    """
    records = trade_logger.read_all()

    # GUARD-2 (SPEC-A3): corrupt threshold exceeded → abort, trust snapshot
    if trade_logger.corrupt_threshold_exceeded:
        logger.warning(
            "Reconcile aborted: trade_history corrupt_lines=%d exceeded threshold; "
            "trusting snapshot.realized=$%.2f.",
            trade_logger.corrupt_lines, portfolio.realized_pnl,
        )
        return

    if not records:
        if abs(portfolio.realized_pnl) > 0.01:
            logger.warning(
                "Reconcile skipped: trade_history empty but snapshot.realized=$%.2f — "
                "logging gap suspected; trusting snapshot. Investigate trade_logger silent failures.",
                portfolio.realized_pnl,
            )
        return

    # GUARD-3 (SPEC-D): records var ama hicbir exit verisi yok (hepsi phantom-restored
    # entry, scale-out/full-exit henüz yazılmamış) → snapshot'a güven, otomatik zerolama yapma.
    has_exit_data = any(
        rec.get("exit_price") is not None or (rec.get("partial_exits") and len(rec["partial_exits"]) > 0)
        for rec in records
    )
    if not has_exit_data:
        if abs(portfolio.realized_pnl) > 0.01:
            logger.warning(
                "Reconcile skipped: %d records but no exit data (phantom-restored only) — "
                "trusting snapshot.realized=$%.2f.",
                len(records), portfolio.realized_pnl,
            )
        return

    true_realized = 0.0
    for rec in records:
        for pe in rec.get("partial_exits") or []:
            true_realized += float(pe.get("realized_pnl_usdc", 0.0))
        if rec.get("exit_price") is not None:
            true_realized += float(rec.get("exit_pnl_usdc", 0.0))

    delta = true_realized - portfolio.realized_pnl
    if abs(delta) < 0.01:  # floating noise — eşit kabul
        return

    logger.warning(
        "Realized PnL reconciliation: snapshot=$%.2f, log=$%.2f, delta=$%+.2f — using log",
        portfolio.realized_pnl, true_realized, delta,
    )
    portfolio.realized_pnl = true_realized
    portfolio.recalculate_bankroll(initial_bankroll)


def persist(state: RuntimeState) -> None:
    """Tüm state'i diske yaz. Light cycle sonunda çağrılır."""
    state.positions_store.save(portfolio_snapshot.to_dict(state.portfolio))
    state.breaker_store.save(state.circuit_breaker.state.to_dict())
    state.blacklist_store.save(state.blacklist.to_dict())
