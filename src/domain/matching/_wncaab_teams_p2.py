"""WNCAAB lookup pt2 — Colonial / Horizon / Ivy ... MVC + misc independents.

Bölünme nedeni: ARCH_GUARD §3 (max 400 satır). _wncaab_teams.py'a merge edilir.
"""
from __future__ import annotations


WNCAAB_TEAMS_P2: dict[str, str] = {
    # Colonial Athletic (CAA) - 14 women's teams
    "campbel2": "CCAA", "campbellcaa": "CCAA",
    "char2": "CHCAA", "charlestoncaa": "CHCAA", "cougars3": "CHCAA",
    "drex": "DREX", "drexel": "DREX", "dragons": "DREX",
    "elon": "ELON", "phoenix": "ELON",
    "hamp": "HAMP", "hampton": "HAMP",
    "hofstra": "HOF", "pridehof": "HOF",
    "monm": "MONM", "monmouth": "MONM", "hawks3": "MONM",
    "nce": "NCE", "ncentral": "NCE", "ncwilm": "NCWILM", "uncw": "UNCW", "seahawks": "UNCW",
    "ne": "NE", "northeastern": "NE",
    "smbo": "STO", "stonybrook": "STO", "seawolves": "STO",
    "tow": "TOW", "towson": "TOW", "towsontigers": "TOW",
    "wm": "WM", "williammary": "WM", "tribe": "WM",
    "tow2": "DREXW", "drexcaa": "DREXW",

    # Horizon League - 11 women's teams
    "clev": "CLEV", "clevelandst": "CLEV", "clevelandstate": "CLEV", "vikings2": "CLEV",
    "det": "DET2", "detroit": "DET2", "titans": "DET2",
    "gv": "GV", "greenbay": "GV", "wgreenbay": "GV", "phoenix2": "GV",
    "iuipui": "IUPUI", "iupui": "IUPUI", "jaguars2": "IUPUI",
    "milw": "MILW", "milwaukee": "MILW", "panthers4": "MILW",
    "nku": "NKU", "norkyu": "NKU", "northernky": "NKU", "norse": "NKU",
    "oak": "OAK", "oakland": "OAK", "goldengrizzlies": "OAK",
    "purdfor": "PFW", "purduefw": "PFW", "purduefortwayne": "PFW",
    "robmor": "RMU", "robertmorris": "RMU", "colonials2": "RMU",
    "wis_": "WIS_", "wright": "WRT", "wrightst": "WRT", "wrightstate": "WRT", "raiders2": "WRT",
    "ysu": "YSU", "youngstown": "YSU", "youngstownstate": "YSU", "penguins": "YSU",

    # Ivy League - 8 women's teams
    "brown": "BRWN", "brownbears": "BRWN",
    "col2": "COL2", "columbia": "COL2", "columbialions": "COL2",
    "corn": "COR", "cornell": "COR", "bigred": "COR",
    "dart": "DART", "dartmouth": "DART", "dartmothbig": "DART",
    "harv": "HARV", "harvard": "HARV", "crimson": "HARV",
    "penn": "PENN", "pennsylvania": "PENN", "quakers": "PENN",
    "prin": "PRIN", "princeton": "PRIN", "princetontigers": "PRIN",
    "yale": "YALE", "bulldogs3": "YALE",

    # MEAC (Mid-Eastern Athletic) - 8 women's teams
    "coppin": "COP", "copst": "COP", "coppinstate": "COP", "eagles3": "COP",
    "del2": "DSU", "delst": "DSU", "delawarestate": "DSU", "hornets3": "DSU",
    "howard": "HOW", "howardbison": "HOW", "bison": "HOW",
    "morganst": "MORG", "morgan": "MORG", "morganstate": "MORG", "bearsmorg": "MORG",
    "norfolk": "NORF", "norfolkst": "NORF", "norfolkstate": "NORF", "spartans2": "NORF",
    "nccarat": "NCCU", "nccentralu": "NCCU", "ncentralu": "NCCU", "eagles4": "NCCU",
    "sccst": "SCSU", "scstate": "SCSU", "scarolinast": "SCSU", "scarolinastate": "SCSU", "bulldogs4": "SCSU",
    "umes": "UMES", "marylandes": "UMES", "marylandeasternshore": "UMES", "hawks4": "UMES",

    # NEC (Northeast) - 9 women's teams
    "ccsu": "CCSU", "centralconn": "CCSU", "centralconnst": "CCSU", "centralconnecticut": "CCSU", "blue_devils2": "CCSU",
    "fdu": "FDU", "fairleighdickinson": "FDU", "knights2": "FDU",
    "hbu": "HBU", "houstonchristian": "HBU", "huskies2": "HBU",
    "leMoyne": "LEM", "lemoyne": "LEM", "dolphins": "LEM",
    "liu": "LIU", "longisland": "LIU", "sharks": "LIU",
    "merr": "MERR", "merrimack": "MERR", "warriorsmerr": "MERR",
    "sfny": "SFN", "stfrancisny": "SFN", "terriers": "SFN",
    "scred": "SCT", "saintredhawks": "SCT", "saintredhk": "SCT", "sthomas": "STH", "stthomas": "STH", "tommies": "STH",
    "wagner": "WAG", "seahawkswag": "WAG",

    # Ohio Valley (OVC) - 10 women's teams
    "ausp": "AUS", "austinpeay": "AUS", "governors": "AUS",
    "eky": "EKU", "easternkentucky": "EKU", "colonels": "EKU",
    "eill": "EIU", "easternillinois": "EIU", "panthers5": "EIU",
    "lind": "LIND", "lindenwood": "LIND", "lynx2": "LIND",
    "morhd": "MOR", "moreheadst": "MOR", "moreheadstate": "MOR", "eagles5": "MOR",
    "siue": "SIUE", "siedwardsville": "SIUE", "sillinoisedwardsville": "SIUE",
    "semo": "SEMO", "southeastmissouri": "SEMO", "redhawks2": "SEMO",
    "tnst": "TNST", "tennst": "TNST", "tennesseestate": "TNST", "lady_tigersst": "TNST",
    "tntech": "TNT", "tenntech": "TNT", "tennesseetech": "TNT", "goldeneagles3": "TNT",
    "umsl": "UMSL", "morrisstate": "UMSL", "uttymartin": "UTM", "uttenneessemartin": "UTM", "skyhawks": "UTM",

    # Patriot League - 10 women's teams
    "amer": "AMER", "american": "AMER", "americaneagles": "AMER",
    "armywp": "ARMY", "army": "ARMY", "blackknights": "ARMY",
    "bk": "BUCK", "bucknell": "BUCK", "bisonbk": "BUCK",
    "boston2": "BOS2", "bostonu": "BOS2", "bostonuniversity": "BOS2", "terrierboston": "BOS2",
    "colg": "COLG", "colgate": "COLG", "raidersclg": "COLG",
    "hcr": "HC", "holycross": "HC", "crusaders": "HC",
    "lafay": "LAF", "lafayette": "LAF", "leopards": "LAF",
    "leh": "LEH", "lehigh": "LEH", "mountainhawks": "LEH",
    "lyola": "LOY2", "loyolamd": "LOY2", "greyhounds": "LOY2",
    "navy2": "NAV", "midshipmen2": "NAV",

    # SoCon (Southern Conference) - 10 women's teams
    "cit": "CIT", "citadel": "CIT", "bulldogs5": "CIT",
    "chat": "CHA", "chattanooga": "CHA", "mocs": "CHA",
    "etsu": "ETSU", "easttennst": "ETSU", "easttennesseestate": "ETSU", "buccaneers2": "ETSU",
    "furman": "FUR", "paladins": "FUR",
    "mer": "MER", "mercer": "MER",
    "samford": "SAM", "samfordbulldogs": "SAM",
    "uncg": "UNCG", "ncgreensboro": "UNCG", "ncarolinagreensboro": "UNCG", "spartans3": "UNCG",
    "vmi": "VMI", "keydets": "VMI",
    "wofford": "WOF", "terriers2": "WOF",
    "wcu": "WCU2", "westcarolina": "WCU2", "westerncarolina": "WCU2", "catamounts": "WCU2",

    # Southland - 9 women's teams
    "hcu": "HCU", "houstonchrist": "HCU",
    "incw": "INCW", "incwordcr": "INCW", "incarnateword": "INCW", "cardinals2": "INCW",
    "lit": "LIT", "lamar": "LIT", "cards": "LIT",
    "mcneese": "MCN", "cowboys": "MCN",
    "nicholls": "NICH", "colonels2": "NICH",
    "northwestst": "NWS", "northwesternst": "NWS", "demons": "NWS",
    "norld": "NO", "neworleans": "NO", "privateers": "NO",
    "selastate": "SELA", "southeastlast": "SELA", "southeasternlouisiana": "SELA", "lions2": "SELA",
    "tamuc": "TAMUC", "texasamcommerce": "TAMUC",

    # Summit League - 9 women's teams
    "denver": "DEN", "denverpioneers": "DEN", "pioneersdu": "DEN",
    "ndst": "NDSU", "ndstate": "NDSU", "northdakotastate": "NDSU", "bisonndst": "NDSU",
    "noddakn": "ND2", "north_dak": "ND2", "northdakota": "ND2", "fightinghawks": "ND2",
    "omaha": "OMA", "neomaha": "OMA", "mavericksomaha": "OMA",
    "orl": "ORLR", "oralroberts": "ORLR", "goldeneagles4": "ORLR",
    "stthomas2": "ST2", "stthomasmn": "ST2",
    "sdst": "SDS", "sdstate": "SDS", "southdakotastate": "SDS", "jackrabbits": "SDS",
    "sd2": "SD", "southdakota": "SD", "coyotes": "SD",
    "kc": "KC", "kansascity": "KC", "rooskc": "KC", "roos": "KC",

    # SWAC (Southwestern Athletic) - 12 women's teams
    "alast": "ALST", "alabamast": "ALST", "alabamastate": "ALST", "hornets4": "ALST",
    "alcorn": "ALCN", "alcornst": "ALCN", "alcornstate": "ALCN", "bravesalcorn": "ALCN",
    "alabamamb": "AAMU", "alabamaamu": "AAMU", "bulldogs6": "AAMU",
    "ark_pb": "UAPB", "arkansaspb": "UAPB", "arkansaspinebluff": "UAPB", "lionsuapb": "UAPB",
    "bcc": "BCU", "bethunecookman": "BCU", "wildcats4": "BCU",
    "famu": "FAMU", "floridaamu": "FAMU", "rattlers": "FAMU",
    "gram": "GRAM", "grambling": "GRAM", "gramblingst": "GRAM", "tigers3": "GRAM",
    "jackson_st": "JKST", "jacksonst": "JKST", "jacksonstate": "JKST", "tigers4": "JKST",
    "msvst": "MVSU", "miss_valley": "MVSU", "mississippivalley": "MVSU", "delta_devils": "MVSU",
    "prairieview": "PV", "pvamu": "PV", "panthers6": "PV",
    "subr": "SUBR", "southernu": "SUBR", "southernuniversity": "SUBR", "jaguars2sub": "SUBR",
    "tsu": "TXSU", "texasso": "TXSU", "texassouthern": "TXSU", "tigers5": "TXSU",

    # WAC (Western Athletic) - 11 women's teams
    "abch": "ABCH", "abchristian": "ABCH", "abilenechristian": "ABCH", "wildcats5": "ABCH",
    "cbu": "CBU", "californiabap": "CBU", "californiabaptist": "CBU", "lancersb": "CBU",
    "gv2": "GCU", "grandcanyon": "GCU", "antelopes": "GCU",
    "ssmary": "SMU3", "stmaryswac": "SMU3",
    "stf": "STF", "stephenf": "STF", "stephenfaustin": "STF", "ladyjacks": "STF", "lumberjacks2": "STF",
    "tarleton": "TAR", "texans": "TAR",
    "uca": "UCA", "centralarkansas": "UCA", "sugar_bears": "UCA", "sugarbears": "UCA",
    "utah_tech": "UT", "utahtech": "UT", "trailblazers": "UT",
    "uta": "UTAW", "utarlington": "UTAW", "mavericksta": "UTAW",
    "utrgv": "UTRGV", "utexrgv": "UTRGV", "utriograndevalley": "UTRGV", "vaqueros": "UTRGV",
    "uvu": "UVU", "utahvalley": "UVU", "wolverines2": "UVU",

    # ASUN (A-Sun) - 12 women's teams
    "austin": "AP", "austinpb": "AP",
    "bell": "BEL", "bellarmine": "BEL", "knights3": "BEL",
    "centarkst": "CARK", "centarkansas": "CARK", "centralark": "CARK",
    "etrkst": "ETSU2",
    "ehilill": "ESH", "eshillhillcrest": "ESH",
    "fgcu": "FGCU", "florida_gulf": "FGCU", "floridagulfcoast": "FGCU", "eagles6": "FGCU",
    "ftbn": "FBNU", "fbynnk": "FBNU",
    "jax_": "JAX", "jacksonville": "JAX", "dolphins2": "JAX",
    "jville_st": "JAXS",
    "kennest": "KSU2", "kennesawst": "KSU2", "kennesawstate": "KSU2", "owls2": "KSU2",
    "lipscomb": "LIP", "bisonsl": "LIP",
    "nflorida": "UNF", "northflorida": "UNF", "ospreys": "UNF",
    "queens": "QUEENS", "queensnc": "QUEENS", "queenscarolina": "QUEENS",
    "stetson": "STET", "hatters": "STET",
    "uwg": "UWG", "westgeorgia": "UWG", "wolves2": "UWG",

    # Northeast / MAAC - additional women's teams (MAAC ~11 teams)
    "canisius": "CAN", "goldengriffins": "CAN", "griffs": "CAN",
    "fairf": "FAIR", "fairfield": "FAIR", "stagsf": "FAIR",
    "iona": "IONA", "gaels": "IONA",
    "manhat": "MAN", "manhattan": "MAN", "jaspers": "MAN",
    "marist": "MARIST", "redfoxes": "MARIST",
    "monm2": "MON2", "monmouthmaac": "MON2",
    "mount": "MSM", "mtstmary": "MSM", "mountsaintmarys": "MSM", "mountaineers3": "MSM",
    "niag": "NIAG", "niagara": "NIAG", "purpleeagles": "NIAG",
    "qu": "QPC", "quinn": "QPC", "quinnipiac": "QPC", "bobcats4": "QPC",
    "rider": "RID", "broncs": "RID",
    "siena": "SIE", "saints": "SIE",

    # Southland additions & misc independents
    "bell2": "BELC", "bellarcal": "BELC", "bellarmineind": "BELC",
    "chic": "CSC", "chicagost": "CSC", "chicagostate": "CSC",
    "njit": "NJIT", "newjerseytech": "NJIT", "highlanders2": "NJIT",
    "saintfran": "SFI", "stfrancisin": "SFI", "stfrancispa": "SFP", "redflash": "SFP",
    "stbon2": "STB2", "stbonaventure2": "STB2",
    "vmh": "VMI2",

    # Independents and unique programs not in the above
    "uic": "UIC", "illchicago": "UIC", "illinoischicago": "UIC", "flames2": "UIC",
    "csaramento": "SAC2", "sacstate2": "SAC2",
    "evans": "EVAN", "evansville": "EVAN", "purpleaces": "EVAN",
    "udayton": "DAY2", "daytonwomen": "DAY2",
    "wofford2": "WOF2",
    "morris": "MOR2", "morris_st": "MOR2",
    "centarknst": "CARS",

    # MVC (Missouri Valley Conference) - 12 women's teams
    "brad": "BRAD", "bradley": "BRAD", "bradleybraves": "BRAD",
    "bel": "BEL2", "belmont": "BEL2", "belmontbruins": "BEL2",
    "drak": "DRAKE", "drake": "DRAKE", "drakebulldogs": "DRAKE",
    "evansv": "EVA2", "evansville2": "EVA2", "purpleaces2": "EVA2",
    "ilstu": "ILSU", "illinoisst": "ILSU", "illinoisstate": "ILSU", "redbirds": "ILSU",
    "indst": "INST", "indianast": "INST", "indianastate": "INST", "sycamores": "INST",
    "mursta": "MUR", "murrayst": "MUR", "murraystate": "MUR", "racers": "MUR",
    "ncolombia": "MIZZ2",
    "niu_mvc": "NIU2",
    "ucwm": "UCM", "centralmissouri": "UCM",
    "uniow": "UNI", "northerniowa": "UNI", "uniowapanthers": "UNI",
    "valpo": "VAL", "valparaiso": "VAL", "beacons": "VAL",
}
