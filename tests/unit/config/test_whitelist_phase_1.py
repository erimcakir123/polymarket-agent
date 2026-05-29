"""Phase 1 verification — historical (Phase 3 superseded these checks).

Phase 1 daralttı: basket-only, dry_run kalır.
Phase 3 eklendi: tennis (atp/wta) + mode=paper default.

Phase 1 testleri güncel state'e göre yeniden ifade edildi (basket hala içeride,
NHL/golf/MMA çıkarılmış kalır). Mode + tennis kontrolü Phase 3 testinde.
"""
from pathlib import Path

import yaml


_BASKET_REQUIRED = {"nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl"}
_PHASE_1_REMOVED = {
    "nhl",
    "ncaaf", "cfl", "ufl",
    "mma", "ufc", "boxing",
    "lpga*", "liv*", "pga*",
}


def _load_config_yaml() -> dict:
    cfg_path = Path("config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def test_phase_1_basketball_still_in_whitelist() -> None:
    """Phase 1 daralttı: basket içeride kalır (Phase 3'te tennis eklendi ama
    basket dokunulmaz)."""
    cfg = _load_config_yaml()
    tags = set(cfg["scanner"]["allowed_sport_tags"])
    missing = _BASKET_REQUIRED - tags
    assert not missing, f"Phase 1 daralttı ama basket TAGLARI EKSİK: {sorted(missing)}"


def test_phase_1_removed_sports_stay_out() -> None:
    """Phase 1'de çıkarılan sporlar (NHL/golf/MMA) Phase 3'te geri eklenmez."""
    cfg = _load_config_yaml()
    tags = set(cfg["scanner"]["allowed_sport_tags"])
    intersect = tags & _PHASE_1_REMOVED
    assert not intersect, f"Phase 1'de çıkarılan tag'ler geri sızmış: {sorted(intersect)}"
