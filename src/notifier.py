"""Telegram bot: notifications + command polling (/stop, /pause, /resume, /status)."""
from __future__ import annotations

import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
PAUSE_FILE = Path("logs/AWAITING_APPROVAL")


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bool(bot_token and chat_id)
        self._last_update_id: int = 0

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def send(self, message: str, parse_mode: str = "Markdown") -> bool:
        if not self.enabled:
            logger.debug("Telegram notifications disabled")
            return False
        try:
            url = TELEGRAM_API.format(token=self.bot_token, method="sendMessage")
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
            }, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error("Telegram send failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Command polling
    # ------------------------------------------------------------------

    def poll_commands(self) -> list[str]:
        """Poll Telegram for new commands. Returns list of command strings."""
        if not self.enabled:
            return []
        try:
            url = TELEGRAM_API.format(token=self.bot_token, method="getUpdates")
            resp = requests.get(url, params={
                "offset": self._last_update_id + 1,
                "timeout": 1,
            }, timeout=5)
            if resp.status_code != 200:
                return []

            commands = []
            for update in resp.json().get("result", []):
                self._last_update_id = update["update_id"]
                msg = update.get("message", {})
                text = msg.get("text", "").strip().lower()
                chat_id = str(msg.get("chat", {}).get("id", ""))
                # Only accept commands from our chat
                if chat_id == self.chat_id and text.startswith("/"):
                    commands.append(text)
            return commands
        except Exception as e:
            logger.debug("Telegram poll error: %s", e)
            return []

    def handle_commands(self, agent) -> None:
        """Process pending Telegram commands."""
        for cmd in self.poll_commands():
            if cmd == "/stop":
                self.send("Bot durduruluyor...")
                agent.running = False
                logger.info("Telegram /stop command received")

            elif cmd == "/pause":
                PAUSE_FILE.parent.mkdir(parents=True, exist_ok=True)
                PAUSE_FILE.write_text("Paused via /pause command", encoding="utf-8")
                self.send("Bot duraklatildi. /resume ile devam edin.")
                logger.info("Telegram /pause command received")

            elif cmd == "/resume":
                if PAUSE_FILE.exists():
                    PAUSE_FILE.unlink()
                    self.send("Bot devam ediyor.")
                    logger.info("Telegram /resume command received")
                else:
                    self.send("Bot zaten calisiyor.")

            elif cmd == "/status":
                positions = len(agent.portfolio.positions)
                bankroll = agent.portfolio.bankroll
                paused = PAUSE_FILE.exists()
                budget = agent.ai.budget_remaining_usd
                self.send(
                    f"*Bot Durumu*\n"
                    f"Mod: `{agent.config.mode.value}`\n"
                    f"Bakiye: `${bankroll:.2f}`\n"
                    f"Acik pozisyon: `{positions}`\n"
                    f"API butce kalan: `${budget:.2f}`\n"
                    f"Durum: `{'DURAKLATILDI' if paused else 'CALISIYOR'}`\n"
                    f"Toplam bet: `{agent.bets_since_approval}`/10"
                )

            else:
                self.send(f"Bilinmeyen komut: {cmd}\nKomutlar: /stop /pause /resume /status")

    # ------------------------------------------------------------------
    # Message formatters
    # ------------------------------------------------------------------

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

    def format_suspicious_bet(
        self, question: str, direction: str, size: float, edge: float, reason: str
    ) -> str:
        return (
            f"*Supheli Bet*\n"
            f"Market: {question}\n"
            f"Direction: `{direction}`\n"
            f"Size: `${size:.2f}`\n"
            f"Edge: `{edge:.1%}`\n"
            f"Sebep: {reason}\n"
            f"_Bu bet otomatik engellendi._"
        )

    def alert_drawdown(self, bankroll: float, hwm: float) -> str:
        return (
            f"*DRAWDOWN BREAKER ACTIVATED*\n"
            f"Bankroll: `${bankroll:.2f}`\n"
            f"High Water Mark: `${hwm:.2f}`\n"
            f"All trading halted. Manual review required."
        )
