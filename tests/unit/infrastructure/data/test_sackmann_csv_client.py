"""SackmannCsvClient için birim test."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.infrastructure.data.sackmann_csv_client import (
    SackmannCsvClient,
    SackmannMatch,
)


SAMPLE_CSV = """tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,match_num,winner_id,winner_seed,winner_entry,winner_name,winner_hand,winner_ht,winner_ioc,winner_age,loser_id,loser_seed,loser_entry,loser_name,loser_hand,loser_ht,loser_ioc,loser_age,score,best_of,round,minutes,w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,winner_rank,winner_rank_points,loser_rank,loser_rank_points
2025-580,Adelaide,Hard,32,A,20250105,1,p1,1,,Player A,R,185,USA,30.0,p2,,,Player B,L,180,ESP,28.0,6-3 6-4,3,F,95,5,2,60,40,30,15,10,3,4,3,1,55,35,22,10,8,5,7,5,500,15,200
"""


@pytest.fixture
def csv_dir(tmp_path):
    csv_dir = tmp_path / "sackmann"
    csv_dir.mkdir()
    (csv_dir / "atp_matches_2025.csv").write_text(SAMPLE_CSV)
    return csv_dir


def test_load_year_valid_csv_returns_parsed_match(csv_dir):
    client = SackmannCsvClient(cache_dir=csv_dir)
    matches = client.load_year(2025)
    assert len(matches) == 1
    m = matches[0]
    assert m.tourney_name == "Adelaide"
    assert m.surface == "Hard"
    assert m.winner_name == "Player A"
    assert m.loser_name == "Player B"
    assert m.score == "6-3 6-4"
    assert m.best_of == 3
    assert m.w_ace == 5
    assert m.w_svpt == 60
    assert m.w_1stIn == 40
    assert m.w_bpSaved == 3
    assert m.winner_rank == 5
    assert m.loser_rank == 15


def test_load_year_missing_returns_empty(tmp_path):
    client = SackmannCsvClient(cache_dir=tmp_path)
    matches = client.load_year(2099)
    assert matches == []


def test_load_years_two_years_returns_combined_list(csv_dir):
    # Aynı CSV'yi 2024 olarak da kopyala
    (csv_dir / "atp_matches_2024.csv").write_text(SAMPLE_CSV)
    client = SackmannCsvClient(cache_dir=csv_dir)
    matches = client.load_years([2024, 2025])
    assert len(matches) == 2


def test_load_year_tourney_date_parsed_as_datetime(csv_dir):
    client = SackmannCsvClient(cache_dir=csv_dir)
    matches = client.load_year(2025)
    m = matches[0]
    # tourney_date 20250105 → datetime parse edilebilmeli
    assert m.match_date.year == 2025
    assert m.match_date.month == 1
    assert m.match_date.day == 5


def test_load_year_malformed_date_skips_row_returns_empty(tmp_path):
    """Bad tourney_date → ValueError caught → row skipped, list empty."""
    bad_csv = SAMPLE_CSV.replace("20250105", "BADDATE")
    csv_dir = tmp_path
    (csv_dir / "atp_matches_2030.csv").write_text(bad_csv)
    client = SackmannCsvClient(cache_dir=csv_dir)
    matches = client.load_year(2030)
    assert matches == []


# ── Challenger loading tests ────────────────────────────────────────────────


CHALLENGER_CSV = """tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,match_num,winner_id,winner_seed,winner_entry,winner_name,winner_hand,winner_ht,winner_ioc,winner_age,loser_id,loser_seed,loser_entry,loser_name,loser_hand,loser_ht,loser_ioc,loser_age,score,best_of,round,minutes,w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,winner_rank,winner_rank_points,loser_rank,loser_rank_points
chall-001,Challenger Buenos Aires,Clay,32,C,20250110,1,c1,1,,Challenger A,R,185,ARG,25.0,c2,,,Challenger B,L,180,ESP,27.0,6-4 6-3,3,F,90,4,1,55,38,28,12,9,2,3,2,1,50,32,20,9,7,4,6,80,150,95,130
atp-001,Australian Open,Hard,128,G,20250106,1,p1,1,,Player A,R,190,USA,28.0,p2,,,Player B,L,182,GBR,30.0,7-5 6-4 6-3,5,R128,130,6,2,65,45,33,18,11,4,5,3,1,60,40,24,12,9,5,8,5,500,18,200
"""


@pytest.fixture
def chall_csv_dir(tmp_path):
    csv_dir = tmp_path / "sackmann"
    csv_dir.mkdir()
    (csv_dir / "atp_matches_qual_chall_2025.csv").write_text(CHALLENGER_CSV)
    return csv_dir


def test_load_challenger_year_returns_only_challenger_level_matches(chall_csv_dir):
    """load_challenger_year filters to tourney_level='C' only."""
    client = SackmannCsvClient(cache_dir=chall_csv_dir)
    matches = client.load_challenger_year(2025)
    assert len(matches) == 1
    m = matches[0]
    assert m.tourney_level == "C"
    assert m.winner_name == "Challenger A"
    assert m.loser_name == "Challenger B"


def test_load_challenger_year_missing_returns_empty(tmp_path):
    client = SackmannCsvClient(cache_dir=tmp_path)
    matches = client.load_challenger_year(2099)
    assert matches == []


def test_load_challenger_years_combines_years(chall_csv_dir):
    """load_challenger_years returns combined sorted list across years."""
    # Copy same file for 2024 to simulate two years
    src = chall_csv_dir / "atp_matches_qual_chall_2025.csv"
    (chall_csv_dir / "atp_matches_qual_chall_2024.csv").write_text(src.read_text())
    client = SackmannCsvClient(cache_dir=chall_csv_dir)
    matches = client.load_challenger_years([2024, 2025])
    # 1 challenger match per file × 2 = 2
    assert len(matches) == 2
    assert all(m.tourney_level == "C" for m in matches)
