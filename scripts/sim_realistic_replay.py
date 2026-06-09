"""SPEC-SIM: Geriye dönük gerçekçi çıkış simülasyonu (Faz 1 — salt-okunur).

Bugünün tüm pozisyonlarını gerçek dakika-dakika fiyat geçmişine karşı yeniden
oynatır; bağlı olunsaydı tetiklenecek kademeli kâr-alma / partial-SL / near-resolve
olaylarını ortaya çıkarır. "Gerçekte olan" (tek seferde satış) ile "gerçekçi olan"ı
(kademeli olaylar) yan yana gösterir.

GÜVENLİK (DEMİR): Hiçbir bot-state dosyasına YAZMAZ. Ağ erişimi yalnızca
Polymarket prices-history GET. Çalışan bota / üretim koduna dokunmaz. Saat,
sadece bu sürecin belleğinde geçmişe sabitlenir (monitor + near_resolve).

Çalıştırma:  python scripts/sim_realistic_replay.py
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

from src.config.settings import load_config
from src.domain.portfolio.lifecycle import tick_position_state
from src.models.enums import ExitReason
from src.models.position import Position
from src.strategy.exit import monitor as exit_monitor
from src.strategy.exit import near_resolve

logger = logging.getLogger(__name__)

_CLOB_HISTORY_URL = "https://clob.polymarket.com/prices-history"
_HISTORY_TIMEOUT_SEC = 15
_HISTORY_FIDELITY = "60"  # 60 saniyelik çözünürlük (prices-history en ince pratik)

_POSITIONS_PATH = Path("data/positions.json")
# Bugün açık olup kapanan pozisyonların giriş durumu (3'ünü de içerir, 02:53 yedeği)
_CLOSED_BACKUP_PATH = Path("data/positions.json.bak.realistic_close_20260608_025345")
_TRADE_EVENTS_PATH = Path("logs/audit/trade_events.jsonl")
# Bugün UTC 11:00 = UTC+3 14:00 — bu andan itibaren girilen trade'ler taranır.
_CUTOFF_ISO = "2026-06-08T11:00:00+00:00"

_real_datetime = datetime  # enjeksiyon sırasında gerçek sınıfa erişim


class _FrozenClock:
    """monitor/near_resolve içindeki `datetime`'ı geçmiş tick zamanına sabitler.

    Sadece sim sürecinin belleğinde geçerli. Çalışan bot ayrı süreç → etkilenmez.
    """
    current: Any = None

    @classmethod
    def now(cls, tz: Any = None) -> Any:
        return cls.current

    @classmethod
    def fromisoformat(cls, s: str) -> Any:
        return _real_datetime.fromisoformat(s)


@dataclass(frozen=True)
class ReplayEvent:
    kind: str            # ExitReason.value (scale_out | partial_sl | near_resolve | ...)
    tier: int | None
    time_iso: str
    price: float
    shares_sold: float
    sell_pct: float
    realized: float


@dataclass
class ReplayResult:
    events: list[ReplayEvent] = field(default_factory=list)
    realized_total: float = 0.0
    remaining_shares: float = 0.0
    closed: bool = False


def _reset_to_entry(pos: Position) -> Position:
    """Pozisyonun derin kopyasını giriş anına sıfırlar (canlı/momentum state temiz)."""
    sim = pos.model_copy(deep=True)
    sim.current_price = sim.entry_price
    sim.bid_price = sim.entry_price
    sim.peak_pnl_pct = 0.0
    sim.peak_price = 0.0
    sim.ever_in_profit = False
    sim.consecutive_down_cycles = 0
    sim.cumulative_drop = 0.0
    sim.previous_cycle_price = 0.0
    sim.cycles_held = 0
    sim.scale_out_tier = 0
    sim.scale_out_realized_usdc = 0.0
    sim.partial_sl_tier = 0
    sim.partial_sl_realized_usdc = 0.0
    return sim


def replay_position(
    pos: Position,
    price_series: list[tuple[float, float]],
    *,
    scale_out_tiers: list,
    partial_sl_tiers: list,
    partial_sl_enabled: bool = True,
    graduated_sl_enabled: bool = False,
    near_resolve_threshold_cents: int = 94,
    near_resolve_guard_min: int = 10,
    near_resolve_max_spread: float = 0.10,
    high_entry_threshold: float = 0.0,
    high_entry_upper: float = 0.0,
    liquidity_floor: float = 0.05,
    resolved_hi: float = 0.98,
    resolved_lo: float = 0.02,
) -> ReplayResult:
    """Botun gerçek çıkış beynini fiyat serisine karşı oynat (HİPER-gerçekçi).

    price_series: [(epoch_seconds, price), ...] artan sıralı, giriş anından itibaren.
    Her tick'te tick_position_state + monitor.evaluate; tetiklenen her çıkış bir olay.
    realized = satılan_hisse × (fiyat − entry_price)  (exit_processor._book_sale ile birebir).

    Gerçekçilik:
      - liquidity_floor: fiyat bu eşiğin altındayken SATMAZ (boş defter — gerçek bot
        "empty_book" reddi verir, pozisyonu tutar). Kâr çıkışları yüksek fiyatta olduğu
        için etkilenmez; sadece çökmüş pozisyonun stop-loss'unu engeller.
      - settlement: seri sonunda maç çözülmüşse (son fiyat ≥resolved_hi veya ≤resolved_lo)
        kalan hisse payout'ta yerleşir (botun resolution-detector davranışı). Maç
        sürüyorsa kalan hisse açık bırakılır (yerleşme yok).
    """
    sim = _reset_to_entry(pos)
    events: list[ReplayEvent] = []
    realized_total = 0.0
    closed = False

    orig_monitor_dt = exit_monitor.datetime
    orig_nr_dt = near_resolve.datetime
    exit_monitor.datetime = _FrozenClock
    near_resolve.datetime = _FrozenClock
    try:
        for t, price in price_series:
            if closed:
                break
            _FrozenClock.current = _real_datetime.fromtimestamp(t, tz=timezone.utc)
            sim.current_price = price
            sim.bid_price = price  # tek fiyat → spread 0 (near_resolve guard'ı geçer)
            tick_position_state(sim)
            result = exit_monitor.evaluate(
                sim,
                near_resolve_threshold_cents=near_resolve_threshold_cents,
                near_resolve_guard_min=near_resolve_guard_min,
                near_resolve_max_spread=near_resolve_max_spread,
                scale_out_tiers=scale_out_tiers,
                partial_sl_tiers=partial_sl_tiers,
                partial_sl_enabled=partial_sl_enabled,
                graduated_sl_enabled=graduated_sl_enabled,
                high_entry_threshold=high_entry_threshold,
                high_entry_upper=high_entry_upper,
            )
            sig = result.exit_signal
            if sig is None:
                continue
            if price < liquidity_floor:
                # Boş defter: bu fiyatta alıcı yok → gerçek bot reddeder, pozisyonu
                # tutar (tier sayacı artmaz, sonraki tick yeniden dener).
                continue
            ev_time = _FrozenClock.current.isoformat()
            if sig.partial:
                shares_sold = sim.shares * sig.sell_pct
                realized = shares_sold * (price - sim.entry_price)
                sim.shares -= shares_sold
                sim.size_usdc *= (1.0 - sig.sell_pct)
                if sig.reason == ExitReason.PARTIAL_SL:
                    sim.partial_sl_tier = sig.tier or sim.partial_sl_tier
                else:
                    sim.scale_out_tier = sig.tier or sim.scale_out_tier
                events.append(ReplayEvent(
                    sig.reason.value, sig.tier, ev_time, price,
                    shares_sold, sig.sell_pct, realized,
                ))
                realized_total += realized
            else:
                shares_sold = sim.shares
                realized = shares_sold * (price - sim.entry_price)
                events.append(ReplayEvent(
                    sig.reason.value, sig.tier, ev_time, price,
                    shares_sold, 1.0, realized,
                ))
                realized_total += realized
                sim.shares = 0.0
                closed = True

        # Çözüm yerleşimi: maç bittiyse kalan hisse payout'ta yerleşir (0/1).
        if not closed and sim.shares > 1e-9 and price_series:
            last_t, last_price = price_series[-1]
            if last_price >= resolved_hi or last_price <= resolved_lo:
                realized = sim.shares * (last_price - sim.entry_price)
                events.append(ReplayEvent(
                    "settlement", None,
                    _real_datetime.fromtimestamp(last_t, tz=timezone.utc).isoformat(),
                    last_price, sim.shares, 1.0, realized,
                ))
                realized_total += realized
                sim.shares = 0.0
                closed = True
    finally:
        exit_monitor.datetime = orig_monitor_dt
        near_resolve.datetime = orig_nr_dt

    return ReplayResult(
        events=events, realized_total=realized_total,
        remaining_shares=sim.shares, closed=closed,
    )


# ── I/O (script seviyesi — domain değil) ──

def fetch_price_history(
    token_id: str, http_get: Callable[..., Any] = requests.get,
) -> list[tuple[float, float]]:
    """Polymarket prices-history → [(epoch_s, price), ...]. Hata → [] (loglar)."""
    try:
        resp = http_get(
            _CLOB_HISTORY_URL,
            params={"market": token_id, "interval": "max", "fidelity": _HISTORY_FIDELITY},
            timeout=_HISTORY_TIMEOUT_SEC,
        )
        if resp.status_code != 200:
            logger.warning("prices-history %s status=%d", token_id[:16], resp.status_code)
            return []
        hist = resp.json().get("history", [])
    except Exception as e:  # noqa: BLE001 — script sınırı; logla + boş dön
        logger.warning("prices-history fetch failed %s: %s", token_id[:16], e)
        return []
    out: list[tuple[float, float]] = []
    for pt in hist:
        try:
            out.append((float(pt["t"]), float(pt["p"])))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _load_positions(path: Path) -> dict[str, Position]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {cid: Position(**v) for cid, v in data.get("positions", {}).items()}


def _load_actual_realized(path: Path) -> dict[str, float]:
    """trade_events.jsonl: cid → gerçek TOPLAM realized (tüm kademe + final dilimler).

    Önemli: bir pozisyon kademeli satıldıysa realized = partial'ların + final'in toplamı.
    Sadece final'i saymak (eski hata) kademeli satışları olduğundan düşük gösterir.
    """
    totals: dict[str, float] = {}
    if not path.exists():
        return totals
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        cid = ev.get("condition_id", "")
        if ev.get("kind") == "partial":
            totals[cid] = totals.get(cid, 0.0) + (ev.get("realized_pnl_usdc") or 0.0)
        elif ev.get("kind") == "final":
            totals[cid] = totals.get(cid, 0.0) + (ev.get("exit_pnl_usdc") or 0.0)
    return totals


# ── Rapor + main ──

def _load_exit_times(path: Path) -> dict[str, Any]:
    """cid → en son çıkış/satış olayının zamanı (datetime). Scope filtresi için."""
    times: dict[str, Any] = {}
    if not path.exists():
        return times
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = ev.get("exit_timestamp") or ev.get("timestamp")
        if not ts:
            continue
        cid = ev.get("condition_id", "")
        try:
            dt = _real_datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            continue
        if cid not in times or dt > times[cid]:
            times[cid] = dt
    return times


def _evaluate_kwargs(cfg: Any) -> dict:
    """Gerçek bot config'inden monitor.evaluate parametreleri (exit_processor ile aynı)."""
    return dict(
        scale_out_tiers=cfg.scale_out.tiers,
        partial_sl_tiers=cfg.partial_sl.tiers,
        partial_sl_enabled=cfg.partial_sl.enabled,
        graduated_sl_enabled=cfg.graduated_sl.enabled,
        near_resolve_max_spread=cfg.price_feed.max_spread_for_near_resolve,
        high_entry_threshold=cfg.scale_out.high_entry_threshold,
        high_entry_upper=cfg.scale_out.high_entry_upper,
    )


def _hhmm(iso: str) -> str:
    try:
        return _real_datetime.fromisoformat(iso).strftime("%H:%M")
    except (ValueError, TypeError):
        return "--:--"


def _print_position(
    pos: Position, res: ReplayResult, state: str, actual_realized: float, last_price: float,
) -> None:
    label = (pos.slug or pos.question or pos.condition_id)[:46]
    outcome = "KAZANDI" if last_price >= 0.9 else ("KAYBETTİ" if last_price <= 0.1 else "sürüyor")
    print(f"\n{label}  (giriş {pos.entry_price:.2f}, {pos.shares:.0f} hisse)  [{state}] → {outcome}")
    if state == "KAPANDI":
        print(f"  GERÇEKTE OLAN : kapandı → toplam realized ${actual_realized:+.2f}")
    elif abs(actual_realized) >= 0.005:
        print(f"  GERÇEKTE OLAN : hâlâ açık, şimdiye dek realized ${actual_realized:+.2f} (kademe satışları)")
    else:
        print("  GERÇEKTE OLAN : hâlâ açık (henüz satış yok)")
    if not res.events:
        print("  GERÇEKÇİ OLSA : olay yok (henüz tetik yok)")
        return
    print(f"  GERÇEKÇİ OLSA : {len(res.events)} olay")
    for e in res.events:
        tier = f"kademe-{e.tier}" if e.tier else "final    "
        fill = "✗ DOLMAZDI→çözüme tutuldu" if e.kind == "settlement" else "✓ dolardı"
        print(f"     {_hhmm(e.time_iso)}  {e.kind:<12} {tier}  %{e.sell_pct*100:>3.0f} @{e.price:.3f}"
              f"  = ${e.realized:+.2f}  [{fill}]")
    tag = "kapandı" if res.closed else f"{res.remaining_shares:.0f} hisse açık kaldı"
    print(f"     └─ gerçekçi realized: ${res.realized_total:+.2f}  ({tag})")


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    cfg = load_config()
    kw = _evaluate_kwargs(cfg)
    open_pos = _load_positions(_POSITIONS_PATH)
    backup_pos = _load_positions(_CLOSED_BACKUP_PATH)
    actual = _load_actual_realized(_TRADE_EVENTS_PATH)
    closed_ids = [cid for cid in backup_pos if cid not in open_pos]

    items = (
        [(cid, open_pos[cid], "AÇIK") for cid in open_pos]
        + [(cid, backup_pos[cid], "KAPANDI") for cid in closed_ids]
    )
    cutoff = _real_datetime.fromisoformat(_CUTOFF_ISO)
    exit_times = _load_exit_times(_TRADE_EVENTS_PATH)
    # Scope: açık pozisyonlar (şu an aktif) + çıkışı 14:00 sonrası olan kapananlar.
    items = [
        it for it in items
        if it[2] == "AÇIK" or (exit_times.get(it[0]) is not None and exit_times[it[0]] >= cutoff)
    ]
    n_open = sum(1 for _, _, s in items if s == "AÇIK")
    n_closed = sum(1 for _, _, s in items if s == "KAPANDI")
    print("=" * 70)
    print(f"BUGÜN 14:00 (UTC+3) SONRASI — {n_open} açık + {n_closed} kapanan = {len(items)} pozisyon")
    print("Salt-okunur. Hiçbir bot dosyasına yazılmadı. Sonuç = Polymarket'in gerçek")
    print("fiyat geçmişi. [✓ dolardı] = o fiyatta alıcı vardı; [✗ dolmazdı] = boş defter.")
    print("=" * 70)

    closed_actual = closed_realistic = open_actual = open_realistic = 0.0
    skipped: list[str] = []
    phantoms: list[tuple] = []
    for cid, pos, state in items:
        entry_epoch = pos.entry_timestamp.timestamp()
        series = [(t, p) for t, p in fetch_price_history(pos.token_id) if t >= entry_epoch]
        if not series:
            skipped.append((pos.slug or cid)[:40])
            continue
        last_price = series[-1][1]
        res = replay_position(pos, series, **kw)
        act = actual.get(cid, 0.0)
        _print_position(pos, res, state, act, last_price)
        # Phantom: bot pozitif kâr yazmış ama token kaybetmiş (≤0.1'de kapanmış)
        if state == "KAPANDI" and act > 0.5 and last_price <= 0.1:
            phantoms.append((pos.slug[:42], act, pos.shares * 0.0 - pos.size_usdc))
        if state == "KAPANDI":
            closed_actual += act
            closed_realistic += res.realized_total
        else:
            open_actual += act
            open_realistic += res.realized_total

    print("\n" + "=" * 70)
    print("TOPLAM")
    print(f"  Kapanan : gerçek ${closed_actual:+.2f}  vs  gerçekçi ${closed_realistic:+.2f}")
    print(f"  Açık    : gerçek (kademe) ${open_actual:+.2f}  vs  gerçekçi şimdiye dek ${open_realistic:+.2f}")
    if phantoms:
        print("  ⚠️ HATALI KAYIT (bot kazanç yazmış ama token KAYBETMİŞ):")
        for slug, booked, true_r in phantoms:
            print(f"     {slug}: bot ${booked:+.2f} → gerçek ${true_r:+.2f}  (hayali ${booked - true_r:+.2f})")
    if skipped:
        print(f"  Fiyat geçmişi yok / atlandı ({len(skipped)}): {', '.join(skipped)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
