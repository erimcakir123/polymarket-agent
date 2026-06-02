"""Tennis bot loss analysis — kesin sayilar, tahmin yok."""
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def hours_held(r):
    a = parse_iso(r.get("entry_timestamp"))
    b = parse_iso(r.get("exit_timestamp"))
    if not a or not b:
        return None
    return (b - a).total_seconds() / 3600


BOTS = [
    ("TENNIS LAB", r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-lab"),
    ("TENNIS PAPER LAB", r"c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/tennis-paper-lab"),
]

for name, path in BOTS:
    print(f"\n{'#'*78}")
    print(f"# {name}")
    print(f"{'#'*78}")
    pos = json.load(open(f"{path}/data/positions.json"))
    try:
        recs = [
            json.loads(l)
            for l in open(f"{path}/logs/audit/trade_history.jsonl", encoding="utf-8")
            if l.strip()
        ]
    except FileNotFoundError:
        recs = []

    print("\n## GENEL")
    print(f"Toplam audit kaydi: {len(recs)}")
    closed = [r for r in recs if r.get("exit_reason")]
    print(f"Kapanmis: {len(closed)} | Acik (state): {len(pos['positions'])}")
    print(f"Toplam realized PnL: ${pos['realized_pnl']:+.2f}")

    # ============ ACIK POZISYONLAR ============
    print(f"\n## ACIK POZISYONLAR ({len(pos['positions'])} adet) - en kotu en ustte")
    p_list = list(pos["positions"].values())
    print(
        f"  {'Slug':<53} {'Conf':<4} {'Size':<6} {'Entry':<6} {'Curr':<6} {'PnL%':<7} {'Hours'}"
    )
    print("  " + "-" * 95)
    now = datetime.now(timezone.utc)
    for p in sorted(p_list, key=lambda x: x.get("unrealized_pnl_pct", 0)):
        slug = p["slug"][:53]
        conf = p.get("confidence", "-")
        size = p["size_usdc"]
        entry = p["entry_price"]
        curr = p.get("current_price", 0)
        pnl_pct = p.get("unrealized_pnl_pct", 0)
        ts = parse_iso(p.get("entry_timestamp"))
        hours = (now - ts).total_seconds() / 3600 if ts else 0
        print(
            f"  {slug:<53} {conf:<4} ${size:<5.0f} {entry:<6.3f} {curr:<6.3f} {pnl_pct:+6.1%} {hours:.1f}h"
        )
    open_exposure = sum(p["size_usdc"] for p in p_list)
    open_unrealized = sum(p.get("unrealized_pnl_usdc", 0) for p in p_list)
    print(f"  TOPLAM: exposure=${open_exposure:.0f}, unrealized={open_unrealized:+.2f}")

    # ============ KAPANMIS TRADE'LER ============
    print(f"\n## KAPANMIS TRADE'LER ({len(closed)} adet) - en buyuk kayip en ustte")
    if closed:
        for r in sorted(closed, key=lambda r: r.get("exit_pnl_usdc", 0)):
            slug = r["slug"][:53]
            conf = r.get("confidence", "-")
            size = r["size_usdc"]
            entry = r["entry_price"]
            exit_p = r.get("exit_price", 0)
            pnl = r.get("exit_pnl_usdc", 0)
            reason = r.get("exit_reason", "-")
            held = hours_held(r) or 0
            print(
                f"  {slug:<53} {conf} ${size:.0f}  {entry:.3f}->{exit_p:.3f}  pnl=${pnl:+7.2f}  reason={reason:<22}  held={held:.1f}h"
            )

    # ============ EXIT REASON BREAKDOWN ============
    print("\n## EXIT SEBEPLERI")
    reason_stats = defaultdict(
        lambda: {"count": 0, "wins": 0, "losses": 0, "total_pnl": 0}
    )
    for r in closed:
        reason = r.get("exit_reason", "?")
        pnl = r.get("exit_pnl_usdc", 0)
        s = reason_stats[reason]
        s["count"] += 1
        s["total_pnl"] += pnl
        if pnl > 0:
            s["wins"] += 1
        elif pnl < 0:
            s["losses"] += 1
    for reason, s in sorted(reason_stats.items(), key=lambda x: x[1]["total_pnl"]):
        print(
            f"  {reason:<25} count={s['count']:2d}  wins={s['wins']}  losses={s['losses']}  net=${s['total_pnl']:+.2f}"
        )

    # ============ CONFIDENCE BREAKDOWN ============
    print("\n## CONFIDENCE BREAKDOWN (kapanmis trade'ler)")
    conf_stats = defaultdict(
        lambda: {"count": 0, "wins": 0, "losses": 0, "total_pnl": 0, "sum_size": 0}
    )
    for r in closed:
        c = r.get("confidence", "-")
        pnl = r.get("exit_pnl_usdc", 0)
        s = conf_stats[c]
        s["count"] += 1
        s["total_pnl"] += pnl
        s["sum_size"] += r["size_usdc"]
        if pnl > 0:
            s["wins"] += 1
        elif pnl < 0:
            s["losses"] += 1
    for c, s in sorted(conf_stats.items()):
        wr = s["wins"] / s["count"] * 100 if s["count"] else 0
        avg_size = s["sum_size"] / s["count"] if s["count"] else 0
        print(
            f"  {c}: count={s['count']:2d}  win%={wr:5.1f}  avg_size=${avg_size:.0f}  net=${s['total_pnl']:+.2f}"
        )

    # ============ MARKET TYPE BREAKDOWN ============
    print("\n## MARKET TIPI (slug-based)")
    prefix_stats = defaultdict(lambda: {"count": 0, "total_pnl": 0, "wins": 0, "losses": 0})
    for r in closed:
        slug = r["slug"]
        if "first-set" in slug and "totals" in slug:
            mt = "first_set_totals"
        elif "first-set" in slug:
            mt = "first_set_winner"
        elif "match-total" in slug:
            mt = "match_total"
        elif "set-handicap" in slug:
            mt = "set_handicap"
        elif "set-totals" in slug:
            mt = "set_totals"
        else:
            mt = "moneyline"
        tour = slug.split("-")[0]
        key = f"{tour}-{mt}"
        s = prefix_stats[key]
        s["count"] += 1
        s["total_pnl"] += r.get("exit_pnl_usdc", 0)
        if r.get("exit_pnl_usdc", 0) > 0:
            s["wins"] += 1
        else:
            s["losses"] += 1
    for k, s in sorted(prefix_stats.items()):
        print(
            f"  {k:<35} count={s['count']:2d}  wins={s['wins']} losses={s['losses']}  net=${s['total_pnl']:+.2f}"
        )

    # ============ HOLD TIME ============
    print("\n## HOLD TIME ANALIZI")
    fast_loss = [
        r for r in closed if (hours_held(r) or 0) < 2 and r.get("exit_pnl_usdc", 0) < 0
    ]
    slow_loss = [
        r for r in closed if (hours_held(r) or 0) >= 2 and r.get("exit_pnl_usdc", 0) < 0
    ]
    fast_win = [
        r for r in closed if (hours_held(r) or 0) < 2 and r.get("exit_pnl_usdc", 0) > 0
    ]
    slow_win = [
        r for r in closed if (hours_held(r) or 0) >= 2 and r.get("exit_pnl_usdc", 0) > 0
    ]
    print(
        f"  Hizli (<2h) kayip: {len(fast_loss)} adet, net=${sum(r['exit_pnl_usdc'] for r in fast_loss):+.2f}"
    )
    print(
        f"  Yavas (>=2h) kayip: {len(slow_loss)} adet, net=${sum(r['exit_pnl_usdc'] for r in slow_loss):+.2f}"
    )
    print(
        f"  Hizli (<2h) kazanc: {len(fast_win)} adet, net=${sum(r['exit_pnl_usdc'] for r in fast_win):+.2f}"
    )
    print(
        f"  Yavas (>=2h) kazanc: {len(slow_win)} adet, net=${sum(r['exit_pnl_usdc'] for r in slow_win):+.2f}"
    )

    # ============ TRADING MATEMATIGI ============
    print("\n## TRADING MATEMATIGI")
    if closed:
        n = len(closed)
        n_win = len([r for r in closed if r.get("exit_pnl_usdc", 0) > 0])
        n_loss = len([r for r in closed if r.get("exit_pnl_usdc", 0) < 0])
        wins_sum = sum(r["exit_pnl_usdc"] for r in closed if r.get("exit_pnl_usdc", 0) > 0)
        losses_sum = sum(r["exit_pnl_usdc"] for r in closed if r.get("exit_pnl_usdc", 0) < 0)
        avg_win = wins_sum / n_win if n_win else 0
        avg_loss = losses_sum / n_loss if n_loss else 0
        wr = n_win / n
        expectancy = wr * avg_win + (1 - wr) * avg_loss
        print(f"  Toplam: {n} trade")
        print(f"  Win rate: {wr:.1%}")
        print(f"  Avg win: ${avg_win:.2f}")
        print(f"  Avg loss: ${avg_loss:.2f}")
        if avg_win:
            print(f"  Kayip/Kazanc orani: {abs(avg_loss/avg_win):.2f}x")
        print(f"  Beklenen deger per trade: ${expectancy:+.2f}")
        print(f"  100 trade icin: ${expectancy*100:+.0f}")
