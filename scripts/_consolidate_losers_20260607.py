"""Tek seferlik: 3 dry-run kaybedeninin 0¢ sahte parçalı satışlarını TEK tam-zarara indir.

Gerekçe: 2026-06-07 dry-run penceresinde bu 3 tenis maçı 0¢'te "parçalı satıldı"
(-4.49 / -5.24 / final -5.24 = 3 sahte parça). Gerçek paper'da 0¢'te alıcı yok →
satış REDDEDİLİR, pozisyon tek seferde tam kaybeder. Bu yüzden 3 parça → TEK final
(net = parçaların toplamı, ≈ -14.97). Kazananlara (Watson/Aguilar) DOKUNULMAZ.

Net etki: her kaybedenin TOPLAM zararı değişmez (parça toplamı = yeni final) →
realized_pnl AYNI kalır, positions.json'a dokunulmaz.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
TRADE_EVENTS = ROOT / "logs" / "audit" / "trade_events.jsonl"

LOSERS = {
    "0xddb3fcf10368818bca4cf4c188da32d12f0a38f813999c4cadadff632fc78788": "shimabu",
    "0x8e855976c8c993fbee79844ee26bc7ab58973d38bfc48acb8f87eaac10e704ab": "huesler",
    "0xbcdd897b7e0bca5a744a59a4ba98d99e557fc5eca886e9eb282b044af8cbff1c": "vandewi",
}


def main(apply: bool) -> None:
    lines = TRADE_EVENTS.read_text(encoding="utf-8").splitlines()

    # 1. pass: her kaybedenin parça toplamı + eski final
    partial_sum: dict[str, float] = {}
    old_final: dict[str, float] = {}
    for l in lines:
        r = json.loads(l)
        cid = r.get("condition_id")
        if cid in LOSERS:
            if r.get("kind") == "partial":
                partial_sum[cid] = partial_sum.get(cid, 0.0) + (r.get("realized_pnl_usdc") or 0.0)
            elif r.get("kind") == "final":
                old_final[cid] = r.get("exit_pnl_usdc") or 0.0
    new_final = {cid: round(partial_sum.get(cid, 0.0) + old_final.get(cid, 0.0), 2) for cid in LOSERS}

    # 2. pass: parçaları SİL, final'i yeni değere ayarla
    out: list[str] = []
    dropped = 0
    fixed = 0
    for l in lines:
        r = json.loads(l)
        cid = r.get("condition_id")
        if cid in LOSERS and r.get("kind") == "partial":
            dropped += 1
            continue
        if cid in LOSERS and r.get("kind") == "final":
            r["exit_pnl_usdc"] = new_final[cid]
            fixed += 1
            out.append(json.dumps(r, ensure_ascii=False))
            continue
        out.append(l)

    print("=== KAYBEDEN BİRLEŞTİRME ===")
    for cid, nm in LOSERS.items():
        print(f"  {nm}: parçalar {round(partial_sum.get(cid,0),2)} + eski final {old_final.get(cid)} "
              f"-> TEK final {new_final[cid]}")
    print(f"  Silinen sahte 0¢ parça: {dropped} (beklenen 6)")
    print(f"  Düzeltilen final: {fixed} (beklenen 3)")
    print(f"  Satır: {len(lines)} -> {len(out)}")
    assert dropped == 6, f"6 parça silinmeli, {dropped} oldu"
    assert fixed == 3, f"3 final düzeltilmeli, {fixed} oldu"

    if not apply:
        print("\n[DRY-RUN] dosya YAZILMADI.")
        return
    TRADE_EVENTS.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n[APPLY] trade_events.jsonl YAZILDI.")


if __name__ == "__main__":
    import sys
    main(apply="--apply" in sys.argv)
