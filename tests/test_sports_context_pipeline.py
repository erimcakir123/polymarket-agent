"""Test that ESPN + TheSportsDB sports context is fetched for non-esports markets."""
from unittest.mock import MagicMock, patch


def _make_gate(sports=None):
    from src.entry_gate import EntryGate
    cfg = MagicMock()
    cfg.edge.min_edge = 0.06
    cfg.edge.fill_ratio_scaling = False
    cfg.ai.batch_size = 10
    cfg.risk.max_positions = 10
    gate = EntryGate.__new__(EntryGate)
    gate.config = cfg
    gate.portfolio = MagicMock()
    gate.portfolio.active_position_count = 0
    gate.odds_api = MagicMock()
    gate.odds_api.available = False
    gate.esports = MagicMock()
    gate.esports.get_match_context = MagicMock(return_value=None)
    gate.news_scanner = MagicMock()
    gate.news_scanner.search_for_markets = MagicMock(return_value={})
    gate.news_scanner.build_news_context = MagicMock(return_value="")
    gate.ai = MagicMock()
    gate.ai.analyze_batch = MagicMock(return_value=[])
    gate.trade_log = MagicMock()
    gate.sports = sports or MagicMock()
    gate.scout = None
    gate._far_market_ids = set()
    gate._analyzed_market_ids = {}
    gate._seen_market_ids = set()
    gate._breaking_news_detected = False
    gate._candidate_stock = []
    gate._fav_stock = []
    gate._far_stock = []
    gate._eligible_cache = []
    gate._eligible_pointer = 0
    gate._eligible_cache_ts = 0.0
    from src.thesportsdb import TheSportsDBClient
    gate.tsdb = TheSportsDBClient()
    return gate


def _make_market(cid="cid-001", slug="mlb-nyy-bos", question="Will NY Yankees beat Boston?", sport_tag=""):
    m = MagicMock()
    m.condition_id = cid
    m.slug = slug
    m.question = question
    m.sport_tag = sport_tag
    m.yes_price = 0.60
    m.end_date_iso = "2026-04-01T00:00:00Z"
    m.match_start_iso = None
    return m


def test_espn_context_fetched_for_sports_market():
    """ESPN get_match_context should be called for non-esports markets."""
    mock_sports = MagicMock()
    mock_sports.get_match_context = MagicMock(return_value="=== SPORTS DATA (ESPN) ===\nTeam A: 15-10")
    gate = _make_gate(sports=mock_sports)

    market = _make_market()
    with patch("src.entry_gate.is_esports_slug", return_value=False):
        # Call _analyze_batch directly
        gate._analyze_batch([market], cycle_count=0)

    mock_sports.get_match_context.assert_called_once()


def test_tsdb_fallback_when_espn_returns_none():
    """TheSportsDB should be tried when ESPN returns None."""
    mock_sports = MagicMock()
    mock_sports.get_match_context = MagicMock(return_value=None)
    gate = _make_gate(sports=mock_sports)

    market = _make_market(slug="soccer-uru-bra", question="Uruguay vs Brazil: Who will win?")
    with patch.object(gate.tsdb, "get_match_context", return_value="=== SPORTS DATA (TheSportsDB) ===") as mock_tsdb:
        with patch("src.entry_gate.is_esports_slug", return_value=False):
            gate._analyze_batch([market], cycle_count=0)
    mock_tsdb.assert_called_once()


def test_sports_context_skipped_for_esports():
    """ESPN/TheSportsDB should NOT be called for esports markets."""
    mock_sports = MagicMock()
    mock_sports.get_match_context = MagicMock(return_value="ESPN data")
    gate = _make_gate(sports=mock_sports)
    gate.esports.get_match_context = MagicMock(return_value="=== ESPORTS DATA ===")

    market = _make_market(slug="cs2-team-a-vs-b", sport_tag="cs2")
    with patch("src.entry_gate.is_esports_slug", return_value=True):
        gate._analyze_batch([market], cycle_count=0)

    mock_sports.get_match_context.assert_not_called()
