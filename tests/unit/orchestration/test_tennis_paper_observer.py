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


def test_pre_match_observation_creates_record(tmp_path: Path) -> None:
    log_path = tmp_path / "tennis_paper.jsonl"
    paper_logger = TennisPaperLogger(log_path=log_path)
    predictor = MagicMock()
    predictor.predict_pre_match.return_value = MagicMock(
        p_win_a=0.62, p_win_b=0.38,
        player_a_record=MagicMock(full_name="Jannik Sinner"),
        player_b_record=MagicMock(full_name="Flavio Cobolli"),
    )
    observer = TennisPaperObserver(
        paper_logger=paper_logger,
        magnus_predictor=predictor,
        phase="paper_trade",
    )
    market = MagicMock()
    market.slug = "atp-sinner-cobolli-2026-04-28"
    market.question = "Madrid Open: Jannik Sinner vs Flavio Cobolli"
    market.tags = ["atp", "madrid-open"]
    tournament_info = MagicMock(tier="masters_1000", surface="clay", format="BO3")
    observer.observe_pre_match(
        market=market,
        tournament_info=tournament_info,
        polymarket_a_price=0.55,
        polymarket_b_price=0.45,
    )
    assert log_path.exists()
    record = json.loads(log_path.read_text().splitlines()[0])
    assert record["match_id"] == "atp-sinner-cobolli-2026-04-28"
    assert record["surface"] == "clay"
    assert record["pre_match"]["model_p_win_a"] == 0.62
