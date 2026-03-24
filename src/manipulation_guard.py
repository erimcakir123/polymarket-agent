"""Manipulation detection and protection filters.

Guards against:
1. Self-resolving markets (subject can influence outcome)
2. Low liquidity manipulation
3. Single-source news (fake news / planted stories)

Note: Whale trap protection backed up in manipulation_guard_backup_whale.py
Note: Price spike filter removed — AI probability analysis already handles this
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

# People/entities who can directly influence their own market outcomes
SELF_RESOLVING_SUBJECTS = [
    "trump", "biden", "elon", "musk", "putin", "zelensky", "xi jinping",
    "desantis", "vance", "newsom", "harris", "netanyahu", "modi",
    "zuckerberg", "bezos", "altman",
]

# Patterns that indicate self-resolving markets
# "Will X say/tweet/announce/sign/veto/pardon..."
SELF_RESOLVING_VERBS = re.compile(
    r"\b(say|tweet|post|announce|sign|veto|pardon|fire|hire|appoint|endorse|"
    r"resign|visit|meet with|call|respond|comment|declare)\b",
    re.IGNORECASE,
)


@dataclass
class ManipulationCheck:
    """Result of manipulation analysis."""
    safe: bool
    risk_level: str  # "low", "medium", "high"
    flags: List[str]
    recommendation: str

    def __str__(self) -> str:
        if self.safe:
            return f"SAFE ({self.risk_level})"
        return f"RISKY ({self.risk_level}): {', '.join(self.flags)}"


class ManipulationGuard:
    """Central manipulation detection engine."""

    def __init__(
        self,
        min_liquidity_usd: float = 10_000,
        min_news_sources: int = 2,
    ) -> None:
        self.min_liquidity_usd = min_liquidity_usd
        self.min_news_sources = min_news_sources

    def check_market(
        self,
        question: str,
        description: str = "",
        liquidity: float = 0,
        news_source_count: int = 0,
    ) -> ManipulationCheck:
        """Run all manipulation checks on a market."""
        flags: List[str] = []
        risk_score = 0

        # 1. Self-resolving market check
        if self._is_self_resolving(question, description):
            flags.append("SELF_RESOLVING: subject can influence outcome")
            risk_score += 3

        # 2. Low liquidity = easy to manipulate (zero is worst case)
        if liquidity < self.min_liquidity_usd:
            flags.append(f"LOW_LIQUIDITY: ${liquidity:,.0f} (min ${self.min_liquidity_usd:,.0f})")
            risk_score += 2 if liquidity <= 0 else 1

        # 3. Single-source or zero-source news
        if news_source_count < self.min_news_sources:
            flags.append(f"LOW_SOURCE_NEWS: only {news_source_count} source(s)")
            risk_score += 2 if news_source_count <= 0 else 1

        # Determine risk level
        if risk_score >= 3:
            risk_level = "high"
            safe = False
            recommendation = "SKIP: high manipulation risk"
        elif risk_score >= 2:
            risk_level = "medium"
            safe = True
            recommendation = "CAUTION: reduce position size by 50%"
        else:
            risk_level = "low"
            safe = True
            recommendation = "OK: no significant manipulation signals"

        result = ManipulationCheck(
            safe=safe, risk_level=risk_level,
            flags=flags, recommendation=recommendation,
        )

        if flags:
            logger.info("Manipulation check [%s]: %s — %s",
                        question[:50], result.risk_level, ", ".join(flags))

        return result

    def _is_self_resolving(self, question: str, description: str = "") -> bool:
        """Check if the market subject can directly influence the outcome."""
        text = (question + " " + description).lower()
        for subject in SELF_RESOLVING_SUBJECTS:
            if subject in text:
                if SELF_RESOLVING_VERBS.search(text):
                    return True
        return False

    def adjust_position_size(
        self,
        size_usdc: float,
        check: ManipulationCheck,
    ) -> float:
        """Reduce position size for risky markets."""
        if check.risk_level == "high":
            return 0.0
        if check.risk_level == "medium":
            return size_usdc * 0.5
        return size_usdc

    def count_unique_sources(self, articles: List[dict]) -> int:
        """Count unique news sources from article list."""
        sources = set()
        for a in articles:
            source = a.get("source", "")
            if ":" in source:
                source = source.split(":", 1)[1]
            if source:
                sources.add(source.lower())
        return len(sources)
