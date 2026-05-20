"""Tennis agent loop — periodic scan + enrich + log pipeline.

Paper-mode MVP: NO real execution, NO positions.json state.
Demonstrates the full pipeline end-to-end with real Polymarket data.
Qualifying candidates (edge ≥ min_edge, tier A or B) are logged via
TennisDiagnosticLogger for post-hoc paper-trade analysis.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §11.4
"""
from __future__ import annotations

import atexit
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.config.settings import AppConfig
from src.domain.matching.tennis_player_matcher import build_match_index, match_player
from src.domain.prediction.feature_extractor import extract_features
from src.domain.prediction.tennis_predictor import MarketPrediction
from src.domain.risk.position_sizer import confidence_position_size
from src.infrastructure.data.sackmann_csv_client import SackmannMatch
from src.infrastructure.data.tennis_ratings_store import PlayerRating
from src.models.market import MarketData
from src.models.signal import Signal
from src.orchestration.scanner import MarketScanner
from src.orchestration.startup import persist
from src.orchestration.tennis_diagnostic_logger import TennisDiagnosticLogger
from src.orchestration.tennis_factory import TennisDeps
from src.strategy.enrichment.tennis_market_enricher import classify_tier, enrich
from src.strategy.enrichment.tennis_question_parser import parse_tennis_question
from src.strategy.entry.tennis_entry import EdgeCandidate, select_best_2_per_event
from src.strategy.entry.tennis_signal_adapter import tennis_candidate_to_signal

logger = logging.getLogger(__name__)


def _load_sackmann_matches(deps: TennisDeps) -> list[SackmannMatch]:
    """Load historical matches for feature extraction."""
    years = deps.config.tennis.sackmann_years
    return deps.sackmann_client.load_years(years)


def _log_candidate(
    candidate: EdgeCandidate,
    market: MarketData,
    parsed: dict,
    ratings: dict[str, PlayerRating],
    sackmann_matches: list[SackmannMatch],
    cfg: AppConfig,
    diagnostic_logger: TennisDiagnosticLogger,
    now: datetime,
    by_full: dict,
    by_last: dict,
) -> tuple[bool, str]:
    """Resolve features + tier for one candidate and write diagnostic log record.

    Returns (did_log, tier) — tier is "A" / "B" / "skip" / "" (player not found).
    Caller uses tier to decide whether to size + submit an entry signal.
    """
    p1_rating = match_player(parsed["p1_name"], ratings, by_full=by_full, by_last=by_last)
    p2_rating = match_player(parsed["p2_name"], ratings, by_full=by_full, by_last=by_last)
    if p1_rating is None or p2_rating is None:
        return False, ""

    features = extract_features(
        matches=sackmann_matches,
        p1=p1_rating.player_name,
        p2=p2_rating.player_name,
        surface=parsed["surface"].capitalize(),
        snapshot_date=now,
    )
    tier = classify_tier(features, cfg)
    if tier == "skip":
        return False, tier

    direction = "BUY_YES" if candidate.edge >= 0 else "BUY_NO"
    prediction = MarketPrediction(
        market_type=candidate.market_type,
        probability=candidate.model_p,
        raw_probability=candidate.model_p,
        notes=f"edge={candidate.edge:+.3f} tier={tier}",
    )
    tournament = market.question.split(":")[0].strip() if ":" in market.question else "Unknown"

    diagnostic_logger.log_prediction(
        trade_id=str(uuid.uuid4()),
        tournament=tournament,
        tournament_tier="unknown",
        slug=market.slug or "",
        format_="BO3",
        match_start_iso=market.match_start_iso or now.isoformat() + "Z",
        market_polymarket_price=market.yes_price,
        direction=direction,
        prediction=prediction,
        features=features,
        confidence_tier=tier,
        edge=candidate.edge,
    )
    return True, tier


def run_one_cycle(
    deps: TennisDeps,
    *,
    sackmann_matches: Optional[list[SackmannMatch]] = None,
    ratings: Optional[dict[str, PlayerRating]] = None,
) -> int:
    """Single scan + enrich + log cycle. Returns count of candidates logged.

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

    # Build name-match indexes once per cycle (not per market)
    by_full, by_last = build_match_index(ratings)

    # Scan Polymarket
    scanner = MarketScanner(config=cfg.scanner)
    markets: list[MarketData] = scanner.scan()

    # Enrich each market → (candidate, market) pairs
    candidates: list[tuple[EdgeCandidate, MarketData]] = []
    for market in markets:
        candidate = enrich(
            market=market,
            ratings=ratings,
            sackmann_matches=sackmann_matches,
            cfg=cfg,
            by_full=by_full,
            by_last=by_last,
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

        did_log, tier = _log_candidate(
            candidate=candidate,
            market=market,
            parsed=parsed,
            ratings=ratings,
            sackmann_matches=sackmann_matches,
            cfg=cfg,
            diagnostic_logger=deps.diagnostic_logger,
            now=now,
            by_full=by_full,
            by_last=by_last,
        )
        if did_log:
            logged += 1
        if tier in ("A", "B"):
            size_usdc = confidence_position_size(
                confidence=tier,
                bankroll=deps.state.portfolio.bankroll,
                confidence_bet_pct=cfg.risk.confidence_bet_pct,
                max_bet_usdc=cfg.risk.max_single_bet_usdc,
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


def _write_pid(pid_file: Path) -> None:
    """Tennis agent process PID dosyası — dashboard bot_is_alive kontrolü için."""
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(lambda: pid_file.unlink(missing_ok=True))


def _write_status(
    status_file: Path,
    *,
    stage: str,
    next_heavy_at: datetime,
    mode: str,
) -> None:
    """Dashboard cycle göstergesi için snapshot yaz."""
    try:
        status_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": mode,
            "cycle": "heavy",
            "stage": stage,
            "stage_at": datetime.now(timezone.utc).isoformat(),
            "next_heavy_at": next_heavy_at.isoformat(),
            "light_alive": True,
        }
        status_file.write_text(json.dumps(payload), encoding="utf-8")
    except OSError as exc:
        logger.warning("bot_status write failed: %s", exc)


def run_forever(
    deps: TennisDeps,
    interval_sec: int = 1800,
    *,
    logs_dir: Path = Path("logs"),
    data_dir: Path = Path("data"),
) -> None:
    """Run agent loop indefinitely with fixed interval between cycles.

    Ratings and Sackmann matches are reloaded each cycle to pick up
    freshly-built ratings without restart.

    Dashboard heartbeat: agent.pid (logs_dir) + bot_status.json (data_dir).

    Args:
        deps: Wired tennis dependencies.
        interval_sec: Seconds to sleep between cycle starts (default 1800 = 30min).
        logs_dir: Path for agent.pid file.
        data_dir: Path for bot_status.json file.
    """
    logger.info(
        "Tennis agent starting: interval=%ds mode=%s",
        interval_sec,
        deps.config.mode.value,
    )
    pid_file = logs_dir / "agent.pid"
    status_file = data_dir / "bot_status.json"
    mode = deps.config.mode.value
    _write_pid(pid_file)

    while True:
        cycle_start = time.monotonic()
        next_heavy_at = datetime.now(timezone.utc) + timedelta(seconds=interval_sec)
        _write_status(status_file, stage="scanning", next_heavy_at=next_heavy_at, mode=mode)
        try:
            n = run_one_cycle(deps)
            logger.info("Cycle logged %d candidates", n)
        except Exception as exc:  # noqa: BLE001 — orchestration catches + logs all
            logger.error("Tennis cycle error: %s", exc, exc_info=True)
        _write_status(status_file, stage="idle", next_heavy_at=next_heavy_at, mode=mode)

        elapsed = time.monotonic() - cycle_start
        sleep_sec = max(0, interval_sec - elapsed)
        if sleep_sec > 0:
            logger.info("Next cycle in %.0fs", sleep_sec)
            time.sleep(sleep_sec)
