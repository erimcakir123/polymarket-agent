"""Team abbreviation / alias resolver — pure, static tables (no I/O).

Eski projede HTTP fetch (Polymarket/ESPN/PandaScore) vardı — v2'de kaldırıldı.
MVP 2-way sporlar için static tables yeterli. API refresh gerekirse ayrı
infrastructure modülü olarak ileri bir fazda eklenir (bot çalışırken cache
güncelleyen bir scheduled job).
"""
from __future__ import annotations

import unicodedata

_STRIP_SUFFIXES: tuple[str, ...] = (" fc", " sc", " esports", " gaming", " clan", " team")


def _strip_accents(text: str) -> str:
    """Diacritic/aksan kaldır: ş→s, ı→i, ö→o, ü→u, ç→c, ğ→g, é→e."""
    text = text.replace("\u0131", "i")  # Turkish dotless i — NFKD decompose etmez
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize(name: str) -> str:
    """Lowercase + strip accents + strip ortak suffix'ler."""
    if not name:
        return ""
    name = _strip_accents(name).lower().strip()
    for suffix in _STRIP_SUFFIXES:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name


# ── Static abbreviations — major leagues ──
_STATIC_ABBREVS: dict[str, str] = {
    # NBA
    "lal": "los angeles lakers", "bos": "boston celtics",
    "gsw": "golden state warriors", "bkn": "brooklyn nets",
    "nyk": "new york knicks", "phi": "philadelphia 76ers",
    "mil": "milwaukee bucks", "mia": "miami heat",
    "chi": "chicago bulls", "phx": "phoenix suns",
    "dal": "dallas mavericks", "den": "denver nuggets",
    "min": "minnesota timberwolves", "okc": "oklahoma city thunder",
    "cle": "cleveland cavaliers", "lac": "la clippers",
    "hou": "houston rockets", "mem": "memphis grizzlies",
    "nop": "new orleans pelicans", "atl": "atlanta hawks",
    "ind": "indiana pacers", "orl": "orlando magic",
    "tor": "toronto raptors", "wsh": "washington wizards",
    "det": "detroit pistons", "cha": "charlotte hornets",
    "sac": "sacramento kings", "por": "portland trail blazers",
    "uta": "utah jazz", "sas": "san antonio spurs",
    # NFL
    "kc": "kansas city chiefs", "buf": "buffalo bills",
    "bal": "baltimore ravens", "sf": "san francisco 49ers",
    "gb": "green bay packers", "tb": "tampa bay buccaneers",
    "ne": "new england patriots", "sea": "seattle seahawks",
    "pit": "pittsburgh steelers", "cin": "cincinnati bengals",
    "jax": "jacksonville jaguars", "ten": "tennessee titans",
    "lar": "los angeles rams", "nyg": "new york giants",
    "nyj": "new york jets", "car": "carolina panthers",
    "no": "new orleans saints", "lv": "las vegas raiders",
    "ari": "arizona cardinals",
    # MLB
    "nyy": "new york yankees", "lad": "los angeles dodgers",
    "nym": "new york mets", "chc": "chicago cubs",
    "cws": "chicago white sox", "sd": "san diego padres",
    "tex": "texas rangers", "stl": "st. louis cardinals",
    # NHL
    "mtl": "montreal canadiens", "nyr": "new york rangers",
    "edm": "edmonton oilers", "cgy": "calgary flames",
    "van": "vancouver canucks", "col": "colorado avalanche",
}


# ── Static aliases / nicknames ──
_STATIC_ALIASES: dict[str, str] = {
    # NBA nicknames
    "lakers": "los angeles lakers", "celtics": "boston celtics",
    "warriors": "golden state warriors", "bucks": "milwaukee bucks",
    "sixers": "philadelphia 76ers", "76ers": "philadelphia 76ers",
    "knicks": "new york knicks", "nets": "brooklyn nets",
    "heat": "miami heat", "nuggets": "denver nuggets",
    "suns": "phoenix suns", "mavs": "dallas mavericks",
    "thunder": "oklahoma city thunder", "wolves": "minnesota timberwolves",
    "cavs": "cleveland cavaliers", "clips": "la clippers",
    "rockets": "houston rockets", "grizzlies": "memphis grizzlies",
    "pelicans": "new orleans pelicans", "hawks": "atlanta hawks",
    "bulls": "chicago bulls", "pacers": "indiana pacers",
    "magic": "orlando magic", "raptors": "toronto raptors",
    "hornets": "charlotte hornets", "kings": "sacramento kings",
    "blazers": "portland trail blazers", "jazz": "utah jazz",
    "spurs": "san antonio spurs",
    # NHL nicknames
    "leafs": "toronto maple leafs", "habs": "montreal canadiens",
    "bruins": "boston bruins", "rangers": "new york rangers",
    "pens": "pittsburgh penguins", "caps": "washington capitals",
    "oilers": "edmonton oilers", "flames": "calgary flames",
    "avs": "colorado avalanche",
    # NFL nicknames
    "chiefs": "kansas city chiefs", "eagles": "philadelphia eagles",
    "niners": "san francisco 49ers", "cowboys": "dallas cowboys",
    "bills": "buffalo bills", "ravens": "baltimore ravens",
    "steelers": "pittsburgh steelers", "packers": "green bay packers",
    # MLB nicknames
    "yankees": "new york yankees", "dodgers": "los angeles dodgers",
    "red sox": "boston red sox", "mets": "new york mets",
    "astros": "houston astros", "braves": "atlanta braves",
    "cubs": "chicago cubs", "phillies": "philadelphia phillies",
    # Tennis (single-name aliases — MVP'de kullanılmayabilir ama referans)
    "djokovic": "novak djokovic", "sinner": "jannik sinner",
    "alcaraz": "carlos alcaraz", "medvedev": "daniil medvedev",
}


def resolve(token: str) -> str | None:
    """Abbreviation / alias / nickname → canonical lowercase team name.

    Bilinmeyen: None döner.
    """
    key = normalize(token)
    if not key:
        return None
    if key in _STATIC_ABBREVS:
        return _STATIC_ABBREVS[key]
    if key in _STATIC_ALIASES:
        return _STATIC_ALIASES[key]
    return None


def canonicalize(name: str) -> str:
    """İsim zaten canonical ise normalize haliyle döner; abbreviation/alias ise çözümler."""
    n = normalize(name)
    return _STATIC_ABBREVS.get(n) or _STATIC_ALIASES.get(n) or n
