"""Self-improving performance tracking with auto-tuning recommendations."""
from __future__ import annotations
import logging
from collections import defaultdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PerformanceTracker:
    def __init__(self) -> None:
        self._trades: List[dict] = []
        self._by_category: Dict[str, List[dict]] = defaultdict(list)

    def record_trade(
        self,
        category: str,
        won: bool,
        edge: float,
        ai_prob: Optional[float] = None,
        actual_resolved_yes: Optional[bool] = None,
    ) -> None:
        record = {
            "category": category, "won": won, "edge": edge,
            "ai_prob": ai_prob, "actual_resolved_yes": actual_resolved_yes,
        }
        self._trades.append(record)
        self._by_category[category].append(record)

    def win_rate(self, category: Optional[str] = None) -> float:
        trades = self._by_category.get(category, []) if category else self._trades
        if not trades:
            return 0.0
        return sum(1 for t in trades if t["won"]) / len(trades)

    def overall_win_rate(self) -> float:
        return self.win_rate(None)

    def brier_score(self) -> float:
        scored = [t for t in self._trades if t["ai_prob"] is not None and t["actual_resolved_yes"] is not None]
        if not scored:
            return 0.0
        total = sum(
            (t["ai_prob"] - (1.0 if t["actual_resolved_yes"] else 0.0)) ** 2
            for t in scored
        )
        return total / len(scored)

    def get_recommendations(
        self, min_win_rate: float = 0.50, min_trades: int = 10
    ) -> dict:
        exclude = []
        raise_edge = []
        for cat, trades in self._by_category.items():
            if len(trades) >= min_trades:
                wr = self.win_rate(cat)
                if wr < min_win_rate * 0.5:
                    exclude.append(cat)
                elif wr < min_win_rate:
                    raise_edge.append(cat)
        return {
            "exclude_categories": exclude,
            "raise_min_edge_categories": raise_edge,
            "overall_win_rate": self.overall_win_rate(),
            "brier_score": self.brier_score(),
            "total_trades": len(self._trades),
        }
