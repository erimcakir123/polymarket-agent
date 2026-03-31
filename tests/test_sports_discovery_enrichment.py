"""Test enrichment integration in SportsDiscovery."""
from unittest.mock import MagicMock, patch
from src.sports_discovery import SportsDiscovery, DiscoveryResult


def test_resolve_espn_includes_enrichment():
    """resolve() should include enrichment context when available."""
    espn = MagicMock()
    espn.get_match_context.return_value = "=== SPORTS DATA (ESPN) -- NBA ===\nTeam A: 40-20"
    espn.get_espn_odds.return_value = {
        "team_a": "Lakers", "team_b": "Celtics",
        "bookmaker_prob_a": 0.55, "bookmaker_prob_b": 0.45,
        "num_bookmakers": 3,
    }
    enrichment = MagicMock()
    enrichment.enrich.return_value = "=== ESPN ENRICHMENT ===\nStandings: #3"

    discovery = SportsDiscovery(
        espn=espn, pandascore=MagicMock(), cricket=MagicMock(),
        odds_api=MagicMock(), enrichment=enrichment,
    )

    result = discovery.resolve("Will Lakers beat Celtics?", "nba-lal-bos", ["nba"])
    assert result is not None
    assert "SPORTS DATA" in result.context
    assert "BOOKMAKER ODDS" in result.context
    assert "ESPN ENRICHMENT" in result.context
    assert result.espn_odds is not None


def test_resolve_espn_no_enrichment():
    """resolve() should still work when enrichment returns None."""
    espn = MagicMock()
    espn.get_match_context.return_value = "=== SPORTS DATA ==="
    espn.get_espn_odds.return_value = None
    enrichment = MagicMock()
    enrichment.enrich.return_value = None

    discovery = SportsDiscovery(
        espn=espn, pandascore=MagicMock(), cricket=MagicMock(),
        odds_api=MagicMock(), enrichment=enrichment,
    )

    result = discovery.resolve("Will A beat B?", "nba-lal-bos", ["nba"])
    assert result is not None
    assert "SPORTS DATA" in result.context
    assert "BOOKMAKER" not in result.context
