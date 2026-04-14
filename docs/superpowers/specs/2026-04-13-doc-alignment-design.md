# Design: Dokümantasyon Hizalama (PRD + TDD + PLAN + ARCHITECTURE_GUARD)

**Tarih**: 2026-04-13
**Durum**: DRAFT → user review bekliyor
**Kapsam**: Polymarket Agent 2.0 doküman setini TDD v2.0 ile tam tutarlı hale getir

---

## 1. Amaç

TDD v2.0 yazıldı (2026-04-13). Diğer dokümanlar (PRD, PLAN, ARCHITECTURE_GUARD) hâlâ eski proje referanslarına ve eski yapıya göre yazılmış. Bu design dört değişikliği tanımlar:

1. **PRD.md'yi sıfırdan yaz** (mevcut dosya silinmiş).
2. **PLAN.md'yi yeniden yapılandır** (3 plan → 7 plan, TDD Faz 1-7 ile 1:1 eşleşme).
3. **TDD.md'den negatif içerikleri temizle** (4 bölüm).
4. **ARCHITECTURE_GUARD.md'de 2 nokta temizle** (eski proje karşılaştırma tablosu + ESPN örneği).

---

## 2. Kılavuz İlkeler

### İlke 1 — SSOT (Single Source of Truth)

Her bilgi **tek bir master dosyada** detaylı tutulur. Diğer dosyalar referans verir.

- Algoritma, veri modeli, teknik akış → **TDD master**
- Mimari kural, katman disiplini → **ARCHITECTURE_GUARD master**
- Ürün davranışı, demir kural, operasyonel akış → **PRD master**
- Uygulama sırası, aktif plan → **PLAN master**
- Gelecekteki işler → **TODO master**

PRD "bot Odds API'dan 20+ bookmaker probability alır" der → detayı TDD §6.1'e referanslar. Algoritmayı tekrarlamaz.

### İlke 2 — Pozitif İçerik (Negative-Free)

Dokümanlar sadece v2'nin **sahip olduğu** özellikleri anlatır. "X yok", "Y kaldırıldı", "Z bizde değil" cümleleri tüm v2 dosyalarında yasak.

**İstisna**: `TODO.md` — gelecekte eklenecek işleri listeler, doğası gereği "şu an yok" bilgisi içerir.

**İstisna**: ARCHITECTURE_GUARD'ın "Neden Bu Dosya Var?" bölümü — kuralların motivasyonu kısa geçmişe dayanıyor, ama mevcut kısa 3 satır yeterli.

### İlke 3 — Çapraz Referans Disiplini

Her bölümde ilgili master dosyaya açık referans:
- `(bkz. TDD §6.5)` — algoritma detayı
- `(bkz. TODO-001)` — ertelenmiş iş
- `(bkz. ARCHITECTURE_GUARD Kural 7)` — mimari disiplini

Bu hem tutarlılığı kolaylaştırır hem de yeni Claude oturumlarında doğru dosyaya yönlendirir.

---

## 3. PRD.md — Sıfırdan Yapı (9 Bölüm)

**Hedef uzunluk**: ~500 satır. Türkçe.

| # | Bölüm | İçerik | SSOT referansları |
|---|---|---|---|
| 1 | Giriş | Bot ne yapar, tek paragraf + tek cümlelik çalışma mantığı | TDD §0 |
| 2 | Demir Kurallar | 7 kural: P(YES) anchor / Event-level Guard / Confidence-based sizing / Bookmaker-derived probability / 3-katmanlı cycle / Circuit breaker zorunlu / Scale-out profit-taking | ARCHITECTURE_GUARD Kural 7-8 + TDD §0 |
| 3 | Operasyonel Akışlar | 5 user flow: (a) Bot başlatma, (b) Entry flow (scan→enrich→gate→sizing→execute), (c) Light cycle monitoring, (d) Exit flow (SL/scale-out/near-resolve), (e) Circuit breaker tetiklendiğinde | TDD §4 |
| 4 | Fonksiyonel Gereksinimler | 8 yetenek grubu: F1 Scan, F2 Enrich, F3 Entry Decision, F4 Position Sizing, F5 Execute, F6 Monitor, F7 Exit, F8 Report. Her biri 3-5 satır tanım + TDD referansı | TDD §3, §6 |
| 5 | Non-Fonksiyonel Gereksinimler | Latency (heavy ≤30sn, light ≤1sn, WS anlık), Uptime (48h+ dry-run), Crash recovery (startup.py pozisyonları geri yükler), Observability (dashboard + telegram + JSONL trade log), Dry-run/paper/live modları | TDD §10, §12 |
| 6 | Teknik Kısıtlar | API rate limits (Odds 20K/ay, CLOB ~100/dk), Polygon mainnet, USDC bakiye, cycle süreleri (30dk/5sn), gece modu (UTC 08-13 → 60dk) | TDD §8, §9 |
| 7 | Savunma Mekanizmaları | 4 katman: (a) Manipulation guard (min likidite + haber kaynağı), (b) Liquidity check (entry %20 book → boyutu yarıla, exit %80 fill ratio), (c) Circuit breaker (daily -8%, hourly -5%, soft -3%, 4 ardışık), (d) Event-level guard (aynı event_id = tek pozisyon) | TDD §6.16, §6.17, §6.15 + ARCH Kural 8 |
| 8 | Sözlük | Terimler: anchor, P(YES), edge, eff_price, direction, confidence (A/B/C), favored, scale-out, elapsed, consensus | — |
| 9 | Referanslar | TDD.md, ARCHITECTURE_GUARD.md, TODO.md, CLAUDE.md | — |

### Dahil Edilmeyecekler

Bu bölümler profesyonel standartta olmasına rağmen, kullanıcı talebi üzerine **PRD'de yer almayacak**:
- Executive Summary, Product Vision, Goals
- Problem Statement
- Target Users / Personas
- Scope (In / Out)
- Success Metrics / KPIs
- Risks & Mitigation
- Out of Scope

Bu bilgiler ya dağınık (user tek kişi, scope TDD'de zaten belli) ya da negatif (out of scope = "yok olanlar").

---

## 4. PLAN.md — 7 Plan Yapısı (TDD Faz 1-7 ile 1:1)

### Mevcut → Yeni

**Silinecekler**:
- PLAN-001 (eski iskelet)
- PLAN-002 (eski infrastructure)
- PLAN-003 (eski domain)
- PLAN-004 (DONE — TDD yazıldı, artık gereksiz)

**Yazılacaklar**:

| Yeni | Eşleşen TDD Faz | Öncelik | Kapsam özeti |
|---|---|---|---|
| PLAN-001 | Faz 1 — Foundation | P0 | config/settings.py, config/sport_rules.py, config.yaml, models/, infrastructure/persistence/, gamma_client, wallet, executor (dry_run mock) |
| PLAN-002 | Faz 2 — Domain Core | P0 | probability, confidence, edge, position_sizer, circuit_breaker, portfolio, matching (migrate), guards |
| PLAN-003 | Faz 3 — Entry Pipeline | P0 | odds_client, odds_enricher, entry/normal, entry/gate, clob_client |
| PLAN-004 | Faz 4 — Exit Pipeline | P0 | price_feed (WS), stop_loss, graduated_sl, scale_out, near_resolve, a_conf_hold, favored, exit/monitor |
| PLAN-005 | Faz 5 — Orkestrasyon | P0 | process_lock, startup, scanner, cycle_manager, agent |
| PLAN-006 | Faz 6 — Ek Entry Stratejileri | P1 | early_entry, volatility_swing, consensus |
| PLAN-007 | Faz 7 — Sunum ve İzleme | P1 | dashboard (Flask), notifier (Telegram), cli |

### Her Plan Aynı Yapıda

```
### PLAN-XXX: [Faz adı]
- Durum: PROPOSED
- Tarih: 2026-04-13
- Öncelik: P0 | P1
- Etki: [hangi katmanlar/dosyalar]
- Açıklama: [TDD §11 Faz tanımı, kısa]
- Adımlar: [TDD Faz listesindeki numaralı adımlar, 1:1 kopyalanır]
- Kabul Kriterleri: [her Faz için özgün + ortak (test yeşil, mimari uyum)]
- Mimari Uyumluluk: [ARCHITECTURE_GUARD kurallarına uyuyor mu, kısa beyan]
- TDD Referansı: TDD §11 Faz X
```

---

## 5. TDD.md — Temizlik (4 Bölüm Silinir)

| Bölüm | Nerede | Aksiyon |
|---|---|---|
| §1.2 "Eski Projenin Problemleri ve v2 Çözümleri" tablosu | Satır ~49-61 | **Tamamen sil** (karşılaştırmalı tablo, negatif içerik) |
| §7.1 "DEFERRED (bkz. TODO-001)" satırı | Satır ~1086 | **Sil** (TODO.md'ye referans bölüm 9'da zaten var — tekrar) |
| §8 "KALDIRILANLAR" bölümü | Satır ~1114-1120 | **Tamamen sil** |
| §9 "DİKKAT: Config'te olmayan eski alanlar" bloğu | Satır ~1262-1268 | **Tamamen sil** |

Kalanlar dokunulmaz. TDD hâlâ DRAFT, temizlik sonrası user onayı ile APPROVED olur.

---

## 6. ARCHITECTURE_GUARD.md — Temizlik (1 Nokta)

**Düzeltme (plan yazımı sırasında keşfedildi)**: İlk design doc'ta "ARCHITECTURE_GUARD'da karşılaştırma tablosu var" yazılmıştı. Grep ile doğrulandı — **ARCHITECTURE_GUARD.md'de eski proje karşılaştırma tablosu yok**. O tablo sadece `TDD.md §1.2`'de (satır 51) bulunuyor ve Task 3.1'de siliniyor. ARCHITECTURE_GUARD.md yalnızca 1 noktada değişecek:

| Nokta | Aksiyon |
|---|---|
| Satır 222 — Anti-pattern örneği `espn_client` | `from src.infrastructure.apis.odds_client import OddsClient` ile değiştir; aynı "lazy import = gizli bağımlılık" mesajı korunur |

"Neden Bu Dosya Var?" bölümü (satır 9-13) dokunulmaz — kural motivasyonunu 3 satırda yeterince anlatıyor.

Dosyanın "DEĞİŞTİRİLEMEZ" etiketi (satır 3) hakkında not: bu etiket **kuralların** değiştirilemezliğini korur. Yanlış örnek düzeltmesi kurallara dokunmuyor; salt editöryal temizlik.

---

## 7. Uygulama Sırası

1. Design doc yazıldı (bu dosya).
2. User review + onay (bu adım).
3. **PLAN.md yaz** → mevcut içerik silinir, 7 yeni PLAN yazılır.
4. **ARCHITECTURE_GUARD.md temizle** → tablo silinir, line 222 düzeltilir.
5. **TDD.md temizle** → 4 bölüm silinir.
6. **TDD.md durumunu** DRAFT → APPROVED işaretle.
7. **PRD.md yaz** → 9 bölüm, ~500 satır.
8. Her dosya commit edilir (user istediğinde).
9. Bitiş → writing-plans skill ile PLAN-001 implementation plan'ına geç (user hazır olunca).

---

## 8. Kabul Kriterleri (Bu Design İçin)

- [ ] PRD 9 bölüm, ~500 satır, negatif içerik yok, SSOT disiplini (referanslar TDD'ye)
- [ ] PLAN 7 plan, her biri bir TDD Faz'ına 1:1 eşleşir
- [ ] TDD'de "kaldırıldı", "yok", "ölü", "eski" ibareleri yok (§1.2, §8, §9 DİKKAT, §7.1 DEFERRED satırı temizlendi)
- [ ] ARCHITECTURE_GUARD'da eski proje karşılaştırma tablosu yok, ESPN örneği yok
- [ ] Hiçbir v2 dosyasında AI/Claude/ESPN/TML/PandaScore/VLR/Lichess/chess/esports/Kelly/B+/B-/TrailingTP/σ-trailing/scouted/bond_farming referansı yok (TODO.md hariç)
- [ ] TDD durumu APPROVED
- [ ] Tüm dosyalar 400 satır altında (TDD hariç — büyük doc)

---

## 9. Riskler ve Yumuşatma

| Risk | Yumuşatma |
|---|---|
| PRD yazarken negatif kaçak (ör. "Kelly yok" cümlesi) | Yazımdan sonra grep taraması: `kaldır|yok|değil|eski|ölü|kelly|espn|ai|claude|trail` — tümü gözden geçir |
| TDD'den silinen bölümlerin yerine tekrar yazılması gereken eksik bilgi | Silinen bölümler pure negatif — yerini doldurmak gereksiz |
| ARCHITECTURE_GUARD tablosu silindiğinde "bu kural niye var?" sorusu | "Neden Bu Dosya Var?" bölümü 3 satırda cevaplıyor, yeterli |
| PLAN-006/007 P1 olarak işaretlenirken MVP scope'a dahil olmayabilir | TDD §11 P1 olarak veriyor, tutarlı |

---

## 10. Onay Noktası

Kullanıcı bu dosyayı review eder. Onay verirse:
- writing-plans skill çağrılır, implementation için adım adım plan üretilir.
- İlk hedef: PLAN.md yeniden yazımı (en az bağımlılığı olan, tek dosya değişikliği).

Onaylamazsa:
- Değişiklik talepleri bu dosyada güncellenir.
- Self-review tekrar çalıştırılır.
