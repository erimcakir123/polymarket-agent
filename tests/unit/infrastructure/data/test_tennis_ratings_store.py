"""TennisRatingsStore — Glicko-2 ratings JSON cache I/O."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.infrastructure.data.tennis_ratings_store import (
    PlayerRating,
    SurfaceRating,
    TennisRatingsStore,
)


@pytest.fixture
def store_path(tmp_path):
    return tmp_path / "tennis_ratings.json"


def _full_rating(rating: float = 1500, rd: float = 350, vol: float = 0.06) -> SurfaceRating:
    return SurfaceRating(rating=rating, rd=rd, volatility=vol)


def _full_player(player_id: str = "p1", player_name: str = "Player A") -> PlayerRating:
    return PlayerRating(
        player_id=player_id, player_name=player_name, tour="atp",
        overall=SurfaceRating(rating=1820, rd=95, volatility=0.05),
        serve_clay=SurfaceRating(rating=1810, rd=98, volatility=0.06),
        serve_grass=SurfaceRating(rating=1800, rd=100, volatility=0.06),
        serve_hard=SurfaceRating(rating=1830, rd=92, volatility=0.05),
        return_clay=SurfaceRating(rating=1750, rd=110, volatility=0.06),
        return_grass=SurfaceRating(rating=1740, rd=112, volatility=0.06),
        return_hard=SurfaceRating(rating=1770, rd=105, volatility=0.05),
        last_match_date="2026-02-15",
        match_count_12mo=87,
    )


def test_save_and_load_full_player_returns_same_data(store_path):
    store = TennisRatingsStore(path=store_path)
    rating = _full_player()
    store.save({"p1": rating})
    loaded = store.load()
    assert "p1" in loaded
    assert loaded["p1"].player_name == "Player A"
    assert loaded["p1"].overall.rating == 1820
    assert loaded["p1"].serve_clay.rd == 98
    assert loaded["p1"].match_count_12mo == 87


def test_load_missing_file_returns_empty_dict(store_path):
    store = TennisRatingsStore(path=store_path)
    loaded = store.load()
    assert loaded == {}


def test_save_atomic_writes_to_disk(store_path):
    store = TennisRatingsStore(path=store_path)
    rating = PlayerRating(
        player_id="p1", player_name="A", tour="atp",
        overall=_full_rating(),
        serve_clay=_full_rating(), serve_grass=_full_rating(), serve_hard=_full_rating(),
        return_clay=_full_rating(), return_grass=_full_rating(), return_hard=_full_rating(),
        last_match_date="2025-01-01",
        match_count_12mo=10,
    )
    store.save({"p1": rating})
    assert store_path.exists()
    data = json.loads(store_path.read_text(encoding="utf-8"))
    assert "p1" in data
    assert data["p1"]["overall"]["rating"] == 1500


def test_load_corrupt_json_returns_empty_dict(tmp_path):
    """Bozuk JSON -> WARNING log + empty dict (ARCH_GUARD K.12)."""
    path = tmp_path / "bad.json"
    path.write_text("not valid json {{{", encoding="utf-8")
    store = TennisRatingsStore(path=path)
    loaded = store.load()
    assert loaded == {}


def test_save_creates_parent_directory_if_missing(tmp_path):
    """Parent dir yoksa save() oluşturmalı."""
    deep_path = tmp_path / "data" / "tennis" / "ratings.json"
    store = TennisRatingsStore(path=deep_path)
    store.save({})
    assert deep_path.parent.exists()
    assert deep_path.exists()


def test_store_save_load_preserves_tour_field(tmp_path: Path) -> None:
    """tour field round-trips through save → load."""
    path = tmp_path / "ratings.json"
    store = TennisRatingsStore(path=path)
    sr = SurfaceRating(rating=1500.0, rd=350.0, volatility=0.06)
    atp_player = PlayerRating(
        player_id="atp:Federer", player_name="Roger Federer", tour="atp",
        overall=sr, serve_clay=sr, serve_grass=sr, serve_hard=sr,
        return_clay=sr, return_grass=sr, return_hard=sr,
        last_match_date="2023-09-01", match_count_12mo=20,
    )
    wta_player = PlayerRating(
        player_id="wta:Swiatek", player_name="Iga Swiatek", tour="wta",
        overall=sr, serve_clay=sr, serve_grass=sr, serve_hard=sr,
        return_clay=sr, return_grass=sr, return_hard=sr,
        last_match_date="2024-09-01", match_count_12mo=55,
    )
    store.save({"atp:Federer": atp_player, "wta:Swiatek": wta_player})
    loaded = store.load()
    assert loaded["atp:Federer"].tour == "atp"
    assert loaded["wta:Swiatek"].tour == "wta"
    assert loaded["atp:Federer"].player_name == "Roger Federer"
    assert loaded["wta:Swiatek"].player_name == "Iga Swiatek"


def test_store_load_missing_tour_field_defaults_to_atp(tmp_path: Path) -> None:
    """Backward compat: old JSON without tour field loads as ATP."""
    path = tmp_path / "ratings.json"
    legacy_json = {
        "Federer": {
            "player_id": "Federer", "player_name": "Federer",
            "overall": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "serve_clay": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "serve_grass": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "serve_hard": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "return_clay": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "return_grass": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "return_hard": {"rating": 1500.0, "rd": 350.0, "volatility": 0.06},
            "last_match_date": "2023-09-01", "match_count_12mo": 20,
        }
    }
    path.write_text(json.dumps(legacy_json), encoding="utf-8")
    store = TennisRatingsStore(path=path)
    loaded = store.load()
    assert loaded["Federer"].tour == "atp"
