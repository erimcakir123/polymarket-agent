"""harvested_result — taze sonuç dataclass + kazanan çıkarımı testleri."""
from src.domain.pricing.tennis.harvested_result import (
    HarvestedResult,
    winner_loser_from_resolution,
)


def _resolved(prices: str) -> dict:
    return {"closed": True, "umaResolutionStatus": "resolved", "outcomePrices": prices}


def test_yes_side_won_returns_player_a_as_winner():
    # prices=['1','0'] → YES (ilk oyuncu) kazandı
    out = winner_loser_from_resolution(_resolved('["1","0"]'), "Alice", "Bob")
    assert out == ("Alice", "Bob")


def test_no_side_won_returns_player_b_as_winner():
    out = winner_loser_from_resolution(_resolved('["0","1"]'), "Alice", "Bob")
    assert out == ("Bob", "Alice")


def test_unresolved_market_returns_none():
    m = {"closed": False, "umaResolutionStatus": "", "outcomePrices": '["1","0"]'}
    assert winner_loser_from_resolution(m, "Alice", "Bob") is None


def test_void_5050_payout_returns_none():
    # 0.5/0.5 → iptal/void, sonuç yok
    assert winner_loser_from_resolution(_resolved('["0.5","0.5"]'), "Alice", "Bob") is None


def test_missing_player_name_returns_none():
    assert winner_loser_from_resolution(_resolved('["1","0"]'), "", "Bob") is None
    assert winner_loser_from_resolution(_resolved('["1","0"]'), "Alice", None) is None


def test_harvested_result_key_is_order_independent_on_pair():
    r = HarvestedResult(winner="Alice", loser="Bob", surface="Clay", date="20260612")
    assert r.match_key() == "20260612|Alice|Bob"
