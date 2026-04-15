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
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.infrastructure.persistence.jsonl_tail import read_jsonl_tail

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
    """Append-only JSONL: her satır = bir TradeRecord."""

    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: TradeRecord) -> None:
        line = record.model_dump_json() + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_recent(self, n: int = 50) -> list[dict[str, Any]]:
        return read_jsonl_tail(self.path, n, _BYTES_PER_LINE)

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for l in self.path.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        return out

    def _rewrite_matching(self, condition_id: str, mutator) -> bool:
        """En son açık (exit_price=None) kaydı bul, mutator(rec) çağır, atomic rewrite et.

        Atomic = tmp dosyaya yaz + replace. Crash-safe.
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
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")
        tmp.replace(self.path)
        return True

    def update_on_exit(self, condition_id: str, exit_data: dict[str, Any]) -> bool:
        """condition_id için en son açık (exit_price=None) kaydı exit verisiyle günceller.
        Atomic rewrite. Return: güncellendi mi?
        """
        return self._rewrite_matching(condition_id, lambda rec: rec.update(exit_data))
