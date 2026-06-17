"""Trading kontrol durumu — /pause ile yeni giriş durdurma. Saf domain, I/O yok."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TradingControl:
    """Yeni giriş açma izni. paused=True iken EntryProcessor yeni trade açmaz.
    Çıkışlar (ExitProcessor) bu bayraktan etkilenmez."""
    paused: bool = False

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def to_dict(self) -> dict:
        return {"paused": self.paused}

    @classmethod
    def from_dict(cls, data: dict) -> "TradingControl":
        return cls(paused=bool(data.get("paused", False)))
