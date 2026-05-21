"""MLB Submarket Engine — real implementation of Plan 1 Protocol.

SPEC-R Plan 4 T2. Orchestrates Plan 2 (domain math) + Plan 3 (data clients).
Implements MlbSubmarketEngineProtocol: process(market) -> Signal | None.

Plan 4 simplifications (v2 TODO items):
- Marcel multi-season weighting deferred (raw Statcast current season only).
- Bullpen segmentation deferred (starter pitches all 9 innings).
- TTO simplified: rough ((inning-1)//3 + 1) instead of full PA tracking.
- Handedness lookup deferred: default R/R matchup for all batters/pitchers.
- DH detection deferred: always 9-inning game.
- Team matching deferred: picks first game in schedule for that date.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from src.config.settings import MlbSubmarketConfig
from src.domain.mlb_submarket.edge_candidate import EdgeCandidate
from src.domain.mlb_submarket.game_simulator import simulate_game
from src.domain.mlb_submarket.league_constants import LEAGUE_PA_RATES
from src.domain.mlb_submarket.pa_outcome import PAContext, compute_pa_outcome
from src.domain.mlb_submarket.spread_pricer import spread_probability
from src.domain.mlb_submarket.totals_pricer import totals_probability
from src.infrastructure.mlb_data.rate_cache import RateCache
from src.infrastructure.mlb_data.statcast_client import StatcastClient, StatcastError
from src.infrastructure.mlb_data.statsapi_client import StatsApiClient, StatsApiError
from src.infrastructure.mlb_data.weather_client import WeatherClient, WeatherError
from src.models.market import MarketData
from src.models.signal import Signal
from src.strategy.entry.mlb_signal_adapter import mlb_candidate_to_signal

logger = logging.getLogger(__name__)

_TIER_A_EDGE_THRESHOLD = 0.07
_DEFAULT_MC_ITERATIONS = 1_000  # Plan 4 — lower than Plan 2 default for speed

# Slug patterns:
#   totals:   mlb-{away}-{home}-{YYYY-MM-DD}-total-{N}pt5
#   run_line: mlb-{away}-{home}-{YYYY-MM-DD}-spread-{pos|neg}1pt5
_SLUG_TOTALS_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})-total-(\d+)pt5$"
)
_SLUG_RUN_LINE_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})-spread-(pos|neg)1pt5$"
)


class MlbSubmarketEngine:
    """MLB totals/run-line signal producer.

    Wires:
    - Plan 3 clients (StatsApiClient, StatcastClient, WeatherClient, RateCache)
    - Plan 2 domain math (pa_outcome, game_simulator, totals_pricer, spread_pricer)
    - Plan 4 T1 adapter (mlb_candidate_to_signal)

    Constructor has 8 dependencies — within the Kural 4 limit because all are
    mandatory data-source injections (no hidden singletons).
    """

    def __init__(
        self,
        statsapi: StatsApiClient,
        statcast: StatcastClient,
        weather: WeatherClient,
        rate_cache: RateCache,
        config: MlbSubmarketConfig,
        ballpark_metadata: dict[str, dict[str, Any]],
        league_rates: dict[str, float] | None = None,
        fixed_bet_usdc: dict[str, float] | None = None,
    ) -> None:
        self.statsapi = statsapi
        self.statcast = statcast
        self.weather = weather
        self.rate_cache = rate_cache
        self.config = config
        self.ballpark_metadata = ballpark_metadata
        self.league_rates = league_rates or LEAGUE_PA_RATES
        self.fixed_bet_usdc = fixed_bet_usdc or {"A": 50.0, "B": 30.0}

    # ------------------------------------------------------------------
    # Public API (Protocol implementation)
    # ------------------------------------------------------------------

    def process(self, market: MarketData) -> Signal | None:
        """Evaluate one Polymarket market; return Signal if edge qualifies.

        Returns None on: parse failure, data unavailability, or sub-threshold edge.
        """
        parsed = self._parse_slug(getattr(market, "slug", "") or "")
        if parsed is None:
            return None
        date_str, market_type, line = parsed

        try:
            schedule = self.statsapi.get_schedule(date_str)
        except StatsApiError as e:
            logger.info("mlb_engine: schedule fetch failed for %s: %s", date_str, e)
            return None

        if not schedule:
            return None

        # Plan 4 simplification: pick first game for that date.
        # v2 will match by away/home team_id parsed from slug.
        game = schedule[0]
        game_pk = game.get("gamePk")
        if game_pk is None:
            return None

        # Lineup
        try:
            lineup = self.statsapi.get_lineup(game_pk)
        except StatsApiError as e:
            logger.info("mlb_engine: lineup fetch failed for game %s: %s", game_pk, e)
            return None
        if not lineup.get("home") or not lineup.get("away"):
            logger.info("mlb_engine: lineup not posted for game %s", game_pk)
            return None
        if len(lineup["home"]) != 9 or len(lineup["away"]) != 9:
            logger.info("mlb_engine: lineup incomplete for game %s", game_pk)
            return None

        # Probable pitchers
        try:
            pitchers = self.statsapi.get_probable_pitchers(date_str).get(game_pk, {})
        except StatsApiError as e:
            logger.info("mlb_engine: probable pitchers fetch failed: %s", e)
            return None
        home_pitcher_id = pitchers.get("home_pitcher_id")
        away_pitcher_id = pitchers.get("away_pitcher_id")
        if home_pitcher_id is None or away_pitcher_id is None:
            return None

        # Rates (cache → Statcast fallback)
        season = int(date_str[:4])
        try:
            home_pitcher_rates = self._get_pitcher_rates(home_pitcher_id, season)
            away_pitcher_rates = self._get_pitcher_rates(away_pitcher_id, season)
            home_batter_rates = [
                self._get_batter_rates(b, season) for b in lineup["home"]
            ]
            away_batter_rates = [
                self._get_batter_rates(b, season) for b in lineup["away"]
            ]
        except StatcastError as e:
            logger.info("mlb_engine: Statcast fetch failed: %s", e)
            return None

        all_rates = (
            [home_pitcher_rates, away_pitcher_rates]
            + home_batter_rates
            + away_batter_rates
        )
        if any(not r for r in all_rates):
            logger.info("mlb_engine: rates missing for some players, skipping")
            return None

        # Fetch handedness for pitchers + all batters
        try:
            home_pitcher_hand = self.statsapi.get_player_handedness(
                home_pitcher_id
            )["pitch_hand"]
            away_pitcher_hand = self.statsapi.get_player_handedness(
                away_pitcher_id
            )["pitch_hand"]
            home_batter_hands = [
                self.statsapi.get_player_handedness(b)["bat_side"]
                for b in lineup["home"]
            ]
            away_batter_hands = [
                self.statsapi.get_player_handedness(b)["bat_side"]
                for b in lineup["away"]
            ]
        except StatsApiError as e:
            logger.info("mlb_engine: handedness fetch failed: %s", e)
            return None

        # Weather — Plan 4 simplification: use first ballpark in metadata.
        # v2: map home team_id → ballpark_id → metadata entry.
        park_meta = next(iter(self.ballpark_metadata.values()), None)
        if park_meta is None:
            logger.info("mlb_engine: no ballpark metadata available")
            return None
        try:
            game_time_iso = f"{date_str}T19:00"  # Plan 4: 7 PM local (UTC approx)
            weather_cond = self.weather.get_conditions(
                park_meta["lat"], park_meta["lon"], game_time_iso,
            )
        except (WeatherError, ValueError) as e:
            logger.info("mlb_engine: weather fetch failed: %s", e)
            return None

        # Build per-inning lineup rate lists with real handedness
        home_per_inning = self._build_inning_lineups(
            home_batter_rates, home_batter_hands,
            away_pitcher_rates, away_pitcher_hand,
            park_meta, weather_cond,
        )
        away_per_inning = self._build_inning_lineups(
            away_batter_rates, away_batter_hands,
            home_pitcher_rates, home_pitcher_hand,
            park_meta, weather_cond,
        )

        # Simulate
        home_dist, away_dist = simulate_game(
            home_per_inning, away_per_inning,
            dh_game=False,
            mc_iterations=_DEFAULT_MC_ITERATIONS,
            seed=42,
        )

        # Price market
        if market_type == "totals":
            p_over, _p_under = totals_probability(home_dist, away_dist, line)
            model_p = p_over  # market YES = over
        else:  # run_line
            home_line = line  # e.g., -1.5 or +1.5
            p_home, _p_away = spread_probability(home_dist, away_dist, home_line)
            model_p = p_home

        market_p: float = market.yes_price
        edge = model_p - market_p

        tier = self._classify_tier(abs(edge), self.config.min_edge)
        if tier is None:
            return None

        candidate = EdgeCandidate(
            model_p=model_p,
            market_p=market_p,
            edge=edge,
            market_type=market_type,
            line=line,
        )
        return mlb_candidate_to_signal(
            candidate, market, tier=tier, fixed_bet_usdc=self.fixed_bet_usdc,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_slug(self, slug: str) -> tuple[str, str, float] | None:
        """Parse slug → (date_str, market_type, line). Returns None on mismatch."""
        m_t = _SLUG_TOTALS_RE.match(slug)
        if m_t:
            _away, _home, date, n = m_t.groups()
            return date, "totals", float(n) + 0.5
        m_r = _SLUG_RUN_LINE_RE.match(slug)
        if m_r:
            _away, _home, date, sign = m_r.groups()
            line = -1.5 if sign == "neg" else 1.5
            return date, "run_line", line
        return None

    def _get_batter_rates(self, mlbam_id: int, season: int) -> dict[str, float]:
        cached = self.rate_cache.get(mlbam_id, season, "batter")
        if cached:
            return cached
        rates = self.statcast.get_batter_rates(mlbam_id, season)
        if rates:
            self.rate_cache.put(mlbam_id, season, "batter", rates)
        return rates

    def _get_pitcher_rates(self, mlbam_id: int, season: int) -> dict[str, float]:
        cached = self.rate_cache.get(mlbam_id, season, "pitcher")
        if cached:
            return cached
        rates = self.statcast.get_pitcher_rates(mlbam_id, season)
        if rates:
            self.rate_cache.put(mlbam_id, season, "pitcher", rates)
        return rates

    def _build_inning_lineups(
        self,
        batter_rates: list[dict[str, float]],
        batter_hands: list[str],
        pitcher_rates: dict[str, float],
        pitcher_hand: str,
        park_meta: dict[str, Any],
        weather: dict[str, float],
    ) -> list[list[dict[str, float]]]:
        """Build per-inning 9-batter PA outcome lists using real handedness.

        Plan 4 simplification: same lineup each inning; CF wind computed once
        from ballpark orientation.
        """
        cf_deg = park_meta.get("cf_orientation_deg", 0.0)
        wind_dir = weather["wind_dir_deg"]
        dir_diff = (wind_dir - cf_deg + 360) % 360
        if dir_diff <= 45 or dir_diff >= 315:
            wind_to_cf = weather["wind_mph"]    # blowing OUT to CF (positive)
        elif 135 <= dir_diff <= 225:
            wind_to_cf = -weather["wind_mph"]   # blowing IN from CF
        else:
            wind_to_cf = 0.0                    # crosswind

        innings = []
        for inning in range(1, 10):
            inning_lineup = []
            for b_rates, b_hand in zip(batter_rates, batter_hands):
                ctx: PAContext = {
                    "park_id": park_meta.get("park_id", ""),
                    "batter_hand": b_hand,
                    "pitcher_hand": pitcher_hand,
                    "times_through": min(((inning - 1) // 3) + 1, 4),  # rough TTO
                    "wind_mph_to_cf": wind_to_cf,
                    "temp_f": weather["temp_f"],
                    "humidity_pct": weather["humidity_pct"],
                }
                inning_lineup.append(compute_pa_outcome(
                    batter_rates=b_rates,
                    pitcher_rates=pitcher_rates,
                    league_rates=self.league_rates,
                    context=ctx,
                ))
            innings.append(inning_lineup)
        return innings

    @staticmethod
    def _classify_tier(edge_magnitude: float, min_edge: float) -> str | None:
        """Return "A", "B", or None based on edge size."""
        if edge_magnitude >= _TIER_A_EDGE_THRESHOLD:
            return "A"
        if edge_magnitude >= min_edge:
            return "B"
        return None
