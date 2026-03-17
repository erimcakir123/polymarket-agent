"""Dual-prompt Claude Sonnet probability estimation."""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict

import anthropic

from src.config import AIConfig
from src.models import MarketData

logger = logging.getLogger(__name__)

PRO_SYSTEM = """You are an expert superforecaster arguing FOR this outcome.
Estimate the probability that this market resolves YES. Be thorough.
Start with base rate, update with evidence. Account for time remaining.
Respond with ONLY JSON: {"probability": 0.XX, "confidence": "low|medium|high",
"reasoning": "...", "key_evidence_for": [...], "key_evidence_against": [...]}"""

CON_SYSTEM = """You are an expert superforecaster arguing AGAINST this outcome.
Estimate the probability that this market resolves YES. Be thorough.
Focus on why it might NOT happen. Be skeptical.
Respond with ONLY JSON: {"probability": 0.XX, "confidence": "low|medium|high",
"reasoning": "...", "key_evidence_for": [...], "key_evidence_against": [...]}"""


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
        self._reset_if_new_month()

    def _reset_if_new_month(self) -> None:
        key = datetime.now(timezone.utc).strftime("%Y-%m")
        if key != self._month_key:
            self._month_key = key
            self._month_cost_usd = 0.0

    @property
    def budget_remaining_usd(self) -> float:
        self._reset_if_new_month()
        return max(0.0, self.config.monthly_budget_usd - self._month_cost_usd)

    @property
    def budget_exhausted(self) -> bool:
        return self.budget_remaining_usd <= 0.0

    def _track_cost(self, input_tokens: int, output_tokens: int) -> None:
        cost = (
            input_tokens * self.config.input_cost_per_mtok / 1_000_000
            + output_tokens * self.config.output_cost_per_mtok / 1_000_000
        )
        self._month_cost_usd += cost
        logger.info(
            "API cost: $%.4f | month total: $%.2f / $%.2f",
            cost, self._month_cost_usd, self.config.monthly_budget_usd,
        )

    def analyze_market(
        self, market: MarketData, news_context: str = ""
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
            logger.warning("Monthly API budget exhausted ($%.2f). Returning market price as estimate.",
                           self.config.monthly_budget_usd)
            return AIEstimate(ai_probability=market.yes_price, confidence="low",
                              reasoning_pro="Budget exhausted", reasoning_con="Budget exhausted")

        prompt = self._build_prompt(market, news_context)

        # Dual calls
        pro_result = self._call_claude(PRO_SYSTEM, prompt)
        con_result = self._call_claude(CON_SYSTEM, prompt)

        if pro_result is None or con_result is None:
            return AIEstimate(ai_probability=market.yes_price, confidence="low",
                              reasoning_pro="API error", reasoning_con="API error")

        # Weighted average (equal weight for now)
        avg_prob = (pro_result["probability"] + con_result["probability"]) / 2
        avg_prob = max(0.01, min(0.99, avg_prob))

        # Conservative confidence: take the lower one
        conf_order = {"low": 0, "medium": 1, "high": 2}
        pro_conf = conf_order.get(pro_result.get("confidence", "medium"), 1)
        con_conf = conf_order.get(con_result.get("confidence", "medium"), 1)
        conf_map = {0: "low", 1: "medium", 2: "high"}
        final_conf = conf_map[min(pro_conf, con_conf)]

        estimate = AIEstimate(
            ai_probability=round(avg_prob, 3),
            confidence=final_conf,
            reasoning_pro=pro_result.get("reasoning", ""),
            reasoning_con=con_result.get("reasoning", ""),
        )

        self._cache[market.condition_id] = (estimate, time.monotonic(), market.yes_price)
        return estimate

    def analyze_batch(
        self, markets: List[MarketData], news_context: str = ""
    ) -> List[AIEstimate]:
        return [self.analyze_market(m, news_context) for m in markets[:self.config.batch_size]]

    def invalidate_cache(self, condition_id: str) -> None:
        self._cache.pop(condition_id, None)

    def _build_prompt(self, market: MarketData, news_context: str) -> str:
        parts = [
            f"Question: {market.question}",
            f"Description: {market.description}" if market.description else "",
            f"Current YES price: ${market.yes_price:.2f}",
            f"Resolution date: {market.end_date_iso}" if market.end_date_iso else "",
        ]
        if news_context:
            parts.append(f"\nRecent news:\n{news_context}")
        return "\n".join(p for p in parts if p)

    def _call_claude(self, system: str, prompt: str) -> Optional[dict]:
        try:
            resp = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            self._track_cost(resp.usage.input_tokens, resp.usage.output_tokens)
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception as e:
            logger.error("Claude API error: %s", e)
            return None
