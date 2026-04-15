# H2H Scope Tightening — Design Spec

**Tarih:** 2026-04-15
**Kapsam:** Bot sadece "kim kazanır" (head-to-head moneyline) bahisleri alsın. Gürültüyü kes + mevcut kapsamda matching iyileştir.

**Kapsam dışı:** Golf outright, futures (>24h), alt market türleri. Kelly/SL rule changes yok. Strategy logic değişmez.

---

## Problem

Bot 258 gate skip üretiyor, çoğu yapısal olarak çözülemeyen veya kapsamdaki bir sporun matching eksikliğinden:

- **146 PGA Top-N prop** — bookmaker H2H yok, skip boşuna
- **33 futures (>24h)** — Odds API 24h penceresi dışı, skip boşuna
- **56 tennis** — 21 tanesi normal 12-24h pencerede ama matching fail → **potansiyel ek entry**

User: "Sadece kim kazanır bahisleri." Scope PGA outrights + futures → out. Tennis matching → debug + fix.

---

## Aşama A — Scanner Strict Filter

**Amaç:** Gate'e sadece h2h moneyline + 24h içinde maç giden market'lar ulaşsın.

### Değişiklik

`src/orchestration/scanner.py::_passes_filters`:

```python
# ÖNCE (gevşek — boş string geçiyor)
if m.sports_market_type and m.sports_market_type != "moneyline":
    return False

# SONRA (strict)
if m.sports_market_type != "moneyline":
    return False

# YENİ — Odds API penceresi 24h; uzak maçları scanner'da ele
if _hours_to_start(m) > 24:
    return False
```

### Testler

`tests/unit/orchestration/test_scanner.py` içine ekle:

1. `test_market_rejected_when_sports_market_type_empty` — PGA Top-N senaryosu
2. `test_market_rejected_when_hours_to_start_exceeds_24h` — futures senaryosu
3. `test_market_accepted_with_moneyline_and_within_24h` — happy path

### Beklenen sonuç

- PGA Top-N 146 market scanner'da elenir
- Futures 33 market scanner'da elenir
- Stock queue %70 temizlenir, log gürültüsü düşer
- Entry sayısında doğrudan artış YOK (zaten enrich/gate'ten geçemeyenlerdi)

### Risk

- `sports_market_type` field'ı MLB/NHL/NBA/tennis kayıtlarında `"moneyline"` dolu (canlı veri ile doğrulandı). Yanlış pozitif risk minimal.
- `match_start_iso` yoksa `_hours_to_start` `+inf` döner → elenir. Sabit zamanlı turnuvalar (golf outright) zaten out. Yan etki yok.

---

## Aşama B — Tennis Matching Debug + Fix

**Amaç:** Tennis h2h market'ların `no_bookmaker_data` skip'ini azalt. Gerçek entry artışı.

### Hipotezler

Enricher `odds_enricher.py::enrich_market` 5 başarısızlık noktasında None dönebilir:

1. **sport_key_resolver** → Rouen/Porsche Tennis gibi turnuvalar için yanlış/eksik key
2. **extract_teams** → "Open Capfinances Rouen Metropole: Kamilla Rakhimova vs Ann Li" — turnuva prefix parser'ı geçebilir mi?
3. **Odds API events boş** — Odds API `tennis_wta_*` için event vermiyor olabilir
4. **find_best_event_match** — team ismi bookmaker formatıyla eşleşmiyor (Kamilla → K. Rakhimova?)
5. **_weighted_average bm_count==0** — event bulundu ama hiçbir bookmaker h2h outcome vermedi

### Investigation task (B.1 — kod değil, teşhis)

Script `scripts/diag_tennis_enrich.py` (commit edilmez, one-off):

```python
"""Tek seferlik teşhis. 5 başarısız tennis market'a enricher çalıştır,
hangi adımda fail ettiğini INFO seviyesinde yaz."""
```

Çalıştır, çıktıyı kaydet: `diag_tennis_output.txt`.

Sample 5 market: stock_queue.json'dan `sport_tag=tennis, last_skip_reason=no_bookmaker_data, 12-24h bucket` filtreli ilk 5.

Her market için log:
- sport_key resolve sonucu
- extract_teams sonucu (team_a, team_b)
- Odds API response event sayısı
- find_best_event_match sonucu (match/no match + closest candidate)
- Varsa weighted_average bm_count

### Fix strategies (B.2 — B.1 sonucuna göre)

B.1 çıktısına göre doğru fix:

| Fail nokta | Olası fix | Lokasyon |
|---|---|---|
| sport_key None | Turnuva → key tablosu genişlet | `domain/matching/odds_sport_keys.py` |
| extract_teams None | Turnuva prefix parser'ı güçlendir | `strategy/enrichment/question_parser.py` |
| events boş | Odds API key mismatch; alternatif key dene | `sport_key_resolver.py` |
| no event match | Fuzzy match threshold düşür; isim normalization | `domain/matching/pair_matcher.py` |
| bm_count 0 | Odds API bookmaker regions genişlet (us,uk,eu,au) | `odds_enricher.py::_odds_query_params` |

**Her fix'e**:
- 1 regression test (failing market'ı başarılı matche çevirir)
- Mevcut testlerin hâlâ geçmesi

### Beklenen sonuç

- 21 tennis 12-24h skip'inden 10-15 entry'ye dönüşüm (~%50-70 kazanım oranı, bookmaker coverage varsayımıyla)
- Günlük entry sayısı ~25-30 ek pozisyon

### Başarısızlık durumu

B.1 çıktısı "events boş" → bookmaker bu turnuvaları yayınlamıyor → **unfixable**, aşama B kapatılır.

---

## Aşamalar arası bağımlılık

- **Yok**. A ve B bağımsız. A önce çalışır (gürültü siler, B.1 log'unu okumak kolaylaşır).
- Aşama A ⟶ commit ⟶ Aşama B.1 (diagnostic, commit edilmez) ⟶ Aşama B.2 (fix + test + commit).

---

## ARCH_GUARD Uyumluluk

- ✓ DRY: scanner filter tek yerde, enrich fix tek modülde
- ✓ <400 satır: scanner.py ~135 satır, odds_enricher.py 171 satır — değişim marjinal
- ✓ Domain I/O yok: scanner.py orchestration, enricher.py strategy (API çağrısı zaten orada — değişmez)
- ✓ Katman düzeni: korundu
- ✓ Magic number yok: 24h ve "moneyline" literal; config'de `max_hours_to_start: 24` olarak tanımlanabilir → daha temiz, ama şu an enricher'da aynı 24 var, DRY için `config.scanner.max_hours_to_start` tercih edilir
- ✓ utils/helpers/misc yok
- ✓ Sessiz hata yok: `_hours_to_start` zaten `+inf` fallback
- ✓ P(YES) anchor: N/A

---

## Başarı Kriteri

- `no_bookmaker_data` skip sayısı 258 → **<100** (B.2 sonrası)
- Gerçek entry sayısı heavy cycle başına 10 → **15-20**
- Test suite 637 → **639+** (Aşama A), **640+** (Aşama B)
- PGA + futures skipped_trades.jsonl'a yazılmaz (scanner'da elenir, gate'e gitmez)

---

## Scope kararı

**Dahil**: Scanner strict + tennis matching
**Hariç**: Golf outright, basketball minor league coverage, edge threshold gevşetme, yeni API integration — tümü YAGNI.
