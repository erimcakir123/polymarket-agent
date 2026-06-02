# LAB v2 — Bağımsız Prediction Lab

**Main bot'a ASLA dokunulmadı.** Bu klasör tamamen izole.

## Aktif iyileştirmeler

1. **Surface-specific Glicko ratings** (Hard / Clay / Grass ayrı reyting)
   - Akademik: PLOS One 2022 — surface-aware ratings standardı yener (log-loss)
   - 6789 oyuncu × 3 yüzey = 20,367 farklı reyting
   - Build: `python lab_v2/scripts/build_tennis_surface_ratings.py`

2. **NBA/WNBA rest days adjustment**
   - Back-to-back oynayan takım → −30 Elo penalty
   - 2-gün ara → −10 Elo
   - 3+ gün → no penalty

3. **Pinnacle sharp-book filter** (pending — Odds API raw stream wiring gerekli)
   - Mevcut: tüm bookmaker'ların weighted ortalaması
   - Hedef: SADECE Pinnacle/Betfair Exchange/Smarkets

## Çalıştırma

```bash
python lab_v2/start.py
```

Dashboard: http://127.0.0.1:5051

## Silme (iz bırakmadan)

```bash
rm -rf lab_v2/
```

Main bot etkilenmez — patch'ler sadece lab process'inde çalışır,
codebase'de değişiklik yok.

## İzole yollar

- Data: `lab_v2/data/`
- Logs: `lab_v2/logs/`
- Config: `lab_v2/config.yaml` (port 5051)
- Process lock: `lab_v2/data/lab_v2.lock`

Main bot kendi `data/`, `logs/`, port 5050 ile aynı anda çalışabilir.
