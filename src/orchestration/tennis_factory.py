"""Tennis lab sandbox composition root.

Builds tennis-specific dependencies (config, ratings, predictor) wired with main bot infra.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §11.2 (shared modules)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import AppConfig, load_config
from src.infrastructure.data.sackmann_csv_client import SackmannCsvClient
from src.infrastructure.data.tennis_ratings_store import TennisRatingsStore
from src.orchestration.tennis_diagnostic_logger import TennisDiagnosticLogger

logger = logging.getLogger(__name__)


@dataclass
class TennisDeps:
    """Tennis sandbox dependencies — composition root output."""

    config: AppConfig
    ratings_store: TennisRatingsStore
    sackmann_client: SackmannCsvClient
    diagnostic_logger: TennisDiagnosticLogger


def build_tennis_deps(config_path: Path) -> TennisDeps:
    """Build all tennis sandbox dependencies from config file.

    Args:
        config_path: Path to YAML config (e.g. config_tennis.yaml).

    Returns:
        TennisDeps with all components wired and ready.
    """
    cfg = load_config(config_path)

    sackmann_client = SackmannCsvClient(cache_dir=Path(cfg.tennis.data_dir))
    ratings_store = TennisRatingsStore(path=Path(cfg.tennis.ratings_cache))
    diagnostic_logger = TennisDiagnosticLogger(
        log_dir=Path(cfg.tennis.diagnostic_log_dir),
    )

    logger.info(
        "Tennis deps built: mode=%s bankroll=$%.2f dashboard=:%d",
        cfg.mode.value,
        cfg.initial_bankroll,
        cfg.dashboard.port,
    )
    return TennisDeps(
        config=cfg,
        ratings_store=ratings_store,
        sackmann_client=sackmann_client,
        diagnostic_logger=diagnostic_logger,
    )
