# Bimodal Sizing + Same-Type-Per-Event Guard (Design Spec)

**Tarih:** 2026-05-23
**Durum:** DONE (2026-05-23) — implementation tamamlandı, DECISIONS §B SPEC-S Faz D kayıtlı
**Anahtar kelime / lookup:** `BIMODAL-SAMETYPE`
**Onaylayan:** Erim (2026-05-23)
**Tetik:** Son 13 saatlik session (22 May 22:23 UTC sonrası) gözlemi: yeni açılan 13 trade'in 12'si zarar; aynı maçta iki totals (NBA OKC/SAS 215.5 + 222.5) birlikte -$52; A güveni $50 sabit sizing tüm spor marketlerine uygulanıyor (Tenis Lab'daki $15 bimodal cap genel bota taşınmamış).

---

## 1. Hedef

İki bağımsız kuralla genel bot kayıplarını azaltmak:

**A) Bimodal sizing** — Tüm spor marketleri (moneyline, totals, spread) "binary": maç bittiğinde fiyat 1.0 veya 0.0'a sıçrar. Bu nedenle hepsi bimodal sayılır; Tenis Lab'da kullanılan $15 cap (SPEC-N, 2026-05-22) genel bota uygulanır. A güveni $50→$15, B güveni $30→$10.

**B) Same-type-per-event guard** — Aynı `event_id` altında aynı `sports_market_type`'tan birden fazla pozisyon açılması yasak. Mevcut `max_positions_per_event=3` cap'i korunur ama her biri farklı tür olur (1 ML + 1 totals + 1 spread). Bu kural tüm branş ve liglerde geçerli.

---

## 2. Mevcut Durum (kodda nerede)

### A) Sizing
- **`config.yaml:71-73`** `risk.fixed_bet_usdc: A: 50, B: 30` (SPEC-P 2026-05-21 sabit-tier sizing)
- **`src/domain/risk/position_sizer.py:confidence_position_size`** config'den `A`/`B` okur, döndürür
- **`src/strategy/entry/gate.py:165-169`** raw_size = confidence_position_size(...)

Değişiklik tek noktada: config.yaml. Kod ve test tarafı aynı imzayı korur (sadece sabitler değişir).

### B) Event-cap
- **`config.yaml:75`** `max_positions_per_event: 3`
- **`src/strategy/entry/gate.py:117-127`** `_check_per_market_guards(market, portfolio, blacklist, max_positions_per_event=...)` çağırır
- **`src/orchestration/portfolio_guards.py`** `_check_per_market_guards` event-cap'i kontrol eder — şu an `event_id` altındaki POZİSYON SAYISINA bakar, **market_type'a bakmaz**

Bu nedenle NBA OKC/SAS 215.5 + 222.5 (her ikisi de TOTALS) açılabilmiş. Same-type guard burada eklenecek.

---

## 3. Yapılacak Değişiklik (kod + config)

### A) Bimodal sizing (sadece config)

`config.yaml`:
```yaml
risk:
  fixed_bet_usdc:
    A: 15    # 50→15 (bimodal cap, tenis paritesi SPEC-N)
    B: 10    # 30→10
```

**Etki:**
- Yeni A trade: $50 → $15 (−%70)
- Yeni B trade: $30 → $10 (−%67)
- Aynı 13 trade × $15 = $195 yatırım vs. eskiden $700; aynı oranda kayıp olsa bile sayısal kayıp ~ %70 düşer
- Kâr potansiyeli de aynı oranda düşer; ancak kayıp sayısı (W/L oranı) değişmez

**Hiçbir kod/test değişikliği gerekmez** — `confidence_position_size` zaten config'den okur, mevcut testler 15/10 değerleriyle güncellenir.

### B) Same-type-per-event guard

`src/orchestration/portfolio_guards.py` — `_check_per_market_guards` fonksiyonuna yeni kontrol:

```python
# (pseudo, gerçek imza ARCH_GUARD'a uygun yazılacak)
def _check_per_market_guards(
    market: MarketData,
    portfolio: PortfolioManager,
    blacklist: Blacklist,
    max_positions_per_event: int,
) -> SkipResult | None:
    event_positions = portfolio.positions_by_event(market.event_id)

    # Mevcut: event-cap (sayıca)
    if len(event_positions) >= max_positions_per_event:
        return SkipResult("event_cap_reached", f"count={len(event_positions)}")

    # YENİ: aynı market_type kontrolü
    same_type = [p for p in event_positions if p.sports_market_type == market.sports_market_type]
    if same_type:
        return SkipResult(
            "same_market_type_per_event",
            f"type={market.sports_market_type.value}, existing={len(same_type)}",
        )

    # Mevcut: blacklist vb.
    ...
```

**Yeni skip reason:** `same_market_type_per_event` — dashboard skip-reason help'ine eklenecek.

**Etki:**
- NBA OKC/SAS 215.5 + 222.5 senaryosunda 2. totals reddedilir
- WNBA GSV/IND (1 ML + 1 totals) — geçer (farklı türler)
- WNBA DAL/ATL (1 ML + 1 totals) — geçer (farklı türler)
- Max 3 pozisyon kuralı korunur; sadece tür çeşitliliği zorunlu olur

---

## 4. Test Senaryoları (TDD)

### A) Bimodal sizing
- `test_confidence_position_size_a_returns_15`: config={A:15,B:10}, confidence=A → 15.0
- `test_confidence_position_size_b_returns_10`: config={A:15,B:10}, confidence=B → 10.0
- (mevcut `tests/unit/domain/risk/test_position_sizer.py` güncellenir)

### B) Same-type guard
- `test_per_market_guards_same_type_blocks_second_totals`:
  - portföyde 1 mevcut totals pozisyon (event_id=X, type=TOTALS)
  - yeni market (event_id=X, type=TOTALS) → SkipResult("same_market_type_per_event")
- `test_per_market_guards_different_types_allowed`:
  - portföyde 1 ML pozisyon (event_id=X, type=MONEYLINE)
  - yeni market (event_id=X, type=TOTALS) → None (geçer)
- `test_per_market_guards_event_cap_still_enforced`:
  - portföyde 3 farklı tür pozisyon (event_id=X: ML, totals, spread)
  - 4. herhangi bir tür → SkipResult("event_cap_reached") (önceki kural)
- `test_per_market_guards_blacklist_takes_precedence`:
  - blacklist match → blacklist skip kazanır (öncelik kontrolü)

### C) Gate entegrasyon
- `test_gate_skips_same_type_per_event`: end-to-end gate.run() ile market dizisi verildiğinde same-type reddi GateResult.skipped_reason'a yazılır

---

## 5. Riskler ve Mitigasyon

| Risk | Mitigasyon |
|---|---|
| Sizing düşüşü → tek trade kâr potansiyeli azalır | Kayıp azalması daha büyük etki (son 13 saatlik veride -$107 → ~-$32 tahmini) |
| Same-type yasak → bazı edge fırsatları kaçar (örn. aynı maçta hem totals 215.5 hem 222.5'te edge varsa) | Korelasyonlu risk azalır — aynı maç ters giderse tek pozisyon kaybı, üç değil |
| WNBA/totals (+$50, %100 kazanan) sizing düşüşünden etkilenir | Kazanan kombinasyon korunuyor, sadece nominal kâr düşüyor; oran aynı |
| Mevcut testler kırılır (50/30 assertion'ları var) | Testler 15/10'a güncellenir (Kural Değişikliği Protokolü Adım 3) |

---

## 6. Kapsam Dışı (Bu Spec'te YOK)

- MLB moneyline'ı kapatma — ayrı karar (kullanıcı: önce sizing + same-type uygulansın, 7 gün gözlem)
- NHL moneyline'ı kapatma — aynı, ayrı karar
- Circuit breaker'ı tekrar açma — kullanıcı reddetti
- Restart sonrası SL davranışı düzeltme — ayrı spec gerekir (uyku→uyanma paradoksu)
- MLB submarket Plan 2-3-4 (model anchor tamamlama) — ayrı çalışma

---

## 7. ARCH_GUARD Uyumluluk

| Kural | Durum |
|---|---|
| 1 (katman) | ✓ Değişiklik strategy + orchestration + config — aynı yön |
| 2 (domain I/O) | ✓ Domain'e dokunulmuyor |
| 3 (<400 satır) | ✓ `gate.py` 217→~217 (çağrı imzası aynı), `portfolio_guards.py` küçük artış |
| 6 (magic number) | ✓ Sabitler config.yaml'da |
| 7 (P(YES) anchor) | ✓ Sizing/guard P(YES)'e dokunmaz |
| 8 (event-level guard) | ✓ Mevcut event-cap **genişletilir**, ihlal değil |
| 11 (test) | ✓ Yeni domain/strategy testleri yazılır |

---

## 8. Onay Sonrası Adımlar

1. Kullanıcı bu spec'i inceler ve onaylar
2. Plan dosyası yazılır (`docs/superpowers/plans/2026-05-23-bimodal-and-same-type-guard.md`) — adım adım TDD planı
3. Plan onayı sonrası: testler önce yazılır (TDD), sonra kod
4. `pytest -q` tüm yeşil → `config.yaml` güncellenir → bot restart
5. DECISIONS.md §B'ye SPEC-S kaydı eklenir
6. 7 gün gözlem; sonra MLB ML / NHL ML kapatma kararı ayrı tartışılır

---

## 9. Tahmini Etki (geriye-bakım — son 13 saatlik veri)

| Değişiklik | Etki |
|---|---|
| Sadece bimodal sizing | -$107 → -$32 (yatırım %70 düştü; kayıp/kâr oranı aynı kalır) |
| Sadece same-type guard | NBA OKC/SAS 222.5 açılmaz → +$22 kâr önlenir; net -$107 → -$85 |
| **Birlikte** | NBA 2. totals açılmaz + sizing $50→$15 → tahmini net **-$24** (mevcut -$107) |

Not: bu sadece bu pencerenin geriye-bakım simülasyonu; gelecek sonuçların garantisi değil.
