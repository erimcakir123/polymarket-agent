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
# Polymarket /teams?league=bkligend endpoint'ten DOĞRULANMIŞ (2026-06-03 fix).
# CRITICAL: Polymarket alias'ları Euroleague convention'undan FARKLI.
# Çakışma örnekleri (sport_tag bazlı dict lookup koruyor):
#   "bas" → Polymarket'te Basquet GIRONA (Baskonia DEĞİL); Baskonia = "sas"
#   "uni" → Polymarket'te UNICAJA (Treviso Lega'da, UNICS VTB'de — sport_tag ayrı)
#   "cb"  → CB Breogán Lugo
#   "gra" → Granada; "gra2" → Gran Canaria (eski "gca" Polymarket'te YOK)
#   "bas2" → Basket Zaragoza; "bas3" → Andorra; "bas" → Girona (3 farklı kulüp)
_ACB_TEAMS: dict[str, str] = {
    # Polymarket alias → standart abbr (alias zorunlu, kalanı isim variantı)
    "rea": "RM", "madrid": "RM", "realmadrid": "RM",
    "bar": "FCB", "fcb": "FCB", "barcelona": "FCB", "barca": "FCB",
    "val": "VAL", "valencia": "VAL", "valenciabasket": "VAL",
    "sas": "BAS", "baskonia": "BAS", "vitoria": "BAS",  # API: sas=Saski Baskonia
    "bas2": "ZAR", "zaragoza": "ZAR",  # Basket Zaragoza
    "bas3": "AND", "andorra": "AND", "basquetandorra": "AND",  # Bàsquet Club Andorra
    "uni": "UCM", "unicaja": "UCM", "malaga": "UCM",  # API: uni=Unicaja
    # 2026-06-03 SPEC-EUROBASKET-001 align: ACB scraper "Tenerife"/"La Laguna
    # Tenerife"/"Lenovo Tenerife" → LEN üretir (Polymarket /teams API'de bu
    # takım tek kayıt). Eski "LAL" yanlıştı (cache key mismatch → trade YOK).
    "la": "LEN", "lalaguna": "LEN", "tenerife": "LEN",  # La Laguna Tenerife
    "len": "LEN", "lenovo": "LEN",
    "bil": "BIL", "bilbao": "BIL", "surne": "BIL",
    "jov": "JOV", "joventut": "JOV", "badalona": "JOV",
    "man": "MAN", "manresa": "MAN",
    "cb2": "MUR", "mur": "MUR", "murcia": "MUR",  # CB Murcia
    "gra": "GRA", "granada": "GRA",
    "gra2": "GCA", "grancanaria": "GCA",  # Gran Canaria (Polymarket gra2, NOT gca)
    "bas": "GIR", "girona": "GIR", "basquetgirona": "GIR",  # Basquet Girona
    "cb": "BTV", "breogan": "BTV", "lugo": "BTV",  # CB Breogán Lugo
    "bur": "BUR", "burgos": "BUR", "sanpablo": "BUR",  # San Pablo Burgos
    "for": "LLE", "lleida": "LLE", "forcalleida": "LLE",  # Força Lleida CE
}

# SPEC-EUROBASKET-001 (2026-06-02): Türkiye BSL 16 takım. Slug prefix bkbsl
# DOĞRULANMIŞ — gamma API tag_id=104347 üzerinden tüm 16 takım kısaltması
# Polymarket'in kullandığı haliyle çıkartıldı (örn: "bkbsl-fen-ana-2026-06-03").
# Önemli ayrımlar:
#   - "man" (Manisa BB, BSL) → "MNS" yapılır çünkü "MAN" Manresa (ACB) için ayrıldı
#   - "mer2" (Merkezefendi) vs "mer" (Mersin BSB) — Polymarket "mer2" suffix
#     ekleyerek zaten ayırmış, biz de aynı convention'ı izliyoruz
#   - "tur" (Turk Telekom) Türkiye genel slug "turkey" ile çakışmaz çünkü
#     resolver context-aware (league="turkey_bsl" parametresi)
_BSL_TEAMS: dict[str, str] = {
    "bes": "BES", "besiktas": "BES", "gain": "BES",
    "bah": "BAH", "bahcesehir": "BAH", "koleji": "BAH",
    "fen": "FEN", "fenerbahce": "FEN", "beko": "FEN",
    "ana": "ANA", "anadolu": "ANA", "anadoluefes": "ANA", "efes": "ANA",
    "gal": "GAL", "galatasaray": "GAL", "mct": "GAL",
    "tur": "TUR", "turktelekom": "TUR",
    "pet": "PET", "petkim": "PET", "petkimspor": "PET",
    "tof": "TOF", "tofas": "TOF",
    "tra": "TRA", "trabzonspor": "TRA",
    "man": "MNS", "manisa": "MNS", "glint": "MNS",  # MNS vs MAN (Manresa ACB) ayrım
    "kar": "KAR", "karsiyaka": "KAR",
    "bur": "BUR", "bursaspor": "BUR", "yorsan": "BUR",
    "mer2": "MER2", "merkezefendi": "MER2", "yukatel": "MER2",  # Polymarket suffix
    "ese": "ESE", "esenler": "ESE", "erokspor": "ESE", "safiport": "ESE",
    "mer": "MER", "mersin": "MER", "msk": "MER",  # Mersin MSK/BSB
    "buy": "BUY", "buyukcekmece": "BUY", "onvo": "BUY",
}

# SPEC-EUROBASKET-001 (2026-06-02): Lega Serie A (Italya) 16 takım.
# Slug prefix bkseriea-* DOĞRULANMIŞ — gamma series_id=10877 üzerinden tüm aktif
# sezon slug'ları çekildi (100+ event) ve takım token'ları çıkartıldı.
# Pallacanestro kümesi: Polymarket 5 farklı "Pallacanestro X" kulübünü
# "pal", "pal2", "pal3", "pal4", "pal5" ile ayırıyor (aynı kelime çakışmasın diye).
# Conflict önleme (diğer ligler çakışmasın):
#   "milano" → MILA  (NBA mil=MIL Bucks ayrı; Euroleague "milano"=MIL ayrı dict)
#   "sassari"/"dinamo" → SASS  (NBA sas=SAS Spurs ayrı)
#   "cantu"/"pallacanestro" → CANT  (ACB can=CAN Casademont ayrı)
#   "tor"/"torino" → TORI  (NBA tor=TOR Raptors ayrı) — şu an Lega'da Torino yok ama
#                  rezerve, çıkarsa hazır
_LEGA_TEAMS: dict[str, str] = {
    # Polymarket slug token'ları (zorunlu — slug parser bunlara birebir bakar)
    "oli": "MILA", "olimpia": "MILA", "milano": "MILA", "armani": "MILA",
    "vir": "VIRT", "virtus": "VIRT", "bologna": "VIRT",
    "rey": "REY", "reyer": "REY", "venezia": "REY",
    "aqu": "TRT", "aquila": "TRT", "trento": "TRT",
    "din": "SASS", "dinamo": "SASS", "sassari": "SASS",  # SASS vs NBA SAS (Spurs)
    "nap": "NAP", "napoli": "NAP",
    "tra": "TRP", "trapani": "TRP",
    "der": "DER", "derthona": "DER", "tortona": "DER",
    "van": "CRE", "vanoli": "CRE", "cremona": "CRE",
    "ami": "UDI", "amici": "UDI", "udinese": "UDI",
    "uni": "TRV", "universo": "TRV", "treviso": "TRV",
    # Pallacanestro kümesi — "pal" + rakam Polymarket convention
    "pal": "CANT", "cantu": "CANT", "pallacanestro": "CANT",  # CANT vs ACB CAN
    "pal2": "BRE", "brescia": "BRE", "germani": "BRE",
    "pal3": "VAR", "varese": "VAR", "openjobmetis": "VAR",
    "pal4": "REG", "reggiana": "REG", "emilia": "REG", "reggio": "REG",
    "pal5": "TRI", "trieste": "TRI",
    # Rezerve (gelecek sezon hazır): Torino henüz Lega'da yok ama dönerse
    "tor": "TORI", "torino": "TORI", "reale": "TORI",  # NBA tor=TOR Raptors ayrı
}

# SPEC-EUROBASKET-001 (2026-06-02): VTB United League 11 aktif takım (2025-26 sezonu).
# Slug prefix "bkvtb-" Polymarket gamma API'den DOĞRULANMIŞ
# (bkvtb-zen-lok-2026-06-03, bkvtb-uni-csk-2026-06-08 vs).
# DİKKAT: Polymarket "csk" kullanıyor — "cska" DEĞİL (3-harf konvansiyonu).
# Minsk 2024-25 ayrıldı (Wikipedia/league listesinde yok); alias future-proof bırakıldı.
_VTB_TEAMS: dict[str, str] = {
    # Polymarket /teams?league=bkvtb endpoint'ten 11 takım DOĞRULANMIŞ (2026-06-03).
    # Minsk listede YOK — eski "min": "MNSK" entry'si kaldırıldı.
    "csk": "CSKA", "cska": "CSKA", "moscow": "CSKA",   # CSKA Moscow
    "zen": "ZEN", "zenit": "ZEN",                      # BC Zenit
    "uni": "UNI", "unics": "UNI", "kazan": "UNI",      # Unics Kazan (Lega "uni"=Treviso, sport_tag ayrı)
    "lok": "LOK", "lokomotiv": "LOK", "kuban": "LOK",  # Lokomotiv Kuban
    "par": "PARMA", "parma": "PARMA", "perm": "PARMA", # Parma Perm (Polymarket alias "par", NOT "parma")
    "avt": "AVT", "avtodor": "AVT",                    # Avtodor
    "mba": "MBA",                                      # MBA Moscow
    "ura": "URA", "uralmash": "URA",                   # Uralmash
    "niz": "NIZ", "nizhny": "NIZ", "novgorod": "NIZ",  # BC Nizhny Novgorod
    "sam": "SAMA", "samara": "SAMA",                   # BC Samara (BSL "sam"=Samsunspor, sport_tag ayrı)
    "eni": "ENI", "enisey": "ENI", "krasnoyarsk": "ENI",  # Enisey Krasnoyarsk
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
