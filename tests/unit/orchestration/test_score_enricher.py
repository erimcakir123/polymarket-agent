"""Score enricher testleri (SPEC-005 Task 4 — ESPN primary + Odds API fallback)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.infrastructure.apis.score_client import MatchScore
from src.models.position import Position
from src.orchestration.score_enricher import (
    ScoreEnricher,
    _build_score_info,
    _find_espn_match,
    _find_match,
    _is_within_match_window,
    _team_match,
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


# ── team matching ──

def test_team_match_exact() -> None:
    assert _team_match("Rangers", "Rangers")


def test_team_match_substring() -> None:
    assert _team_match("Rangers", "New York Rangers")


def test_team_match_last_word() -> None:
    assert _team_match("New York Rangers", "NY Rangers")


def test_team_match_no_match() -> None:
    assert not _team_match("Sharks", "New York Rangers")


# ── match window ──

def test_within_match_window() -> None:
    pos = _pos(hours_ago=2.0)
    assert _is_within_match_window(pos, window_hours=4.0)


def test_outside_match_window() -> None:
    pos = _pos(hours_ago=6.0)
    assert not _is_within_match_window(pos, window_hours=4.0)


# ── find_match (Odds API MatchScore) ──

def test_find_match_by_team_name() -> None:
    pos = _pos(question="Rangers vs. Lightning")
    ms = _ms(home="New York Rangers", away="Tampa Bay Lightning")
    result = _find_match(pos, [ms])
    assert result is not None
    assert result.event_id == "e1"


def test_find_match_no_match() -> None:
    pos = _pos(question="Sharks vs. Jets")
    ms = _ms(home="New York Rangers", away="Tampa Bay Lightning")
    assert _find_match(pos, [ms]) is None


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


# ── _find_espn_match ──

def test_find_espn_match_skips_wrong_match_same_player() -> None:
    """Two-team position must not match ESPN entry with only one matching player."""
    pos = _pos(question="Rafael Jodar vs Arthur Fils", sport_tag="tennis")
    old_match = ESPNMatchScore(
        event_id="old", home_name="Cameron Norrie", away_name="Rafael Jodar",
        home_score=0, away_score=2, period="Final", is_completed=True,
        is_live=False, last_updated="", linescores=[[3, 6], [3, 6]],
    )
    assert _find_espn_match(pos, [old_match]) is None


def test_find_espn_match_correct_two_team() -> None:
    """Two-team position matches when both players found."""
    pos = _pos(question="Rafael Jodar vs Arthur Fils", sport_tag="tennis")
    correct = ESPNMatchScore(
        event_id="new", home_name="Rafael Jodar", away_name="Arthur Fils",
        home_score=0, away_score=0, period="In Progress", is_completed=False,
        is_live=True, last_updated="", linescores=[[3, 3]],
    )
    result = _find_espn_match(pos, [correct])
    assert result is not None
    assert result.event_id == "new"


def test_find_espn_match_single_team_fallback() -> None:
    """Single-team position (no team_b) still uses fallback matching."""
    pos = _pos(question="Will Tiger Woods win?", sport_tag="golf")
    espn = ESPNMatchScore(
        event_id="g1", home_name="Tiger Woods", away_name="Rory McIlroy",
        home_score=None, away_score=None, period="", is_completed=False,
        is_live=False, last_updated="",
    )
    result = _find_espn_match(pos, [espn])
    assert result is not None
    assert result.event_id == "g1"


def test_find_espn_match_prefers_correct_over_old() -> None:
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
    result = _find_espn_match(pos, [correct, old_match])
    assert result is not None
    assert result.event_id == "new"

    # Old listed first — skipped, correct matches
    result2 = _find_espn_match(pos, [old_match, correct])
    assert result2 is not None
    assert result2.event_id == "new"


# ── SPEC-009: Archive score events ──

def _pos_with_event(
    event_id: str = "E1",
    slug: str = "rangers-lightning",
    sport_tag: str = "nhl",
    hours_ago: float = 1.0,
) -> Position:
    """event_id ve slug dolu pozisyon — archive testleri icin."""
    start = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return Position(
        condition_id="cid1", token_id="t", direction="BUY_YES",
        entry_price=0.55, size_usdc=50, shares=90,
        current_price=0.55, anchor_probability=0.55,
        confidence="B", sport_tag=sport_tag,
        question="Rangers vs. Lightning",
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
