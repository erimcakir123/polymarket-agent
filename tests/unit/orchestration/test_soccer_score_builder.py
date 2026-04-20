"""Soccer score builder helper tests (SPEC-015)."""


class _Pos:
    """Minimal Position stub for testing."""
    def __init__(self, question="", direction="BUY_YES", tags=None):
        self.question = question
        self.direction = direction
        self.tags = tags or []


def test_determine_our_outcome_buy_yes_home() -> None:
    from src.orchestration.soccer_score_builder import determine_our_outcome
    pos = _Pos(question="Will Arsenal win?", direction="BUY_YES")
    assert determine_our_outcome(pos) == "home"


def test_determine_our_outcome_buy_no_away() -> None:
    from src.orchestration.soccer_score_builder import determine_our_outcome
    pos = _Pos(question="Will Arsenal win?", direction="BUY_NO")
    assert determine_our_outcome(pos) == "away"


def test_determine_our_outcome_draw_keyword() -> None:
    from src.orchestration.soccer_score_builder import determine_our_outcome
    pos = _Pos(question="Will the match end in a draw?", direction="BUY_YES")
    assert determine_our_outcome(pos) == "draw"


def test_is_knockout_competition_champions_league() -> None:
    from src.orchestration.soccer_score_builder import is_knockout_competition
    pos = _Pos(question="Will Real Madrid win the Champions League final?")
    assert is_knockout_competition(pos) is True


def test_is_knockout_competition_league_match() -> None:
    from src.orchestration.soccer_score_builder import is_knockout_competition
    pos = _Pos(question="Will Arsenal win?", tags=["soccer", "epl"])
    assert is_knockout_competition(pos) is False


def test_is_knockout_competition_cup_in_question() -> None:
    from src.orchestration.soccer_score_builder import is_knockout_competition
    pos = _Pos(question="FA Cup: Will Liverpool beat Manchester City?")
    assert is_knockout_competition(pos) is True


def test_is_knockout_competition_tag_based() -> None:
    from src.orchestration.soccer_score_builder import is_knockout_competition
    pos = _Pos(question="Will X win?", tags=["soccer", "europa-league"])
    assert is_knockout_competition(pos) is True
