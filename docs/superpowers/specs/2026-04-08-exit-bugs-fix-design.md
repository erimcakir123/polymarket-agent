# Exit System Bug Fixes — 4 Bugs

## Context
WS scale-out eklendi ama `int(so["tier"][-1])` crash → her cycle hata → hiçbir exit çalışmıyor. Ayrıca dedup yok (aynı pozisyon 10+ kez queue), match_start_iso retroactive güncellenmiyor (tenis turnuva saati vs gerçek maç saati).

## Bug 1: Cycle Crash — `int("e")` Parse Error
**Dosya**: `src/agent.py` line 693
**Sorun**: `so["tier"]` = `"tier1_risk_free"` → `[-1]` = `"e"` → `int("e")` crash
**Fix**: Tier numarasını string'den çıkar:
```python
# Eski:
if pos and pos.scale_out_tier < int(so["tier"][-1]):
# Yeni:
_tier_num = 1 if "tier1" in so["tier"] else (2 if "tier2" in so["tier"] else 0)
if pos and pos.scale_out_tier < _tier_num:
```

## Bug 2: WS Scale-Out Dedup
**Dosya**: `src/exit_monitor.py` line 234-241
**Sorun**: Aynı cid 10+ kez queue'ya ekleniyor, dedup guard yok
**Fix**: `_ws_scale_out_queued_set` ekle (exit queue pattern'ını kopyala):
- Queue'ya eklemeden önce `cid in _ws_scale_out_queued_set` kontrol
- `drain_scale_outs()`'ta set'i temizle

## Bug 3: Scale-Out Execute
**Sorun**: Bug 1 crash yüzünden `process_scale_outs()` hiç çalışmıyordu
**Fix**: Bug 1 fix'lenince otomatik çözülür. Fiyat hala yüksekken process_scale_outs current price'a bakar → tetikler. Ek fix gerekmez.

## Bug 4: match_start_iso Retroactive Update
**Dosya**: `src/price_updater.py` line 169
**Sorun**: `not pos.match_start_iso` koşulu retroactive güncellemeyi engelliyor
**Fix**: Koşulu kaldır, her zaman güncelle:
```python
# Eski:
if _start_usable and not pos.match_start_iso:
# Yeni:
if _start_usable:
```

## Doğrulama
1. Cycle error logu olmamalı
2. `WS_SCALE_OUT queued` per cid 1 kez
3. `SCALE_OUT` execute logu görünmeli
4. Tenis pozisyonlarında doğru match_start_iso (gameStartTime)
