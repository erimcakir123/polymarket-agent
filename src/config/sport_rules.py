"""Sport-specific trading rules (TDD §7.2). MVP 2-way sports only.

Draw-possible sporlar TODO-001 kapsamında, bu dosyada YOK.
"""
from __future__ import annotations

from typing import Any

# ── MVP sport rules (2-way) ──
SPORT_RULES: dict[str, dict] = {
    "nba": {
        "match_duration_hours": 2.5,
        "score_source": "espn",
        "espn_sport": "basketball",
        "espn_league": "nba",
        # Score exit N1: Q3 sonu + ağır fark (SPEC-A4: 20→18, modern NBA regime change payı)
        "score_exit_n1_elapsed": 0.75,
        "score_exit_n1_deficit": 18,
        # Score exit N2: son 4dk + anlamlı fark (SPEC-A4: 10→8, hala %8-10 safe)
        "score_exit_n2_elapsed": 0.92,
        "score_exit_n2_deficit": 8,
        # Score exit N3 (SPEC-A4): son 2dk + one-score+ deficit → matematiksel bitik
        "score_exit_n3_clock_seconds": 120,
        "score_exit_n3_deficit": 5,
    },
    "nfl": {
        "match_duration_hours": 3.25,
        "score_source": "espn",
        "espn_sport": "football",
        "espn_league": "nfl",
        # Score exit N1: Q3 sonu + 2.5-skor farkı (SPEC-A4: 21→17, σ-model %99 güven)
        "score_exit_n1_elapsed": 0.75,
        "score_exit_n1_deficit": 17,
        # Score exit N2: son 5dk + 2-possession (SPEC-A4: 11→9, hala %3-4 safe)
        "score_exit_n2_elapsed": 0.92,
        "score_exit_n2_deficit": 9,
        # Score exit N3 (SPEC-A4): son 2.5dk + one-score deficit → possession belirsiz
        "score_exit_n3_clock_seconds": 150,
        "score_exit_n3_deficit": 4,
    },
    "nhl": {
        "match_duration_hours": 2.5,
        "period_exit_deficit": 3,
        "late_deficit": 2,
        "late_elapsed_gate": 0.67,
        "score_price_confirm": 0.35,
        "final_elapsed_gate": 0.92,
        "score_source": "espn",
        "espn_sport": "hockey",
        "espn_league": "nhl",
    },
    "mlb": {
        "match_duration_hours": 3.0,
        # SPEC-010: M1/M2/M3 forced exit (tennis T1/T2, hockey K1-K4 simetrik)
        "score_exit_m1_inning": 7,     # M1 tetik inning (blowout)
        "score_exit_m1_deficit": 5,    # M1 run deficit threshold
        "score_exit_m2_inning": 8,     # M2 tetik inning (late big deficit)
        "score_exit_m2_deficit": 3,    # M2 run deficit threshold
        "score_exit_m3_inning": 9,     # M3 tetik inning (final inning)
        "score_exit_m3_deficit": 1,    # M3 run deficit threshold
        "score_source": "espn",
        "espn_sport": "baseball",
        "espn_league": "mlb",
    },
    "tennis": {
        "match_duration_hours": 2.5,
        "match_duration_hours_bo3": 1.75,
        "match_duration_hours_bo5": 3.5,
        "score_source": "espn",
        "espn_sport": "tennis",
        "espn_league": "atp",
        "set_exit_deficit": 3,
        "set_exit_games_total": 7,
        "set_exit_blowout_deficit": 4,
        "set_exit_close_set_threshold": 5,
        "set_exit_close_set_buffer": 1,
        "set_exit_serve_for_match_games": 5,
    },
    "tennis_wta": {
        "match_duration_hours": 2.5,
        "match_duration_hours_bo3": 1.75,
        "match_duration_hours_bo5": 3.5,
        "score_source": "espn",
        "espn_sport": "tennis",
        "espn_league": "wta",
        "set_exit_deficit": 3,
        "set_exit_games_total": 7,
        "set_exit_blowout_deficit": 4,
        "set_exit_close_set_threshold": 5,
        "set_exit_close_set_buffer": 1,
        "set_exit_serve_for_match_games": 5,
    },
}

# ── Cricket (SPEC-011) ──────────────────────────────────────
# T20 formatlari ayni C1/C2/C3 threshold'lari paylasir.
# ODI icin daha gevsek threshold (daha uzun mac, daha fazla ball).

_T20_SCORE_EXIT = {
    "score_exit_c1_balls": 30,    # son 5 over
    "score_exit_c1_rate": 18.0,   # RRR > 18 imkansiz
    "score_exit_c2_wickets": 8,
    "score_exit_c2_runs": 20,
    "score_exit_c3_balls": 6,     # son 1 over
    "score_exit_c3_runs": 10,
}

_CRICKET_BASE = {
    "score_source": "cricapi",    # ESPN yok, Odds API aggregate only
}

for _key in (
    "cricket_ipl", "cricket_big_bash", "cricket_caribbean_premier_league",
    "cricket_t20_blast", "cricket_international_t20", "cricket_psl",
):
    SPORT_RULES[_key] = {
        **_CRICKET_BASE,
        "match_duration_hours": 3.5,
        **_T20_SCORE_EXIT,
    }

SPORT_RULES["cricket_odi"] = {
    **_CRICKET_BASE,
    "match_duration_hours": 8.0,
    "score_exit_c1_balls": 60,     # son 10 over
    "score_exit_c1_rate": 12.0,    # ODI RRR > 12 imkansiz
    "score_exit_c2_wickets": 8,
    "score_exit_c2_runs": 40,
    "score_exit_c3_balls": 30,     # son 5 over
    "score_exit_c3_runs": 30,
}

SPORT_RULES["cricket"] = SPORT_RULES["cricket_ipl"]  # default T20 fallback

# SPEC-015: Soccer + 3-way sports
SPORT_RULES["soccer"] = {
    "match_duration_hours": 2.0,    # 90 dk + stoppage + buffer
    "score_source": "espn",
    "espn_sport": "soccer",
    "espn_league": "",              # league per-event (slug-based)
}

SPORT_RULES["rugby_union"] = {
    "match_duration_hours": 1.75,
    "score_source": "espn",
    "espn_sport": "rugby",
    "espn_league": "",
}

SPORT_RULES["afl"] = {
    "match_duration_hours": 2.0,
    "score_source": "espn",
    "espn_sport": "aussierules",
    "espn_league": "afl",
}

SPORT_RULES["handball"] = {
    "match_duration_hours": 1.5,
    "score_source": "espn",
    "espn_sport": "handball",
    "espn_league": "",
}

# SPEC-014: AHL hockey family — NHL K1-K4 eşiklerini paylaşır, sadece ESPN endpoint farklı
SPORT_RULES["ahl"] = {
    **SPORT_RULES["nhl"],
    "espn_league": "ahl",
}

# ── Basketball — non-NBA ────────────────────────────────────
SPORT_RULES["wnba"] = {
    "match_duration_hours": 2.25,
    "score_source": "espn",
    "espn_sport": "basketball",
    "espn_league": "wnba",  # basketball/wnba — 200 confirmed
}

SPORT_RULES["euroleague"] = {
    "match_duration_hours": 2.5,
    "score_source": "espn",
    "espn_sport": "basketball",
    "espn_league": "",  # ESPN basketball/euroleague → 400; no valid path
}

SPORT_RULES["ncaab"] = {
    "match_duration_hours": 2.5,
    "score_source": "espn",
    "espn_sport": "basketball",
    "espn_league": "mens-college-basketball",  # basketball/mens-college-basketball → 200 confirmed
}

SPORT_RULES["nbl"] = {
    "match_duration_hours": 2.5,
    "score_source": "espn",
    "espn_sport": "basketball",
    "espn_league": "nbl",  # basketball/nbl → 200 confirmed (Australian NBL)
}

# ── Ice Hockey — European Leagues ──────────────────────────
SPORT_RULES["liiga"] = {
    **SPORT_RULES["nhl"],
    "espn_league": "",  # hockey/liiga → 400; no ESPN path
}

SPORT_RULES["shl"] = {
    **SPORT_RULES["nhl"],
    "espn_league": "",  # hockey/shl → 400; no ESPN path
}

SPORT_RULES["allsvenskan"] = {
    **SPORT_RULES["nhl"],
    "espn_league": "",  # hockey/allsvenskan → 400; no ESPN path
}

SPORT_RULES["mestis"] = {
    **SPORT_RULES["nhl"],
    "espn_league": "",  # hockey/mestis → 400; no ESPN path
}

# ── Baseball — Asian Leagues ────────────────────────────────
# ESPN HTTP 400 confirmed — score enrichment ESPN'den gelmez, Odds API fallback
SPORT_RULES["kbo"] = {
    **SPORT_RULES["mlb"],
    "espn_sport": "baseball",
    "espn_league": "",  # baseball/kbo → 400; no ESPN path
}

SPORT_RULES["npb"] = {
    **SPORT_RULES["mlb"],
    "espn_sport": "baseball",
    "espn_league": "",  # baseball/npb → 400; no ESPN path
}

# ── Combat / Golf — ESPN desteği yok ───────────────────────
SPORT_RULES["mma"] = {
    "match_duration_hours": 0.5,
    "score_source": "odds",
    "espn_sport": "",
    "espn_league": "",
}

SPORT_RULES["golf"] = {
    "match_duration_hours": 8.0,
    "score_source": "odds",
    "espn_sport": "",
    "espn_league": "",
}

DEFAULT_RULES: dict[str, Any] = {
    "match_duration_hours": 2.0,
}

# Odds API key → internal sport key aliases (TDD §7.1 MVP)
_ALIASES: dict[str, str] = {
    # Basketball
    "basketball_nba": "nba",
    "basketball_wnba": "wnba",
    "basketball_ncaab": "ncaab",
    "basketball_wncaab": "ncaab",
    "basketball_euroleague": "euroleague",
    "basketball_nbl": "nbl",
    "basketball": "nba",
    # American Football
    "americanfootball_ncaaf": "nfl",
    "americanfootball_cfl": "nfl",
    "americanfootball_ufl": "nfl",
    "americanfootball": "nfl",
    # Ice Hockey
    "icehockey_nhl": "nhl",
    "icehockey_ahl": "ahl",
    "icehockey_liiga": "liiga",
    "icehockey_mestis": "mestis",
    "icehockey_sweden_hockey_league": "shl",
    "icehockey_sweden_allsvenskan": "allsvenskan",
    "icehockey": "nhl",
    # Baseball
    "baseball_mlb": "mlb",
    "baseball_milb": "mlb",
    "baseball_npb": "npb",
    "baseball_kbo": "kbo",
    "baseball_ncaa": "mlb",
    "baseball": "mlb",
    # Tennis
    "tennis_atp": "tennis",
    "tennis_wta": "tennis_wta",
    # Combat sports
    "mma_ufc": "mma",
    "ufc": "mma",
    "boxing": "mma",
    # Golf
    "golf_lpga_tour": "golf",
    "golf_liv_tour": "golf",
    # Cricket Polymarket/OddsAPI aliases (SPEC-011)
    "indian-premier-league": "cricket_ipl",
    "international-cricket": "cricket_international_t20",
    "cricket_test": "cricket",  # defensive — test cricket not directly supported
    # Soccer aliases (SPEC-015) — common Polymarket tags → soccer
    "epl": "soccer",
    "premier-league": "soccer",
    "la-liga": "soccer",
    "la-liga-2": "soccer",
    "bundesliga": "soccer",
    "serie-a": "soccer",
    "ligue-1": "soccer",
    "champions-league": "soccer",
    "europa-league": "soccer",
    "conference-league": "soccer",
    "mls": "soccer",
    "eredivisie": "soccer",
    "primeira-liga": "soccer",
    "super-lig": "soccer",
    "brasileirao": "soccer",
    "argentine-primera-division": "soccer",
    "liga-mx": "soccer",
    "scottish-premiership": "soccer",
    "belgian-pro-league": "soccer",
    "danish-superliga": "soccer",
    "eliteserien": "soccer",
    "allsvenskan-soccer": "soccer",
    "greek-super-league": "soccer",
    "austrian-bundesliga": "soccer",
    "russian-premier-league": "soccer",
    "saudi-professional-league": "soccer",
    "k-league": "soccer",
    "j1-league": "soccer",
    "a-league": "soccer",
    "chinese-super-league": "soccer",
    "thai-league": "soccer",
    "indian-super-league": "soccer",
    "egyptian-premier-league": "soccer",
    "polish-ekstraklasa": "soccer",
    "czech-first-league": "soccer",
    "romanian-liga-i": "soccer",
    "ukrainian-premier-league": "soccer",
    "croatian-football-league": "soccer",
    "colombian-primera-a": "soccer",
    "peruvian-liga-1": "soccer",
    "uruguayan-primera-division": "soccer",
    "ecuadorian-ligapro": "soccer",
    "fa-cup": "soccer",
    "efl-cup": "soccer",
    "dfb-pokal": "soccer",
    "copa-del-rey": "soccer",
    "coppa-italia": "soccer",
    "coupe-de-france": "soccer",
    "copa-libertadores": "soccer",
    "copa-sudamericana": "soccer",
    "nwsl": "soccer",
    # Rugby aliases (SPEC-015)
    "rugby": "rugby_union",
    "rugby-union": "rugby_union",
    "rugby-league": "rugby_union",
    "six-nations": "rugby_union",
    "premiership-rugby": "rugby_union",
    "nrl": "rugby_union",
    # Cricket Odds API keys (SPEC-011 Task 3)
    "cricket_bbl": "cricket_big_bash",
    "cricket_cpl": "cricket_caribbean_premier_league",
    "cricket_sa20": "cricket",           # SA20 not in MVP scope; fallback to generic T20 cricket
    "cricket_test_match": "cricket",     # Test matches out of scope; degrade gracefully
}


def _normalize(sport_tag: str) -> str:
    tag = (sport_tag or "").lower().strip()
    if tag in SPORT_RULES:
        return tag
    if tag in _ALIASES:
        return _ALIASES[tag]
    # tennis_* prefix match (dinamik turnuvalar)
    if tag.startswith("tennis_"):
        return "tennis"
    return ""


def get_sport_rule(sport_tag: str, key: str, default: Any = None) -> Any:
    tag = _normalize(sport_tag)
    rules = SPORT_RULES.get(tag, DEFAULT_RULES)
    return rules.get(key, DEFAULT_RULES.get(key, default))


def get_match_duration_hours(sport_tag: str) -> float:
    return float(get_sport_rule(sport_tag, "match_duration_hours", 2.0))


CRICKET_SPORT_TAGS: frozenset[str] = frozenset({
    "cricket", "cricket_ipl", "cricket_odi", "cricket_international_t20",
    "cricket_psl", "cricket_big_bash", "cricket_caribbean_premier_league",
    "cricket_t20_blast", "cricket_bbl", "cricket_cpl",
})


def is_cricket_sport(sport_tag: str) -> bool:
    """Cricket sport_tag mi? Explicit lig tag'leri + cricket_* prefix."""
    tag = _normalize(sport_tag)
    return tag in CRICKET_SPORT_TAGS or tag.startswith("cricket")
