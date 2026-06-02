"""Periyodik health check + telegram alert (SPEC-TG-001 Task 4).

Sport-agnostic: tüm scraper'lar / sport_tag'ler için aynı pattern. Yeni
eklenecek scraper'lar (Avrupa basket SPEC-EUROBASKET-001) data_source_health
JSON'ına state yazar → bu monitor okur → broken/stale ise telegram critical
alert atar.

agent.py light cycle'da periyodik çağrılır. Throttle (dedupe window): aynı
alert N dk içinde tekrar atılmaz — spam engellenir.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Alert:
    """Tek alert kaydı. category dedupe key olarak kullanılır."""
    severity: str   # "critical" | "warning" | "info"
    category: str   # "STALE_PRICE_RATE" | "SCRAPER_DOWN_<source>" | ...
    message: str


class HealthMonitor:
    """Periyodik health check + telegram alert dedupe.

    Tek sorumluluk: ayrı check fonksiyonları, ortak send + dedupe akışı. Yeni
    health kategorisi eklemek için `_check_*` metod ekle + `check_all`'a dahil et.
    """

    _SEVERITY_EMOJI = {"critical": "🔴", "warning": "⚠️", "info": "🟢"}
    _STALE_PRICE_LOG_PATTERN = re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*STALE_PRICE_REJECT",
    )
    _CALIBRATION_STALE_DAYS = 7

    def __init__(
        self,
        notifier,
        state_dir: Path,
        audit_dir: Path,
        runtime_dir: Path,
        stale_price_threshold: int = 5,
        exposure_lockup_minutes: int = 60,
        consecutive_losses: int = 5,
        dedupe_window_minutes: int = 30,
        now_fn=lambda: datetime.now(timezone.utc),
    ) -> None:
        self.notifier = notifier
        self.state_dir = state_dir
        self.audit_dir = audit_dir
        self.runtime_dir = runtime_dir
        self.stale_price_threshold = stale_price_threshold
        self.exposure_lockup_minutes = exposure_lockup_minutes
        self.consecutive_losses_threshold = consecutive_losses
        self.dedupe_window = dedupe_window_minutes
        self._now = now_fn
        self._sent_alerts: dict[tuple[str, str], datetime] = {}

    # ── Public ──

    def check_all(self) -> list[Alert]:
        alerts: list[Alert] = []
        alerts.extend(self._check_stale_price_rate())
        alerts.extend(self._check_scraper_health())
        alerts.extend(self._check_consecutive_losses())
        alerts.extend(self._check_calibration_age())
        return alerts

    def send_alerts(self, alerts: list[Alert]) -> None:
        """Throttle/dedupe ile telegram'a gönder."""
        if self.notifier is None:
            return
        now = self._now()
        for alert in alerts:
            key = (alert.severity, alert.category)
            last = self._sent_alerts.get(key)
            if last is not None and (now - last).total_seconds() < self.dedupe_window * 60:
                continue
            emoji = self._SEVERITY_EMOJI.get(alert.severity, "")
            msg = f"{emoji} <b>{alert.category}</b>\n{alert.message}"
            self.notifier.send(msg)
            self._sent_alerts[key] = now

    # ── Check'ler ──

    def _check_stale_price_rate(self) -> list[Alert]:
        """Son 1 saatte STALE_PRICE_REJECT >= threshold → warning."""
        log_path = self.runtime_dir / "bot.log"
        if not log_path.exists():
            return []
        cutoff = self._now() - timedelta(hours=1)
        count = 0
        try:
            with log_path.open(encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = self._STALE_PRICE_LOG_PATTERN.search(line)
                    if not m:
                        continue
                    try:
                        ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S").replace(
                            tzinfo=timezone.utc,
                        )
                    except ValueError:
                        continue
                    if ts >= cutoff:
                        count += 1
        except OSError as e:
            logger.warning("health check stale_price log read fail: %s", e)
            return []
        if count >= self.stale_price_threshold:
            return [Alert(
                severity="warning",
                category="STALE_PRICE_RATE",
                message=(
                    f"Son 1 saatte {count} stale price reject "
                    f"(eşik: {self.stale_price_threshold}). Scanner ↔ orderbook drift büyük."
                ),
            )]
        return []

    def _check_scraper_health(self) -> list[Alert]:
        """data_source_health JSON broken state varsa critical."""
        # SPEC-EUROBASKET-001 entegrasyon noktası: tüm scraper'lar buraya yazar
        health_path = self.state_dir / "basketball_cache" / "_health" / "sources_status.json"
        if not health_path.exists():
            return []
        try:
            data = json.loads(health_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("health check scraper health JSON parse fail: %s", e)
            return []
        if not isinstance(data, dict):
            return []
        alerts: list[Alert] = []
        for source, status in data.items():
            if not isinstance(status, dict):
                continue
            state = status.get("state", "")
            if state == "broken":
                alerts.append(Alert(
                    severity="critical",
                    category=f"SCRAPER_DOWN_{source}",
                    message=(
                        f"Veri kaynağı '{source}' çalışmıyor. "
                        f"Son fail: {status.get('last_fail', '')}. "
                        f"Hata: {status.get('error', 'unknown')}. "
                        f"Bu lig için trade YAPILMIYOR."
                    ),
                ))
            elif state == "stale":
                alerts.append(Alert(
                    severity="warning",
                    category=f"SCRAPER_STALE_{source}",
                    message=(
                        f"Veri kaynağı '{source}' eski (24h+). "
                        f"Cache son güncelleme: {status.get('last_success', '')}. "
                        f"Trade ediyor ama veri yenilenmedi."
                    ),
                ))
        return alerts

    def _check_consecutive_losses(self) -> list[Alert]:
        """trade_history son N exit'in hepsi zarar → warning."""
        history = self.audit_dir / "trade_history.jsonl"
        if not history.exists():
            return []
        try:
            lines = history.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            logger.warning("health check trade_history read fail: %s", e)
            return []
        exits: list[float] = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            pnl = d.get("exit_pnl_usdc")
            if pnl is None or pnl == 0.0:
                continue  # entry kayıt veya orphan
            exits.append(float(pnl))
            if len(exits) >= self.consecutive_losses_threshold:
                break
        if (
            len(exits) >= self.consecutive_losses_threshold
            and all(p < 0 for p in exits)
        ):
            total_loss = sum(exits)
            return [Alert(
                severity="warning",
                category="CONSECUTIVE_LOSSES",
                message=(
                    f"Son {self.consecutive_losses_threshold} trade'in hepsi zarar. "
                    f"Toplam: ${total_loss:.2f}. Strateji review gerekebilir."
                ),
            )]
        return []

    def _check_calibration_age(self) -> list[Alert]:
        """tennis_calibration.json > _CALIBRATION_STALE_DAYS gün eski → info."""
        calib = self.state_dir / "tennis_calibration.json"
        if not calib.exists():
            return []
        age_days = (self._now().timestamp() - calib.stat().st_mtime) / 86400
        if age_days > self._CALIBRATION_STALE_DAYS:
            return [Alert(
                severity="info",
                category="CALIBRATION_AGE",
                message=(
                    f"Tennis calibration {age_days:.0f} gün eski "
                    f"(eşik: {self._CALIBRATION_STALE_DAYS} gün). Refresh önerilir."
                ),
            )]
        return []

    # ── Daily summary (atexit veya cron'dan çağrılır) ──

    def daily_summary(self, positions_path: Path) -> str:
        """Günlük özet metin (positions, realized, win rate, sport breakdown)."""
        if not positions_path.exists():
            return "Daily summary: state yok."
        try:
            data = json.loads(positions_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return "Daily summary: state parse fail."
        positions = data.get("positions", {})
        realized = data.get("realized_pnl", 0.0)
        n_open = len(positions)
        from collections import Counter
        sports = Counter(p.get("sport_tag", "?") for p in positions.values())
        sport_str = ", ".join(f"{s}:{n}" for s, n in sports.most_common())
        return (
            f"📊 <b>Günlük özet</b>\n"
            f"Realized PnL: ${realized:+.2f}\n"
            f"Açık pozisyon: {n_open}\n"
            f"Sport: {sport_str or '(yok)'}"
        )
