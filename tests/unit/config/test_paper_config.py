"""PaperConfig dataclass + AppConfig.paper field validation."""
from src.config.settings import AppConfig, PaperConfig


def test_paper_config_defaults() -> None:
    p = PaperConfig()
    assert p.max_buy_slippage_pct == 0.02
    assert p.max_sell_slippage_pct == 0.05
    assert p.min_fill_ratio == 0.95
    assert p.book_cache_ttl_sec == 5
    assert p.max_open_cycles == 6
    assert p.max_stuck_cycles == 12
    assert p.min_order_usdc == 1.0
    assert p.price_tick == 0.01
    assert p.maker_fee_pct == 0.0
    assert p.taker_fee_pct == 0.0
    assert p.polygon_gas_usdc == 0.01


def test_app_config_has_paper_field() -> None:
    cfg = AppConfig()
    assert isinstance(cfg.paper, PaperConfig)
    assert cfg.paper.min_order_usdc == 1.0
