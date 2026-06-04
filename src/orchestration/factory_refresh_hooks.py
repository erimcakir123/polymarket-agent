"""Bot startup refresh hook'ları — factory.py'dan ayrı modül (ARCH_GUARD §3).

Tennis (Sackmann CSV) + Calibration eğrileri için startup refresh wrapper'ları.
Basketball refresh hook'ları factory_basketball.py'da.
"""
from __future__ import annotations

import logging
from pathlib import Path

from src.config.settings import AppConfig
from src.infrastructure.data.sackmann_refresher import (
    is_cache_stale,
    refresh_if_stale,
)

logger = logging.getLogger(__name__)


def maybe_refresh_sackmann_on_startup(cache_dir: Path) -> None:
    """Refresh Sackmann CSV + rebuild ratings if cache stale (tennis aktif iken).

    Synchronous; bot agent build_deps öncesi blocking çalışır. Stale değilse
    early return (1sn altı). İlk başlatma stale → ~1-2dk download + rebuild.
    Network fail → log WARNING, mevcut cache ile devam.
    """
    if not is_cache_stale(cache_dir):
        logger.info("Sackmann cache fresh — skipping startup refresh")
        return
    logger.info("Sackmann cache stale — refreshing before agent start")
    refreshed = refresh_if_stale(cache_dir)
    if not refreshed:
        logger.warning("Sackmann refresh attempted but no files downloaded")
        return
    logger.info("Rebuilding tennis_ratings.json from refreshed CSVs...")
    try:
        from scripts.build_tennis_ratings import main as rebuild_main  # noqa: PLC0415
        rebuild_main()
        logger.info("Startup Sackmann refresh + rebuild complete")
    except ImportError:
        logger.warning("scripts/build_tennis_ratings.py yok — sadece CSV refresh yapıldı")


def _maybe_invoke_sackmann_refresh(cfg: AppConfig) -> None:
    """Tennis aktif iken Sackmann refresh hook çağır (allowed_sport_tags'e bak)."""
    tags_lc = {t.lower() for t in (cfg.scanner.allowed_sport_tags or [])}
    if not ({"atp", "wta"} & tags_lc):
        return
    maybe_refresh_sackmann_on_startup(Path("data/sackmann_cache"))


def _maybe_invoke_calibration_refresh() -> None:
    """Plan 1.D Task 6: haftalık calibration eğrisi update hook.

    Stale değilse skip. Bot başlangıçta blocking değil — fit hızlı,
    save atomic, yarım dosya riski yok.
    """
    from src.orchestration.calibration_refresher import refresh_calibration_if_stale
    # SPEC-Z17 (2026-06-04): tek truth = event log; refresher dahili replay yapar.
    refresh_calibration_if_stale(
        calibration_path=Path("data/calibration_curves.json"),
        trades_path=Path("logs/audit/trade_events.jsonl"),
    )
