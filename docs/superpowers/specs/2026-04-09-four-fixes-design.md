# 4 Fix Design — Scale-out + Hold Rules + Live Dip Bug + Slot

## 1. Futbol + Beyzbol A-conf Scale-out
**Sorun**: A-conf'ta scale-out bypass — hold-to-resolve. Ama futbolda draw riski (3 outcome), beyzbolda inning spike'ları var. Her ikisinde de kısmı kâr alınmalı.

**Fix**: `src/portfolio.py` check_scale_outs() — A-conf bypass'a soccer + baseball exception:
```python
# Mevcut:
if (pos.confidence == "A" and _eff_entry >= 0.60
        and entry_reason not in ("upset", "penny")):
    continue  # skip scale-out

# Yeni:
_sport = classify_sport_from_slug(pos.slug)
if (pos.confidence == "A" and _eff_entry >= 0.60
        and entry_reason not in ("upset", "penny")
        and _sport not in ("soccer", "baseball")):  # draw risk + inning spikes
    continue
```

`classify_sport_from_slug` = slug prefix'ten sport döndüren basit helper (sport_classifier.py zaten var, Position objesinden çağrılabilir).

## 2. Beyzbol A-conf: %70 Elapsed Sonrası SL Aktif
**Sorun**: MLB A-conf'ta sadece catastrophic floor + market flip koruyor. %70 elapsed sonrası (6. inning+) kaybediyorsak graduated SL devreye girmeli.

**Fix**: `src/match_exit.py` check_match_exit() — A-conf hold bloğuna elapsed exception:
```python
# Mevcut:
if a_conf_hold:
    if effective_current < 0.50:
        return exit(a_conf_market_flip)
    # else: skip graduated SL

# Yeni:
if a_conf_hold:
    if effective_current < 0.50:
        return exit(a_conf_market_flip)
    # Baseball: after 70% elapsed, allow graduated SL
    _is_baseball = sport_tag in ("mlb", "baseball", "kbo", "npb")
    if _is_baseball and elapsed_pct >= 0.70:
        pass  # Fall through to graduated SL below
    else:
        pass  # Skip graduated SL (normal hold-to-resolve)
        # Need to skip the graduated SL block — restructure if/elif
```

Daha temiz: A-conf hold bloğunda beyzbol %70+ ve zararda ise graduated SL'ye düşür:
```python
if a_conf_hold:
    if effective_current < 0.50:
        return exit(a_conf_market_flip)
    # Baseball 70%+ elapsed: if losing, allow graduated SL. If winning, keep holding.
    _is_baseball = sport_tag in ("mlb", "baseball", "kbo", "npb")
    if _is_baseball and elapsed_pct >= 0.70 and effective_current < effective_entry:
        pass  # Fall through to graduated SL (losing, cut it)
    else:
        pass  # Normal hold-to-resolve (winning or <70%)
```

Yani: beyzbol %70 elapsed + zararda → graduated SL. Kârdaysa → hold-to-resolve devam (%94+ near_resolve çıkar).

## 3. Live Dip Bug Fix — B- skip + Moneyline filtresi
**Sorun**: Live dip entry_gate'i bypass ediyor → B- skip yok, moneyline filtresi yok. Golf Top10 prop market'e $20 girdi.

**Fix**: `src/live_strategies.py` check_live_dip() — iki guard ekle:
1. Moneyline filtresi: `sportsMarketType != "moneyline"` → skip
2. Confidence kontrolü yok ama B- skip dolaylı: live_dip zaten `confidence="B-"` ile giriyor — ama B- skip entry_gate'te. Fix: live_dip size'ı 0'a düşür veya direkt skip.

Aslında en basit: scanner zaten `sportsMarketType: moneyline` filtresi var. Live dip `fresh_markets` scanner'dan alıyor — ama scanner filtresi çalışmıyorsa sorun orada. Kontrol gerekiyor.

## 4. Slot Fix — Tek Pool
**Sorun**: VS reserved 3 slot ama VS hiç kullanılmıyor. NRM 15/15 gösterip 19 pozisyon var.

**Fix**: 
- `src/config.py`: `reserved_slots: int = 0` (VS reserved kaldır)
- `src/entry_gate.py` line 994: `max_positions - active_count` (zaten doğru, reserved yok)
- `src/agent.py` refill loop: `open_slots = max_positions - active_count` (vs_reserved çıkar)
- Dashboard: NRM max = max_positions (20), VS 0/0

## Doğrulama
1. Futbol + beyzbol A-conf: scale-out tetikleniyor (+%25'te)
2. MLB %70 elapsed: graduated SL aktif, kaybediyorsak çıkıyor
3. Golf/prop market'lere live dip girmiyor
4. Slot count: max 20, NRM/VS ayrımı yok
