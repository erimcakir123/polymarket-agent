"""PlayerSnapshot — Glicko rating + surface-spesifik serve stats container.

Domain saf veri yapısı. Hem pricer'lar hem infra ratings store kullanır.
Strategy katmanı buradan import eder (infra'yı geçer → layer kuralı).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats


@dataclass
class PlayerSnapshot:
    rating: Rating
    serve_by_surface: dict[str, PlayerServeStats]
