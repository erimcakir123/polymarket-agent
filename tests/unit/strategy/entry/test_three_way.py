"""ThreeWayEntry strategy unit tests (SPEC-015)."""
from __future__ import annotations

from src.domain.analysis.probability import BookmakerProbability
from src.models.enums import Direction
from src.models.market import MarketData
from src.strategy.entry.three_way import evaluate as three_way_evaluate


def _market(yes: float, sport: str = "soccer", q: str = "Q?", cid: str = "c") -> MarketData:
    return MarketData(
        condition_id=cid, question=q, slug="s",
        yes_token_id="y", no_token_id="n",
        yes_price=yes, no_price=1 - yes,
        liquidity=50000, volume_24h=10000, tags=[],
        end_date_iso="2026-04-25T00:00:00Z",
        sport_tag=sport, event_id="e1",
    )


def _bm_probs(h: float, d: float, a: float, conf: str = "A") -> dict:
    return {
        "home": BookmakerProbability(probability=h, confidence=conf,
            bookmaker_prob=h, num_bookmakers=10.0, has_sharp=True),
        "draw": BookmakerProbability(probability=d, confidence=conf,
            bookmaker_prob=d, num_bookmakers=10.0, has_sharp=True),
        "away": BookmakerProbability(probability=a, confidence=conf,
            bookmaker_prob=a, num_bookmakers=10.0, has_sharp=True),
    }


def test_clear_home_favorite_passes() -> None:
    """Home 45%/Draw 27%/Away 28% → home favori (margin 17pp), PM 65c in [0.60, 0.85] ✓."""
    sig = three_way_evaluate(
        home_market=_market(yes=0.65, q="Will Arsenal win?", cid="h"),
        draw_market=_market(yes=0.27, q="Will the match end in a draw?", cid="d"),
        away_market=_market(yes=0.28, q="Will Chelsea win?", cid="a"),
        probs=_bm_probs(0.45, 0.27, 0.28),
    )
    assert sig is not None
    assert sig.direction == Direction.BUY_YES
    assert sig.condition_id == "h"
    assert sig.bookmaker_prob == 0.45  # anchor is the top bookmaker probability


def test_three_way_skips_when_favorite_price_out_of_range() -> None:
    """Favorite market yes_price 0.90 > max_entry_price 0.85 → SKIP."""
    sig = three_way_evaluate(
        home_market=_market(yes=0.90, q="Will Arsenal win?", cid="h"),  # too expensive
        draw_market=_market(yes=0.27, q="Will the match end in a draw?", cid="d"),
        away_market=_market(yes=0.28, q="Will Chelsea win?", cid="a"),
        probs=_bm_probs(0.45, 0.27, 0.28),
    )
    assert sig is None


def test_three_way_skips_when_favorite_price_below_min() -> None:
    """Favorite market yes_price 0.50 < min_entry_price 0.60 → SKIP."""
    sig = three_way_evaluate(
        home_market=_market(yes=0.50, q="Will Arsenal win?", cid="h"),  # too cheap
        draw_market=_market(yes=0.27, q="Will the match end in a draw?", cid="d"),
        away_market=_market(yes=0.28, q="Will Chelsea win?", cid="a"),
        probs=_bm_probs(0.45, 0.27, 0.28),
    )
    assert sig is None


def test_absolute_threshold_fail() -> None:
    """Home 38% < 40% threshold → SKIP (absolute fail)."""
    sig = three_way_evaluate(
        home_market=_market(yes=0.36),
        draw_market=_market(yes=0.30),
        away_market=_market(yes=0.34),
        probs=_bm_probs(0.38, 0.30, 0.32),
    )
    assert sig is None


def test_margin_below_7pp_skipped() -> None:
    """Home 40.5% vs Away 39.5% → margin 1pp < 7pp → SKIP."""
    sig = three_way_evaluate(
        home_market=_market(yes=0.38),
        draw_market=_market(yes=0.20),
        away_market=_market(yes=0.42),
        probs=_bm_probs(0.405, 0.20, 0.395),
    )
    assert sig is None


def test_tie_break_equal_probs() -> None:
    """Eşit olasılıklar → SKIP (tie-break)."""
    sig = three_way_evaluate(
        home_market=_market(yes=0.30),
        draw_market=_market(yes=0.30),
        away_market=_market(yes=0.40),
        probs=_bm_probs(0.40, 0.20, 0.40),
    )
    assert sig is None


def test_away_favorite_selects_away_market() -> None:
    """Away favori → signal away market'a yönelir. yes=0.65 in price range [0.60, 0.85]."""
    sig = three_way_evaluate(
        home_market=_market(yes=0.30, cid="h"),
        draw_market=_market(yes=0.25, cid="d"),
        away_market=_market(yes=0.65, q="Will Real Madrid win?", cid="a"),
        probs=_bm_probs(0.25, 0.25, 0.50),
    )
    assert sig is not None
    assert sig.condition_id == "a"


def test_draw_favorite_rare_case() -> None:
    """Draw favori (nadir) — Bayern vs Dortmund tipi dengeli."""
    sig = three_way_evaluate(
        home_market=_market(yes=0.32, cid="h"),
        draw_market=_market(yes=0.65, q="Will the match end in a draw?", cid="d"),
        away_market=_market(yes=0.32, cid="a"),
        probs=_bm_probs(0.32, 0.40, 0.28),
    )
    # Draw 0.40 >= 0.40 threshold ✓; margin 0.40-0.32=0.08 >= 0.07 ✓
    # Price: 0.65 in [0.60, 0.85] ✓
    assert sig is not None
    assert sig.condition_id == "d"


def test_c_confidence_skipped() -> None:
    """Herhangi outcome C-conf → SKIP."""
    probs = _bm_probs(0.45, 0.27, 0.28, conf="A")
    probs["home"] = BookmakerProbability(
        probability=0.45, confidence="C",
        bookmaker_prob=0.45, num_bookmakers=2.0, has_sharp=False,
    )
    sig = three_way_evaluate(
        home_market=_market(yes=0.37),
        draw_market=_market(yes=0.27),
        away_market=_market(yes=0.28),
        probs=probs,
    )
    assert sig is None


def test_missing_market_for_favorite() -> None:
    """Favorite outcome market'i None → SKIP (3-way grouping inkomplet)."""
    sig = three_way_evaluate(
        home_market=None,  # eksik
        draw_market=_market(yes=0.27),
        away_market=_market(yes=0.28),
        probs=_bm_probs(0.45, 0.27, 0.28),
    )
    assert sig is None


def test_three_way_logs_skip_reason(caplog) -> None:
    """SPEC-015: SKIP kararları INFO log'a yazılır (debug için)."""
    import logging

    # Below absolute threshold senaryosu
    with caplog.at_level(logging.INFO, logger="src.strategy.entry.three_way"):
        three_way_evaluate(
            home_market=_market(yes=0.36),
            draw_market=_market(yes=0.30),
            away_market=_market(yes=0.34),
            probs=_bm_probs(0.38, 0.30, 0.32),
        )
    assert any("SKIP" in r.message for r in caplog.records)
    assert any("below_threshold" in r.message or "margin_too_low" in r.message for r in caplog.records)


def test_three_way_logs_enter_decision(caplog) -> None:
    """SPEC-015: Başarılı ENTER kararı INFO log'a yazılır."""
    import logging

    with caplog.at_level(logging.INFO, logger="src.strategy.entry.three_way"):
        sig = three_way_evaluate(
            home_market=_market(yes=0.65, q="Will Arsenal win?", cid="h"),
            draw_market=_market(yes=0.27, q="Will the match end in a draw?", cid="d"),
            away_market=_market(yes=0.28, q="Will Chelsea win?", cid="a"),
            probs=_bm_probs(0.45, 0.27, 0.28),
        )
    assert sig is not None
    assert any("ENTER" in r.message for r in caplog.records)
