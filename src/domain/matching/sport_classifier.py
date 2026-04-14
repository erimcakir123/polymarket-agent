"""Market sport kategorisi sınıflandırıcı — slug / sport_tag / question fallback.

Sport code → category lookup. Polymarket GET /sports'tan türetilmiş 170+ code.
"""
from __future__ import annotations

# Polymarket sport code → category
_SLUG_TO_CATEGORY: dict[str, str] = {
    # Basketball
    "nba": "basketball", "wnba": "basketball", "cbb": "basketball",
    "cwbb": "basketball", "ncaab": "basketball",
    "euroleague": "basketball", "bkaba": "basketball", "bkarg": "basketball",
    "bkbbl": "basketball", "bkbsl": "basketball", "bkcba": "basketball",
    "bkcl": "basketball", "bkfr1": "basketball", "bkgr1": "basketball",
    "bkjpn": "basketball", "bkkbl": "basketball", "bkligend": "basketball",
    "bknbl": "basketball", "bkseriea": "basketball", "bkvtb": "basketball",
    "bkfibaqaf": "basketball", "bkfibaqam": "basketball",
    "bkfibaqas": "basketball", "bkfibaqeu": "basketball",
    # American Football
    "nfl": "football", "cfb": "football", "ncaaf": "football",
    "cfl": "football", "ufl": "football", "xfl": "football",
    # Baseball
    "mlb": "baseball", "kbo": "baseball", "wbc": "baseball",
    "npb": "baseball", "cbase": "baseball",
    # Hockey
    "nhl": "hockey", "ahl": "hockey", "khl": "hockey",
    "shl": "hockey", "cehl": "hockey", "dehl": "hockey", "snhl": "hockey",
    # Soccer
    "epl": "soccer", "lal": "soccer", "bun": "soccer", "sea": "soccer",
    "fl1": "soccer", "ucl": "soccer", "uel": "soccer", "uef": "soccer",
    "ere": "soccer", "por": "soccer", "tur": "soccer", "mls": "soccer",
    "efa": "soccer", "efl": "soccer", "dfb": "soccer", "cde": "soccer",
    "cdr": "soccer", "lcs": "soccer", "lib": "soccer", "sud": "soccer",
    "con": "soccer", "cof": "soccer", "ofc": "soccer", "fif": "soccer", "afc": "soccer",
    "mex": "soccer", "bra": "soccer", "bra2": "soccer", "arg": "soccer",
    "col": "soccer", "chi": "soccer", "jap": "soccer", "kor": "soccer",
    "ind": "soccer", "spl": "soccer", "aus": "soccer", "nor": "soccer",
    "den": "soccer", "rus": "soccer", "caf": "soccer", "acn": "soccer",
    "itc": "soccer", "cze1": "soccer", "egy1": "soccer", "mar1": "soccer",
    "per1": "soccer", "rou1": "soccer", "ukr1": "soccer", "uwcl": "soccer",
    "bol1": "soccer", "chi1": "soccer", "col1": "soccer",
    "ja2": "soccer", "j1-100": "soccer", "j2-100": "soccer",
    "j1100": "soccer", "j2100": "soccer",
    "abb": "soccer", "ssc": "soccer", "mwoh": "soccer", "wwoh": "soccer",
    "nwsl": "soccer", "bl2": "soccer", "es2": "soccer", "fr2": "soccer",
    "scop": "soccer", "svk1": "soccer", "hr1": "soccer", "isp": "soccer",
    "ecu": "soccer", "uru": "soccer", "par": "soccer", "ven": "soccer",
    "sui": "soccer", "pol": "soccer", "cyp": "soccer", "irl1": "soccer",
    "nga": "soccer", "gha": "soccer", "tha": "soccer", "mys": "soccer",
    "idn": "soccer", "sgp": "soccer", "elc": "soccer",
    "unl": "soccer", "cnl": "soccer", "afcl": "soccer", "ccup": "soccer",
    "cafcl": "soccer", "ser": "soccer", "sco": "soccer", "bel": "soccer",
    "aut": "soccer", "gre": "soccer", "swe": "soccer",
    # MMA
    "ufc": "mma", "zuffa": "mma",
    # Tennis
    "atp": "tennis", "wta": "tennis", "wttmen": "tennis",
    # Golf
    "pga": "golf", "lpga": "golf",
    # Cricket
    "ipl": "cricket", "odi": "cricket", "t20": "cricket", "test": "cricket",
    "csa": "cricket", "lpl": "cricket", "psp": "cricket", "she": "cricket",
    "sasa": "cricket", "craus": "cricket", "crban": "cricket",
    "creng": "cricket", "crind": "cricket", "crint": "cricket",
    "crnew": "cricket", "crpak": "cricket", "crsou": "cricket",
    "cruae": "cricket", "cru19wc": "cricket", "crwncl": "cricket",
    "crwpl20": "cricket", "crwt20wcgq": "cricket", "crafgwi20": "cricket",
    "crbtnmlyhkg20": "cricket",
    "cricbbl": "cricket", "cricbpl": "cricket", "criccpl": "cricket",
    "criccsat20w": "cricket", "crichkt20w": "cricket", "cricilt20": "cricket",
    "cricipl": "cricket", "criclcl": "cricket", "cricmlc": "cricket",
    "cricnt20c": "cricket", "cricpakt20cup": "cricket", "cricps": "cricket",
    "cricpsl": "cricket", "cricsa20": "cricket", "cricsm": "cricket",
    "cricss": "cricket", "crict20blast": "cricket", "crict20lpl": "cricket",
    "crict20plw": "cricket", "cricthunderbolt": "cricket",
    "cricwncl": "cricket",
    # Rugby
    "ruchamp": "rugby", "rueuchamp": "rugby", "ruprem": "rugby",
    "rusixnat": "rugby", "rusrp": "rugby", "rutopft": "rugby",
    "ruurc": "rugby",
    # Esports
    "cs2": "esports", "lol": "esports", "dota2": "esports", "val": "esports",
    "ow": "esports", "codmw": "esports", "mlbb": "esports", "pubg": "esports",
    "r6siege": "esports", "rl": "esports", "hok": "esports",
    "wildrift": "esports", "sc2": "esports", "sc": "esports", "fifa": "esports",
    # Lacrosse
    "pll": "lacrosse", "wll": "lacrosse", "nll": "lacrosse",
    # Australian Football
    "afl": "australian_football",
    # Boxing
    "box": "boxing",
    # Racing
    "f1": "racing", "irl": "racing", "nascar": "racing",
    # Chess
    "chess": "chess",
    # Water Polo
    "wpolo": "water_polo",
}

# Question keyword fallback
_QUESTION_KEYWORDS: dict[str, str] = {
    "nba": "basketball", "wnba": "basketball", "ncaa basketball": "basketball",
    "nfl": "football", "mlb": "baseball", "nhl": "hockey",
    "premier league": "soccer", "champions league": "soccer",
    "la liga": "soccer", "bundesliga": "soccer", "serie a": "soccer",
    "ligue 1": "soccer", "mls": "soccer",
    "ufc": "mma", "mma": "mma",
    "atp": "tennis", "wta": "tennis",
    "counter-strike": "esports", "cs2": "esports", "valorant": "esports",
    "league of legends": "esports", "dota": "esports",
    "overwatch": "esports", "rocket league": "esports",
    "call of duty": "esports", "pubg": "esports",
    "starcraft": "esports", "mobile legends": "esports",
    "rainbow six": "esports", "r6 siege": "esports",
    "honor of kings": "esports", "king of glory": "esports",
    "wild rift": "esports", "ea fc": "esports",
    "cricket": "cricket", "ipl": "cricket", "t20": "cricket",
    "rugby": "rugby",
    "lacrosse": "lacrosse", "pll": "lacrosse",
}


def classify_sport(slug: str = "", sport_tag: str = "", question: str = "") -> str | None:
    """Pazar verisini spor kategorisine sınıflandır.

    Öncelik: slug prefix → sport_tag → question keyword. Bilinmeyen: None.
    """
    slug = (slug or "").lower()
    sport_tag = (sport_tag or "").lower()

    # 1. Slug prefix (en güvenilir)
    prefix = slug.split("-")[0] if slug else ""
    if prefix in _SLUG_TO_CATEGORY:
        return _SLUG_TO_CATEGORY[prefix]

    # 2. sport_tag
    if sport_tag in _SLUG_TO_CATEGORY:
        return _SLUG_TO_CATEGORY[sport_tag]

    # 3. Question keyword fallback
    q = (question or "").lower()
    for keyword, category in _QUESTION_KEYWORDS.items():
        if keyword in q:
            return category

    return None
