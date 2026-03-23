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
        if self.enabled:
            self._flush_old_updates()

    def _flush_old_updates(self) -> None:
        """Discard all pending Telegram updates so old /stop commands don't fire."""
        try:
            url = TELEGRAM_API.format(token=self.bot_token, method="getUpdates")
            resp = requests.get(url, params={"offset": -1, "timeout": 1}, timeout=5)
            if resp.status_code == 200:
                results = resp.json().get("result", [])
                if results:
                    self._last_update_id = results[-1]["update_id"]
                    logger.info("Flushed %d old Telegram updates (last_id=%d)", len(results), self._last_update_id)
        except Exception as e:
            logger.debug("Telegram flush error: %s", e)

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
                self.send("*STOPPING*\n\nShutting down after current cycle.")
                agent.running = False
                logger.info("Telegram /stop command received")

            elif cmd == "/pause":
                PAUSE_FILE.parent.mkdir(parents=True, exist_ok=True)
                PAUSE_FILE.write_text("Paused via /pause command", encoding="utf-8")
                self.send("*PAUSED*\n\nSend /resume to continue.")
                logger.info("Telegram /pause command received")

            elif cmd == "/resume":
                if PAUSE_FILE.exists():
                    PAUSE_FILE.unlink()
                    self.send("*RESUMED*\n\nBot is running.")
                    logger.info("Telegram /resume command received")
                else:
                    self.send("Bot is already running.")

            elif cmd == "/status":
                positions = len(agent.portfolio.positions)
                bankroll = agent.portfolio.bankroll
                paused = PAUSE_FILE.exists()
                budget = agent.ai.budget_remaining_usd
                self.send(
                    f"*STATUS*\n\n"
                    f"Mode: `{agent.config.mode.value}`\n"
                    f"Balance: `${bankroll:.2f}`\n"
                    f"Positions: `{positions}`\n"
                    f"API budget left: `${budget:.2f}`\n"
                    f"State: `{'PAUSED' if paused else 'RUNNING'}`\n"
                    f"Bets: `{agent.bets_since_approval}`/10"
                )

            else:
                self.send(f"Unknown command: {cmd}\n\nAvailable: /stop /pause /resume /status")

    # ------------------------------------------------------------------
    # Message formatters
    # ------------------------------------------------------------------

    def format_trade(
        self, question: str, direction: str, size: float, price: float, edge: float
    ) -> str:
        return (
            f"*TRADE OPENED*\n\n"
            f"{question}\n"
            f"`{direction}` | `${size:.2f}` @ `{price:.2f}`\n"
            f"Edge: `{edge:.1%}`"
        )

    def format_exit(self, question: str, reason: str, pnl: float) -> str:
        sign = "+" if pnl >= 0 else ""
        return (
            f"*POSITION CLOSED*\n\n"
            f"{question}\n"
            f"Reason: {reason}\n"
            f"PnL: `{sign}${pnl:.2f}`"
        )

    def format_suspicious_bet(
        self, question: str, direction: str, size: float, edge: float, reason: str
    ) -> str:
        return (
            f"*BLOCKED*\n\n"
            f"{question}\n"
            f"`{direction}` | `${size:.2f}` | Edge: `{edge:.1%}`\n\n"
            f"Reason: {reason}"
        )

    def alert_drawdown(self, bankroll: float, hwm: float) -> str:
        return (
            f"*DRAWDOWN BREAKER*\n\n"
            f"Balance: `${bankroll:.2f}`\n"
            f"Peak: `${hwm:.2f}`\n\n"
            f"All trading halted. Manual review required."
        )
