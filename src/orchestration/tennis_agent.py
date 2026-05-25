"""Tennis agent loop — periodic heavy (scan/enrich/entry) + light (exit) cycles.

Paper mode: entries via EntryProcessor.process_signals, exits via
ExitProcessor.run_light. All positions written to data/positions.json after
heavy or light cycles. Qualifying candidates (edge ≥ min_edge, tier A or B)
are also logged via TennisDiagnosticLogger for post-hoc paper-trade analysis.

Heavy cycle (default 30 min): scan Polymarket → enrich → size → entry.
Light cycle (default 60 sec): tick open positions → exit evaluation (SL/TP/
graduated/near-resolve). Tennis run_light artık ESPN ScoreEnricher üzerinden
score_map besler (2026-05-20 wire) — set/games verisi map_diff/never_in_profit
guard'larında kullanılır; ESPN down ise score_map={} fallback (compute_elapsed_pct
match_start_iso primary path'i devreye girer).

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §11.4
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.domain.risk.position_sizer import confidence_position_size
from src.infrastructure.data.sackmann_csv_client import SackmannMatch
from src.infrastructure.data.tennis_ratings_store import PlayerRating
from src.models.enums import SportsMarketType
from src.models.market import MarketData
from src.models.signal import Signal
from src.orchestration import operational_writers
from src.orchestration.match_start_refresh import maybe_refresh_match_start
from src.orchestration.scanner import MarketScanner
from src.orchestration.startup import persist
from src.orchestration.tennis_diagnostic_writer import log_candidate
from src.orchestration.tennis_factory import TennisDeps
from src.orchestration.tennis_price_callback import install_price_feed
from src.orchestration.tennis_pnl_integrity import run_light_telemetry
from src.orchestration.tennis_status_writer import write_pid, write_status
from src.strategy.enrichment.tennis_market_enricher import enrich
from src.strategy.enrichment.tennis_question_parser import parse_tennis_question
from src.strategy.entry.tennis_entry import EdgeCandidate, select_best_2_per_event
from src.strategy.entry.tennis_signal_adapter import tennis_candidate_to_signal

logger = logging.getLogger(__name__)
# Light cycle log throttle: her 10. tick'te INFO (10dk aralık, 144/gün, 1440 değil).
_LIGHT_TICK_LOG_EVERY = 10
_light_tick_state = {"count": 0}


def _is_bimodal_slug(slug: str) -> bool:
    """Tennis bimodal market detection from slug (set_handicap + set_totals)."""
    s = (slug or "").lower()
    return "set-handicap" in s or "set-total" in s


def _load_sackmann_matches(deps: TennisDeps) -> list[SackmannMatch]:
    """Load historical matches for feature extraction.

    Loads ATP main + ATP challenger + WTA per config (same composition as
    scripts/build_tennis_ratings.py). Without WTA matches the enricher's
    feature extractor returns p1/p2 match_count=0 for all WTA markets,
    causing classify_tier to fall to "skip" and the agent to never produce
    WTA candidates.
    """
    cfg = deps.config.tennis
    atp_main = deps.sackmann_client.load_years(cfg.sackmann_years)
    atp_chall = deps.sackmann_client.load_challenger_years(cfg.challenger_years)
    wta = deps.sackmann_client.load_wta_years(cfg.sackmann_wta_years)
    return atp_main + atp_chall + wta


def run_one_cycle(
    deps: TennisDeps,
    *,
    sackmann_matches: Optional[list[SackmannMatch]] = None,
    ratings: Optional[dict[str, PlayerRating]] = None,
) -> int:
    """Single scan + enrich + log cycle. Returns count of candidates logged.

    Heavy cycle adım sırası (test_tennis_full_cycle.py ile sabitlendi):
      1. ratings + sackmann_matches yükle
      2. MarketScanner.scan() → tennis market'ları
      3. enrich(market) → EdgeCandidate listesi
      4. select_best_2_per_event → event başına en iyi 2
      5. min_edge filtresi (|edge| ≥ cfg.edge.min_edge)
      6. Her qualified için diagnostic log + (tier A/B ise) sized Signal üret
      7. entry_processor.process_signals(markets, signals) [skip if 0 signal]
      8. persist(state) [skip if 0 signal]
      9. operational_writers.log_equity_snapshot(...)  [heartbeat — her zaman]

    Args:
        deps: All wired tennis dependencies.
        sackmann_matches: Optional pre-loaded match history (avoids reload per cycle).
        ratings: Optional pre-loaded player ratings (avoids reload per cycle).

    Returns:
        Number of qualifying candidates logged this cycle.
    """
    cfg = deps.config

    # Load ratings + matches (or reuse provided)
    if ratings is None:
        ratings = deps.ratings_store.load()
        if not ratings:
            logger.warning("Tennis agent: no player ratings — run build_tennis_ratings.py first")
            return 0
    if not ratings:
        logger.warning("Tennis agent: empty ratings dict — no predictions possible")
        return 0

    if sackmann_matches is None:
        sackmann_matches = _load_sackmann_matches(deps)

    # Scan Polymarket
    scanner = MarketScanner(config=cfg.scanner)
    markets: list[MarketData] = scanner.scan()

    # Enrich each market → (candidate, market) pairs.
    # Name-match indexes are rebuilt per call inside enrich() (tour-scoped —
    # ATP and WTA have separate dicts, so cross-market caching is unsafe).
    candidates: list[tuple[EdgeCandidate, MarketData]] = []
    for market in markets:
        candidate = enrich(
            market=market,
            ratings=ratings,
            sackmann_matches=sackmann_matches,
            cfg=cfg,
        )
        if candidate is not None:
            candidates.append((candidate, market))

    # Select best 2 per event
    edge_only = [c for c, _ in candidates]
    selected_edges = select_best_2_per_event(edge_only)
    selected_set = {id(c) for c in selected_edges}

    # Apply min_edge threshold
    qualified_pairs = [
        (c, m) for c, m in candidates
        if id(c) in selected_set and abs(c.edge) >= cfg.edge.min_edge
    ]

    # Risk-based priority: SL-protected (non-bimodal) markets fill slots first.
    # Bimodal markets (set_handicap + set_totals) carry full-loss tail risk
    # because price gaps prevent SL fire — they should consume residual capacity
    # only, not crowd out SL-protected entries when max_positions cap is tight.
    # Stable sort preserves scanner's nearest-match ordering within each group.
    qualified_pairs.sort(key=lambda pair: 1 if _is_bimodal_slug(pair[1].slug or "") else 0)

    # Log each qualifying candidate + build sized signals for entry
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC for Sackmann comparisons
    logged = 0
    signals_for_entry: list[Signal] = []
    markets_for_entry: list[MarketData] = []

    for candidate, market in qualified_pairs:
        parsed = parse_tennis_question(
            question=market.question,
            sports_market_type=market.sports_market_type,
            slug=market.slug or "",
        )
        if parsed is None:
            continue

        did_log, tier = log_candidate(
            candidate=candidate,
            market=market,
            parsed=parsed,
            ratings=ratings,
            sackmann_matches=sackmann_matches,
            cfg=cfg,
            diagnostic_logger=deps.diagnostic_logger,
            now=now,
        )
        if did_log:
            logged += 1
        # Tennis sizing (PLAN-SIZING-001, 2026-05-22):
        # Bimodal piyasalar (set_totals + set_handicap) SL fire etmiyor → her tier $15 cap.
        # Non-bimodal piyasalar (ML / match_o_u / first_set_winner) normal tier sizing.
        # /3 küçültme kaldırıldı; tier'ın kendi bet_pct'i (A=%5, B=%3.5) kullanılır.
        if tier in ("A", "B"):
            if market.sports_market_type == SportsMarketType.TENNIS_SET_TOTALS.value:
                max_cap = cfg.risk.set_totals_max_usdc
            elif market.sports_market_type == SportsMarketType.TENNIS_SET_HANDICAP.value:
                max_cap = cfg.risk.set_handicap_max_usdc
            else:
                max_cap = cfg.risk.max_single_bet_usdc
            size_usdc = confidence_position_size(
                confidence=tier,
                bankroll=deps.state.portfolio.bankroll,
                confidence_bet_pct=cfg.risk.confidence_bet_pct,
                max_bet_usdc=max_cap,
                max_bet_pct=cfg.risk.max_bet_pct,
            )
            if size_usdc > 0:
                signal = tennis_candidate_to_signal(candidate, market, tier)
                signal = signal.model_copy(update={"size_usdc": size_usdc})
                signals_for_entry.append(signal)
                markets_for_entry.append(market)

    # Execute paper entries via EntryProcessor (sport-agnostic portfolio guards),
    # then persist portfolio snapshot so positions.json reflects the new state.
    if signals_for_entry:
        deps.entry_processor.process_signals(markets_for_entry, signals_for_entry)
        persist(deps.state)

    # Heavy cycle equity snapshot — heartbeat for dashboard Total Equity chart.
    # Main bot pattern: EntryProcessor.run_heavy fires log_equity_snapshot at
    # cycle end regardless of entry count (entry_processor.py:55, 77). Tennis
    # uses process_signals which doesn't auto-snapshot, so caller writes here.
    operational_writers.log_equity_snapshot(deps.state.portfolio, deps.equity_logger)

    logger.info(
        "Tennis cycle done: %d markets scanned, %d enriched, %d selected, "
        "%d qualified (edge≥%.0f%%), %d signals submitted",
        len(markets),
        len(candidates),
        len(selected_edges),
        logged,
        cfg.edge.min_edge * 100,
        len(signals_for_entry),
    )
    return logged


def _fetch_tennis_score_map(deps: TennisDeps) -> dict[str, dict]:
    """ESPN ScoreEnricher'dan açık pozisyonlar için score_map çek.

    score_enricher = None (legacy/test) veya ESPN exception → {} dön (boş map
    ExitProcessor.run_light'a verildiğinde monitor.evaluate score_info={} alır,
    compute_elapsed_pct match_start_iso primary path'i kullanır).
    """
    enricher = getattr(deps, "score_enricher", None)
    if enricher is None:
        return {}
    try:
        return enricher.get_scores_if_due(deps.state.portfolio.positions)
    except Exception as exc:  # noqa: BLE001 — orchestration catches infra errors
        logger.warning("Tennis ESPN score enrichment failed: %s — empty score_map", exc)
        return {}


def run_light_cycle(
    deps: TennisDeps,
    *,
    data_dir: Path = Path("data"),
    next_heavy_at: Optional[datetime] = None,
) -> None:
    """Light cycle — açık pozisyonları exit guard'larından geçir + persist.

    Tennis için score_map ESPN ATP/WTA scoreboard üzerinden ScoreEnricher
    tarafından doldurulur (2026-05-20 wire); set/games verisi map_diff +
    never_in_profit + hold_revocation guard'larına input olur. ESPN down ise
    score_map={} fallback (compute_elapsed_pct match_start_iso primary path).

    Light cycle adım sırası (test_tennis_full_cycle.py ile sabitlendi):
      1. exit_processor.run_light(score_map=<ESPN map veya {}>)
      2. persist(state)  [heartbeat — tick alanlarını yaz]
      3. operational_writers.log_equity_snapshot(...)  [chart 60sn tick'i]
      4. bot_status.json yaz (stage="light")

    Args:
        deps: Wired tennis dependencies.
        data_dir: bot_status.json yazım dizini.
        next_heavy_at: Dashboard göstergesi için bir sonraki heavy cycle zamanı.
            run_forever bunu monotonic clock'tan hesaplayıp geçer; doğrudan
            çağrılan testler/script'ler için None → şu an (gösterge placeholder).
    """
    # 2026-05-20: WS güvensiz (10¢'e kadar drift + boş book'ta RESOLVED kaçar)
    # → exit_processor ÖNCESİ REST top-up + realized PnL drift visibility check.
    run_light_telemetry(deps.state.portfolio, deps.trade_logger)
    _light_tick_state["count"] += 1
    # 2026-05-26 stale-cache fix: Polymarket can reschedule a match after position
    # opens — re-fetch gameStartTime every N ticks BEFORE exit_processor so SL +
    # graduated_sl + LIVE badge use fresh elapsed_pct.
    maybe_refresh_match_start(
        _light_tick_state["count"], deps.config.tennis.match_start_refresh_every_n_ticks,
        deps.state.portfolio, deps.gamma_client,
    )
    score_map = _fetch_tennis_score_map(deps)
    deps.exit_processor.run_light(score_map=score_map)
    if _light_tick_state["count"] % _LIGHT_TICK_LOG_EVERY == 0:
        logger.info("Light cycle tick #%d: %d open positions checked",
                    _light_tick_state["count"], len(deps.state.portfolio.positions))
    # Heavy cycle ile aynı persist davranışı — pos state (current_price, peak,
    # consecutive_down_cycles) tick'lendiği için her light sonunda diske yaz.
    persist(deps.state)
    # ExitProcessor.run_light yalnızca EXIT olunca snapshot atıyor; tennis için
    # unrealized_pnl tick'i her light sonunda görünür olmalı.
    operational_writers.log_equity_snapshot(deps.state.portfolio, deps.equity_logger)
    write_status(
        data_dir / "bot_status.json",
        stage="light",
        next_heavy_at=next_heavy_at or datetime.now(timezone.utc),
        mode=deps.config.mode.value,
    )


def run_forever(
    deps: TennisDeps,
    interval_sec: int = 1800,
    *,
    logs_dir: Path = Path("logs"),
    data_dir: Path = Path("data"),
    light_interval_sec: int = 60,
) -> None:
    """Run agent loop indefinitely with independent heavy/light cycles.

    Heavy cycle (default every 1800s = 30min): scan/enrich/entry via
    run_one_cycle. Light cycle (default every 60s): exit guards via
    run_light_cycle. Loop ticks once per second; each cycle fires when its
    interval has elapsed.

    Ratings and Sackmann matches are reloaded inside run_one_cycle each heavy
    cycle to pick up freshly-built ratings without restart.

    Dashboard heartbeat: agent.pid (logs_dir) + bot_status.json (data_dir).

    Args:
        deps: Wired tennis dependencies.
        interval_sec: Heavy cycle interval (default 1800 = 30min).
        logs_dir: Path for agent.pid file.
        data_dir: Path for bot_status.json file.
        light_interval_sec: Light cycle interval (default 60s).
    """
    logger.info(
        "Tennis agent starting: heavy=%ds light=%ds mode=%s",
        interval_sec, light_interval_sec, deps.config.mode.value,
    )
    pid_file = logs_dir / "agent.pid"
    status_file = data_dir / "bot_status.json"
    mode = deps.config.mode.value
    write_pid(pid_file)
    install_price_feed(deps.price_feed, deps.state.portfolio)

    # Heavy + light tetik zamanları monotonic clock üzerinden bağımsız izlenir.
    # İlk iterasyonda her ikisi de tetiklenecek şekilde "uzun zaman önce" başlatılır.
    last_heavy_at = time.monotonic() - interval_sec
    last_light_at = time.monotonic() - light_interval_sec

    while True:
        now_mono = time.monotonic()

        if now_mono - last_heavy_at >= interval_sec:
            next_heavy_at = datetime.now(timezone.utc) + timedelta(seconds=interval_sec)
            write_status(status_file, stage="scanning", next_heavy_at=next_heavy_at, mode=mode)
            try:
                n = run_one_cycle(deps)
                logger.info("Heavy cycle logged %d candidates", n)
            except Exception as exc:  # noqa: BLE001 — orchestration catches + logs all
                logger.error("Tennis heavy cycle error: %s", exc, exc_info=True)
            write_status(status_file, stage="idle", next_heavy_at=next_heavy_at, mode=mode)
            last_heavy_at = time.monotonic()

        if time.monotonic() - last_light_at >= light_interval_sec:
            # next_heavy_at = bir sonraki heavy tetikleme noktası (monotonic clock)
            seconds_until_heavy = max(0.0, interval_sec - (time.monotonic() - last_heavy_at))
            light_next_heavy_at = datetime.now(timezone.utc) + timedelta(seconds=seconds_until_heavy)
            try:
                run_light_cycle(deps, data_dir=data_dir, next_heavy_at=light_next_heavy_at)
            except Exception as exc:  # noqa: BLE001 — orchestration catches + logs all
                logger.error("Tennis light cycle error: %s", exc, exc_info=True)
            last_light_at = time.monotonic()

        time.sleep(1)
