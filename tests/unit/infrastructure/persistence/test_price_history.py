"""price_history.py için birim testler."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from src.infrastructure.persistence.price_history import PriceHistorySaver


def _mock_response(status: int = 200, body: Any = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body or {"history": [{"t": 1, "p": 0.5}, {"t": 2, "p": 0.6}]}
    return resp


def test_save_happy_path_writes_file(tmp_path: Path) -> None:
    http = MagicMock(return_value=_mock_response())
    saver = PriceHistorySaver(base_dir=tmp_path, http_get=http)
    saver.save(
        slug="lakers-vs-celtics",
        token_id="tok123",
        entry_price=0.40,
        exit_price=0.48,
        exit_reason="scale_out",
        match_score="10-5",
    )
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8"))
    assert record["slug"] == "lakers-vs-celtics"
    assert record["entry_price"] == 0.40
    assert record["exit_price"] == 0.48
    assert record["exit_reason"] == "scale_out"
    assert len(record["price_history"]) == 2


def test_save_http_error_swallowed(tmp_path: Path) -> None:
    http = MagicMock(side_effect=RuntimeError("timeout"))
    saver = PriceHistorySaver(base_dir=tmp_path, http_get=http)
    saver.save(slug="x", token_id="t", entry_price=0.3, exit_price=0.2, exit_reason="sl", match_score="")
    assert list(tmp_path.glob("*.json")) == []


def test_save_non_200_skips(tmp_path: Path) -> None:
    http = MagicMock(return_value=_mock_response(status=500))
    saver = PriceHistorySaver(base_dir=tmp_path, http_get=http)
    saver.save(slug="x", token_id="t", entry_price=0.3, exit_price=0.2, exit_reason="sl", match_score="")
    assert list(tmp_path.glob("*.json")) == []


def test_save_slug_sanitization(tmp_path: Path) -> None:
    http = MagicMock(return_value=_mock_response())
    saver = PriceHistorySaver(base_dir=tmp_path, http_get=http)
    saver.save(slug="a/b/c weird", token_id="t", entry_price=0.3, exit_price=0.2, exit_reason="sl", match_score="")
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert "/" not in files[0].name
