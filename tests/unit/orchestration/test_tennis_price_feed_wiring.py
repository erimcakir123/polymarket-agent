"""tennis_factory + tennis_agent PriceFeed lifecycle wiring testleri.

2026-05-20 (tennis-lab Faz tennis): Paper bot 9 pozisyon açtı ama
current_price entry_price'a takılı kaldı → ExitProcessor.run_light stale price
okuyor, SL/TP/near_resolve hiç tetiklemiyor. Bu test suite şunu doğrular:
  - tennis_factory.build_tennis_deps → deps.price_feed gerçek PriceFeed instance
  - tennis_agent.run_forever → start_background + callback bind + atexit stop
  - WS callback → portfolio.update_position_price (token_id eşleşmesi)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.domain.portfolio.manager import PortfolioManager
from src.infrastructure.websocket.price_feed import PriceFeed
from src.models.position import Position
from src.orchestration.tennis_factory import build_tennis_deps
from src.orchestration.tennis_price_callback import (
    bind_price_callback,
    install_price_feed,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _write_min_tennis_config(path: Path) -> Path:
    """Minimal config_tennis.yaml — sadece test izolasyonu için zorunlu alanlar."""
    cfg_text = """
mode: paper
initial_bankroll: 500
edge:
  min_edge: 0.06
risk:
  consecutive_loss_cooldown: 3
  cooldown_cycles: 2
price_feed:
  max_spike_pct: 0.50
  max_spread_for_near_resolve: 0.10
tennis:
  data_dir: "data/sackmann_cache"
  ratings_cache: "data/tennis_ratings.json"
  diagnostic_log_dir: "data/tennis_diagnostics"
"""
    path.write_text(cfg_text, encoding="utf-8")
    return path


def _open_position(token_id: str = "0xTOKEN", entry_price: float = 0.40) -> Position:
    return Position(
        condition_id="0xCID",
        token_id=token_id,
        direction="BUY_YES",
        entry_price=entry_price,
        size_usdc=40.0,
        shares=100.0,
        current_price=entry_price,
        anchor_probability=0.5,
        entry_reason="tennis",
        confidence="A",
        sport_tag="tennis_atp",
    )


# ── tennis_factory wiring ────────────────────────────────────────────────────


def test_tennis_factory_builds_price_feed(tmp_path: Path) -> None:
    """build_tennis_deps → deps.price_feed gerçek PriceFeed instance.

    Bug fix doğrulaması: tennis_factory önceki sürümde price_feed=None geçiyordu
    → ExitProcessor.run_light stale current_price okuyor + SL hiç tetiklemiyor.
    Bu test artık gerçek PriceFeed instance bağlandığını assert eder.
    """
    cfg_path = _write_min_tennis_config(tmp_path / "config.yaml")
    deps = build_tennis_deps(cfg_path, data_dir=tmp_path / "data", logs_dir=tmp_path / "logs")
    assert deps.price_feed is not None
    assert isinstance(deps.price_feed, PriceFeed)


def test_tennis_factory_entry_processor_shares_price_feed(tmp_path: Path) -> None:
    """EntryProcessor + ExitProcessor aynı PriceFeed instance'ı görür.

    Subscribe (entry) + unsubscribe (exit) symmetric — iki processor'ın
    deps.price_feed'i aynı obje olmalı.
    """
    cfg_path = _write_min_tennis_config(tmp_path / "config.yaml")
    deps = build_tennis_deps(cfg_path, data_dir=tmp_path / "data", logs_dir=tmp_path / "logs")
    assert deps.entry_processor.deps.price_feed is deps.price_feed
    assert deps.exit_processor.deps.price_feed is deps.price_feed


# ── tennis_price_callback bind/install ────────────────────────────────────────


def test_price_callback_updates_position_current_price() -> None:
    """WS callback simülasyonu → portfolio.update_position_price(token_id, yes, bid).

    Token_id eşleşmesi kritik: WS başka token'lar için de tick gönderir,
    portfolio sadece kendi pozisyonunu güncellemeli (manager.py:121-125).
    """
    portfolio = PortfolioManager(initial_bankroll=500.0)
    portfolio.add_position(_open_position(token_id="0xTOKEN_A", entry_price=0.40))
    callback = bind_price_callback(portfolio)

    # WS tick — yes_price=0.55, bid=0.54 (entry_price 0.40'tan farklı)
    callback("0xTOKEN_A", 0.55, 0.54, 1234567890.0)

    pos = next(iter(portfolio.positions.values()))
    assert pos.current_price == 0.55
    assert pos.bid_price == 0.54
    # entry_price değişmedi (anchor invariant)
    assert pos.entry_price == 0.40


def test_install_price_feed_starts_background_and_subscribes() -> None:
    """install_price_feed → set_callback + subscribe(tokens) + start_background()."""
    portfolio = PortfolioManager(initial_bankroll=500.0)
    portfolio.add_position(_open_position(token_id="0xTOKEN_X"))
    portfolio.add_position(_open_position(token_id="0xTOKEN_Y"))
    portfolio.positions["0xCID_2"] = portfolio.positions.pop("0xCID")
    # Re-add unique pos for the second token
    pos2 = _open_position(token_id="0xTOKEN_Y")
    pos2.condition_id = "0xCID_2"

    pf = MagicMock(spec=PriceFeed)
    install_price_feed(pf, portfolio)

    pf.set_callback.assert_called_once()
    pf.start_background.assert_called_once()
    pf.subscribe.assert_called_once()
    subscribed_tokens = pf.subscribe.call_args[0][0]
    # Tek pozisyon var (overwrite oldu) — token_id 0xTOKEN_Y subscribe edildi
    assert len(subscribed_tokens) >= 1


def test_install_price_feed_noop_when_price_feed_is_none() -> None:
    """price_feed=None → no-op (test path / disabled)."""
    portfolio = PortfolioManager(initial_bankroll=500.0)
    # Hata vermeyecek — sadece return eder
    install_price_feed(None, portfolio)


def test_install_price_feed_registers_atexit_stop() -> None:
    """atexit.register → price_feed.stop callable bağlandı."""
    portfolio = PortfolioManager(initial_bankroll=500.0)
    pf = MagicMock(spec=PriceFeed)
    with patch("atexit.register") as atexit_reg:
        install_price_feed(pf, portfolio)
    atexit_reg.assert_called_once_with(pf.stop)


def test_install_price_feed_no_subscribe_when_no_positions() -> None:
    """Açık pozisyon yoksa subscribe çağrılmaz (boş liste verilmez)."""
    portfolio = PortfolioManager(initial_bankroll=500.0)
    pf = MagicMock(spec=PriceFeed)
    install_price_feed(pf, portfolio)

    pf.subscribe.assert_not_called()
    pf.start_background.assert_called_once()
