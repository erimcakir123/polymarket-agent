"""TmlCsvClient — TML-Database backup parser."""
from __future__ import annotations

import pytest

from src.infrastructure.data.tml_csv_client import TmlCsvClient


TML_SAMPLE = """tourney_id,tourney_name,surface,draw_size,tourney_level,indoor,tourney_date,match_num,winner_id,winner_seed,winner_entry,winner_name,winner_hand,winner_ht,winner_ioc,winner_age,winner_rank,winner_rank_points,loser_id,loser_seed,loser_entry,loser_name,loser_hand,loser_ht,loser_ioc,loser_age,loser_rank,loser_rank_points,score,best_of,round,minutes,w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced
2026-1,Auckland,Hard,32,A,F,20260105,1,p1,1,,Player X,R,185,USA,30.0,5,500,p2,,,Player Y,L,180,ESP,28.0,15,200,6-2 6-3,3,F,80,4,1,55,35,28,15,10,2,3,2,2,50,32,20,10,8,4,6
"""


@pytest.fixture
def csv_dir(tmp_path):
    d = tmp_path / "tml"
    d.mkdir()
    (d / "2026.csv").write_text(TML_SAMPLE)
    return d


def test_load_year_valid_csv_returns_parsed_match(csv_dir):
    client = TmlCsvClient(cache_dir=csv_dir)
    matches = client.load_year(2026)
    assert len(matches) == 1
    m = matches[0]
    assert m.tourney_name == "Auckland"
    assert m.winner_name == "Player X"
    assert m.score == "6-2 6-3"
    # TML aynı schema dönmeli (extra 'indoor' field skip, SackmannMatch'a uyumlu)
    assert m.w_ace == 4


def test_load_year_missing_returns_empty(tmp_path):
    client = TmlCsvClient(cache_dir=tmp_path)
    matches = client.load_year(2099)
    assert matches == []


def test_load_year_indoor_field_ignored(csv_dir):
    """TML schema has 'indoor' column; should be silently dropped."""
    client = TmlCsvClient(cache_dir=csv_dir)
    matches = client.load_year(2026)
    assert len(matches) == 1
    # If 'indoor' was passed to SackmannMatch ctor, ValueError on extra arg
    # Test passes => no spurious fields leak through


def test_load_year_malformed_date_skips_row_returns_empty(tmp_path):
    """Bad tourney_date -> ValueError caught -> row skipped, list empty."""
    bad_csv = TML_SAMPLE.replace("20260105", "BADDATE")
    csv_dir = tmp_path / "tml"
    csv_dir.mkdir()
    (csv_dir / "2026.csv").write_text(bad_csv)
    client = TmlCsvClient(cache_dir=csv_dir)
    matches = client.load_year(2026)
    assert matches == []


def test_load_year_tourney_date_parsed_as_datetime(csv_dir):
    client = TmlCsvClient(cache_dir=csv_dir)
    matches = client.load_year(2026)
    m = matches[0]
    assert m.match_date.year == 2026
    assert m.match_date.month == 1
    assert m.match_date.day == 5
