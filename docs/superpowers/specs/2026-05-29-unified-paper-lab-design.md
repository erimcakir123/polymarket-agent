# Unified Paper Lab — Design (Basket + Tennis, Tek Bot, Hiper Gerçekçi Paper)

- **Tarih:** 2026-05-29
- **Durum:** DRAFT (kullanıcı review bekliyor)
- **Ortak:** Erim (teknik olmayan proje sahibi)
- **Tetikleyici:** Tennis lab (feature/tennis-lab) ile main bot ayrı duruyor; iki ayrı process + bankroll + dashboard yormakta. Hedef: gerçek parayla başlamadan önce TEK gerçekçi paper bot.

---

## 1. Vizyon (tek paragraf)

Şu an iki ayrı bot var: (a) **main bot** master'da — WNBA/NBA/NHL trade alıyor, dry_run modunda (hayali fill, alıcı/satıcı varlığı kontrol edilmiyor), (b) **tennis lab** feature/tennis-lab branch'ında — Sackmann tabanlı tennis modeli + canlı orderbook tabanlı paper executor (REJECTED/PARTIAL_FILL/FILLED gerçek fill simülasyonu). Bu spec iki bota tek bot haline getirir: tennis lab'ın **paper realism mantığı** main bot executor'ına entegre edilir, tennis-spesifik bug fix + data refresher master'a alınır, spor portföyü sadece **basket (WNBA + NBA) + tennis (ATP + WTA)** olur. Sonuç: tek process, tek bankroll, tek dashboard, hiper gerçekçi fill, gerçek parayla başlamaya hazır.

---

## 2. Kapsam — IN / OUT

### IN (bu spec yapacaklar)

| # | Konu | Detay |
|---|---|---|
| 1 | **Spor whitelist kısıtlama** | `allowed_sport_tags` → sadece `nba, wnba, ncaab, wncaab, cbb, euroleague, nbl, atp, wta` |
| 2 | **Tennis whitelist'e ekle** | Bug fix öncesi `tennis ana botta KAPALI` yorumu vardı; aktifleştir |
| 3 | **Spor whitelist çıkarmalar** | NHL, NCAAF, CFL, UFL, MMA, UFC, Boxing, LPGA*, LIV*, PGA* → hepsi çıkar |
| 4 | **Paper realism executor** | Mode.PAPER enum + clob orderbook walk + slippage + min_fill_ratio + partial fill + retry |
| 5 | **Mode default = paper** | dry_run yedek olarak kalır (test için), live ileri faz |
| 6 | **Tennis bug fix migrasyonu** | `tennis_player_matcher` surname-collision fix + test |
| 7 | **Gamma series_id desteği** | `gamma_client` ITF/series-based fetch (tennis için kritik, ATP/WTA da yararlanır) |
| 8 | **Sackmann startup refresher** | Tennis aktif olduğu için startup'ta CSV cache stale ise refresh + rebuild ratings |
| 9 | **Tennis-spesifik exclude_combos** | tennis_set_totals (-$63), tennis_first_set_winner (-$162) negative-EV → exclude (config_tennis'ten al) |
| 10 | **Tennis-spesifik config değerleri** | bimodal $15 cap (zaten ana botta var), tennis bimodal market_types (zaten sport_rules'ta var) |
| 11 | **Tennis-only enrichment** | scanner'da tennis branch'i (set_totals, set_handicap, match_total_games market_type'ları) |
| 12 | **Bankroll birleşme** | Tek `initial_bankroll`, exposure cap basket + tennis ortak |
| 13 | **Tek entry script** | `src/main.py` korunur; `scripts/tennis_main.py` silinir |
| 14 | **Tek config** | `config.yaml` korunur; `config_tennis.yaml` silinir |
| 15 | **Branch konsolidasyonu** | feature/tennis-lab → master merge sonrası silinir, tag'lenir |
| 16 | **Geri dönüş yedeği** | git tag `pre-unified-2026-05-29` + state snapshot |
| 17 | **paper_executions.jsonl audit** | Her fill kararı book snapshot (top 3 bid/ask) ile loglanır |

### OUT (bu spec YAPMAYACAKLAR)

| # | Konu | Sebep |
|---|---|---|
| 1 | Live mode yazımı | Ayrı spec, gerçek cüzdan bağlama farklı domain |
| 2 | NBA spread aç | `sport_rules.py` `spread_blocked: True` — kanıt yok, korunur |
| 3 | Diğer basket alt-ligler (NCAAB/WNCAAB/CBB/EuroLeague/NBL) için yeni kural | Default rule yeterli, ayrı geliştirme gereksiz |
| 4 | MLB submarket | Zaten `enabled: false`, baseball çıkarıldı, dokunulmuyor |
| 5 | Yeni dashboard widget | Mevcut dashboard yeterli; sadece "PAPER" tag topbar'a eklenir |
| 6 | Stratejide değişiklik | Edge formülü, confidence grading, entry gate kuralları AYNI |
| 7 | Tennis ratings build pipeline değişikliği | Mevcut Sackmann pipeline aynı kalır |
| 8 | Dry_run'ın silinmesi | Test fonksiyonu için kalır, sadece default değil |

---

## 3. Mimari Karar

**Beş katmanlı mimari korunur (ARCH_GUARD Kural 1).**

```
PRESENTATION (dashboard, topbar "PAPER" tag)
       ↓
ORCHESTRATION (agent, executor — paper mode dispatch)
       ↓
STRATEGY (entry_gate, exit signals — değişiklik yok)
       ↓
DOMAIN (paper fill walker — saf hesap, I/O yok)
       ↓
INFRASTRUCTURE (clob_client.fetch_book, gamma_client series_id, sackmann_refresher)
```

**Yeni modüller:**

| Modül | Katman | Sorumluluk | Tahmini satır |
|---|---|---|---|
| `src/domain/execution/paper_fill.py` | domain | Saf fonksiyon: orderbook walk, slippage + min_fill_ratio kontrolü, FillResult döner (FILLED/PARTIAL_FILL/REJECTED + weighted_price + filled_shares) | ~150 |
| `src/infrastructure/apis/clob_book.py` | infrastructure | clob.polymarket.com/book?token_id=X read-only fetch + 5sn cache | ~80 |
| `src/infrastructure/audit/paper_executions.py` | infrastructure | paper_executions.jsonl writer (book snapshot dahil) | ~60 |
| `src/orchestration/paper_executor.py` | orchestration | Mode.PAPER iken executor dispatch; fetch_book → paper_fill → log → state güncelle | ~200 |
| `src/infrastructure/data/sackmann_refresher.py` | infrastructure | Tennis lab'dan migrasyon, CSV cache stale → download + rebuild | ~tennis lab'daki halinden |

**Mevcut modüllerde değişiklik:**

| Modül | Değişiklik |
|---|---|
| `src/config/settings.py` | `Mode.PAPER` enum + `paper:` config bloğu (slippage, min_fill, cache_ttl) |
| `src/orchestration/executor.py` | Mode dispatch: dry_run / paper / live |
| `src/orchestration/factory.py` | Mode'a göre executor instantiate; tennis aktif olduğunda Sackmann refresher build_deps öncesi çağrı |
| `src/orchestration/scanner.py` | `allowed_sport_tags` güncellenmiş config'i okur (kod değişikliği yok, sadece config) |
| `src/infrastructure/apis/gamma_client.py` | `_fetch_league_sources` (tag + series) — tennis branch'tan al |
| `src/domain/matching/tennis_player_matcher.py` | Surname-collision fix — tennis branch'tan al |
| `src/presentation/dashboard/static/js/*.js` | Topbar "PAPER" rozet (mode=paper iken) |
| `config.yaml` | allowed_sport_tags güncelle, paper bloğu ekle, mode: paper |
| `scripts/reboot.py` | `--live-lab` marker kaldır (artık tek bot, kafa karışıklığı yok) |
| `scripts/tennis_main.py` | **SİLİN** |
| `config_tennis.yaml` | **SİLİN** (exclude_combos main config'e taşı) |

**Mimari ihlal kontrolü:**
- ✓ Domain'de I/O yok (paper_fill.py saf hesap, book parametre olarak gelir)
- ✓ Katman ihlali yok (paper_executor orchestration, paper_fill domain, clob_book infra)
- ✓ Magic number yok (slippage/min_fill/cache_ttl config'den)
- ✓ <400 satır (paper_executor ~200, paper_fill ~150)
- ✓ utils/misc yok (her yeni modül net bir katman + sorumluluk)

---

## 4. Davranış Kuralları

### 4.1. Mode dispatch

```
Mode = dry_run | paper | live
Default = paper
```

- **dry_run:** Mevcut davranış. Fill her zaman başarılı, slippage 0, market price kullanılır. Test için korunur.
- **paper:** Bu spec'in odağı. Gerçek orderbook → gerçekçi fill. Polymarket'e gerçek emir GİTMEZ.
- **live:** Bu spec'in dışında. Wallet bağlı, gerçek emir. Sonraki faz.

### 4.2. Paper BUY simülasyonu

Girdi: `token_id`, `target_price`, `target_size_usdc`.

1. `clob_book.fetch_book(token_id)` → asks listesi `[(price, size), ...]` artan sıralı.
2. `paper_fill.walk_buy(asks, target_price, target_size_usdc, max_slippage_pct, min_fill_ratio)`:
   - Asks'i artan sırada yürü.
   - Her seviyede satın al: `level_price <= target_price * (1 + max_slippage_pct)` ise.
   - Toplam satın alınan share × weighted_avg_price birikir.
   - Tamamlanan dolar hedef dolar × `min_fill_ratio` (default 0.95) altında → REJECTED.
   - Aksi → FILLED, weighted_avg_price ve filled_shares ile state güncellenir.
3. Sonuç `paper_executions.jsonl`'a yazılır (book snapshot top 3 ask + karar + sonuç).
4. REJECTED → pozisyon açılmaz, bot bir sonraki cycle'da yeniden değerlendirebilir.

### 4.3. Paper SELL simülasyonu (exit)

Girdi: `token_id`, `position.shares`, `target_price` (entry/SL/scale-out target).

1. `clob_book.fetch_book(token_id)` → bids listesi `[(price, size), ...]` azalan sıralı.
2. `paper_fill.walk_sell(bids, target_price, shares, max_slippage_pct)`:
   - Bids'i azalan sırada yürü.
   - Her seviyede sat: `level_price >= target_price * (1 - max_slippage_pct)` ise.
   - Tamamlanan share × weighted_avg_price birikir.
   - Tüm bids tükenmesine rağmen 0 share dolduysa → REJECTED.
   - Kısmi doluysa → PARTIAL_FILL. Kalan shares pozisyonda kalır; bir sonraki cycle yeniden denenir.
   - Tam doluysa → FILLED.
3. Sonuç `paper_executions.jsonl`'a yazılır.
4. **Force-close timeout:** `paper_fill.walk_sell` REJECTED dönerse force-close 0 ile realize ETMEZ; pozisyon "stuck" durumuna geçer ve N sonraki cycle yeniden denenir. Max retry sonrası alarm (dashboard'da görünür, gerçek live'da operatör müdahalesi gerekir). Bu MEVCUT "bid yoksa 0 ile realize" davranışını DEĞİŞTİRİR — paper'da 0 hayali, sürpriz pnl yaratır.

### 4.4. Cache mantığı

- `clob_book` LRU cache, key=token_id, TTL=5sn (config'den).
- Aynı cycle içinde aynı token için tekrar fetch yapılmaz (entry + exit guard cycle paralellikleri).

### 4.5. Sport whitelist (kapalı liste)

```yaml
allowed_sport_tags:
  # Basket
  - nba
  - wnba
  - ncaab
  - wncaab
  - cbb
  - euroleague
  - nbl
  # Tennis
  - atp
  - wta
```

> NCAAB/WNCAAB/CBB/EuroLeague/NBL pratikte trade üretmedi (0 trade tarihte) ama basket portföyünde teorik açık tutuluyor — sezon başlarsa basket altmarket ekosistemi içinde kalır, NHL/golf gibi farklı dinamik değil.
>
> NHL çıkarıldı — 13 trade, %0 win rate, -$57 net (kullanıcı kararı: sadece basket + tennis).

### 4.6. Bankroll

- `initial_bankroll` tek değer (default 1000 USDC).
- Exposure cap basket + tennis ortak (`max_exposure_pct` global).
- Tennis bimodal sizing ($15/$10 A/B) ile basket fixed sizing ($50/$30 A/B) ortak kasadan çekilir. `sport_rules.is_bimodal_market(sport_tag, market_type)` zaten ayrımı yapıyor.

### 4.7. Tennis-spesifik exclude_combos

config_tennis'ten alınıp ana config'e taşınır:

```yaml
edge:
  exclude_combos:
    - {tour: atp, market_type: tennis_set_totals, confidence: A}
    - {tour: atp, market_type: tennis_set_totals, confidence: B}
    - {tour: wta, market_type: tennis_set_totals, confidence: A}
    - {tour: wta, market_type: tennis_set_totals, confidence: B}
    - {tour: atp, market_type: tennis_first_set_winner, confidence: A}
    - {tour: atp, market_type: tennis_first_set_winner, confidence: B}
    - {tour: wta, market_type: tennis_first_set_winner, confidence: A}
    - {tour: wta, market_type: tennis_first_set_winner, confidence: B}
```

Sebep: tennis paper lab'ı 97 trade analizi (post-spike-removal) → bu iki sub-market net negatif EV. Sackmann modeli bu iki market'te %16 ve %56 doğru, market sırasıyla %72 ve %69 → modele güvenilmez.

### 4.8. Sackmann startup refresher

Tennis aktif olduğu için `main.py` startup'ta:

1. `is_cache_stale(data/sackmann_cache)` kontrolü.
2. Stale ise: `refresh_if_stale` → CSV indir.
3. `build_tennis_ratings.main()` → ratings.json yeniden inşa.
4. Sonra `build_deps()` → agent başlar.

Stale değilse skip. Tennis whitelist'te değilse skip (config-driven). İlk başlatma ~1-2 dk sürebilir; sonraki başlatmalar 1sn'den az.

### 4.9. Gamma series_id desteği

`gamma_client._fetch_league_sources` artık hem `tag_id` hem `series_id` döner. Tennis ITF gibi tag-orphan event'ler series_id ile bulunur. Diğer sporlarda etki yok (sport entry'de series yoksa atlanır).

### 4.10. Dashboard topbar

Mode'a göre rozet:
- `dry_run` → kırmızı "DRY RUN" rozet
- `paper` → sarı "PAPER" rozet
- `live` → yeşil "LIVE" rozet

Operatörün hangi modda olduğunu hep göstersin (yanlış mod sürprizini engelle).

---

## 5. Sınır Durumları

| Durum | Davranış |
|---|---|
| `clob_book.fetch_book` HTTP timeout | Log WARNING, cycle'da skip; entry için REJECTED, exit için stuck (retry) |
| Orderbook boş (no bids, no asks) | BUY REJECTED, SELL REJECTED + stuck |
| `clob_book` rate limit (429) | Exponential backoff 1s/2s/4s, sonra cycle skip |
| Sackmann refresher network fail | Log WARNING, mevcut cache ile devam (tennis stale ratings kullanılır) |
| Sackmann CSV download fail | Log ERROR, refresh atla, mevcut ratings.json kullanılır |
| Tennis market_type bilinmiyor | enrichment skip, ARK trade alınmaz |
| `allowed_sport_tags`'de olmayan slug Polymarket'te görünür | scanner filter atar (zaten mevcut davranış) |
| Aynı maça basket + tennis çakışması (mümkün değil) | Yok (event_id farklı) |
| Tennis player matcher None döner (ambiguous surname) | enrichment skip, market trade alınmaz |
| Force-close timeout SELL stuck N cycle | Dashboard "stuck position" alarm; manuel müdahale opsiyonel |
| Mode config'de tanımsız (dry_run/paper/live dışı) | Startup ERROR + exit (program açılmaz) |
| `config_tennis.yaml` artık yok ama eski script onu arıyor | tennis_main.py silindi (Adım), reboot.py marker güncel; sorun yok |
| Reboot sonrası state restore (positions/audit) | Reboot=full-wipe kuralı (memory) korunur, paper mode da temizler |

---

## 6. Test Senaryoları

### 6.1. Domain unit testleri (`tests/unit/domain/execution/test_paper_fill.py`)

- `walk_buy_full_fill_at_target_price` — asks tek seviyede yeter, slippage 0
- `walk_buy_partial_through_levels` — birden fazla ask seviyesi yürünür, weighted avg doğru
- `walk_buy_rejected_when_below_min_fill_ratio` — sadece %50 dolar dolar → REJECTED
- `walk_buy_rejected_when_slippage_exceeded` — ilk ask target + %3, max %2 → 0 fill → REJECTED
- `walk_buy_partial_within_slippage_then_rejected` — kısmi %80 (min %95 altı) → REJECTED
- `walk_sell_full_fill` — bids yeter, hedef altında doluyor
- `walk_sell_partial_fill` — kısmi → PARTIAL_FILL, kalan shares
- `walk_sell_no_bids_rejected` — bids boş → REJECTED
- `walk_sell_slippage_exceeded_partial` — ilk bid hedef üstü, sonrakiler altı → kısmi
- `walk_buy_with_empty_asks_rejected`
- `walk_sell_with_zero_shares_returns_filled_zero` (degenerate)
- `walk_buy_weighted_avg_price_correct_multiple_levels`

### 6.2. Infrastructure testleri (`tests/unit/infrastructure/apis/test_clob_book.py`)

- `fetch_book_returns_parsed_bids_asks`
- `fetch_book_cache_hit_no_extra_http`
- `fetch_book_cache_expired_refetches`
- `fetch_book_http_error_returns_none`
- `fetch_book_timeout_returns_none`

### 6.3. Audit testleri (`tests/unit/infrastructure/audit/test_paper_executions.py`)

- `writes_execution_record_with_book_snapshot`
- `appends_not_overwrites_existing_jsonl`
- `handles_empty_book_snapshot`

### 6.4. Integration / smoke

- `tests/integration/test_paper_executor_buy_flow.py` — fake market + fake book → paper_executor.handle_buy → state güncel, paper_executions.jsonl satır
- `tests/integration/test_paper_executor_sell_partial_then_full.py` — kısmi fill state korunur, sonraki cycle tam fill
- `tests/integration/test_paper_executor_sell_stuck_retry.py` — no bids → stuck → retry cycle

### 6.5. Migration testleri

- Tennis-lab branch'tan alınmış mevcut testler (test_tennis_player_matcher, test_gamma_client) — yeşil kalmalı
- `test_sackmann_refresher.py` — startup hook çalıştığını doğrular

### 6.6. End-to-end smoke (manuel, 1 saat)

1. `python -m src.main --once --mode paper` çalıştır.
2. Polymarket'ten en az 1 gerçek book çekildi mi (log).
3. py-clob-client `place_order` çağrı sayısı = 0.
4. `paper_executions.jsonl`'da en az 1 kayıt + book snapshot.
5. Dashboard topbar "PAPER" rozet görünüyor.
6. Tennis maçı + basket maçı scanner'da görüldü mü.
7. NHL/UFL/MMA/golf/boxing maçları scanner'da skip oldu (whitelist).

---

## 7. Acceptance Kriteri (her madde Onay = ✅)

- [ ] `git tag pre-unified-2026-05-29` oluşturuldu, snapshot yedek mevcut
- [ ] `feature/tennis-lab` branch tag'lendi (`feature-tennis-lab-archived-2026-05-29`)
- [ ] `config.yaml` allowed_sport_tags: sadece basket + tennis (9 entry)
- [ ] `config.yaml` mode: paper (default)
- [ ] `config.yaml` paper bloğu eklendi (slippage, min_fill, cache_ttl)
- [ ] `config_tennis.yaml` silindi
- [ ] `scripts/tennis_main.py` silindi
- [ ] `scripts/reboot.py` `--live-lab` marker temizlendi
- [ ] `src/config/settings.py` Mode enum (dry_run/paper/live) + PaperConfig dataclass
- [ ] `src/infrastructure/apis/clob_book.py` yazıldı + testler yeşil
- [ ] `src/domain/execution/paper_fill.py` yazıldı + 12 unit test yeşil
- [ ] `src/infrastructure/audit/paper_executions.py` yazıldı + 3 unit test yeşil
- [ ] `src/orchestration/paper_executor.py` yazıldı + 3 integration test yeşil
- [ ] `src/orchestration/factory.py` mode dispatch ekledi, tennis aktif → Sackmann refresher hook
- [ ] `src/infrastructure/apis/gamma_client.py` series_id desteği eklendi (tennis lab patch)
- [ ] `src/domain/matching/tennis_player_matcher.py` surname-collision fix (tennis lab patch)
- [ ] `src/infrastructure/data/sackmann_refresher.py` migrasyon tamamlandı + test yeşil
- [ ] Tennis exclude_combos `config.yaml`'a eklendi
- [ ] Dashboard topbar mode rozet renkli (dry/paper/live)
- [ ] `pytest -q` tam yeşil (mevcut testler + yeni ~20 test)
- [ ] 1 saatlik smoke run: paper_executions.jsonl ≥ 1 kayıt, scanner basket+tennis maçı görüyor, NHL/golf/MMA atılıyor
- [ ] DECISIONS.md güncellendi (paper mode + spor portföy kararı)
- [ ] `_backup_tennis_lab/` arşivlendi (silinmedi, geri dönüş için)

---

## 8. Faz Sırası (writing-plans 3 ardışık plan dosyası üretecek)

Refactor büyük → tek plan dosyasına sığmaz, hata riski yükselir. Plan **3 ardışık parçaya** bölünür. Her parçanın kendi onay noktası ve testi var. Faz N tamamlanmadan Faz N+1 başlamaz.

### Faz 1 — **Yedek + Spor Whitelist Kısıtlama** (en güvenli, geri dönüşü kolay)

**Ne yapar:** Yedek + spor portföyünü daralt + tennis'i AÇMA (henüz). dry_run modu korunur.

**Adımlar:**
1. git tag `pre-unified-2026-05-29` oluştur (master HEAD).
2. `feature/tennis-lab` branch tag'le (`feature-tennis-lab-archived-2026-05-29`).
3. `data/`, `logs/audit/` snapshot → `_archive/2026-05-29/`.
4. `config.yaml` allowed_sport_tags: NHL, NCAAF, CFL, UFL, MMA, UFC, Boxing, LPGA, LIV, PGA → ÇIKAR. Tennis henüz EKLENMEZ.
5. `pytest -q` tam yeşil.
6. Smoke: `python -m src.main --once --mode dry_run` → scanner sadece basket maçları görüyor mu, NHL maçı atıldı mı.
7. Commit: `refactor(config): cut sport whitelist to basketball only (pre-tennis-merge)`.

**Onay noktası:** Smoke logunda "skipped: NHL", "skipped: golf", "skipped: MMA" görünmeli; sadece basket maçları akmalı. Açık NHL pozisyon yok (kontrol).

**Risk:** Düşük. Sadece config değişikliği. Geri dönüş: config'den çıkarılan slugları geri ekle.

---

### Faz 2 — **Paper Realism Executor** (en kritik, en uzun)

**Ne yapar:** Mode.PAPER enum, clob_book infra, paper_fill domain, paper_executor orchestration, dashboard mode rozet.

**Adımlar:**
1. `src/config/settings.py` → Mode enum (dry_run/paper/live) + PaperConfig dataclass (slippage, min_fill, cache_ttl).
2. `config.yaml` → paper bloğu (defaults: max_buy_slippage_pct=0.02, max_sell_slippage_pct=0.05, min_fill_ratio=0.95, book_cache_ttl_sec=5). Mode HALA dry_run (paper'a sonra çevireceğiz).
3. `src/infrastructure/apis/clob_book.py` yaz + 5 unit test (TDD).
4. `src/domain/execution/paper_fill.py` yaz + 12 unit test (TDD).
5. `src/infrastructure/audit/paper_executions.py` yaz + 3 unit test.
6. `src/orchestration/paper_executor.py` yaz + 3 integration test.
7. `src/orchestration/factory.py` → mode'a göre executor seçimi (dry_run mevcut kalır, paper yeni dispatch).
8. `src/presentation/dashboard/static/js/dashboard.js` → mode rozet (dry/paper/live renk).
9. `pytest -q` tam yeşil.
10. Smoke: `python -m src.main --once --mode paper` → 1 trade gerçek book çekti mi, paper_executions.jsonl satır var mı, py-clob-client place_order çağrı sayısı=0.
11. Commit: `feat(paper): realistic fill simulator + clob orderbook walker`.

**Onay noktası:** Smoke logunda paper_executions.jsonl ≥ 1 satır + book snapshot. Tennis hala kapalı; sadece WNBA/NBA paper modunda işliyor.

**Risk:** Orta-yüksek. Yeni 4 modül + executor değişimi. TDD ile risk azaltılır. Geri dönüş: paper modülünü import etmemek, mode=dry_run kalır.

---

### Faz 3 — **Tennis Migrasyonu + Bankroll Birleşme + Mode=Paper Default**

**Ne yapar:** Tennis aktive, Sackmann refresher entegre, gamma series_id, exclude_combos, tek bot ve tek config.

**Adımlar:**
1. tennis lab branch patch'ten cherry-pick et:
   - `src/infrastructure/apis/gamma_client.py` series_id desteği + test.
   - `src/domain/matching/tennis_player_matcher.py` surname-collision fix + 3 yeni test.
   - `src/infrastructure/data/sackmann_refresher.py` + test (yeni dosya).
   - `scripts/build_tennis_ratings.py` (tennis lab'da varsa kontrol).
2. `src/orchestration/factory.py` → tennis aktif iken Sackmann startup hook (`build_deps` öncesi `_maybe_refresh_sackmann_on_startup`).
3. `config.yaml`:
   - `allowed_sport_tags` → `atp`, `wta` EKLE.
   - `edge.exclude_combos` → tennis_set_totals (4) + tennis_first_set_winner (4) EKLE.
   - `mode: paper` (default).
4. `scripts/tennis_main.py` SİL.
5. `config_tennis.yaml` SİL.
6. `scripts/reboot.py` → `--live-lab` marker temizle (artık tek bot).
7. `_backup_tennis_lab/` → `_archive/tennis-lab-backup-2026-05-29/` taşı.
8. `pytest -q` tam yeşil (tennis testleri dahil).
9. Smoke: `python -m src.main --once --mode paper`:
   - Sackmann startup hook çalıştı mı (log).
   - Tennis ATP/WTA maçı scanner'da görüldü mü.
   - Gamma series_id query atıldı mı (log).
   - Paper executor tennis maçı için book çekti mi.
   - paper_executions.jsonl satırlarında basket + tennis var mı.
10. DECISIONS.md güncelle (paper mode + spor portföy + tennis merge).
11. Commit: `feat(unified-lab): merge tennis into main bot, paper mode default`.

**Onay noktası:** Smoke logu: basket + tennis maçı görüldü, gamma series_id query atıldı, Sackmann refresher çalıştı, paper_executions.jsonl basket + tennis satırları, py-clob-client place_order=0.

**Risk:** Yüksek (en geniş scope, en çok dosya). 3 faza bölündüğü için Faz 1-2 doğrulanmış olduğundan tennis-spesifik kısımlar izole. Geri dönüş: git tag pre-unified-2026-05-29 → 5 dk'da reset.

---

### Faz 4 — **Gözlem (paper run 3-7 gün)** (kod yok, monitor)

3-7 gün paper modunda çalıştır. Metrikler:
- Fill success ratio (kaç entry FILLED / REJECTED / PARTIAL_FILL).
- Tennis vs basket trade dağılımı.
- Net PnL (paper).
- Stuck position süresi (force-close timeout SELL retry'leri).
- Skipped sport counter (NHL/golf/MMA scanner'da gerçekten skip ediliyor mu).

Sonuç tatmin edici → live faz (ayrı spec). Sonuç sorunlu → Adım 1 yedekten geri dön, kök sebep araştır.

---

## 9. Geri Dönüş Planı

Her fazda problem çıkarsa geri dönüş yolu net:

| Faz | Geri dönüş |
|---|---|
| 1 | `git revert HEAD` (config commit), açık pozisyon etkilenmez (config-only) |
| 2 | `git revert <range>` paper modülleri, mode dry_run kalır, paper modülleri import edilmez |
| 3 | `git reset --hard pre-unified-2026-05-29` + state snapshot restore (`_archive/2026-05-29/data` ve `logs/audit/`) |

Manuel müdahale gereken durum: paper run'da stuck position alarm + operatör dashboard'dan manual close. Bu mevcut force-close mantığını AŞAR (paper'da 0-realize yapmıyoruz).

---

## 10. Bağımlılık ve Dış Sistem Etkileri

| Sistem | Etki |
|---|---|
| Polymarket Gamma (markets) | Mevcut (değişiklik yok), sadece daha az slug sorgulanır (whitelist daraldı) |
| Polymarket CLOB (orderbook) | YENİ kullanım (paper book fetch). Read-only, free, no auth. Cycle başına ~5-10 fetch beklenir. |
| Odds API (bookmaker) | Mevcut (değişiklik yok). Tennis aktifleşmesi → odds_sport_keys.py'de tennis branch zaten dinamik (sport_key_resolver.py) |
| Sackmann GitHub repo | Tennis aktif → startup'ta CSV download (~25 dosya, ilk başlatmada ~30sn) |
| ESPN scoreboard | Mevcut (değişiklik yok), tennis için ESPN tennis endpoint kullanılır (mevcut) |
| Dashboard | Mevcut, mode rozet ekleme |
| File system | `paper_executions.jsonl` yeni, `data/sackmann_cache/` yeni (tennis), `_archive/2026-05-29/` yeni |

---

## 11. Açık Kalan Detay (writing-plans çözecek)

Writing-plans skill bunları kod seviyesinde detaylandıracak:

- `paper_fill.walk_buy` / `walk_sell` fonksiyon imzaları + dataclass tanımları (FillResult)
- `clob_book.fetch_book` HTTP retry stratejisi (urllib3 vs httpx — mevcut codebase ne kullanıyor)
- `paper_executor` mevcut `executor.py` ile composition mı, mode dispatch mi
- Dashboard mode rozet CSS class isimleri
- DECISIONS.md hangi bölümlere ne yazılacak (§A demir kural + §B SPEC log)

---

## 12. Self-Review (kullanıcı review öncesi)

- ✅ Placeholder yok (her bölüm somut)
- ✅ Çelişki yok (mode dispatch tek yerde tanımlı, exclude_combos tek listede)
- ✅ Kapsam tek implementation plan'a sığmıyor → 3 faza bölündü (faz sırası §8)
- ✅ Ambiguity: "stuck position alarm" — manuel müdahale faz 4 gözlem konusu, bu spec'te alarm dashboard'da görünür kuralı net
- ✅ ARCH_GUARD 8 anti-pattern kontrol: katman düzeni, domain I/O yok, magic number yok, <400 satır, P(YES) anchor, sessiz hata yok, utils yok, DRY (paper logic tek yerde)
- ✅ Geri dönüş planı her faz için var
- ✅ Acceptance kriteri ölçülebilir (sayısal/loglanan)
- ✅ Risk her faz için belirtilmiş
