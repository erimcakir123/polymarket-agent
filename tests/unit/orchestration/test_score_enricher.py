"""Score enricher testleri (SPEC-005 Task 4 — ESPN primary + Odds API fallback)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.infrastructure.apis.score_client import MatchScore
from src.models.position import Position
from src.orchestration.score_enricher import (
    ScoreEnricher,
    _build_score_info,
    _find_match_via_pair,
    _is_within_match_window,
)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _pos(
    cid: str = "c1",
    question: str = "Rangers vs. Lightning",
    direction: str = "BUY_NO",
    sport_tag: str = "nhl",
    hours_ago: float = 1.0,
) -> Position:
    start = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return Position(
        condition_id=cid, token_id="t", direction=direction,
        entry_price=0.61, size_usdc=50, shares=80,
        current_price=0.50, anchor_probability=0.40,
        confidence="A", sport_tag=sport_tag,
        question=question, match_start_iso=_iso(start),
    )


def _ms(
    home: str = "New York Rangers",
    away: str = "Tampa Bay Lightning",
    h_score: int | None = 3,
    a_score: int | None = 1,
) -> MatchScore:
    return MatchScore(
        event_id="e1", home_team=home, away_team=away,
        home_score=h_score, away_score=a_score,
        period="2nd", is_completed=False, last_updated="",
    )


def _espn_score(
    home: str = "New York Rangers",
    away: str = "Tampa Bay Lightning",
    h_score: int = 3,
    a_score: int = 1,
) -> ESPNMatchScore:
    return ESPNMatchScore(
        event_id="e1", home_name=home, away_name=away,
        home_score=h_score, away_score=a_score,
        period="2nd", is_completed=False, is_live=True,
        last_updated="", linescores=[],
    )


# ── Fake clients ──

class _FakeESPN:
    def __init__(self, scores: list[ESPNMatchScore] | None = None, fail: bool = False) -> None:
        self.call_count = 0
        self._scores = scores or []
        self._fail = fail

    def fetch(self, sport: str, league: str, date: str | None = None) -> list[ESPNMatchScore]:
        self.call_count += 1
        if self._fail:
            return []
        return self._scores


class _FakeClient:
    def __init__(self, data: list[dict] | None = None) -> None:
        self.call_count = 0
        self._data = data

    def get_scores(self, sport_key: str, days_from: int = 1) -> list[dict] | None:
        self.call_count += 1
        return self._data


# ── match window ──

def test_within_match_window() -> None:
    pos = _pos(hours_ago=2.0)
    assert _is_within_match_window(pos, window_hours=4.0)


def test_outside_match_window() -> None:
    pos = _pos(hours_ago=6.0)
    assert not _is_within_match_window(pos, window_hours=4.0)


# ── build_score_info ──

def test_build_score_info_buy_no_behind() -> None:
    pos = _pos(direction="BUY_NO", question="Rangers vs. Lightning")
    ms = _ms(home="New York Rangers", away="Tampa Bay Lightning", h_score=3, a_score=1)
    # BUY_NO: YES side = Rangers (home), NO side = Lightning (away) = bizim taraf
    # Rangers (YES) = home = 3, Lightning (NO) = away = 1
    # Bizim taraf = NO side = Lightning = 1, Rakip = Rangers = 3
    info = _build_score_info(pos, ms)
    assert info["available"]
    assert info["our_score"] == 1
    assert info["opp_score"] == 3
    assert info["deficit"] == 2  # gerideyiz


def test_build_score_info_buy_yes_ahead() -> None:
    pos = _pos(direction="BUY_YES", question="Rangers vs. Lightning")
    ms = _ms(home="New York Rangers", away="Tampa Bay Lightning", h_score=3, a_score=1)
    info = _build_score_info(pos, ms)
    assert info["our_score"] == 3
    assert info["opp_score"] == 1
    assert info["deficit"] == -2  # öndeyiz


def test_build_score_info_no_score_yet() -> None:
    pos = _pos(direction="BUY_NO")
    ms = _ms(h_score=None, a_score=None)
    info = _build_score_info(pos, ms)
    assert not info["available"]


# ── ScoreEnricher polling (new constructor) ──

def test_enricher_polls_only_when_due() -> None:
    espn = _FakeESPN([])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=120, poll_critical_sec=120,
    )
    pos = _pos(hours_ago=1.0)
    enricher.get_scores_if_due({"c1": pos})
    assert espn.call_count >= 1
    old_count = espn.call_count

    # 120 sn geçmeden tekrar çağır — API çağrılmamalı
    enricher.get_scores_if_due({"c1": pos})
    assert espn.call_count == old_count


def test_enricher_no_live_positions_no_call() -> None:
    espn = _FakeESPN([])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=120, poll_critical_sec=120,
    )
    pos = _pos(hours_ago=10.0)  # pencere dışı
    enricher.get_scores_if_due({"c1": pos})
    assert espn.call_count == 0  # API hiç çağrılmadı


# ── NEW: ESPN dispatch ──

def test_enricher_uses_espn_for_nhl() -> None:
    espn = _FakeESPN([_espn_score()])
    odds = _FakeClient()
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        poll_normal_sec=0, poll_critical_sec=0,
    )
    pos = _pos(cid="c1", question="Rangers vs. Lightning", sport_tag="nhl", hours_ago=1.0)
    result = enricher.get_scores_if_due({"c1": pos})
    assert espn.call_count >= 1
    assert odds.call_count == 0
    assert "c1" in result
    assert result["c1"]["available"]


def test_enricher_falls_back_to_odds_api() -> None:
    espn = _FakeESPN(fail=True)
    odds_data = [
        {
            "id": "e1",
            "home_team": "New York Rangers",
            "away_team": "Tampa Bay Lightning",
            "scores": [
                {"name": "New York Rangers", "score": "3"},
                {"name": "Tampa Bay Lightning", "score": "1"},
            ],
            "completed": False,
            "last_update": "",
        },
    ]
    odds = _FakeClient(data=odds_data)
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        poll_normal_sec=0, poll_critical_sec=0,
    )
    pos = _pos(cid="c1", question="Rangers vs. Lightning", sport_tag="nhl", hours_ago=1.0)
    result = enricher.get_scores_if_due({"c1": pos})
    assert espn.call_count >= 1
    assert odds.call_count >= 1
    assert "c1" in result


def test_enricher_tennis_no_fallback() -> None:
    espn = _FakeESPN(fail=True)
    odds = _FakeClient()
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        poll_normal_sec=0, poll_critical_sec=0,
    )
    pos = _pos(cid="c1", question="Muchova vs. Gauff", sport_tag="tennis", hours_ago=1.0)
    result = enricher.get_scores_if_due({"c1": pos})
    assert odds.call_count == 0
    assert "c1" not in result


def test_enricher_adaptif_polling_critical() -> None:
    espn = _FakeESPN([_espn_score()])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=60, poll_critical_sec=30, critical_price_threshold=0.35,
    )
    pos = _pos(cid="c1", sport_tag="nhl", hours_ago=1.0)
    pos.current_price = 0.20
    enricher.get_scores_if_due({"c1": pos})
    assert enricher._poll_sec == 30


# ── _find_match_via_pair ──

def test_find_match_via_pair_skips_wrong_match_same_player() -> None:
    """Two-team position must not match ESPN entry with only one matching player."""
    pos = _pos(question="Rafael Jodar vs Arthur Fils", sport_tag="tennis")
    old_match = ESPNMatchScore(
        event_id="old", home_name="Cameron Norrie", away_name="Rafael Jodar",
        home_score=0, away_score=2, period="Final", is_completed=True,
        is_live=False, last_updated="", linescores=[[3, 6], [3, 6]],
    )
    assert _find_match_via_pair(pos, [old_match], "home_name", "away_name") is None


def test_find_match_via_pair_correct_two_team() -> None:
    """Two-team position matches when both players found."""
    pos = _pos(question="Rafael Jodar vs Arthur Fils", sport_tag="tennis")
    correct = ESPNMatchScore(
        event_id="new", home_name="Rafael Jodar", away_name="Arthur Fils",
        home_score=0, away_score=0, period="In Progress", is_completed=False,
        is_live=True, last_updated="", linescores=[[3, 3]],
    )
    result = _find_match_via_pair(pos, [correct], "home_name", "away_name")
    assert result is not None
    assert result.event_id == "new"


def test_find_match_via_pair_single_team_fallback() -> None:
    """Single-team position (no team_b) still uses fallback matching."""
    pos = _pos(question="Will Tiger Woods win?", sport_tag="golf")
    espn = ESPNMatchScore(
        event_id="g1", home_name="Tiger Woods", away_name="Rory McIlroy",
        home_score=None, away_score=None, period="", is_completed=False,
        is_live=False, last_updated="",
    )
    result = _find_match_via_pair(pos, [espn], "home_name", "away_name")
    assert result is not None
    assert result.event_id == "g1"


def test_find_match_via_pair_prefers_correct_over_old() -> None:
    """When both old and correct matches exist, correct one matches regardless of order."""
    pos = _pos(question="Rafael Jodar vs Arthur Fils", sport_tag="tennis")
    old_match = ESPNMatchScore(
        event_id="old", home_name="Cameron Norrie", away_name="Rafael Jodar",
        home_score=0, away_score=2, period="Final", is_completed=True,
        is_live=False, last_updated="", linescores=[[3, 6], [3, 6]],
    )
    correct = ESPNMatchScore(
        event_id="new", home_name="Rafael Jodar", away_name="Arthur Fils",
        home_score=0, away_score=0, period="In Progress", is_completed=False,
        is_live=True, last_updated="", linescores=[[3, 3]],
    )
    # Correct listed first
    result = _find_match_via_pair(pos, [correct, old_match], "home_name", "away_name")
    assert result is not None
    assert result.event_id == "new"

    # Old listed first — skipped, correct matches
    result2 = _find_match_via_pair(pos, [old_match, correct], "home_name", "away_name")
    assert result2 is not None
    assert result2.event_id == "new"


# ── SPEC-009: Archive score events ──

def _pos_with_event(
    event_id: str = "E1",
    slug: str = "rangers-lightning",
    sport_tag: str = "nhl",
    hours_ago: float = 1.0,
    question: str = "Rangers vs. Lightning",
) -> Position:
    """event_id ve slug dolu pozisyon — archive testleri icin."""
    start = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return Position(
        condition_id="cid1", token_id="t", direction="BUY_YES",
        entry_price=0.55, size_usdc=50, shares=90,
        current_price=0.55, anchor_probability=0.55,
        confidence="B", sport_tag=sport_tag,
        question=question,
        match_start_iso=_iso(start),
        event_id=event_id,
        slug=slug,
    )


def test_score_change_logs_to_archive(tmp_path) -> None:
    """Skor degisince score_events.jsonl'e yazilir (SPEC-009)."""
    import json
    from src.infrastructure.persistence.archive_logger import ArchiveLogger

    archive = ArchiveLogger(str(tmp_path / "archive"))
    pos = _pos_with_event()

    # Ilk poll: skor 1-0
    espn = _FakeESPN([_espn_score(h_score=1, a_score=0)])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=0, poll_critical_sec=0,
        archive_logger=archive,
    )
    enricher.get_scores_if_due({"cid1": pos})

    score_file = tmp_path / "archive" / "score_events.jsonl"
    # Ilk gorunum — sadece kaydedilir, yazilmaz
    assert not score_file.exists() or score_file.read_text().strip() == ""

    # Skoru degistir: 2-0; poll interval = 0 → hemen yeniden çek
    enricher._espn = _FakeESPN([_espn_score(h_score=2, a_score=0)])
    enricher._last_poll_ts = 0.0  # zorla refresh
    enricher.get_scores_if_due({"cid1": pos})

    assert score_file.exists()
    lines = [l for l in score_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["event_id"] == "E1"
    assert event["prev_score"] == "1-0"
    assert event["new_score"] == "2-0"


def test_same_score_no_archive_log(tmp_path) -> None:
    """Skor degismezse score_events.jsonl'e yazilmaz (SPEC-009)."""
    from src.infrastructure.persistence.archive_logger import ArchiveLogger

    archive = ArchiveLogger(str(tmp_path / "archive"))
    pos = _pos_with_event()

    espn = _FakeESPN([_espn_score(h_score=1, a_score=0)])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=0, poll_critical_sec=0,
        archive_logger=archive,
    )

    # Ayni skorla 3 kez poll
    for _ in range(3):
        enricher._last_poll_ts = 0.0
        enricher.get_scores_if_due({"cid1": pos})

    score_file = tmp_path / "archive" / "score_events.jsonl"
    # Dosya ya yok ya da bos
    if score_file.exists():
        assert score_file.read_text().strip() == ""


# ── SPEC-009 Task 5: match_result logging ──

def _espn_score_completed(
    event_id: str = "E1",
    home: str = "Red Sox",
    away: str = "Yankees",
    h_score: int = 5,
    a_score: int = 3,
) -> ESPNMatchScore:
    """is_completed=True olan final skor nesnesi — match_result testleri icin."""
    return ESPNMatchScore(
        event_id=event_id,
        home_name=home, away_name=away,
        home_score=h_score, away_score=a_score,
        period="Final", is_completed=True,
        is_live=False, last_updated="", linescores=[],
        commence_time="",
    )


def _pos_with_event_mlb(
    event_id: str = "E1",
    slug: str = "red-sox-yankees",
    question: str = "Red Sox vs Yankees",
    hours_ago: float = 1.0,
) -> Position:
    """MLB pozisyonu event_id + slug dolu — match_result testleri icin."""
    start = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return Position(
        condition_id="cid1", token_id="t", direction="BUY_YES",
        entry_price=0.55, size_usdc=50, shares=90,
        current_price=0.55, anchor_probability=0.55,
        confidence="B", sport_tag="mlb",
        question=question,
        match_start_iso=_iso(start),
        event_id=event_id,
        slug=slug,
    )


def test_match_completion_logs_result(tmp_path) -> None:
    """Mac bittiginde match_results.jsonl'e yazilir (SPEC-009 Task 5)."""
    import json
    from src.infrastructure.persistence.archive_logger import ArchiveLogger

    archive = ArchiveLogger(str(tmp_path / "archive"))
    pos = _pos_with_event_mlb()

    espn = _FakeESPN([_espn_score_completed()])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=0, poll_critical_sec=0,
        archive_logger=archive,
    )
    enricher.get_scores_if_due({"cid1": pos})

    results_file = tmp_path / "archive" / "match_results.jsonl"
    assert results_file.exists()
    lines = [ln for ln in results_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["event_id"] == "E1"
    assert data["final_score"] == "5-3"
    assert data["winner_home"] is True


def test_match_completion_winner_home_false(tmp_path) -> None:
    """Away kazaninca winner_home=False yazilir (SPEC-009 Task 5)."""
    import json
    from src.infrastructure.persistence.archive_logger import ArchiveLogger

    archive = ArchiveLogger(str(tmp_path / "archive"))
    pos = _pos_with_event_mlb()

    # Away (Yankees) kazaniyor: 2-5
    espn = _FakeESPN([_espn_score_completed(h_score=2, a_score=5)])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=0, poll_critical_sec=0,
        archive_logger=archive,
    )
    enricher.get_scores_if_due({"cid1": pos})

    results_file = tmp_path / "archive" / "match_results.jsonl"
    assert results_file.exists()
    lines = [ln for ln in results_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["winner_home"] is False


def test_match_result_not_duplicated_on_restart(tmp_path) -> None:
    """Startup'ta archive'dan existing event_id'ler yuklenir - duplicate atilmaz (SPEC-009 Task 5)."""
    import json
    from src.infrastructure.persistence.archive_logger import (
        ArchiveLogger, ArchiveMatchResult,
    )

    archive_dir = tmp_path / "archive"

    # Onceden 1 match_result yazmis ol (restart oncesi)
    archive1 = ArchiveLogger(str(archive_dir))
    archive1.log_match_result(ArchiveMatchResult(
        event_id="E1", slug="red-sox-yankees", sport_tag="mlb", final_score="5-3",
        winner_home=True, completed_timestamp="2026-04-19T18:00:00Z",
    ))

    # Yeni enricher (restart sonrasi) — load_logged_match_event_ids() cagrilmali
    archive2 = ArchiveLogger(str(archive_dir))
    pos = _pos_with_event_mlb()
    espn = _FakeESPN([_espn_score_completed()])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=0, poll_critical_sec=0,
        archive_logger=archive2,
    )
    # Ayni event_id'yi tekrar gor — duplicate olmamali
    enricher.get_scores_if_due({"cid1": pos})

    results_file = archive_dir / "match_results.jsonl"
    lines = [ln for ln in results_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1  # duplicate yok


def test_match_result_no_archive_logger_does_not_crash() -> None:
    """archive_logger=None durumunda hata vermez (SPEC-009 Task 5 defensive)."""
    pos = _pos_with_event_mlb()
    espn = _FakeESPN([_espn_score_completed()])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=0, poll_critical_sec=0,
        archive_logger=None,
    )
    # Crassh olmamali
    result = enricher.get_scores_if_due({"cid1": pos})
    assert isinstance(result, dict)


# ── SPEC-010 Task 1: _find_match_via_pair yeni testler ──

def test_find_match_via_pair_exact_names() -> None:
    """pair_matcher: tam isim eslesmesi."""
    pos = _pos_with_event(
        event_id="E1",
        question="Boston Red Sox vs. New York Yankees",
        sport_tag="mlb",
    )
    scores = [
        ESPNMatchScore(
            event_id="x", home_name="Boston Red Sox", away_name="New York Yankees",
            home_score=1, away_score=0, period="Top 5th",
            is_completed=False, is_live=True, last_updated="",
            linescores=[], commence_time="",
        ),
    ]
    result = _find_match_via_pair(pos, scores, "home_name", "away_name")
    assert result is not None
    assert result.home_name == "Boston Red Sox"


def test_find_match_via_pair_swapped_order() -> None:
    """pair_matcher: home/away ters olsa bile eslesme."""
    pos = _pos_with_event(
        event_id="E1",
        question="Boston Red Sox vs. New York Yankees",
        sport_tag="mlb",
    )
    # ESPN home=Yankees, away=Red Sox (ters)
    scores = [
        ESPNMatchScore(
            event_id="x", home_name="New York Yankees", away_name="Boston Red Sox",
            home_score=3, away_score=2, period="Top 5th",
            is_completed=False, is_live=True, last_updated="",
            linescores=[], commence_time="",
        ),
    ]
    result = _find_match_via_pair(pos, scores, "home_name", "away_name")
    assert result is not None


def test_find_match_via_pair_phantom_no_match() -> None:
    """Phantom matchup: Polymarket slug gercek ESPN maciyla eslesmiyor."""
    pos = _pos_with_event(
        event_id="E1",
        question="Tampa Bay Rays vs. Pittsburgh Pirates",
        sport_tag="mlb",
    )
    # ESPN'de Tampa vs Yankees (Pittsburgh yok)
    scores = [
        ESPNMatchScore(
            event_id="x", home_name="Tampa Bay Rays", away_name="New York Yankees",
            home_score=0, away_score=1, period="Top 9th",
            is_completed=True, is_live=False, last_updated="",
            linescores=[], commence_time="",
        ),
    ]
    # Pittsburgh yok → match_pair False → None
    result = _find_match_via_pair(pos, scores, "home_name", "away_name")
    assert result is None


def test_find_match_via_pair_low_confidence_rejected() -> None:
    """Confidence < 0.80 → None."""
    pos = _pos_with_event(
        event_id="E1",
        question="Abc vs. Xyz",
        sport_tag="mlb",
    )
    scores = [
        ESPNMatchScore(
            event_id="x", home_name="Unrelated Team", away_name="Another Team",
            home_score=0, away_score=0, period="",
            is_completed=False, is_live=False, last_updated="",
            linescores=[], commence_time="",
        ),
    ]
    result = _find_match_via_pair(pos, scores, "home_name", "away_name")
    assert result is None


# ── SPEC-011: Cricket dispatch ──

def test_cricket_position_uses_cricket_client() -> None:
    """Cricket sport_tag → CricketAPIClient path used, ESPN/Odds API skipped."""
    from unittest.mock import MagicMock
    from src.infrastructure.apis.cricket_client import CricketMatchScore

    cricket_client = MagicMock()
    cricket_client.get_current_matches.return_value = [
        CricketMatchScore(
            match_id="m1",
            name="India vs Australia",
            match_type="t20",
            teams=["India", "Australia"],
            status="live",
            match_started=True,
            match_ended=False,
            venue="",
            date_time_gmt="",
            innings=[
                {"runs": 150, "wickets": 6, "overs": 20.0, "team": "Australia", "inning_num": 1},
                {"runs": 80, "wickets": 5, "overs": 12.0, "team": "India", "inning_num": 2},
            ],
        ),
    ]
    espn = _FakeESPN([])
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=None,
        poll_normal_sec=0, poll_critical_sec=0,
        match_window_hours=999,
        cricket_client=cricket_client,
    )
    pos = _pos_with_event(
        event_id="cric1",
        question="India vs Australia",
        sport_tag="cricket",
    )
    result = enricher.get_scores_if_due({"cid1": pos})
    # cricket_client was called, ESPN was NOT called (cricket short-circuits)
    assert cricket_client.get_current_matches.called
    assert espn.call_count == 0
    # result contains score_info for the cricket position
    assert "cid1" in result
    assert result["cid1"]["available"] is True


def test_cricket_without_client_skips_silently() -> None:
    """cricket_client=None → cricket position skipped cleanly, no crash."""
    enricher = ScoreEnricher(
        espn_client=None, odds_client=None,
        cricket_client=None,
    )
    assert enricher._cricket_client is None
    pos = _pos_with_event(
        event_id="cric2",
        question="India vs Australia",
        sport_tag="cricket",
    )
    # Should not raise; cricket position simply yields no result
    result = enricher.get_scores_if_due({"cid1": pos})
    assert "cid1" not in result
