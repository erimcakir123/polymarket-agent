"""Tennis agent WS price-feed lifecycle helpers (Stage tennis-lab 2026-05-20).

Tennis agent.run_forever uses these to wire the PriceFeed:
  - bind_price_callback: portfolio.update_position_price closure for WS ticks
  - start_price_feed: subscribe to currently-open token_ids + start_background()

Main bot's `agent.py` pattern is identical (set_callback → subscribe →
start_background); duplicated here so tennis_agent stays under the 400-line
guard (ARCHITECTURE_GUARD Kural 3) and isolated from main Agent class.
"""
from __future__ import annotations

import logging
from typing import Callable

from src.domain.portfolio.manager import PortfolioManager
from src.infrastructure.websocket.price_feed import PriceFeed

logger = logging.getLogger(__name__)


def bind_price_callback(portfolio: PortfolioManager) -> Callable[[str, float, float, float], None]:
    """WS callback'i portfolio.update_position_price üzerine bağla.

    Tennis için sadece current_price + bid_price güncellemesi. peak/momentum/
    ever_in_profit state cycle-bazlı kalır (lifecycle.tick_position_state).
    """
    def _on_price_update(token_id: str, yes_price: float, bid_price: float, _ts: float) -> None:
        try:
            portfolio.update_position_price(token_id, yes_price, bid_price)
        except Exception as exc:  # noqa: BLE001 — orchestration catches + logs
            logger.error("Tennis WS price update error: %s", exc)
    return _on_price_update


def start_price_feed(price_feed: PriceFeed, portfolio: PortfolioManager) -> None:
    """Açık pozisyon token_id'lerine subscribe ol + WS thread'i başlat.

    Yeni entry'ler `EntryProcessor._execute_entry` içinde
    `price_feed.subscribe([token_id])` ile dinamik eklenir; bu fonksiyon
    yalnızca bot restart sonrası mevcut pozisyonları subscribe eder.
    """
    tokens = [p.token_id for p in portfolio.positions.values() if p.token_id]
    if tokens:
        price_feed.subscribe(tokens)
    price_feed.start_background()
    logger.info(
        "Tennis WS price feed started: subscribed=%d tokens", len(tokens),
    )


def install_price_feed(price_feed: PriceFeed | None, portfolio: PortfolioManager) -> None:
    """Tek satır lifecycle wiring helper (tennis_agent.run_forever çağırır).

    price_feed None ise no-op (test path). Aksi halde callback bağlar +
    açık pozisyonları subscribe eder + thread başlatır + atexit stop kaydeder.
    """
    if price_feed is None:
        return
    import atexit
    price_feed.set_callback(bind_price_callback(portfolio))
    start_price_feed(price_feed, portfolio)
    atexit.register(price_feed.stop)
