"""Lab auto-sync: yeni rating dosyalari glob pattern ile otomatik dahil edilir.

SPEC-AUDIT-001 Task 3: lab_v2/start.py'da sabit liste eksikliği yan task riskti —
yeni Avrupa basket scraper'lari (liga_acb_ratings.json, turkey_bsl_ratings.json,
vs.) eklenince manuel listeye eklemek gerekmesin.
"""
from __future__ import annotations

from pathlib import Path


def _setup_dirs(tmp_path: Path) -> tuple[Path, Path]:
    main = tmp_path / "main"
    lab = tmp_path / "lab"
    (main / "data" / "basketball_cache").mkdir(parents=True)
    (lab / "data" / "basketball_cache").mkdir(parents=True)
    return main, lab


# lab_v2/start.py import edilemez (modül-seviyesi os.chdir yan etkisi diğer
# testlerin cwd'sini bozar) — değerleri parse edip taklit ediyoruz.
def _read_sync_constants() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """lab_v2/start.py'dan _SYNC_FILES_FIXED ve _SYNC_GLOBS değerlerini parse et."""
    import ast
    src_text = (Path(__file__).parent.parent.parent / "lab_v2" / "start.py").read_text(encoding="utf-8")
    tree = ast.parse(src_text)
    fixed: tuple[str, ...] = ()
    globs: tuple[str, ...] = ()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "_SYNC_FILES_FIXED" and isinstance(node.value, ast.Tuple):
                        fixed = tuple(str(e.value) for e in node.value.elts if isinstance(e, ast.Constant))
                    elif target.id == "_SYNC_GLOBS" and isinstance(node.value, ast.Tuple):
                        globs = tuple(str(e.value) for e in node.value.elts if isinstance(e, ast.Constant))
    return fixed, globs


def _run_sync(main: Path, lab: Path) -> None:
    """lab_v2.start._sync_reference_data taklit (modül import etmeden)."""
    import shutil
    fixed, globs = _read_sync_constants()
    # 1. Sabit dosyalar
    for rel in fixed:
        src = main / rel
        dst = lab / rel
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            shutil.copy2(src, dst)
    # 2. Glob — yeni dosyalar otomatik
    for pattern in globs:
        for src in main.glob(pattern):
            dst = lab / src.relative_to(main)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
                shutil.copy2(src, dst)


def test_glob_picks_up_new_basketball_ratings_file(tmp_path):
    """Yeni hayali lig (Avrupa basket scraper'i) rating dosyasi glob ile sync olur."""
    main, lab = _setup_dirs(tmp_path)
    # Mevcut ligler
    (main / "data" / "basketball_cache" / "nba_ratings.json").write_text('[{"t":"LAL"}]')
    # YENİ hayali lig — Avrupa basket scraper output'u
    new_lig = main / "data" / "basketball_cache" / "liga_acb_ratings.json"
    new_lig.write_text('[{"t":"RM"}]')

    _run_sync(main, lab)

    # Beklenen: hem mevcut hem yeni lig lab'a sync edildi
    assert (lab / "data" / "basketball_cache" / "nba_ratings.json").exists()
    assert (lab / "data" / "basketball_cache" / "liga_acb_ratings.json").exists()
    # İçerik aynı
    assert (lab / "data" / "basketball_cache" / "liga_acb_ratings.json").read_text() == '[{"t":"RM"}]'


def test_fixed_list_syncs_calibration_and_ratings(tmp_path):
    """Sabit liste (tennis_calibration.json + tennis_ratings.json + tennis_ratings_surface.json)
    her sync'te kontrol edilir."""
    main, lab = _setup_dirs(tmp_path)
    (main / "data" / "tennis_calibration.json").write_text('{"curve": []}')
    (main / "data" / "tennis_ratings.json").write_text('{"players": {}}')
    (main / "data" / "tennis_ratings_surface.json").write_text('{"players_by_surface": {}}')

    _run_sync(main, lab)

    assert (lab / "data" / "tennis_calibration.json").exists()
    assert (lab / "data" / "tennis_ratings.json").exists()
    assert (lab / "data" / "tennis_ratings_surface.json").exists()


def test_state_files_NOT_synced(tmp_path):
    """positions.json, bot_status.json, stock_queue.json STATE-LEVEL — sync DEGIL.

    Lab kendi state'ini ureti̇r, ana bottan kopyalanmaz (her process kendi state).
    """
    main, lab = _setup_dirs(tmp_path)
    # Ana bot state file'lari
    (main / "data" / "positions.json").write_text('{"positions": {"x": {}}}')
    (main / "data" / "bot_status.json").write_text('{"mode": "live"}')
    (main / "data" / "stock_queue.json").write_text('{"items": []}')

    _run_sync(main, lab)

    # State file'lari lab'a sync EDILMEMELI
    assert not (lab / "data" / "positions.json").exists()
    assert not (lab / "data" / "bot_status.json").exists()
    assert not (lab / "data" / "stock_queue.json").exists()
