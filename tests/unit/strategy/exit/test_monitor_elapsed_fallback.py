"""compute_elapsed_pct ESPN/score_info fallback testleri (SPEC-B Task 6 / audit#4)."""
from __future__ import annotations

from src.models.position import Position
from src.strategy.exit.monitor import compute_elapsed_pct


def _pos(sport_tag: str = "nhl", match_start: str = "bad-iso") -> Position:
    return Position(
        condition_id="c", token_id="t", direction="BUY_YES",
        entry_price=0.5, size_usdc=50, shares=100, current_price=0.5,
        anchor_probability=0.5, event_id="e", slug="s",
        sport_tag=sport_tag, match_start_iso=match_start,
    )


def test_parse_fail_no_score_returns_minus_one() -> None:
    """match_start parse fail + no score_info → -1.0 (mevcut davranış)."""
    pos = _pos()
    assert compute_elapsed_pct(pos, score_info={}) == -1.0


def test_parse_fail_score_unavailable_returns_minus_one() -> None:
    """score_info present but available=False → -1.0."""
    pos = _pos()
    assert compute_elapsed_pct(pos, score_info={"available": False}) == -1.0


def test_parse_fail_nhl_period_3_estimates_high() -> None:
    """match_start parse fail + NHL period '3rd' → ≥ 0.66 (son periyot yaklaşık)."""
    pos = _pos(sport_tag="nhl")
    score_info = {"available": True, "period": "3rd"}
    assert compute_elapsed_pct(pos, score_info=score_info) >= 0.66


def test_parse_fail_nhl_final_returns_one() -> None:
    """NHL Final → 1.0."""
    pos = _pos(sport_tag="nhl")
    score_info = {"available": True, "period": "Final"}
    assert compute_elapsed_pct(pos, score_info=score_info) == 1.0


def test_parse_fail_mlb_inning_7_estimates_mid_late() -> None:
    """MLB '7th' → ≥ 0.5 (mid-late game)."""
    pos = _pos(sport_tag="mlb")
    score_info = {"available": True, "period": "7th"}
    assert compute_elapsed_pct(pos, score_info=score_info) >= 0.5


def test_parse_fail_nba_quarter_4_estimates_high() -> None:
    """NBA 4th quarter → ≥ 0.7."""
    pos = _pos(sport_tag="nba")
    score_info = {"available": True, "period": "4th"}
    assert compute_elapsed_pct(pos, score_info=score_info) >= 0.7


def test_valid_match_start_uses_duration_calculation() -> None:
    """match_start valid + score_info verilse de süre bazlı hesap kullanılır (regression check)."""
    from datetime import datetime, timedelta, timezone
    # 1 saat önce başlamış 2.5 saatlik NHL maçı → ~0.4
    start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    pos = _pos(sport_tag="nhl", match_start=start)
    result = compute_elapsed_pct(pos, score_info={"available": True, "period": "3rd"})
    assert 0.3 <= result <= 0.5  # süre bazlı, period değil


def test_no_match_start_no_score_returns_minus_one() -> None:
    """Boş match_start + no score → -1.0."""
    pos = _pos(match_start="")
    assert compute_elapsed_pct(pos, score_info={}) == -1.0
