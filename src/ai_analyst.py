"""Dual-prompt Claude Sonnet probability estimation."""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict

import anthropic

from src.config import AIConfig
from src.models import MarketData
from src.api_usage import record_call

logger = logging.getLogger(__name__)

BUDGET_FILE = Path("logs/ai_budget.json")

_SLUG_GUIDE = """
READING THE SLUG:
The market slug contains encoded info. Decode it to understand the full context:
- "ucl" = UEFA Champions League, "uel" = Europa League, "epl" = Premier League
- Team abbreviations: "liv" = Liverpool, "gal" = Galatasaray, "bay" = Bayern, "bar" = Barcelona, etc.
- "cbb" = college basketball, "nba"/"nfl"/"nhl" = US sports leagues
- "cs2"/"csgo" = Counter-Strike 2, "val" = Valorant, "lol" = League of Legends
- Format is usually: league-team1-team2-date-outcome
If the question mentions one team, use the slug to identify the opponent and competition."""

_SPORTS_RULES = """
SPORTS-SPECIFIC RULES:
- You MUST use the match data provided (win rates, recent form, H2H) as your primary signal.
- Recent form (last 5 matches) matters more than all-time record.
- Head-to-head record is very important — some teams consistently beat others.
- Tournament tier matters: teams play harder in Majors/playoffs vs group stages.
- BO1 (best-of-1) is more volatile than BO3/BO5 — widen your confidence interval.
- If you have NO data about a team, set confidence to "C" — do NOT guess.
- Underdogs win ~20-30% of the time in esports BO1s. Don't overestimate favorites."""

_POLITICS_RULES = """
POLITICS/ELECTIONS/EVENTS RULES:
- Consider historical precedent, current conditions, stakeholder incentives.
- For events resolving within 7 days: focus on what's already in motion, not speculation.
- Be very conservative on long-shot political events — they almost never happen.
- Base rates matter more than narratives.
- ELECTIONS: Markets often overreact to last-minute news near election day.
  Voters rarely change their minds in the final week — polls 7 days out are highly predictive.
  Incumbent advantage is real (~55-60% win rate globally). Don't let dramatic headlines move your estimate.
  If you know the country's political landscape, USE that knowledge — it's your edge over emotional traders."""

UNIFIED_SYSTEM = """You are an expert superforecaster. Analyze BOTH sides of this market.

STEP 1 — Argue FOR: Why this outcome WILL happen. Cite concrete evidence.
STEP 2 — Argue AGAINST: Why this outcome will NOT happen. Be skeptical, find counterarguments.
STEP 3 — Synthesize: Weigh both sides and give your final probability estimate.

RULES:
- Base your estimate ONLY on the evidence provided (news, description, match data, time remaining).
- Do NOT anchor to any market price — form your OWN independent estimate.
- Be specific about your reasoning — cite concrete evidence, not vague intuitions.
- Account for time remaining until resolution. Use today's date to calculate how far away the event is.
{category_rules}
{slug_guide}

Respond with ONLY JSON:
{{"probability": 0.XX, "confidence": "C|B-|B+|A",
"reasoning_pro": "why YES...", "reasoning_con": "why NO...",
"key_evidence_for": [...], "key_evidence_against": [...]}}

Confidence grades:
- "A" = strong data, high conviction (multiple corroborating sources, clear edge)
- "B+" = good data, solid conviction (reasonable certainty with minor gaps)
- "B-" = decent data, moderate conviction (some uncertainty but reasonable estimate)
- "C" = weak/no data, low conviction (guessing, unreliable — will be skipped)"""


@dataclass
class AIEstimate:
    ai_probability: float
    confidence: str
    reasoning_pro: str
    reasoning_con: str


class AIAnalyst:
    def __init__(self, config: AIConfig) -> None:
        self.config = config
        self.client = anthropic.Anthropic()
        self._cache: Dict[str, tuple[AIEstimate, float, float]] = {}
        self._month_key: str = ""
        self._month_cost_usd: float = 0.0
        self._sprint_key: str = ""
        self._sprint_cost_usd: float = 0.0
        self._alerted_thresholds: set = set()
        self._last_api_call: float = 0.0  # Rate limit tracker
        self._load_budget()
        self._reset_if_new_period()

    def _load_budget(self) -> None:
        """Load persisted budget from disk with backup integrity check."""
        backup = BUDGET_FILE.with_suffix(".backup.json")
        for path in [BUDGET_FILE, backup]:
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text())
                self._month_key = data.get("month", "")
                self._month_cost_usd = data.get("spent", 0.0)
                self._sprint_key = data.get("sprint", "")
                self._sprint_cost_usd = data.get("sprint_spent", 0.0)
                return
            except (json.JSONDecodeError, KeyError, ValueError):
                logger.warning("Budget file corrupted: %s — trying backup", path)
        # Both files missing or corrupted — start fresh but log loudly
        logger.error("NO BUDGET FILE FOUND — starting with $0 spent. Check logs/ai_budget.json")

    def _save_budget(self) -> None:
        """Persist budget to disk with backup copy."""
        BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps({
            "month": self._month_key,
            "spent": float(f"{self._month_cost_usd:.6f}"),
            "limit": self.config.monthly_budget_usd,
            "remaining": float(f"{max(0.0, self.config.monthly_budget_usd - self._month_cost_usd):.6f}"),
            "sprint": self._sprint_key,
            "sprint_spent": float(f"{self._sprint_cost_usd:.6f}"),
            "sprint_limit": self.config.sprint_budget_usd,
            "sprint_remaining": float(f"{max(0.0, self.config.sprint_budget_usd - self._sprint_cost_usd):.6f}"),
        })
        # Write main + backup atomically
        tmp = BUDGET_FILE.with_suffix(".tmp")
        tmp.write_text(data)
        tmp.replace(BUDGET_FILE)
        backup = BUDGET_FILE.with_suffix(".backup.json")
        backup.write_text(data)

    def _reset_if_new_period(self) -> None:
        now = datetime.now(timezone.utc)
        month_key = now.strftime("%Y-%m")
        # Sprint = 2-week period: days 1-15 = sprint A, days 16-end = sprint B
        sprint_half = "A" if now.day <= 15 else "B"
        sprint_key = f"{month_key}-{sprint_half}"
        changed = False
        if month_key != self._month_key:
            self._month_key = month_key
            self._month_cost_usd = 0.0
            changed = True
        if sprint_key != self._sprint_key:
            self._sprint_key = sprint_key
            self._sprint_cost_usd = 0.0
            changed = True
        if changed:
            self._save_budget()

    @property
    def budget_remaining_usd(self) -> float:
        self._reset_if_new_period()
        monthly_left = max(0.0, self.config.monthly_budget_usd - self._month_cost_usd)
        sprint_left = max(0.0, self.config.sprint_budget_usd - self._sprint_cost_usd)
        return min(monthly_left, sprint_left)

    @property
    def budget_exhausted(self) -> bool:
        return self.budget_remaining_usd <= 0.0

    def _rate_limit(self) -> None:
        """Enforce minimum 1 second between API calls."""
        now = time.monotonic()
        elapsed = now - self._last_api_call
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._last_api_call = time.monotonic()

    def _track_cost(self, input_tokens: int, output_tokens: int) -> None:
        cost = (
            input_tokens * self.config.input_cost_per_mtok / 1_000_000
            + output_tokens * self.config.output_cost_per_mtok / 1_000_000
        )
        self._month_cost_usd += cost
        self._sprint_cost_usd += cost
        self._save_budget()
        record_call("claude")
        logger.info(
            "API cost: $%.4f | sprint: $%.2f/$%.2f | month: $%.2f/$%.2f",
            cost, self._sprint_cost_usd, self.config.sprint_budget_usd,
            self._month_cost_usd, self.config.monthly_budget_usd,
        )

    def check_budget_alerts(self) -> List[str]:
        """Return alert messages for budget thresholds (50%, 75%, 90%)."""
        alerts = []
        for threshold in [0.50, 0.75, 0.90]:
            pct = int(threshold * 100)
            # Check sprint budget
            if self.config.sprint_budget_usd > 0:
                sprint_used_pct = self._sprint_cost_usd / self.config.sprint_budget_usd
                key = f"sprint-{pct}"
                if sprint_used_pct >= threshold and key not in self._alerted_thresholds:
                    self._alerted_thresholds.add(key)
                    alerts.append(
                        f"⚠️ *Sprint bütçesi %{pct} doldu!*\n"
                        f"Harcanan: ${self._sprint_cost_usd:.2f} / ${self.config.sprint_budget_usd:.2f}\n"
                        f"Kalan: ${max(0, self.config.sprint_budget_usd - self._sprint_cost_usd):.2f}"
                    )
            # Check monthly budget
            if self.config.monthly_budget_usd > 0:
                month_used_pct = self._month_cost_usd / self.config.monthly_budget_usd
                key = f"month-{pct}"
                if month_used_pct >= threshold and key not in self._alerted_thresholds:
                    self._alerted_thresholds.add(key)
                    alerts.append(
                        f"⚠️ *Aylık bütçe %{pct} doldu!*\n"
                        f"Harcanan: ${self._month_cost_usd:.2f} / ${self.config.monthly_budget_usd:.2f}"
                    )
        return alerts

    def _is_sports_market(self, market: MarketData) -> bool:
        """Check if market is sports/esports based on tags and question."""
        sport_tags = {"sports", "soccer", "football", "basketball", "baseball",
                      "hockey", "tennis", "boxing", "mma", "cricket", "esports"}
        tags_lower = {t.lower() for t in market.tags}
        if sport_tags & tags_lower:
            return True
        sport_kw = {"vs", "vs.", "match", "game", "win", "score", "nba", "nfl",
                    "ncaa", "ufc", "counter-strike", "cs2", "valorant"}
        q_lower = market.question.lower()
        return any(kw in q_lower for kw in sport_kw)

    def _get_system_prompt(self, market: MarketData) -> str:
        """Return category-aware unified system prompt."""
        is_sports = self._is_sports_market(market)
        category_rules = _SPORTS_RULES if is_sports else _POLITICS_RULES
        return UNIFIED_SYSTEM.format(category_rules=category_rules, slug_guide=_SLUG_GUIDE)

    def analyze_market(
        self, market: MarketData, news_context: str = "",
        esports_context: str = "",
    ) -> AIEstimate:
        # Check cache
        cached = self._cache.get(market.condition_id)
        if cached:
            estimate, cached_time, cached_price = cached
            age_min = (time.monotonic() - cached_time) / 60
            price_move = abs(market.yes_price - cached_price)
            if age_min < self.config.cache_ttl_min and price_move < self.config.cache_invalidate_price_move_pct:
                return estimate

        if self.budget_exhausted:
            logger.warning("HARD STOP: Monthly API budget exhausted ($%.2f/$%.2f). Skipping analysis.",
                           self._month_cost_usd, self.config.monthly_budget_usd)
            return AIEstimate(ai_probability=0.5, confidence="C",
                              reasoning_pro="BUDGET_EXHAUSTED", reasoning_con="BUDGET_EXHAUSTED")

        # Pre-flight: estimate cost of 1 unified call and check remaining
        estimated_cost = (2000 * self.config.input_cost_per_mtok / 1_000_000
                          + self.config.max_tokens * self.config.output_cost_per_mtok / 1_000_000)
        if self.budget_remaining_usd < estimated_cost:
            logger.warning("HARD STOP: Budget too low for analysis ($%.4f remaining, ~$%.4f needed).",
                           self.budget_remaining_usd, estimated_cost)
            return AIEstimate(ai_probability=0.5, confidence="C",
                              reasoning_pro="BUDGET_EXHAUSTED", reasoning_con="BUDGET_EXHAUSTED")

        prompt = self._build_prompt(market, news_context, esports_context)

        # Single unified call (PRO + CON in one request)
        system_prompt = self._get_system_prompt(market)
        result = self._call_claude(system_prompt, prompt)

        if result is None:
            logger.warning("AI call failed — returning neutral 0.5 (no trade will trigger)")
            return AIEstimate(ai_probability=0.5, confidence="C",
                              reasoning_pro="API_ERROR", reasoning_con="API_ERROR")

        prob = result.get("probability", 0.5)
        prob = max(0.01, min(0.99, prob))
        confidence = result.get("confidence", "B-")
        # Normalize confidence to valid values
        if confidence not in ("C", "B-", "B+", "A"):
            confidence = "B-"

        estimate = AIEstimate(
            ai_probability=round(prob, 3),
            confidence=confidence,
            reasoning_pro=result.get("reasoning_pro", result.get("reasoning", "")),
            reasoning_con=result.get("reasoning_con", ""),
        )

        self._cache[market.condition_id] = (estimate, time.monotonic(), market.yes_price)
        return estimate

    def analyze_batch(
        self, markets: List[MarketData], news_context: str = "",
        esports_contexts: Optional[Dict[str, str]] = None,
        news_by_market: Optional[Dict[str, str]] = None,
    ) -> List[AIEstimate]:
        ctx = esports_contexts or {}
        news_map = news_by_market or {}
        return [
            self.analyze_market(
                m,
                news_map.get(m.condition_id, news_context),
                ctx.get(m.condition_id, ""),
            )
            for m in markets[:self.config.batch_size]
        ]

    def invalidate_cache(self, condition_id: str) -> None:
        self._cache.pop(condition_id, None)

    def _build_prompt(
        self, market: MarketData, news_context: str, esports_context: str = ""
    ) -> str:
        # Format today's date so AI knows when "now" is
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        parts = [
            f"Today's date: {today}",
            f"Question: {market.question}",
            f"Market slug: {market.slug}" if market.slug else "",
            f"Description: {market.description}" if market.description else "",
            # Market price intentionally excluded — prevents anchoring bias
            f"Resolution date: {market.end_date_iso}" if market.end_date_iso else "",
        ]
        # Esports/sports match data (from PandaScore)
        if esports_context:
            parts.append(f"\n{esports_context}")
        if news_context:
            parts.append(f"\nRecent news:\n{news_context}")
        # Include lessons from past mistakes (if any)
        lessons = self._load_lessons()
        if lessons:
            parts.append(f"\nLESSONS FROM YOUR PAST MISTAKES:\n{lessons}")
        return "\n".join(p for p in parts if p)

    def _load_lessons(self) -> str:
        """Load AI self-reflection lessons from past calibration analysis."""
        lessons_path = Path("logs/ai_lessons.md")
        if lessons_path.exists():
            try:
                content = lessons_path.read_text(encoding="utf-8").strip()
                # Cap at 500 chars to save tokens
                return content[:500] if content else ""
            except Exception:
                pass
        return ""

    def _call_claude(self, system: str, prompt: str, parse_json: bool = True):
        self._rate_limit()
        try:
            resp = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_cost(resp.usage.input_tokens, resp.usage.output_tokens)
            if not resp.content:
                logger.error("Claude returned empty content")
                return None
            text = resp.content[0].text.strip()
            if not parse_json:
                return text
            return self._parse_json_response(text)
        except Exception as e:
            logger.error("Claude API error: %s", e)
            return None

    @staticmethod
    def _parse_json_response(text: str) -> Optional[dict]:
        """Robustly extract JSON from Claude response."""
        # Try raw JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Strip markdown fences
        if "```" in text:
            # Handle ```json ... ``` or ``` ... ```
            parts = text.split("```")
            for part in parts[1::2]:  # odd-indexed parts are inside fences
                cleaned = part.strip()
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    continue
        # Try to find JSON object in text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        logger.error("Could not parse JSON from Claude response: %s", text[:200])
        return None
