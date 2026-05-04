"""Sport-specific configs for 3-way sports (SPEC-015 DRY pattern)."""
from src.config.sport_configs.afl import AFL_CONFIG
from src.config.sport_configs.handball import HANDBALL_CONFIG
from src.config.sport_configs.rugby_union import RUGBY_UNION_CONFIG
from src.config.sport_configs.soccer import SOCCER_CONFIG

_SPORT_CONFIG_MAP: dict[str, dict] = {
    "soccer": SOCCER_CONFIG,
    "rugby_union": RUGBY_UNION_CONFIG,
    "rugby": RUGBY_UNION_CONFIG,
    "afl": AFL_CONFIG,
    "handball": HANDBALL_CONFIG,
}


def get_sport_config(sport_tag: str) -> dict | None:
    """sport_tag (lowercase) → config dict. Bulunmazsa None.

    Önce exact match, sonra substring (örn. 'soccer_epl' → 'soccer').
    """
    if not sport_tag:
        return None
    key = sport_tag.lower().strip()
    if key in _SPORT_CONFIG_MAP:
        return _SPORT_CONFIG_MAP[key]
    for k, v in _SPORT_CONFIG_MAP.items():
        if key.startswith(k):
            return v
    return None
