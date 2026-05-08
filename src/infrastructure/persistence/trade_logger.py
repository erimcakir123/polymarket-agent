"""Zengin trade case-study logger — her maç trade'i tek kayıt (JSONL).

Kayıt bir maç trade'inin TÜM yaşam döngüsünü tutar:
  - Entry: kaçtan girdik, branş, lig, confidence, bookmaker prob, kaç bookmaker
  - match_timeline: maç ilerlerken skor/fiyat snapshot'ları (Faz 4+)
  - Exit: çıkış fiyatı, sebep, PnL
  - Resolution: biz çıktıktan sonra maç sonucu (Faz 5+)

Testlerde ve karar analizinde referans olarak kullanılır.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict

from src.infrastructure.persistence.jsonl_tail import read_jsonl_tail

logger = logging.getLogger(__name__)

_BYTES_PER_LINE = 1000  # Zengin kayıt (match_timeline dahil) → büyük tahmin


def _split_sport_tag(sport_tag: str) -> tuple[str, str]:
    """'basketball_nba' → ('basketball', 'nba'). 'tennis_atp_french_open' → ('tennis', 'atp_french_open').
    Boş → ('', ''). Underscore yoksa → (tag, '').
    """
    tag = (sport_tag or "").strip()
    if not tag:
        return "", ""
    if "_" not in tag:
        return tag, ""
    category, rest = tag.split("_", 1)
    return category, rest


class TradeRecord(BaseModel):
    """Bir maç trade'inin tam yaşam döngüsü kaydı."""
    model_config = ConfigDict(extra="ignore")

    # ── Market kimliği ──
    slug: str
    condition_id: str
    event_id: str
    token_id: str
    question: str = ""
    match_title: str = ""  # SPEC-015 3-way display başlığı; 2-way/draw için boş

    # ── Branş & lig ──
    sport_tag: str
    sport_category: str
    league: str

    # ── Giriş ──
    direction: str
    entry_price: float
    size_usdc: float
    shares: float
    confidence: str
    bookmaker_prob: float
    anchor_probability: float
    num_bookmakers: float = 0.0
    has_sharp: bool = False
    entry_reason: str
    entry_timestamp: str

    # ── Maç ilerleyişi (Faz 4+'te doldurulur) ──
    match_timeline: list[dict] = []

    # ── Çıkış ──
    exit_price: float | None = None
    exit_reason: str = ""
    exit_pnl_usdc: float = 0.0
    exit_pnl_pct: float = 0.0
    exit_timestamp: str = ""

    # ── Scale-out partial exit'ler (her tier için bir kayıt) ──
    partial_exits: list[dict] = []

    # ── Resolution (Faz 5+'te doldurulur) ──
    final_outcome: str = "unresolved"
    we_were_right: bool | None = None
    resolution_timestamp: str = ""
    resolution_source: str = ""


class TradeHistoryLogger:
    """Append-only JSONL: her satır = bir TradeRecord.

    mirror_path verilirse her write/rewrite işlemi session/ aynasına da uygulanır.
    """

    _CORRUPT_THRESHOLD = 3  # 3+ bozuk satır → reconcile'a abort sinyal (SPEC-A3)

    def __init__(self, file_path: str, mirror_path: str | None = None) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.mirror: Path | None = None
        if mirror_path:
            self.mirror = Path(mirror_path)
            self.mirror.parent.mkdir(parents=True, exist_ok=True)
        # Corrupt-row tracking — read_all'da güncellenir, reconcile bunu okur (SPEC-A3).
        self.corrupt_lines = 0
        self.corrupt_threshold_exceeded = False

    def _write_line(self, line: str) -> None:
        """audit + mirror (varsa) dosyasına satır ekler."""
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
        if self.mirror is not None:
            with open(self.mirror, "a", encoding="utf-8") as f:
                f.write(line)

    def log(self, record: TradeRecord) -> None:
        self._write_line(record.model_dump_json() + "\n")

    def read_recent(self, n: int = 50) -> list[dict[str, Any]]:
        return read_jsonl_tail(self.path, n, _BYTES_PER_LINE)

    def read_all(self) -> list[dict[str, Any]]:
        """Tüm jsonl satırlarını oku. Bozuk satırları sayar; threshold geçerse flag set."""
        self.corrupt_lines = 0
        self.corrupt_threshold_exceeded = False
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for l in self.path.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                self.corrupt_lines += 1
                if self.corrupt_lines == 1:
                    logger.warning("trade_history.jsonl corrupt line detected (count=1)")
        if self.corrupt_lines >= self._CORRUPT_THRESHOLD:
            self.corrupt_threshold_exceeded = True
            logger.error(
                "trade_history.jsonl: %d corrupt lines (>=%d) — reconcile will abort",
                self.corrupt_lines, self._CORRUPT_THRESHOLD,
            )
        return out

    def _rewrite_matching(self, condition_id: str, mutator: Callable[[dict[str, Any]], None]) -> bool:
        """En son açık (exit_price=None) kaydı bul, mutator(rec) çağır, atomic rewrite et.

        Atomic = tmp dosyaya yaz + replace. Crash-safe.
        Mirror varsa aynı içerikle mirror da rewrite edilir.
        Return: matching record bulundu mu.
        """
        records = self.read_all()
        updated = False
        for rec in reversed(records):
            if rec.get("condition_id") == condition_id and rec.get("exit_price") is None:
                mutator(rec)
                updated = True
                break
        if not updated:
            return False
        serialized = [json.dumps(rec) + "\n" for rec in records]
        # Audit atomic rewrite
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(serialized)
        tmp.replace(self.path)
        # Mirror atomic rewrite (varsa)
        if self.mirror is not None:
            mirror_tmp = self.mirror.with_suffix(self.mirror.suffix + ".tmp")
            with open(mirror_tmp, "w", encoding="utf-8") as f:
                f.writelines(serialized)
            mirror_tmp.replace(self.mirror)
        return True

    def update_on_exit(self, condition_id: str, exit_data: dict[str, Any]) -> bool:
        """condition_id için en son açık (exit_price=None) kaydı exit verisiyle günceller.
        Atomic rewrite. Return: güncellendi mi?
        """
        return self._rewrite_matching(condition_id, lambda rec: rec.update(exit_data))

    def log_partial_exit(self, condition_id: str, tier: int, sell_pct: float,
                         realized_pnl_usdc: float, timestamp: str,
                         price: float) -> bool:
        """En son açık trade kaydının partial_exits listesine bir partial ekle.
        Atomic rewrite. Return: kayıt bulundu mu.
        """
        entry: dict[str, Any] = {
            "tier": tier,
            "sell_pct": sell_pct,
            "realized_pnl_usdc": realized_pnl_usdc,
            "timestamp": timestamp,
            "price": price,
        }

        def append_partial(rec: dict[str, Any]) -> None:
            existing = rec.get("partial_exits") or []
            existing.append(entry)
            rec["partial_exits"] = existing

        return self._rewrite_matching(condition_id, append_partial)
