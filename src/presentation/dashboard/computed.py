"""Dashboard pure derivations — raw dict'lerden metrik üretir.

I/O YOK, domain/infra import YOK. Readers'dan gelen raw dict'leri presentation
için işler (PnL toplamları, slot breakdown, drawdown %, vb.).

Her fonksiyon pure — aynı input → aynı output.
"""
from __future__ import annotations

from typing import Any

_DEFAULT_STOP_AT_PCT = 50.0
_DEFAULT_SAFE_PCT = 15.0
_DEFAULT_WARN_PCT = 30.0


# ── Position helpers (pure) ──

def _position_unrealized(pos: dict[str, Any]) -> float:
    """Token-native PnL hesabı. shares × current_price − size_usdc.

    Direction-agnostic çünkü current_price zaten pozisyon token'ının fiyatıdır
    (BUY_YES → YES token price, BUY_NO → NO token price). Hiçbir yön çevrimi
    gerekmez. Eski `_eff_price(current, direction)` yanlış hesaplıyordu.
    """
    shares = float(pos.get("shares", 0.0))
    size = float(pos.get("size_usdc", 0.0))
    current_price = float(pos.get("current_price", 0.0))
    return shares * current_price - size


# ── Public derivations ──

def _peak_total_equity(
    equity_history: list[dict[str, Any]] | None,
    current_total_equity: float,
    initial_bankroll: float,
) -> float:
    """Tüm zamanların total_equity zirvesi. equity_history.jsonl'den yükselir.
    Snapshot yoksa initial vs current'in max'ı.
    """
    candidates = [initial_bankroll, current_total_equity]
    for snap in equity_history or []:
        eq = (float(snap.get("bankroll", 0.0))
              + float(snap.get("invested", 0.0))
              + float(snap.get("unrealized_pnl", 0.0)))
        candidates.append(eq)
    return max(candidates)


def equity_summary(
    positions_blob: dict[str, Any],
    initial_bankroll: float,
    equity_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Balance / Open PnL / Realized / Locked / Peak + drawdown%.

    Peak Balance = total_equity'nin tüm zamanlardaki zirvesi (equity_history
    snapshots + current). Domain'deki PortfolioManager.high_water_mark sadece
    cash'i izliyor; dashboard için total_equity peak'i ayrı hesaplanır.
    """
    positions: dict[str, dict] = positions_blob.get("positions", {})
    realized = float(positions_blob.get("realized_pnl", 0.0))
    invested = sum(float(p.get("size_usdc", 0.0)) for p in positions.values())
    open_pnl = sum(_position_unrealized(p) for p in positions.values())
    # NOT: PortfolioManager.compute_bankroll bu modülde kullanılamaz —
    # `test_computed_module_has_no_layer_imports` domain import'u yasaklar.
    # Formül burada bilerek inline tutulur (yerel invariant > küresel DRY).
    bankroll = initial_bankroll + realized - invested
    total_equity = bankroll + invested + open_pnl
    peak = _peak_total_equity(equity_history, total_equity, initial_bankroll)
    drawdown_pct = 0.0 if peak <= 0 else max(0.0, (peak - total_equity) / peak * 100.0)
    return {
        "bankroll": round(bankroll, 2),
        "total_equity": round(total_equity, 2),
        "open_pnl": round(open_pnl, 2),
        "realized_pnl": round(realized, 2),
        "locked": round(invested, 2),
        "peak_balance": round(peak, 2),
        "drawdown_pct": round(drawdown_pct, 2),
        "position_count": len(positions),
    }


def slots_summary(positions_blob: dict[str, Any], max_positions: int) -> dict[str, Any]:
    """Anlık slot kullanımı + entry_reason breakdown."""
    positions: dict[str, dict] = positions_blob.get("positions", {})
    counts: dict[str, int] = {}
    for p in positions.values():
        reason = p.get("entry_reason", "normal") or "normal"
        counts[reason] = counts.get(reason, 0) + 1
    return {
        "current": len(positions),
        "max": max_positions,
        "by_reason": counts,
    }


def loss_protection(
    positions_blob: dict[str, Any],
    initial_bankroll: float,
    stop_at_pct: float = _DEFAULT_STOP_AT_PCT,
    safe_drawdown_pct: float = _DEFAULT_SAFE_PCT,
    warn_drawdown_pct: float = _DEFAULT_WARN_PCT,
    equity_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """RISK gauge + Down% + Stop at% + Safe/Caution/Warning/Stopped status.

    safe_drawdown_pct / warn_drawdown_pct: Safe→Caution ve Caution→Warning
    geçiş eşikleri. Config'den gelir, default'lar güvenli fallback.
    """
    summary = equity_summary(positions_blob, initial_bankroll, equity_history)
    down = summary["drawdown_pct"]
    if down >= stop_at_pct:
        status = "Stopped"
    elif down >= warn_drawdown_pct:
        status = "Warning"
    elif down >= safe_drawdown_pct:
        status = "Caution"
    else:
        status = "Safe"
    risk_pct = 0.0 if stop_at_pct <= 0 else min(100.0, down / stop_at_pct * 100.0)
    return {
        "down_pct": round(down, 2),
        "stop_at_pct": round(stop_at_pct, 2),
        "risk_pct": round(risk_pct, 2),
        "status": status,
    }


def closed_trades(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sadece kapanmış trade'ler (exit_price != null), kronolojik DESC."""
    closed = [t for t in trades if t.get("exit_price") is not None]
    closed.sort(key=lambda t: t.get("exit_timestamp", ""), reverse=True)
    return closed


def exit_events(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Full exit'ler + partial scale-out'ları tek liste olarak döner.

    Her full-close TradeRecord bir event, her partial_exit ayrı bir event.
    Exited tab source. Treemap aggregation `closed_trades` kullanmaya devam
    (yalnız full close).
    """
    events: list[dict[str, Any]] = []
    for t in trades:
        for pe in (t.get("partial_exits") or []):
            events.append({
                "slug": t.get("slug", ""),
                "sport_tag": t.get("sport_tag", ""),
                "direction": t.get("direction", ""),
                "entry_price": t.get("entry_price"),
                "question": t.get("question", ""),
                "exit_price": None,
                "exit_pnl_usdc": pe.get("realized_pnl_usdc", 0.0),
                "exit_reason": f"scale_out_tier_{pe.get('tier', '?')}",
                "exit_timestamp": pe.get("timestamp", ""),
                "partial": True,
                "sell_pct": pe.get("sell_pct", 0.0),
            })
        if t.get("exit_price") is not None:
            ev = dict(t)
            ev["partial"] = False
            events.append(ev)
    events.sort(key=lambda e: e.get("exit_timestamp", ""), reverse=True)
    return events


# Liglerden branşa map (treemap gruplaması için). Eski kayıtlarda sport_tag
# sadece lig kodu (ör. "mlb") olabiliyor; doğru branşa eşle.
_LEAGUE_TO_SPORT: dict[str, str] = {
    "mlb": "baseball",
    "nhl": "hockey", "ahl": "hockey", "khl": "hockey",
    "nba": "basketball", "wnba": "basketball",
    "nfl": "football", "cfl": "football",
    "epl": "soccer", "ucl": "soccer", "mls": "soccer", "seriea": "soccer",
    "wta": "tennis", "atp": "tennis",
    "pga": "golf", "lpga": "golf", "rbc": "golf",
}


def _sport_category(trade: dict[str, Any]) -> str:
    """Trade kaydından branş (sport category) türet: baseball, hockey, tennis, ...

    Öncelik: sport_category (yeni kayıt) → sport_tag split ("baseball_mlb" →
    "baseball") → lig→branş map (eski kayıt: "mlb" → "baseball") → sport_tag
    olduğu gibi → "unknown".
    """
    tag = (trade.get("sport_tag") or "").lower()
    # Yeni format: "baseball_mlb" — split'in ilk kısmı zaten branş.
    if "_" in tag:
        return tag.split("_", 1)[0]
    cat = (trade.get("sport_category") or "").lower()
    # sport_category gerçek branş mı yoksa (eski hatadan) lig kodu mu?
    if cat and cat not in _LEAGUE_TO_SPORT:
        return cat
    # Eski kayıt: lig kodunu branşa map et.
    if tag in _LEAGUE_TO_SPORT:
        return _LEAGUE_TO_SPORT[tag]
    return tag or "unknown"


def sport_roi_treemap(trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Trade history'den BRANŞ (sport category) bazında ROI aggregate.

    Sadece kapanmış trade'ler sayılır. Grup anahtarı: sport_category (baseball,
    hockey, tennis, ...). Field yoksa sport_tag'den türetilir.
    """
    groups: dict[str, dict[str, Any]] = {}
    for t in trades:
        if t.get("exit_price") is None:
            continue
        key = _sport_category(t)
        g = groups.setdefault(key, {
            "league": key, "trades": 0, "wins": 0, "losses": 0,
            "invested": 0.0, "net_pnl": 0.0,
        })
        pnl = float(t.get("exit_pnl_usdc") or 0.0)
        g["trades"] += 1
        g["invested"] += float(t.get("size_usdc") or 0.0)
        g["net_pnl"] += pnl
        if pnl > 0:
            g["wins"] += 1
        elif pnl < 0:
            g["losses"] += 1

    leagues: list[dict[str, Any]] = []
    for g in groups.values():
        g["roi"] = (g["net_pnl"] / g["invested"]) if g["invested"] > 0 else 0.0
        g["avg_size"] = (g["invested"] / g["trades"]) if g["trades"] > 0 else 0.0
        g["win_rate"] = (g["wins"] / g["trades"]) if g["trades"] > 0 else 0.0
        g["invested"] = round(g["invested"], 2)
        g["net_pnl"] = round(g["net_pnl"], 2)
        g["avg_size"] = round(g["avg_size"], 2)
        g["roi"] = round(g["roi"], 4)
        g["win_rate"] = round(g["win_rate"], 4)
        leagues.append(g)
    leagues.sort(key=lambda x: x["invested"], reverse=True)

    total_trades = sum(g["trades"] for g in groups.values())
    total_wins = sum(g["wins"] for g in groups.values())
    total_invested = sum(float(g["invested"]) for g in groups.values())
    total_pnl = sum(float(g["net_pnl"]) for g in groups.values())

    return {
        "summary": {
            "total_trades": total_trades,
            "win_rate": round(total_wins / total_trades, 4) if total_trades else 0.0,
            "portfolio_roi": round(total_pnl / total_invested, 4) if total_invested else 0.0,
        },
        "leagues": leagues,
    }


def win_loss(trades: list[dict[str, Any]]) -> dict[str, int]:
    """Kapanmış trade'lerden kazanma/kaybetme sayısı (PnL > 0 = win)."""
    wins = 0
    losses = 0
    for t in trades:
        if t.get("exit_price") is None:
            continue
        pnl = float(t.get("exit_pnl_usdc") or 0.0)
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1
    return {"wins": wins, "losses": losses}
