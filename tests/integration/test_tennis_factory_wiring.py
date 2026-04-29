"""Integration test: when tennis is enabled in config, factory must
construct a fully-wired TennisMagnusPredictor and inject it into the
TennisPaperObserver. Prevents regression of the silent-no-op bug where
observe_pre_match returns immediately because predictor=None.
"""
from __future__ import annotations

from pathlib import Path

from src.orchestration.tennis_magnus_predictor import TennisMagnusPredictor
from src.orchestration.tennis_paper_observer import TennisPaperObserver


_FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "sackmann"


def _write_min_config(cfg_path: Path, *, tennis_enabled: bool, phase: str) -> None:
    cfg_path.write_text(
        f"""
mode: dry_run
initial_bankroll: 1000.0
score:
  enabled: false
tennis:
  enabled: {str(tennis_enabled).lower()}
  phase: {phase}
  data:
    sackmann_cache_dir: "data/sackmann_cache/"
    sackmann_refresh_days: 7
""",
        encoding="utf-8",
    )


def _seed_sackmann_cache(tmp_path: Path) -> None:
    """Pre-populate cache so refresh_atp_data sees fresh files (no fetch)."""
    cache_dir = tmp_path / "data" / "sackmann_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    players_src = _FIXTURE_DIR / "atp_players_sample.csv"
    matches_src = _FIXTURE_DIR / "atp_matches_2025_sample.csv"
    (cache_dir / "atp_players.csv").write_text(
        players_src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (cache_dir / "wta_players.csv").write_text(
        players_src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    matches_text = matches_src.read_text(encoding="utf-8")
    # Seed both years for ATP and WTA so needs_refresh returns False
    for filename in (
        "atp_matches_2025.csv",
        "atp_matches_2024.csv",
        "wta_matches_2025.csv",
        "wta_matches_2024.csv",
    ):
        (cache_dir / filename).write_text(matches_text, encoding="utf-8")


def _stub_sackmann_network(monkeypatch) -> None:
    """Belt-and-suspenders: stub network call so test is hermetic even if
    cache freshness check fires."""
    from src.infrastructure.apis import sackmann_client

    def _fake_fetch(url, cache_path, timeout=30):
        return cache_path.exists()

    monkeypatch.setattr(sackmann_client, "fetch_csv_to_cache", _fake_fetch)


def test_factory_wires_tennis_predictor_when_phase_paper_trade(
    tmp_path, monkeypatch
) -> None:
    """When tennis.phase != 'disabled', factory must wire predictor (not None)."""
    monkeypatch.chdir(tmp_path)
    cfg_path = tmp_path / "config.yaml"
    _write_min_config(cfg_path, tennis_enabled=True, phase="paper_trade")
    _seed_sackmann_cache(tmp_path)
    _stub_sackmann_network(monkeypatch)

    from src.config.settings import load_config
    from src.orchestration.factory import build_agent
    from src.orchestration.startup import bootstrap

    cfg = load_config(cfg_path)
    state = bootstrap(cfg, logs_dir=tmp_path / "logs")
    agent = build_agent(state)

    observer = agent.deps.tennis_observer
    assert observer is not None, "Observer must be constructed when phase != disabled"
    assert isinstance(observer, TennisPaperObserver)
    assert observer._predictor is not None, (
        "Predictor must be wired (was None — silent no-op bug)"
    )
    assert isinstance(observer._predictor, TennisMagnusPredictor)


def test_factory_skips_tennis_observer_when_phase_disabled(
    tmp_path, monkeypatch
) -> None:
    """When tennis.phase == 'disabled', observer is None (no overhead)."""
    monkeypatch.chdir(tmp_path)
    cfg_path = tmp_path / "config.yaml"
    _write_min_config(cfg_path, tennis_enabled=False, phase="disabled")

    from src.config.settings import load_config
    from src.orchestration.factory import build_agent
    from src.orchestration.startup import bootstrap

    cfg = load_config(cfg_path)
    state = bootstrap(cfg, logs_dir=tmp_path / "logs")
    agent = build_agent(state)

    assert agent.deps.tennis_observer is None


def test_tennis_observer_called_with_full_scan_output_not_active_sports_batch(
    monkeypatch, tmp_path
) -> None:
    """Regression: hook must run on full scan_fresh, not on filtered batch.

    Tennis is intentionally excluded from active_sports (paper-only). If
    the hook fires AFTER the active_sports filter, tennis markets never
    reach it and Phase 0 paper log stays empty.
    """
    from unittest.mock import MagicMock
    from src.orchestration.entry_processor import EntryProcessor
    from src.models.market import MarketData

    tennis_market = MarketData(
        condition_id="ten1",
        slug="atp-fils-lehecka-2026-04-29",
        question="Madrid Open: Arthur Fils vs Jiri Lehecka",
        sport_tag="tennis",
        sports_market_type="moneyline",
        yes_price=0.615,
        no_price=0.385,
        liquidity=105000.0,
        volume_24h=10000.0,
        match_start_iso="2026-04-29T22:00:00Z",
        end_date_iso="2026-04-30T01:00:00Z",
        closed=False,
        resolved=False,
        accepting_orders=True,
        yes_token_id="t1",
        no_token_id="t2",
        event_id="e1",
        tags=[],
    )

    observer_calls: list[str] = []

    class FakeObserver:
        def observe_pre_match(
            self,
            market,
            tournament_info,
            polymarket_a_price,
            polymarket_b_price,
        ):
            observer_calls.append(market.slug)

    deps = MagicMock()
    deps.scanner.scan.return_value = [tennis_market]
    deps.tennis_observer = FakeObserver()
    deps.gate.config.active_sports = ["basketball_nba", "icehockey_nhl"]
    deps.gate.config.max_positions = 50
    deps.state.portfolio.count.return_value = 3
    deps.state.portfolio.positions = {}
    deps.stock.config.jit_batch_multiplier = 3
    deps.stock.top_n_by_match_start.return_value = []
    deps.stock.has.return_value = False
    deps.gate.run.return_value = []

    tennis_cfg = MagicMock()
    tennis_cfg.tournaments = {
        "masters_1000": {"madrid_open": "clay"},
    }
    tennis_cfg.excluded_tiers = ["itf", "challenger", "futures"]
    deps.state.config.tennis = tennis_cfg
    deps.state.config.mode.value = "dry_run"

    proc = EntryProcessor(deps=deps)
    proc.run_heavy()

    assert "atp-fils-lehecka-2026-04-29" in observer_calls, (
        f"Tennis observer not called! observer_calls={observer_calls}. "
        "Hook must fire on full scan_fresh BEFORE active_sports filter."
    )
