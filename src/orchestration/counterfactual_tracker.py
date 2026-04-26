"""Counterfactual tracker — exit sonrası fiyat izleme (Seçenek B: light cycle).

Exit gerçekleşince token_id kaydedilir. Her light cycle'da pending trace'ler
Gamma API'den bulk fetch ile güncellenir. 30 dk sonra tracking_complete=True,
sadece settlement beklenir. Match settle olunca final_settlement set edilir.

Reboot güvenliği: pending trace'ler logs/audit/counterfactual.jsonl'e yazılır.
Bot yeniden başlayınca dosyadaki incomplete trace'ler restore edilir ve devam eder.

ARCH: Orchestration katmanı. Domain'de I/O yasak — bu modül infra (Gamma) çağırır,
dolayısıyla orchestration'da doğru yerde.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TRACKING_WINDOW_SEC = 1800   # 30 dakika
_SETTLE_PRICE_THRESHOLD = 0.98  # Yaklaşık settlement (resolved)


class _TraceEntry:
    """Tek bir exit'in counterfactual iz kaydı."""

    __slots__ = (
        "trade_id", "token_id", "exit_timestamp", "exit_price",
        "exit_reason", "trace", "tracking_complete", "final_settlement",
    )

    def __init__(
        self,
        trade_id: str,
        token_id: str,
        exit_timestamp: str,
        exit_price: float,
        exit_reason: str,
    ) -> None:
        self.trade_id = trade_id
        self.token_id = token_id
        self.exit_timestamp = exit_timestamp
        self.exit_price = exit_price
        self.exit_reason = exit_reason
        self.trace: list[dict[str, Any]] = []
        self.tracking_complete = False
        self.final_settlement: float | None = None

    def elapsed_sec(self) -> float:
        try:
            t0 = datetime.fromisoformat(self.exit_timestamp)
            return (datetime.now(timezone.utc) - t0).total_seconds()
        except ValueError:
            return 0.0

    def to_dict(self) -> dict[str, Any]:
        cf_pnl: float | None = None
        if self.final_settlement is not None:
            cf_pnl = round((self.final_settlement - self.exit_price), 4)
        return {
            "trade_id": self.trade_id,
            "exit_timestamp": self.exit_timestamp,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "trace": self.trace,
            "final_settlement": self.final_settlement,
            "counterfactual_pnl": cf_pnl,
            "tracking_complete": self.tracking_complete,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "_TraceEntry":
        e = cls(
            trade_id=d["trade_id"],
            token_id=d.get("token_id", ""),
            exit_timestamp=d["exit_timestamp"],
            exit_price=d["exit_price"],
            exit_reason=d.get("exit_reason", ""),
        )
        e.trace = d.get("trace", [])
        e.tracking_complete = d.get("tracking_complete", False)
        e.final_settlement = d.get("final_settlement")
        return e


class CounterfactualTracker:
    """Exit sonrası fiyat izleyici.

    Kullanım:
      - exit_processor'dan: tracker.add(trade_id, token_id, exit_time, exit_price, reason)
      - light cycle'da: tracker.tick(gamma_client)
      - shutdown'da: tracker.flush() (atexit veya agent.stop)
    """

    def __init__(self, audit_dir: str | Path) -> None:
        self._dir = Path(audit_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._pending: dict[str, _TraceEntry] = {}  # trade_id → entry
        self._jsonl_path = self._dir / "counterfactual.jsonl"
        self._restore()

    # ── Public API ────────────────────────────────────────────────────────

    def add(
        self,
        trade_id: str,
        token_id: str,
        exit_timestamp: str,
        exit_price: float,
        exit_reason: str,
    ) -> None:
        """Exit anında çağrılır — trace başlatılır."""
        if trade_id in self._pending:
            return  # zaten takipte
        entry = _TraceEntry(
            trade_id=trade_id,
            token_id=token_id,
            exit_timestamp=exit_timestamp,
            exit_price=exit_price,
            exit_reason=exit_reason,
        )
        self._pending[trade_id] = entry
        logger.debug("CF_TRACK start: trade=%s token=%s", trade_id[:16], token_id[:16])

    def tick(self, gamma_client: Any) -> None:
        """Her light cycle'da çağrılır — pending trace'leri günceller.

        gamma_client: GammaClient veya GammaClient-compatible API.
        Bulk fetch: tüm pending token_id'leri tek istekte çeker.
        """
        if not self._pending:
            return
        token_ids = [e.token_id for e in self._pending.values() if not e.tracking_complete]
        if not token_ids:
            return

        try:
            prices = self._bulk_fetch(gamma_client, token_ids)
        except Exception as exc:
            logger.warning("CF_TRACK bulk fetch failed: %s", exc)
            return

        now_ts = datetime.now(timezone.utc).isoformat()
        completed: list[str] = []

        for trade_id, entry in self._pending.items():
            if entry.tracking_complete:
                continue
            price = prices.get(entry.token_id)
            if price is None:
                continue

            elapsed = entry.elapsed_sec()
            entry.trace.append({
                "t_offset_s": int(elapsed),
                "price": round(price, 4),
                "ts": now_ts,
            })

            if price >= _SETTLE_PRICE_THRESHOLD:
                entry.final_settlement = round(price, 4)
                entry.tracking_complete = True
                logger.info("CF_TRACK settled: trade=%s price=%.4f", trade_id[:16], price)
            elif price <= 0.02:
                entry.final_settlement = 0.0
                entry.tracking_complete = True
                logger.info("CF_TRACK resolved_no: trade=%s", trade_id[:16])
            elif elapsed >= _TRACKING_WINDOW_SEC:
                entry.tracking_complete = True
                logger.info("CF_TRACK window_closed: trade=%s elapsed=%ds", trade_id[:16], int(elapsed))

            if entry.tracking_complete:
                self._write_record(entry)
                completed.append(trade_id)

        for tid in completed:
            del self._pending[tid]

    def flush(self) -> None:
        """Shutdown veya reboot öncesi — tüm incomplete trace'leri diske yaz."""
        for entry in self._pending.values():
            self._write_pending(entry)
        logger.info("CF_TRACK flush: %d incomplete traces saved", len(self._pending))

    # ── Private ───────────────────────────────────────────────────────────

    def _bulk_fetch(self, gamma_client: Any, token_ids: list[str]) -> dict[str, float]:
        """token_id → current_price dict döner."""
        results: dict[str, float] = {}
        try:
            markets = gamma_client.get_markets_by_token_ids(token_ids)
        except AttributeError:
            # Fallback: get_market per token (eski API)
            for tid in token_ids:
                try:
                    m = gamma_client.get_market_by_token_id(tid)
                    if m and m.get("lastTradePrice") is not None:
                        results[tid] = float(m["lastTradePrice"])
                except Exception:
                    continue
            return results

        for m in (markets or []):
            tid = m.get("tokenId") or m.get("token_id", "")
            price = m.get("lastTradePrice") or m.get("yes_price")
            if tid and price is not None:
                results[tid] = float(price)
        return results

    def _write_record(self, entry: _TraceEntry) -> None:
        """Tamamlanan trace'i audit JSONL'e yaz."""
        try:
            with open(self._jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except OSError as e:
            logger.warning("CF_TRACK write failed: %s", e)

    def _write_pending(self, entry: _TraceEntry) -> None:
        """Incomplete trace'i serialize et (reboot safety).

        Tamam olmayan trace'ler de aynı dosyaya yazılır, tracking_complete=False
        ile ayrışır. _restore() sadece incomplete olanları pending'e alır.
        """
        try:
            d = entry.to_dict()
            d["token_id"] = entry.token_id  # restore için gerekli
            with open(self._jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(d) + "\n")
        except OSError as e:
            logger.warning("CF_TRACK pending write failed: %s", e)

    def _restore(self) -> None:
        """Startup'ta incomplete trace'leri restore et — reboot sonrası devam."""
        if not self._jsonl_path.exists():
            return
        seen: dict[str, _TraceEntry] = {}
        try:
            with open(self._jsonl_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        entry = _TraceEntry.from_dict(d)
                        seen[entry.trade_id] = entry  # last wins — en güncel state
                    except (json.JSONDecodeError, KeyError):
                        continue
        except OSError:
            return

        for entry in seen.values():
            if not entry.tracking_complete:
                elapsed = entry.elapsed_sec()
                if elapsed < _TRACKING_WINDOW_SEC:
                    self._pending[entry.trade_id] = entry
                    logger.debug(
                        "CF_TRACK restored: trade=%s elapsed=%ds",
                        entry.trade_id[:16], int(elapsed),
                    )

        if self._pending:
            logger.info("CF_TRACK restored %d incomplete traces", len(self._pending))
