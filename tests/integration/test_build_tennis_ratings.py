"""build_tennis_ratings — integration test: minik CSV → ratings.json üretir."""
import json


SAMPLE_CSV = (
    "tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,match_num,"
    "winner_id,winner_seed,winner_entry,winner_name,winner_hand,winner_ht,winner_ioc,winner_age,"
    "loser_id,loser_seed,loser_entry,loser_name,loser_hand,loser_ht,loser_ioc,loser_age,"
    "score,best_of,round,minutes,"
    "w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,"
    "l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,"
    "winner_rank,winner_rank_points,loser_rank,loser_rank_points\n"
    "x,X,Hard,32,A,20260101,1,1,,,Alice,R,180,USA,25,2,,,Bob,R,180,ESP,26,"
    "6-3 6-4,3,F,90,5,1,80,55,40,15,10,3,5,4,2,75,45,30,10,10,5,8,1,100,2,90\n"
)


def test_build_creates_ratings_json(tmp_path):
    from scripts.build_tennis_ratings import build_ratings

    csv_path = tmp_path / "atp_matches_2026.csv"
    csv_path.write_text(SAMPLE_CSV, encoding="utf-8")
    out = tmp_path / "ratings.json"

    build_ratings(tmp_path, out)

    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "Alice" in data
    assert "Bob" in data
    assert data["Alice"]["rating"]["mu"] > 1500  # winner gained rating
    assert data["Bob"]["rating"]["mu"] < 1500
