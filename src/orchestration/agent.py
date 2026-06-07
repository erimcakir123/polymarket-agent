"""Ana agent döngüsü — katmanları bağlayan orchestrator (DECISIONS §4).

Heavy cycle: EntryProcessor'a delegate edilir.
Light cycle: ExitProcessor'a delegate edilir.

Bu dosya sadece lifecycle koordinasyonu yapar — iş mantığı
entry_processor/exit_processor + domain/strategy'de, I/O infrastructure'da.
"""
from __future__ import annotations

import atexit
import logging
import time
from dataclasses import dataclass

from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.apis.espn_client import ESPNClient
from src.infrastructure.apis.gamma_client import GammaClient
from src.infrastructure.executor import Executor
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.trade_event_log import TradeEventLog
from src.infrastructure.telegram.command_poller import TelegramCommandPoller
from src.infrastructure.telegram.notifier import TelegramNotifier
from src.infrastructure.websocket.price_feed import PriceFeed
from src.orchestration._agent_resilience import CycleResilience
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.entry_processor import EntryProcessor
from src.orchestration.exit_processor import ExitProcessor
from src.orchestration.health_monitor import HealthMonitor
from src.orchestration.roster_drift_monitor import RosterDriftMonitor
from src.orchestration.scanner import MarketScanner
from src.orchestration.startup import RuntimeState, persist
from src.orchestration.stock_queue import StockQueue
from src.orchestration.score_enricher import ScoreEnricher
from src.orchestration.tennis_start_enricher import TennisStartEnricher
from src.strategy.entry.gate import EntryGate
from src.strategy.entry.mlb_submarket_engine_protocol import MlbSubmarketEngineProtocol

logger = logging.getLogger(__name__)


@dataclass
class AgentDeps:
    """Dependency injection container — test için mock'lanabilir."""
    state: RuntimeState
    scanner: MarketScanner
    cycle_manager: CycleManager
    executor: Executor
    odds_client: object
    gate: EntryGate
    cooldown: CooldownTracker
    equity_logger: EquityHistoryLogger
    skipped_logger: SkippedTradeLogger
    stock: StockQueue
    bot_status_writer: BotStatusWriter
    price_feed: PriceFeed | None = None
    trade_event_log: TradeEventLog | None = None  # SPEC-Z17: append-only event log (tek truth)
    command_poller: TelegramCommandPoller | None = None
    score_enricher: ScoreEnricher | None = None  # SPEC-B: light cycle score injector + SPEC-Z5 match_live refresh
    mlb_submarket_engine: MlbSubmarketEngineProtocol | None = None  # SPEC-R: Plan 4'te gerçek engine
    tennis_start_enricher: TennisStartEnricher | None = None  # SPEC: light cycle'da tennis pozisyonlarinin match_start_iso'sunu ESPN ile refresh eder
    espn_client: ESPNClient | None = None  # SPEC-force-close 2026-05-27: get_match_status icin
    gamma_client: GammaClient | None = None  # 2026-05-28: ExitProcessor polymarket-resolution detector
    notifier: TelegramNotifier | None = None  # SPEC-TG-001 2026-06-02: entry/exit/critical alert
    health_monitor: HealthMonitor | None = None  # SPEC-TG-001 2026-06-02: periyodik health check
    roster_drift_monitor: RosterDriftMonitor | None = None  # SPEC-Z9 2026-06-03: günde 1 Polymarket /teams + /sports diff


class Agent:
    """Bot ana döngüsü. Thin orchestration layer."""

    def __init__(self, deps: AgentDeps) -> None:
        self.deps = deps
        self._stop_requested = False
        self._ws_started = False
        self._entry = EntryProcessor(deps)
        self._exit = ExitProcessor(deps)
        # SPEC-TG-001 2026-06-02: health check tick sayacı (light interval × N).
        # MagicMock deps'lerde config attribute olmayabilir → güvenli default 60 tick.
        self._health_tick: int = 0
        # SPEC-Z9 2026-06-03: roster drift check timestamp (time-based 12h throttle)
        from datetime import datetime  # noqa: PLC0415 — type hint local
        self._drift_last_check_at: datetime | None = None
        try:
            cfg_alert = deps.state.config.telegram.alert
            light_sec = max(1, int(deps.state.config.cycle.light_interval_sec))
            self._health_check_every: int = max(
                1, int(cfg_alert.health_check_interval_sec) // light_sec,
            )
        except (AttributeError, TypeError, ValueError):
            self._health_check_every = 60  # default: 5dk @ 5sec light tick
        self._resilience = CycleResilience(
            max_consecutive=deps.state.config.agent.cycle_max_consecutive_errors
        )
        if self.deps.price_feed is not None:
            self.deps.price_feed.set_callback(self._on_price_update)
        # SPEC-TG-001 Task 5: graceful exit telegram alert (SIGKILL muaf).
        # atexit Python normal exit'te + Agent.request_stop sonrası çalışır.
        atexit.register(self._on_exit_alert)

    def _on_exit_alert(self) -> None:
        """Process exit'te telegram'a kritik bildirim — kullanıcı bot kapandığını anlar."""
        notifier = getattr(self.deps, "notifier", None)
        if notifier is not None:
            try:
                notifier.send("🔴 <b>Bot kapandı</b>\nProcess exit detected (graceful).")
            except Exception:  # noqa: BLE001 — atexit içinde exception bastırılır
                pass

    def request_stop(self) -> None:
        self._stop_requested = True
        if self.deps.price_feed is not None:
            self.deps.price_feed.stop()

    def request_pause(self) -> None:
        """Telegram /pause — yeni giriş açmayı durdur (kalıcı). Çıkışlar sürer."""
        self.deps.state.trading_control.pause()
        self.deps.state.trading_control_store.save(self.deps.state.trading_control.to_dict())
        logger.info("Trading PAUSED via Telegram")

    def request_resume(self) -> None:
        """Telegram /resume — yeni girişe devam (kalıcı)."""
        self.deps.state.trading_control.resume()
        self.deps.state.trading_control_store.save(self.deps.state.trading_control.to_dict())
        logger.info("Trading RESUMED via Telegram")

    def status_summary(self) -> str:
        """Telegram /status — kısa durum metni."""
        p = self.deps.state.portfolio
        paused = self.deps.state.trading_control.paused
        return (
            f"📊 <b>Durum</b>\n"
            f"Mod: {self.deps.state.config.mode.value}\n"
            f"Açık pozisyon: {p.count()}\n"
            f"Realized PnL: ${p.realized_pnl:.2f}\n"
            f"Bankroll: ${p.bankroll:.2f}\n"
            f"Trading: {'⏸ DURAKLATILDI' if paused else '▶ aktif'}"
        )

    def run(self, max_ticks: int | None = None) -> None:
        """Ana döngü. max_ticks=None → sonsuza kadar; test için sayılı tick."""
        self._start_ws_if_needed()
        self._start_command_poller()
        # SPEC-Z11 (2026-06-03): Initial equity snapshot — reload sonrası
        # dashboard widget'ları (Balance/Locked/Peak) HEMEN doğru değer göstersin.
        # Eski davranış: ilk equity tick sadece entry/exit anında yazılırdı; reload
        # sonrası yeni trade olmadan dashboard 25dk+ "$0" gösteriyordu. Bu satır
        # boot anında bir snapshot yazar → dashboard backend session/equity'i bulur.
        try:
            from src.orchestration import operational_writers  # noqa: PLC0415
            operational_writers.log_equity_snapshot(
                self.deps.state.portfolio, self.deps.equity_logger,
            )
        except Exception as e:  # noqa: BLE001 — boot snapshot fail → log + devam
            logger.warning("Initial equity snapshot failed: %s", e)
        ticks = 0
        while not self._stop_requested:
            tick = self.deps.cycle_manager.tick(has_positions=self.deps.state.portfolio.count() > 0)
            self.deps.cooldown.new_cycle()

            try:
                if tick.run_heavy:
                    self._entry.run_heavy()
                    # SPEC-M: Heavy sonrasi en yakin maca kadar saatleri hesapla,
                    # cycle_manager bir sonraki interval'i bu bilgiyle secsin.
                    nearest = self._compute_nearest_match_hours()
                    self.deps.cycle_manager.update_nearest_match_hours(nearest)
                if tick.run_light:
                    # Tennis pozisyonlarinin match_start_iso'sunu ESPN ile refresh et
                    # (TTL-cached, exit kararlari guncel match start ile alinsin).
                    if self.deps.tennis_start_enricher is not None:
                        self.deps.tennis_start_enricher.refresh_positions(
                            list(self.deps.state.portfolio.positions.values()),
                        )
                    score_map: dict[str, dict] = {}
                    if self.deps.score_enricher is not None:
                        try:
                            # SPEC-Z5: ESPN'den match_live/match_ended bayraklarini tum
                            # sporlar icin tazele (eskiden sadece tenis icin vardi).
                            # Polymarket event.live gecikiyor olabilir; ESPN canli kaynak.
                            self.deps.score_enricher.refresh_match_status(
                                self.deps.state.portfolio.positions,
                            )
                            score_map = self.deps.score_enricher.get_scores_if_due(
                                self.deps.state.portfolio.positions,
                            )
                        except Exception as e:
                            logger.warning(
                                "Score enrichment failed: %s — using empty score_map", e,
                            )
                            score_map = {}
                    self._exit.run_light(score_map=score_map)
                    # SPEC-TG-001 2026-06-02: periyodik health check (her N light tick).
                    # check_all + dedupe + send — exception isolated, light cycle bozulmasin.
                    if self.deps.health_monitor is not None:
                        self._health_tick += 1
                        if self._health_tick % self._health_check_every == 0:
                            try:
                                alerts = self.deps.health_monitor.check_all()
                                if alerts:
                                    self.deps.health_monitor.send_alerts(alerts)
                            except Exception as e:
                                logger.warning("HealthMonitor check failed: %s", e)
                            # SPEC-Z9 2026-06-03: aynı tetiklemede roster drift de
                            # kontrol et (günlük cadence). HealthMonitor ile aynı
                            # dedupe pattern — DriftAlert → HealthMonitor.Alert
                            # adapter (severity/category/message uyumlu).
                            self._maybe_check_roster_drift()
                self._resilience.record_success()
            except Exception as e:
                logger.error("Cycle error (%s): %s", tick.reason, e, exc_info=True)
                self._resilience.record_error(e)
                if self._resilience.should_stop():
                    logger.critical(
                        "STOPPING: %d ardışık programatik hata (%s) — bot durduruldu",
                        self._resilience.consecutive_count, type(e).__name__,
                    )
                    self._stop_requested = True

            persist(self.deps.state)
            self.deps.bot_status_writer.write_from_tick(
                mode=self.deps.state.config.mode.value, tick=tick
            )

            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            time.sleep(self.deps.cycle_manager.sleep_seconds())

    def _maybe_check_roster_drift(self) -> None:
        """SPEC-Z9 (2026-06-03): günde 1 Polymarket /teams + /sports diff.

        Time-based throttle — health tick rate'inden bağımsız. İlk health
        check'te bir kere çalışır, sonra her 12h'de 1. DriftAlert → HealthMonitor
        Alert adapter (severity/category/message birebir uyumlu).
        Exception isolated — drift check fail → light cycle bozulmaz.
        """
        if self.deps.roster_drift_monitor is None:
            return
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        if self._drift_last_check_at is not None:
            if now - self._drift_last_check_at < timedelta(hours=12):
                return
        self._drift_last_check_at = now
        try:
            drift_alerts = self.deps.roster_drift_monitor.check_all()
        except Exception as e:
            logger.warning("RosterDriftMonitor check failed: %s", e)
            return
        if not drift_alerts or self.deps.health_monitor is None:
            return
        # DriftAlert → HealthMonitor.Alert adapter
        from src.orchestration.health_monitor import Alert as HMAlert
        adapted = [
            HMAlert(severity=d.severity, category=d.category, message=d.message)
            for d in drift_alerts
        ]
        try:
            self.deps.health_monitor.send_alerts(adapted)
        except Exception as e:
            logger.warning("RosterDrift send_alerts failed: %s", e)

    def _compute_nearest_match_hours(self) -> float | None:
        """SPEC-M: Acik pozisyon + stock'taki market'lerden en yakin maca saatleri.

        Kaynaklar: portfolio.positions + stock.entries (her ikisinde match_start_iso var).
        Sadece gelecek (positive hours) macleri sayar. Hiç maç yoksa None.

        Caller (cycle_manager) None gorunce default heavy/night davranisi uygular.
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        candidates: list[str] = []
        # Acik pozisyonlar
        for pos in self.deps.state.portfolio.positions.values():
            iso = (pos.match_start_iso or "").strip()
            if iso:
                candidates.append(iso)
        # Stock'taki market'ler
        try:
            for entry in self.deps.stock.all_entries():
                iso = (entry.market.match_start_iso or "").strip()
                if iso:
                    candidates.append(iso)
        except (AttributeError, TypeError):
            pass  # stock erisilebilir degilse atla (cold start, test mock)

        min_hours: float | None = None
        for iso in candidates:
            try:
                dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            hours = (dt - now).total_seconds() / 3600.0
            if hours <= 0:
                continue  # gecmis veya bashlamis mac
            if min_hours is None or hours < min_hours:
                min_hours = hours
        return min_hours

    def _start_ws_if_needed(self) -> None:
        if self._ws_started or self.deps.price_feed is None:
            return
        tokens = [p.token_id for p in self.deps.state.portfolio.positions.values() if p.token_id]
        if tokens:
            self.deps.price_feed.subscribe(tokens)
        self.deps.price_feed.start_background()
        self._ws_started = True

    def _start_command_poller(self) -> None:
        if self.deps.command_poller is None:
            return
        self.deps.command_poller.start()

    def _on_price_update(self, token_id: str, yes_price: float, bid_price: float, _ts: float) -> None:
        try:
            self.deps.state.portfolio.update_position_price(token_id, yes_price, bid_price)
        except Exception as e:
            logger.error("WS price update error: %s", e)
