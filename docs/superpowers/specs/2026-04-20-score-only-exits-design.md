# SPEC — Score-Only Exit System (A3 Unification)

**Tarih:** 2026-04-20
**Durum:** IMPLEMENTED (2026-04-20)
**Kapsam:** Exit sistemi baştan aşağı sadeleştirme — fiyat-tabanlı refleksler (flat SL + graduated SL + catastrophic bounce) kaldırılıyor, çıkış kararları skor-tabanlı kurallara dayanıyor. NBA ve NFL için yeni skor-çıkışları ekleniyor. A-hold / non-A-hold dal ayrımı tek dala indiriliyor.

---

## 1. Motivasyon

### Gözlemlenen problem
Halys vs Faria maçında pozisyon `graduated_sl` ile -%32.7 ROI'de kapandı; skorda henüz kayıp yok, 1. set 6-6 tiebreak öncesi. Fiyat-refleks SL, maç içi normal dalgalanmayı "kayıp" olarak okudu. Bot 1 dakika sonra aynı maça yeniden girdi, tekrar aynı şekilde stop oldu.

### Kök neden
Fiyat-tabanlı SL guard'ları (flat stop-loss, graduated SL, catastrophic watch) piyasayı "sinyal" olarak kabul ediyor. Polymarket fiyatları düşük likidite + haber reaksiyonu ile dalgalanıyor → yanlış pozitif yüksek. Skor verisi çok daha sağlam bir "bitmiş iş" sinyali.

### Çözüm prensibi
**Fiyat ≠ gerçek.** Çıkış kararları maçın gerçek durumuna (skor) dayansın. Fiyat sadece geç-maç safety net olarak kalsın (elapsed ≥ %70 sonrası).

---

## 2. Hedef Durum (A3)

### Çıkış Kuralları (tam liste)

#### 2.1 Pozitif (kâr-tetikli) — 2 kural
| # | Kural | Tetik | Davranış |
|---|---|---|---|
| P1 | `NEAR_RESOLVE` | eff ≥ 94¢ + min 10dk guard | Tam çıkış |
| P2 | `SCALE_OUT` | entry ile 99¢ arasındaki mesafenin %50'si | %40 kısmi çıkış |

#### 2.2 Skor-tabanlı — 22 kural, 7 spor ailesi

**Tennis (mevcut — değişmez):**
- T1: 0-1 set + 2. set deficit ≥3 (close-set buffer +1, blowout ≥4)
- T1-SFM: 0-1 set + rakip 5+ game (serve-for-match)
- T2: 1-1 set + 3. set deficit ≥3
- T2-SFM: 1-1 set + rakip 5+ game

**Hockey / NHL / AHL (mevcut — `confidence == "A"` gate kaldırılacak):**
- K1: deficit ≥3 (zaman gate yok)
- K2: deficit ≥2 + elapsed ≥67%
- K3: deficit ≥2 + price <0.35 (zaman gate yok)
- K4: deficit ≥1 + elapsed ≥92%

**Baseball / MLB / KBO / NPB (mevcut):**
- M1: inning ≥7 + deficit ≥5
- M2: inning ≥8 + deficit ≥3
- M3: inning ≥9 + deficit ≥1

**Cricket (mevcut):**
- C1: balls_left <30 + RRR >18
- C2: wickets ≥8 + runs_left >20
- C3: balls_left <6 + runs_left >10

**Soccer / Rugby / AFL / Handball (mevcut):**
- 2-gol: minute ≥65 + deficit ≥2
- 1-gol: minute ≥75 + deficit ≥1
- DRAW goal-late: minute ≥75 + herhangi gol
- DRAW knockout auto: minute ≥90 + knockout maç

**NBA (YENİ) — 2 kural:**
- N1: `q3_end_elapsed` + deficit ≥ `nba_late_deficit` (default: elapsed ≥0.75, deficit ≥20)
- N2: `final_elapsed` + deficit ≥ `nba_final_deficit` (default: elapsed ≥0.92, deficit ≥10)

**NFL (YENİ) — 2 kural:**
- N1: `q3_end_elapsed` + deficit ≥ `nfl_late_deficit` (default: elapsed ≥0.75, deficit ≥21)
- N2: `final_elapsed` + deficit ≥ `nfl_final_deficit` (default: elapsed ≥0.92, deficit ≥11)

#### 2.3 Fiyat-tabanlı geç guard — 4 kural
Hepsi geç-maç gate'li, erken fire etmez:
- `NEVER_IN_PROFIT`: elapsed ≥70% + hiç kâra geçmedi + eff_current < entry × 0.75
- `ULTRA_LOW_GUARD`: entry <9¢ + elapsed ≥75% + eff_current <5¢
- `HOLD_REVOKED`: elapsed >60% (ever_profit) / >70% (değilse) + büyük düşüş + skor önde değil
- `MARKET_FLIP`: elapsed ≥85% + eff_current <50¢ (tennis hariç)

### 2.4 Öncelik Zinciri (monitor.py yeni tek-dal akışı)

```
1. NEAR_RESOLVE (positive, önce kâr lock)
2. SCALE_OUT (positive, partial)
3. Sport-specific score exit (tennis/hockey/baseball/cricket/soccer/nba/nfl)
4. MARKET_FLIP (tennis hariç)
5. ULTRA_LOW_GUARD
6. NEVER_IN_PROFIT
7. HOLD_REVOKED
```

İlk tetiklenen kazanır. A-hold / non-A-hold dal ayrımı yok.

### 2.5 MVP Spor Kapsamı

**İçeride (7 spor ailesi, 13 bireysel spor):** NBA, NFL, Hockey (NHL + AHL), Baseball (MLB + KBO + NPB), Tennis, Cricket (tüm ligler), Soccer family (Soccer + Rugby + AFL + Handball).

**Çıkarıldı:**
- **MMA** — canlı skor sistemi yok (judge decision maç sonunda). Entry gate'te reddedilir. TODO-002.
- **Golf** — ESPN canlı score_source yok. Entry gate'te reddedilir. TODO-003.

---

## 3. Silinecekler (Drift Temizliği)

### 3.1 Kod Modülleri
- `src/strategy/exit/stop_loss.py` — flat 7-katman SL
- `src/strategy/exit/graduated_sl.py` — elapsed-aware graduated SL
- `src/strategy/exit/catastrophic_watch.py` — NHL bounce detector
- `src/strategy/exit/a_conf_hold.py` içindeki `is_a_conf_hold()` fonksiyonu (market_flip_exit kalır, dosya içeriği sadeleşir)

### 3.2 Monitor.py Değişiklikleri
- A-hold / non-A-hold `if/else` dal ayrımı → tek dal
- NHL catastrophic bloğu (satır 182-190) → silinir
- Dosya docstring'i yeniden yazılacak (mevcut yapıyı anlatıyor, drift)

### 3.3 Position Modeli
- `catastrophic_watch: bool` alanı → silinir
- `catastrophic_recovery_peak: float` alanı → silinir

### 3.4 Config (sport_rules.py)
**Tüm sporlarda silinecek:** `stop_loss_pct`
**NBA / NFL:** `halftime_exit`, `halftime_exit_deficit`
**NHL:** `period_exit` (Boolean flag; `period_exit_deficit` hockey score exit'te kullanıldığı için KALIR)
**MLB:** `inning_exit`, `inning_exit_deficit`, `inning_exit_after` (eski pre-SPEC-010 key'leri)
**Tennis:** `set_exit` (Boolean flag; sub-key'ler kullanıldığı için kalır)
**Tüm sporlardan:** MMA ve Golf entry'leri tamamen silinir

### 3.5 Config (config.yaml)
- `exit_extras.catastrophic_*` alanları → silinir

### 3.6 Enum (src/models/enums.py)
```python
class ExitReason(str, Enum):
    # KALAN:
    SCALE_OUT = "scale_out"
    NEAR_RESOLVE = "near_resolve"
    NEVER_IN_PROFIT = "never_in_profit"
    MARKET_FLIP = "market_flip"
    HOLD_REVOKED = "hold_revoked"
    ULTRA_LOW_GUARD = "ultra_low_guard"
    SCORE_EXIT = "score_exit"

    # SİLİNECEK:
    # STOP_LOSS
    # GRADUATED_SL
    # CIRCUIT_BREAKER (hiç fire etmemiş — vestigial)
    # MANUAL (implement edilmemiş)
    # CATASTROPHIC_BOUNCE
```

### 3.7 Frontend
- `src/presentation/dashboard/static/js/trade_history_modal.js` — stop_loss, graduated_sl, circuit_breaker, manual, catastrophic_bounce için display label'ları silinir

### 3.8 Dokümantasyon
- TDD §6.8 (graduated SL) → silinir
- TDD §6.9 (A-conf hold) → `is_a_conf_hold` kısmı silinir, `market_flip_exit` kısmı kalır
- SPEC-004 K5 (catastrophic_watch) referansları → arşive taşınır / silinir
- TDD §7.1 / §7.2 → MMA + Golf kaldırılır; NBA + NFL score exit bölümü eklenir
- `monitor.py` dosya docstring'i → yeniden yazılır

---

## 4. Eklenecekler

### 4.1 Yeni Modüller
- `src/strategy/exit/nba_score_exit.py` — N1 + N2 (hockey_score_exit benzeri yapı)
- `src/strategy/exit/nfl_score_exit.py` — N1 + N2 (aynı yapı)

Her iki dosya da pure fonksiyon, I/O yok, config'den threshold okur (magic number yasağı).

### 4.2 Yeni Config Key'leri (sport_rules.py)

**NBA:**
```python
"nba": {
    "match_duration_hours": 2.5,
    "score_source": "espn",
    "espn_sport": "basketball",
    "espn_league": "nba",
    # Score exit N1: Q3 sonu + ağır fark
    "score_exit_n1_elapsed": 0.75,
    "score_exit_n1_deficit": 20,
    # Score exit N2: son dakikalar + iki possession
    "score_exit_n2_elapsed": 0.92,
    "score_exit_n2_deficit": 10,
}
```

**NFL:**
```python
"nfl": {
    "match_duration_hours": 3.25,
    "score_source": "espn",
    "espn_sport": "football",
    "espn_league": "nfl",
    "score_exit_n1_elapsed": 0.75,
    "score_exit_n1_deficit": 21,
    "score_exit_n2_elapsed": 0.92,
    "score_exit_n2_deficit": 11,
}
```

### 4.3 Monitor.py Entegrasyonu

Öncelik zincirinde 3. adıma NBA + NFL branch eklenir:
```python
if _normalize(pos.sport_tag) == "nba" and score_info.get("available"):
    nba_result = nba_score_exit.check(...)
    if nba_result: return MonitorResult(...)

if _normalize(pos.sport_tag) == "nfl" and score_info.get("available"):
    nfl_result = nfl_score_exit.check(...)
    if nfl_result: return MonitorResult(...)
```

### 4.4 Entry Gate
`src/strategy/entry/gate.py` — MMA ve Golf için early reject:
- `sport_tag in {"mma", "golf"}` → skip reason: "sport_not_in_mvp"
- Günlüğe "sport_not_in_mvp" skip istatistiği eklenir (skipped_trades.jsonl)

### 4.5 TODO.md Girişleri
- **TODO-002:** MMA skor-tabanlı exit kuralları. Önkoşul: MMA için canlı skor source bulunmalı (ESPN MMA ham veride round/control data var mı araştırılmalı).
- **TODO-003:** Golf skor-tabanlı exit kuralları. Önkoşul: ESPN golf canlı leaderboard endpoint'i araştırılmalı (veya alternatif provider).

---

## 5. Davranış Kuralları ve Sınır Durumları

### 5.1 score_info.available = False
Hiçbir skor-tabanlı kural fire etmez. Sadece P1/P2/fiyat-tabanlı guard'lar aktif. NBA/NFL pozisyonları için bu → sadece NEAR_RESOLVE + SCALE_OUT + NEVER_IN_PROFIT + ULTRA_LOW + HOLD_REVOKED + MARKET_FLIP görür (skor yoksa geç-maç fiyat guard'ları sağlar).

### 5.2 Elapsed hesaplanamıyor (match_start_iso bozuk)
`compute_elapsed_pct` -1.0 döndürür. Elapsed gate'li tüm kurallar skip edilir (erken fire güvenli tarafta kalır). Sadece zaman-gate'siz kurallar (Tennis T1/T2, Hockey K1/K3) çalışır.

### 5.3 NBA deficit 0 veya negatif (önde/eşit)
`nba_score_exit.check` None döndürür (exit yok).

### 5.4 NFL overtime
Overtime'da elapsed 1.0'ı aşabilir. N1/N2 gate'leri zaten aşıldığı için OT deficit büyürse fire edebilir. Bu istenen davranış (OT'de 10+ deficit ≈ maç bitti).

### 5.5 Market flip + tennis istisnası
Tennis'te set kaybı fiyatı düşürür (0.50 altına) ama maç dönebilir → MARKET_FLIP tennis'te fire etmez. Bu mevcut davranış korunur.

### 5.6 Historical trade data
`trade_history.jsonl` dosyasında `STOP_LOSS`, `GRADUATED_SL`, `CATASTROPHIC_BOUNCE` reason'lı kayıtlar var. Enum'dan silince:
- Yazma artık bu değerleri üretmez ✓
- Okuma: dashboard string-based display kullanıyor, enum lookup değil → kırılmaz
- Pydantic validation: `ExitReason(string_value)` kayıt okurken patlar → `Optional[ExitReason]` veya `str` olarak fallback tut

**Karar:** ExitReason field'ı `str` olarak kalsın (Polymarket bot zaten string tutuyor JSONL'de). Silinen enum değerler sadece yazma tarafında kullanılmıyor; okuma tarafı string karşılaştırma yapıyor. Kırılma yok.

### 5.7 Scale-out tier sayısı (drift doğrulama)
Config tek tier: threshold 0.50, sell_pct 0.40. monitor.py docstring "25%/40% + 50%/50%" diyordu — silinir, "tek tier: midpoint %40" yazılır.

---

## 6. Test Senaryoları

### 6.1 Silme regression testleri
- `tests/unit/strategy/exit/test_stop_loss.py` → silinir
- `tests/unit/strategy/exit/test_graduated_sl.py` → silinir
- `tests/unit/strategy/exit/test_catastrophic_watch.py` (varsa) → silinir
- `tests/unit/strategy/exit/test_monitor.py` → A-hold dal testleri silinir, tek-dal testleri güncellenir
- `tests/unit/models/test_enums.py` → silinen değerler için testler kaldırılır

### 6.2 Yeni NBA testleri (`tests/unit/strategy/exit/test_nba_score_exit.py`)
- N1 tetiklenir: elapsed 0.76 + deficit 20 → SCORE_EXIT
- N1 tetiklenmez (early): elapsed 0.74 + deficit 25 → None
- N1 tetiklenmez (küçük deficit): elapsed 0.80 + deficit 19 → None
- N2 tetiklenir: elapsed 0.93 + deficit 10 → SCORE_EXIT
- N2 tetiklenmez (early): elapsed 0.91 + deficit 15 → None
- N2 tetiklenmez (küçük deficit): elapsed 0.95 + deficit 9 → None
- Deficit 0 veya negatif → None
- score_info.available = False → None

### 6.3 Yeni NFL testleri (`tests/unit/strategy/exit/test_nfl_score_exit.py`)
- N1: elapsed 0.76 + deficit 21 → SCORE_EXIT
- N1 early reject: elapsed 0.74 + deficit 25 → None
- N2: elapsed 0.93 + deficit 11 → SCORE_EXIT
- N2 early reject: elapsed 0.91 + deficit 15 → None
- Deficit 0 → None
- Overtime: elapsed 1.05 + deficit 14 → N2 fire (doğru davranış)

### 6.4 Monitor.py entegrasyon testleri
- NBA + skor mevcut + N1 koşulu → SCORE_EXIT (diğer kurallar skip)
- NFL + skor yok → MARKET_FLIP fallback (elapsed ≥0.85 + eff<0.50)
- Tennis + T1 tetikliyor + elapsed 0.40 → erken fire etsin (KALSIN kararı)
- Hockey + K1 tetikliyor + confidence "B" → fire etsin (A-gate kaldırıldı)

### 6.5 Entry gate testleri
- MMA pozisyonu entry denemesi → SKIP, reason "sport_not_in_mvp"
- Golf pozisyonu entry denemesi → SKIP, reason "sport_not_in_mvp"
- Diğer 8 spor ailesi → normal gate akışı (regression yok)

### 6.6 Drift temizlik doğrulama
Silme sonrası grep kontrolü:
- `grep -r "stop_loss_pct" src/` → 0 sonuç
- `grep -r "graduated_sl" src/` → 0 sonuç
- `grep -r "catastrophic_bounce\|CATASTROPHIC_BOUNCE" src/` → 0 sonuç
- `grep -r "catastrophic" src/` → 0 sonuç
- `grep -r "halftime_exit\|period_exit\"\|inning_exit\"\|set_exit\"" src/config/` → 0 sonuç

---

## 7. Mimari Uyum

- **Kural 1 (katman)**: Yeni modüller `src/strategy/exit/` altında — doğru katman ✓
- **Kural 2 (domain I/O)**: NBA/NFL score exit pure function, hiçbir I/O yok ✓
- **Kural 3 (400 satır)**: Her yeni dosya ~100 satır tahmini ✓
- **Kural 6 (magic number)**: Tüm threshold'lar config'den okunur ✓
- **Kural 7 (P(YES))**: Bu spec anchor probability'e dokunmaz ✓
- **Kural 8 (event-guard)**: Bu spec giriş mantığına dokunmaz ✓
- **Kural 9 (dizin yapısı)**: Yeni dosyalar mevcut `src/strategy/exit/` dizinine ✓
- **Kural 11 (test)**: Her yeni modül için test dosyası yazılır ✓
- **Kural 12 (hata)**: Domain'de try/except yok, saf fonksiyonlar ✓

---

## 8. Açık Sorular

Yok. Tüm kararlar brainstorming turunda netleşti:
- NBA/NFL eşikleri konservatif (erken fire etmez): 20/10 ve 21/11
- Mevcut 3 erken-fire kuralı (Tennis T1, Hokey K1/K3) kalır
- MMA + Golf kapsamdan çıkar (TODO'ya)
- Tüm drift silmeler onaylı

---

## 9. Uygulama Sırası (Özet)

1. NBA + NFL score exit modüllerini yaz (test-driven)
2. monitor.py'yi tek-dal akışa dönüştür
3. Silme turu: stop_loss.py, graduated_sl.py, catastrophic_watch.py + Position field'ları
4. Enum sadeleştir
5. Config temizliği (sport_rules.py + config.yaml)
6. Entry gate MMA/Golf reject
7. Frontend (JS) label'ları temizle
8. Dokümantasyon (TDD §6.8/§6.9, SPEC-004 K5, §7.1/§7.2)
9. TODO.md'ye TODO-002 + TODO-003 ekle
10. Test regression (pytest -q tümü geçer)
11. Grep verification (drift temizliği)

Ayrıntılı plan için `writing-plans` skill'ine geçilecek.
