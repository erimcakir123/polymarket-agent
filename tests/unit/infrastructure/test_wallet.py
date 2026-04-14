"""wallet.py için birim testler."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.infrastructure.wallet import USDC_ADDRESS, USDC_DECIMALS, Wallet


def _resp(result_hex: str) -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock(return_value=None)
    r.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": result_hex}
    return r


TEST_KEY = "0x" + "11" * 32  # Geçerli 32-byte hex anahtar


def test_wallet_requires_private_key() -> None:
    with pytest.raises(ValueError):
        Wallet(private_key="")


def test_wallet_derives_address_from_key() -> None:
    w = Wallet(private_key=TEST_KEY)
    assert w.address.startswith("0x")
    assert len(w.address) == 42


def test_wallet_get_usdc_balance() -> None:
    http = MagicMock(return_value=_resp(hex(5_000_000)))  # 5 USDC
    w = Wallet(private_key=TEST_KEY, http_post=http)
    assert w.get_usdc_balance() == 5.0
    call = http.call_args
    payload = call.kwargs.get("json")
    assert payload["method"] == "eth_call"
    assert payload["params"][0]["to"] == USDC_ADDRESS
    assert payload["params"][0]["data"].startswith("0x70a08231")


def test_wallet_get_matic_balance() -> None:
    http = MagicMock(return_value=_resp(hex(10**18)))  # 1 MATIC
    w = Wallet(private_key=TEST_KEY, http_post=http)
    assert w.get_matic_balance() == 1.0


def test_wallet_http_error_returns_zero() -> None:
    http = MagicMock(side_effect=RuntimeError("timeout"))
    w = Wallet(private_key=TEST_KEY, http_post=http)
    assert w.get_usdc_balance() == 0.0
    assert w.get_matic_balance() == 0.0


def test_wallet_usdc_decimals_constant() -> None:
    assert USDC_DECIMALS == 6
