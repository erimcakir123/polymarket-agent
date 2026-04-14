"""Polygon USDC/MATIC balance reader."""
from __future__ import annotations

import logging
from typing import Any, Callable

import requests
from eth_account import Account

logger = logging.getLogger(__name__)

USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_DECIMALS = 6
DEFAULT_RPC = "https://polygon-rpc.com"
_DEFAULT_TIMEOUT = 10


def _default_http_post(url: str, json: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.post(url, json=json, timeout=timeout)


class Wallet:
    def __init__(
        self,
        private_key: str,
        rpc_url: str = DEFAULT_RPC,
        http_post: Callable[..., Any] = _default_http_post,
    ) -> None:
        if not private_key:
            raise ValueError("private_key is required")
        self.private_key = private_key
        self.rpc_url = rpc_url
        self._http = http_post
        self.address = Account.from_key(private_key).address

    def get_usdc_balance(self) -> float:
        addr = self.address.lower().replace("0x", "").zfill(64)
        data = f"0x70a08231{addr}"
        payload = {
            "jsonrpc": "2.0", "method": "eth_call",
            "params": [{"to": USDC_ADDRESS, "data": data}, "latest"],
            "id": 1,
        }
        return self._read_balance(payload, decimals=USDC_DECIMALS)

    def get_matic_balance(self) -> float:
        payload = {
            "jsonrpc": "2.0", "method": "eth_getBalance",
            "params": [self.address, "latest"],
            "id": 1,
        }
        return self._read_balance(payload, decimals=18)

    def _read_balance(self, payload: dict, decimals: int) -> float:
        try:
            resp = self._http(self.rpc_url, json=payload, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
            raw = int(resp.json()["result"], 16)
            return raw / (10 ** decimals)
        except Exception as e:
            logger.error("Wallet RPC failed (method=%s): %s", payload.get("method"), e)
            return 0.0
