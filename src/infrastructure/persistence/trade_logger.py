"""Trade record veri modeli + sport_tag ayrıştırıcı.

SPEC-Z17 (2026-06-04): TradeHistoryLogger sınıfı tamamen kaldırıldı (Bug A
kök nedeni: atomic rewrite'lar trade_history.jsonl'yi siliyordu). Tek truth
artık append-only TradeEventLog (logs/audit/trade_events.jsonl).

Bu dosyada kalan:
  - TradeRecord pydantic modeli — event log replay sonucunu temsil eder,
    entry/exit blocklarında tip imzası olarak kullanılır
  - _split_sport_tag yardımcısı — "basketball_nba" → ("basketball", "nba")
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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
    # K4 (2026-05-31): "bookmaker" veya "model" — model çıktısı bookmaker_prob
    # alanını paylaştığı için dashboard/audit'te ayırt etmek gerek.
    source: str = "bookmaker"
    entry_reason: str = ""
    entry_timestamp: str = ""

    # ── Maç ilerleyişi (event replay sonucunda dolar) ──
    match_timeline: list[dict] = []

    # ── Çıkış ──
    exit_price: float | None = None
    exit_reason: str = ""
    exit_pnl_usdc: float = 0.0
    exit_pnl_pct: float = 0.0
    exit_timestamp: str = ""

    # ── Scale-out partial exit'ler (her tier için bir kayıt) ──
    partial_exits: list[dict] = []

    # ── Resolution (event replay sonucunda doldurulur) ──
    final_outcome: str = "unresolved"
    we_were_right: bool | None = None
    resolution_timestamp: str = ""
    resolution_source: str = ""
