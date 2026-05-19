"""TennisRatingsStore — Glicko-2 ratings JSON cache I/O."""
from __future__ import annotations

import json

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
        player_id=player_id, player_name=player_name,
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
        player_id="p1", player_name="A",
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
