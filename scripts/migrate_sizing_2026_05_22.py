"""Retroactive sizing migration — PLAN-SIZING-001 (2026-05-22).

Tennis lab state'ini yeni bimodal-aware sizing kurallarına göre yeniden hesaplar.
Pre-migration: B-tier /3 küçültme + set_totals $15 cap (set_handicap cap yok).
Post-migration: tier'ın kendi bet_pct'i (A=%5, B=%3.5) + bimodal'larda (set_totals
+ set_handicap) $15 cap.

Iki mod:
  --dry-run : raporu yaz, hiçbir dosyaya dokunma
  --apply   : .bak yedeği oluştur, dosyaları güncelle

Etkilenen dosyalar:
  tennis-lab/data/positions.json
  tennis-lab/logs/audit/trade_history.jsonl
  tennis-lab/logs/session/trade_history.jsonl  (varsa)
  tennis-lab/logs/audit/equity_history.jsonl   (regenerate)
  tennis-lab/logs/session/equity_history.jsonl (regenerate)

Migration tek-yönlüdür; .bak dosyaları manuel recovery için tutulur.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows cp1252 fix — script Turkce karakter icerebilir, stdout UTF-8.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Sizing kuralları ──────────────────────────────────────────────────────────

# Yeni rules (PLAN-SIZING-001):
NEW_BET_PCT = {"A": 0.05, "B": 0.035}
NEW_MAX_PCT = 0.05  # bankroll × max_bet_pct cap
BIMODAL_TYPES = ("tennis_set_totals", "tennis_set_handicap")
BIMODAL_CAP = 15.0
NON_BIMODAL_CAP = 50.0

# Eski rules (migration öncesi):
OLD_BET_PCT_HARDCODED_A = 0.05  # tennis_agent.py hardcoded "A" idi
OLD_SET_TOTALS_CAP = 15.0       # eski set_totals_max_usdc
OLD_NON_BIMODAL_CAP = 50.0      # eski max_single_bet_usdc
# Eski set_handicap: cap yoktu (max_single_bet_usdc=50 kullanırdı)


def detect_market_type(slug: str) -> str:
    """Slug'tan market type tespit — positions.json'da sports_market_type
    'moneyline' olarak yanlış kaydedilmiş, slug güvenilir tek kaynak."""
    s = slug.lower()
    if "set-totals" in s:
        return "tennis_set_totals"
    if "set-handicap" in s:
        return "tennis_set_handicap"
    if "first-set-winner" in s:
        return "tennis_first_set_winner"
    if "match-total" in s or "match-o-u" in s:
        return "tennis_match_o_u"
    return "tennis_moneyline"


def old_size(confidence: str, market_type: str, bankroll: float) -> float:
    """Migration öncesi sizing rule'unu uygula."""
    cap = OLD_SET_TOTALS_CAP if market_type == "tennis_set_totals" else OLD_NON_BIMODAL_CAP
    size = min(bankroll * OLD_BET_PCT_HARDCODED_A, cap, bankroll * NEW_MAX_PCT)
    if confidence == "B":
        size = round(size / 3.0, 2)
    return round(size, 2)


def new_size(confidence: str, market_type: str, bankroll: float) -> float:
    """Yeni sizing rule'unu uygula."""
    cap = BIMODAL_CAP if market_type in BIMODAL_TYPES else NON_BIMODAL_CAP
    bet_pct = NEW_BET_PCT.get(confidence, 0.0)
    size = min(bankroll * bet_pct, cap, bankroll * NEW_MAX_PCT)
    return round(size, 2)


def infer_bankroll_at_entry(confidence: str, market_type: str, recorded_size: float) -> float:
    """Eski size'tan giriş anındaki bankroll'u geri çıkar.

    Eski formül: size = min(bankroll × 0.05, cap_old) / (3 if B else 1)
    Cap aktif değilse bankroll = raw_old / 0.05 olarak ters çevrilir.
    Cap aktifse $1000 varsayılır (paper trading default).
    """
    raw_old = recorded_size * (3.0 if confidence == "B" else 1.0)
    cap_old = OLD_SET_TOTALS_CAP if market_type == "tennis_set_totals" else OLD_NON_BIMODAL_CAP
    if raw_old < cap_old:
        return raw_old / OLD_BET_PCT_HARDCODED_A
    return 1000.0


def compute_new_size_for_record(confidence: str, market_type: str, old_recorded_size: float) -> float:
    """Tek bir trade/position kaydı için yeni size."""
    bankroll = infer_bankroll_at_entry(confidence, market_type, old_recorded_size)
    return new_size(confidence, market_type, bankroll)


def scale_factor(confidence: str, market_type: str, old_recorded_size: float) -> float:
    """Tüm finansal alanları çarpacağımız oran."""
    if old_recorded_size <= 0:
        return 0.0
    return compute_new_size_for_record(confidence, market_type, old_recorded_size) / old_recorded_size


# ── Record scaling ────────────────────────────────────────────────────────────


def scale_position(pos: dict) -> tuple[dict, float]:
    """Pozisyon kaydını yeni size'a göre ölçekle. (yeni_kayıt, ratio) döner."""
    confidence = pos.get("confidence", "")
    market_type = detect_market_type(pos.get("slug", ""))
    # Positions için recorded size = entry-time orijinal değil, partial sonrası CURRENT.
    # Original'ı reverse engineer etmek için scale_out_tier + scale_out_realized'a gerek var
    # ama veri eksik; bunun yerine ratio'yu old vs new orijinal sizing oranı üstünden hesaplıyoruz.
    bankroll = 1000.0  # paper default — bankroll snapshot'ı yok
    old_orig = old_size(confidence, market_type, bankroll)
    new_orig = new_size(confidence, market_type, bankroll)
    ratio = new_orig / old_orig if old_orig > 0 else 1.0

    pos["size_usdc"] = round(pos["size_usdc"] * ratio, 4)
    pos["shares"] = pos["shares"] * ratio
    pos["scale_out_realized_usdc"] = pos.get("scale_out_realized_usdc", 0.0) * ratio
    for pe in pos.get("partial_exits", []):
        if "realized_pnl_usdc" in pe:
            pe["realized_pnl_usdc"] = pe["realized_pnl_usdc"] * ratio
    return pos, ratio


def scale_trade(t: dict) -> tuple[dict, float]:
    """Trade history kaydını ölçekle."""
    confidence = t.get("confidence", "")
    market_type = detect_market_type(t.get("slug", ""))
    old_recorded = t.get("size_usdc", 0.0)
    ratio = scale_factor(confidence, market_type, old_recorded)

    t["size_usdc"] = round(old_recorded * ratio, 4)
    t["shares"] = t.get("shares", 0.0) * ratio
    t["exit_pnl_usdc"] = t.get("exit_pnl_usdc", 0.0) * ratio
    for pe in t.get("partial_exits", []):
        if "realized_pnl_usdc" in pe:
            pe["realized_pnl_usdc"] = pe["realized_pnl_usdc"] * ratio
    return t, ratio


# ── File I/O ──────────────────────────────────────────────────────────────────


def backup(path: Path, suffix: str = ".bak.2026-05-22-pre-sizing-migration") -> Path | None:
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + suffix)
    shutil.copy2(path, bak)
    return bak


def atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def atomic_write_jsonl(path: Path, records: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    tmp.replace(path)


def rebuild_equity_history(initial_bankroll: float, trades: list[dict], positions: dict) -> list[dict]:
    """Trade history + active positions'tan equity_history yeniden inşa et.

    Basitleştirme: tek bir 'current' snapshot üret — tarihsel chart yeni
    girişlerle dolacak. Migration zamanı discontinuity kabul edilir.
    """
    realized = sum(t.get("exit_pnl_usdc", 0.0) for t in trades)
    realized += sum(
        sum(pe.get("realized_pnl_usdc", 0.0) for pe in p.get("partial_exits", []))
        for p in positions.values()
    )
    realized += sum(p.get("scale_out_realized_usdc", 0.0) for p in positions.values())
    invested = sum(p.get("size_usdc", 0.0) for p in positions.values())
    bankroll = initial_bankroll - invested + realized
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bankroll": round(bankroll, 2),
        "realized_pnl": round(realized, 2),
        "unrealized_pnl": 0.0,
        "invested": round(invested, 2),
        "open_positions": len(positions),
    }
    return [snapshot]


# ── Main migration ────────────────────────────────────────────────────────────


def run_migration(repo_root: Path, apply: bool) -> dict:
    """Migration'ı çalıştır. Apply=False ise dry-run, dosya yazılmaz.

    Return: rapor sözlüğü (dosya counts + summary tutarları).
    """
    positions_path = repo_root / "data" / "positions.json"
    audit_dir = repo_root / "logs" / "audit"
    session_dir = repo_root / "logs" / "session"

    report = {
        "mode": "apply" if apply else "dry-run",
        "files_touched": [],
        "positions": {"count": 0, "old_invested": 0.0, "new_invested": 0.0, "rows": []},
        "trades": {
            "count": 0, "events": 0,
            "old_full_pnl": 0.0, "new_full_pnl": 0.0,
            "old_partial_pnl": 0.0, "new_partial_pnl": 0.0,
            "old_total_pnl": 0.0, "new_total_pnl": 0.0,
            "rows": [],
        },
    }

    # 1. positions.json
    if positions_path.exists():
        data = json.loads(positions_path.read_text(encoding="utf-8"))
        positions = data.get("positions", {})
        report["positions"]["count"] = len(positions)
        new_positions: dict = {}
        for cid, pos in positions.items():
            old_size_val = pos.get("size_usdc", 0.0)
            report["positions"]["old_invested"] += old_size_val
            updated, ratio = scale_position(dict(pos))
            new_positions[cid] = updated
            new_size_val = updated["size_usdc"]
            report["positions"]["new_invested"] += new_size_val
            report["positions"]["rows"].append({
                "slug": pos.get("slug", ""),
                "confidence": pos.get("confidence", ""),
                "market": detect_market_type(pos.get("slug", "")),
                "old_size": round(old_size_val, 2),
                "new_size": round(new_size_val, 2),
                "ratio": round(ratio, 3),
            })
        data["positions"] = new_positions
        if apply:
            backup(positions_path)
            atomic_write_json(positions_path, data)
            report["files_touched"].append(str(positions_path))

    # 2. trade_history.jsonl (audit + session)
    all_trades: list[dict] = []
    for src_dir in (audit_dir, session_dir):
        th_path = src_dir / "trade_history.jsonl"
        if not th_path.exists():
            continue
        raw = th_path.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        trades = [json.loads(line) for line in raw.split("\n") if line.strip()]
        new_trades = []
        for t in trades:
            old_full_p = t.get("exit_pnl_usdc", 0.0)
            old_partials = t.get("partial_exits", []) or []
            old_partial_p = sum(pe.get("realized_pnl_usdc", 0.0) for pe in old_partials)
            updated, _ratio = scale_trade(dict(t))
            new_trades.append(updated)
            new_full_p = updated.get("exit_pnl_usdc", 0.0)
            new_partials = updated.get("partial_exits", []) or []
            new_partial_p = sum(pe.get("realized_pnl_usdc", 0.0) for pe in new_partials)
            report["trades"]["count"] += 1
            # Event sayisi: her full-close 1 event (eger exit_pnl != 0) + her partial 1 event
            is_closed = (old_full_p != 0.0)
            report["trades"]["events"] += (1 if is_closed else 0) + len(old_partials)
            report["trades"]["old_full_pnl"] += old_full_p
            report["trades"]["new_full_pnl"] += new_full_p
            report["trades"]["old_partial_pnl"] += old_partial_p
            report["trades"]["new_partial_pnl"] += new_partial_p
            report["trades"]["old_total_pnl"] += old_full_p + old_partial_p
            report["trades"]["new_total_pnl"] += new_full_p + new_partial_p
            report["trades"]["rows"].append({
                "slug": t.get("slug", ""),
                "confidence": t.get("confidence", ""),
                "market": detect_market_type(t.get("slug", "")),
                "old_size": round(t.get("size_usdc", 0.0), 2),
                "new_size": round(updated.get("size_usdc", 0.0), 2),
                "old_full_pnl": round(old_full_p, 2),
                "new_full_pnl": round(new_full_p, 2),
                "old_partial_pnl": round(old_partial_p, 2),
                "new_partial_pnl": round(new_partial_p, 2),
                "num_partials": len(old_partials),
                "is_closed": is_closed,
            })
        if apply:
            backup(th_path)
            atomic_write_jsonl(th_path, new_trades)
            report["files_touched"].append(str(th_path))
        all_trades.extend(new_trades)

    # 3. equity_history.jsonl — regenerate
    new_positions_for_equity = data.get("positions", {}) if positions_path.exists() else {}
    new_equity = rebuild_equity_history(1000.0, all_trades, new_positions_for_equity)
    if apply:
        for eq_dir in (audit_dir, session_dir):
            eq_path = eq_dir / "equity_history.jsonl"
            if eq_path.exists():
                backup(eq_path)
                atomic_write_jsonl(eq_path, new_equity)
                report["files_touched"].append(str(eq_path))

    return report


def print_report(report: dict) -> None:
    print(f"\n{'='*72}")
    print(f"  MIGRATION RAPORU — mode: {report['mode']}")
    print(f"{'='*72}")

    print(f"\n  AKTİF POZİSYONLAR ({report['positions']['count']}):")
    print(f"  {'Slug':<55} {'Tier':<5} {'Old':>8} {'New':>8} {'Ratio':>7}")
    print(f"  {'-'*55} {'-'*5} {'-'*8} {'-'*8} {'-'*7}")
    for row in report["positions"]["rows"]:
        slug_short = row["slug"][:55]
        print(f"  {slug_short:<55} {row['confidence']:<5} ${row['old_size']:>6.2f} ${row['new_size']:>6.2f} {row['ratio']:>6.2f}x")
    print(f"\n  Toplam invested: ${report['positions']['old_invested']:.2f} → ${report['positions']['new_invested']:.2f}")

    print(f"\n  TRADE KAYITLARI ({report['trades']['count']} record, {report['trades']['events']} event):")
    print(f"  {'Slug':<55} {'Tier':<5} {'OldSz':>7} {'NewSz':>7} {'OldTot':>8} {'NewTot':>8} {'#P':>3}")
    print(f"  {'-'*55} {'-'*5} {'-'*7} {'-'*7} {'-'*8} {'-'*8} {'-'*3}")
    seen_slugs: set[str] = set()
    for row in report["trades"]["rows"]:
        key = row["slug"] + row["confidence"]
        if key in seen_slugs:
            continue
        seen_slugs.add(key)
        slug_short = row["slug"][:55]
        old_tot = row["old_full_pnl"] + row["old_partial_pnl"]
        new_tot = row["new_full_pnl"] + row["new_partial_pnl"]
        status = "" if row["is_closed"] else " (open)"
        print(f"  {slug_short:<55} {row['confidence']:<5} ${row['old_size']:>5.2f} ${row['new_size']:>5.2f} ${old_tot:>+6.2f} ${new_tot:>+6.2f} {row['num_partials']:>3}{status}")
    print(f"\n  Full-close PnL toplami:  ${report['trades']['old_full_pnl']:>+8.2f} -> ${report['trades']['new_full_pnl']:>+8.2f}")
    print(f"  Partial-exit PnL toplami: ${report['trades']['old_partial_pnl']:>+8.2f} -> ${report['trades']['new_partial_pnl']:>+8.2f}")
    print(f"  REALIZED PnL toplami:    ${report['trades']['old_total_pnl']:>+8.2f} -> ${report['trades']['new_total_pnl']:>+8.2f}")

    if report["files_touched"]:
        print(f"\n  YAZILAN DOSYALAR:")
        for f in report["files_touched"]:
            print(f"    - {f}")
        print(f"\n  Her dosya için .bak.2026-05-22-pre-sizing-migration yedek oluşturuldu.")
    else:
        print(f"\n  [DRY-RUN] Hiçbir dosya değiştirilmedi.")
    print(f"\n{'='*72}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Dosyaları gerçekten güncelle (default dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Sadece rapor (default davranış)")
    parser.add_argument("--self-test", action="store_true", help="Sizing helper sanity test")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    repo_root = Path(__file__).resolve().parent.parent  # tennis-lab/
    apply = args.apply  # dry-run default
    report = run_migration(repo_root, apply=apply)
    print_report(report)
    return 0


def _self_test() -> int:
    """Sizing helper'larının sanity check'i."""
    # B FSW: old $16.67 (capped at $50/3), new $35
    assert old_size("B", "tennis_first_set_winner", 1000) == 16.67, old_size("B", "tennis_first_set_winner", 1000)
    assert new_size("B", "tennis_first_set_winner", 1000) == 35.0
    # B set_totals: old $5 ($15/3), new $15
    assert old_size("B", "tennis_set_totals", 1000) == 5.0, old_size("B", "tennis_set_totals", 1000)
    assert new_size("B", "tennis_set_totals", 1000) == 15.0
    # A set_handicap: old $50 (no cap), new $15
    assert old_size("A", "tennis_set_handicap", 1000) == 50.0
    assert new_size("A", "tennis_set_handicap", 1000) == 15.0
    # A non-bimodal: old $50 (no /3), new $50 (no change)
    assert old_size("A", "tennis_moneyline", 1000) == 50.0
    assert new_size("A", "tennis_moneyline", 1000) == 50.0
    # Market type detection
    assert detect_market_type("atp-x-y-2026-set-totals-2pt5") == "tennis_set_totals"
    assert detect_market_type("atp-x-y-2026-set-handicap-home-1pt5") == "tennis_set_handicap"
    assert detect_market_type("atp-x-y-2026-match-total-23pt5") == "tennis_match_o_u"
    assert detect_market_type("atp-x-y-2026") == "tennis_moneyline"
    print("Self-test PASS — all assertions hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
