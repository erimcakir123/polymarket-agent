# SPEC-013: Favorite Filter + Midpoint Scale-Out

> **Durum**: IMPLEMENTED
> **Tarih**: 2026-04-20

## Problem

1. **Underdog bet'ler**: Bot TEX-SEA 30¢ BUY_YES girdi (bookmaker %44), 10 dk'da
   -$20 patladı. MIL-CHI (46¢, %49.7), SD-LAA (43¢, %48) gibi ince edge'li
   underdog'lar yüksek varyans oluşturdu. Kullanıcı "rasyonel sistem = sadece
   favori tarafa oyna" dedi.

2. **Scale-out erken tetik**: Threshold PnL% bazlıydı (0.15 = %15 PnL).
   43¢ entry'de 49¢'te tetikleniyor — sadece +6¢ hareket, $2-3 kilit,
   "kalp kırıyor". Entry fiyatına göre adaletsiz (70¢ entry'de 80¢'te tetikler,
   farklı distance).

## Solution

### 1. Favorite Filter (min_favorite_probability)

Normal + early entry'de **post-direction** guard:

```python
our_side_prob = bm_prob.probability if direction == BUY_YES else (1 - bm_prob.probability)
if our_side_prob < min_favorite_probability:
    return None
```

Default 0.52 (SPEC-013 rev, 0.55→0.52 DET-BOS 1-puan-marj fix). config.yaml'da `edge.min_favorite_probability` + `early.min_favorite_probability`.

**NOT**: Eski `early.min_anchor_probability` yalnız P(YES) kontrol ediyordu —
BUY_NO durumunda yanlış mantık. Yeni unified filter tüm direction'lara adil.

### 2. Scale-out Midpoint Semantics

Threshold yeni anlam: `(current - entry) / (0.99 - entry)` distance fraction.
- threshold = 0.50 → entry ile 0.99 arasının yarısında tetikler
- Entry fiyatından bağımsız adaletli tetikleme

| Entry | Trigger price (0.50 threshold) | Max distance | Lock (40% of $45) |
|---|---|---|---|
| 0.30 | 0.645 | 0.69 | ≈$14 |
| 0.43 | 0.71 | 0.56 | ≈$11 |
| 0.70 | 0.845 | 0.29 | ≈$8 |

## Etki

- MIL, SD-LAA, TEX gibi underdog bet'ler **girmez**
- Scale-out kilit miktarları ~3-4x büyür ($2-3 → $8-14)

## Rollback

Config override ile:
- `edge.min_favorite_probability: 0.0` → underdog'lar yine girer
- `scale_out.tiers[0].threshold: 0.15` → eski PnL% davranışı YAKLAŞIK (yeni kod
  distance fraction hesaplar, 0.15 = %15 yol, entry'ye göre farklı anlama gelir)

## İlgili dosyalar

- `src/strategy/entry/normal.py` — favorite guard
- `src/strategy/entry/early_entry.py` — rename + fix
- `src/strategy/entry/gate.py` — GateConfig fields
- `src/config/settings.py` — EdgeConfig + EarlyEntryConfig
- `src/strategy/exit/scale_out.py` — midpoint semantic
- `src/strategy/exit/monitor.py` — call site
- `config.yaml` — edge.min_favorite_probability: 0.55, scale_out.tiers[0].threshold: 0.50
- Tests: test_normal.py, test_early_entry.py, test_gate.py, test_scale_out.py, test_monitor.py

## Commits

- 84b3392: Task 1 — min_favorite_probability guard
- 5259b04: Task 2 — scale-out midpoint
