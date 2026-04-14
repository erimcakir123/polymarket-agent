# Dokümantasyon Hizalama Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PRD/TDD/PLAN/ARCHITECTURE_GUARD dosyalarını TDD v2.0 ile tam tutarlı, pozitif-içerikli (negative-free) hale getirmek.

**Architecture:** SSOT (Single Source of Truth) disiplini — her bilgi tek master dosyada tutulur, diğerleri referans verir. Negatif içerik sadece TODO.md'de (istisna).

**Tech Stack:** Markdown dokümanlar. Kod değişikliği yok. Proje git deposu değil — commit adımı yok, dosya operasyonu + doğrulama.

**Spec:** [docs/superpowers/specs/2026-04-13-doc-alignment-design.md](../specs/2026-04-13-doc-alignment-design.md)

---

## Dosya Yapısı

| Dosya | İşlem | Değişiklik tipi |
|---|---|---|
| `PLAN.md` | Tamamen yeniden yaz | 4 eski PLAN → 7 yeni PLAN |
| `ARCHITECTURE_GUARD.md` | Surgical edit | Tablo sil + 1 örnek düzelt |
| `TDD.md` | Surgical edit | 4 bölüm sil + durum değiştir |
| `PRD.md` | Sıfırdan oluştur | 9 bölüm, ~500 satır |

Bağımlılık sırası: PLAN → ARCH_GUARD → TDD temizlik → TDD APPROVED → PRD → Verification.

---

## Task 1: PLAN.md Yeniden Yaz

**Files:**
- Overwrite: `PLAN.md`

**Amaç**: Mevcut 4 PLAN (3 eski + 1 DONE) silinir. TDD Faz 1-7'ye 1:1 eşleşen 7 yeni PLAN yazılır.

- [ ] **Step 1.1: Mevcut PLAN.md'yi oku ve başlık yapısını not al**

Run: `Read PLAN.md`
Expected: Mevcut içerik okundu. "Nasıl Kullanılır" ve "Plan Formatı" bölümleri korunacak (başlık şablonu), "Aktif Planlar" altındaki 4 PLAN ise tamamen yenilenecek.

- [ ] **Step 1.2: Yeni PLAN.md içeriğini yaz (tek Write operasyonu)**

Dosyanın tam içeriği:

````markdown
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

### PLAN-001: Faz 1 — Foundation

- **Durum**: PROPOSED
- **Tarih**: 2026-04-13
- **Öncelik**: P0
- **Etki**: config/, models/, infrastructure/persistence/, infrastructure/apis/gamma_client.py, infrastructure/wallet.py, infrastructure/executor.py
- **Açıklama**: Proje iskeleti, konfigürasyon, domain modelleri, temel infrastructure (persistence + Gamma API + wallet + executor mock).
- **Adımlar** (TDD §11 Faz 1 ile 1:1):
  1. `config/settings.py` — Pydantic config modelleri
  2. `config/sport_rules.py` — Spor-özel SL/TP/duration tabloları
  3. `config.yaml` — Varsayılan konfigürasyon (TDD §9'daki şablon)
  4. `models/enums.py` — Direction, Confidence, EntryReason, ExitReason
  5. `models/market.py` — MarketData dataclass
  6. `models/position.py` — Position (Pydantic + anchor_probability validator)
  7. `models/signal.py` — Signal (entry kararı)
  8. `infrastructure/persistence/json_store.py` — JSON okuma/yazma
  9. `infrastructure/persistence/trade_logger.py` — JSONL trade log
  10. `infrastructure/persistence/price_history.py` — Fiyat geçmişi
  11. `infrastructure/apis/gamma_client.py` — Polymarket Gamma
  12. `infrastructure/wallet.py` — Polygon wallet
  13. `infrastructure/executor.py` — Emir yürütme (dry_run mock)
  14. `src/main.py` — Tek giriş noktası (argparse + startup), max 50 satır
  15. `.env.example`, `requirements.txt`, `pyproject.toml`
- **Kabul Kriterleri**:
  - [ ] Tüm dizinler TDD §2'deki yapıya uyuyor
  - [ ] `python -c "from src.models import MarketData, Position, Signal"` çalışıyor
  - [ ] config.yaml yüklenebiliyor (Pydantic validation geçiyor)
  - [ ] Her enum için basic test var
  - [ ] JSON store read/write unit test yeşil
  - [ ] Hiçbir infrastructure dosyası domain/strategy import etmiyor
- **Mimari Uyumluluk**: Evet — sadece iskelet, domain I/O yok, main.py 50 satır altı, utils/helpers yasak
- **TDD Referansı**: TDD §11 Faz 1

---

### PLAN-002: Faz 2 — Domain Core

- **Durum**: PROPOSED
- **Tarih**: 2026-04-13
- **Öncelik**: P0
- **Etki**: domain/ katmanı (analysis, risk, portfolio, matching, guards)
- **Açıklama**: Saf iş mantığı — probability, confidence, edge, sizing, circuit breaker, portfolio, matching tabloları, guards.
- **Adımlar** (TDD §11 Faz 2):
  1. `domain/analysis/probability.py` — Bookmaker probability (TDD §6.1)
  2. `domain/analysis/confidence.py` — A/B/C grading (TDD §6.2)
  3. `domain/analysis/edge.py` — Edge + confidence multiplier (TDD §6.3)
  4. `domain/risk/position_sizer.py` — Confidence-based sizing (TDD §6.5)
  5. `domain/risk/circuit_breaker.py` — Daily/hourly/consecutive limits (TDD §6.15)
  6. `domain/risk/cooldown.py` — Ardışık kayıp cooldown
  7. `domain/portfolio/manager.py` — Pozisyon takip
  8. `domain/portfolio/exposure.py` — Exposure cap
  9. `domain/matching/pair_matcher.py` — Takım eşleştirme (migrate)
  10. `domain/matching/slug_parser.py`, `team_resolver.py`, `sport_classifier.py` (migrate)
  11. `domain/matching/odds_sport_keys.py` — Polymarket sport_tag → Odds API key mapping
  12. `domain/matching/bookmaker_weights.py` — Bookmaker ağırlıkları
  13. `domain/guards/manipulation.py` (TDD §6.16)
  14. `domain/guards/liquidity.py` (TDD §6.17)
  15. `domain/guards/blacklist.py`
- **Kabul Kriterleri**:
  - [ ] Tüm domain fonksiyonları pure (no I/O)
  - [ ] Her fonksiyon için unit test var (TDD §10.1 listesi)
  - [ ] `grep -r "import requests\|import httpx\|open(" src/domain/` boş dönüyor
  - [ ] Confidence grading testleri TDD §6.2 örnekleriyle eşleşiyor
  - [ ] Bookmaker probability testleri TDD §6.1 formülüyle eşleşiyor
  - [ ] Circuit breaker 4 senaryosu test ediliyor (daily, hourly, soft, consecutive)
- **Mimari Uyumluluk**: Evet — Kural 2 (domain I/O yasak), Kural 11 (test zorunlu), Kural 4 (max 10 method)
- **TDD Referansı**: TDD §11 Faz 2

---

### PLAN-003: Faz 3 — Entry Pipeline

- **Durum**: PROPOSED
- **Tarih**: 2026-04-13
- **Öncelik**: P0
- **Etki**: infrastructure/apis/odds_client.py, infrastructure/apis/clob_client.py, strategy/enrichment/, strategy/entry/
- **Açıklama**: Odds API entegrasyonu, enrichment, normal entry kararı, gate orchestrator, CLOB emir gönderimi.
- **Adımlar** (TDD §11 Faz 3):
  1. `infrastructure/apis/odds_client.py` — The Odds API istemcisi
  2. `strategy/enrichment/odds_enricher.py` — MarketData + odds verisi birleştirme
  3. `strategy/entry/normal.py` — Normal giriş kararı (TDD §6)
  4. `strategy/entry/gate.py` — Giriş orchestrator (Case A/B logic — TDD §6.4)
  5. `infrastructure/apis/clob_client.py` — Polymarket CLOB emir gönderim
- **Kabul Kriterleri**:
  - [ ] `odds_client.fetch_odds(sport_key)` canlı API ile çalışıyor (dry_run mock ile)
  - [ ] `entry/gate.py` event-level guard kontrolü yapıyor (ARCH Kural 8)
  - [ ] Entry pipeline integration testi: scan → enrich → gate → sizing → signal üretimi
  - [ ] Consensus entry (TDD §6.4) birim testleri
  - [ ] Strategy katmanı domain'e bağlı, infrastructure'dan sadece gate üstünden geçiyor (Kural 1)
- **Mimari Uyumluluk**: Evet — Kural 1 (katman sırası), Kural 8 (event guard)
- **TDD Referansı**: TDD §11 Faz 3

---

### PLAN-004: Faz 4 — Exit Pipeline

- **Durum**: PROPOSED
- **Tarih**: 2026-04-13
- **Öncelik**: P0
- **Etki**: infrastructure/websocket/, strategy/exit/
- **Açıklama**: WebSocket fiyat beslemesi, çıkış stratejileri (flat SL, graduated SL, scale-out, near-resolve, a-conf hold, favored), exit monitor orchestrator.
- **Adımlar** (TDD §11 Faz 4):
  1. `infrastructure/websocket/price_feed.py` — CLOB WS (TDD §8)
  2. `strategy/exit/stop_loss.py` — 9-katman flat SL helper (TDD §6.7)
  3. `strategy/exit/graduated_sl.py` — Elapsed-aware graduated SL (TDD §6.8)
  4. `strategy/exit/scale_out.py` — 3-tier scale-out (TDD §6.6)
  5. `strategy/exit/near_resolve.py` — 94¢ exit + 5dk guard (TDD §6.11)
  6. `strategy/exit/a_conf_hold.py` — Elapsed-gated market flip (TDD §6.9, elapsed ≥ %85)
  7. `strategy/exit/favored.py` — Promote/demote (TDD §6.13)
  8. `strategy/exit/monitor.py` — Exit orchestrator
- **Kabul Kriterleri**:
  - [ ] WebSocket disconnect → 30 sn içinde reconnect
  - [ ] Scale-out 3 tier (25%→40% sat, 50%→kalan 50% sat, tier3=resolution) testleri
  - [ ] A-conf hold: market_flip sadece elapsed ≥ %85'te tetikleniyor
  - [ ] Near-resolve: eff ≥ 94¢ + 5dk pre-match guard testleri
  - [ ] Graduated SL: elapsed tier'ları + price mult + score adj testleri
  - [ ] Exit monitor ilk tetiklenen exit sinyalini uyguluyor (çakışma yönetimi)
- **Mimari Uyumluluk**: Evet — Strategy katmanı, domain'e bağlı, infrastructure WS'ten veri alıyor
- **TDD Referansı**: TDD §11 Faz 4

---

### PLAN-005: Faz 5 — Orkestrasyon

- **Durum**: PROPOSED
- **Tarih**: 2026-04-13
- **Öncelik**: P0
- **Etki**: orchestration/
- **Açıklama**: Process lock, startup (pozisyon geri yükleme), scanner, cycle manager (heavy + light), ana agent döngüsü.
- **Adımlar** (TDD §11 Faz 5):
  1. `orchestration/process_lock.py` — Çoklu instance engelleme
  2. `orchestration/startup.py` — Başlangıç akışı (wallet, persistence, pozisyon restore)
  3. `orchestration/scanner.py` — Market tarama (allowed_sport_tags filter)
  4. `orchestration/cycle_manager.py` — Heavy (30dk) + Light (5sn) cycle interleave
  5. `orchestration/agent.py` — Ana döngü (TDD §4)
- **Kabul Kriterleri**:
  - [ ] Bot 48h dry-run boyunca çökmeden çalışıyor
  - [ ] Crash recovery: startup.py pozisyonları JSON'dan geri yüklüyor
  - [ ] Heavy cycle içinde light cycle interleave çalışıyor (heavy uzun sürse bile light tetikleniyor)
  - [ ] Scanner sadece allowed_sport_tags'teki sporları topluyor (TDD §9)
  - [ ] Night mode (UTC 08-13) cycle süresi 60dk'ya geçiyor
  - [ ] agent.py 400 satırın altında (Kural 3)
- **Mimari Uyumluluk**: Evet — Kural 5 (main.py 50 satır), Kural 3 (400 satır), Kural 4 (god object yok)
- **TDD Referansı**: TDD §11 Faz 5

---

### PLAN-006: Faz 6 — Ek Entry Stratejileri

- **Durum**: PROPOSED
- **Tarih**: 2026-04-13
- **Öncelik**: P1
- **Etki**: strategy/entry/
- **Açıklama**: Early entry, volatility swing, consensus entry stratejileri.
- **Adımlar** (TDD §11 Faz 6):
  1. `strategy/entry/early_entry.py` — 6+ saat öncesi yüksek edge girişi (TDD §9 `early` config)
  2. `strategy/entry/volatility_swing.py` — Düşük fiyatlı underdog scalp (TDD §9 `volatility_swing` config)
  3. `strategy/entry/consensus.py` — Bookmaker+market aynı favori (TDD §6.4, §9 `consensus` config)
- **Kabul Kriterleri**:
  - [ ] Her strateji `entry/gate.py` orchestrator'ı tarafından çağrılıyor
  - [ ] Her strateji için birim test var (edge hesabı, eşik kontrolü, sinyal üretimi)
  - [ ] Consensus: Case A (bookmaker yok) + Case B (her iki kaynak anlaşıyor) senaryoları test ediliyor
  - [ ] Strateji katmanı domain'e bağlı kalıyor (Kural 1)
- **Mimari Uyumluluk**: Evet
- **TDD Referansı**: TDD §11 Faz 6

---

### PLAN-007: Faz 7 — Sunum ve İzleme

- **Durum**: PROPOSED
- **Tarih**: 2026-04-13
- **Öncelik**: P1
- **Etki**: presentation/
- **Açıklama**: Flask dashboard, Telegram notifier, CLI.
- **Adımlar** (TDD §11 Faz 7):
  1. `presentation/dashboard/` — Flask web dashboard (localhost:5050)
  2. `presentation/notifier.py` — Telegram bildirim
  3. `presentation/cli.py` — Komut satırı araçları
- **Kabul Kriterleri**:
  - [ ] Dashboard pozisyonları < 3 sn gecikmeyle gösteriyor
  - [ ] Telegram: entry/exit/CB olaylarında bildirim geliyor (ratelimit-aware)
  - [ ] CLI: `status`, `positions`, `config` komutları çalışıyor
  - [ ] Dashboard Flask app'i orchestration'a bağımlı değil (read-only JSON store)
- **Mimari Uyumluluk**: Evet — Presentation en üst katman, infra'dan okuyor
- **TDD Referansı**: TDD §11 Faz 7

---

*Daha fazla plan gerektiğinde buraya eklenir.*
*Tamamlanan planlar silinir.*
````

Run: `Write PLAN.md <yukarıdaki içerik>`
Expected: Dosya tamamen yenilendi.

- [ ] **Step 1.3: Doğrulama — 7 PLAN var, eski 4 PLAN yok**

Run:
```bash
grep -c "^### PLAN-" "PLAN.md"
```
Expected: `7`

Run:
```bash
grep "^### PLAN-" "PLAN.md"
```
Expected: PLAN-001..PLAN-007 (sırayla), tekrar yok.

- [ ] **Step 1.4: Doğrulama — Negatif ibareler yok**

Run:
```bash
grep -iE "kelly|trailing[_ ]tp|sigma[-_ ]trailing|b\+|b-|scouted|espn|pandascore|lichess|chess|esports|espor|satranç|tml|anthropic|\bai\b|claude" "PLAN.md"
```
Expected: Boş (çıktı yok).

---

## Task 2: ARCHITECTURE_GUARD.md Temizlik

**Files:**
- Modify: `ARCHITECTURE_GUARD.md:49-62` (eski proje karşılaştırma tablosu sil)
- Modify: `ARCHITECTURE_GUARD.md:222` (ESPN örneği → odds_client)

**Amaç**: Tek negatif bölümü (eski sorun/v2 çözüm tablosu) sil; anti-pattern örneğindeki ESPN referansını `odds_client` ile değiştir.

- [ ] **Step 2.1: Tabloyu bulup sil**

Mevcut içerik (satır ~49-62, Edit ile hedef):

```markdown
### 1.2 Eski Projenin Problemleri ve v2 Çözümleri

| Eski Sorun | v2 Çözüm |
|---|---|
| agent.py 70KB god object | Orchestration sadece döngü; iş mantığı Strategy'de |
| entry_gate.py 60KB | Entry pipeline 4 ayrı modül (gate / normal / early / vs / consensus) |
| Tight coupling | Katmanlar arası interface |
| AI cache, ESPN enrichment, TML, esports API'leri | **Hepsi kaldırıldı** — sadece Odds API |
| 4 confidence tier (A/B+/B-/C), yarım geçiş | Temiz A/B/C (eski `confidence.py`'nin son hali) |
| Trailing TP karmaşası | Scale-out tek profit-taking |
| Scouted + FAV promotion + A-conf hold + hold_revoke karışıklığı | Tek sistem: **favored** (eski scouted renamed) + A-conf hold |
| Soccer yanlış kurallarla para kaybetti | Soccer tamamen TODO'ya (bkz. `TODO.md` TODO-001) |
| Espor destek edildi ama 0W/5L | Espor komple kaldırıldı |
```

**NOT**: Yukarıdaki metin mevcut ARCHITECTURE_GUARD.md'de değil. ARCHITECTURE_GUARD'da tablo **yok**, sadece demir kurallar var. Bu tablonun asıl yeri **TDD.md §1.2**'dir — Task 3'te ele alınacak.

Step 2.1 → **ATLA** (ARCHITECTURE_GUARD'da silinecek tablo yok).

- [ ] **Step 2.2: ESPN anti-pattern örneğini düzelt**

Hedef satır: `ARCHITECTURE_GUARD.md:222`

Old content:
```python
# ❌ YASAK: Gizli bağımlılık
class ExitMonitor:
    def check(self):
        from src.infrastructure.apis.espn_client import ESPNClient  # ❌ Lazy import = gizli bağımlılık
        espn = ESPNClient()
        score = espn.get_score(...)  # ❌ Strategy katmanı doğrudan infra çağırıyor
```

New content:
```python
# ❌ YASAK: Gizli bağımlılık
class ExitMonitor:
    def check(self):
        from src.infrastructure.apis.odds_client import OddsClient  # ❌ Lazy import = gizli bağımlılık
        odds = OddsClient()
        odds_data = odds.fetch(...)  # ❌ Strategy katmanı doğrudan infra çağırıyor
```

Run: `Edit ARCHITECTURE_GUARD.md` — yukarıdaki old_string → new_string.
Expected: Sadece bu blok değişti, "ExitMonitor" ismi ve anti-pattern mesajı korundu.

- [ ] **Step 2.3: Doğrulama — ESPN/espn yok**

Run:
```bash
grep -iE "espn" "ARCHITECTURE_GUARD.md"
```
Expected: Boş.

Run:
```bash
grep "odds_client" "ARCHITECTURE_GUARD.md"
```
Expected: 1 eşleşme (düzelttiğimiz satır).

---

## Task 3: TDD.md Temizlik (4 Bölüm Sil)

**Files:**
- Modify: `TDD.md` — 4 ayrı silme işlemi

**Amaç**: TDD'den 4 negatif bölüm silinir. Kalan içerik dokunulmaz.

- [ ] **Step 3.1: §1.2 "Eski Projenin Problemleri ve v2 Çözümleri" tablosunu sil**

Hedef: TDD.md satır ~49-62.

Old content (tam blok):
```markdown
### 1.2 Eski Projenin Problemleri ve v2 Çözümleri

| Eski Sorun | v2 Çözüm |
|---|---|
| agent.py 70KB god object | Orchestration sadece döngü; iş mantığı Strategy'de |
| entry_gate.py 60KB | Entry pipeline 4 ayrı modül (gate / normal / early / vs / consensus) |
| Tight coupling | Katmanlar arası interface |
| AI cache, ESPN enrichment, TML, esports API'leri | **Hepsi kaldırıldı** — sadece Odds API |
| 4 confidence tier (A/B+/B-/C), yarım geçiş | Temiz A/B/C (eski `confidence.py`'nin son hali) |
| Trailing TP karmaşası | Scale-out tek profit-taking |
| Scouted + FAV promotion + A-conf hold + hold_revoke karışıklığı | Tek sistem: **favored** (eski scouted renamed) + A-conf hold |
| Soccer yanlış kurallarla para kaybetti | Soccer tamamen TODO'ya (bkz. `TODO.md` TODO-001) |
| Espor destek edildi ama 0W/5L | Espor komple kaldırıldı |

---
```

New content: (boş — tüm bloğu + sonrasındaki `---` separator'ı sil)

**Dikkat**: Edit işleminde `### 1.2` başlığından bir sonraki `---` separator'ına kadar (dahil) tüm blok silinecek. Eğer bu şekilde yaparsan §1.1'den doğrudan §2'ye geçer. §1'in altında sadece 1.1 kalacak (numarasız da olabilir, ama §1.1 başlığını koruyabiliriz).

**Uygulama**: 
1. TDD.md'yi Read et (önce exact line range doğrula).
2. Edit ile tam bloğu sil — replacement boş string değil, bir önceki `---` ile bir sonraki `## 2` arasında tek bir `---` kalmalı.

Expected after edit: §1.1 biter → tek `---` separator → `## 2. Dizin Yapısı`.

- [ ] **Step 3.2: §7.1 "DEFERRED (bkz. TODO-001)" satırını sil**

Hedef: TDD.md §7.1 içindeki satır ~1086.

Old content:
```markdown
**DEFERRED (bkz. TODO-001)**: Soccer, Cricket, Rugby, Boxing, MMA, AFL, NFL, Handball, Lacrosse.
```

New content: (tamamen silinir, boş satır bırakma)

Expected after edit: §7.1'in "MVP'de aktif sporlar" listesinden sonra doğrudan "### 7.2" başlığına geçer. DEFERRED satırı yok.

- [ ] **Step 3.3: §8 "KALDIRILANLAR" bölümünü sil**

Hedef: TDD.md §8 altındaki "KALDIRILANLAR" alt bölümü (satır ~1114-1120).

Old content:
```markdown
**KALDIRILANLAR** (eski projede vardı):
- ESPN API (enrichment) — AI zamanındaydı, bookmaker-only yaklaşımda gereksiz
- PandaScore (espor) — espor MVP'de yok
- VLR (Valorant) — espor yok
- Lichess / Chess.com (satranç) — satranç yok
- TML (tenis H2H) — Odds API yeterli
- Anthropic (Claude AI) — tamamen kaldırıldı
```

New content: (tamamen silinir)

Expected after edit: §8'de sadece API tablosu kalır (Polymarket Gamma, CLOB REST, CLOB WS, Odds API, Telegram). KALDIRILANLAR alt bölümü yok.

- [ ] **Step 3.4: §9 "DİKKAT: Config'te olmayan eski alanlar" uyarı bloğunu sil**

Hedef: TDD.md §9'un sonu, config.yaml bloğundan sonra (satır ~1262-1268).

Old content:
```markdown
**DİKKAT**: Config'te olmayan eski alanlar (ölü):
- `ai.*` (model, cache, budget)
- `tennis.tml_*` 
- `chess.*`
- `bond_farming.*`
- `trailing_tp.*` (scale-out yeterli)
- `reentry_farming.*`, `live_momentum.*`, `live_dip.*`
```

New content: (tamamen silinir)

Expected after edit: §9 config.yaml bloğundan sonra doğrudan `---` separator ve `## 10. Test Stratejisi` başlığına geçer.

- [ ] **Step 3.5: Doğrulama — TDD'de hiçbir yasaklı ibare yok**

Run:
```bash
grep -iE "kaldırıld|kaldıran|yok diyoruz|ölü alan|deprecated|removed|eski proje|espn|pandascore|lichess|chess\.com|anthropic|\bai[\s_:\.]|claude|\bTML\b|sigma.?trailing|trailing_tp|b_plus|b_minus|b\+|b-|scouted|bond_farming|reentry_farming|live_momentum|live_dip" "TDD.md"
```
Expected: Boş.

**Alt istisnalar**: Eğer hâlâ `kelly` veya `draw` geçiyorsa kontekstine bak:
- `"no Kelly"` veya `"Kelly YOK"` → sil/yeniden yaz
- `"draw"` → TODO-001 referansı dışında geçmemeli

Run:
```bash
grep -iE "kelly|trailing tp|σ-trailing" "TDD.md"
```
Expected: Boş.

---

## Task 4: TDD.md Durum DRAFT → APPROVED

**Files:**
- Modify: `TDD.md:4`

- [ ] **Step 4.1: Durum satırını güncelle**

Old content:
```
> Durum: DRAFT — Onay bekliyor
```

New content:
```
> Durum: APPROVED (2026-04-13)
```

Run: `Edit TDD.md` — yukarıdaki old → new.

- [ ] **Step 4.2: Doğrulama**

Run:
```bash
head -n 10 "TDD.md"
```
Expected: "Durum: APPROVED (2026-04-13)" görünüyor, DRAFT yok.

---

## Task 5: PRD.md Sıfırdan Yaz

**Files:**
- Create: `PRD.md`

**Amaç**: 9 bölümlük, ~500 satır, pozitif-içerikli, SSOT disiplinli PRD.

- [ ] **Step 5.1: PRD.md'yi yaz (tek Write operasyonu)**

Dosyanın tam içeriği:

````markdown
# PRD — Polymarket Agent 2.0

> Ürün gereksinimleri ve demir kurallar.
> Version: 2.0 | Tarih: 2026-04-13 | Durum: APPROVED
>
> **SSOT ilkesi**: Bu dosya "ne" ve "neden" sorularına cevap verir. Teknik "nasıl" için TDD.md'ye referans verilir.

---

## 1. Giriş

Polymarket Agent 2.0, Polymarket tahmin piyasalarında otomatik trading yapan bir bot. Odds API üzerinden 20+ bookmaker'ın konsensüs olasılığını çıkarır, Polymarket'teki piyasa fiyatıyla karşılaştırarak pozitif beklenen değer (edge) tespit eder, çok katmanlı risk yönetimiyle pozisyon açar ve yönetir.

Çalışma mantığı tek cümlede: **Bookmaker konsensüsü + piyasa fiyatı fırsatı → boyutlandır → aç → izle → çık.**

---

## 2. Demir Kurallar

Bu kuralların hiçbiri ihlal edilemez. Her biri ya mimari bütünlüğü ya da sermaye güvenliğini korur.

### 2.1 P(YES) Anchor Kuralı
Olasılık her zaman P(YES) olarak saklanır. BUY_YES de BUY_NO da olsa, `anchor_probability = P(YES)` değişmez. Yön ayarlaması karar mantığında yapılır, saklama yapılmaz. (bkz. ARCHITECTURE_GUARD Kural 7, TDD §5.2)

### 2.2 Event-Level Guard
Aynı `event_id`'ye sahip iki pozisyon ASLA açılamaz. "Man City vs Brighton" maçında BUY_YES "City wins" varsa, BUY_NO "Brighton wins" açılamaz — aynı event. Bu kural `entry/gate.py` seviyesinde kontrol edilir. (bkz. ARCHITECTURE_GUARD Kural 8, TDD §6.4)

### 2.3 Confidence-Based Sizing
Pozisyon boyutu confidence seviyesine göre belirlenir:
- **A**: bankroll × %5
- **B**: bankroll × %4
- **C**: giriş yok (blok)

Ek çarpanlar `max_single_bet_usdc` ve `max_bet_pct` cap'lerine tabidir. (bkz. TDD §6.5)

### 2.4 Bookmaker-Derived Probability
P(YES), Odds API'den çekilen bookmaker verisiyle hesaplanır. Pinnacle/Betfair gibi sharp book'lar `bookmaker_weights` ile ağırlıklandırılır. (bkz. TDD §6.1)

### 2.5 3-Katmanlı Cycle
Bot üç cycle seviyesinde çalışır:
- **WebSocket**: anlık fiyat tick (SL + scale-out)
- **Light (5 sn)**: hızlı çıkış kontrolü
- **Heavy (30 dk)**: scan + enrichment + entry kararları

Heavy cycle içinde light cycle interleave eder (heavy uzun sürerse light yine tetiklenir). Gece modunda (UTC 08-13) heavy 60 dk'ya uzar. (bkz. TDD §4)

### 2.6 Circuit Breaker Zorunludur
Aşağıdaki eşiklerden birinde bot yeni giriş yapmaz:
- Günlük kayıp ≥ %8 → 120 dk cooldown
- Saatlik kayıp ≥ %5 → 60 dk cooldown
- 4 ardışık kayıp → 60 dk cooldown
- Soft blok: günlük kayıp ≥ %3 → yeni giriş askıda

Circuit breaker devre dışı bırakılamaz. (bkz. TDD §6.15)

### 2.7 Scale-Out Profit-Taking
Kâr alma tek mekanizma ile: 3-tier scale-out.
- **Tier 1**: PnL ≥ %25 → pozisyonun %40'ını sat
- **Tier 2**: PnL ≥ %50 → kalan pozisyonun %50'sini sat
- **Tier 3**: Resolution'a kadar hold

(bkz. TDD §6.6)

---

## 3. Operasyonel Akışlar

### 3.1 Bot Başlatma Akışı
1. `main.py` argparse (mode: dry_run | paper | live) ve config.yaml yükler.
2. `orchestration/process_lock.py` tek instance garantisi verir.
3. `orchestration/startup.py` wallet'i bağlar, persistence'ı açar, açık pozisyonları JSON store'dan geri yükler.
4. `agent.py` ana döngüyü başlatır → heavy cycle tetiklenir.

### 3.2 Entry Akışı (Heavy Cycle)
1. **Scan**: `scanner.py` Polymarket Gamma'dan `allowed_sport_tags` filtreli market'ler çeker (TDD §9).
2. **Match**: `domain/matching/` modülleri Polymarket market'ini Odds API sport key'ine eşler.
3. **Enrich**: `strategy/enrichment/odds_enricher.py` Odds API'dan bookmaker probability çeker.
4. **Gate**: `strategy/entry/gate.py` event-guard + manipulation + liquidity + confidence + edge kontrolü yapar.
5. **Size**: `domain/risk/position_sizer.py` confidence bazlı boyut üretir, cap'lere uygular.
6. **Execute**: `infrastructure/executor.py` CLOB client üzerinden emri gönderir (dry_run modunda loglar).
7. **Record**: Pozisyon JSON store'a yazılır, trade log JSONL'e eklenir.

### 3.3 Light Cycle İzleme (5 sn)
Her 5 saniyede bir:
1. WebSocket tick'lerinden son fiyatlar okunur.
2. Açık pozisyonlar için flat SL (`stop_loss.py`) ve scale-out (`scale_out.py`) kontrolü yapılır.
3. Tetiklenen çıkış sinyali varsa `exit/monitor.py` üzerinden ilkine göre emir gönderilir.

### 3.4 Exit Akışı (Heavy Cycle)
Heavy cycle sırasında açık pozisyonlar için:
1. **Graduated SL**: elapsed-aware dinamik SL (TDD §6.8).
2. **Near-Resolve**: eff_price ≥ 94¢ + 5 dk pre-match guard → çık (TDD §6.11).
3. **A-Conf Hold**: confidence=A + entry ≥ 60¢ → graduated SL atlanır; market_flip sadece elapsed ≥ %85'te tetiklenir (TDD §6.9).
4. **Favored**: eff_price ≥ 65¢ + confidence ∈ {A, B} → promoted; altı demoted (TDD §6.13).
5. **Never-in-Profit Guard**: peak_pnl hiç pozitif olmamış + elapsed > %70 → daha agresif SL (TDD §6.10).

### 3.5 Circuit Breaker Tetiklendiğinde
1. `circuit_breaker.py` bankroll durumunu her entry öncesi kontrol eder.
2. Eşik aşılırsa yeni entry reddedilir, pozitif log + Telegram bildirimi.
3. Cooldown süresi dolana kadar bot sadece **çıkış** kararları alır (açık pozisyon yönetimi devam).
4. Cooldown sonrası otomatik devreye girer.

---

## 4. Fonksiyonel Gereksinimler

8 yetenek grubu. Detaylar TDD'ye referans.

### F1. Scan
Bot Polymarket Gamma API'dan canlı market'leri keşfeder. `allowed_sport_tags` filtresi uygular. Max `max_markets_per_cycle=300` limitiyle sınırlı. (bkz. TDD §3.4, §9 scanner config)

### F2. Enrich
Her adaya Odds API'dan bookmaker verisi çekilir. `domain/matching/` modülleri Polymarket slug'ını Odds API sport key'ine dönüştürür. `bookmaker_weights.py` sharp book'ları ağırlıklandırır. (bkz. TDD §6.1)

### F3. Entry Decision
`strategy/entry/gate.py` giriş kararını orchestrate eder. 4 entry stratejisi: normal, early_entry (6+ saat öncesi), volatility_swing (düşük fiyatlı underdog), consensus (bookmaker+market aynı favori). Her strateji edge + confidence + guards'tan geçer. (bkz. TDD §6.4, §11 Faz 3 ve Faz 6)

### F4. Position Sizing
Confidence-based. A=%5, B=%4, C=blok. `max_single_bet_usdc` ve `max_bet_pct` cap'leri uygulanır. Scale-in yok. (bkz. TDD §6.5)

### F5. Execute
`executor.py` 3 modda çalışır: `dry_run` (log-only), `paper` (mock fills), `live` (gerçek CLOB emri). Her emir trade log'a JSONL formatında yazılır. (bkz. TDD §8)

### F6. Monitor
3 katmanlı izleme: WS tick (anlık), Light cycle (5 sn), Heavy cycle (30 dk). Pozisyon durumu JSON store'da tutulur, dashboard anlık okur. (bkz. TDD §4)

### F7. Exit
7 çıkış mekanizması: flat SL, graduated SL, scale-out, near-resolve, a_conf_hold, favored, manual. İlk tetiklenen sinyal uygulanır. (bkz. TDD §6.6–§6.14)

### F8. Report
3 sunum kanalı: Flask dashboard (localhost:5050), Telegram bildirim (entry/exit/CB), JSONL trade log (audit). (bkz. TDD §11 Faz 7)

---

## 5. Non-Fonksiyonel Gereksinimler

### 5.1 Latency
- Heavy cycle ≤ 30 sn (scan + enrichment + entry decision)
- Light cycle ≤ 1 sn (SL + scale-out kontrolü)
- WebSocket tick → exit decision ≤ 500 ms

### 5.2 Uptime
- MVP hedefi: 48 saat kesintisiz dry_run
- WebSocket disconnect → 30 sn içinde reconnect (TDD §12)

### 5.3 Crash Recovery
- `startup.py` açık pozisyonları `positions.json`'dan geri yükler
- Trade log JSONL append-only, crash'ten sonra replayable
- Process lock çift instance engeller

### 5.4 Observability
- Flask dashboard: pozisyonlar, PnL, circuit breaker durumu, < 3 sn gecikme
- Telegram: entry/exit/CB olayları
- JSONL trade log: audit için append-only

### 5.5 Çalışma Modları
- `dry_run`: API çağrıları canlı, emir gönderimi yok — default test modu
- `paper`: mock fills, bankroll simülasyonu
- `live`: gerçek emir + gerçek USDC

### 5.6 Test Kapsamı
- Domain katmanı: > %90 unit test coverage zorunlu
- Strategy katmanı: > %80 unit test coverage
- Integration test: entry pipeline + exit pipeline + WS reconnect

---

## 6. Teknik Kısıtlar

### 6.1 API Limitleri
- **The Odds API**: 20K kredi/ay (paid tier), her `fetch_odds` 1-10 kredi
- **Polymarket CLOB REST**: ~100 istek/dk
- **Polymarket Gamma**: rate limit belirsiz, ~300 market/cycle güvenli
- **Telegram**: 30 mesaj/sn

### 6.2 Altyapı
- **Chain**: Polygon mainnet
- **Ödeme**: USDC (6 decimal)
- **Python**: 3.12+
- **OS**: Linux (production), Windows (dev)

### 6.3 Cycle Süreleri
- Heavy: 30 dk (gündüz), 60 dk (gece UTC 08-13)
- Light: 5 sn
- WebSocket: sürekli (disconnect + reconnect)

### 6.4 Market Filtreleme
- Min likidite: $1000
- Max süre: 14 gün (maç başlangıcından öncesi)
- Allowed categories: `sports` (yalnızca)
- Allowed sport_tags: `baseball_*`, `basketball_*`, `icehockey_*`, `americanfootball_ncaaf|cfl|ufl`, `tennis_*` (dinamik), `golf_lpga_tour|liv_tour` (TDD §9)

---

## 7. Savunma Mekanizmaları

4 katmanlı koruma. Her biri pozitif feature — bot'un aktif yaptığı kontroller.

### 7.1 Manipulation Guard
`domain/guards/manipulation.py` şu kontrolleri yapar:
- Min likidite: $10K toplam book
- Self-resolving market tespiti (kişi/kurum + self-resolving fiil paterni)

(bkz. TDD §6.16)

### 7.2 Liquidity Check
`domain/guards/liquidity.py` entry + exit seviyelerinde:
- **Entry**: min $100 depth; pozisyon > %20 book payı ise boyut yarıya iner
- **Exit**: min %80 fill ratio; altıysa emir bölünür

(bkz. TDD §6.17)

### 7.3 Circuit Breaker
Bölüm 2.6'daki eşiklerin aktif enforcement'ı. `domain/risk/circuit_breaker.py` her entry öncesi bankroll durumunu kontrol eder. (bkz. TDD §6.15)

### 7.4 Event-Level Guard
`strategy/entry/gate.py` her entry kararında event_id kontrolü yapar. Açık pozisyon listesinde aynı event_id varsa entry reddedilir. (bkz. Demir Kural 2.2, ARCHITECTURE_GUARD Kural 8)

---

## 8. Sözlük

| Terim | Tanım |
|---|---|
| **anchor** / `anchor_probability` | Bookmaker konsensüsünden hesaplanan P(YES). Pozisyon yönünden bağımsız saklanır. |
| **P(YES)** | Polymarket market'indeki YES outcome'unun olasılığı (0.0 – 1.0) |
| **edge** | Piyasa fiyatı ile anchor arasındaki beklenen değer farkı (`anchor - market_price` BUY_YES için) |
| **eff_price** | Effective price — pozisyon için pratik fiyat (market mid ± slippage tahmini) |
| **direction** | `BUY_YES` / `BUY_NO` / `HOLD` — Direction enum |
| **confidence** | `A` (sharp book veya ≥5 bookmaker) / `B` (≥3 bookmaker) / `C` (yetersiz, giriş blok) |
| **favored** | Pozisyonun elverişli durumda olduğunu işaretleyen flag (eff ≥ 65¢ + conf ∈ {A,B}) |
| **scale-out** | Kademeli kâr alma: PnL eşiklerinde pozisyonun bir kısmı satılır |
| **elapsed** | Maç ilerleme oranı (0.0 = başlangıç, 1.0 = bitiş) |
| **consensus** | Bookmaker ve Polymarket market'inin aynı favori üzerinde anlaşması |

---

## 9. Referanslar

- [TDD.md](TDD.md) — Teknik tasarım, algoritmalar, veri modelleri, cycle detayları
- [ARCHITECTURE_GUARD.md](ARCHITECTURE_GUARD.md) — Mimari kurallar (12 demir kural + anti-pattern'ler)
- [TODO.md](TODO.md) — Post-MVP işler (draw-possible sporlar sırayla)
- [CLAUDE.md](CLAUDE.md) — Claude Code davranış kuralları, TODO yönetimi, mimari koruma
- [PLAN.md](PLAN.md) — Aktif implementation planları (PLAN-001..PLAN-007)
````

Run: `Write PRD.md <yukarıdaki içerik>`

- [ ] **Step 5.2: Doğrulama — 9 bölüm var**

Run:
```bash
grep -c "^## [0-9]" "PRD.md"
```
Expected: `9` (Bölüm 1-9)

- [ ] **Step 5.3: Doğrulama — yasaklı ibareler yok**

Run:
```bash
grep -iE "kaldırıld|yok[^t]|eski proje|espn|pandascore|lichess|chess\.com|anthropic|\bclaude\b|\bai[\s_:\.]|\bTML\b|sigma.?trailing|trailing[_ ]tp|kelly|b\+|b-|scouted|bond_farming|reentry_farming|live_momentum|live_dip|soccer|cricket|rugby|boxing|\bmma\b|\bafl\b|\bnfl\b|handball|lacrosse|drawn?\b|satranç|tenis H2H" "PRD.md"
```
Expected: Boş.

**İstisnalar**:
- `BUY_NO`, `tennis_*` (sport_tag), "Scale-Out" gibi teknik terimler normal
- "no" standalone değilse (ör. `no-Kelly`, `no draw`) sıkıntı yok; tek başına "yok" cümlesi varsa düzelt

- [ ] **Step 5.4: Doğrulama — TDD referansları mevcut**

Run:
```bash
grep -oE "TDD §[0-9]+(\.[0-9]+)?" "PRD.md" | sort -u
```
Expected: En az 10 farklı TDD referansı (§3.4, §4, §5.2, §6.1, §6.4, §6.5, §6.6, §6.8, §6.9, §6.10, §6.11, §6.13, §6.15, §6.16, §6.17, §8, §9, §11, §12).

- [ ] **Step 5.5: Doğrulama — satır sayısı ~500**

Run:
```bash
wc -l "PRD.md"
```
Expected: 300-600 satır arası (hedef ~500).

---

## Task 6: Final Doğrulama (Tüm Dosyalarda Yasaklı Terim Taraması)

**Files:** Tüm v2 dokümanları

**Amaç**: TODO.md dışındaki hiçbir dosyada yasaklı referans kalmadığını kanıtla.

- [ ] **Step 6.1: Geniş yasaklı terim taraması (TODO.md hariç)**

Run:
```bash
grep -iErn --include="*.md" --exclude="TODO.md" --exclude-dir="docs" "espn|pandascore|lichess|chess\.com|anthropic|\bTML\b|sigma.?trailing|trailing[_ ]tp|kelly|\bB\+\b|\bB-\b|scouted|bond_farming|reentry_farming|live_momentum|live_dip" .
```
Expected: Boş çıktı (hiçbir eşleşme).

**Not**: `--exclude-dir="docs"` design doc'u ve plan dosyasını hariç tutar (bunlar process artifact, historical record tutuyor).

- [ ] **Step 6.2: "Claude" ve "AI" taraması (CLAUDE.md hariç — dosya adı geçer)**

Run:
```bash
grep -iErn --include="*.md" --exclude="TODO.md" --exclude="CLAUDE.md" --exclude-dir="docs" "\bclaude\b|\banthropic\b" .
```
Expected: Boş.

Run:
```bash
grep -En --include="*.md" --exclude="TODO.md" --exclude-dir="docs" "\bAI\b|\bAI-" *.md
```
Expected: Boş.

- [ ] **Step 6.3: Eski feature adları taraması**

Run:
```bash
grep -iErn --include="*.md" --exclude="TODO.md" --exclude-dir="docs" "satranç|esports|espor|valorant|\bCS2\b|\bLoL\b|\bdota" .
```
Expected: Boş.

- [ ] **Step 6.4: Draw-possible sporların aktif kural olarak geçmediğini doğrula**

TODO.md'de kural listesi normal. PRD/TDD/PLAN'da sport olarak **kural** geçmemeli.

Run:
```bash
grep -iEn "^[^|#>]*soccer.*(sl|stop_loss|match_duration|rule)" "PRD.md" "TDD.md" "PLAN.md" 2>/dev/null
```
Expected: Boş (sport_rules bağlamında soccer/cricket/rugby vb. yok).

- [ ] **Step 6.5: Cross-reference sağlık kontrolü**

PRD'deki TDD bölüm referansları TDD'de var mı?

Run:
```bash
# PRD'deki referansları çıkar
grep -oE "TDD §[0-9]+(\.[0-9]+)?" "PRD.md" | sort -u > /tmp/prd_refs.txt
# TDD'deki mevcut bölüm başlıklarını çıkar
grep -oE "^#+ [0-9]+(\.[0-9]+)? " "TDD.md" | grep -oE "[0-9]+(\.[0-9]+)?" | sort -u > /tmp/tdd_sections.txt
# PRD'deki referansların TDD'de olup olmadığını kontrol et
while read ref; do
  sec=$(echo "$ref" | grep -oE "[0-9]+(\.[0-9]+)?")
  grep -q "^$sec$" /tmp/tdd_sections.txt || echo "MISSING: $ref"
done < /tmp/prd_refs.txt
```
Expected: Hiç "MISSING: ..." çıktısı yok.

- [ ] **Step 6.6: Dosya boyutları**

Run:
```bash
wc -l *.md
```
Expected:
- `PRD.md`: 300-600 satır
- `TDD.md`: ~1380 (silmeler sonrası)
- `PLAN.md`: ~250 satır
- `ARCHITECTURE_GUARD.md`: ~280 satır (321 − 13 satır silinmedi, yalnız ESPN düzeltmesi)
- `CLAUDE.md`, `TODO.md`: değişmedi

**Dikkat**: ARCHITECTURE_GUARD'da tablo silinmedi (yoktu zaten). Sadece ESPN örneği düzeltildi.

---

## Sonuç

Tüm task'lar tamamlandığında:
- PRD.md: 9 bölüm, ~500 satır, SSOT disiplini
- TDD.md: 4 negatif bölüm silinmiş, durum APPROVED
- PLAN.md: 7 plan (TDD Faz 1-7 1:1)
- ARCHITECTURE_GUARD.md: ESPN örneği odds_client
- Hiçbir v2 dosyasında (TODO hariç) yasaklı referans yok
- Cross-reference sağlığı: PRD → TDD bölümleri mevcut

Sonraki adım: PLAN-001'i execute etmeye başlamak için ayrı bir implementation plan yazılır (Faz 1 — Foundation).
