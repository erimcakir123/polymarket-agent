"""Cycle hata sınıflandırma + ardışık-aynı-tip-2-strike politikası.

Sebep: Programatik bug'lar (TypeError, AttributeError vb.) bot'un sessiz
çalışmaya devam etmesine neden oluyordu. Ağ hataları kabul edilir; programatik
hatalar 2 ardışık aynı tipten sonra bot'u durdurur.
"""
from __future__ import annotations

_PROGRAMMATIC_TYPES: tuple[type[BaseException], ...] = (
    TypeError, AttributeError, ValueError, KeyError, AssertionError,
)


def is_programmatic_error(e: BaseException) -> bool:
    """Programatik bug'lar bu sınıflara dahildir; geri kalan (ağ, IO) değil."""
    return isinstance(e, _PROGRAMMATIC_TYPES)


class CycleResilience:
    """Ardışık aynı-tip programatik hata sayacı.

    record_error(e): hata kayıt et.
    record_success(): sayacı sıfırla.
    should_stop(): max_consecutive eşiğine ulaşıldıysa True.
    """

    def __init__(self, max_consecutive: int = 2) -> None:
        self._max = max_consecutive
        self._last_type: type[BaseException] | None = None
        self._count = 0

    def record_error(self, e: BaseException) -> None:
        if not is_programmatic_error(e):
            return
        et = type(e)
        if et is self._last_type:
            self._count += 1
        else:
            self._last_type = et
            self._count = 1

    def record_success(self) -> None:
        self._last_type = None
        self._count = 0

    def should_stop(self) -> bool:
        return self._count >= self._max

    @property
    def consecutive_count(self) -> int:
        return self._count
