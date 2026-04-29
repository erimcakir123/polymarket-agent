"""Tennis paper observer integration tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.orchestration.tennis_paper_logger import TennisPaperLogger
from src.orchestration.tennis_paper_observer import (
    TennisPaperObserver,
    is_tennis_market,
)


def test_is_tennis_market_atp_slug() -> None:
    assert is_tennis_market("atp-medvedev-cobolli-2026-04-28") is True


def test_is_tennis_market_wta_slug() -> None:
    assert is_tennis_market("wta-stuttgart-open-2026-04-28") is True


def test_is_tennis_market_nhl_slug() -> None:
    assert is_tennis_market("nhl-bos-buf-2026-04-28") is False


def test_is_tennis_market_empty() -> None:
    assert is_tennis_market("") is False


def test_observer_skips_non_tennis(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    paper_logger = TennisPaperLogger(log_path=log_path)
    observer = TennisPaperObserver(paper_logger=paper_logger, magnus_predictor=MagicMock())

    # Mock position with NHL slug
    pos = MagicMock()
    pos.slug = "nhl-bos-buf-2026-04-28"
    pos.sport_tag = "nhl"

    observer.observe_position(pos, current_bid=0.55, score_info={})
    assert not log_path.exists()


def test_observer_skips_when_phase_disabled(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    paper_logger = TennisPaperLogger(log_path=log_path)
    observer = TennisPaperObserver(
        paper_logger=paper_logger,
        magnus_predictor=MagicMock(),
        phase="disabled",
    )

    pos = MagicMock()
    pos.slug = "atp-medvedev-cobolli-2026-04-28"
    pos.sport_tag = "tennis"

    observer.observe_position(pos, current_bid=0.55, score_info={})
    assert not log_path.exists()
