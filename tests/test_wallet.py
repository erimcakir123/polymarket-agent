import pytest
from unittest.mock import patch, MagicMock


@patch("src.wallet.requests.post")
def test_get_usdc_balance(mock_post):
    from src.wallet import Wallet
    mock_resp = MagicMock()
    # USDC has 6 decimals, 60 USDC = 60_000_000
    mock_resp.json.return_value = {"result": hex(60_000_000)}
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp
    w = Wallet(private_key="0x" + "a" * 64, rpc_url="https://polygon-rpc.com")
    # Force address for test (eth_account may not be installed)
    w.address = "0x1234567890abcdef1234567890abcdef12345678"
    balance = w.get_usdc_balance()
    assert balance == pytest.approx(60.0)


def test_wallet_requires_private_key():
    from src.wallet import Wallet
    with pytest.raises(ValueError):
        Wallet(private_key="", rpc_url="https://polygon-rpc.com")
