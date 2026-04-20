"""Tek seferlik dry-run — scanner + gate çalıştır, skip_detail üret.

Canlı bot paralel çalışırken bu script bağımsız process olarak scanner+gate'i
simüle eder, SONUÇLARI AYRI BİR DOSYAYA yazar (prod log'u kirletmez).

Amaç: SPEC-001 sonrası skip_detail formatını gerçek veri üzerinde görmek.

Çalıştır: python -m scripts.manual_skip_dryrun
Sonra: logs/manual_skip_dryrun.jsonl dosyasını analiz et.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Proje kökünü import path'e ekle
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

from src.config.settings import load_config
from src.domain.guards.blacklist import Blacklist
from src.domain.guards.manipulation import check_market as manipulation_check
from src.domain.portfolio.manager import PortfolioManager
from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.apis.gamma_client import GammaClient
from src.infrastructure.apis.odds_client import OddsAPIClient
from src.infrastructure.persistence.skipped_trade_logger import (
    SkippedTradeLogger,
    SkippedTradeRecord,
)
from src.models.position import Position
from src.orchestration.scanner import MarketScanner
from src.strategy.enrichment.odds_enricher import enrich_market
from src.strategy.entry.gate import EntryGate, GateConfig


class _NoHaltBreaker:
    def should_halt_entries(self) -> tuple[bool, str]:
        return (False, "")


def _load_portfolio_event_ids(path: str = "logs/positions.json") -> PortfolioManager:
    """Mevcut positions.json'u yükle — event_id'ler event_already_held testinde."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    if not Path(path).exists():
        return pm
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    pm.realized_pnl = data.get("realized_pnl", 0.0)
    for cid, pos_data in data.get("positions", {}).items():
        try:
            pos = Position(**{k: v for k, v in pos_data.items() if k in Position.model_fields})
            pm.positions[cid] = pos
        except Exception as e:
            logging.warning("Position load skip %s: %s", cid[:16], e)
    return pm


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("manual_skip_dryrun")

    if not os.environ.get("ODDS_API_KEY"):
        log.error("ODDS_API_KEY env var bos")
        sys.exit(1)

    cfg = load_config()

    # Infrastructure
    gamma = GammaClient()
    odds = OddsAPIClient()
    scanner = MarketScanner(cfg.scanner, gamma_client=gamma)

    # Domain guards
    portfolio = _load_portfolio_event_ids()
    breaker = _NoHaltBreaker()
    cooldown = CooldownTracker(
        trigger_threshold=cfg.risk.consecutive_loss_cooldown,
        cooldown_cycles=cfg.risk.cooldown_cycles,
    )
    blacklist = Blacklist()  # boş

    def _enricher(market):
        return enrich_market(market, odds)

    def _manip(question: str, liquidity: float):
        return manipulation_check(
            question=question, liquidity=liquidity,
            min_liquidity_usd=cfg.manipulation.min_liquidity_usd,
        )

    gate = EntryGate(
        config=GateConfig(
            min_favorite_probability=cfg.entry.min_favorite_probability,
            max_entry_price=cfg.entry.max_entry_price,
            max_positions=cfg.risk.max_positions,
            max_exposure_pct=cfg.risk.max_exposure_pct,
            confidence_bet_pct=cfg.risk.confidence_bet_pct,
            max_single_bet_usdc=cfg.risk.max_single_bet_usdc,
            max_bet_pct=cfg.risk.max_bet_pct,
            probability_weighted=cfg.risk.probability_weighted,
        ),
        portfolio=portfolio,
        circuit_breaker=breaker,
        cooldown=cooldown,
        blacklist=blacklist,
        odds_enricher=_enricher,
        manipulation_checker=_manip,
    )

    log.info("Scanning...")
    markets = scanner.scan()
    log.info("Gate.run on %d markets", len(markets))
    results = gate.run(markets)

    # Ayrı dosyaya yaz (prod log'u kirletme)
    out_path = Path("logs/manual_skip_dryrun.jsonl")
    out_path.unlink(missing_ok=True)
    out_logger = SkippedTradeLogger(str(out_path))

    skip_count = 0
    approved_count = 0
    market_by_cid = {m.condition_id: m for m in markets}
    for r in results:
        if r.signal is not None:
            approved_count += 1
            continue
        m = market_by_cid.get(r.condition_id)
        if m is None:
            continue
        rec = SkippedTradeRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            slug=m.slug,
            sport_tag=m.sport_tag,
            question=m.question,
            event_id=m.event_id or "",
            entry_price=m.yes_price,
            skip_reason=r.skipped_reason or "unknown",
            skip_detail=r.skip_detail or "",
        )
        out_logger.log(rec)
        skip_count += 1

    log.info("Done. approved=%d, skipped=%d", approved_count, skip_count)
    log.info("Output: %s", out_path)


if __name__ == "__main__":
    main()
