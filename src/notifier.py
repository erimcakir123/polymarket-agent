"""Telegram bot notifications."""
from __future__ import annotations
import logging

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    def send(self, message: str, parse_mode: str = "Markdown") -> bool:
        if not self.enabled:
            logger.debug("Telegram notifications disabled")
            return False
        try:
            url = TELEGRAM_API.format(token=self.bot_token)
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
            }, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error("Telegram send failed: %s", e)
            return False

    def format_trade(
        self, question: str, direction: str, size: float, price: float, edge: float
    ) -> str:
        return (
            f"*Trade Opened*\n"
            f"Market: {question}\n"
            f"Direction: `{direction}`\n"
            f"Size: `${size:.2f}`\n"
            f"Price: `${price:.2f}`\n"
            f"Edge: `{edge:.1%}`"
        )

    def format_exit(self, question: str, reason: str, pnl: float) -> str:
        emoji = "+" if pnl >= 0 else ""
        return (
            f"*Position Closed*\n"
            f"Market: {question}\n"
            f"Reason: {reason}\n"
            f"PnL: `{emoji}${pnl:.2f}`"
        )

    def format_daily_summary(
        self, bankroll: float, positions: int, daily_pnl: float, win_rate: float
    ) -> str:
        return (
            f"*Daily Summary*\n"
            f"Bankroll: `${bankroll:.2f}`\n"
            f"Open positions: `{positions}`\n"
            f"Daily PnL: `${daily_pnl:+.2f}`\n"
            f"Win rate: `{win_rate:.0%}`"
        )

    def alert_drawdown(self, bankroll: float, hwm: float) -> str:
        return (
            f"*DRAWDOWN BREAKER ACTIVATED*\n"
            f"Bankroll: `${bankroll:.2f}`\n"
            f"High Water Mark: `${hwm:.2f}`\n"
            f"All trading halted. Manual review required."
        )
