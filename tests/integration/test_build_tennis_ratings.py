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
    import os
    from pathlib import Path

    from scripts.build_tennis_ratings import build_ratings

    csv_path = tmp_path / "atp_matches_2026.csv"
    csv_path.write_text(SAMPLE_CSV, encoding="utf-8")
    out = tmp_path / "ratings.json"

    production_map = Path("data/tennis_surface_map.json")
    before_mtime = production_map.stat().st_mtime if production_map.exists() else None

    build_ratings(tmp_path, out)

    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "Alice" in data
    assert "Bob" in data
    assert data["Alice"]["rating"]["mu"] > 1500  # winner gained rating
    assert data["Bob"]["rating"]["mu"] < 1500

    # surface map ratings'in yaninda (tmp) — production dosyasi KIRLENMEZ
    smap_path = tmp_path / "tennis_surface_map.json"
    assert smap_path.exists()
    assert json.loads(smap_path.read_text(encoding="utf-8")) == {"x": "Hard"}

    # production dosyasinin mtime degismemeli (test kirletmemeli)
    after_mtime = production_map.stat().st_mtime if production_map.exists() else None
    assert before_mtime == after_mtime, "Test production data/tennis_surface_map.json dosyasini kirletti!"


def test_build_ratings_default_surface_output_next_to_ratings_production_untouched(tmp_path):
    """2026-06-10 olayı: surface çıktısı üretim yoluna default'lanıyordu — pytest her
    koşuda data/tennis_ratings_surface.json'ı 2 sahte oyuncuyla (Bob/Alice) ezip canlı
    botun tenis modelini kör etti (531 skip). Surface dosyası output_path'in YANINA
    yazılmalı, üretim dosyası kirlenmemeli."""
    from pathlib import Path

    from scripts.build_tennis_ratings import build_ratings

    csv_path = tmp_path / "atp_matches_2026.csv"
    csv_path.write_text(SAMPLE_CSV, encoding="utf-8")
    out = tmp_path / "ratings.json"

    production_surface = Path("data/tennis_ratings_surface.json")
    before_mtime = production_surface.stat().st_mtime if production_surface.exists() else None

    build_ratings(tmp_path, out)

    tmp_surface = tmp_path / "tennis_ratings_surface.json"
    assert tmp_surface.exists(), "surface ratings output_path'in yanina yazilmali"
    data = json.loads(tmp_surface.read_text(encoding="utf-8"))
    assert "Alice" in data
    assert "Bob" in data

    after_mtime = production_surface.stat().st_mtime if production_surface.exists() else None
    assert before_mtime == after_mtime, (
        "Test uretim data/tennis_ratings_surface.json dosyasini kirletti!"
    )


def test_build_ratings_writes_surface_map(tmp_path, monkeypatch):
    import scripts.build_tennis_ratings as _mod
    from scripts.build_tennis_ratings import build_ratings

    captured: list[dict] = []

    def _fake_save(surface_map, _path=None):  # noqa: ANN001
        captured.append(surface_map)

    monkeypatch.setattr(_mod, "save_surface_map", _fake_save)

    csv_path = tmp_path / "atp_matches_2026.csv"
    csv_path.write_text(SAMPLE_CSV, encoding="utf-8")
    out = tmp_path / "ratings.json"

    build_ratings(tmp_path, out)

    assert len(captured) == 1, "save_surface_map must be called exactly once"
    surface_map = captured[0]
    # SAMPLE_CSV tourney_name="X" → normalized key "x", surface="Hard"
    assert surface_map == {"x": "Hard"}
