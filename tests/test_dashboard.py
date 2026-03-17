import pytest


def test_create_app_returns_flask():
    from src.dashboard import create_app
    app = create_app()
    assert app is not None
    assert hasattr(app, "test_client")


def test_api_trades_returns_json(tmp_path):
    import json
    trades_file = tmp_path / "trades.jsonl"
    trades_file.write_text(json.dumps({"market": "test", "action": "BUY"}) + "\n")
    from src.dashboard import create_app
    app = create_app(trades_file=str(trades_file))
    client = app.test_client()
    resp = client.get("/api/trades")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["market"] == "test"


def test_index_returns_html():
    from src.dashboard import create_app
    app = create_app()
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
