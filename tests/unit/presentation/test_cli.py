"""cli.py için birim testler — capsys + tmp_path."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.presentation import cli


@pytest.fixture(autouse=True)
def _use_tmp_logs(tmp_path: Path, monkeypatch):
    """Her test için logs dizini tmp_path'e yönlendir."""
    monkeypatch.setattr(cli, "_LOGS", tmp_path)
    yield


def test_cli_status_cold(capsys, tmp_path: Path) -> None:
    # config.yaml proje kökünde — cli load_config çağırıyor
    # Config load fonk default'larda kalır → initial 1000
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "Mode:" in out
    assert "Bot PID:" in out
    assert "Positions:      0" in out


def test_cli_status_with_positions(capsys, tmp_path: Path) -> None:
    (tmp_path / "positions.json").write_text(json.dumps({
        "positions": {
            "c1": {"size_usdc": 40, "slug": "a-b"},
            "c2": {"size_usdc": 25, "slug": "c-d"},
        },
        "realized_pnl": 8.5,
    }), encoding="utf-8")
    cli.main(["status"])
    out = capsys.readouterr().out
    assert "Positions:      2" in out
    assert "+8.50" in out
    # Bankroll = 1000 + 8.5 - 65 = 943.5
    assert "$943.50" in out


def test_cli_positions_empty(capsys) -> None:
    cli.main(["positions"])
    out = capsys.readouterr().out
    assert "Açık pozisyon yok" in out


def test_cli_positions_with_data(capsys, tmp_path: Path) -> None:
    (tmp_path / "positions.json").write_text(json.dumps({
        "positions": {
            "c1": {"slug": "nba-lal-bos", "direction": "BUY_YES",
                   "entry_price": 0.40, "current_price": 0.55,
                   "size_usdc": 40, "shares": 100, "confidence": "A"},
        },
        "realized_pnl": 0.0,
    }), encoding="utf-8")
    cli.main(["positions"])
    out = capsys.readouterr().out
    assert "nba-lal-bos" in out
    assert "BUY_YES" in out
    # pnl% = (100*0.55 - 40)/40 = 37.5%
    assert "37.5" in out


def test_cli_config_masks_telegram_token(capsys, monkeypatch) -> None:
    from src.config import settings as settings_mod
    from src.config.settings import AppConfig, TelegramConfig

    cfg = AppConfig()
    cfg.telegram = TelegramConfig(enabled=True, bot_token="secretXYZ1234", chat_id="5555")
    monkeypatch.setattr(settings_mod, "load_config", lambda path=None: cfg)
    monkeypatch.setattr(cli, "load_config", lambda: cfg)

    cli.main(["config"])
    out = capsys.readouterr().out
    assert "***1234" in out  # Masked suffix
    assert "secretXYZ" not in out  # Full token leaked olmasın


def test_cli_trades_empty(capsys) -> None:
    cli.main(["trades"])
    out = capsys.readouterr().out
    assert "Kapanan trade yok" in out


def test_cli_trades_with_data(capsys, tmp_path: Path) -> None:
    line = json.dumps({
        "slug": "nba-lal-bos", "condition_id": "0x1", "event_id": "e1", "token_id": "t",
        "sport_tag": "nba", "sport_category": "basketball", "league": "nba",
        "direction": "BUY_YES", "entry_price": 0.40, "size_usdc": 40, "shares": 100,
        "confidence": "A", "bookmaker_prob": 0.55, "anchor_probability": 0.55,
        "num_bookmakers": 10.0, "has_sharp": True,
        "entry_reason": "normal", "entry_timestamp": "2026-04-13T20:00:00Z",
        "exit_price": 0.50, "exit_pnl_usdc": 10.0, "exit_reason": "scale_out",
        "exit_timestamp": "2026-04-13T21:00:00Z",
    })
    (tmp_path / "trade_history.jsonl").write_text(line + "\n", encoding="utf-8")
    cli.main(["trades"])
    out = capsys.readouterr().out
    assert "nba-lal-bos" in out
    assert "scale_out" in out
    assert "+10.00" in out


def test_cli_invalid_command_error() -> None:
    with pytest.raises(SystemExit):
        cli.main(["invalid_cmd"])
