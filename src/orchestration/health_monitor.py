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

    def __init__(
        self,
        notifier,
        state_dir: Path = Path("data"),
        audit_dir: Path = Path("logs/audit"),
        runtime_dir: Path = Path("logs/runtime"),
        stale_price_threshold: int = 5,
        exposure_lockup_minutes: int = 60,
        consecutive_losses: int = 5,
        dedupe_window_minutes: int = 30,
        calibration_stale_days: int = 7,
        scraper_stale_hours: int = 24,
        muted_alert_categories=None,
        odds_client=None,
        odds_low_credit_threshold: int = 50,
        surface_resolver=None,
        now_fn=lambda: datetime.now(timezone.utc),
    ) -> None:
        self.notifier = notifier
        self.odds_client = odds_client
        self.odds_low_credit_threshold = odds_low_credit_threshold
        self.surface_resolver = surface_resolver
        self.state_dir = state_dir
        self.audit_dir = audit_dir
        self.runtime_dir = runtime_dir
        self.stale_price_threshold = stale_price_threshold
        self.exposure_lockup_minutes = exposure_lockup_minutes
        self.consecutive_losses_threshold = consecutive_losses
        self.dedupe_window = dedupe_window_minutes
        self.calibration_stale_days = calibration_stale_days
        self.scraper_stale_hours = scraper_stale_hours
        # SPEC-Z10 (2026-06-03): kategori-bazli alert mute (config'den)
        self.muted_alert_categories: set[str] = set(muted_alert_categories or [])
        self._now = now_fn
        self._sent_alerts: dict[tuple[str, str], datetime] = {}

    # ── Public ──

    def check_all(self) -> list[Alert]:
        alerts: list[Alert] = []
        alerts.extend(self._check_stale_price_rate())
        alerts.extend(self._check_scraper_health())
        alerts.extend(self._check_consecutive_losses())
        alerts.extend(self._check_calibration_age())
        alerts.extend(self._check_odds_quota())
        alerts.extend(self._check_surface_unknown())
        return alerts

    def send_alerts(self, alerts: list[Alert]) -> None:
        """Throttle/dedupe + kategori mute ile telegram'a gönder."""
        if self.notifier is None:
            return
        now = self._now()
        for alert in alerts:
            # SPEC-Z10 + PLAN-Z30 g6: kategori muted ise sessizce skip (telegram
            # spam onleme). Prefix wildcard (SCRAPER_*) veya tam eslesme.
            if self._is_muted(alert.category):
                continue
            key = (alert.severity, alert.category)
            last = self._sent_alerts.get(key)
            if last is not None and (now - last).total_seconds() < self.dedupe_window * 60:
                continue
            emoji = self._SEVERITY_EMOJI.get(alert.severity, "")
            msg = f"{emoji} <b>{alert.category}</b>\n{alert.message}"
            self.notifier.send(msg)
            self._sent_alerts[key] = now

    def _is_muted(self, category: str) -> bool:
        """Muted kontrol: 'PREFIX_*' wildcard veya tam kategori eslesmesi."""
        for pat in self.muted_alert_categories:
            if pat.endswith("*"):
                if category.startswith(pat[:-1]):
                    return True
            elif category == pat:
                return True
        return False

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
        """HealthTracker JSON array → broken/stale state derive + alert.

        Mevcut HealthTracker (3-strike fallback) ile uyumlu okuma:
        - active=False (3+ ardışık fail) → critical "broken"
        - active=True + last_success_utc > scraper_stale_hours eski → warning "stale"
        - else → healthy (alert yok)

        SPEC-EUROBASKET-001 entegrasyon noktası: yeni scraper'lar mevcut
        HealthTracker.record_success/record_failure API'sini kullanır.
        """
        health_path = self.state_dir / "basketball_cache" / "_health" / "sources_status.json"
        if not health_path.exists():
            return []
        try:
            data = json.loads(health_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("health check scraper health JSON parse fail: %s", e)
            return []
        if not isinstance(data, list):
            return []
        now = self._now()
        alerts: list[Alert] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            source = str(row.get("source", "")).strip()
            if not source:
                continue
            active = bool(row.get("active", True))
            last_success = str(row.get("last_success_utc") or "")
            last_fail = str(row.get("last_fail_utc") or "")
            if not active:
                alerts.append(Alert(
                    severity="critical",
                    category=f"SCRAPER_DOWN_{source}",
                    message=(
                        f"Veri kaynağı '{source}' devre dışı (3+ ardışık fail). "
                        f"Son fail: {last_fail or 'yok'}. "
                        f"Bu kaynağa bağlı lig için trade YAPILMIYOR."
                    ),
                ))
                continue
            if last_success and self._is_stale(last_success, now):
                alerts.append(Alert(
                    severity="warning",
                    category=f"SCRAPER_STALE_{source}",
                    message=(
                        f"Veri kaynağı '{source}' eski "
                        f"(> {self.scraper_stale_hours}h yenilenmedi). "
                        f"Son success: {last_success}. Cache ile devam ediyor."
                    ),
                ))
        return alerts

    def _is_stale(self, last_success_iso: str, now: datetime) -> bool:
        try:
            ts = datetime.fromisoformat(last_success_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return False
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (now - ts).total_seconds() > self.scraper_stale_hours * 3600

    def _check_consecutive_losses(self) -> list[Alert]:
        """trade_events.jsonl son N exit'in hepsi zarar → warning.

        SPEC-Z17 (2026-06-04): kaynak event log; sadece kind="final" event'ler
        gerçek tam kapanışı temsil eder (entry/partial atlanır).
        """
        events_path = self.audit_dir / "trade_events.jsonl"
        if not events_path.exists():
            return []
        try:
            lines = events_path.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            logger.warning("health check trade_events read fail: %s", e)
            return []
        exits: list[float] = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("kind") != "final":
                continue  # entry/partial event'leri sayma
            pnl = d.get("exit_pnl_usdc")
            if pnl is None or pnl == 0.0:
                continue
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
        """tennis_calibration.json > calibration_stale_days gün eski → info."""
        calib = self.state_dir / "tennis_calibration.json"
        if not calib.exists():
            return []
        age_days = (self._now().timestamp() - calib.stat().st_mtime) / 86400
        if age_days > self.calibration_stale_days:
            return [Alert(
                severity="info",
                category="CALIBRATION_AGE",
                message=(
                    f"Tennis calibration {age_days:.0f} gün eski "
                    f"(eşik: {self.calibration_stale_days} gün). Refresh önerilir."
                ),
            )]
        return []

    def _check_odds_quota(self) -> list[Alert]:
        """Odds API kalan kredi düşük/bitti → telegram alert (2026-06-09).

        Bahisçi-fiyatlı marketler (asıl kazanan leg) Odds API kredisine bağlı.
        Kredi bitince enrich 401 döner → bu marketler trade EDİLEMEZ. Bitmeden
        haber ver ki yeni anahtar alınabilsin. odds_client henüz çağrı yapmadıysa
        remaining=None → sessiz (alert yok). Dedupe send_alerts'te (30dk).
        """
        if self.odds_client is None:
            return []
        remaining = getattr(self.odds_client, "remaining", None)
        if remaining is None:
            return []
        if remaining <= 0:
            return [Alert(
                severity="critical",
                category="ODDS_QUOTA_EXHAUSTED",
                message=(
                    "Odds API kotası BİTTİ (kalan 0). Bahisçi-fiyatlı marketler "
                    "(WNBA totals vb.) trade EDİLEMİYOR. Yeni Odds API anahtarı gerekli."
                ),
            )]
        if remaining < self.odds_low_credit_threshold:
            return [Alert(
                severity="warning",
                category="ODDS_QUOTA_LOW",
                message=(
                    f"Odds API kredisi azaldı (kalan {remaining}, eşik "
                    f"{self.odds_low_credit_threshold}). Yakında yeni anahtar gerekecek."
                ),
            )]
        return []

    def _check_surface_unknown(self) -> list[Alert]:
        """Tenis turnuva zemini hiçbir kaynaktan çözülemedi → warning.

        PLAN-Z30 g6: kullanıcı eline alıp Google AI ile çözüp override ekler.
        Dedupe send_alerts'te (kategori+severity, 30dk) — tekrar spam yok.
        """
        r = self.surface_resolver
        if r is None or not getattr(r, "unresolved", None):
            return []
        return [Alert("warning", "SURFACE_UNKNOWN",
                      f"Zemin bilinmiyor: {n} — Google AI ile elle çöz/ekle")
                for n in sorted(r.unresolved)]

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
