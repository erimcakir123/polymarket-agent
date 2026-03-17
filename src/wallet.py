"""On-chain USDC/MATIC balance and allowance checks on Polygon."""
from __future__ import annotations
import logging

import requests

logger = logging.getLogger(__name__)

USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_DECIMALS = 6
DEFAULT_RPC = "https://polygon-rpc.com"


class Wallet:
    def __init__(self, private_key: str, rpc_url: str = DEFAULT_RPC) -> None:
        if not private_key:
            raise ValueError("Private key is required")
        self.private_key = private_key
        self.rpc_url = rpc_url
        # Derive address from private key
        try:
            from eth_account import Account
            self.address = Account.from_key(private_key).address
        except ImportError:
            # Fallback: address must be provided separately
            self.address = ""
            logger.warning("eth_account not installed — address derivation unavailable")

    def get_usdc_balance(self) -> float:
        """Get USDC balance on Polygon via RPC."""
        if not self.address:
            logger.error("No wallet address available")
            return 0.0
        # balanceOf(address) selector = 0x70a08231
        addr_padded = self.address.lower().replace("0x", "").zfill(64)
        data = f"0x70a08231{addr_padded}"
        payload = {
            "jsonrpc": "2.0", "method": "eth_call",
            "params": [{"to": USDC_ADDRESS, "data": data}, "latest"],
            "id": 1,
        }
        try:
            resp = requests.post(self.rpc_url, json=payload, timeout=10)
            resp.raise_for_status()
            raw = int(resp.json()["result"], 16)
            return raw / (10 ** USDC_DECIMALS)
        except Exception as e:
            logger.error("Failed to get USDC balance: %s", e)
            return 0.0

    def get_matic_balance(self) -> float:
        """Get MATIC balance for gas."""
        if not self.address:
            return 0.0
        payload = {
            "jsonrpc": "2.0", "method": "eth_getBalance",
            "params": [self.address, "latest"],
            "id": 1,
        }
        try:
            resp = requests.post(self.rpc_url, json=payload, timeout=10)
            resp.raise_for_status()
            raw = int(resp.json()["result"], 16)
            return raw / (10 ** 18)
        except Exception as e:
            logger.error("Failed to get MATIC balance: %s", e)
            return 0.0
