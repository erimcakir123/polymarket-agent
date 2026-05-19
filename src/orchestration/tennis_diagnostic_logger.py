"""Tennis diagnostic logger — per-trade feature snapshot persistence.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §8
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from src.domain.prediction.feature_extractor import FeatureSnapshot
from src.domain.prediction.tennis_predictor import MarketPrediction

logger = logging.getLogger(__name__)


class TennisDiagnosticLogger:
    """Append-only JSONL log of tennis predictions + outcomes.

    File rotation: per day (logs/tennis_diagnostics/YYYY-MM-DD.jsonl).
    Outcomes appended as separate records (with same trade_id).
    """

    def __init__(self, log_dir: Path) -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def _current_file(self) -> Path:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self._log_dir / f"{today}.jsonl"

    def log_prediction(
        self,
        trade_id: str,
        tournament: str,
        tournament_tier: str,
        slug: str,
        format_: str,
        match_start_iso: str,
        market_polymarket_price: float,
        direction: str,
        prediction: MarketPrediction,
        features: FeatureSnapshot,
        confidence_tier: str,
        edge: float,
    ) -> None:
        record = {
            "trade_id": trade_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "match": {
                "slug": slug,
                "tournament": tournament,
                "tournament_tier": tournament_tier,
                "surface": features.surface,
                "format": format_,
                "match_start_iso": match_start_iso,
            },
            "market": {
                "type": prediction.market_type,
                "polymarket_price": market_polymarket_price,
                "direction": direction,
            },
            "prediction": {
                "model_prob": prediction.probability,
                "raw_prob": prediction.raw_probability,
                "edge": edge,
                "confidence_tier": confidence_tier,
                "notes": prediction.notes,
            },
            "features": asdict(features),
            "outcome": None,
            "exit_price": None,
            "realized_pnl_usdc": None,
        }
        with open(self._current_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def update_outcome(
        self,
        trade_id: str,
        outcome: str,
        exit_price: float,
        realized_pnl: float,
    ) -> None:
        """Append outcome update (same trade_id, partial record)."""
        record = {
            "trade_id": trade_id,
            "outcome_update_timestamp": datetime.utcnow().isoformat() + "Z",
            "outcome": outcome,
            "exit_price": exit_price,
            "realized_pnl_usdc": realized_pnl,
        }
        with open(self._current_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
