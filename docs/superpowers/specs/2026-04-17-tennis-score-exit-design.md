# SPEC-006: Tennis Score-Based Exit (T1-T2)

> **Tarih:** 2026-04-17
> **Durum:** DRAFT
> **Bağımlılık:** SPEC-005 (ESPN Score Client — IMPLEMENTED)
> **Kapsam:** Sadece BO3 tennis (ATP/WTA). BO5 (Grand Slam) gelecek SPEC.

---

## Amaç

Tennis A-conf hold pozisyonlarda set/game skoru kullanarak kaybedilen maçlardan
erken çıkış. Mevcut durumda tennis'te market_flip ve catastrophic watch DISABLED —
dead token (≤2¢) tek koruma. Bu SPEC, maç bitmeden 15-20¢ seviyesinde çıkış
sağlayarak kayıp başına ~$10-15 tasarruf eder.

---

## Kurallar

### T1 — Straight Set Kaybı Yaklaşıyor

```
Koşul: sets_lost == 1 AND sets_won == 0          (0-1 set geride)
       AND (
           (current_set_deficit >= 3 AND current_set_games_total >= 7)
           OR current_set_deficit >= 4
       )
Aksiyon: FULL EXIT
Dönüş ihtimali: %3-8
```

**Tiebreak koruması:** 1. set tiebreak'le kaybedildiyse (skor 6-7 veya 7-6 rakibe)
→ "dar kayıp", deficit eşiği +1 artar (3→4). Böylece 2-5'te çıkmaz, 1-5'te çıkar.
Blowout kaybı (≤4 game alınan set, ör: 2-6, 3-6) → buffer uygulanmaz.

Gerekçe: Tiebreak kaybından sonra %30-35 dönüş olasılığı, blowout sonrası %15-20.

### T2 — Decider Set Kaybı

```
Koşul: sets_lost == 1 AND sets_won == 1          (1-1, decider sette)
       AND (
           (current_set_deficit >= 3 AND current_set_games_total >= 7)
           OR current_set_deficit >= 4
       )
Aksiyon: FULL EXIT
Dönüş ihtimali: %5-8
```

T2'de tiebreak buffer uygulanmaz — 3. set zaten decider, tolerans yok.

---

## Linescores Parse Mantığı

ESPN `score_info.linescores` formatı: `[[h1, a1], [h2, a2], ...]`

```python
linescores = [[6, 3], [2, 5]]  # 1. set: 6-3 (biz kazandık), 2. set: 2-5 (kaybediyoruz)
```

Direction-aware: score_enricher zaten `our_score/opp_score` hesaplıyor ama linescores
ham ESPN verisi (home/away). `tennis_exit` direction mapping yapmalı:

```
completed_sets = linescores[:-1]     # bitmiş setler
current_set = linescores[-1]         # devam eden set (son eleman)
sets_won = count(our > opp for completed sets)
sets_lost = count(opp > our for completed sets)
current_set_our = current_set mapping
current_set_opp = current_set mapping
deficit = current_set_opp - current_set_our
games_total = current_set_our + current_set_opp
```

**Mapping:** `score_info` zaten direction-aware `our_score/opp_score` veriyor.
Ama linescores ham — direction mapping `tennis_exit.py` içinde yapılır.
`score_info["our_is_home"]` flag'i ile home/away → our/opp çevrilir.

---

## Config (sport_rules.py)

```python
"tennis": {
    # ... mevcut alanlar ...
    "set_exit_deficit": 3,
    "set_exit_games_total": 7,
    "set_exit_blowout_deficit": 4,
    "set_exit_close_set_threshold": 5,
    "set_exit_close_set_buffer": 1,
}
```

| Config key | Değer | Açıklama |
|---|---|---|
| `set_exit_deficit` | 3 | T1/T2 minimum game fark |
| `set_exit_games_total` | 7 | T1/T2 minimum toplam game (deficit < 4 ise) |
| `set_exit_blowout_deficit` | 4 | Deficit ≥ 4 → games_total şartı kalkar |
| `set_exit_close_set_threshold` | 5 | Set kazananın aldığı game ≥ 5 → close set (ör: 5-7, 6-7) |
| `set_exit_close_set_buffer` | 1 | Close set kaybı → T1 deficit eşiği +1 |

---

## Monitor.py Entegrasyonu

Mevcut A-conf hold dalında, hockey score_exit'ten sonra:

```python
# 3a. Score-based exit — hockey (mevcut, satır ~178)
if _normalize(pos.sport_tag) == "nhl" and score_info.get("available"):
    sc_result = score_exit.check(...)

# 3a-tennis. Score-based exit — tennis (YENİ)
if _normalize(pos.sport_tag) == "tennis" and score_info.get("available"):
    t_result = tennis_exit.check(
        score_info=score_info,
        current_price=pos.current_price,
        sport_tag=pos.sport_tag,
    )
    if t_result is not None:
        return MonitorResult(
            exit_signal=ExitSignal(reason=t_result.reason, detail=t_result.detail),
            ...)
```

**Priority zinciri (tennis A-conf hold):**
1. Near-resolve (≥94¢) — mevcut
2. Scale-out — mevcut
3. Dead token (≤2¢) — mevcut (near_resolve içinde)
4. **Tennis score exit T1/T2** — YENİ (bu SPEC)
5. Market flip — DISABLED (tennis)
6. Catastrophic watch — DISABLED (tennis)

---

## score_info Direction Mapping

`score_enricher.py` zaten `our_score/opp_score` hesaplıyor ama `linescores`
ham ESPN verisi (home/away sırasıyla). Tennis exit'in direction-aware linescores'a
ihtiyacı var.

**Çözüm:** `_build_espn_score_info` veya `_build_score_info`'da `our_is_home` flag'i
ekle. `tennis_exit.py` bunu kullanarak linescores'u `[[our, opp], ...]` olarak okur.

```python
# score_info'ya eklenen field:
"our_is_home": bool  # True → linescores[i][0] = bizim, False → linescores[i][1] = bizim
```

---

## Test Stratejisi

### Yeni test dosyası: `tests/unit/strategy/exit/test_tennis_exit.py`

| Test | Senaryo | Beklenen |
|---|---|---|
| `test_t1_straight_set_2_5` | 0-1 set + 2-5 game | EXIT |
| `test_t1_early_deficit_1_4` | 0-1 set + 1-4 (total 5) | HOLD |
| `test_t1_deficit_4_any_total` | 0-1 set + 0-4 (deficit 4) | EXIT |
| `test_t1_close_set_buffer` | 1. set 6-7 tiebreak + 2-5 game | HOLD (buffer) |
| `test_t1_blowout_no_buffer` | 1. set 2-6 + 2-5 game | EXIT |
| `test_t2_decider_2_5` | 1-1 set + 2-5 game | EXIT |
| `test_t2_decider_deficit_2` | 1-1 set + 3-5 (deficit 2) | HOLD |
| `test_no_score_no_exit` | available=False | HOLD |
| `test_winning_no_exit` | 1-0 set + öndeyiz | HOLD |
| `test_monitor_tennis_exit_wired` | monitor.py'den tetiklenir | EXIT |

### Mevcut testler — kırılmamalı
- `test_tennis_immune_to_market_flip` ✅
- `test_tennis_immune_to_catastrophic_watch` ✅
- `test_dead_token_exit_at_near_zero` ✅

---

## Tamamlanma Kriterleri

1. `pytest tests/ -q` → tümü green
2. T1 straight set yaklaşırken exit tetiklenir
3. T2 decider sette exit tetiklenir
4. Tiebreak buffer doğru çalışır (6-7 → tolerant, 2-6 → agresif)
5. Deficit ≥ 4 → games_total şartsız exit
6. Config-driven eşikler (magic number yok)
7. Mevcut 775+ test kırılmaz

---

## Dosya Haritası

| Dosya | Aksiyon | Sorumluluk |
|---|---|---|
| `src/strategy/exit/tennis_exit.py` | CREATE | T1/T2 pure fonksiyon |
| `tests/unit/strategy/exit/test_tennis_exit.py` | CREATE | 9 birim test |
| `src/strategy/exit/monitor.py` | MODIFY | Tennis exit çağrısı ekle |
| `tests/unit/strategy/exit/test_monitor.py` | MODIFY | Integration test ekle |
| `src/config/sport_rules.py` | MODIFY | Tennis exit config |
| `src/orchestration/score_enricher.py` | MODIFY | `our_is_home` flag ekle |

---

## Kapsam Dışı

- BO5 (Grand Slam) kuralları
- Soft exit (fiyat-skor combo)
- Servis bilgisi (ESPN'de yok)
- Tier 2 fiyat-skor combo kuralları
