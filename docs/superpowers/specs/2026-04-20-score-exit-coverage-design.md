# SPEC — Score-Exit Coverage Bug Fixes

**Tarih**: 2026-04-20
**Durum**: IMPLEMENTED (2026-04-20)
**Bağlam**: 2026-04-19 trade audit'inde 14 kapanan/açık trade incelendi; score-exit kuralları eksik veya hiç tetiklenmiyor olarak tespit edildi.

---

## 1. Problem

`logs/trade_history.jsonl` ve `logs/archive/exits.jsonl` audit'inde tespit edilen 3 bug:

### Bug #1 — AHL score-exit yok
- `pos.sport_tag = "ahl"` Position'da kaydediliyor (örn. `ahl-leh-cha-2026-04-19`).
- `_normalize("ahl")` → `""` döner çünkü:
  - `SPORT_RULES` içinde `"ahl"` key yok ([sport_rules.py:10-89](../../../src/config/sport_rules.py#L10-L89))
  - `_ALIASES` içinde sadece `"icehockey_ahl": "nhl"` var (Odds API key formatı, sport_tag değil)
- Sonuç: `get_sport_rule("ahl", ...)` → `DEFAULT_RULES`. Hockey K1-K4 eşikleri AHL pozisyonlara uygulanmıyor.
- monitor.py'daki `_normalize(pos.sport_tag) == "nhl"` ([monitor.py:188](../../../src/strategy/exit/monitor.py#L188)) `False` döner → `hockey_score_exit.check` çağrılmıyor.

### Bug #2 — MLB M1/M2/M3 hiç tetiklenmez
- ESPN client `_parse_competition` ([espn_client.py:107](../../../src/infrastructure/apis/espn_client.py#L107)) `status.type.description` → `period` field'ına yazıyor.
- ESPN MLB için `description` "In Progress" / "Top of 5th" formatında değişkenlik gösteriyor; **archive doğrulaması**: `logs/archive/score_events.jsonl` line 16-21 (MLB) → `"period":""` (boş).
- baseball_score_exit `_parse_inning` regex `(\d+)(?:st|nd|rd|th)` matchlemez → `inning=None` → check erken return.
- Sonuç: M1/M2/M3 (blowout/late-deficit/final-inning) **hiç tetiklenemez**. 0-19 audit'inde `mlb-cws-oak` deficit 0-4'e ulaştı, score-exit denenemedi → stop_loss ile çıktı.

### Bug #3 — `score_at_exit` arşivde tamamen boş
- `Position` modelinde `match_score: str = ""` ve `match_period: str = ""` alanları tanımlı ([position.py:56-57](../../../src/models/position.py#L56-L57)).
- `score_enricher.get_scores_if_due` sadece `dict[cid → score_info]` döndürüyor; **pozisyon state'ini güncellemiyor**.
- `exit_processor._log_exit_to_archive` ([exit_processor.py:207-208](../../../src/orchestration/exit_processor.py#L207-L208)) `pos.match_score or ""` okuyor → her exit'te `""` yazılıyor.
- Audit doğrulaması: `logs/archive/exits.jsonl` 13/13 kayıtta `"score_at_exit":""`, `"period_at_exit":""`. SPEC-009'un retrospektif analiz amacı baltalanmış.

---

## 2. Çözüm

### Fix #1 — AHL hockey ailesine bağlanır

İki değişim:

**(a) `src/config/sport_rules.py`** — SPORT_RULES'a "ahl" bloğu eklenir. NHL eşiklerini paylaşır, sadece `espn_league` farklı:

```python
"ahl": {
    **SPORT_RULES["nhl"],         # period_exit, period_exit_deficit, late_*, K1-K4 eşikleri
    "espn_league": "ahl",         # ESPN AHL endpoint
},
```

`_ALIASES`'a dokunulmaz (sport_tag zaten "ahl" geliyor; alias gereksiz). NHL eşikleri spread ile paylaşıldığından eşik drift'i imkansız.

**(b) Hockey family helper** — DRY için yeni helper:

`hockey_score_exit._is_hockey` ([hockey_score_exit.py:23-24](../../../src/strategy/exit/hockey_score_exit.py#L23-L24)) `_is_hockey_family` olarak yeniden adlandırılır:

```python
_HOCKEY_FAMILY: frozenset[str] = frozenset({"nhl", "ahl"})

def _is_hockey_family(sport_tag: str) -> bool:
    return _normalize(sport_tag) in _HOCKEY_FAMILY
```

`monitor.py:188` `_normalize(pos.sport_tag) == "nhl"` koşulu `_is_hockey_family(pos.sport_tag)` çağrısına dönüştürülür (import + 1 satır değişim). İleride bir hokey ligi daha eklenirse tek yerden büyür.

### Fix #2 — MLB inning parse

ESPN MLB API response'u inceleyerek inning bilgisinin **`status.period`** (sayısal: 1-9+) field'ında taşındığı bilinmektedir; `status.type.description` ise dilsel ("Top 5th", "In Progress", "End of 7th"). En güvenilir kaynak `status.period` (int).

**Plan adımı**: ESPN response'u canlı bir MLB maçında doğrula (diag script). Doğrulama sonucu plan içinde değişebilir; SPEC bu varsayım üzerine yazılmıştır.

**Değişiklikler**:

1. `ESPNMatchScore` dataclass'ına `inning: int | None = None` field eklenir.
2. `_parse_competition`'da MLB için (sport=`baseball`):
   ```python
   raw_period = status_block.get("period")
   inning = int(raw_period) if raw_period is not None else None
   ```
   Diğer sporlar için `inning = None` (kullanılmaz).
3. `score_enricher._build_score_info` `inning` field'ını score_info dict'ine ekler:
   ```python
   "inning": getattr(ms, "inning", None),
   ```
4. `baseball_score_exit.check` artık `score_info.get("inning")` okur, `_parse_inning` ve regex tamamen silinir.
5. Eski `_INNING_RE` ve `_parse_inning` ölü kod → silinir (clean).

### Fix #3 — score_at_exit doğru yazımı

`score_enricher._match_cached` ([score_enricher.py:290-327](../../../src/orchestration/score_enricher.py#L290-L327)) içinde, eşleşen score bulunduğunda **pozisyona da yazılır**:

```python
if matched_score_obj is not None:
    pos.match_score = f"{matched_score_obj.home_score}-{matched_score_obj.away_score}"
    pos.match_period = getattr(matched_score_obj, "period", "") or ""
    self._maybe_log_score_event(pos, matched_score_obj)
    self._maybe_log_match_result(pos, matched_score_obj)
```

**Mimari değerlendirme**:
- `score_enricher` orchestration katmanında — Position state mutasyonu doğal sorumluluğudur.
- `_build_score_info` saf kalır (yan etki yok).
- Pozisyon zaten bu field'lar için tanımlı — eklemenin kendisi değil, **kullanılmama** anti-pattern'di.

`exit_processor._log_exit_to_archive` ([exit_processor.py:207-208](../../../src/orchestration/exit_processor.py#L207-L208)) zaten `pos.match_score or ""` okuyor; **kod değişikliği gerekmez** — sadece artık dolu gelir.

---

## 3. Kapsam dışı

- **NBA score-exit**: Audit'te NBA için score-exit kuralı yok (sport_rules NBA bloğunda `halftime_exit_deficit:15` var ama monitor'da çağrılmıyor). Bu ayrı SPEC konusu, bu PR'a girmez.
- **Tennis score-exit**: Çalışıyor (T1/T2 aktif); sadece audit'teki 2 trade near_resolve önce tetiklendiği için kontrol edilemedi. Davranış doğru.
- **Cricket score-exit**: Bu oturumda cricket trade yok; SPEC-011 kapsamında ayrıca verifiye edildi.
- **ESPN AHL endpoint canlılığı**: AHL ESPN endpoint var (`hockey/ahl`); response yapısı NHL ile aynı. Plan adımında diag ile doğrulanır.

---

## 4. Etkilenen dosyalar

| Dosya | Değişim | Tahmini diff |
|---|---|---|
| `src/config/sport_rules.py` | SPORT_RULES'a "ahl" bloğu (NHL spread + espn_league) | +5 satır |
| `src/strategy/exit/hockey_score_exit.py` | `_is_hockey` → `_is_hockey_family` (set check) | ~3 satır |
| `src/strategy/exit/monitor.py` | `== "nhl"` → `_is_hockey_family(tag)` (import + 1 yer) | ~2 satır |
| `src/infrastructure/apis/espn_client.py` | `ESPNMatchScore.inning` + parse | +5 satır |
| `src/orchestration/score_enricher.py` | `_build_score_info` inning geçir + `_match_cached` pos.match_score yazsın | +6 satır |
| `src/strategy/exit/baseball_score_exit.py` | `_parse_inning`/regex silinir, `score_info["inning"]` okunur | ~-15, +5 satır |
| `tests/unit/config/test_sport_rules.py` | AHL alias + NHL eşik paylaşımı testi | +20 satır |
| `tests/unit/infrastructure/apis/test_espn_client.py` | MLB inning parse testi | +30 satır |
| `tests/unit/orchestration/test_score_enricher.py` | pos.match_score/period yazılma testi | +25 satır |
| `tests/unit/strategy/exit/test_baseball_score_exit.py` | inning input formatı değişikliği (regex değil int) | ~-20, +20 satır |
| `tests/unit/strategy/exit/test_hockey_score_exit.py` | AHL sport_tag ile K1-K4 testi | +30 satır |
| `tests/unit/strategy/exit/test_monitor.py` | AHL → hockey_score_exit çağrılma testi | +20 satır |
| `TDD.md` §7.2 | AHL → NHL hockey kuralları paylaşımı; baseball inning kaynağı "ESPN status.period" | ~5 satır |

**Dokunulmayan**:
- PRD.md (demir kural değişmiyor; davranış zaten "score-exit kuralları çalışır" olarak yazılı)
- ARCHITECTURE_GUARD.md (yapısal invariant değişmiyor)
- TODO.md (yeni TODO oluşmaz)

---

## 5. Test stratejisi

Her fix için failing test → impl → green:

1. **AHL sport rules**:
   - `test_get_sport_rule_ahl_inherits_nhl_thresholds()` — `period_exit_deficit == 3`, `late_deficit == 2`, `final_elapsed_gate == 0.92`
   - `test_ahl_has_own_espn_league()` — `get_sport_rule("ahl", "espn_league") == "ahl"`
   - `test_normalize_ahl_returns_ahl()` — `_normalize("ahl") == "ahl"` (kendi key'i)

2. **Hockey family**:
   - `test_is_hockey_family_includes_nhl_and_ahl()` — pure function test
   - `test_monitor_calls_hockey_score_exit_for_ahl()` — A-conf AHL pos + score_info.deficit=3 → SCORE_EXIT signal

3. **MLB inning**:
   - `test_espn_client_parses_mlb_inning_from_status_period()` — synthetic ESPN response → `inning == 7`
   - `test_baseball_score_exit_reads_inning_field()` — score_info["inning"]=7, deficit=5 → M1
   - `test_baseball_score_exit_returns_none_when_inning_missing()` — None inning → None result

4. **score_at_exit**:
   - `test_score_enricher_writes_match_score_to_position()` — _match_cached çağrısı sonrası pos.match_score == "3-1"
   - `test_score_enricher_writes_match_period_to_position()` — pos.match_period == "Top 5th"

Mevcut testlerden bozulanlar (`test_baseball_score_exit.py`'da `period="Top 7th"` kullananlar) → `score_info["inning"]=7` formatına migrate edilir.

---

## 6. Doğrulama (Adım 6 — CLAUDE.md Kural Değişikliği Protokolü §6)

- `pytest -q` → tüm testler geçer
- `grep -rn "_parse_inning\|_INNING_RE" src/` → 0 sonuç (ölü kod silindi)
- `grep -rn '"score_at_exit":""' logs/archive/exits.jsonl` → mevcut 13 kayıt korunur (geçmiş audit), yeni exit'lerde dolu gelir
- `grep -rn "_normalize.*== .nhl." src/` → 0 sonuç (helper'a taşındı)

---

## 7. Riskler

| Risk | Önlem |
|---|---|
| ESPN MLB `status.period` varsayımı yanlış olabilir | Plan Task 1'de canlı diag (`scripts/diag_mlb_espn.py` benzeri) — varsayım yanlışsa `status.type.detail` regex fallback |
| AHL ESPN endpoint farklı response yapısı | Plan'da synthetic test fixture + opsiyonel canlı diag |
| `pos.match_score` yazımı pure fonksiyon prensibini bozar görünür | `_build_score_info` saf kalır; mutation `_match_cached` (orchestration) içinde — katman izni var |

---

## 8. Tamamlama kriterleri

- [x] 4 yeni unit test grubu yeşil
- [x] Mevcut baseball_score_exit testleri yeni signature'a migrate
- [x] AHL pozisyonunda K1 (deficit=3) tetiklenmesi monitor unit testi ile doğrulanır
- [x] MLB pozisyonunda M1 (inning=7, deficit=5) tetiklenmesi monitor unit testi ile doğrulanır
- [x] Yeni bir exit kaydı `score_at_exit` field'ı dolu yazar (integration test veya synthetic flow)
- [x] TDD §7.2 güncellenir
- [x] ARCH_GUARD self-check her commit öncesi atılır

---

## Implementation Commits

- 838259c: Task 1 — ESPN MLB inning from status.period, baseball_score_exit rewrite
- 13d2e4c: Task 2 — AHL hockey family (SPORT_RULES spread + _is_hockey_family)
- 852135d: Task 3 — score_at_exit writing in _match_cached
- (this commit): Task 4 — TDD update + spec IMPLEMENTED
