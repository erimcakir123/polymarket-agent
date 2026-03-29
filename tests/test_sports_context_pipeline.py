"""Test that SportsDiscovery context is fetched for non-esports markets."""
from unittest.mock import MagicMock, patch


def _make_gate(discovery=None):
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
    gate.portfolio.positions = {}
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
    gate.discovery = discovery or MagicMock()
    gate.scout = None
    gate._early_market_ids = set()
    gate._analyzed_market_ids = {}
    gate._seen_market_ids = set()
    gate._confidence_c_cids = set()
    gate._breaking_news_detected = False
    gate._candidate_stock = []
    gate._fav_stock = []
    gate._early_stock = []
    gate._eligible_cache = []
    gate._eligible_pointer = 0
    gate._eligible_cache_ts = 0.0
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
    m.tags = []
    return m


def test_discovery_called_for_sports_market():
    """SportsDiscovery.resolve() should be called for non-esports markets."""
    from src.sports_discovery import DiscoveryResult
    mock_discovery = MagicMock()
    mock_discovery.resolve = MagicMock(return_value=DiscoveryResult(
        context="=== SPORTS DATA (ESPN) ===\nTeam A: 15-10",
        source="ESPN",
        confidence="A",
    ))
    gate = _make_gate(discovery=mock_discovery)

    market = _make_market()
    with patch("src.entry_gate.is_esports_slug", return_value=False):
        gate._analyze_batch([market], cycle_count=0)

    mock_discovery.resolve.assert_called_once()


def test_discovery_skipped_for_esports():
    """SportsDiscovery should NOT be called for esports markets (PandaScore handles them)."""
    mock_discovery = MagicMock()
    gate = _make_gate(discovery=mock_discovery)
    gate.esports.get_match_context = MagicMock(return_value="=== ESPORTS DATA ===")

    market = _make_market(slug="cs2-team-a-vs-b", sport_tag="cs2")
    with patch("src.entry_gate.is_esports_slug", return_value=True):
        gate._analyze_batch([market], cycle_count=0)

    mock_discovery.resolve.assert_not_called()


def test_no_data_markets_skipped():
    """Markets without any sports context should be skipped (not sent to AI)."""
    mock_discovery = MagicMock()
    mock_discovery.resolve = MagicMock(return_value=None)  # No data
    gate = _make_gate(discovery=mock_discovery)

    market = _make_market(slug="unknown-xyz-abc", question="Unknown Sport: X vs Y")
    with patch("src.entry_gate.is_esports_slug", return_value=False):
        result = gate._analyze_batch([market], cycle_count=0)

    # Should return empty — no markets with data
    assert result == ([], {})
