"""Sharp vs Polymarket analiz scripti.

logs/sharp_vs_poly/*.jsonl dosyalarini okur, her benzersiz mac icin:
- Sharp ve Polymarket fiyat zaman serisini cikartir
- Maks hareket (volatilite) olcer
- Kim once hareket etmis (lead/lag)
- Hareketlerin buyuklugu
- Terminal'e tablo + markdown rapor basar
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs" / "sharp_vs_poly"
REPORT_FILE = LOG_DIR / "_report.md"


# Hareket esigi: bu kadar yuzde puan degisim "anlamli" kabul edilir
MOVE_THRESHOLD_PCT = 0.03  # %3 absolute probability move


def load_snapshots() -> list[dict]:
    rows: list[dict] = []
    for f in sorted(LOG_DIR.glob("*.jsonl")):
        if f.name.startswith("_"):
            continue
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def group_by_match(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        cid = r.get("cid") or r.get("slug", "?")
        groups[cid].append(r)
    # Sort each by timestamp
    for cid in groups:
        groups[cid].sort(key=lambda x: x.get("ts", ""))
    return groups


def analyze_match(rows: list[dict]) -> dict:
    """Tek mac icin metrikler."""
    sharp_series = [r["sharp_prob_home"] for r in rows if "sharp_prob_home" in r]
    pm_series = [r["pm_yes_price"] for r in rows if "pm_yes_price" in r]

    if len(sharp_series) < 2 or len(pm_series) < 2:
        return {}

    sharp_range = max(sharp_series) - min(sharp_series)
    pm_range = max(pm_series) - min(pm_series)

    # Max hareket — hangi iki ardisik snapshot arasi en buyuk mutlak degisim
    sharp_moves = [abs(sharp_series[i] - sharp_series[i - 1]) for i in range(1, len(sharp_series))]
    pm_moves = [abs(pm_series[i] - pm_series[i - 1]) for i in range(1, len(pm_series))]

    sharp_max_move = max(sharp_moves) if sharp_moves else 0
    pm_max_move = max(pm_moves) if pm_moves else 0

    # Direction correlation — ayni yone mi gidiyor?
    concordance = 0
    for i in range(1, len(sharp_series)):
        s_dir = sharp_series[i] - sharp_series[i - 1]
        p_dir = pm_series[i] - pm_series[i - 1]
        if (s_dir > 0 and p_dir > 0) or (s_dir < 0 and p_dir < 0):
            concordance += 1
        elif s_dir == 0 or p_dir == 0:
            pass  # skip neutral
    concordance_ratio = (
        concordance / (len(sharp_series) - 1) if len(sharp_series) > 1 else 0.0
    )

    # Lead/lag — ilk anlamli hareket kim yapmis?
    # Iki seride >=MOVE_THRESHOLD_PCT hareket oldugu ilk index'leri bul
    sharp_first_move_idx = next(
        (i for i in range(1, len(sharp_series))
         if abs(sharp_series[i] - sharp_series[0]) >= MOVE_THRESHOLD_PCT),
        None,
    )
    pm_first_move_idx = next(
        (i for i in range(1, len(pm_series))
         if abs(pm_series[i] - pm_series[0]) >= MOVE_THRESHOLD_PCT),
        None,
    )
    lead = "none"
    if sharp_first_move_idx is not None and pm_first_move_idx is not None:
        if sharp_first_move_idx < pm_first_move_idx:
            lead = "sharp"
        elif pm_first_move_idx < sharp_first_move_idx:
            lead = "polymarket"
        else:
            lead = "sync"
    elif sharp_first_move_idx is not None:
        lead = "sharp_only"
    elif pm_first_move_idx is not None:
        lead = "pm_only"

    first_row = rows[0]
    last_row = rows[-1]

    return {
        "question": first_row.get("question", "")[:60],
        "sport_key": first_row.get("sport_key", ""),
        "snapshots": len(rows),
        "sharp_first": sharp_series[0],
        "sharp_last": sharp_series[-1],
        "sharp_range": sharp_range,
        "sharp_max_move": sharp_max_move,
        "pm_first": pm_series[0],
        "pm_last": pm_series[-1],
        "pm_range": pm_range,
        "pm_max_move": pm_max_move,
        "concordance": concordance_ratio,
        "lead": lead,
        "sharp_first_move_idx": sharp_first_move_idx,
        "pm_first_move_idx": pm_first_move_idx,
    }


def print_table(analyses: dict[str, dict]) -> None:
    print("\n" + "=" * 120)
    print(
        f"{'Mac':<45}{'Sport':<20}{'Snap':<6}{'SharpR':<8}{'PolyR':<8}"
        f"{'SMax':<7}{'PMax':<7}{'Concord':<9}{'Lead':<10}"
    )
    print("-" * 120)

    for cid, a in sorted(analyses.items(), key=lambda x: -x[1].get("pm_range", 0)):
        if not a:
            continue
        print(
            f"{a['question']:<45}{a['sport_key']:<20}"
            f"{a['snapshots']:<6}"
            f"{a['sharp_range']:.2%}  "
            f"{a['pm_range']:.2%}  "
            f"{a['sharp_max_move']:.2%}  "
            f"{a['pm_max_move']:.2%}  "
            f"{a['concordance']:<9.2f}"
            f"{a['lead']:<10}"
        )


def print_summary(analyses: dict[str, dict]) -> None:
    valid = [a for a in analyses.values() if a]
    if not valid:
        print("\n[!] Analiz edilecek yeterli veri yok")
        return

    print("\n" + "=" * 70)
    print("OZET")
    print("=" * 70)

    sharp_ranges = [a["sharp_range"] for a in valid]
    pm_ranges = [a["pm_range"] for a in valid]
    sharp_max_moves = [a["sharp_max_move"] for a in valid]
    pm_max_moves = [a["pm_max_move"] for a in valid]
    concordances = [a["concordance"] for a in valid]

    leads = defaultdict(int)
    for a in valid:
        leads[a["lead"]] += 1

    print(f"Toplam mac: {len(valid)}")
    print(f"\n[OYNAKLIK] — daha yuksek = daha dalgali")
    print(f"  Sharp  aralik (max-min)  mean {mean(sharp_ranges):.2%}  median {median(sharp_ranges):.2%}")
    print(f"  Poly   aralik (max-min)  mean {mean(pm_ranges):.2%}    median {median(pm_ranges):.2%}")
    print(f"  Sharp  tek adim max move mean {mean(sharp_max_moves):.2%}")
    print(f"  Poly   tek adim max move mean {mean(pm_max_moves):.2%}")

    ratio = mean(pm_ranges) / mean(sharp_ranges) if mean(sharp_ranges) > 0 else 0
    print(f"\n  --> Polymarket sharplara gore {ratio:.2f}x oynak")
    if ratio > 1.2:
        print(f"      YORUM: Polymarket daha dalgali (noise daha fazla).")
    elif ratio < 0.8:
        print(f"      YORUM: Sharp'lar daha dalgali (Polymarket daha stabil).")
    else:
        print(f"      YORUM: Ikisi de benzer oynaklikta.")

    print(f"\n[YON TUTARLILIGI] — ikisi ayni yonde mi hareket ediyor")
    print(f"  Ortalama concordance: {mean(concordances):.2%}")
    if mean(concordances) > 0.7:
        print(f"      --> Sharp ve Poly cogunlukla ayni yonde hareket ediyor.")
    elif mean(concordances) > 0.5:
        print(f"      --> Orta uyum, ciddi gurultu var.")
    else:
        print(f"      --> Dusuk uyum, ayri hareket ediyorlar.")

    print(f"\n[LEAD ANALIZI] — anlamli hareket ({MOVE_THRESHOLD_PCT:.0%}+) kim ilk yapmis")
    total_with_lead = sum(v for k, v in leads.items() if k in ("sharp", "polymarket", "sync"))
    for k in ("sharp", "polymarket", "sync", "sharp_only", "pm_only", "none"):
        cnt = leads.get(k, 0)
        if cnt == 0:
            continue
        pct = (cnt / len(valid)) * 100
        print(f"  {k:<12}: {cnt:>3}  ({pct:.1f}%)")

    if total_with_lead > 0:
        sharp_leads = leads.get("sharp", 0)
        pm_leads = leads.get("polymarket", 0)
        lead_ratio = sharp_leads / max(1, sharp_leads + pm_leads)
        print(f"\n  Sharp-Poly karsilastirmasi: sharp {sharp_leads}, poly {pm_leads}")
        if lead_ratio > 0.60:
            print(f"  --> SHARP once hareket ediyor (%{lead_ratio*100:.0f})")
        elif lead_ratio < 0.40:
            print(f"  --> POLYMARKET once hareket ediyor (%{(1-lead_ratio)*100:.0f})")
        else:
            print(f"  --> Ikisi dengeli (%{lead_ratio*100:.0f} - %{(1-lead_ratio)*100:.0f})")

    print("\n" + "=" * 70)
    print("SONUC")
    print("=" * 70)
    if mean(sharp_ranges) > mean(pm_ranges) * 0.7 and leads.get("sharp", 0) > leads.get("polymarket", 0) * 1.5:
        print("  --> Live odds exit ekleme DEGERLI olabilir.")
        print("      Sharp ~smooth + once hareket ediyor, exit sinyali verilebilir.")
    elif leads.get("sharp", 0) < leads.get("polymarket", 0):
        print("  --> Live odds exit ekleme BOSA GIDER.")
        print("      Polymarket ya kendi basina once hareket ediyor ya eslesik.")
    else:
        print("  --> KARISIK sonuc. Daha fazla veri toplamak veya sport-specific analiz gerekli.")


def write_markdown_report(analyses: dict[str, dict]) -> None:
    valid = [a for a in analyses.values() if a]
    if not valid:
        return
    lines = ["# Sharp vs Polymarket Analysis Report", ""]
    lines.append(f"Toplam mac: {len(valid)}")
    lines.append("")
    lines.append("| Mac | Sport | Snap | Sharp Range | Poly Range | Lead |")
    lines.append("|---|---|---:|---:|---:|---|")
    for a in sorted(valid, key=lambda x: -x.get("pm_range", 0)):
        lines.append(
            f"| {a['question']} | {a['sport_key']} | {a['snapshots']} | "
            f"{a['sharp_range']:.2%} | {a['pm_range']:.2%} | {a['lead']} |"
        )

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nMarkdown rapor: {REPORT_FILE}")


def main() -> None:
    rows = load_snapshots()
    if not rows:
        print(f"[!] {LOG_DIR} altinda veri bulunamadi")
        return
    print(f"[OK] {len(rows)} snapshot yuklendi")

    groups = group_by_match(rows)
    print(f"[OK] {len(groups)} benzersiz mac")

    analyses: dict[str, dict] = {}
    for cid, match_rows in groups.items():
        analyses[cid] = analyze_match(match_rows)

    print_table(analyses)
    print_summary(analyses)
    write_markdown_report(analyses)


if __name__ == "__main__":
    main()
