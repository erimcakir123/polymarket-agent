"""SPEC-SIM2 koşucu: counterfactual değerlendirme + fiyat-geçmişi replay + rapor.

Karar mantığı scripts/sim_surface_counterfactual.py'de (test edilen kısım);
bu dosya I/O orkestrasyonu + konsol raporu. Salt-okunur; Odds API KULLANILMAZ.

Çalıştırma:  python scripts/sim_surface_counterfactual_run.py
"""
from __future__ import annotations

import logging
from datetime import datetime

from src.config.settings import load_config
from src.infrastructure.data.calibration_store import load_calibration
from src.infrastructure.data.tennis_surface_ratings_store import (
    _SURFACE_PHI_FALLBACK_THRESHOLD,
)
from src.models.position import Position
from src.strategy.enrichment.tennis_dispatch import _extract_location
from src.strategy.enrichment.tennis_dispatch_surface import make_surface_aware_dispatch

from scripts.sim_realistic_replay import (
    ReplayResult,
    _evaluate_kwargs,
    _load_actual_realized,
    fetch_price_history,
    replay_position,
)
from scripts.sim_surface_counterfactual import (
    _ARCHIVE_EVENTS,
    _ARCHIVE_EXECS,
    _CACHE_DIR,
    _CALIBRATION_PATH,
    _CUTOFF_DATE,
    _EXEC_WINDOW_SEC,
    _PROB_CLAMP,
    _build_resolver,
    _load_sackmann_matches,
    build_cutoff_snapshots,
    evaluate_entries,
    invert_series,
    link_token_ids,
    load_tennis_entries,
    synth_event_links,
)

logger = logging.getLogger(__name__)


def _backfill_event_tournaments(
    entries: list[dict], idx_to_event: dict[int, str], event_tournaments: dict[str, str],
) -> None:
    """Eşlenemeyen event'lere turnuva: Polymarket Gamma event başlığından.

    Canlı bot turnuvayı TARANAN (girilmemiş dahil) moneyline marketten alır; arşivde
    sadece girilenler var. Gamma başlığı aynı bilgiyi verir (Odds API DEĞİL, ücretsiz).
    """
    from src.infrastructure.apis.gamma_client import GammaClient
    gc = GammaClient()
    done: set[str] = set()
    for idx, ev_id in idx_to_event.items():
        if ev_id in event_tournaments or ev_id in done:
            continue
        done.add(ev_id)
        m = gc.fetch_closed_market_by_condition(entries[idx].get("condition_id", ""))
        events = (m or {}).get("events") or []
        title = (events[0] or {}).get("title") or "" if events else ""
        loc = _extract_location(title)
        if loc:
            event_tournaments[ev_id] = loc
        else:
            logger.warning("Gamma event başlığından turnuva çıkarılamadı: %s", title[:60])


def _replay_one(row: dict, token_id: str | None, kw: dict) -> tuple[ReplayResult | None, str]:
    """Girilen trade'i gerçek fiyat serisiyle oynat. (None, sebep) = oynatılamadı."""
    if token_id is None:
        return None, "token eşleşmedi"
    e, d = row["entry"], row["decision"]
    entry_epoch = datetime.fromisoformat(e["entry_timestamp"]).timestamp()
    series = [(t, p) for t, p in fetch_price_history(token_id) if t >= entry_epoch]
    if not series:
        return None, "fiyat geçmişi yok"
    if d.direction != e.get("direction"):
        series = invert_series(series)  # karşı taraf: 1−p yaklaşımı
    lo, hi = _PROB_CLAMP
    pos = Position(
        condition_id=e.get("condition_id", ""), token_id=token_id,
        direction=d.direction, entry_price=d.eff_entry, size_usdc=d.size_usdc,
        shares=d.size_usdc / d.eff_entry, slug=e.get("slug", ""),
        entry_timestamp=datetime.fromisoformat(e["entry_timestamp"]),
        confidence="A", anchor_probability=min(hi, max(lo, row["new_prob"])),
        current_price=d.eff_entry, sport_tag="tennis",
        question=e.get("question", ""),
    )
    return replay_position(pos, series, **kw), ""


def _print_report(rows: list[dict], replays: dict[int, tuple], actual: dict[str, float]) -> None:
    print("=" * 92)
    print("ÖNCEKİ SESSION (2026-06-06→09) — BUGÜNKÜ KURALLARLA COUNTERFACTUAL")
    print("Salt-okunur sim. Gerçek fiyat geçmişi + botun bugünkü karar/çıkış beyni.")
    print("=" * 92)
    seen_cids: set[str] = set()
    actual_total = sim_total = 0.0
    n = {"SAME": 0, "FLIP": 0, "SKIP": 0}
    skip_reasons: dict[str, int] = {}
    unplayed: list[str] = []
    for idx, row in enumerate(rows):
        e, d = row["entry"], row["decision"]
        cid = e.get("condition_id", "")
        first_cid = cid not in seen_cids
        seen_cids.add(cid)
        act = actual.get(cid, 0.0) if first_cid else None
        if act is not None:
            actual_total += act
        n[d.action] += 1
        old_p = e.get("anchor_probability")
        hhmm = (e.get("entry_timestamp") or "")[5:16].replace("T", " ")
        q = (e.get("question") or "")[:46]
        old_s = f"{old_p:.2f}" if old_p is not None else "  ? "
        new_s = f"{row['new_prob']:.2f}" if row["new_prob"] is not None else "  — "
        act_s = f"{act:+7.2f}$" if act is not None else "   (üst)"
        if d.action == "SKIP":
            skip_reasons[d.reason] = skip_reasons.get(d.reason, 0) + 1
            print(f"{hhmm}  {q:<46} eski {old_s} yeni {new_s} zemin {row['surface']:<12}"
                  f" GİRMEZ[{d.reason}]  gerçek {act_s}  sim   0.00$")
            continue
        res, why = replays.get(idx, (None, "?"))
        if res is None:
            unplayed.append(f"{q} ({why})")
            print(f"{hhmm}  {q:<46} eski {old_s} yeni {new_s} zemin {row['surface']:<12}"
                  f" {d.action}/{d.direction}  gerçek {act_s}  sim OYNATILAMADI")
            continue
        sim_total += res.realized_total
        tag = "kapandı" if res.closed else f"{res.remaining_shares:.0f} hisse açık"
        print(f"{hhmm}  {q:<46} eski {old_s} yeni {new_s} zemin {row['surface']:<12}"
              f" {d.action}/{d.direction} @{d.eff_entry:.2f} ${d.size_usdc:.0f}"
              f"  gerçek {act_s}  sim {res.realized_total:+7.2f}$ ({tag})")
    print("-" * 92)
    print(f"KARAR: aynı yön {n['SAME']}  |  ters yön {n['FLIP']}  |  girmez {n['SKIP']}"
          f"  (sebepler: {skip_reasons})")
    print(f"TOPLAM: gerçek (tenis) ${actual_total:+.2f}   vs   counterfactual ${sim_total:+.2f}"
          f"   →  fark ${sim_total - actual_total:+.2f}")
    if unplayed:
        print(f"Oynatılamayan girişler ({len(unplayed)}): " + "; ".join(unplayed))
    print("Notlar: ters-yön fiyatları 1−p yaklaşımı; bahisçi-kaynaklı 8 trade'de tahmin")
    print("değişmez; tenis-dışı 6 trade kapsam dışı; reytingler 2026-06-06 öncesi veriyle")
    print("(lookahead yok); 0.05 altı fiyatta satış yok (alıcı-yok koruması).")
    print("=" * 92)


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    cfg = load_config()
    entries = load_tennis_entries(_ARCHIVE_EVENTS)
    print(f"Arşivden {len(entries)} tenis entry yüklendi; cutoff reytingler kuruluyor "
          f"(<{_CUTOFF_DATE}, birkaç dk sürebilir)...")
    matches = _load_sackmann_matches(_CACHE_DIR)
    _, by_surface = build_cutoff_snapshots(
        matches, _CUTOFF_DATE, _SURFACE_PHI_FALLBACK_THRESHOLD,
    )
    print(f"Reytingler hazır ({len(matches)} maçtan). Değerlendirme başlıyor...")
    idx_to_event, event_tournaments = synth_event_links(entries)
    _backfill_event_tournaments(entries, idx_to_event, event_tournaments)
    resolver = _build_resolver(cfg, event_tournaments)
    enrich_model = make_surface_aware_dispatch(by_surface)
    calib = load_calibration(_CALIBRATION_PATH)
    rows = evaluate_entries(entries, cfg, resolver, enrich_model, calib)

    links = link_token_ids(entries, _ARCHIVE_EXECS, _EXEC_WINDOW_SEC)
    kw = _evaluate_kwargs(cfg)
    replays: dict[int, tuple] = {}
    for idx, row in enumerate(rows):
        if row["decision"].action != "SKIP":
            replays[idx] = _replay_one(row, links.get(idx), kw)
    actual = _load_actual_realized(_ARCHIVE_EVENTS)
    _print_report(rows, replays, actual)
    if resolver.unresolved:
        print(f"Zemin çözülemeyenler: {sorted(resolver.unresolved)}")


if __name__ == "__main__":
    main()
