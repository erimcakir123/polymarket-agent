import json, tempfile, pytest
from pathlib import Path


def test_log_trade_appends_jsonl(tmp_path):
    from src.trade_logger import TradeLogger
    log_file = tmp_path / "trades.jsonl"
    logger = TradeLogger(str(log_file))
    logger.log({"market": "test", "action": "BUY_YES", "edge": 0.08})
    logger.log({"market": "test2", "action": "HOLD"})
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["market"] == "test"


def test_log_trade_adds_timestamp(tmp_path):
    from src.trade_logger import TradeLogger
    log_file = tmp_path / "trades.jsonl"
    logger = TradeLogger(str(log_file))
    logger.log({"market": "test"})
    record = json.loads(log_file.read_text().strip())
    assert "timestamp" in record


def test_read_recent(tmp_path):
    from src.trade_logger import TradeLogger
    log_file = tmp_path / "trades.jsonl"
    logger = TradeLogger(str(log_file))
    for i in range(10):
        logger.log({"i": i})
    recent = logger.read_recent(3)
    assert len(recent) == 3
    assert recent[-1]["i"] == 9
