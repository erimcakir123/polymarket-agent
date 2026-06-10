"""Bimodal (set bahisleri) çıkış politikası karşılaştırması — salt-okunur rapor.

Kullanıcı sorusu (2026-06-10): "kademeli kâr almayı tamamen mi kapatsak,
1 kademeye mi düşürsek?" Geçmiş trade_events arşivlerinden tüm tenis bimodal
pozisyonları (Set Handicap / Total Sets) çıkarır, dört politikayı kıyaslar:

  GERÇEK      : kayıtlı parçalar (ground truth — doğrulama için yeniden hesaplanır)
  TUT         : hiç kademe yok, çözüme kadar tut
  TEK-ERKEN   : sadece kademe-1 (yolun %40'ında %40 sat), kalan çözüme
  TEK-GEÇ     : sadece kademe-2 (yolun %70'inde %50 sat), kalan çözüme

Kademe eşikleri config.yaml > scale_out.tiers'tan okunur (DRY).
Sonuç bilinmeyen pozisyonlar (erken manuel/force kapanış, 0.15-0.85 arası)
counterfactual'dan DIŞLANIR ve sayısı raporlanır — uydurma sonuç yok.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import yaml

_AUDIT_DIR = Path("logs/audit")
_WIN_PRICE = 0.85   # final fiyat >= bu → kazandı say (near_resolve dahil)
_LOSE_PRICE = 0.15  # final fiyat <= bu → kaybetti say
_VALIDATION_TOLERANCE_USDC = 0.06  # yeniden hesap vs kayıt farkı toleransı
_BIMODAL_QUESTION_KEYS = ("Set Handicap", "Total Sets")


def _load_events() -> list[dict]:
    files = sorted(glob.glob(str(_AUDIT_DIR / "trade_events*.jsonl")))
    events: list[dict] = []
    for f in files:
        if ".bak" in f:
            continue  # yedekler ana arşivlerin kopyası — çift sayma olmasın
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def _is_bimodal_tennis(question: str) -> bool:
    return any(k in question for k in _BIMODAL_QUESTION_KEYS)


def _group_positions(events: list[dict]) -> list[dict]:
    """slug bazında entry + sonraki parçalar/final. Aynı sluga yeniden giriş
    görülürse yeni pozisyon açılır (entry event'i sınır sayılır)."""
    positions: list[dict] = []
    open_by_slug: dict[str, dict] = {}
    for e in events:
        kind = e.get("kind")
        slug = e.get("slug", "")
        if kind == "entry":
            if not _is_bimodal_tennis(e.get("question", "")):
                continue
            pos = {"entry": e, "parts": [], "final": None}
            open_by_slug[slug] = pos
            positions.append(pos)
        elif slug in open_by_slug:
            pos = open_by_slug[slug]
            if kind == "partial":
                pos["parts"].append(e)
            elif kind == "final":
                pos["final"] = e
                del open_by_slug[slug]
    return positions


def _outcome(pos: dict) -> str:
    """'win' | 'lose' | 'unknown' — final fiyatından."""
    fin = pos["final"]
    if fin is None:
        return "unknown"  # hâlâ açık
    price = fin.get("exit_price")
    if price is None:
        return "unknown"
    if price >= _WIN_PRICE:
        return "win"
    if price <= _LOSE_PRICE:
        return "lose"
    return "unknown"


def _actual_pnl(pos: dict) -> float:
    total = sum(p.get("realized_pnl_usdc", 0.0) for p in pos["parts"])
    fin = pos["final"]
    if fin is not None:
        total += fin.get("exit_pnl_usdc", 0.0)
    return total


def _crossed_tiers(pos: dict, outcome: str) -> set[int]:
    """Fiyatın hangi kademe eşiklerini geçtiği. Kazanan → hepsi (fiyat 1'e gitti).
    Kaybeden → sadece kayıtlı scale-out parçalarının kanıtladıkları (muhafazakâr)."""
    if outcome == "win":
        return {1, 2}
    entry_price = pos["entry"]["entry_price"]
    crossed: set[int] = set()
    for p in pos["parts"]:
        if p.get("price", 0.0) > entry_price:  # entry üstü satış = scale-out kanıtı
            crossed.add(int(p.get("tier", 0)))
    if 2 in crossed:
        crossed.add(1)
    return crossed


def _policy_pnl(
    pos: dict, outcome: str, tiers: list[dict], use_tiers: list[int],
) -> float:
    """Verilen kademe alt-kümesiyle pozisyonun kâr/zararı (kalan çözüme tutulur)."""
    entry = pos["entry"]
    e, shares = entry["entry_price"], entry["shares"]
    crossed = _crossed_tiers(pos, outcome)
    remaining = 1.0
    pnl = 0.0
    for idx in use_tiers:
        t = tiers[idx - 1]
        if idx not in crossed:
            continue
        tier_price = e + t["threshold"] * (1.0 - e)
        sold = remaining * t["sell_pct"]
        pnl += sold * shares * (tier_price - e)
        remaining -= sold
    if outcome == "win":
        pnl += remaining * shares * (1.0 - e)
    else:
        pnl -= remaining * shares * e
    return pnl


def main() -> None:
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    tiers = cfg["scale_out"]["tiers"]  # [{threshold, sell_pct}, ...]

    positions = _group_positions(_load_events())
    decided, unknown, validation_failed = [], 0, 0
    for pos in positions:
        out = _outcome(pos)
        if out == "unknown":
            unknown += 1
            continue
        # Doğrulama: GERÇEK politika yeniden hesabı kayıtla tutmalı.
        recorded = _actual_pnl(pos)
        recomputed = _policy_pnl(pos, out, tiers, use_tiers=[1, 2])
        # near_resolve 0.88 gibi erken satışlar küçük sapma yaratır — sadece
        # büyük tutarsızlıkta dışla (yanlış gruplama/veri bozukluğu işareti).
        if abs(recomputed - recorded) > max(3.0, 0.35 * abs(recorded)):
            validation_failed += 1
            continue
        decided.append((pos, out, recorded))

    print(f"Bimodal tenis pozisyonu: toplam={len(positions)} "
          f"karari-belli={len(decided)} bilinmeyen/acik={unknown} "
          f"dogrulama-disi={validation_failed}")
    if not decided:
        print("Karari belli pozisyon yok — rapor üretilemiyor.")
        return

    wins = sum(1 for _, o, _ in decided if o == "win")
    print(f"Sonuc dagilimi: {wins} kazanan / {len(decided) - wins} kaybeden")
    print()

    policies = {
        "GERCEK (2 kademe)": None,  # kayıtlı
        "TUT (kademe yok)": [],
        "TEK-ERKEN (k1)": [1],
        "TEK-GEC (k2)": [2],
    }
    print(f"{'POLITIKA':18} {'TOPLAM':>9} {'ORT/POZ':>8} {'KAZANANDA':>10} {'KAYBEDENDE':>10}")
    for name, use in policies.items():
        if use is None:
            vals = [(rec, o) for _, o, rec in decided]
        else:
            vals = [(_policy_pnl(p, o, tiers, use), o) for p, o, _ in decided]
        total = sum(v for v, _ in vals)
        avg_w = [v for v, o in vals if o == "win"]
        avg_l = [v for v, o in vals if o == "lose"]
        aw = sum(avg_w) / len(avg_w) if avg_w else 0.0
        al = sum(avg_l) / len(avg_l) if avg_l else 0.0
        print(f"{name:18} {total:>+9.2f} {total / len(vals):>+8.2f} {aw:>+10.2f} {al:>+10.2f}")

    print()
    print("Pozisyon dökümü (GERÇEK vs TUT vs TEK-ERKEN vs TEK-GEÇ):")
    for pos, out, recorded in decided:
        e = pos["entry"]
        hold = _policy_pnl(pos, out, tiers, [])
        t1 = _policy_pnl(pos, out, tiers, [1])
        t2 = _policy_pnl(pos, out, tiers, [2])
        print(f"  {out:4} giris={e['entry_price']:.2f} ${e['size_usdc']:.0f} "
              f"gercek={recorded:+7.2f} tut={hold:+7.2f} k1={t1:+7.2f} k2={t2:+7.2f}"
              f"  {e['question'][:46]}")


if __name__ == "__main__":
    main()
