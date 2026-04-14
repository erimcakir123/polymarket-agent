"""Polymarket slug/tag → The Odds API sport_key mapping.

Tek kaynak. Eski projeden migrate (tam tablo), tüm sporlar var. MVP kapsamı dışı
olan sporlar (draw-possible) scanner.allowed_sport_tags filter'ında bloklanır;
bu modül mapping için yetkili.
"""
from __future__ import annotations

import re

# ── Polymarket slug prefix → Odds API sport_key ──
_SLUG_TO_ODDS: dict[str, str] = {
    # American sports
    "mlb": "baseball_mlb",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
    "nfl": "americanfootball_nfl",
    "cfb": "americanfootball_ncaaf",
    # MMA
    "ufc": "mma_mixed_martial_arts",
    # Soccer — England
    "epl": "soccer_epl",
    "efa": "soccer_fa_cup",
    "efl": "soccer_efl_champ",
    "elc": "soccer_england_efl_cup",
    # Soccer — Spain
    "lal": "soccer_spain_la_liga",
    "cde": "soccer_spain_copa_del_rey",
    "cdr": "soccer_spain_copa_del_rey",
    # Soccer — Germany
    "bun": "soccer_germany_bundesliga",
    "bl2": "soccer_germany_bundesliga2",
    "dfb": "soccer_germany_dfb_pokal",
    # Soccer — Italy
    "sea": "soccer_italy_serie_a",
    "ser": "soccer_italy_serie_a",
    "itc": "soccer_italy_coppa_italia",
    # Soccer — France
    "fl1": "soccer_france_ligue_one",
    "fr2": "soccer_france_ligue_two",
    "cof": "soccer_france_coupe_de_france",
    # Soccer — Other Europe
    "ere": "soccer_netherlands_eredivisie",
    "por": "soccer_portugal_primeira_liga",
    "tur": "soccer_turkey_super_league",
    "sco": "soccer_spl",
    "bel": "soccer_belgium_first_div",
    "den": "soccer_denmark_superliga",
    "nor": "soccer_norway_eliteserien",
    "swe": "soccer_sweden_allsvenskan",
    "rus": "soccer_russia_premier_league",
    "gre": "soccer_greece_super_league",
    "aut": "soccer_austria_bundesliga",
    # Soccer — Americas
    "mls": "soccer_usa_mls",
    "arg": "soccer_argentina_primera_division",
    "bra": "soccer_brazil_campeonato",
    "bra2": "soccer_brazil_serie_b",
    "mex": "soccer_mexico_ligamx",
    "col": "soccer_colombia_primera_a",
    "col1": "soccer_colombia_primera_a",
    "chi": "soccer_chile_campeonato",
    "chi1": "soccer_chile_campeonato",
    "per1": "soccer_peru_primera_division",
    "bol1": "soccer_bolivia_primera_division",
    "ecu": "soccer_ecuador_primera_a",
    "uru": "soccer_uruguay_primera_division",
    "par": "soccer_paraguay_primera_division",
    "ven": "soccer_venezuela_primera_division",
    # Soccer — Asia
    "spl": "soccer_saudi_arabia_pro_league",
    "kor": "soccer_korea_kleague1",
    "jpn": "soccer_japan_j_league",
    "ind": "soccer_india_super_league",
    "chn": "soccer_china_superleague",
    "tha": "soccer_thailand_thai_league",
    "idn": "soccer_indonesia_liga1",
    # Soccer — Africa
    "egy1": "soccer_egypt_premier_league",
    "mar1": "soccer_morocco_botola_pro",
    # Soccer — Other Europe (2)
    "cze1": "soccer_czech_republic_first_league",
    "rou1": "soccer_romania_liga_1",
    "ukr1": "soccer_ukraine_premier_league",
    "hr1": "soccer_croatia_hnl",
    "svk1": "soccer_slovakia_super_liga",
    "sui": "soccer_switzerland_superleague",
    "pol": "soccer_poland_ekstraklasa",
    "cyp": "soccer_cyprus_first_division",
    # Soccer — Cups/International
    "ucl": "soccer_uefa_champs_league",
    "uel": "soccer_uefa_europa_league",
    "uecl": "soccer_uefa_europa_conference_league",
    "lib": "soccer_conmebol_copa_libertadores",
    "sud": "soccer_conmebol_copa_sudamericana",
    "fif": "soccer_fifa_world_cup",
    "euro": "soccer_uefa_european_championship",
    "con": "soccer_conmebol_copa_libertadores",
    "gold": "soccer_concacaf_gold_cup",
    "aus": "soccer_australia_aleague",
    # Basketball — non-NBA
    "wnba": "basketball_wnba",
    "cbb": "basketball_ncaab",
    "ncaab": "basketball_ncaab",
    "euroleague": "basketball_euroleague",
    # Hockey — non-NHL
    "ahl": "icehockey_ahl",
    # American Football — non-NFL
    "ncaaf": "americanfootball_ncaaf",
    # Boxing
    "box": "boxing_boxing",
    # Cricket
    "ipl": "cricket_ipl",
    "cric": "cricket_test_match",
    "cricipl": "cricket_ipl",
    "cricpsl": "cricket_psl",
    "psp": "cricket_psl",
    "cricbbl": "cricket_bbl",
    "criccpl": "cricket_cpl",
    "crict20blast": "cricket_t20_blast",
    "cricsa20": "cricket_sa20",
    "crint": "cricket_international_t20",
    "t20": "cricket_international_t20",
    "test": "cricket_test_match",
    "odi": "cricket_odi",
    # AFL
    "afl": "aussierules_afl",
    # Rugby
    "ruchamp": "rugbyunion_six_nations",
    "ruprem": "rugbyunion_premiership",
    # Baseball — non-MLB
    "kbo": "baseball_kbo",
    "npb": "baseball_npb",
    # Canadian Football
    "cfl": "americanfootball_cfl",
    # Golf
    "lpga": "golf_lpga_tour",
    "liv": "golf_liv_tour",
    # Rugby League
    "nrl": "rugbyleague_nrl",
}

# ── Polymarket Gamma tag slug → Odds API sport_key ──
_TAG_TO_ODDS: dict[str, str] = {
    # Soccer
    "premier-league": "soccer_epl",
    "la-liga": "soccer_spain_la_liga",
    "la-liga-2": "soccer_spain_segunda_division",
    "bundesliga": "soccer_germany_bundesliga",
    "serie-a": "soccer_italy_serie_a",
    "ligue-1": "soccer_france_ligue_one",
    "eredivisie": "soccer_netherlands_eredivisie",
    "primeira-liga": "soccer_portugal_primeira_liga",
    "super-lig": "soccer_turkey_super_league",
    "scottish-premiership": "soccer_spl",
    "belgian-pro-league": "soccer_belgium_first_div",
    "danish-superliga": "soccer_denmark_superliga",
    "eliteserien": "soccer_norway_eliteserien",
    "allsvenskan": "soccer_sweden_allsvenskan",
    "greek-super-league": "soccer_greece_super_league",
    "austrian-bundesliga": "soccer_austria_bundesliga",
    "russian-premier-league": "soccer_russia_premier_league",
    "saudi-professional-league": "soccer_saudi_arabia_pro_league",
    "k-league": "soccer_korea_kleague1",
    "j1-league": "soccer_japan_j_league",
    "a-league": "soccer_australia_aleague",
    "liga-mx": "soccer_mexico_ligamx",
    "liga-betplay": "soccer_colombia_primera_a",
    "brasileirao": "soccer_brazil_campeonato",
    "brazil-serie-b": "soccer_brazil_serie_b",
    "mls": "soccer_usa_mls",
    # Soccer — Cups
    "champions-league": "soccer_uefa_champs_league",
    "europa-league": "soccer_uefa_europa_league",
    "conference-league": "soccer_uefa_europa_conference_league",
    "copa-libertadores": "soccer_conmebol_copa_libertadores",
    "copa-sudamericana": "soccer_conmebol_copa_sudamericana",
    "fa-cup": "soccer_fa_cup",
    "efl-cup": "soccer_england_efl_cup",
    "dfb-pokal": "soccer_germany_dfb_pokal",
    "copa-del-rey": "soccer_spain_copa_del_rey",
    "coppa-italia": "soccer_italy_coppa_italia",
    "coupe-de-france": "soccer_france_coupe_de_france",
    # Soccer — additional
    "swiss-super-league": "soccer_switzerland_superleague",
    "polish-ekstraklasa": "soccer_poland_ekstraklasa",
    "czech-first-league": "soccer_czech_republic_first_league",
    "romanian-liga-i": "soccer_romania_liga_1",
    "ukrainian-premier-league": "soccer_ukraine_premier_league",
    "croatian-football-league": "soccer_croatia_hnl",
    "primera-divisin-argentina": "soccer_argentina_primera_division",
    "colombian-primera-a": "soccer_colombia_primera_a",
    "peruvian-liga-1": "soccer_peru_primera_division",
    "uruguayan-primera-division": "soccer_uruguay_primera_division",
    "ecuadorian-ligapro": "soccer_ecuador_primera_a",
    "venezuelan-primera": "soccer_venezuela_primera_division",
    "paraguayan-primera": "soccer_paraguay_primera_division",
    "indian-super-league": "soccer_india_super_league",
    "chinese-super-league": "soccer_china_superleague",
    "thai-league": "soccer_thailand_thai_league",
    "egyptian-premier-league": "soccer_egypt_premier_league",
    "concacaf-champions-cup": "soccer_concacaf_gold_cup",
    "uefa-nations-league": "soccer_uefa_european_championship",
    # Non-soccer
    "mlb": "baseball_mlb",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
    "nfl": "americanfootball_nfl",
    "wnba": "basketball_wnba",
    "ncaab": "basketball_ncaab",
    "ncaaf": "americanfootball_ncaaf",
    "afl": "aussierules_afl",
    "ipl": "cricket_ipl",
    "euroleague": "basketball_euroleague",
    # Cricket — tournament tags
    "psl": "cricket_psl",
    "big-bash-league": "cricket_bbl",
    "caribbean-premier-league": "cricket_cpl",
    "t20-blast": "cricket_t20_blast",
}


def slug_to_odds_key(slug_prefix: str) -> str | None:
    """Polymarket slug prefix'i → Odds API sport key."""
    if not slug_prefix:
        return None
    return _SLUG_TO_ODDS.get(slug_prefix.lower().strip())


def tag_to_odds_key(tag: str) -> str | None:
    """Polymarket Gamma tag slug'ı → Odds API sport key.
    Yıl eki varsa (örn. 'serie-a-2025') stripler.
    """
    if not tag:
        return None
    tag_lower = tag.lower().strip()
    if tag_lower in _TAG_TO_ODDS:
        return _TAG_TO_ODDS[tag_lower]
    stripped = re.sub(r"-\d{4}$", "", tag_lower)
    if stripped != tag_lower and stripped in _TAG_TO_ODDS:
        return _TAG_TO_ODDS[stripped]
    return None


def resolve_odds_key(slug: str | None, tags: list[str] | None) -> str | None:
    """Slug + tags'ten Odds API key bul. Slug kazanır, tag'ler fallback."""
    prefix = slug.split("-")[0].lower() if slug else ""
    result = slug_to_odds_key(prefix)
    if result:
        return result
    for tag in tags or []:
        result = tag_to_odds_key(tag)
        if result:
            return result
    return None


def is_soccer_key(sport_key: str | None) -> bool:
    """Odds API key soccer mı?"""
    if not sport_key:
        return False
    return sport_key.startswith("soccer_")
