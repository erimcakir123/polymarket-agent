"""three_way_title.py için birim testler (PLAN-011, SPEC-015)."""
from __future__ import annotations

from src.domain.matching.three_way_title import (
    enrich_three_way_titles,
    extract_teams_from_draw,
)
from src.models.market import MarketData


def _make_market(
    *,
    cid: str,
    question: str,
    sport_tag: str = "soccer_eng_epl",
    event_id: str = "evt-1",
    match_title: str = "",
) -> MarketData:
    return MarketData(
        condition_id=cid,
        question=question,
        slug=cid,
        yes_token_id=f"{cid}-yes",
        no_token_id=f"{cid}-no",
        yes_price=0.33,
        no_price=0.67,
        liquidity=1000.0,
        volume_24h=500.0,
        end_date_iso="2026-04-21T14:30:00Z",
        match_start_iso="2026-04-21T14:30:00Z",
        event_id=event_id,
        sport_tag=sport_tag,
        sports_market_type="moneyline",
        match_title=match_title,
    )


# ── extract_teams_from_draw ──

def test_extract_teams_valid_draw_question_returns_tuple() -> None:
    q = "Will PFK Krylia Sovetov Samara vs Spartak Kostroma end in a draw?"
    assert extract_teams_from_draw(q) == ("PFK Krylia Sovetov Samara", "Spartak Kostroma")


def test_extract_teams_with_vs_dot_variant_returns_tuple() -> None:
    q = "Will Real Madrid vs. Barcelona end in a draw?"
    assert extract_teams_from_draw(q) == ("Real Madrid", "Barcelona")


def test_extract_teams_case_insensitive() -> None:
    q = "will liverpool vs chelsea END IN A DRAW?"
    assert extract_teams_from_draw(q) == ("liverpool", "chelsea")


def test_extract_teams_single_team_win_question_returns_none() -> None:
    assert extract_teams_from_draw("Will PFK Krylia Sovetov Samara win on 2026-04-21?") is None


def test_extract_teams_empty_returns_none() -> None:
    assert extract_teams_from_draw("") is None
    assert extract_teams_from_draw(None) is None  # type: ignore[arg-type]


def test_extract_teams_unrelated_question_returns_none() -> None:
    assert extract_teams_from_draw("Who will win the 2026 election?") is None


# ── enrich_three_way_titles ──

def test_enrich_three_way_sets_match_title_on_home_away_draw() -> None:
    home = _make_market(cid="h", question="Will PFK Krylia win on 2026-04-21?")
    draw = _make_market(cid="d", question="Will PFK Krylia vs Spartak Kostroma end in a draw?")
    away = _make_market(cid="a", question="Will Spartak Kostroma win on 2026-04-21?")
    out = enrich_three_way_titles([home, draw, away])
    titles = {m.condition_id: m.match_title for m in out}
    assert titles == {
        "h": "PFK Krylia vs Spartak Kostroma",
        "d": "PFK Krylia vs Spartak Kostroma",
        "a": "PFK Krylia vs Spartak Kostroma",
    }


def test_enrich_three_way_preserves_original_question() -> None:
    home = _make_market(cid="h", question="Will X win on 2026-04-21?")
    draw = _make_market(cid="d", question="Will X vs Y end in a draw?")
    away = _make_market(cid="a", question="Will Y win on 2026-04-21?")
    out = enrich_three_way_titles([home, draw, away])
    for m in out:
        # Ham question alanı dokunulmaz (question_parser invariantı).
        assert "match_title" not in m.question
    assert out[0].question == "Will X win on 2026-04-21?"


def test_enrich_two_way_market_not_touched() -> None:
    # MLB 2-way event (soccer olmayan sport_tag → THREE_WAY değil)
    m1 = _make_market(cid="m1", question="Will Yankees beat Red Sox?", sport_tag="baseball_mlb")
    out = enrich_three_way_titles([m1])
    assert out[0].match_title == ""


def test_enrich_three_way_missing_draw_no_op() -> None:
    # 2 market (home + away), draw yok → classify_outcomes draw=None → enrichment atlanır.
    home = _make_market(cid="h", question="Will X win on 2026-04-21?")
    away = _make_market(cid="a", question="Will Y win on 2026-04-21?")
    out = enrich_three_way_titles([home, away])
    for m in out:
        assert m.match_title == ""


def test_enrich_three_way_unparseable_draw_no_op() -> None:
    # Draw keyword var ama regex "Will X vs Y end in a draw" pattern'i yok.
    home = _make_market(cid="h", question="Will X win on 2026-04-21?")
    draw = _make_market(cid="d", question="Will there be a draw in match 123?")
    away = _make_market(cid="a", question="Will Y win on 2026-04-21?")
    out = enrich_three_way_titles([home, draw, away])
    for m in out:
        assert m.match_title == ""


def test_enrich_idempotent_existing_match_title_preserved() -> None:
    # Önceden set edilmiş match_title (ör. manuel test data) overwrite edilmez.
    home = _make_market(
        cid="h",
        question="Will X win on 2026-04-21?",
        match_title="Manual Title",
    )
    draw = _make_market(cid="d", question="Will X vs Y end in a draw?")
    away = _make_market(cid="a", question="Will Y win on 2026-04-21?")
    out = enrich_three_way_titles([home, draw, away])
    by_cid = {m.condition_id: m for m in out}
    assert by_cid["h"].match_title == "Manual Title"
    assert by_cid["d"].match_title == "X vs Y"
    assert by_cid["a"].match_title == "X vs Y"


def test_enrich_mixed_sports_only_soccer_enriched() -> None:
    soc_home = _make_market(cid="sh", question="Will X win on 2026-04-21?", event_id="soc1")
    soc_draw = _make_market(cid="sd", question="Will X vs Y end in a draw?", event_id="soc1")
    soc_away = _make_market(cid="sa", question="Will Y win on 2026-04-21?", event_id="soc1")
    mlb = _make_market(
        cid="mlb1",
        question="Will Yankees beat Red Sox?",
        sport_tag="baseball_mlb",
        event_id="mlb-evt",
    )
    out = enrich_three_way_titles([soc_home, soc_draw, soc_away, mlb])
    by_cid = {m.condition_id: m for m in out}
    assert by_cid["sh"].match_title == "X vs Y"
    assert by_cid["sd"].match_title == "X vs Y"
    assert by_cid["sa"].match_title == "X vs Y"
    assert by_cid["mlb1"].match_title == ""
