"""NHL totals table loader tests."""
from __future__ import annotations

import json

import pytest

from src.infrastructure.repositories import nhl_totals_repository as repo


def test_load_table_returns_dict(tmp_path, monkeypatch):
    fake = {"metadata": {"total_games": 100}, "totals_over": {"3_4_300_5.5": {"p_over": 0.42}}}
    fake_path = tmp_path / "nhl_empirical_totals_table.json"
    fake_path.write_text(json.dumps(fake), encoding="utf-8")
    monkeypatch.setattr(repo, "TABLE_PATH", fake_path)
    repo.load_table.cache_clear()
    result = repo.load_table()
    assert "totals_over" in result


def test_load_table_raises_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(repo, "TABLE_PATH", tmp_path / "missing.json")
    repo.load_table.cache_clear()
    with pytest.raises(FileNotFoundError):
        repo.load_table()
