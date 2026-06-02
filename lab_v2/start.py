"""LAB v2: Bagimsiz bot launcher (port 5051).

Main bot UNTOUCHED. Tum override'lar import-time monkey-patch ile yapilir.

Calistirma:
  python lab_v2/start.py [--mode paper]

Silme: rm -rf lab_v2/  → her sey gider, main bot etkilenmez.
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 1. cwd'yi lab_v2'ye al → tum relative path'ler lab_v2/ altina cozulur
LAB_ROOT = Path(__file__).resolve().parent
MAIN_REPO = LAB_ROOT.parent
os.chdir(LAB_ROOT)

# 2. PYTHONPATH'e main repo + lab_v2 ekle
sys.path.insert(0, str(LAB_ROOT))
sys.path.insert(0, str(MAIN_REPO))

# 3. .env yukle (main repo'dan)
from dotenv import load_dotenv  # noqa: E402
load_dotenv(MAIN_REPO / ".env")


def _setup_logging() -> None:
    Path("logs/runtime").mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s [LAB] [%(levelname)s] %(name)s: %(message)s"
    file_h = RotatingFileHandler(
        "logs/runtime/bot.log", maxBytes=10 * 1024 * 1024,
        backupCount=5, encoding="utf-8",
    )
    file_h.setFormatter(logging.Formatter(fmt))
    con_h = logging.StreamHandler()
    con_h.setFormatter(logging.Formatter(fmt))
    logging.basicConfig(level=logging.INFO, handlers=[file_h, con_h])


def _apply_surface_glicko_patch() -> None:
    """Tennis dispatch'i surface-aware versiyonla degistir."""
    log = logging.getLogger(__name__)
    surface_path = LAB_ROOT / "data" / "tennis_ratings_surface.json"
    if not surface_path.exists():
        log.warning("[LAB] surface ratings missing — skipping tennis surface patch")
        return
    from lab_modules.surface_ratings_loader import load_all_surfaces
    from lab_modules.tennis_dispatch_surface import make_surface_aware_dispatch
    ratings_by_surface = load_all_surfaces(surface_path)
    log.info(
        "[LAB] loaded surface ratings: Hard=%d, Clay=%d, Grass=%d players",
        len(ratings_by_surface.get("Hard", {})),
        len(ratings_by_surface.get("Clay", {})),
        len(ratings_by_surface.get("Grass", {})),
    )
    new_dispatch = make_surface_aware_dispatch(ratings_by_surface)
    # Monkey-patch ana bot modulu (lab process icinde, main process etkilenmez)
    import src.strategy.enrichment.tennis_dispatch as td
    td.enrich_with_tennis_dispatch = new_dispatch
    import src.orchestration.factory as fact
    fact.enrich_with_tennis_dispatch = new_dispatch
    log.info("[LAB] tennis_dispatch monkey-patched (surface-aware)")


def _apply_rest_days_patch() -> None:
    """Basketball ratings yuklenince rest-day adjustment uygula."""
    log = logging.getLogger(__name__)
    schedule_path = LAB_ROOT / "data" / "basketball_schedule.json"
    from lab_modules.basketball_rest_days import adjust_ratings_now
    import src.orchestration.factory_basketball as fb
    original_loader = fb._load_basketball_caches

    def wrapped(cfg):
        ratings, eff = original_loader(cfg)
        adjusted = adjust_ratings_now(ratings, schedule_path)
        log.info(
            "[LAB] basketball rest-day adjustment applied (%d leagues)",
            len(adjusted),
        )
        return adjusted, eff

    fb._load_basketball_caches = wrapped
    log.info("[LAB] basketball rest-days monkey-patched")


def _start_dashboard_subprocess(port: int) -> None:
    """Launch dashboard as separate process (mirrors reboot.py pattern)."""
    import subprocess
    log = logging.getLogger(__name__)
    # cwd=LAB_ROOT so dashboard reads lab_v2/data/, logs/
    env = os.environ.copy()
    env["PYTHONPATH"] = str(MAIN_REPO) + os.pathsep + str(LAB_ROOT)
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.presentation.dashboard.app"],
        cwd=str(LAB_ROOT), env=env,
        stdout=open(str(LAB_ROOT / "logs" / "runtime" / "dashboard.log"), "ab"),
        stderr=subprocess.STDOUT,
    )
    log.info("[LAB] dashboard subprocess PID=%d → http://127.0.0.1:%d", proc.pid, port)


def main() -> None:
    _setup_logging()
    log = logging.getLogger(__name__)
    log.info("=" * 60)
    log.info("LAB v2 STARTING — port 5051, isolated data/logs")
    log.info("Main bot UNTOUCHED — delete lab_v2/ to remove without trace")
    log.info("=" * 60)

    # Launch dashboard first (so it's up before bot generates state)
    _start_dashboard_subprocess(port=5051)

    # Apply all lab patches BEFORE main bot init
    _apply_surface_glicko_patch()
    _apply_rest_days_patch()
    # Pinnacle filter: separate flag; default off (needs raw bookmaker stream)
    log.info("[LAB] pinnacle filter: PENDING (Odds API raw stream wiring needed)")

    # Now boot main bot with lab config
    from src.config.settings import Mode, load_config
    from src.orchestration.factory import build_agent
    from src.orchestration.process_lock import acquire_lock
    from src.orchestration.startup import bootstrap

    cfg = load_config(Path("config.yaml"))  # → lab_v2/config.yaml (cwd)
    # Process lock under lab_v2/data/
    Path("data").mkdir(exist_ok=True)
    acquire_lock(lock_path=Path("data/lab_v2.lock"))
    state = bootstrap(cfg)
    agent = build_agent(state)
    log.info("[LAB] agent starting: mode=%s dashboard=http://127.0.0.1:%d",
             cfg.mode.value, cfg.dashboard.port)
    agent.run()


if __name__ == "__main__":
    main()
