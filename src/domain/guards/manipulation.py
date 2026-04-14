"""Manipulation tespiti — self-resolving + düşük likidite.

TDD §6.16. Pure: dışarıdan question/description/liquidity alır.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Kendi market sonuçlarını etkileyebilecek kişi/kurumlar
SELF_RESOLVING_SUBJECTS: frozenset[str] = frozenset({
    "trump", "biden", "elon", "musk", "putin", "zelensky", "xi jinping",
    "desantis", "vance", "newsom", "harris", "netanyahu", "modi",
    "zuckerberg", "bezos", "altman",
})

# "Will X say/tweet/announce..." gibi self-resolving patterns
_SELF_RESOLVING_VERBS = re.compile(
    r"\b(say|tweet|post|announce|sign|veto|pardon|fire|hire|appoint|endorse|"
    r"resign|visit|meet with|call|respond|comment|declare)\b",
    re.IGNORECASE,
)


@dataclass
class ManipulationCheck:
    safe: bool
    risk_level: str           # "low" | "medium" | "high"
    flags: list[str]
    recommendation: str

    def __str__(self) -> str:
        if self.safe:
            return f"SAFE ({self.risk_level})"
        return f"RISKY ({self.risk_level}): {', '.join(self.flags)}"


def _is_self_resolving(question: str, description: str = "") -> bool:
    """Subject + verb birlikte → self-resolving."""
    text = (question + " " + description).lower()
    for subject in SELF_RESOLVING_SUBJECTS:
        if subject in text and _SELF_RESOLVING_VERBS.search(text):
            return True
    return False


def check_market(
    question: str,
    description: str = "",
    liquidity: float = 0.0,
    min_liquidity_usd: float = 10_000.0,
) -> ManipulationCheck:
    """Manipulation kontrollerini çalıştır. Risk skoru → level."""
    flags: list[str] = []
    risk_score = 0

    # 1. Self-resolving
    if _is_self_resolving(question, description):
        flags.append("SELF_RESOLVING: subject can influence outcome")
        risk_score += 3

    # 2. Düşük likidite
    if liquidity < min_liquidity_usd:
        flags.append(f"LOW_LIQUIDITY: ${liquidity:,.0f} (min ${min_liquidity_usd:,.0f})")
        risk_score += 2 if liquidity <= 0 else 1

    if risk_score >= 3:
        return ManipulationCheck(safe=False, risk_level="high", flags=flags,
                                 recommendation="SKIP: high manipulation risk")
    if risk_score >= 2:
        return ManipulationCheck(safe=True, risk_level="medium", flags=flags,
                                 recommendation="CAUTION: reduce position size by 50%")
    return ManipulationCheck(safe=True, risk_level="low", flags=flags,
                             recommendation="OK: no significant manipulation signals")


def adjust_position_size(size_usdc: float, check: ManipulationCheck) -> float:
    """Risk seviyesine göre pozisyon boyutunu ayarla (high → 0, medium → ×0.5)."""
    if check.risk_level == "high":
        return 0.0
    if check.risk_level == "medium":
        return size_usdc * 0.5
    return size_usdc
