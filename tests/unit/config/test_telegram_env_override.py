"""Telegram credentials .env'den otomatik override (SPEC-TG-001 Task 1).

config.yaml'da token/chat_id boş bırakılırsa .env'den TELEGRAM_BOT_TOKEN +
TELEGRAM_CHAT_ID auto-load + ikisi de varsa enabled=True (boot deneyimini
basitleştirir — kullanıcı sadece .env'e secret yazar, config'i değiştirmez).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.config.settings import load_config


def test_telegram_credentials_loaded_from_env(tmp_path: Path) -> None:
    cfg_file = tmp_path / "test.yaml"
    cfg_file.write_text(
        "mode: paper\n"
        "initial_bankroll: 1000.0\n"
        "telegram:\n"
        "  enabled: false\n"
        "  bot_token: ''\n"
        "  chat_id: ''\n"
    )
    with patch.dict(
        "os.environ",
        {"TELEGRAM_BOT_TOKEN": "env-test-token", "TELEGRAM_CHAT_ID": "env-test-chat"},
    ):
        cfg = load_config(cfg_file)
    assert cfg.telegram.bot_token == "env-test-token"
    assert cfg.telegram.chat_id == "env-test-chat"
    assert cfg.telegram.enabled is True


def test_explicit_yaml_token_wins_over_env(tmp_path: Path) -> None:
    """config.yaml'da değer varsa .env override etmez."""
    cfg_file = tmp_path / "test.yaml"
    cfg_file.write_text(
        "mode: paper\n"
        "initial_bankroll: 1000.0\n"
        "telegram:\n"
        "  enabled: true\n"
        "  bot_token: 'explicit-token'\n"
        "  chat_id: 'explicit-chat'\n"
    )
    with patch.dict(
        "os.environ",
        {"TELEGRAM_BOT_TOKEN": "env-token-ignored", "TELEGRAM_CHAT_ID": "env-chat-ignored"},
    ):
        cfg = load_config(cfg_file)
    assert cfg.telegram.bot_token == "explicit-token"
    assert cfg.telegram.chat_id == "explicit-chat"


def test_missing_env_keeps_disabled(tmp_path: Path) -> None:
    """Hem yaml boş hem env yok → enabled False (no-op, hata yok)."""
    cfg_file = tmp_path / "test.yaml"
    cfg_file.write_text(
        "mode: paper\n"
        "initial_bankroll: 1000.0\n"
        "telegram:\n"
        "  enabled: false\n"
        "  bot_token: ''\n"
        "  chat_id: ''\n"
    )
    with patch.dict("os.environ", {}, clear=True):
        cfg = load_config(cfg_file)
    assert cfg.telegram.bot_token == ""
    assert cfg.telegram.chat_id == ""
    assert cfg.telegram.enabled is False
