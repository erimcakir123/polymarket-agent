"""SPEC-Z24: zararla kapanan condition_id türetimi. Pure, I/O yok. Domain.

Tekrar-giriş yasağı için kullanılır: bir markete girip net zararla kapandıysa
o market bu session bir daha açılmaz.
"""
from __future__ import annotations

from typing import Any


def closed_at_loss_cids(events: list[dict[str, Any]]) -> set[str]:
    """En az bir 'final' çıkışı olan VE net realized < 0 olan condition_id'ler.

    net realized = tüm 'partial' realized_pnl_usdc + tüm 'final' exit_pnl_usdc.
    Canlı akışta: episode-1 zararla kapanınca defterde net<0 görünür → bloklanır
    (gelecek kazanan episode henüz yoktur).
    """
    net: dict[str, float] = {}
    has_final: set[str] = set()
    for ev in events:
        cid = ev.get("condition_id")
        if not cid:
            continue
        kind = ev.get("kind")
        if kind == "partial":
            net[cid] = net.get(cid, 0.0) + float(ev.get("realized_pnl_usdc") or 0.0)
        elif kind == "final":
            net[cid] = net.get(cid, 0.0) + float(ev.get("exit_pnl_usdc") or 0.0)
            has_final.add(cid)
    return {cid for cid in has_final if net.get(cid, 0.0) < 0.0}
