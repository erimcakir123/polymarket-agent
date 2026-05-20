"""CLOB price-history fetcher — replay engine için (saf okuma, kayıt değil).

`price_history.py` PriceHistorySaver: exit anında snapshot kaydeder.
Bu dosya: retroactive replay için historik fiyat çeker, kayıt etmez.

Endpoint:
  GET https://clob.polymarket.com/prices-history?market={token_id}&interval=max&fidelity=1
  Returns: {"history": [{"t": unix_seconds, "p": price}, ...]}

İade formatı domain replay engine'in beklediği şekilde normalize edilir:
  list[dict] -> [{"timestamp_iso": "2026-05-20T16:00:00+00:00", "price": 0.41}, ...]
Entry öncesi noktalar opsiyonel olarak filtrelenir (start_iso parametresi).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

_CLOB_HISTORY_URL = "https://clob.polymarket.com/prices-history"
_DEFAULT_TIMEOUT_SEC = 15
_DEFAULT_FIDELITY = "1"  # 1-dakika candle (spec: max çözünürlük replay için)
_DEFAULT_INTERVAL = "max"


def _default_http_get(url: str, params: dict, timeout: int) -> Any:
    return requests.get(url, params=params, timeout=timeout)


def _parse_iso(iso: str) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def fetch_price_history(
    token_id: str,
    start_iso: str = "",
    end_iso: str = "",
    fidelity: str = _DEFAULT_FIDELITY,
    interval: str = _DEFAULT_INTERVAL,
    http_get: Callable[..., Any] = _default_http_get,
    timeout: int = _DEFAULT_TIMEOUT_SEC,
) -> list[dict]:
    """CLOB'tan token_id için fiyat geçmişini çek.

    Args:
        token_id: Polymarket token id (markets.tokens[*].token_id).
        start_iso: Filtre alt sınırı (entry timestamp). Boşsa filtrelenmez.
        end_iso:   Filtre üst sınırı (exit timestamp). Boşsa now sınırı yok.
        fidelity:  Candle çözünürlüğü dakika cinsinden (default "1" = 1dk).
        interval:  CLOB interval flag (default "max" = tüm tarih).

    Returns:
        list[{"timestamp_iso", "price"}] — start/end filtrelenmiş, kronolojik sıralı.
        Hata/boş yanıt durumunda []. Sessiz hata yutma yok: WARNING log + boş döndür.
    """
    try:
        resp = http_get(
            _CLOB_HISTORY_URL,
            params={"market": token_id, "interval": interval, "fidelity": fidelity},
            timeout=timeout,
        )
        if resp.status_code != 200:
            logger.warning(
                "price_history fetch token=%s status=%d", token_id[:12], resp.status_code,
            )
            return []
        raw = resp.json().get("history", []) or []
    except (requests.RequestException, ValueError) as e:
        logger.warning("price_history fetch failed token=%s err=%s", token_id[:12], e)
        return []

    start_dt = _parse_iso(start_iso)
    end_dt = _parse_iso(end_iso)

    points: list[dict] = []
    for row in raw:
        try:
            ts_unix = int(row["t"])
            price = float(row["p"])
        except (KeyError, TypeError, ValueError):
            continue
        ts_dt = datetime.fromtimestamp(ts_unix, tz=timezone.utc)
        if start_dt is not None and ts_dt < start_dt:
            continue
        if end_dt is not None and ts_dt > end_dt:
            continue
        points.append({"timestamp_iso": ts_dt.isoformat(), "price": price})

    points.sort(key=lambda p: p["timestamp_iso"])
    return points
