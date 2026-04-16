"""computed.py::_sport_category ve treemap branş gruplaması testleri."""
from __future__ import annotations

from src.presentation.dashboard.computed import _sport_category, sport_roi_treemap


def _trade(**kwargs):
    base = {
        "slug": "x",
        "exit_price": 0.5,  # kapalı trade (treemap'e dahil)
        "exit_pnl_usdc": 0.0,
        "size_usdc": 10.0,
        "partial_exits": [],
    }
    base.update(kwargs)
    return base


def test_sport_category_from_underscore_tag():
    assert _sport_category({"sport_tag": "baseball_mlb"}) == "baseball"


def test_sport_category_from_league_map_mlb():
    assert _sport_category({"sport_tag": "mlb"}) == "baseball"


def test_sport_category_from_league_map_nhl():
    assert _sport_category({"sport_tag": "nhl"}) == "hockey"


def test_sport_category_from_league_map_ahl():
    assert _sport_category({"sport_tag": "ahl"}) == "hockey"


def test_sport_category_tennis():
    assert _sport_category({"sport_tag": "wta"}) == "tennis"
    assert _sport_category({"sport_tag": "atp"}) == "tennis"


def test_sport_category_prefers_explicit_category_when_not_league_code():
    # sport_category "hockey" gerçek branş — döner.
    assert _sport_category({"sport_tag": "", "sport_category": "hockey"}) == "hockey"


def test_sport_category_ignores_category_if_it_is_a_league_code():
    # sport_category "mlb" aslında lig → map'ten branşa.
    assert _sport_category({"sport_tag": "mlb", "sport_category": "mlb"}) == "baseball"


def test_sport_category_unknown_fallback():
    assert _sport_category({"sport_tag": "xyz"}) == "xyz"


def test_sport_category_empty_defaults_unknown():
    assert _sport_category({}) == "unknown"


def test_treemap_merges_nhl_and_hockey_records():
    """Regression: nhl lig kodu + hockey branşı kayıtları tek 'hockey' grubunda."""
    trades = [
        _trade(sport_tag="nhl", exit_pnl_usdc=-10.0, size_usdc=50.0),
        _trade(sport_tag="hockey", exit_pnl_usdc=5.0, size_usdc=25.0),
        _trade(sport_tag="ahl", exit_pnl_usdc=-3.0, size_usdc=20.0),
    ]
    result = sport_roi_treemap(trades)
    leagues = {g["league"]: g for g in result["leagues"]}
    assert "hockey" in leagues
    assert "nhl" not in leagues  # ham lig kodu görünmemeli
    assert "ahl" not in leagues
    assert leagues["hockey"]["trades"] == 3
    assert leagues["hockey"]["invested"] == 95.0
    assert leagues["hockey"]["net_pnl"] == -8.0
