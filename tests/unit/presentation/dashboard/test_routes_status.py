"""/api/status endpoint — yeni şema testi."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from flask import Flask

from src.config.settings import AppConfig
from src.presentation.dashboard.routes import register_routes


@pytest.fixture
def client(tmp_path: Path):
    """bot_status.json ile birlikte flask test client."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "agent.pid").write_text("99999", encoding="utf-8")  # alive=false'a düşecek
    app = Flask(__name__)
    config = AppConfig()
    register_routes(app, config, logs_dir)
    return app.test_client(), tmp_path


def test_api_status_returns_new_fields_when_bot_status_present(client):
    c, tmp_path = client
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "bot_status.json").write_text(json.dumps({
        "mode": "dry_run",
        "cycle": "heavy",
        "stage": "scanning",
        "stage_at": "2026-04-15T12:00:00+00:00",
        "next_heavy_at": "2026-04-15T12:30:00+00:00",
        "light_alive": True,
    }), encoding="utf-8")

    r = c.get("/api/status")
    data = r.get_json()
    assert data["cycle"] == "heavy"
    assert data["stage"] == "scanning"
    assert data["stage_at"] == "2026-04-15T12:00:00+00:00"
    assert data["next_heavy_at"] == "2026-04-15T12:30:00+00:00"
    assert data["light_alive"] is True


def test_api_status_returns_nulls_when_bot_status_missing(client):
    c, _ = client
    r = c.get("/api/status")
    data = r.get_json()
    assert data["cycle"] is None
    assert data["stage"] is None
    assert data["stage_at"] is None
    assert data["next_heavy_at"] is None
    assert data["light_alive"] is False
