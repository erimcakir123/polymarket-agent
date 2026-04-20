# SPEC-008: Tennis Score Exit Fix

> **Durum**: DRAFT
> **Tarih**: 2026-04-18
> **Katman**: strategy + orchestration
> **Scope**: tennis exit bug fix + kural iyileştirme — bot core akışı değişmez

---

## 1. Sorun Tanımı

### Bug A — Yanlış ESPN Maç Eşleşmesi (Kritik)

`score_enricher.py` → `_find_espn_match()` fonksiyonundaki fallback koşulu
`(home_a or away_a)` sadece tek oyuncuyu kontrol ediyor. İki takımlı bir
pozisyon (team_b mevcut) için eski/tamamlanmış maçı döndürebiliyor.

**Kanıt:** "Rafael Jodar vs Arthur Fils" pozisyonu (2026-04-18):
- Maç S1 3-3'te (canlı, deficit yok)
- Bot dünkü "Cameron Norrie vs Rafael Jodar" (tamamlanmış) maçını eşleştirdi
- Tamamlanmış maçın linescores'u T1 exit tetikledi
- Bot 1-2 saniyede 4 kez giriş-çıkış yaptı (feedback loop)

**Etki:** 4× $38 = $152 gereksiz işlem hacmi, $0 PnL (dry_run).

### Bug B — T1/T2 Serve-for-Match Eksik

Maç bitirici sette (set 2 when 0-1, set 3 when 1-1) rakip 5 game'e ulaştığında
bot çıkmıyor. Rakip bir game daha alıp seti/maçı bitiriyor → büyük kayıp.

**Mevcut kural:** deficit ≥ 3 + games_total ≥ 7 (veya deficit ≥ 4 blowout).
3-5'te (deficit=2) tetiklenmiyor. Rakip 6-3 yapıyor, maç bitiyor.

---

## 2. Fix A — `_find_espn_match` Eşleşme Düzeltmesi

### Değişiklik

`score_enricher.py` satır 85, tek satır:

```python
# ESKİ (buggy):
if (home_a and away_b) or (home_b and away_a) or (home_a or away_a):

# YENİ:
if (home_a and away_b) or (home_b and away_a) or (not team_b and (home_a or away_a)):
```

### Mantık

- **İki takımlı pozisyon** (team_b var): SADECE iki taraflı eşleşme kabul et.
  `(home_a and away_b)` veya `(home_b and away_a)` — her iki oyuncu eşleşmeli.
- **Tek takımlı pozisyon** (team_b yok): Mevcut fallback korunur
  `(home_a or away_a)` — bu durum golf/tek isimli piyasalar için gerekli.

### Etkilenen Dosya

| Dosya | Satır | Değişiklik |
|---|---|---|
| `score_enricher.py` | 85 | Koşul güncelleme (1 satır) |

---

## 3. Fix B — Serve-for-Match Kuralı

### Kural

**Maç bitirici sette rakip ≥ 5 game + deficit > 0 → ÇIK.**

Maç bitirici set = kaybedilirse maçın biteceği set:
- **T1 (0-1 set):** Set 2 maç bitirici (kaybedilirse 0-2 → maç biter)
- **T2 (1-1 set):** Set 3 maç bitirici (kaybedilirse 1-2 → maç biter)

### Örnekler

| Senaryo | Skor | Deficit | Rakip≥5? | Sonuç |
|---|---|---|---|---|
| T2 decider | 4-5 | 1 | ✓ | **ÇIK** (yeni) |
| T2 decider | 3-5 | 2 | ✓ | **ÇIK** (yeni) |
| T2 decider | 2-5 | 3 | ✓ | ÇIK (mevcut kural zaten tetikler) |
| T2 decider | 3-4 | 1 | ✗ | HOLD (rakip henüz 5'e ulaşmadı) |
| T2 decider | 5-5 | 0 | — | HOLD (deficit≤0, geride değiliz) |
| T1 straight | 4-5 | 1 | ✓ | **ÇIK** (yeni) |
| T1 straight | 3-5 | 2 | ✓ | **ÇIK** (yeni) |
| T1 straight | 4-4 | 0 | — | HOLD (deficit≤0) |

### Neden Bu Eşik

Rakip 5'e ulaştığında seti bitirmek için 1 game lazım:
- 3-5 → rakip servis tutar → 3-6 maç biter (dönüş ihtimali ~%8)
- 4-5 → rakip servis tutar → 4-6 maç biter (dönüş ihtimali ~%15)
- 5-5 olsa bile → tiebreak riski (ama deficit=0, çıkmıyoruz)

Kalan dönüş ihtimali risk/ödül dengesine değmez.

### Implementasyon

`tennis_exit.py` → `check()` fonksiyonunda T1 ve T2 bloklarına
`_should_exit` çağrısından ÖNCE:

```python
serve_for_match_games = int(get_sport_rule(sport_tag, "set_exit_serve_for_match_games", 5))

# T1 (0-1 set) — set 2 maç bitirici
if sets_won == 0 and sets_lost == 1:
    if current_opp >= serve_for_match_games and deficit > 0:
        return TennisExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"T1-SFM: sets=0-1 game={current_our}-{current_opp}",
        )
    # ... mevcut threshold mantığı ...

# T2 (1-1 set) — set 3 maç bitirici
if sets_won == 1 and sets_lost == 1:
    if current_opp >= serve_for_match_games and deficit > 0:
        return TennisExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"T2-SFM: sets=1-1 game={current_our}-{current_opp}",
        )
    # ... mevcut threshold mantığı ...
```

### Config

`sport_rules.py` → tennis dict'ine:

```python
"set_exit_serve_for_match_games": 5,
```

### Etkilenen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `tennis_exit.py` | SFM koşulu ekleme (T1 + T2 bloklarına ~4+4 satır) |
| `sport_rules.py` | Yeni config parametresi (+1 satır) |

---

## 4. Fix C — Trade History Temizliği

### Sorun

`trade_history.jsonl`'de 3 adet hayalet trade var:

| Entry | Exit | Süre | PnL | Sebep |
|---|---|---|---|---|
| 14:07:04 | 14:07:05 | 1sn | $0 | Bug A (yanlış eşleşme) |
| 14:09:20 | 14:09:22 | 2sn | $0 | Bug A (yanlış eşleşme) |
| 14:11:35 | 14:11:36 | 1sn | $0 | Bug A (yanlış eşleşme) |

4\. trade (14:14→14:25, +$2.62) gerçek — kalır.

### Aksiyon

Bu 3 satırı `trade_history.jsonl`'den sil. Dashboard otomatik düzelir
(tüm paneller bu dosyadan besleniyor).

---

## 5. Doküman Güncellemeleri

### TDD.md §6.9d

Mevcut metin sonuna ekleme:

```
**Serve-for-match (SFM):** Maç bitirici sette (T1: set 2 when 0-1, T2: set 3
when 1-1) rakip ≥ 5 game + gerideyiz → çık. Config: `set_exit_serve_for_match_games`.
Deficit eşiği ve games_total kontrolü bu durumda atlanır — rakip seti/maçı
bitirmek için 1 game uzakta, dönüş ihtimali %8-15.
```

---

## 6. Test Senaryoları

### Fix A testleri (`tests/unit/orchestration/test_score_enricher.py` veya mevcut test)

- `test_find_espn_match_skips_wrong_match_same_player`: İki takımlı
  pozisyon (A vs B) için sadece A'yı içeren farklı maçı eşleştirmez
- `test_find_espn_match_single_team_fallback_still_works`: Tek takımlı
  pozisyon için fallback koşulu hâlâ çalışır

### Fix B testleri (`tests/unit/strategy/exit/test_tennis_exit.py`)

- `test_t2_serve_for_match_opp_5_deficit_1_exits`: 1-1 set, 4-5 → ÇIK
- `test_t2_serve_for_match_opp_5_deficit_2_exits`: 1-1 set, 3-5 → ÇIK
- `test_t2_serve_for_match_opp_4_deficit_1_holds`: 1-1 set, 3-4 → HOLD
- `test_t1_serve_for_match_opp_5_deficit_1_exits`: 0-1 set, 4-5 → ÇIK
- `test_serve_for_match_no_deficit_holds`: 1-1 set, 5-5 → HOLD (deficit=0)

---

## 7. Dosya Değişiklik Özeti

| Dosya | İşlem | Satır |
|---|---|---|
| `score_enricher.py` | Koşul fix (1 satır) | ~0 net |
| `tennis_exit.py` | SFM koşulu ekleme | +10 |
| `sport_rules.py` | Yeni config | +1 |
| `TDD.md` | §6.9d güncelleme | +3 |
| `trade_history.jsonl` | 3 hayalet trade silme | -3 |
| `test_tennis_exit.py` | Yeni test senaryoları | +30 |
| `test_score_enricher.py` (yeni veya mevcut) | Eşleşme testleri | +20 |
| **Toplam** | | ~+60 |

Tüm dosyalar 400 satır altında. Katman ihlali yok. Magic number yok (config'den).
