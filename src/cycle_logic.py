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

    def maybe_run_reflection(self) -> None:
        """Every 3 days, analyze calibration results and generate lessons."""
        lessons_path = Path("logs/ai_lessons.md")
        cal_path = Path("logs/calibration.jsonl")

        marker_path = Path("logs/.last_reflection")
        if marker_path.exists():
            try:
                last = datetime.fromisoformat(marker_path.read_text().strip())
                if (datetime.now(timezone.utc) - last).days < 3:
                    return
            except (ValueError, OSError):
                pass

        if not cal_path.exists():
            return

        try:
            lines = [l for l in cal_path.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
        except Exception:
            return
        if len(lines) < 5:
            return

        results = []
        for line in lines[-20:]:
            try:
                r = json.loads(line)
                results.append(
                    f"- Q: {r.get('question', '')[:80]} | "
                    f"Anchor: {r.get('anchor_probability', r.get('ai_probability', 0)):.0%} | "
                    f"Result: {'YES' if r.get('resolved_yes') else 'NO'} | "
                    f"{'CORRECT' if r.get('ai_correct') else 'WRONG'} | "
                    f"Error: {r.get('prediction_error', 0):.0%} | "
                    f"Category: {r.get('category', 'unknown')}"
                )
            except (json.JSONDecodeError, KeyError):
                continue

        if not results:
            return

        correct = 0
        for l in lines:
            try:
                correct += 1 if json.loads(l).get("ai_correct") else 0
            except (json.JSONDecodeError, AttributeError):
                pass
        total = len(lines)
        accuracy = correct / total if total > 0 else 0

        reflection_prompt = (
            f"You are reviewing your past prediction performance.\n"
            f"Overall accuracy: {correct}/{total} ({accuracy:.0%})\n\n"
            f"Recent results:\n" + "\n".join(results) + "\n\n"
            f"Analyze your mistakes. Write 3-5 SHORT, SPECIFIC rules for yourself. "
            f"Focus on: What reasoning patterns led to wrong predictions? "
            f"What should you do differently? Which categories are you weak in?\n"
            f"Keep it under 400 characters total. Be brutally honest."
        )

        try:
            if self.ctx.ai.budget_remaining_usd < 0.05:
                return

            result = self.ctx.ai._call_claude(
                "You are a prediction analyst reviewing your own performance. "
                "Output ONLY plain text rules, no JSON.",
                reflection_prompt,
                parse_json=False,
            )
            if not result or not isinstance(result, str):
                return
            lessons_text = result

            lessons_path.write_text(
                f"# AI Self-Reflection (updated {datetime.now(timezone.utc).strftime('%Y-%m-%d')})\n"
                f"Accuracy: {correct}/{total} ({accuracy:.0%})\n\n"
                f"{lessons_text}\n",
                encoding="utf-8",
            )
            marker_path.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
            logger.info("Self-reflection complete: %d/%d correct (%.0f%%)", correct, total, accuracy * 100)
        except Exception as e:
            logger.debug("Reflection failed: %s", e)
