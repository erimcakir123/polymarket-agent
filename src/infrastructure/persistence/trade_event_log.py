"""SPEC-Z17 (2026-06-04): append-only trade event log.

Tek dosya tüm bot aksiyonlarını kronolojik sırayla taşır. Sadece append.
Rewrite/update API YOK — atomic rewrite bug'larından tamamen kaçınır.

Eski Z15.B/E shrink-guard, Z15.D orphan_metadata, Z16 merger gibi yamalar
artık gereksiz: tek kaynak, tek yazma yolu, replay ile reconstruction.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TradeEventLog:
    """Append-only event log.

    Event türleri:
      - "entry":   pozisyon açıldı (slug, question, sport_tag, source,
                   direction, entry_price, entry_timestamp, size_usdc,
                   shares, confidence, bookmaker_prob, anchor_probability,
                   num_bookmakers, has_sharp, entry_reason)
      - "partial": kısmi satış (tier, sell_pct, realized_pnl_usdc,
                   timestamp, price)
      - "final":   tam kapanış (exit_price, exit_reason, exit_pnl_usdc,
                   exit_timestamp)

    Tüm append çağrıları slug + question + sport_tag + source meta'sını
    da yazar — replay sırasında orphan path'e gerek kalmadan etiketler dolu.

    SPEC-Z18 (2026-06-05): session aynası kaldırıldı. audit=session ayrımı
    reboot=tam-wipe kararıyla (2026-05-23) anlamsızlaştı; iki kopya ayrışıp
    (audit=4 vs session=113) karmaşaya yol açıyordu. Tek dosya = divergence
    imkânsız.
    """

    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False) + "\n"
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
        except OSError as e:
            logger.error("TradeEventLog write failed: %s", e)

    def append_entry(
        self, *, condition_id: str, slug: str, question: str,
        sport_tag: str, source: str, direction: str,
        entry_price: float, entry_timestamp: str,
        size_usdc: float, shares: float, confidence: str,
        bookmaker_prob: float, anchor_probability: float,
        num_bookmakers: float, has_sharp: bool, entry_reason: str,
    ) -> None:
        self._write({
            "kind": "entry", "condition_id": condition_id,
            "slug": slug, "question": question,
            "sport_tag": sport_tag, "source": source,
            "direction": direction,
            "entry_price": entry_price, "entry_timestamp": entry_timestamp,
            "size_usdc": size_usdc, "shares": shares,
            "confidence": confidence,
            "bookmaker_prob": bookmaker_prob,
            "anchor_probability": anchor_probability,
            "num_bookmakers": num_bookmakers, "has_sharp": has_sharp,
            "entry_reason": entry_reason,
        })

    def append_partial(
        self, *, condition_id: str, slug: str, question: str,
        sport_tag: str, source: str, tier: int, sell_pct: float,
        realized_pnl_usdc: float, timestamp: str, price: float,
    ) -> None:
        self._write({
            "kind": "partial", "condition_id": condition_id,
            "slug": slug, "question": question,
            "sport_tag": sport_tag, "source": source,
            "tier": tier, "sell_pct": sell_pct,
            "realized_pnl_usdc": realized_pnl_usdc,
            "timestamp": timestamp, "price": price,
        })

    def append_final(
        self, *, condition_id: str, slug: str, question: str,
        sport_tag: str, source: str, exit_price: float,
        exit_reason: str, exit_pnl_usdc: float, exit_timestamp: str,
    ) -> None:
        self._write({
            "kind": "final", "condition_id": condition_id,
            "slug": slug, "question": question,
            "sport_tag": sport_tag, "source": source,
            "exit_price": exit_price, "exit_reason": exit_reason,
            "exit_pnl_usdc": exit_pnl_usdc,
            "exit_timestamp": exit_timestamp,
        })

    def read_events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        corrupt = 0
        for ln in self.path.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                corrupt += 1
        if corrupt:
            logger.warning(
                "TradeEventLog: %d corrupt line dropped on read", corrupt,
            )
        return out
