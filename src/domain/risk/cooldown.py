"""Ardışık kayıp → cooldown cycle sayacı (pure state).

CircuitBreaker zamana-bağlı (saatlik/günlük), bu modül cycle-bazlı kısa
cooldown: N ardışık kayıp → M cycle boyunca entry askıda.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CooldownState:
    consecutive_losses: int = 0
    cooldown_remaining: int = 0
    cooldown_decremented_this_cycle: bool = False


class CooldownTracker:
    def __init__(
        self,
        trigger_threshold: int = 3,
        cooldown_cycles: int = 2,
        state: CooldownState | None = None,
    ) -> None:
        self.trigger_threshold = trigger_threshold
        self.cooldown_cycles = cooldown_cycles
        self.state = state or CooldownState()

    def record_outcome(self, win: bool) -> None:
        if win:
            self.state.consecutive_losses = 0
            return
        self.state.consecutive_losses += 1
        if self.state.consecutive_losses >= self.trigger_threshold:
            self.state.cooldown_remaining = self.cooldown_cycles
            self.state.consecutive_losses = 0  # Çift cooldown önle

    def new_cycle(self) -> None:
        """Her cycle başında çağır — decrement guard'ını sıfırla."""
        self.state.cooldown_decremented_this_cycle = False

    def is_active(self) -> bool:
        """Cooldown aktif mi? Bu çağrı cycle başına bir kez decrement yapar."""
        if self.state.cooldown_remaining <= 0:
            return False
        if not self.state.cooldown_decremented_this_cycle:
            self.state.cooldown_remaining -= 1
            self.state.cooldown_decremented_this_cycle = True
        return self.state.cooldown_remaining > 0
