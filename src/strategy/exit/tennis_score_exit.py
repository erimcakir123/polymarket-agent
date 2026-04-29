"""Tennis score exit — set-bazlı sabit tablo (Phase 1 v1, BO3 only).

Spec: docs/superpowers/specs/2026-04-29-tennis-magnus-live-system-design.md §6
DECISIONS.md tennis section.

Bu dosya monitor.py'nin tennis dispatch noktası için thin wrapper.
Karar mantığı: `_tennis_exit_dispatch.decide_tennis_exit` (pure, test-edilebilir).

Phase roadmap:
- v1 (current): set-bazlı tablo + bid/price tabanlı override'lar
- v2 (Phase 2):  Bayesian p_serve update, BO5 desteği
- v3 (Phase 3):  Momentum EWMA + risk-adjusted EV
"""
from __future__ import annotations

from typing import Any

from src.models.enums import ExitReason
from src.strategy.exit._tennis_exit_dispatch import (
    TennisExitConfig,
    TennisExitSignal,
    check_tennis_exit,
)


_DEFAULT_CFG = TennisExitConfig()


class _CheckResult:
    """Lightweight result for monitor.py consumption.

    Carries `reason`, `detail`, `partial`, `sell_pct` — same shape as NHLSignal
    so monitor.py can build ExitSignal uniformly across sports.
    """

    def __init__(
        self,
        reason: ExitReason,
        detail: str,
        partial: bool,
        sell_pct: float,
    ) -> None:
        self.reason = reason
        self.detail = detail
        self.partial = partial
        self.sell_pct = sell_pct


def check(
    *,
    score_info: dict,
    current_price: float,
    sport_tag: str,
    entry_price: float = 0.0,
    direction: str = "BUY_YES",
    cfg: TennisExitConfig | None = None,
    **_: Any,  # tolerate extra legacy kwargs from monitor
) -> _CheckResult | None:
    """Tennis exit check — backward-compatible wrapper for monitor.py.

    Returns None → HOLD; otherwise a result with reason/detail/partial/sell_pct.

    Note: monitor.py currently passes (score_info, current_price, sport_tag).
    For full functionality (entry/direction/structural-damage), monitor must
    also pass entry_price + direction. Defaults keep backward compat.
    """
    if not score_info.get("available"):
        return None

    cfg = cfg if cfg is not None else _DEFAULT_CFG

    # Build a minimal Position-like adapter so we can reuse check_tennis_exit
    # without forcing monitor.py to construct a full Position. We accept
    # entry_price and direction here as keyword args — monitor.py wiring will
    # supply pos.entry_price + pos.direction.
    class _PosLike:
        def __init__(self) -> None:
            self.entry_price = float(entry_price)
            self.bid_price = float(current_price)
            self.current_price = float(current_price)
            self.direction = direction

    signal: TennisExitSignal | None = check_tennis_exit(
        pos=_PosLike(),  # type: ignore[arg-type]
        score_info=score_info,
        cfg=cfg,
    )
    if signal is None:
        return None
    return _CheckResult(
        reason=signal.reason,
        detail=signal.detail,
        partial=signal.partial,
        sell_pct=signal.sell_pct,
    )
