"""NHL puck line table loader tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.infrastructure.repositories import nhl_puck_line_repository as repo


def test_load_table_returns_dict(tmp_path, monkeypatch):
    """Table file varsa dict döner."""
    fake_table = {
        "metadata": {"total_games": 100},
        "puck_line_cover": {"3_1_300": {"p_favorite_covers": 0.42, "n_games": 80}},
    }
    fake_path = tmp_path / "nhl_empirical_puck_line_table.json"
    fake_path.write_text(json.dumps(fake_table), encoding="utf-8")
    monkeypatch.setattr(repo, "TABLE_PATH", fake_path)
    repo.load_table.cache_clear()

    result = repo.load_table()
    assert "puck_line_cover" in result
    assert result["puck_line_cover"]["3_1_300"]["p_favorite_covers"] == 0.42


def test_load_table_raises_when_missing(monkeypatch, tmp_path):
    """Dosya yoksa FileNotFoundError."""
    monkeypatch.setattr(repo, "TABLE_PATH", tmp_path / "nonexistent.json")
    repo.load_table.cache_clear()
    with pytest.raises(FileNotFoundError):
        repo.load_table()
