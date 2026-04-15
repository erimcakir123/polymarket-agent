"""scanner.py için birim testler — filter + 4-bucket priority sort."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.config.settings import ScannerConfig
from src.models.market import MarketData
from src.orchestration.scanner import MarketScanner, _sort_key


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _market(
    cid: str = "c",
    sport_tag: str = "basketball_nba",
    match_start: datetime | None = None,
    end_date: datetime | None = None,
    liquidity: float = 5000,
    volume: float = 1000,
    market_type: str = "moneyline",
    closed: bool = False,
) -> MarketData:
    return MarketData(
        condition_id=cid,
        question=f"Q? {cid}",
        slug=f"s-{cid}",
        yes_token_id=f"y{cid}", no_token_id=f"n{cid}",
        yes_price=0.50, no_price=0.50,
        liquidity=liquidity, volume_24h=volume,
        tags=[],
        end_date_iso=_iso(end_date) if end_date else "",
        match_start_iso=_iso(match_start) if match_start else "",
        sport_tag=sport_tag, sports_market_type=market_type,
        closed=closed,
    )


def _config(**over) -> ScannerConfig:
    base = ScannerConfig(
        min_liquidity=1000,
        max_markets_per_cycle=300,
        max_duration_days=14,
        allowed_sport_tags=["basketball_nba", "icehockey_nhl", "tennis_*"],
    )
    for k, v in over.items():
        setattr(base, k, v)
    return base


# ── Filters ──

def test_closed_markets_filtered() -> None:
    now = datetime.now(timezone.utc)
    m = _market(closed=True, end_date=now + timedelta(days=1))
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert sc.scan() == []


def test_non_moneyline_filtered() -> None:
    now = datetime.now(timezone.utc)
    m = _market(market_type="spreads", end_date=now + timedelta(days=1))
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert sc.scan() == []


def test_empty_sports_market_type_filtered() -> None:
    """PGA Top-N gibi marketlerde sports_market_type='' — strict reject."""
    now = datetime.now(timezone.utc)
    m = _market(
        market_type="",
        match_start=now + timedelta(hours=12),
        end_date=now + timedelta(hours=14),
    )
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert sc.scan() == []


def test_match_start_beyond_24h_filtered() -> None:
    """Odds API penceresi 24h — daha uzak maçlar scanner'da elenir."""
    now = datetime.now(timezone.utc)
    m = _market(
        match_start=now + timedelta(hours=30),
        end_date=now + timedelta(hours=32),
    )
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert sc.scan() == []


def test_match_start_within_24h_kept() -> None:
    """23h sonrası — kalır."""
    now = datetime.now(timezone.utc)
    m = _market(
        match_start=now + timedelta(hours=23),
        end_date=now + timedelta(hours=25),
    )
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert len(sc.scan()) == 1


def test_not_allowed_sport_filtered() -> None:
    now = datetime.now(timezone.utc)
    m = _market(sport_tag="soccer_epl", end_date=now + timedelta(days=1))
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert sc.scan() == []


def test_low_liquidity_filtered() -> None:
    now = datetime.now(timezone.utc)
    m = _market(liquidity=500, end_date=now + timedelta(days=1))
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert sc.scan() == []


def test_duration_beyond_limit_filtered() -> None:
    now = datetime.now(timezone.utc)
    m = _market(end_date=now + timedelta(days=30))
    sc = MarketScanner(_config(max_duration_days=14), gamma_client=_mock_gamma([m]))
    assert sc.scan() == []


def test_stale_match_start_filtered() -> None:
    # Sezon-uzunluğu futures: match_start 6 ay önce → atla
    now = datetime.now(timezone.utc)
    m = _market(
        match_start=now - timedelta(days=180),
        end_date=now + timedelta(days=2),
    )
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert sc.scan() == []


def test_recently_started_kept() -> None:
    # Maç 2 saat önce başlamış (live) → kalır
    now = datetime.now(timezone.utc)
    m = _market(
        match_start=now - timedelta(hours=2),
        end_date=now + timedelta(hours=2),
    )
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert len(sc.scan()) == 1


def test_just_under_8h_boundary_kept() -> None:
    # 7 saat önce başlamış → kalır
    now = datetime.now(timezone.utc)
    m = _market(
        match_start=now - timedelta(hours=7),
        end_date=now + timedelta(hours=2),
    )
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert len(sc.scan()) == 1


def test_just_over_8h_boundary_filtered() -> None:
    # 9 saat önce başlamış → atla
    now = datetime.now(timezone.utc)
    m = _market(
        match_start=now - timedelta(hours=9),
        end_date=now + timedelta(hours=2),
    )
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert sc.scan() == []


def test_tennis_wildcard_matches() -> None:
    now = datetime.now(timezone.utc)
    m = _market(sport_tag="tennis_atp_french_open", match_start=now + timedelta(hours=3),
                end_date=now + timedelta(hours=6))
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([m]))
    assert len(sc.scan()) == 1


# ── Priority sort ──

def test_imminent_before_midrange() -> None:
    """Bucket sort (imminent → midrange → discovery) — config'i geniş tut
    ki discovery (>24h default cap) de testi etkilemesin."""
    now = datetime.now(timezone.utc)
    imminent = _market(cid="imm", match_start=now + timedelta(hours=2),
                       end_date=now + timedelta(hours=5))
    midrange = _market(cid="mid", match_start=now + timedelta(hours=10),
                       end_date=now + timedelta(hours=13))
    discovery = _market(cid="disc", match_start=now + timedelta(hours=48),
                        end_date=now + timedelta(days=3))
    sc = MarketScanner(_config(max_hours_to_start=72), gamma_client=_mock_gamma([discovery, midrange, imminent]))
    result = sc.scan()
    assert [m.condition_id for m in result] == ["imm", "mid", "disc"]


def test_within_bucket_sorted_by_hours_then_volume() -> None:
    now = datetime.now(timezone.utc)
    # İki imminent — daha yakını önce
    a = _market(cid="a", match_start=now + timedelta(hours=1),
                end_date=now + timedelta(hours=4), volume=500)
    b = _market(cid="b", match_start=now + timedelta(hours=3),
                end_date=now + timedelta(hours=6), volume=2000)
    # Aynı saatte iki imminent — hacim DESC tiebreak
    c = _market(cid="c", match_start=now + timedelta(hours=1),
                end_date=now + timedelta(hours=4), volume=5000)
    sc = MarketScanner(_config(), gamma_client=_mock_gamma([b, a, c]))
    result = sc.scan()
    # 1 saat olanlar önce (c 5000 > a 500), sonra 3 saat
    assert [m.condition_id for m in result] == ["c", "a", "b"]


def test_unknown_time_bucket_after_imminent() -> None:
    now = datetime.now(timezone.utc)
    imm = _market(cid="imm", match_start=now + timedelta(hours=4),
                  end_date=now + timedelta(hours=7))
    # No match_start, end_date 30h → bucket 1 (unknown ≤48h). Config'i geniş tut.
    unk = _market(cid="unk", end_date=now + timedelta(hours=30))
    sc = MarketScanner(_config(max_hours_to_start=48), gamma_client=_mock_gamma([unk, imm]))
    result = sc.scan()
    assert [m.condition_id for m in result] == ["imm", "unk"]


# ── Top N cap ──

def test_top_n_cap() -> None:
    now = datetime.now(timezone.utc)
    markets = [
        _market(cid=f"m{i}", match_start=now + timedelta(hours=i + 1),
                end_date=now + timedelta(hours=i + 4))
        for i in range(10)
    ]
    sc = MarketScanner(_config(max_markets_per_cycle=3), gamma_client=_mock_gamma(markets))
    assert len(sc.scan()) == 3


def _mock_gamma(markets: list[MarketData]) -> MagicMock:
    g = MagicMock()
    g.fetch_events.return_value = markets
    return g
