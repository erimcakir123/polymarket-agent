"""LAB v2: Bagimsiz bot launcher (port 5051).

Lab ana botla AYNI kodu calistirir — tek fark config.yaml ayarlari.
Sport ratings (Glicko surface + basketball cache) factory.py icinde otomatik
yuklenir; lab tarafinda monkey-patch YOK.

Calistirma:
  python lab_v2/start.py [--mode paper]

Silme: rm -rf lab_v2/  → her sey gider, main bot etkilenmez.
"""
from __future__ import annotations

import logging
import os
import shutil
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


# Lab'da olmasi gereken ama lab data'da uretilmeyen, ana bot data'sindan
# senkronize edilen referans dosyalar. Model-level snapshots — state DEGIL.
# 2026-06-02 SPEC-AUDIT-001 Task 3: sabit liste + glob pattern — yeni rating
# dosyalari (Avrupa basket scraper'lari, yeni tenis modelleri, vs.) otomatik
# dahil edilir, manuel listeye eklemek gerekmez.
_SYNC_FILES_FIXED: tuple[str, ...] = (
    # Kalibrasyon egrileri (proje-cap)
    "data/tennis_calibration.json",
    # Sackmann tenis ratings (3MB, lig-cap)
    "data/tennis_ratings.json",
    "data/tennis_ratings_surface.json",
)
_SYNC_GLOBS: tuple[str, ...] = (
    # Basketball ratings — yeni ligler otomatik dahil (nba, wnba, g_league,
    # summer_league + sonra eklenecek Avrupa ligleri liga_acb, turkey_bsl, vs.)
    "data/basketball_cache/*_ratings.json",
)


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


def _sync_reference_data() -> None:
    """Ana bot data'sindan referans dosyalari lab'a kopyala (yoksa veya eskise).

    Why: lab calibration/surface ratings olmadan ham model uretiyor → ana bot
    ile farkli bookmaker_prob veriyor. Senkron tutarak iki bot ayni input
    uretir, A/B testin temizligi korunur.
    """
    log = logging.getLogger(__name__)
    lab_root = LAB_ROOT
    lab_root.mkdir(exist_ok=True)
    # 1. Sabit liste — bilinen tek dosyalar
    for rel in _SYNC_FILES_FIXED:
        _sync_one(MAIN_REPO / rel, lab_root / rel, log)
    # 2. Glob pattern — yeni rating dosyalari otomatik dahil
    for pattern in _SYNC_GLOBS:
        for src in MAIN_REPO.glob(pattern):
            dst = lab_root / src.relative_to(MAIN_REPO)
            _sync_one(src, dst, log)


def _sync_one(src: Path, dst: Path, log) -> None:
    """Tek dosya sync — yoksa kopya, eskise yenile."""
    if not src.exists():
        log.warning("[LAB] sync skip: %s (main yok)", src.name)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
        log.info("[LAB] synced: %s (%d bytes)", src.name, dst.stat().st_size)


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

    # Referans data'yi ana bottan senkronize et (calibration, surface ratings)
    _sync_reference_data()

    # Launch dashboard first (so it's up before bot generates state)
    _start_dashboard_subprocess(port=5051)

    # Now boot main bot with lab config
    from src.config.settings import Mode, load_config
    from src.orchestration.factory import build_agent
    from src.orchestration.process_lock import acquire_lock
    from src.orchestration.startup import bootstrap

    cfg = load_config(Path("config.yaml"))  # → lab_v2/config.yaml (cwd)
    # Process lock under lab_v2/data/
    Path("data").mkdir(exist_ok=True)
    # SPEC-Z8 (2026-06-03): process_marker zorunlu — lab "src.main" değil
    # "lab_v2.start" ile çalışıyor; default marker stale detection bozar.
    acquire_lock(lock_path=Path("data/lab_v2.lock"), process_marker="lab_v2.start")
    # Dashboard "bot_alive" göstergesi logs/agent.pid'i okur — ayrıca yaz
    Path("logs").mkdir(exist_ok=True)
    Path("logs/agent.pid").write_text(str(os.getpid()), encoding="utf-8")
    state = bootstrap(cfg)
    agent = build_agent(state)
    log.info("[LAB] agent starting: mode=%s dashboard=http://127.0.0.1:%d",
             cfg.mode.value, cfg.dashboard.port)
    agent.run()


if __name__ == "__main__":
    main()
