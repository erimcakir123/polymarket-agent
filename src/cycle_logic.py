from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class CycleHelpers:
    """Cycle helper methods extracted from Agent."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def log_cycle_summary(self, bankroll: float, status: str) -> None:
        invested = sum(p.size_usdc for p in self.ctx.portfolio.positions.values())
        unrealized = self.ctx.portfolio.total_unrealized_pnl()
        # Equity = initial + realized + unrealized (always correct, no tracking drift)
        equity = self.ctx.portfolio._initial_bankroll + self.ctx.portfolio.realized_pnl + unrealized
        self.ctx.portfolio_log.log({
            "bankroll": self.ctx.portfolio.bankroll,
            "positions": len(self.ctx.portfolio.positions),
            "invested": round(invested, 2),
            "unrealized_pnl": unrealized,
            "realized_pnl": self.ctx.portfolio.realized_pnl,
            "realized_wins": self.ctx.portfolio.realized_wins,
            "realized_losses": self.ctx.portfolio.realized_losses,
            "hwm": self.ctx.portfolio.high_water_mark,
            "initial_bankroll": self.ctx.portfolio._initial_bankroll,
            "equity": round(equity, 2),
            "status": status,
        })
        self.log_performance()

    def write_status(self, state: str, step: str, **kwargs) -> None:
        """Write bot status to logs/bot_status.json for dashboard consumption."""
        from datetime import datetime, timezone
        status = {
            "state": state,
            "step": step,
            "ts": datetime.now(timezone.utc).isoformat(),
            "has_positions": self.ctx.portfolio.active_position_count > 0,
            **kwargs,
        }
        try:
            status_path = Path("logs/bot_status.json")
            status_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = status_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(status), encoding="utf-8")
            tmp.replace(status_path)
        except Exception as e:
            logger.debug("Status file write error: %s", e)

    def log_performance(self) -> None:
        """Write performance stats to performance.jsonl for the dashboard."""
        cal = Path("logs/calibration.jsonl")
        if not cal.exists():
            return
        try:
            lines = [json.loads(l) for l in cal.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
        except Exception:
            return
        if not lines:
            return
        wins = sum(1 for l in lines if l.get("ai_correct", False))
        losses = sum(1 for l in lines if not l.get("ai_correct", False))
        total = wins + losses
        if total == 0:
            return
        brier_pairs = []
        for l in lines:
            prob = l.get("anchor_probability", l.get("ai_probability", 0.5))
            outcome = 1 if l.get("resolved_yes", False) else 0
            brier_pairs.append((prob - outcome) ** 2)
        brier = sum(brier_pairs) / len(brier_pairs) if brier_pairs else 0.5
        cat_wins: dict[str, int] = {}
        cat_total: dict[str, int] = {}
        for l in lines:
            q = l.get("question", "")
            slug = l.get("condition_id", "")
            cat = l.get("category", "")
            if not cat:
                cat_match = re.search(r"\b(NBA|NHL|CBB|NFL|MLB|CS2|CS:GO|LoL|EPL|UCL|UEL|Dota|Valorant)\b", q, re.IGNORECASE)
                cat = cat_match.group(1).upper() if cat_match else "Other"
            cat_total[cat] = cat_total.get(cat, 0) + 1
            if l.get("ai_correct", False):
                cat_wins[cat] = cat_wins.get(cat, 0) + 1
        best_cat = max(cat_total, key=lambda c: (cat_wins.get(c, 0) / cat_total[c], cat_total[c])) if cat_total else None
        self.ctx.perf_log.log({
            "win_rate": round(wins / total, 4),
            "wins": wins,
            "losses": losses,
            "resolved": total,
            "brier_score": round(brier, 4),
            "best_category": best_cat,
            "best_category_rate": round(cat_wins.get(best_cat, 0) / cat_total.get(best_cat, 1), 4) if best_cat else None,
        })

