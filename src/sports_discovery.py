"""Unified sports data discovery -- routes markets to the correct API dynamically.

Replaces the old 5-tier cascade (Bridge->ESPN->football-data->CricketData->TheSportsDB)
with a simple 3-way router: esports -> PandaScore, cricket -> CricketData, else -> ESPN.
No hardcoded slug/keyword mappings -- each API uses its own search endpoints.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from src.sport_rules import ESPORTS_SLUGS

if TYPE_CHECKING:
    from src.sports_data import SportsDataClient
    from src.esports_data import EsportsDataClient
    from src.cricket_data import CricketDataClient
    from src.odds_api import OddsAPIClient
    from src.espn_enrichment import ESPNEnrichment

logger = logging.getLogger(__name__)

# Lightweight route detection -- categorization, not discovery
_CRICKET_SLUGS = frozenset({"ipl", "psl", "t20", "crint", "cricpakt20cup", "criclcl"})


@dataclass
class DiscoveryResult:
    """Result from sports data discovery."""
    context: str      # Sports context string for AI analyst
    source: str       # "ESPN", "PandaScore", "CricketData"
    confidence: str   # Always "A" -- all sources are reliable
    espn_odds: Optional[dict] = None  # ESPN odds data (if available)


class SportsDiscovery:
    """Single entry point for all sports data resolution.

    Thin orchestrator -- routes markets to the correct API based on
    lightweight categorization (esports/cricket/everything else).
    """

    def __init__(
        self,
        espn: "SportsDataClient",
        pandascore: "EsportsDataClient",
        cricket: "CricketDataClient",
        odds_api: "OddsAPIClient",
        enrichment: "ESPNEnrichment | None" = None,
    ) -> None:
        self.espn = espn
        self.pandascore = pandascore
        self.cricket = cricket
        self.odds_api = odds_api
        self.enrichment = enrichment

    def resolve(
        self, question: str, slug: str, tags: list[str],
    ) -> Optional[DiscoveryResult]:
        """Route market to correct API, return context or None."""
        route = self._detect_route(question, slug, tags)

        try:
            if route == "esports":
                ctx = self.pandascore.get_match_context(question, tags)
                if ctx:
                    return DiscoveryResult(context=ctx, source="PandaScore", confidence="A")

            elif route == "cricket":
                ctx = self.cricket.get_match_context(question, slug, tags)
                if ctx:
                    return DiscoveryResult(context=ctx, source="CricketData", confidence="A")

            else:  # espn
                ctx = self.espn.get_match_context(question, slug, tags)
                if ctx:
                    espn_odds = self.espn.get_espn_odds(question, slug, tags)

                    # Enrichment: athlete-specific extras only
                    # (team enrichment is now in sports_data.py._get_team_match_context)
                    enrichment_ctx = None
                    if self.enrichment:
                        try:
                            enrichment_ctx = self.enrichment.enrich(question, slug, tags)
                        except Exception as exc:
                            logger.warning("Enrichment error for '%s': %s", slug[:40], exc)

                    # Combine context
                    parts = [ctx]
                    if espn_odds:
                        parts.append(
                            f"\n=== BOOKMAKER ODDS (ESPN) ===\n"
                            f"{espn_odds.get('team_a', '?')} "
                            f"{espn_odds.get('bookmaker_prob_a', 0):.0%} vs "
                            f"{espn_odds.get('team_b', '?')} "
                            f"{espn_odds.get('bookmaker_prob_b', 0):.0%} "
                            f"({espn_odds.get('num_bookmakers', 0)} bookmakers)"
                        )
                    if enrichment_ctx:
                        parts.append(enrichment_ctx)
                    full_context = "\n".join(parts)

                    return DiscoveryResult(
                        context=full_context, source="ESPN",
                        confidence="A", espn_odds=espn_odds,
                    )

        except Exception as exc:
            logger.warning("Discovery error (%s) for '%s': %s", route, slug[:40], exc)

        return None

    def _detect_route(self, question: str, slug: str, tags: list[str]) -> str:
        """Lightweight categorization: 'esports', 'cricket', or 'espn'."""
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        tags_lower = {t.lower() for t in tags}

        # Esports: tag or slug prefix
        if "esports" in tags_lower or slug_prefix in ESPORTS_SLUGS:
            return "esports"
        if any(game in tags_lower for game in ESPORTS_SLUGS):
            return "esports"

        # Cricket: tag, slug, or question keyword
        if "cricket" in tags_lower or slug_prefix in _CRICKET_SLUGS:
            return "cricket"
        if "cricket" in question.lower():
            return "cricket"

        # Everything else -> ESPN
        return "espn"
