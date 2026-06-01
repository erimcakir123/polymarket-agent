"""Agent dependency injection factory — tüm katmanları inşa edip Agent döner.

main.py burayı çağırır. Test izolasyonu için agent.py DI container
(AgentDeps) üzerinden çalışır; factory sadece production wiring yapar.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.config.settings import AppConfig, Mode
from src.infrastructure.data.sackmann_refresher import (
    is_cache_stale,
    refresh_if_stale,
)
from src.domain.guards.manipulation import ManipulationCheck, check_market as manipulation_check
from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.apis.espn_client import ESPNClient
from src.infrastructure.apis.gamma_client import GammaClient
from src.infrastructure.apis.odds_client import OddsAPIClient
from src.infrastructure.executor import Executor
from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.stock_snapshot import StockSnapshot
from src.infrastructure.telegram.command_poller import TelegramCommandPoller
from src.infrastructure.websocket.price_feed import PriceFeed
from src.orchestration._factory_loggers import build_equity_logger, build_trade_logger
from src.orchestration.agent import Agent, AgentDeps
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.scanner import MarketScanner
from src.orchestration.score_enricher import ScoreEnricher
from src.orchestration.startup import RuntimeState
from src.orchestration.stock_queue import StockConfig, StockQueue
from src.orchestration.tennis_start_enricher import TennisStartEnricher
from src.infrastructure.data.basketball.team_ratings_store import (
    load_team_snapshots,
)
from src.infrastructure.data.calibration_store import load_calibration as load_tennis_calibration
from src.infrastructure.data.tennis_ratings_store import load_ratings as load_tennis_ratings
from src.strategy.entry.gate import EntryGate, GateConfig
from src.strategy.entry.mlb_submarket_engine_protocol import MlbSubmarketEngineProtocol
from src.strategy.enrichment.basketball_dispatch import (
    enrich_with_basketball_dispatch,
)
from src.strategy.enrichment.odds_enricher import enrich_market
from src.strategy.enrichment.tennis_dispatch import enrich_with_tennis_dispatch

logger = logging.getLogger(__name__)

# All 30 active MLB ballparks (2024-2026 season).
# lat/lon rounded to 4 decimals; cf_orientation_deg = direction CF points (0=N, 90=E, 180=S, 270=W).
_DEFAULT_BALLPARK_METADATA: dict[str, dict[str, Any]] = {
    "COORS":            {"park_id": "COORS",            "lat": 39.7559, "lon": -104.9942, "cf_orientation_deg": 0.0},
    "FENWAY":           {"park_id": "FENWAY",           "lat": 42.3467, "lon": -71.0972,  "cf_orientation_deg": 75.0},
    "YANKEE":           {"park_id": "YANKEE",           "lat": 40.8296, "lon": -73.9262,  "cf_orientation_deg": 60.0},
    "DODGER":           {"park_id": "DODGER",           "lat": 34.0739, "lon": -118.2400, "cf_orientation_deg": 0.0},
    "PETCO":            {"park_id": "PETCO",            "lat": 32.7073, "lon": -117.1566, "cf_orientation_deg": 0.0},
    "WRIGLEY":          {"park_id": "WRIGLEY",          "lat": 41.9484, "lon": -87.6553,  "cf_orientation_deg": 70.0},
    "BUSCH":            {"park_id": "BUSCH",            "lat": 38.6226, "lon": -90.1928,  "cf_orientation_deg": 30.0},
    "GLOBE_LIFE":       {"park_id": "GLOBE_LIFE",       "lat": 32.7473, "lon": -97.0817,  "cf_orientation_deg": 0.0},
    "GREAT_AMERICAN":   {"park_id": "GREAT_AMERICAN",   "lat": 39.0975, "lon": -84.5067,  "cf_orientation_deg": 320.0},
    "CITIZENS_BANK":    {"park_id": "CITIZENS_BANK",    "lat": 39.9061, "lon": -75.1665,  "cf_orientation_deg": 30.0},
    "AMERICAN_FAMILY":  {"park_id": "AMERICAN_FAMILY",  "lat": 43.0280, "lon": -87.9712,  "cf_orientation_deg": 0.0},
    "TARGET":           {"park_id": "TARGET",           "lat": 44.9817, "lon": -93.2776,  "cf_orientation_deg": 0.0},
    "KAUFFMAN":         {"park_id": "KAUFFMAN",         "lat": 39.0517, "lon": -94.4803,  "cf_orientation_deg": 90.0},
    "PROGRESSIVE":      {"park_id": "PROGRESSIVE",      "lat": 41.4962, "lon": -81.6852,  "cf_orientation_deg": 90.0},
    "GUARANTEED_RATE":  {"park_id": "GUARANTEED_RATE",  "lat": 41.8300, "lon": -87.6338,  "cf_orientation_deg": 0.0},
    "ROGERS":           {"park_id": "ROGERS",           "lat": 43.6414, "lon": -79.3894,  "cf_orientation_deg": 0.0},
    "ORACLE":           {"park_id": "ORACLE",           "lat": 37.7786, "lon": -122.3893, "cf_orientation_deg": 0.0},
    "CHASE":            {"park_id": "CHASE",            "lat": 33.4453, "lon": -112.0667, "cf_orientation_deg": 0.0},
    "T_MOBILE":         {"park_id": "T_MOBILE",         "lat": 47.5914, "lon": -122.3325, "cf_orientation_deg": 0.0},
    "ANGEL":            {"park_id": "ANGEL",            "lat": 33.8003, "lon": -117.8827, "cf_orientation_deg": 0.0},
    "MINUTE_MAID":      {"park_id": "MINUTE_MAID",      "lat": 29.7572, "lon": -95.3556,  "cf_orientation_deg": 0.0},
    "TROPICANA":        {"park_id": "TROPICANA",        "lat": 27.7682, "lon": -82.6534,  "cf_orientation_deg": 0.0},
    "LOAN_DEPOT":       {"park_id": "LOAN_DEPOT",       "lat": 25.7781, "lon": -80.2197,  "cf_orientation_deg": 0.0},
    "TRUIST":           {"park_id": "TRUIST",           "lat": 33.8908, "lon": -84.4678,  "cf_orientation_deg": 0.0},
    "ORIOLE_PARK":      {"park_id": "ORIOLE_PARK",      "lat": 39.2839, "lon": -76.6217,  "cf_orientation_deg": 70.0},
    "NATIONALS":        {"park_id": "NATIONALS",        "lat": 38.8730, "lon": -77.0074,  "cf_orientation_deg": 30.0},
    "CITI":             {"park_id": "CITI",             "lat": 40.7571, "lon": -73.8458,  "cf_orientation_deg": 60.0},
    "PNC":              {"park_id": "PNC",              "lat": 40.4469, "lon": -80.0058,  "cf_orientation_deg": 290.0},
    "COMERICA":         {"park_id": "COMERICA",         "lat": 42.3390, "lon": -83.0485,  "cf_orientation_deg": 30.0},
    "OAKLAND_COLISEUM": {"park_id": "OAKLAND_COLISEUM", "lat": 37.7516, "lon": -122.2005, "cf_orientation_deg": 0.0},
}

# Stats API team_id → ballpark_id (_DEFAULT_BALLPARK_METADATA anahtarı).
# 2026 sezonu (Athletics geçici Sacramento 2025-2027, OAKLAND_COLISEUM key korunur).
TEAM_ID_TO_PARK_ID: dict[int, str] = {
    # AL East
    110: "ORIOLE_PARK",     # Orioles
    111: "FENWAY",          # Red Sox
    147: "YANKEE",          # Yankees
    139: "TROPICANA",       # Rays
    141: "ROGERS",          # Blue Jays
    # AL Central
    145: "GUARANTEED_RATE", # White Sox
    114: "PROGRESSIVE",     # Guardians
    116: "COMERICA",        # Tigers
    118: "KAUFFMAN",        # Royals
    142: "TARGET",          # Twins
    # AL West
    117: "MINUTE_MAID",     # Astros
    108: "ANGEL",           # Angels
    133: "OAKLAND_COLISEUM",# Athletics (geçici Sacramento 2025-27)
    136: "T_MOBILE",        # Mariners
    140: "GLOBE_LIFE",      # Rangers
    # NL East
    144: "TRUIST",          # Braves
    146: "LOAN_DEPOT",      # Marlins
    121: "CITI",            # Mets
    143: "CITIZENS_BANK",   # Phillies
    120: "NATIONALS",       # Nationals
    # NL Central
    112: "WRIGLEY",         # Cubs
    113: "GREAT_AMERICAN",  # Reds
    158: "AMERICAN_FAMILY", # Brewers
    134: "PNC",             # Pirates
    138: "BUSCH",           # Cardinals
    # NL West
    109: "CHASE",           # D-backs
    115: "COORS",           # Rockies
    119: "DODGER",          # Dodgers
    135: "PETCO",           # Padres
    137: "ORACLE",          # Giants
}


def park_meta_for_team(team_id: int) -> dict | None:
    """Stats API team_id → ballpark metadata. Bilinmeyen → None."""
    park_id = TEAM_ID_TO_PARK_ID.get(team_id)
    if park_id is None:
        return None
    return _DEFAULT_BALLPARK_METADATA.get(park_id)


def build_agent(state: RuntimeState) -> Agent:
    """Tüm agent bağımlılıklarını inşa et."""
    cfg = state.config

    # Phase 3: tennis aktif iken Sackmann cache refresh hook (build_deps öncesi
    # blocking, ratings.json'ı agent'ın taze yüklemesi için). Stale değilse skip.
    _maybe_invoke_sackmann_refresh(cfg)

    # SPEC 2026-06-01 Faz 1: basketball aktif iken refresh hook (tennis paraleli).
    # Plan 1.A foundation — Plan 1.B'de team rating wiring tamamlanır.
    _maybe_invoke_basketball_refresh(cfg)

    # YAYINA ALMA (2026-06-01): basket ratings cache build hook.
    # Cache yoksa/eskimişse NBA/WNBA otomatik build; diğer ligler manuel script.
    _maybe_build_basketball_ratings(cfg)

    # Plan 1.D Task 6: haftalık calibration eğrisi update (FiveThirtyEight paterni).
    _maybe_invoke_calibration_refresh()

    gamma = GammaClient()
    odds = OddsAPIClient()
    espn = ESPNClient(athlete_cache_ttl_sec=cfg.scanner.tennis_athlete_cache_ttl_sec)
    score_enricher = ScoreEnricher(
        espn_client=espn,
        odds_client=odds,
        config=cfg.score,
    )
    tennis_enricher = TennisStartEnricher(
        espn_client=espn,
        cache_ttl_sec=cfg.scanner.tennis_start_cache_ttl_sec,
    )
    scanner = MarketScanner(
        cfg.scanner,
        gamma_client=gamma,
        tennis_start_enricher=tennis_enricher,
    )
    cycle_manager = CycleManager(cfg.cycle)
    cooldown = CooldownTracker(
        trigger_threshold=cfg.risk.consecutive_loss_cooldown,
        cooldown_cycles=cfg.risk.cooldown_cycles,
    )
    # WS price feed — agent entry/exit'te subscribe/unsubscribe yapacak,
    # callback agent.__init__'te bağlanır. Test senaryosunda None verilebilir;
    # production'da her zaman inşa edilir. SPEC-M: spike rejection threshold config'den.
    price_feed = PriceFeed(max_spike_pct=cfg.price_feed.max_spike_pct)

    # Executor: LIVE ise CLOB client gerekli — main.py LIVE confirm'dan sonra wire'lar
    executor = _build_executor(cfg)

    # 3-tier log paths: audit (kalıcı) + session (reboot mirror) + runtime (reboot temizler).
    # State (positions/breaker/blacklist) startup.py'de data/'da; operasyonel state burada data/'da.
    trade_logger = build_trade_logger()
    equity_logger = build_equity_logger()
    skipped_logger = SkippedTradeLogger("logs/runtime/skipped_trades.jsonl")
    stock_snapshot = StockSnapshot("data/stock_queue.json")
    stock = StockQueue(
        config=StockConfig(
            enabled=cfg.stock.enabled,
            jit_batch_multiplier=cfg.stock.jit_batch_multiplier,
            ttl_hours=cfg.stock.ttl_hours,
            pre_match_cutoff_min=cfg.stock.pre_match_cutoff_min,
            max_no_edge_attempts=cfg.stock.max_no_edge_attempts,
        ),
        snapshot=stock_snapshot,
    )
    stock.load()  # restart sonrası restore
    bot_status_store = JsonStore("data/bot_status.json")
    bot_status_writer = BotStatusWriter(bot_status_store, cycle_manager)

    # Tennis ratings cache — startup'ta yüklenir, runtime'da statik kullanılır.
    # Build script tarafından üretilir (scripts/build_tennis_ratings.py).
    # Yok ise dispatch boş dict ile çağrılır → moneyline bookmaker'a düşer.
    tennis_ratings = load_tennis_ratings(Path("data/tennis_ratings.json"))
    tennis_calibration = load_tennis_calibration(Path("data/tennis_calibration.json"))
    tennis_active = bool({"atp", "wta"} & {t.lower() for t in (cfg.scanner.allowed_sport_tags or [])})

    # Basketball ratings + efficiencies cache (Plan 1.A-D wiring tamamlanması).
    # Lig-başına ayrı JSON dosyası (basketball_cache/{league}_ratings.json).
    basket_ratings, basket_efficiencies = _load_basketball_caches(cfg)
    basket_calibration = load_tennis_calibration(
        Path("data/calibration_curves.json"),  # Plan 1.D generic location
    )
    if tennis_ratings:
        logger.info(
            "Tennis model anchor aktif: %d oyuncu reytingi, calibration curves=%d",
            len(tennis_ratings), len(tennis_calibration),
        )
    elif tennis_active:
        logger.warning(
            "Tennis allowed_sport_tags'te AMA tennis_ratings.json yok — "
            "alt market'ler tamamen skip, h2h bookmaker fallback. "
            "Çözüm: python -m scripts.build_tennis_ratings",
        )
    else:
        logger.info("Tennis ratings yok ve tennis pasif — sorun yok")

    def _bookmaker_enrich(market):
        return enrich_market(market, odds)

    def _tennis_dispatched(market):
        return enrich_with_tennis_dispatch(
            market, _bookmaker_enrich, tennis_ratings, tennis_calibration,
            glicko_weight=cfg.risk.tennis_h2h_glicko_weight,
        )

    # Gate: enricher + manipulation_check closure'ları.
    # Tri-dispatch: sport_tag basketball → basketball_dispatch (Plan 1.C wiring),
    # tennis/diğer → tennis_dispatch → bookmaker fallback (mevcut).
    _basket_sports = frozenset({"nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague"})

    def _enricher(market):
        sport = (market.sport_tag or "").lower()
        if sport in _basket_sports:
            return enrich_with_basketball_dispatch(
                market, _tennis_dispatched,
                ratings=basket_ratings,
                efficiencies=basket_efficiencies,
                basketball_cfg=cfg.basketball,
                calibration_curves=basket_calibration,
            )
        return _tennis_dispatched(market)

    def _manip(question: str, liquidity: float) -> ManipulationCheck:
        return manipulation_check(
            question=question, liquidity=liquidity,
            min_liquidity_usd=cfg.manipulation.min_liquidity_usd,
        )

    gate_cfg = GateConfig(
        min_edge=cfg.edge.min_edge,
        max_positions=cfg.risk.max_positions,
        max_positions_per_event=cfg.risk.max_positions_per_event,
        max_exposure_pct=cfg.risk.max_exposure_pct,
        fixed_bet_usdc=cfg.risk.fixed_bet_usdc,
        bimodal_bet_usdc=cfg.risk.bimodal_bet_usdc,
        max_entry_price=cfg.risk.max_entry_price,
        entry_price_slippage_buffer=cfg.risk.entry_price_slippage_buffer,
        model_min_anchor_distance_from_half=cfg.risk.model_min_anchor_distance_from_half,
        bimodal_min_entry_price=cfg.risk.bimodal_min_entry_price,
        kelly_enabled_tennis=cfg.risk.kelly_enabled_tennis,
        kelly_multiplier=cfg.risk.kelly_multiplier,
        kelly_max_pct=cfg.risk.kelly_max_pct,
        # Consensus
        consensus_enabled=cfg.consensus.enabled,
        consensus_min_price=cfg.consensus.min_price,
        # Early entry
        early_enabled=cfg.early.enabled,
        early_min_edge=cfg.early.min_edge,
        early_min_anchor_probability=cfg.early.min_anchor_probability,
        early_min_confidence=cfg.early.min_confidence,
        early_max_entry_price=cfg.early.max_entry_price,
        early_min_hours_to_start=cfg.early.min_hours_to_start,
        early_max_hours_to_start=cfg.early.max_hours_to_start,
    )
    gate = EntryGate(
        config=gate_cfg,
        portfolio=state.portfolio,
        circuit_breaker=state.circuit_breaker,
        cooldown=cooldown,
        blacklist=state.blacklist,
        odds_enricher=_enricher,
        manipulation_checker=_manip,
    )

    # Telegram command poller — /stop ile botu uzaktan durdurma
    command_poller: TelegramCommandPoller | None = None
    tg = cfg.telegram
    if tg.enabled and tg.bot_token and tg.chat_id:
        # on_stop callback agent oluşturulduktan sonra bağlanır (aşağıda)
        command_poller = TelegramCommandPoller(
            bot_token=tg.bot_token, chat_id=tg.chat_id, on_stop=lambda: None,
        )

    mlb_engine: MlbSubmarketEngineProtocol | None = None
    if cfg.mlb_submarket.enabled:
        from src.infrastructure.mlb_data.rate_cache import RateCache
        from src.infrastructure.mlb_data.statcast_client import StatcastClient
        from src.infrastructure.mlb_data.statsapi_client import StatsApiClient
        from src.infrastructure.mlb_data.weather_client import WeatherClient
        from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine

        statsapi = StatsApiClient(timeout=cfg.mlb_submarket.statsapi_timeout_sec)
        statcast = StatcastClient(cache_dir=Path("data/mlb_statcast_cache"))
        weather = WeatherClient()
        rate_cache = RateCache(Path(cfg.mlb_submarket.rate_cache_path))

        fixed_bet = getattr(cfg.risk, "fixed_bet_usdc", {"A": 50.0, "B": 30.0})
        bimodal_bet = getattr(cfg.risk, "bimodal_bet_usdc", {"A": 15.0, "B": 10.0})

        mlb_engine = MlbSubmarketEngine(
            statsapi=statsapi,
            statcast=statcast,
            weather=weather,
            rate_cache=rate_cache,
            config=cfg.mlb_submarket,
            ballpark_metadata=_DEFAULT_BALLPARK_METADATA,
            team_id_to_park_id=TEAM_ID_TO_PARK_ID,
            fixed_bet_usdc=fixed_bet,
            bimodal_bet_usdc=bimodal_bet,
        )
        logger.info("MlbSubmarketEngine initialized (config.mlb_submarket.enabled=True)")

    deps = AgentDeps(
        state=state, scanner=scanner, cycle_manager=cycle_manager,
        executor=executor, odds_client=odds, trade_logger=trade_logger,
        gate=gate, cooldown=cooldown,
        equity_logger=equity_logger, skipped_logger=skipped_logger,
        stock=stock, bot_status_writer=bot_status_writer,
        price_feed=price_feed,
        command_poller=command_poller,
        score_enricher=score_enricher,
        mlb_submarket_engine=mlb_engine,
        tennis_start_enricher=tennis_enricher,
        espn_client=espn,  # SPEC-force-close 2026-05-27
        gamma_client=gamma,  # 2026-05-28: ExitProcessor polymarket-resolution detector
    )
    agent = Agent(deps)

    # Callback'i agent oluştuktan sonra bağla
    if command_poller is not None:
        command_poller.set_on_stop(agent.request_stop)

    return agent


def maybe_refresh_sackmann_on_startup(cache_dir: Path) -> None:
    """Refresh Sackmann CSV + rebuild ratings if cache stale (tennis aktif iken).

    Synchronous; bot agent build_deps öncesi blocking çalışır. Stale değilse
    early return (1sn altı). İlk başlatma stale → ~1-2dk download + rebuild.
    Network fail → log WARNING, mevcut cache ile devam.
    """
    if not is_cache_stale(cache_dir):
        logger.info("Sackmann cache fresh — skipping startup refresh")
        return
    logger.info("Sackmann cache stale — refreshing before agent start")
    refreshed = refresh_if_stale(cache_dir)
    if not refreshed:
        logger.warning("Sackmann refresh attempted but no files downloaded")
        return
    logger.info("Rebuilding tennis_ratings.json from refreshed CSVs...")
    try:
        from scripts.build_tennis_ratings import main as rebuild_main  # noqa: PLC0415
        rebuild_main()
        logger.info("Startup Sackmann refresh + rebuild complete")
    except ImportError:
        logger.warning("scripts/build_tennis_ratings.py yok — sadece CSV refresh yapıldı")


def _maybe_invoke_sackmann_refresh(cfg: AppConfig) -> None:
    """Tennis aktif iken Sackmann refresh hook çağır (allowed_sport_tags'e bak)."""
    tags_lc = {t.lower() for t in (cfg.scanner.allowed_sport_tags or [])}
    if not ({"atp", "wta"} & tags_lc):
        return
    maybe_refresh_sackmann_on_startup(Path("data/sackmann_cache"))


def _maybe_invoke_calibration_refresh() -> None:
    """Plan 1.D Task 6: haftalık calibration eğrisi update hook.

    Stale değilse skip. Bot başlangıçta blocking değil — fit hızlı,
    save atomic, yarım dosya riski yok.
    """
    from src.orchestration.calibration_refresher import refresh_calibration_if_stale
    refresh_calibration_if_stale(
        calibration_path=Path("data/calibration_curves.json"),
        trades_path=Path("logs/audit/trade_history.jsonl"),
    )


_TENNIS_SPORT_TAGS = frozenset({"tennis", "atp", "wta"})
_BASKETBALL_SPORT_TAGS = frozenset({
    "nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl",
})


def _select_enricher_for_sport(sport_tag: str) -> str:
    """Sport_tag → enricher tipi seçimi.

    'tennis_model'    → Sackmann-anchored (Adım 3-5, tenis paper lab).
    'basketball_model' → Elo + Pace×Efficiency (Plan 1.C).
    'bookmaker'       → Odds API h2h fallback (diğer sporlar).
    """
    s = sport_tag.lower()
    if s in _TENNIS_SPORT_TAGS:
        return "tennis_model"
    if s in _BASKETBALL_SPORT_TAGS:
        return "basketball_model"
    return "bookmaker"


_PRO_BASKET_LEAGUES = frozenset({"nba", "wnba"})
_COLLEGE_BASKET_LEAGUES = frozenset({"ncaab", "wncaab"})
_EUROPE_BASKET_LEAGUES = frozenset({"euroleague"})


def _load_basketball_caches(cfg: AppConfig) -> tuple[dict, dict]:
    """Lig-başına team_ratings_store JSON'larından ratings + efficiencies oku.

    Returns: ({league: {team: EloRating}}, {league: {team: TeamEfficiency}}).
    Eksik dosya → boş dict (degrade — basketball_dispatch bookmaker fallback).
    """
    from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
    from src.domain.pricing.basketball.team_elo import EloRating

    cache_dir = Path(cfg.basketball.cache_dir)
    ratings: dict[str, dict[str, EloRating]] = {}
    efficiencies: dict[str, dict[str, TeamEfficiency]] = {}
    for league in cfg.basketball.enabled_leagues:
        path = cache_dir / f"{league}_ratings.json"
        snapshots = load_team_snapshots(path, league=league)
        if not snapshots:
            continue
        ratings[league] = {
            team: EloRating(rating=snap.elo_rating, games=snap.elo_games)
            for team, snap in snapshots.items()
        }
        efficiencies[league] = {
            team: TeamEfficiency(
                adj_o=snap.adj_o, adj_d=snap.adj_d, adj_pace=snap.adj_pace,
            )
            for team, snap in snapshots.items()
        }
        logger.info(
            "Basketball ratings yüklendi: %s — %d takım",
            league, len(snapshots),
        )
    return ratings, efficiencies


def _make_basketball_fetchers(
    league: str,
    date_utc: str,
    http_get,
    espn_fetcher,
):
    """Lig-bazlı (primary_fetch, secondary_fetch) callable çifti üret.

    NBA / WNBA: primary nba_api stub (Plan 1.B wiring noktası), secondary ESPN.
    NCAAB / WNCAAB: primary ESPN, secondary boş (yedek kaynak yok).
    Euroleague: primary euroleague-api stub (Faz 3 wiring), secondary boş.
    """
    def _empty_list() -> list:
        return []

    def _espn(_league: str = league, _date: str = date_utc) -> list:
        return espn_fetcher(league=_league, date_utc=_date, http_get=http_get)

    if league in _PRO_BASKET_LEAGUES:
        # nba_api primary (Plan 1.B wiring), ESPN secondary
        return _empty_list, _espn
    if league in _COLLEGE_BASKET_LEAGUES:
        # ESPN primary, yedek yok (degrade boş liste döner)
        return _espn, _empty_list
    if league in _EUROPE_BASKET_LEAGUES:
        # Faz 3: euroleague-api primary. Endpoint factory bot başlangıçta
        # opsiyonel (paket eksikse degrade boş list). Gerçek wiring sezon
        # delta-fetch script'iyle eşleşir (gelecekte trade history beslenir).
        return _empty_list, _empty_list
    # Bilinmeyen lig — sessizce empty (mantıken buraya gelmez, enabled_leagues filtreliyor)
    return _empty_list, _empty_list


def _maybe_build_basketball_ratings(cfg: AppConfig) -> None:
    """Bot başlangıçta basket ratings cache build (Sackmann paralel).

    Her enabled lig için:
      - Cache yoksa veya 24sa+ eskiyse: scripts/build_basketball_ratings.py paterni
      - NBA/WNBA: nba_api bulk fetch (hızlı, 1 API call)
      - NCAAB/WNCAAB/Euroleague: scripts/build_basketball_ratings.py manuel önerisi
        (boot'ta blocking çağrı çok yavaş olur — 90 gün ESPN scrape)
    """
    tags_lc = {t.lower() for t in (cfg.scanner.allowed_sport_tags or [])}
    enabled = [lg for lg in cfg.basketball.enabled_leagues if lg in tags_lc]
    if not enabled:
        return
    import time  # noqa: PLC0415
    from datetime import datetime, timezone  # noqa: PLC0415

    cache_dir = Path(cfg.basketball.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fast_build_leagues = {"nba", "wnba"}

    for league in enabled:
        cache_path = cache_dir / f"{league}_ratings.json"
        if cache_path.exists():
            age_h = (time.time() - cache_path.stat().st_mtime) / 3600.0
            if age_h < 24.0:
                logger.info(
                    "Basketball ratings fresh: %s (age=%.1fh, skip)",
                    league, age_h,
                )
                continue
        if league not in fast_build_leagues:
            logger.warning(
                "Basketball ratings cache yok/eski: %s. "
                "Manuel build: python scripts/build_basketball_ratings.py --league %s",
                league, league,
            )
            continue
        # NBA / WNBA — nba_api bulk (hızlı)
        params = cfg.basketball.leagues.get(league)
        if params is None:
            continue
        try:
            from nba_api.stats.endpoints import leaguegamelog  # noqa: PLC0415

            from src.infrastructure.data.basketball.nba_api_refresher import (  # noqa: PLC0415
                fetch_game_log_via_nba_api,
            )
            from src.orchestration.basketball_ratings_builder import (  # noqa: PLC0415
                build_and_persist_snapshots,
            )
            current = datetime.now(timezone.utc).year
            season = str(current - 1)
            logger.info("Basketball ratings build: %s season=%s", league, season)
            games = fetch_game_log_via_nba_api(
                league=league, season=season,
                endpoint_factory=lambda **kw: leaguegamelog.LeagueGameLog(
                    season=kw["season"], league_id=kw["league_id"],
                    season_type_all_star="Regular Season",
                ),
            )
            n = build_and_persist_snapshots(
                games=games, league=league,
                k_factor=params.k_factor, home_advantage=params.home_advantage,
                output_path=cache_path,
            )
            logger.info(
                "Basketball ratings built: %s — %d takım, %d maç",
                league, n, len(games),
            )
        except Exception as exc:  # noqa: BLE001 — infra boundary
            logger.warning(
                "Basketball ratings build skipped %s: %s", league, exc,
            )


def _maybe_invoke_basketball_refresh(cfg: AppConfig) -> None:
    """Basketball aktif iken refresh hook çağır.

    Lig-bazlı kaynak dispatch:
      NBA / WNBA       → nba_api primary, ESPN secondary
      NCAAB / WNCAAB   → ESPN primary (nba_api college yok), secondary yok
      Euroleague       → euroleague_api primary (Faz 3 wiring), secondary yok

    Plan 1.B wiring noktası: nba_api endpoint factory ile primary fetch
    gerçek delta-fetch yapacak (şu an stub).
    """
    tags_lc = {t.lower() for t in (cfg.scanner.allowed_sport_tags or [])}
    enabled = [lg for lg in cfg.basketball.enabled_leagues if lg in tags_lc]
    if not enabled:
        logger.info("basketball refresh skipped — no enabled league in whitelist")
        return
    from datetime import datetime, timezone

    import requests

    from src.infrastructure.data.basketball.espn_pbp_refresher import (
        fetch_game_log_via_espn,
    )
    from src.infrastructure.data.basketball.refresh_runner import (
        BasketballRefreshRunner,
    )

    health_path = Path(cfg.basketball.health_file)
    today = datetime.now(timezone.utc).date().isoformat()

    for league in enabled:
        primary_fetch, secondary_fetch = _make_basketball_fetchers(
            league=league, date_utc=today, http_get=requests.get,
            espn_fetcher=fetch_game_log_via_espn,
        )

        runner = BasketballRefreshRunner(
            league=league, health_path=health_path,
            primary_fetch=primary_fetch, secondary_fetch=secondary_fetch,
            now_utc_str=lambda: datetime.now(timezone.utc).isoformat(),
        )
        outcome = runner.run()
        logger.info(
            "basketball refresh: league=%s source=%s games=%d",
            league, outcome.source_used, len(outcome.games),
        )


def _build_executor(cfg: AppConfig) -> Executor:
    """Mode dispatch: dry_run → stub; paper → realistic fill; live → CLOB."""
    if cfg.mode == Mode.DRY_RUN:
        return Executor(mode=cfg.mode)
    if cfg.mode == Mode.PAPER:
        return Executor(
            mode=cfg.mode,
            paper_config=cfg.paper,
            paper_audit_path="logs/audit/paper_executions.jsonl",
        )
    # LIVE: py-clob-client runtime wiring
    import os
    from src.infrastructure.apis.clob_client import ClobOrderClient, build_client
    private_key = os.getenv("PRIVATE_KEY", "")
    if not private_key:
        raise RuntimeError("LIVE mode requires PRIVATE_KEY env var")
    raw = build_client(host="https://clob.polymarket.com", chain_id=137, private_key=private_key)
    clob = ClobOrderClient(raw)
    return Executor(mode=cfg.mode, clob_client=clob)
