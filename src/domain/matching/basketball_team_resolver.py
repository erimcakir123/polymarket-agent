"""Polymarket slug ↔ NBA/WNBA/NCAAB/WNCAAB/Euroleague team abbreviation eşlemesi.

Tennis player resolver paraleli (src/domain/matching/tennis_player_resolver.py).
Saf domain — I/O yok, sabit lookup tabloları.

Polymarket slug pattern'leri:
  - "nba-lal-gsw-2024-11-01" (3-harf abbreviation)
  - "nba-lakers-vs-warriors-2024-11-01" (full team adı)
  - "ncaab-duke-unc-2024-12-01"
  - "euroleague-realmadrid-barcelona-2024-10-15"

NCAAB / WNCAAB tam D1 listesi (~363 / ~351 takım) ayrı dosyalarda
(_ncaab_teams.py, _wncaab_teams.py) — yayına alma için Polymarket'te
trade edilebilecek tüm aktif programları kapsar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.domain.matching._ncaab_teams import NCAAB_TEAMS as _NCAAB_TEAMS_FULL
from src.domain.matching._wncaab_teams import WNCAAB_TEAMS as _WNCAAB_TEAMS_FULL


# NBA team abbreviations + alternate full-name kelimeleri.
_NBA_TEAMS: dict[str, str] = {
    "lal": "LAL", "lakers": "LAL",
    "gsw": "GSW", "warriors": "GSW",
    "bos": "BOS", "celtics": "BOS",
    "lac": "LAC", "clippers": "LAC",
    "phx": "PHX", "suns": "PHX", "phoenix": "PHX",
    "den": "DEN", "nuggets": "DEN",
    "mia": "MIA", "heat": "MIA",
    "nyk": "NYK", "knicks": "NYK",
    "bkn": "BKN", "nets": "BKN", "brooklyn": "BKN",
    "phi": "PHI", "76ers": "PHI", "sixers": "PHI",
    "mil": "MIL", "bucks": "MIL",
    "tor": "TOR", "raptors": "TOR",
    "chi": "CHI", "bulls": "CHI",
    "cle": "CLE", "cavaliers": "CLE", "cavs": "CLE",
    "det": "DET", "pistons": "DET",
    "ind": "IND", "pacers": "IND",
    "atl": "ATL", "hawks": "ATL",
    "cha": "CHA", "hornets": "CHA",
    "orl": "ORL", "magic": "ORL",
    "was": "WAS", "wizards": "WAS",
    "sas": "SAS", "spurs": "SAS",
    "hou": "HOU", "rockets": "HOU",
    "mem": "MEM", "grizzlies": "MEM",
    "nop": "NOP", "pelicans": "NOP",
    "dal": "DAL", "mavericks": "DAL", "mavs": "DAL",
    "okc": "OKC", "thunder": "OKC",
    "min": "MIN", "timberwolves": "MIN", "wolves": "MIN",
    "por": "POR", "blazers": "POR", "trail": "POR",
    "sac": "SAC", "kings": "SAC",
    "uta": "UTA", "jazz": "UTA",
}

# WNBA 14 takım (2026 sezonu — Golden State Valkyries 2025'te, Portland Fire 2026'da
# eklendi). Polymarket slug convention: lig kısaltması + 3-4 harf takım kısaltması.
# 2026-06-02 fix: gsv/por yeni takımlar; conn/wsh/la slug variantları alias olarak
# eklendi (Polymarket "wnba-conn-atl", "wnba-chi-wsh", "wnba-las-la" pattern üretiyor
# ama resolver eski sadece "con"/"was"/"las" tanıyordu → 111 maç skip alıyordu).
_WNBA_TEAMS: dict[str, str] = {
    "atl": "ATL", "dream": "ATL",
    "chi": "CHI", "sky": "CHI",
    "con": "CON", "conn": "CON", "sun": "CON", "connecticut": "CON",
    "dal": "DAL", "wings": "DAL",
    "ind": "IND", "fever": "IND",
    # Polymarket convention (test kanıtı: "wnba-las-la-2026-06-02" question
    # "Las Vegas Aces vs Los Angeles Sparks"): "las" = Las Vegas, "la" = LA Sparks
    "las": "LVA", "lv": "LVA", "lva": "LVA", "aces": "LVA", "vegas": "LVA",
    "la": "LAS", "sparks": "LAS",
    "min": "MIN", "lynx": "MIN",
    "nyl": "NYL", "liberty": "NYL",
    "phx": "PHX", "mercury": "PHX",
    "sea": "SEA", "storm": "SEA",
    "was": "WAS", "wsh": "WAS", "mystics": "WAS",
    # 2025 ekspansiyon — Golden State Valkyries
    "gsv": "GSV", "valkyries": "GSV",
    # 2026 ekspansiyon — Portland Fire (rating cache 13 takım, POR henüz yok;
    # rating eklenince hazır olur; resolver kabul eder, basketball_dispatch
    # rating yokluğunda zaten MODEL_TEAM_NOT_IN_RATINGS fail döner)
    "por": "POR", "fire": "POR",
    # 2026 ekspansiyon — Toronto Tempo (regression test ile yakalandı
    # 2026-06-02 SPEC-AUDIT-001 Task 4 — Polymarket "wnba-tor-nyl-..." slug)
    "tor": "TOR", "tempo": "TOR", "toronto": "TOR",
}

# SPEC-EUROBASKET-001 (2026-06-02): Liga Endesa (ACB) 18 takım.
# Polymarket slug pattern: "bkligend-rea-la-2026-06-02" (DOĞRULANMIŞ gamma API).
# Önemli: "bas" (Baskonia, Euroleague) vs "bas2" (Basket Zaragoza, ACB) ayrımı —
# slug "bas2" Zaragoza'yı işaret eder, KARIŞMASIN.
_ACB_TEAMS: dict[str, str] = {
    "rea": "RM", "madrid": "RM", "realmadrid": "RM",
    "bar": "FCB", "fcb": "FCB", "barcelona": "FCB", "barca": "FCB",
    "val": "VAL", "valencia": "VAL", "valenciabasket": "VAL",
    "bas": "BAS", "baskonia": "BAS", "vitoria": "BAS",
    "bas2": "ZAR", "zaragoza": "ZAR",  # Basket Zaragoza (NOT Baskonia)
    "ucm": "UCM", "unicaja": "UCM", "malaga": "UCM",
    "len": "LEN", "tenerife": "LEN",
    "la": "LAL", "lalaguna": "LAL",  # La Laguna Tenerife (DOĞRULANMIŞ)
    "gca": "GCA", "grancanaria": "GCA", "gc": "GCA",
    "bil": "BIL", "bilbao": "BIL", "surne": "BIL",
    "can": "CAN", "casademont": "CAN",  # Casademont Zaragoza
    "jov": "JOV", "joventut": "JOV", "badalona": "JOV",
    "man": "MAN", "manresa": "MAN",
    "mur": "MUR", "murcia": "MUR",
    "cb2": "MUR",  # CB Murcia alt slug (DOĞRULANMIŞ)
    "gra": "GRA", "granada": "GRA",
    "zun": "ZUN", "palencia": "ZUN", "zunder": "ZUN",
    "gir": "GIR", "girona": "GIR", "basquet": "GIR",
    "btv": "BTV", "breogan": "BTV", "lugo": "BTV",
    "rio": "RIO", "riobreogan": "RIO",
}

# SPEC-EUROBASKET-001 (2026-06-02): Türkiye BSL 16 takım. Slug prefix bkbsl tahmin.
_BSL_TEAMS: dict[str, str] = {
    "fb": "FB", "fenerbahce": "FB", "beko": "FB",
    "efes": "EFES", "anadoluefes": "EFES",
    "gs": "GS", "galatasaray": "GS", "nef": "GS",
    "tt": "TT", "tf": "TT", "turktelekom": "TT",
    "dar": "DAR", "darussafaka": "DAR",
    "bah": "BAH", "bahcesehir": "BAH", "koleji": "BAH",
    "bes": "BES", "besiktas": "BES", "emlakjet": "BES",
    "mer": "MER", "merkezefendi": "MER",
    "tof": "TOF", "tofas": "TOF",
    "kar": "KAR", "karsiyaka": "KAR",
    "pet": "PET", "petkim": "PET", "petkimspor": "PET",
    "man": "MNS", "manisa": "MNS",  # MNS (Manisa) vs MAN (Manresa ACB) ayrım için
    "sam": "SAM", "samsunspor": "SAM",
    "art": "ART", "aliaga": "ART",
    "yil": "YIL", "yilmaz": "YIL",
    "onv": "ONV", "buyukcekmece": "ONV", "onvo": "ONV",
}

# SPEC-EUROBASKET-001 (2026-06-02): Lega Serie A (İtalya) 16 takım. Slug prefix bklega tahmin.
_LEGA_TEAMS: dict[str, str] = {
    "mil": "MILA", "milano": "MILA", "olimpia": "MILA", "armani": "MILA",
    "virt": "VIRT", "virtus": "VIRT", "bologna": "VIRT",
    "trt": "TRT", "trento": "TRT",
    "ven": "VEN", "venezia": "VEN", "reyer": "VEN",
    "tor": "TORI", "torino": "TORI", "reale": "TORI",  # Lega Torino, NBA tor=TOR Raptors ayrı
    "bre": "BRE", "brescia": "BRE", "germani": "BRE",
    "var": "VAR", "varese": "VAR", "openjobmetis": "VAR",
    "sas": "SASS", "sassari": "SASS", "dinamo": "SASS",  # SASS (Sassari) vs NBA SAS (Spurs) ayrı
    "trp": "TRP", "trapani": "TRP",
    "scv": "SCV", "verona": "SCV", "scaligera": "SCV",
    "can": "CANT", "cantu": "CANT", "pallacanestro": "CANT",
    "nap": "NAP", "napoli": "NAP",
    "cre": "CRE", "cremona": "CRE",
    "tre": "TRE", "treviso": "TRE",
    "pis": "PIS", "pistoia": "PIS",
    "reg": "REG", "reggio": "REG", "emilia": "REG",
}

# SPEC-EUROBASKET-001 (2026-06-02): VTB United League 12 takım. Slug prefix bkvtb tahmin.
_VTB_TEAMS: dict[str, str] = {
    "cska": "CSKA", "moscow": "CSKA",
    "zen": "ZEN", "zenit": "ZEN", "petersburg": "ZEN",
    "uni": "UNI", "unics": "UNI", "kazan": "UNI",
    "lok": "LOK", "lokomotiv": "LOK", "kuban": "LOK",
    "parma": "PARMA", "pari": "PARMA",
    "avt": "AVT", "avtodor": "AVT", "saratov": "AVT",
    "mba": "MBA",
    "ura": "URA", "uralmash": "URA",
    "niz": "NIZ", "nizhny": "NIZ", "novgorod": "NIZ",
    "sam": "SAMA", "samara": "SAMA",  # SAMA vs BSL SAM ayrım
    "eni": "ENI", "enisey": "ENI", "krasnoyarsk": "ENI",
    "min": "MNSK", "minsk": "MNSK",  # MNSK vs NBA MIN (Timberwolves) ayrım
}


# Euroleague 20 takım (Polymarket aktif). Türkçe + İngilizce slug varyasyonları.
_EUROLEAGUE_TEAMS: dict[str, str] = {
    "realmadrid": "RM", "rm": "RM",
    "barcelona": "FCB", "barca": "FCB", "fcb": "FCB",
    "fenerbahce": "FB", "fb": "FB",
    "anadoluefes": "EFES", "efes": "EFES",
    "panathinaikos": "PAO", "pao": "PAO",
    "olympiacos": "OLY", "olympiakos": "OLY", "oly": "OLY",
    "maccabi": "MAC", "maccabitelaviv": "MAC",
    "cska": "CSKA", "moscow": "CSKA",
    "zalgiris": "ZAL", "zal": "ZAL",
    "bayern": "BAY", "bayernmunich": "BAY",
    "alba": "ALBA", "berlin": "ALBA",
    "asvel": "ASV", "lyon": "ASV",
    "monaco": "MON",
    "virtus": "VIRT", "virtusbologna": "VIRT", "bologna": "VIRT",
    "milano": "MIL", "olimpiamilano": "MIL", "armani": "MIL",
    "partizan": "PAR", "partizanbelgrade": "PAR",
    "redstar": "RED", "crvenazvezda": "RED",
    "valencia": "VAL", "valenciabasket": "VAL",
    "baskonia": "BASK", "vitoria": "BASK",
    "parisbasket": "PARI", "paris": "PARI",
}


@dataclass(frozen=True)
class ResolveResult:
    home: Optional[str]
    away: Optional[str]
    ok: bool
    fail_reason: Optional[str] = None


def _lookup(league: str) -> dict[str, str]:
    if league == "nba":
        return _NBA_TEAMS
    if league == "wnba":
        return _WNBA_TEAMS
    if league == "ncaab":
        return _NCAAB_TEAMS_FULL
    if league == "wncaab":
        return _WNCAAB_TEAMS_FULL
    if league == "euroleague":
        return _EUROLEAGUE_TEAMS
    # SPEC-EUROBASKET-001 (2026-06-02): 4 yeni Avrupa lig
    if league == "liga_acb":
        return _ACB_TEAMS
    if league == "turkey_bsl":
        return _BSL_TEAMS
    if league == "italy_lega":
        return _LEGA_TEAMS
    if league == "vtb":
        return _VTB_TEAMS
    return {}


def resolve_team_pair(slug: str, league: str) -> ResolveResult:
    """Polymarket slug'undan home/away abbreviation çıkar."""
    tbl = _lookup(league)
    if not tbl:
        return ResolveResult(None, None, False, f"unknown_league:{league}")
    parts = [p for p in slug.lower().split("-") if p and p not in {"vs", "v"}]
    found: list[str] = []
    for p in parts:
        if p in tbl:
            abbr = tbl[p]
            if abbr not in found:
                found.append(abbr)
        if len(found) == 2:
            break
    if len(found) < 2:
        return ResolveResult(None, None, False, f"teams_not_found:{slug}")
    return ResolveResult(home=found[0], away=found[1], ok=True)
