# tests/test_liquidity_check.py
import pytest


class TestLiquidityCheck:
    def test_nothing_to_sell(self):
        from src.liquidity_check import check_exit_liquidity
        result = check_exit_liquidity("token123", 0, mock_book={"bids": []})
        assert result["fillable"] is True
        assert result["strategy"] == "market"

    def test_no_bids(self):
        from src.liquidity_check import check_exit_liquidity
        result = check_exit_liquidity("token123", 100, mock_book={"bids": []})
        assert result["fillable"] is False
        assert result["strategy"] == "skip"

    def test_full_depth(self):
        from src.liquidity_check import check_exit_liquidity
        book = {"bids": [{"price": "0.50", "size": "200"}]}
        result = check_exit_liquidity("token123", 100, mock_book=book)
        assert result["fillable"] is True
        assert result["strategy"] == "market"

    def test_partial_depth(self):
        from src.liquidity_check import check_exit_liquidity
        book = {"bids": [{"price": "0.50", "size": "50"}]}
        result = check_exit_liquidity("token123", 100, mock_book=book)
        assert result["fillable"] is False
        assert result["strategy"] == "split"
