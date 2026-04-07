"""Check data coverage for all Polymarket sports leagues."""
import requests
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.matching.odds_sport_keys import slug_to_odds_key

resp = requests.get("https://gamma-api.polymarket.com/sports", timeout=15)
sports = resp.json()

ODDS_API = {
    "basketball_nba","basketball_wnba","basketball_ncaab",
    "icehockey_nhl","icehockey_ahl",
    "baseball_mlb","baseball_kbo","baseball_npb",
    "americanfootball_nfl","americanfootball_ncaaf","americanfootball_cfl",
    "soccer_epl","soccer_efl_champ","soccer_fa_cup","soccer_england_efl_cup",
    "soccer_england_league1","soccer_england_league2",
    "soccer_spain_la_liga","soccer_spain_segunda_division","soccer_spain_copa_del_rey",
    "soccer_germany_bundesliga","soccer_germany_bundesliga2","soccer_germany_dfb_pokal",
    "soccer_italy_serie_a","soccer_italy_serie_b","soccer_italy_coppa_italia",
    "soccer_france_ligue_one","soccer_france_ligue_two","soccer_france_coupe_de_france",
    "soccer_netherlands_eredivisie","soccer_portugal_primeira_liga",
    "soccer_turkey_super_league","soccer_spl","soccer_belgium_first_div",
    "soccer_denmark_superliga","soccer_norway_eliteserien","soccer_sweden_allsvenskan",
    "soccer_russia_premier_league","soccer_greece_super_league","soccer_austria_bundesliga",
    "soccer_switzerland_superleague","soccer_poland_ekstraklasa",
    "soccer_czech_republic_first_league","soccer_finland_veikkausliiga",
    "soccer_croatia_hnl","soccer_romania_liga_1","soccer_ukraine_premier_league",
    "soccer_usa_mls","soccer_argentina_primera_division",
    "soccer_brazil_campeonato","soccer_brazil_serie_b","soccer_mexico_ligamx",
    "soccer_chile_campeonato","soccer_colombia_primera_a","soccer_australia_aleague",
    "soccer_korea_kleague1","soccer_japan_j_league","soccer_china_superleague",
    "soccer_peru_primera_division","soccer_uruguay_primera_division",
    "soccer_ecuador_primera_a","soccer_paraguay_primera_division",
    "soccer_bolivia_primera_division","soccer_india_super_league",
    "soccer_saudi_arabia_pro_league","soccer_egypt_premier_league",
    "soccer_conmebol_copa_libertadores","soccer_conmebol_copa_sudamericana",
    "soccer_uefa_champs_league","soccer_uefa_europa_league","soccer_uefa_europa_conference_league",
    "tennis_atp_french_open","tennis_atp_us_open","tennis_atp_wimbledon",
    "tennis_atp_australian_open","tennis_atp_monte_carlo_masters",
    "tennis_atp_madrid_open","tennis_atp_rome","tennis_atp_shanghai",
    "tennis_wta_french_open","tennis_wta_us_open","tennis_wta_australian_open",
    "mma_mixed_martial_arts","boxing_boxing",
    "cricket_ipl","cricket_test_match","cricket_odi","cricket_t20i",
    "rugbyunion_six_nations","rugbyunion_premiership","rugbyleague_nrl",
    "aussierules_afl",
    "golf_pga_tour","golf_lpga_tour","golf_liv_tour",
}

ESPN = {
    "nba","nhl","mlb","nfl","wnba","mls","ncaab","ncaaf",
    "eng.1","eng.2","eng.3","eng.4","eng.5","eng.fa","eng.league_cup",
    "esp.1","esp.2","ita.1","ita.2","ger.1","ger.2","fra.1","fra.2",
    "ned.1","por.1","tur.1","sco.1","bel.1","aut.1","gre.1","den.1",
    "nor.1","swe.1","arg.1","bra.1","bra.2","col.1","chi.1","mex.1",
    "per.1","bol.1","uru.1","ecu.1","par.1","ven.1","jpn.1","chn.1",
    "ksa.1","ind.1","aus.1","rsa.1","cze.1","rou.1","irl.1","cyp.1",
    "sui.1","pol.1","ukr.1",
    "uefa.champions","uefa.europa","uefa.europa.conf",
    "conmebol.libertadores","conmebol.sudamericana",
}

CODE_ESPN = {
    "nba":"nba","nhl":"nhl","mlb":"mlb","nfl":"nfl","wnba":"wnba","mls":"mls",
    "epl":"eng.1","efl":"eng.2","elc":"eng.league_cup","efa":"eng.fa",
    "lal":"esp.1","cdr":"esp.1","cde":"esp.1",
    "bun":"ger.1","dfb":"ger.1","sea":"ita.1","ser":"ita.1",
    "fl1":"fra.1","fr2":"fra.2","cof":"fra.1",
    "ere":"ned.1","por":"por.1","tur":"tur.1","sco":"sco.1",
    "bel":"bel.1","aut":"aut.1","gre":"gre.1","den":"den.1",
    "nor":"nor.1","swe":"swe.1",
    "arg":"arg.1","bra":"bra.1","bra2":"bra.2",
    "col":"col.1","col1":"col.1","chi":"chi.1","chi1":"chi.1",
    "mex":"mex.1","ucl":"uefa.champions","uel":"uefa.europa","uecl":"uefa.europa.conf",
    "lib":"conmebol.libertadores","sud":"conmebol.sudamericana","con":"conmebol.libertadores",
    "per1":"per.1","bol1":"bol.1","ecu":"ecu.1","uru":"uru.1","par":"par.1","ven":"ven.1",
    "ind":"ind.1","aus":"aus.1","jpn":"jpn.1","jap":"jpn.1",
    "spl":"ksa.1","chn":"chn.1","rsa":"rsa.1",
    "cze1":"cze.1","rou1":"rou.1","ukr1":"ukr.1","sui":"sui.1","pol":"pol.1",
    "cfb":"ncaaf","cbb":"ncaab","ncaab":"ncaab",
    "egy1":"egy.1","mar1":"mar.1","rus":"rus.1",
}

CRICKET = {"ipl","cricipl","cricps","cricpsl","crict20blast","cricbpl",
    "criccpl","cricmlc","cricsa20","cricsm","cricss","crict20lpl",
    "test","t20","odi","crint","craus","creng","crind","crpak","crnew","crban","crsou"}

results = []
for s in sorted(sports, key=lambda x: x.get("sport","")):
    code = s.get("sport","")
    odds_key = slug_to_odds_key(code)
    has_odds = bool(odds_key and odds_key in ODDS_API)
    espn_id = CODE_ESPN.get(code, "")
    has_espn = espn_id in ESPN
    has_cricket = code in CRICKET or code.startswith("cric") or code.startswith("cr")

    sources = []
    if has_espn: sources.append("ESPN(DK)")
    if has_odds: sources.append("OddsAPI(Pin)")
    if has_cricket: sources.append("CricketAPI")

    if has_odds and (has_espn or has_cricket):
        tier = "A"
    elif len(sources) >= 2:
        tier = "A"
    elif sources:
        tier = "B+"
    else:
        tier = "X"

    results.append((code, tier, sources))

for t, label in [("A","A-CAPABLE"), ("B+","B+ ONLY"), ("X","NO DATA")]:
    items = [r for r in results if r[1] == t]
    print(f"\n=== {label} ({len(items)}) ===")
    for code, _, sources in items:
        print(f"  {code:12s} | {' + '.join(sources)}")
