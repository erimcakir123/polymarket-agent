"""Sackmann CSV loader — bir CSV string'i alıp MatchRecord listesine çevirir."""
from io import StringIO

from src.infrastructure.data.sackmann_csv_loader import load_matches_from_csv


SAMPLE_CSV = (
    "tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,match_num,"
    "winner_id,winner_seed,winner_entry,winner_name,winner_hand,winner_ht,winner_ioc,winner_age,"
    "loser_id,loser_seed,loser_entry,loser_name,loser_hand,loser_ht,loser_ioc,loser_age,"
    "score,best_of,round,minutes,"
    "w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,"
    "l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,"
    "winner_rank,winner_rank_points,loser_rank,loser_rank_points\n"
    "2026-9900,United Cup,Hard,18,A,20260105,400,128034,9,,Hurkacz,R,196,POL,28.8,"
    "104527,16,,Wawrinka,R,183,SUI,40.7,6-3 3-6 6-3,3,F,114,"
    "18,0,90,63,52,9,14,8,9,10,1,78,49,38,15,13,5,7,83,710,156,397\n"
)


def test_load_basic_match():
    records = load_matches_from_csv(StringIO(SAMPLE_CSV))
    assert len(records) == 1
    m = records[0]
    assert m.winner_name == "Hurkacz"
    assert m.loser_name == "Wawrinka"
    assert m.surface == "Hard"
    assert m.w_svpt == 90 and m.w_1st_in == 63 and m.w_1st_won == 52


def test_skips_invalid_rows():
    bad = SAMPLE_CSV + "incomplete,row\n"
    records = load_matches_from_csv(StringIO(bad))
    assert len(records) == 1  # bad row silently dropped (infra boundary)


ILKLEY_CSV = (
    "tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,match_num,"
    "winner_id,winner_seed,winner_entry,winner_name,winner_hand,winner_ht,winner_ioc,winner_age,"
    "loser_id,loser_seed,loser_entry,loser_name,loser_hand,loser_ht,loser_ioc,loser_age,"
    "score,best_of,round,minutes,"
    "w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,"
    "l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,"
    "winner_rank,winner_rank_points,loser_rank,loser_rank_points\n"
    "2026-0700,Ilkley,Grass,32,A,20260617,100,104925,1,,Murray,R,190,GBR,38.9,"
    "144195,,,,Smith,R,185,GBR,30.1,6-4 6-3,3,R32,65,"
    "8,2,60,42,35,10,9,3,4,5,3,55,36,25,8,8,2,5,12,950,88,450\n"
)


def test_tourney_name_parsed():
    records = load_matches_from_csv(StringIO(ILKLEY_CSV))
    assert len(records) == 1
    m = records[0]
    assert m.tourney_name == "Ilkley"
    assert m.surface == "Grass"
