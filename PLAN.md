# PLAN — Aktif Planlar

> Bu dosya aktif uygulama planlarını içerir.
> Bir plan entegre edilip onaylandıktan sonra bu dosyadan **SİLİNİR**.
> Sadece aktif, henüz uygulanmamış planlar burada durur.

---

## Nasıl Kullanılır

### Plan Ekleme
```
1. Yeni bir plan önerisi yaz (aşağıdaki formata uy)
2. Durum: PROPOSED
3. Onay bekle
4. Onay alınca durum: APPROVED → uygula
5. Uygulama bittikten sonra durum: DONE → bu dosyadan sil
```

### Plan Formatı
```
### PLAN-XXX: [Kısa başlık]
- **Durum**: PROPOSED | APPROVED | IN_PROGRESS | DONE
- **Tarih**: YYYY-MM-DD
- **Öncelik**: P0 | P1 | P2
- **Etki**: Hangi katmanlar/dosyalar etkilenir
- **Açıklama**: Ne yapılacak ve neden
- **Adımlar**:
  1. ...
  2. ...
- **Kabul Kriterleri**:
  - [ ] ...
- **Mimari Uyumluluk**: ARCHITECTURE_GUARD.md kurallarına uygun mu?
- **TDD Referansı**: TDD §X
```

---

## Aktif Planlar

### PLAN-A: Stock Queue — persistent eligible pool + JIT enrichment
- **Durum**: PROPOSED
- **Tarih**: 2026-04-15
- **Öncelik**: P1 (B+C uygulandıktan sonra)
- **Etki**: Yeni infrastructure modül + orchestration revize. Dosyalar:
  - Yeni: `src/orchestration/stock_queue.py` (in-memory + persistent pool manager)
  - Revize: `src/orchestration/scanner.py` (eligible'dan reddedilenleri stock'a push eder)
  - Revize: `src/orchestration/agent.py` (heavy cycle sırası: stock re-evaluate → scanner → gate)
  - Revize: `src/infrastructure/persistence/eligible_queue_snapshot.py` → stock pool snapshot da buradan yazılır veya yeni `stock_snapshot.py`
  - Dashboard: "Stock" sekmesi zaten var; data kaynağı değişir (mevcut eligible_queue.json → stock_queue.json)
  - Config: `stock` bölümü eklenir
  - Testler: stock_queue unit test + orchestration integration test

- **Açıklama + Tasarım**:
  **Problem:** Mevcut sistemde eligible marketler (scan+match+enrich+manipulation'dan geçen) her cycle sıfırdan değerlendirilir. Exposure/slot/no_edge gibi "anlık" nedenlerle reddedilen marketler kaybedilir — Odds API kredisi boşa gider, fırsat kaçar.

  **Çözüm:** Stock = **persistent eligible pool**. Sinyal üretip red yenilen veya no_edge gelen marketler stock'a alınır; slot boşaldıkça JIT re-evaluate edilir, sadece en yakın match_start'lı subset enrich edilir.

  **Davranış sırası (heavy cycle):**
  ```
  1. Heavy cycle başlar
  2. Stock FAZ:
     - Stock pool'u match_start ASC sırala (en yakın maç önce)
     - Boş slot sayısı = N (max_positions - open_positions)
     - Top (3 × N) elemanı seç — "JIT batch"
     - Bu batch için SADECE:
         a. Market fiyatı yenile (Gamma quick-fetch — sadece price)
         b. Odds enrich (taze bm_prob)
     - Gate'ten geçir (event-guard + manipulation + strateji + sizing + exposure)
     - APPROVED olanlar → executor → pozisyon aç (ilk N tanesi)
     - Kalanlar stock'ta DURUR (TTL bitmediyse)
  3. Stock'ta hâlâ boş slot varsa (N'den az approved): Scanner FAZ'ı
     - Gamma'dan yeni adaylar çek, eligible pipeline
     - Reddedilenler (exposure_cap/no_edge/signal-ama-slot-yok) stock'a push
  4. Cycle biter
  ```

  **Stock kayıt şeması (per item):**
  ```json
  {
    "condition_id": "0x...",
    "event_id": "...",
    "slug": "...",
    "match_start_iso": "...",
    "sport_tag": "...",
    "first_seen_ts": "...",     // stock'a ilk giriş zamanı
    "last_eval_ts": "...",      // son re-evaluate zamanı
    "last_skip_reason": "...",  // neden stock'a düştü
    "market_snapshot": { yes_price, liquidity, ... },  // son bilinen
    "ttl_expires_iso": "..."    // match_start - 30dk VEYA first_seen + 24h, hangisi önce
  }
  ```

  **TTL (stock'tan çıkarma):**
  - Match başladı (veya başlangıçtan 30 dk önce eşik) → düşür
  - 24 saat hiç re-evaluate edilmediyse → düşür
  - Event_id artık açık pozisyon listesinde → düşür
  - Blacklist'e alındıysa → düşür
  - Aynı market için 3. kez "no_edge" gelirse → düşür (VS gibi değil artık — edge yoksa inatçı olma)

  **Sıralama:** Her cycle match_start ASC (en yakın maç önce). Tie-breaker: confidence A > B, sonra edge yüksek.

  **JIT batch size neden 3×N?**
  - 1×N yetersiz: reject/skip olursa slot boş kalır
  - 5×N israf: odds kredisi çok tüketir
  - 3×N: ampirik olarak ~70-80% fill rate (1-slot senaryoda 3 enrich → 2 uygun → 1 slota + 1 stock'ta kalır)

- **Adımlar**:
  1. `src/orchestration/stock_queue.py` yarat — `StockQueue` class:
     - `add(market, skip_reason)`, `evict_expired()`, `top_n_by_match_start(n)`, `remove(cid)`, `load()`, `save()`
     - Saf domain + infrastructure persistence (I/O stock_snapshot'a delege)
     - <200 satır hedef
  2. `src/infrastructure/persistence/stock_snapshot.py` yarat (eligible_queue_snapshot örneği) — yalnızca JSON read/write
  3. `src/config/settings.py` + `config.yaml`: yeni `stock` bölümü (jit_batch_multiplier=3, ttl_hours=24, pre_match_cutoff_min=30, max_no_edge_attempts=3)
  4. `src/orchestration/agent.py` heavy cycle: önce stock_queue.evaluate_top → sonra scanner fresh. DI: stock_queue factory'de inşa edilir.
  5. `src/orchestration/scanner.py` veya yeni koordinator: reject edilenleri `stock.add()` çağır
  6. `src/orchestration/factory.py`: StockQueue + StockSnapshot wiring
  7. Dashboard: `Stock` sekmesi data source `stock_queue.json` → statue/age/last_skip_reason göster
  8. `tests/unit/orchestration/test_stock_queue.py`: add/evict/sort/TTL
  9. Integration test: 1 slot boş → 3 item enrich → 1 open → 2 stock'ta kalır senaryosu
  10. PRD/TDD güncelleme: F1 Scan ile F3 Entry arasına yeni F1.5 "Stock re-evaluation" bölümü

- **Kabul Kriterleri**:
  - [ ] Her heavy cycle stock önce evaluate edilir (boş slot varsa)
  - [ ] Enrichment çağrısı sayısı ≤ (3 × boş_slot) + scanner_fresh
  - [ ] TTL düşme: match_start - 30dk kuralı çalışır (unit test)
  - [ ] no_edge 3 kez → auto-evict (unit test)
  - [ ] Dashboard Stock sekmesi yeni JSON'dan beslenir
  - [ ] pytest tamamı geçer
  - [ ] stock_queue.py + stock_snapshot.py her biri < 400 satır

- **Mimari Uyumluluk**:
  - ✓ Orchestration katmanında (scanner/gate/executor'ı koordine ediyor, iş mantığı değil)
  - ✓ Domain'de I/O yok (persistence infrastructure'a delege)
  - ✓ Magic number yok (tüm eşikler config)
  - ✓ God object yok (StockQueue tek sorumluluk: pool CRUD + sıralama)
  - ✓ 400 satır limiti her dosya için
  - ✓ Yeni dizin yok (orchestration/ ve infrastructure/persistence/ mevcut)

- **TDD Referansı**: Yeni §11 (Stock Queue), mevcut §6 unchanged
- **Not**: B + C tamamlanıp test geçmeden A'ya başlanmaz. A büyük refactor; izole branch'te çalışılması önerilir.

---
