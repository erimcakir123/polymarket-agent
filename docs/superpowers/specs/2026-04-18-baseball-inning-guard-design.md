# SPEC-008: Baseball Inning Guard — Skor+İnning Aware SL

> **Tarih:** 2026-04-18 (güncelleme: 2026-04-19)
> **Durum:** SUPERSEDED_BY SPEC-010 (baseball guard kaldirildi, yerine baseball_score_exit.py FORCED exit geldi)
> **Bağımlılık:** SPEC-005 (ESPN Score Client — IMPLEMENTED)
> **Kapsam:** Strategy katmanı — `stop_loss.py` + `monitor.py`

---

## 1. Problem

Baseball'da düz %30 stop loss maçın hangi aşamasında olduğuna ve skora bakmıyor.
1. inning'te skor 0-0 iken fiyat %30 düşünce (whale hareketi, pitching
tepkisi gibi geçici nedenlerle) SL tetiklenip pozisyon erken kapatılıyor.

**Gerçek örnek:** Giants vs Nationals — 1. inning ortası, 0-0, fiyat
53¢→37¢, SL tetiklendi (-$20.35 kayıp). Maçta henüz bilgi yok.

Baseball 9 inning oynanır. Erken inning'lerde büyük açıklar bile kapanabilir
(6-7 inning kaldı). Geç inning'lerde aynı açık kapanması çok zor.

---

## 2. Çözüm Felsefesi

Bot artık "fiyat %30 düştü mü?" yerine **"bu maç hala kazanılabilir mi?"**
sorusunu sorar.

- **Kazanılabilir** → fiyat ne kadar düşerse düşsün SL devre dışı, tut.
  Fiyat düşüşü muhtemelen geçici gürültü.
- **Kazanılamaz** → normal %30 SL aktif. Maç ölü, SL doğru çalışır.
- **Bilinmiyor** (veri yok) → güvenli fallback, normal %30 SL.

Aynı skor (3-0 geride) erken inning'te "dur bekle", geç inning'te "çık"
anlamına geliyor. Maç ne kadar ilerlerse, o kadar az açık tolere ediyoruz.

Tenis SPEC-006'daki yaklaşıma benzer: orada set+game skouna bakarak
"maç dönebilir mi?" kararı veriyoruz. Burada inning+run skoruna bakıyoruz.

---

## 3. Canlılık Matrisi

`deficit` = rakip skor − bizim takım skoru (negatifse öndeyiz)

| İnning | Deficit ≥ bu ise → ÖLÜ | Mantık |
|---|---|---|
| 1-3 | 6 | Daha 6+ inning var, her şey olabilir |
| 4-5 | 5 | Maç şekillenmeye başladı ama hala erken |
| 6-7 | 4 | Maçın son üçte biri, büyük açık kapanmaz |
| 8 | 3 | 1-2 inning kaldı, 3 run zor |
| 9 | 2 | Son inning, 2+ run çok zor |
| Uzatma (10+) | 1 | Her run kritik, gerideysen bitti |

**Deficit ≤ 0 (önde veya eşit) → HER ZAMAN canlı.** SL devre dışı.

### Karar akışı

```
Skor verisi var mı?
  ├─ Hayır → UNKNOWN → normal %30 SL
  └─ Evet → deficit hesapla
       ├─ Önde/eşit (deficit ≤ 0) → ALIVE → SL devre dışı
       └─ Geride (deficit > 0)
            ├─ deficit < eşik → ALIVE → SL devre dışı
            └─ deficit ≥ eşik → DEAD → normal %30 SL aktif
```

---

## 4. Veri Kaynağı

### İnning tespiti

ESPN API'den `period` alanı zaten geliyor → `score_info["period"]`.

ESPN baseball period format örnekleri:
- `"Top 1st"`, `"Mid 1st"`, `"Bot 1st"`
- `"Top 5th"`, `"Mid 5th"`, `"Bot 5th"`
- `"Top 9th"`, `"End 9th"`
- `"Final"`, `"In Progress"`, `""`

Parse: string'den sayısal kısmı çıkar (`1st`→1, `2nd`→2, `5th`→5).
Parse edilemezse `None` → UNKNOWN fallback.

### Deficit tespiti

`score_info["deficit"]` zaten score_enricher'da hesaplanıyor.
Direction-aware: `opp_score - our_score`. Pozitif = gerideyiz.

`score_info["available"]` flag'i verinin geçerli olup olmadığını gösterir.

Her iki veri (inning + deficit) zaten mevcut altyapıda var.
Yeni API çağrısı veya veri kaynağı gerekmez.

---

## 5. Kod Değişiklikleri

### 5.1. `stop_loss.py` — `parse_baseball_inning()` (yeni pure fonksiyon)

```python
def parse_baseball_inning(period: str) -> int | None:
    """ESPN period string'inden inning numarası çıkar.

    Örnekler: "Top 1st" → 1, "Bot 5th" → 5, "Mid 9th" → 9
    Returns None eğer parse edilemezse.
    """
```

### 5.2. `stop_loss.py` — `is_baseball_alive()` (yeni pure fonksiyon)

```python
def is_baseball_alive(inning: int, deficit: int, is_extra: bool) -> bool | None:
    """Canlılık matrisi. True=canlı, False=ölü, None=bilinmiyor."""
```

Config'den `comeback_thresholds` okur. Magic number yok.

### 5.3. `stop_loss.py` — `compute_stop_loss_pct()` güncelleme

Mevcut imza:
```python
def compute_stop_loss_pct(pos: Position) -> float | None:
```

Yeni imza:
```python
def compute_stop_loss_pct(pos: Position, score_info: dict | None = None) -> float | None:
```

Yeni katman — mevcut katman 2 (totals/spread skip) ile katman 3 (ultra-low)
arasına eklenir:

```
Katman 2.5: Baseball canlılık guard
  1. score_info yoksa veya available=False → atla (fallback)
  2. period parse et → inning al. Parse edilemezse → atla
  3. deficit al. deficit ≤ 0 → return None (SL devre dışı, canlı)
  4. is_baseball_alive(inning, deficit) → True ise return None (SL devre dışı)
  5. False ise → atla, SL normal devam (ölü maç, %30 SL aktif)
```

### 5.4. `stop_loss.py` — `check()` güncelleme

Mevcut imza:
```python
def check(pos: Position) -> bool:
```

Yeni imza:
```python
def check(pos: Position, score_info: dict | None = None) -> bool:
```

`score_info`'yu `compute_stop_loss_pct()`'ye iletir. Geriye uyumlu.

### 5.5. `monitor.py` — `stop_loss.check()` çağrısı güncelleme

Satır ~219:
```python
# Mevcut:
if stop_loss.check(pos):

# Yeni:
if stop_loss.check(pos, score_info):
```

`score_info` zaten `evaluate()` parametresi olarak mevcut. Sadece iletmek yeterli.

---

## 6. Config

`sport_rules.py`'deki `mlb` bloğuna yeni alan:

```python
"mlb": {
    "stop_loss_pct": 0.30,
    "comeback_thresholds": {3: 6, 5: 5, 7: 4, 8: 3, 9: 2},  # YENİ
    "extra_inning_threshold": 1,                               # YENİ
    ...
}
```

`comeback_thresholds` dict: key = inning üst sınırı (dahil), value = ölü eşiği.
Lookup: inning ≤ key olan ilk eşleşme. Ör: inning=4 → key=5 → eşik=5.

---

## 7. Etkilenmeyen Mekanizmalar

Bu değişiklik SADECE flat stop_loss'u etkiler. Aşağıdakiler **olduğu gibi kalır**:

| Mekanizma | Etki |
|---|---|
| Graduated SL | Etkilenmez (ayrı fonksiyon, kendi elapsed-gated mantığı) |
| Near-resolve | Etkilenmez (fiyat ≥ threshold → çık) |
| Scale-out | Etkilenmez (kâr al mekanizması) |
| Market flip | Etkilenmez (A-conf hold dalı) |
| Never-in-profit | Etkilenmez (elapsed-gated) |
| Catastrophic watch | Etkilenmez (NHL only) |

---

## 8. Sınır Durumları

| Durum | Davranış |
|---|---|
| Score enricher veri çekemedi (`score_info=None`) | UNKNOWN → SL normal %30 |
| `period` parse edilemiyor (boş, "In Progress") | UNKNOWN → SL normal %30 |
| Maç başlamadı (`match_live=False`) | Score enricher veri göndermez → SL normal |
| Önde veya eşit (deficit ≤ 0) | ALIVE → SL devre dışı |
| 1. inning, 0-0 | deficit=0, ALIVE → SL devre dışı (Giants fix) |
| 1. inning, 0-5 geride | deficit=5 < eşik 6, ALIVE → SL devre dışı |
| 1. inning, 0-6 geride | deficit=6 ≥ eşik 6, DEAD → SL %30 aktif |
| 8. inning, 0-3 geride | deficit=3 ≥ eşik 3, DEAD → SL %30 aktif |
| 8. inning, 0-2 geride | deficit=2 < eşik 3, ALIVE → SL devre dışı |
| 9. inning, 1 run geride | deficit=1 < eşik 2, ALIVE → SL devre dışı |
| Uzatma, 1 run geride | deficit=1 ≥ eşik 1, DEAD → SL %30 aktif |
| Uzatma, eşit | deficit=0, ALIVE → SL devre dışı |
| Maç bitti ("Final") | Parse `None` → UNKNOWN → SL normal |
| KBO/NPB | Aynı `baseball` normalize → aynı kural |
| Non-baseball (NBA, tennis) | Guard atlanır, mevcut davranış korunur |

---

## 9. Test Senaryoları

Dosya: `tests/unit/strategy/exit/test_baseball_guard.py`

### Parse testleri
- `test_parse_inning_top_1st_returns_1`
- `test_parse_inning_bot_5th_returns_5`
- `test_parse_inning_mid_9th_returns_9`
- `test_parse_inning_extra_11th_returns_11`
- `test_parse_inning_empty_returns_none`
- `test_parse_inning_final_returns_none`

### Canlılık matrisi testleri
- `test_alive_deficit_0_any_inning`: eşit skor → ALIVE
- `test_alive_leading_any_inning`: önde → ALIVE
- `test_alive_inning_1_deficit_5`: 5 run geride ama erken → ALIVE
- `test_dead_inning_1_deficit_6`: 6 run geride, erken de olsa → DEAD
- `test_alive_inning_8_deficit_2`: 2 run geride, 8. inning → ALIVE
- `test_dead_inning_8_deficit_3`: 3 run geride, 8. inning → DEAD
- `test_alive_inning_9_deficit_1`: 1 run geride, son inning → ALIVE
- `test_dead_inning_9_deficit_2`: 2 run geride, son inning → DEAD
- `test_dead_extra_deficit_1`: uzatma, 1 run geride → DEAD
- `test_alive_extra_deficit_0`: uzatma, eşit → ALIVE

### SL entegrasyon testleri
- `test_baseball_alive_sl_disabled`: canlı maç → %35 düşüş → SL tetiklenmez
- `test_baseball_dead_sl_active`: ölü maç → %35 düşüş → SL tetiklenir
- `test_baseball_unknown_sl_fallback`: veri yok → %35 düşüş → SL tetiklenir
- `test_non_baseball_unaffected`: NBA → guard atlanır → SL normal çalışır
- `test_score_info_none_fallback`: score_info=None → SL normal çalışır

---

## 10. Dosya Değişiklik Özeti

| Dosya | İşlem | Tahmini Değişiklik |
|---|---|---|
| `src/strategy/exit/stop_loss.py` | GÜNCELLEME | +35 satır (parse + canlılık + guard) |
| `src/strategy/exit/monitor.py` | GÜNCELLEME | +1 satır (score_info iletme) |
| `src/config/sport_rules.py` | GÜNCELLEME | +2 satır (comeback_thresholds + extra) |
| `tests/unit/strategy/exit/test_baseball_guard.py` | YENİ | ~120 satır |
| **Toplam** | | ~160 satır |

Tüm dosyalar 400 satır altında kalır. `stop_loss.py` 73 + 35 = ~108 satır.
Sadece strategy katmanı.

---

## 11. Kapsam Dışı

- Catastrophic floor (kullanıcı istemedi)
- Skor modifier (SL yüzdesini skora göre kaydırma — gereksiz karmaşıklık)
- Direkt çıkış (DEAD = hemen çık) — ölü maçta bile %30 SL ile çıkmak daha güvenli
- Bases loaded / at-bat context — v2 için backtest sonrası değerlendirilir
- Diğer sporlar (NBA, NFL) için benzer sistem — ayrı SPEC gerekir
