"""Tahmin motoru sağlık kontrolu — ratings + calibration + open positions."""
import json
from pathlib import Path

# Tennis ratings
d = json.loads(Path("data/tennis_ratings.json").read_text(encoding="utf-8"))
mus = [v["rating"]["mu"] for v in d.values()
       if isinstance(v.get("rating"), dict) and "mu" in v["rating"]]
phis = [v["rating"]["phi"] for v in d.values()
        if isinstance(v.get("rating"), dict) and "phi" in v["rating"]]
print(f"Tennis ratings: {len(mus)} oyuncu")
print(f"  mu  min/avg/max: {min(mus):.0f} / {sum(mus)/len(mus):.0f} / {max(mus):.0f}")
print(f"  phi min/avg/max: {min(phis):.0f} / {sum(phis)/len(phis):.0f} / {max(phis):.0f}")
trusted = sum(1 for p in phis if p < 100)
print(f"  Guvenilir (phi<100): {trusted} ({100*trusted/len(phis):.0f}%)")
print()

top = sorted([(v["rating"]["mu"], k) for k, v in d.items()], reverse=True)[:10]
print("=== TENNIS TOP 10 ===")
for mu, name in top:
    print(f"  {name:30} mu={mu:.0f}")
print()

print("=== BASKETBALL ratings ===")
for league in ["nba", "wnba", "ncaab", "wncaab", "euroleague",
               "g_league", "summer_league", "eurocup"]:
    fp = Path(f"data/basketball_cache/{league}_ratings.json")
    if fp.exists():
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                items = list(data.items())[:2]
            else:
                items = []
            print(f"  {league:15} {len(data)} takim")
            for k, v in items:
                if isinstance(v, dict):
                    elo = v.get("elo_rating") or v.get("rating") or 0
                    games = v.get("elo_games", 0)
                    print(f"      {k}: elo={elo:.0f} games={games}")
        except Exception as e:
            print(f"  {league:15} ERROR: {e}")
    else:
        print(f"  {league:15} dosya yok (sezon disi)")
print()

cp = Path("data/calibration_curves.json")
if cp.exists():
    c = json.loads(cp.read_text(encoding="utf-8"))
    print(f"Calibration curves: VAR ({len(c)} egri)")
else:
    print("Calibration curves: YOK (model ham olasilik veriyor, kalibre edilmemis)")
print()

# Open positions
pp = Path("data/positions.json")
if pp.exists():
    pos = json.loads(pp.read_text(encoding="utf-8"))
    if isinstance(pos, dict) and "positions" in pos:
        pos = pos["positions"]
    if isinstance(pos, dict):
        items = list(pos.values())
    else:
        items = pos
    print(f"=== ACIK POZISYONLAR ({len(items)}) ===")
    for p in items[:20]:
        if not isinstance(p, dict):
            continue
        anchor = p.get("anchor_probability", 0)
        entry = p.get("entry_price", 0)
        d_ = p.get("direction", "")
        sl = p.get("slug", "?")[:55]
        ms = anchor if d_ == "BUY_YES" else 1 - anchor
        edge = ms - entry
        print(f"  {sl:55} {d_:8} entry={entry:.3f} anchor={anchor:.3f} model_for_side={ms:.3f} edge={edge:+.3f}")
