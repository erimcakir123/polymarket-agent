# Gamma Client `match_start_iso` Bug Fix

> **For agentic workers:** Use superpowers:executing-plans or subagent-driven-development.

**Goal:** Polymarket single-game marketlerinin (NBA/NHL/MLB bu akşam oynanacak maçları vb.) scanner'dan düşmesine neden olan `match_start_iso` öncelik sırası bug'ını düzelt. Test ekle, pytest'te doğrula.

**Architecture:** Tek satırlık kod değişikliği + 3 yeni unit test. Davranış etkisi: scanner artık gelecekteki single-game maçları doğru tespit edecek.

**Bug özeti:**
- Polymarket raw JSON'da: `event.startTime` = maç saati, `market.startDate` = market yaratılma tarihi
- Mevcut kod `market.startDate` önce kullanıyor → single-game için yanlış (market aylar önce açılmış, maç bu akşam)
- Kanıt: Portsmouth vs Ipswich event.startTime=2026-04-14T19:00 ama market.startDate=2025-12-08 (126 gün önce)

---

## Referanslar

- Bug yeri: [src/infrastructure/apis/gamma_client.py:144-148](../../../src/infrastructure/apis/gamma_client.py#L144-L148)
- Test dosyası: [tests/unit/infrastructure/apis/test_gamma_client.py](../../../tests/unit/infrastructure/apis/test_gamma_client.py)
- Scanner filter ilgili satır: [src/orchestration/scanner.py:148-160](../../../src/orchestration/scanner.py#L148-L160) (dokunulmaz)
- Diagnostic bulguları: bu repo kökündeki `diag_scan.py`, `diag2-5.py` (Task 3'te silinir)

---

## File Structure

**Değişen:**
- `src/infrastructure/apis/gamma_client.py` — 1 satırlık fix + yorum
- `tests/unit/infrastructure/apis/test_gamma_client.py` — 3 yeni test

**Değişmeyen:** config.yaml, TDD.md, PRD.md, scanner.py, diğer src

---

## Task 1: gamma_client.py fix

**Files:**
- Modify: `src/infrastructure/apis/gamma_client.py`

- [ ] **Step 1: Edit — `or` sırasını çevir + yorum güncelle**

Edit tool:

`old_string`:
```
                match_start_iso=str(
                    raw.get("startDate", "")
                    or raw.get("_event_start_time", "")
                    or ""
                ),
```

`new_string`:
```
                match_start_iso=str(
                    raw.get("_event_start_time", "")
                    or raw.get("startDate", "")
                    or ""
                ),
```

**Not:** Yukarıdaki yorum satırlarını da güncelle:

`old_string`:
```
                # match_start_iso öncelik: market.startDate (en spesifik) →
                # event.startTime (single-game event'lerde dolu) → "" (futures)
```

`new_string`:
```
                # match_start_iso öncelik: event.startTime (single-game maç saati,
                # mevcutsa) → market.startDate (futures fallback — market yaratılma
                # tarihi) → "" (ikisi de yoksa)
```

- [ ] **Step 2: Doğrulama**

Run: `grep -A 4 "_event_start_time" src/infrastructure/apis/gamma_client.py | head -6`
Expected: Yeni sırada `_event_start_time` önce, `startDate` sonra görünür.

---

## Task 2: Unit testler

**Files:**
- Modify: `tests/unit/infrastructure/apis/test_gamma_client.py`

- [ ] **Step 1: 3 yeni test ekle**

Edit tool — mevcut `test_parse_market_missing_tokens_returns_none` fonksiyonunun HEMEN ALTINA 3 yeni test ekle:

`old_string`:
```
def test_parse_market_missing_tokens_returns_none() -> None:
    client = GammaClient(http_get=MagicMock())
    raw = {"conditionId": "0xabc", "question": "Q", "slug": "s"}
    assert client._parse_market(raw) is None
```

`new_string`:
```
def test_parse_market_missing_tokens_returns_none() -> None:
    client = GammaClient(http_get=MagicMock())
    raw = {"conditionId": "0xabc", "question": "Q", "slug": "s"}
    assert client._parse_market(raw) is None


def test_parse_market_prefers_event_start_time_over_market_start_date() -> None:
    """Single-game event: event.startTime = maç saati, market.startDate = yaratılma.
    match_start_iso event.startTime'dan gelmeli, yoksa scanner bu maçı 'geçmişte başlamış'
    sanıp atar (bkz. docs/superpowers/plans/2026-04-14-gamma-match-start-fix.md).
    """
    client = GammaClient(http_get=MagicMock())
    raw = _event("0xgame")["markets"][0]
    raw["_event_start_time"] = "2026-04-14T23:30:00Z"  # maç saati (gelecek)
    raw["startDate"] = "2025-12-08T05:12:40Z"          # market yaratılma (aylar önce)
    raw["_event_live"] = False
    raw["_sport_tag"] = "nba"
    raw["_event_id"] = "evt_game"
    m = client._parse_market(raw)
    assert m is not None
    assert m.match_start_iso == "2026-04-14T23:30:00Z"


def test_parse_market_falls_back_to_market_start_date_for_futures() -> None:
    """Futures event: event.startTime yok (None/""), market.startDate var.
    match_start_iso fallback olarak market.startDate kullanmalı.
    """
    client = GammaClient(http_get=MagicMock())
    raw = _event("0xfutures")["markets"][0]
    raw["_event_start_time"] = ""                       # futures: event startTime yok
    raw["startDate"] = "2025-06-23T16:00:27Z"          # market yaratılma
    raw["_event_live"] = False
    raw["_sport_tag"] = "nhl"
    raw["_event_id"] = "evt_futures"
    m = client._parse_market(raw)
    assert m is not None
    assert m.match_start_iso == "2025-06-23T16:00:27Z"


def test_parse_market_match_start_empty_when_both_missing() -> None:
    """Ne event.startTime ne market.startDate varsa match_start_iso = ""."""
    client = GammaClient(http_get=MagicMock())
    raw = _event("0xnone")["markets"][0]
    raw["_event_start_time"] = ""
    raw["startDate"] = ""
    raw["_event_live"] = False
    raw["_sport_tag"] = "tennis"
    raw["_event_id"] = "evt_none"
    m = client._parse_market(raw)
    assert m is not None
    assert m.match_start_iso == ""
```

- [ ] **Step 2: Testleri çalıştır — sadece gamma_client testleri**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m pytest tests/unit/infrastructure/apis/test_gamma_client.py -v`

Expected:
- `test_parse_market_valid` PASS
- `test_parse_market_missing_tokens_returns_none` PASS
- `test_parse_market_prefers_event_start_time_over_market_start_date` PASS (YENİ)
- `test_parse_market_falls_back_to_market_start_date_for_futures` PASS (YENİ)
- `test_parse_market_match_start_empty_when_both_missing` PASS (YENİ)
- Önceki tüm gamma testleri PASS

Eğer `test_parse_market_valid` KIRILIRSA: fixture `_event` default'unda `startTime` set, `startDate` market içinde olmadığı için problem olmamalı. Ama olursa durdur, raporla.

- [ ] **Step 3: Tüm test suite**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m pytest -q`

Expected: `598 passed` (önceki 595 + 3 yeni).

Eğer başka yerde regresyon varsa: durdur, raporla.

---

## Task 3: Diagnostic scriptleri sil

**Files:**
- Delete: `diag_scan.py`, `diag2.py`, `diag3.py`, `diag4.py`, `diag5.py`

- [ ] **Step 1: Kontrol**

Run: `ls diag*.py 2>/dev/null`
Expected: `diag_scan.py diag2.py diag3.py diag4.py diag5.py` (veya bir kısmı)

- [ ] **Step 2: Sil**

Run: `rm -f diag_scan.py diag2.py diag3.py diag4.py diag5.py`

- [ ] **Step 3: Doğrula**

Run: `ls diag*.py 2>/dev/null; echo "exit=$?"`
Expected: Boş liste, `exit=2` (dosya yok).

---

## Task 4: Final doğrulama + rapor

- [ ] **Step 1: Kod değişikliği doğrula**

Run: `grep -n "_event_start_time" src/infrastructure/apis/gamma_client.py`
Expected: En az 2 satır; `_parse_market` içinde yeni sıra görünür.

- [ ] **Step 2: Test suite**

Run: `python -m pytest -q`
Expected: `598 passed`

- [ ] **Step 3: Gerçek dünya kontrol (opsiyonel)**

Eğer kullanıcı isterse bot'u dry_run modunda 1 heavy cycle çalıştırabilir ve `logs/bot.log`'da scanner'ın kaç market gördüğünü karşılaştırabilir. Bu plan kapsamı dışı; kullanıcı kararı.

- [ ] **Step 4: Rapor**

Kullanıcıya:
- Değişen dosya: `src/infrastructure/apis/gamma_client.py` (1 satır fix + yorum)
- Yeni test: `test_gamma_client.py` (3 test)
- Silinen: diagnostic scriptleri
- pytest: 598/598
- Beklenen etki: scanner bundan sonra gelecekteki single-game marketleri (NBA/NHL/MLB bu akşamın maçları vs.) doğru tespit edecek. Önceki 9 market yerine gerçek maç sayısını (likidite ≥ $1000 olanlar) görecek.

---

## Self-Review

**Kapsam tam:**
- Bug fix tek satır ✅
- 3 edge case covered in tests ✅
- Diagnostic cleanup ✅
- Verification steps eksiksiz ✅

**Placeholder yok:** Tüm `old_string` ve `new_string` tam içerikli.

**Risk değerlendirmesi:**
- `test_parse_market_valid` fixture default `startTime` var, `startDate` market içinde YOK → yeni sırada da aynı değer gelir (`_event_start_time` kullanır). Zaten eski sırada da `startDate` boş olduğu için fallback oluyordu. Regresyon yok.
- Scanner testlerinde `MarketData.match_start_iso` manuel set ediliyor, gamma parsing'e bağlı değil → dokunulmaz.
- Production davranış: daha fazla market scanner'dan geçer → entry gate daha fazla market değerlendirir. Manipulation guard zaten düzeltildi, likidite/edge filter'ları hala aktif.

**Git yok:** Commit adımı yok, doğrulama için pytest yeterli.
