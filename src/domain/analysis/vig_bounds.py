"""Vig sanity bounds for bookmaker probability normalization.

Pre-normalize total of 1/odds across outcomes:
- 2-way (h2h, spreads, totals): typical 1.02-1.08, outlier reject [0.85, 1.20]
- 3-way (soccer h2h): typical 1.05-1.10, outlier reject [0.85, 1.30]
"""
from __future__ import annotations

VIG_2WAY_MIN: float = 0.85
VIG_2WAY_MAX: float = 1.20
VIG_3WAY_MIN: float = 0.85
VIG_3WAY_MAX: float = 1.30
