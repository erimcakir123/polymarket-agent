"""2026-05-31 fix: entry'de exit-likidite check.

Polymarket alt market'lerde (WNBA totals, tennis set_handicap) bid book çok ince —
pozisyon açılır ama satılamaz (paper'da %82 REJECT). Çözüm: girişte bid_depth
yeterli değilse pozisyon AÇMA.
"""
from pathlib import Path
from unittest.mock import MagicMock

from src.config.settings import PaperConfig
from src.orchestration.paper_executor import PaperExecutor


def _book_resp(asks, bids):
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status = MagicMock()
    m.json.return_value = {"asks": asks, "bids": bids}
    return m


def _ask(p, s):
    return {"price": str(p), "size": str(s)}


def _bid(p, s):
    return _ask(p, s)


def test_paper_buy_rejected_when_bid_book_too_thin(tmp_path):
    """KRİTİK: bid_depth < min_bid_depth_usdc → BUY REJECTED.

    Ask book yeterli olsa bile (satıcı var), bid book çok ince ise pozisyona
    girilmez (exit olamayacak). WNBA totals senaryosu — alıcı tarafı $5-15.
    """
    # Ask side yeterli (satıcı var, alabiliriz)
    asks = [_ask(0.65, 1000)]
    # Bid side çok ince — toplam $15 (3 bid × ~$5)
    bids = [_bid(0.62, 8), _bid(0.61, 5), _bid(0.60, 10)]
    # 0.62 × 8 + 0.61 × 5 + 0.60 × 10 = $4.96 + $3.05 + $6.00 = $14.01

    cfg = PaperConfig()
    cfg.min_bid_depth_usdc = 50.0   # Min 50$ alıcı tarafı zorunlu

    px = PaperExecutor(
        config=cfg,
        audit_path=tmp_path / "exec.jsonl",
        http_get=MagicMock(return_value=_book_resp(asks, bids)),
    )
    result = px.place_buy(token_id="tok1", target_price=0.65, target_size_usdc=50.0)

    assert result["status"] == "REJECTED"
    assert "exit_liquidity" in result["reason"] or "bid_depth" in result["reason"]


def test_paper_buy_accepts_when_bid_book_sufficient(tmp_path):
    """Kontrol: bid depth yeterliyse normal akış (FILLED)."""
    asks = [_ask(0.65, 1000)]
    # Bid side derin — toplam $620 ($620 alıcı)
    bids = [_bid(0.62, 1000)]

    cfg = PaperConfig()
    cfg.min_bid_depth_usdc = 50.0

    px = PaperExecutor(
        config=cfg,
        audit_path=tmp_path / "exec.jsonl",
        http_get=MagicMock(return_value=_book_resp(asks, bids)),
    )
    result = px.place_buy(token_id="tok1", target_price=0.65, target_size_usdc=50.0)

    assert result["status"] == "FILLED"


def test_paper_config_has_min_bid_depth_default():
    """Default değer config'de tanımlı olmalı."""
    cfg = PaperConfig()
    assert hasattr(cfg, "min_bid_depth_usdc")
    assert cfg.min_bid_depth_usdc > 0
