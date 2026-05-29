"""Phase 1 verification — config.yaml allowed_sport_tags constraint.

After Phase 1, the whitelist must contain ONLY basketball sport tags
(NHL/NCAAF/CFL/UFL/MMA/UFC/Boxing/PGA/LIV/LPGA removed). Tennis
(atp/wta) is NOT added yet — that's Phase 3.
"""
from pathlib import Path

import yaml


_BASKET_ALLOWED = {"nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl"}
_MUST_NOT_BE_PRESENT = {
    "nhl",
    "ncaaf", "cfl", "ufl",
    "mma", "ufc", "boxing",
    "lpga*", "liv*", "pga*",
    # Tennis NOT added in Phase 1
    "atp", "wta",
}


def _load_config_yaml() -> dict:
    cfg_path = Path("config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def test_phase_1_whitelist_contains_only_basketball() -> None:
    cfg = _load_config_yaml()
    tags = set(cfg["scanner"]["allowed_sport_tags"])
    assert tags == _BASKET_ALLOWED, (
        f"Phase 1: whitelist must equal basketball-only set.\n"
        f"got: {sorted(tags)}\nexpected: {sorted(_BASKET_ALLOWED)}"
    )


def test_phase_1_whitelist_excludes_removed_sports() -> None:
    cfg = _load_config_yaml()
    tags = set(cfg["scanner"]["allowed_sport_tags"])
    intersect = tags & _MUST_NOT_BE_PRESENT
    assert not intersect, f"Phase 1: these tags must be REMOVED: {sorted(intersect)}"


def test_phase_1_mode_remains_dry_run() -> None:
    """Phase 1 must NOT change mode. Mode default stays dry_run until Phase 3."""
    cfg = _load_config_yaml()
    assert cfg.get("mode", "dry_run") == "dry_run", (
        "Phase 1 must keep mode=dry_run. Mode change is Phase 3."
    )
