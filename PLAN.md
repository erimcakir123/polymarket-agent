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

### PLAN-023: Exit Güvenlik Paketi (Phantom Exit + SL Elapsed Gate) (DONE)
- **Durum**: DONE
- **Tarih**: 2026-04-21
- **Öncelik**: P0
- **Önceki planlar**: Bu plan eski PLAN-020 (Phantom Exit Bug / bid_price) ve PLAN-022 (SL Elapsed-Gated) maddelerini birleştirir. Her ikisi de henüz uygulanmadı — SADECE `near_resolve.py` 2026-04-21 oturumunda minimum fix olarak `bid_price`'a çevrildi (acil önlem). Bu plan kalan tüm işi kapsar.
- **Etki**:
  - **Part A (phantom exit)**: `src/strategy/exit/scale_out.py`, `src/strategy/exit/price_cap.py`, `src/strategy/exit/a_conf_hold.py` (market_flip), `src/strategy/exit/baseball_score_exit.py`, `src/strategy/exit/hockey_score_exit.py`, `src/strategy/exit/tennis_score_exit.py`, `src/strategy/exit/cricket_score_exit.py`, `src/strategy/exit/soccer_score_exit.py`, `src/strategy/exit/nba_score_exit.py`, `src/strategy/exit/nfl_score_exit.py`, `src/strategy/exit/monitor.py` (çağrı yerleri), tüm `tests/unit/strategy/exit/*.py` (fixture'lara `bid_price` ekle)
  - **Part B (SL elapsed gate)**: `config.yaml`, `src/config/settings.py`, `src/strategy/exit/price_cap.py`, `src/strategy/exit/monitor.py`, `tests/unit/strategy/exit/test_price_cap.py`
- **Açıklama**:
  - **Part A — Kök neden**: `pos.current_price` = yes_price = **best-ASK** ([price_feed.py:44](src/infrastructure/websocket/price_feed.py#L44)). Exit kararları bunu kullanıyor → ASK spike'ında phantom exit fire ediyor, gerçekte satış BID'den gerçekleşir. 2026-04-21 oturumunda 3 phantom exit ($31.98, Zvezda + Rotherham ×2) bu nedenle oluştu. near_resolve için acil fix edildi ama diğer exit'ler (scale_out, market_flip, sport-specific score exits) hâlâ ASK üzerinden karar veriyor.
  - **Part B — Kullanıcı şikayeti (Girona/Real Betis örneği)**: Entry 0.33 → 0.17 (−$19.18), SL fire, elapsed ~%10. 1 gol → fiyat "lak diye düşer", $12 kaybı aşar, SL erken tetikler, maç geri dönemez kapanır. Kullanıcı: "75'i geçmeden uyanmasın SL". PLAN-014'ün "elapsed bağımsız" tasarımı bu senaryoda kullanıcı felsefesine uymuyor.

#### Adımlar

**Part A — bid_price Migration (Phantom Exit fix)**
1. `src/strategy/exit/scale_out.py` → `check_scale_out(...)` imzasında `current_price` parametresini caller taraftan `pos.bid_price` ile çağır (monitor.py:194). İç mantık değişmez, sadece giriş.
2. `src/strategy/exit/a_conf_hold.py` → `market_flip_exit(pos, elapsed_pct)` → içeride `pos.current_price` < 0.50 yerine `pos.bid_price` < 0.50.
3. `src/strategy/exit/baseball_score_exit.py` → `check(..., current_price, ...)` çağrı noktasında `pos.bid_price` geçir (monitor.py:259). İç eşik karşılaştırması bid üzerinden.
4. `src/strategy/exit/hockey_score_exit.py` → aynı (monitor.py:234: `current_price=pos.current_price` → `pos.bid_price`).
5. `src/strategy/exit/tennis_score_exit.py` → aynı (monitor.py:246).
6. `src/strategy/exit/cricket_score_exit.py` → aynı (monitor.py:272).
7. `src/strategy/exit/nba_score_exit.py` → aynı (monitor.py'de current_price geçiyor mu kontrol et, geçiyorsa bid).
8. `src/strategy/exit/nfl_score_exit.py` → aynı.
9. `src/strategy/exit/monitor.py` içindeki `_never_in_profit_exit`, `_ultra_low_guard_exit`, `_hold_revocation_should_revoke` fonksiyonları `pos.current_price`'ı `eff_current` olarak kullanıyor — **bunları `pos.bid_price`** yap (çünkü bunlar da exit kararına girdi).
10. `_fav_transition`/`favored.should_promote/demote` — observation amaçlı, **ASK'ta kalabilir** (not exit). Dokunma.
11. Tüm `tests/unit/strategy/exit/*.py` fixture'larında Position oluştururken `bid_price=<current_price>` default ayarla (en basiti: Position dataclass `__post_init__` veya factory'de eğer `bid_price==0.0 ve current_price>0` ise `bid_price=current_price` fallback — mevcut testleri kırmaz). Eğer Position modelinde böyle fallback yoksa, fixture'ları manuel `bid_price=...` ile güncelle.
12. Yeni test: `test_near_resolve.py::test_ask_spike_does_not_fire` — `current_price=0.97`, `bid_price=0.82` → near_resolve **False**.
13. Yeni test: `test_scale_out.py::test_ask_spike_does_not_trigger` — benzer.
14. `pytest -q tests/` → hepsi geçmeli.

**Part B — SL Gate'leri (2-way ve 3-way AYRI kurallar + elapsed ≥ 0.75)**
Kullanıcı kuralı özet:
- **2-way (home/away)**: mevcut PLAN-014 kuralı `bid < 0.50` **doğru** — karşı taraf 0.50 üstü demek → biz kaybediyoruz. Değiştirme.
- **3-way (home/draw/away)**: `bid < 0.50` YANLIŞ çalışıyor — entry 0.45 + draw 0.30 + karşı 0.25'te biz **öndeyiz** ama eski kural SL fire ediyordu. 3-way'e özel: `bid ≤ max(sibling_bids)` iken (biz lider değilsek) SL fire.

15. `config.yaml::sl` bölümüne `min_elapsed_pct: 0.75` ekle.
16. `src/config/settings.py::SLParams` → `min_elapsed_pct: float = 0.75` field ekle.
17. **Event sibling bids erişimi (3-way için gerekli)**:
    - `src/models/position.py`'ye `event_sibling_bids: list[float] = field(default_factory=list)` ekle. 2-way pozisyonda bu liste kullanılmaz (veya 1 elemanlı karşı bid). 3-way pozisyonda 2 elemanlı (draw + karşı).
    - Orchestration her cycle güncellesin (event_id üzerinden kardeş market'ların bid'ini çek). Dosya önerisi: `src/orchestration/entry_processor.py` veya ayrı `sibling_bid_updater.py`.

    **17a. Plumbing kolay tarafı — veri hazır**:
    - Gamma scan zaten `event.markets[]` döndürüyor. Heavy cycle'da entry_processor tüm event markets'ı görür. Ekstra API çağrısı **gerekmez**.
    - Scanner'da `_passes_three_way_sum_filter` event_id ile markets group'luyor ([scanner.py:52](src/orchestration/scanner.py#L52)) — reuse için iyi referans.
    - Plumbing: sadece Position'a field plumb etmek + update adımı lazım.

    **17b. Plumbing riskli tarafı (implementer karar versin)**:
    - **WS light cycle sibling güncellemez**: Bot sadece sahip olduğu token'lara subscribe. Draw + karşı token'lar subscribed değil → real-time sibling bid akışı yok. Üç seçenek:
      - **(a) Sibling token'lara subscribe**: WS kotası + callback koordinasyonu artar. En gerçek-zamanlı.
      - **(b) 30 dk heavy cycle'da tazele**: Gecikme kabul. SL için yeterli (dramatik skor değişimlerinde gate zaten elapsed≥0.75 sağlanınca açılıyor). **En ucuz, önerilen başlangıç**.
      - **(c) Her cycle mini Gamma fetch (event_id filtresi)**: API yükü artar, rate-limit riski.
    - **Edge: 3-way soccer market'ta draw eksik (gelmez)**: `len(siblings) == 1` olursa gerçekten 2-way mi yoksa draw market listelenmemiş mi? `sport_tag=soccer` + `siblings=1` → **fail-closed** (ayırt edilemez, SL blokla + WARNING).
    - **Race condition (entry anı)**: ilk cycle'da sibling_bids henüz populate olmamış olabilir. Bu dönemde elapsed <0.75 olduğu için SL zaten fire edemez → sorun yok, doğal akış.
    - **Network/Gamma fail**: sibling_bids stale kalır. 3-way pozisyon fail-closed → SL blokla. Sağlık metriği dashboard'a eklenmeli (PLAN-025 candidate: "sibling staleness").
18. `src/strategy/exit/price_cap.py::check` → imzayı `check(pos, params, elapsed_pct: float)` yap. **Way tespiti sport_tag'den (sibling_bids len'den DEĞİL)**:

    ```
    # 1. Elapsed gate (tüm durumlar)
    if elapsed_pct < params.min_elapsed_pct: return False
    if elapsed_pct == -1.0: return False   # fail-closed

    # 2. Loss hesabı
    loss_usd = pos.shares * (pos.entry_price - pos.bid_price)
    if loss_usd <= params.max_loss_usd: return False

    # 3. Way tespiti (SPORT'TAN, sibling count'tan DEĞİL)
    is_three_way = _is_soccer_sport(pos.sport_tag)  # monitor.py:31 helper'ı reuse

    # 4. Way'e göre "kaybediyor muyuz?"
    if is_three_way:
        # 3-way: sibling_bids mutlaka dolmuş olmalı
        if not pos.event_sibling_bids:
            # Sibling yok ama sport 3-way → fail-closed (SL blokla + warning)
            logger.warning("price_cap: 3-way pos %s has empty sibling_bids, blocking SL", pos.slug)
            return False
        if pos.bid_price > max(pos.event_sibling_bids):
            return False   # piyasa lideri biz, SL yok
        return True   # lider değiliz + loss tuttu → SL

    # 2-way: klasik 0.50 eşiği (sibling_bids opsiyonel, kullanılmıyor)
    if pos.bid_price >= params.price_below:
        return False   # bid >= 0.50, karşı <= 0.50, öndeyiz
    return True   # bid < 0.50 + loss tuttu → SL
    ```

    **Edge case'ler**:
    - **3-way + sibling boş**: fail-closed (SL blokla + WARNING log). User kuralı: yanlış SL'den kaçın.
    - **3-way + eşit bid (bid == max(sibling))**: lider değiliz → SL fire (strict `>`).
    - **2-way**: sibling_bids kullanılmıyor, `bid<0.50` yeterli.
    - **MMA/combat** `elapsed_exit_disabled` → elapsed=-1 → SL hiç çalışmaz (kabul edilen tradeoff, PLAN-024 candidate).
    - **Orchestration güncelleme başarısız** (network, event_id mismatch, race): 3-way pozisyon korumada kalır (fail-closed); monitoring için WARNING log üretir. Sibling populate sağlığı dashboard'a metrik olarak eklenebilir (PLAN-025 candidate).

19. `src/strategy/exit/monitor.py:215` → `price_cap.check(pos, sl_params, elapsed_pct)` çağrısına elapsed geçir.
20. `src/strategy/exit/price_cap.py` docstring güncelle: "4-katmanlı gate: (1) elapsed ≥ 0.75, (2) loss > max_loss_usd, (3a) 2-way → bid < price_below, (3b) 3-way → bid ≤ max(sibling_bids)".
21. `tests/unit/strategy/exit/test_price_cap.py` yeni test setleri (11 test):

    **2-way senaryolar (sibling_bids=[karşı])**
    - 2w-leader: bid=0.60 + sibling=[0.40] + elapsed=0.90 + loss>12 → SL **False** (bid>=0.50)
    - 2w-loser: bid=0.30 + sibling=[0.70] + elapsed=0.90 + loss>12 → SL **True**
    - 2w-border: bid=0.50 + sibling=[0.50] + elapsed=0.90 + loss>12 → SL **False** (bid>=0.50 strict)

    **3-way senaryolar (sibling_bids=[draw, karşı])**
    - 3w-leader: bid=0.45 + sibling=[0.30,0.25] + elapsed=0.90 + loss>12 → SL **False**
    - 3w-not-leader: bid=0.30 + sibling=[0.45,0.25] + elapsed=0.90 + loss>12 → SL **True**
    - 3w-tied: bid=0.40 + sibling=[0.40,0.20] + elapsed=0.90 + loss>12 → SL **True** (strict `>`)

    **Elapsed gate**
    - elapsed=0.10 + diğerleri tuttu → SL **False**
    - elapsed=0.80 + 2w-loser → SL **True**
    - elapsed=-1 + diğerleri tuttu → SL **False**
    - elapsed=0.75 sınır + 2w-loser → SL **True**

    **Way tespiti / Fail-closed**
    - 3-way (soccer) + sibling=[] + bid=0.30 + elapsed=0.90 + loss>12 → SL **False** (fail-closed, WARNING log)
    - 2-way (non-soccer) + sibling=[] + bid=0.30 + elapsed=0.90 + loss>12 → SL **True** (sibling gerekmez, bid<0.50)

22. Existing `test_price_cap.py` test'lerine fixture olarak `elapsed_pct=0.80` + `event_sibling_bids=[]` ekle ki eski davranış bozulmasın.
23. `pytest -q tests/unit/strategy/exit/` → yeşil.
24. TDD.md §6.12 SL bölümünü güncelle: "2-way/3-way ayrımı ile 4-katmanlı gate. 2-way: bid<0.50 (karşı>0.50 = kaybediyor). 3-way: bid>max(sibling_bids) = piyasa lideri, değilse SL. Elapsed ≥0.75 ortak."

**Bot restart sonrası doğrulama**
24. Bot'u durdur (taskkill), değişiklikler commit et, bot'u yeniden başlat (`PYTHONIOENCODING=utf-8 nohup python -m src.main > logs/bot_stdout.log 2>&1 &`).
25. 24 saat gözle: dashboard'da phantom exit (ASK spike exit) **sıfır**, ve erken SL exit (elapsed<0.75) **sıfır**.

#### Kabul Kriterleri (tümü yeşil olmalı)
- [ ] **Part A**: `test_near_resolve.py::test_ask_spike_does_not_fire` geçer (ASK=0.97, BID=0.82 → no exit)
- [ ] **Part A**: Tüm mevcut exit testleri yeşil kalır (bid_price fixture default veya manuel set)
- [ ] **Part A**: monitor.py'deki sport-specific score exits + never_in_profit + ultra_low + hold_revoke kontrollerinin hepsi `pos.bid_price` kullanıyor (grep: `pos\.current_price` exit decision satırlarında kalmamalı)
- [ ] **Part B**: `test_price_cap.py` — 11 yeni test (2-way 3, 3-way 3, elapsed 4, fallback 1) yeşil
- [ ] **Part B**: `test_price_cap.py` mevcut testleri `elapsed=0.80` + `event_sibling_bids=[]` fixture ile geçer
- [ ] **Part B**: `price_cap.py` docstring 2-way/3-way ayrımını net açıklar, örneklerle
- [ ] **Part B**: `Position.event_sibling_bids` field eklendi, orchestration her cycle günceller (2-way→1 eleman, 3-way→2 eleman)
- [ ] **Part B**: 2-way doğru — PLAN-014 `bid<0.50` mantığı korundu
- [ ] **Part B**: 3-way doğru — entry 0.45 / sibling [0.30, 0.25] → SL fire etmez; entry 0.30 / sibling [0.45, 0.25] → SL fire
- [ ] **Integration**: 24h gözlem — phantom exit 0, erken-SL exit 0, 3-way false-positive SL exit 0

#### Mimari Uyumluluk
- Tüm değişiklikler **strategy/** katmanında (pure fn, I/O yok). ARCH_GUARD ihlali yok.
- Dosya başı satır limiti (400) korunur (scale_out, price_cap vb. küçük dosyalar).

#### TDD Referansı
- §6.11 (near_resolve) — input best-BID'e döndü (zaten uygulandı)
- §6.12 (SL / price_cap) — "elapsed bağımsız" → "elapsed ≥ 0.75"
- §6.12b (scale_out) — tier threshold best-BID üzerinde
- §6.14 (hold_revocation + market_flip) — best-BID
- §6.15 (sport-specific score exits) — best-BID

#### Follow-up (PLAN-024 candidate, bu planın dışında)
- MMA/combat (`elapsed_exit_disabled`) sporlarda SL tamamen devre dışı kalıyor (min_elapsed_pct gate + elapsed=-1 kombinasyonu). Bu sporlar için alternatif koruma: sabit loss cap (örn. $15) elapsed'dan bağımsız, veya round-based gate.
- Sustained-threshold guard: tek tick yerine N ardışık tick'te threshold aşılsın (ekstra phantom koruması) — P2, PLAN-025 candidate.

---

### PLAN-021: 2026-04-21 Phantom Exit Reversion (DONE)
- **Durum**: DONE
- **Tarih**: 2026-04-21
- **Etki**: logs/ (positions.json, trade_history.jsonl, equity_history.jsonl, circuit_breaker_state.json)
- **Açıklama**: PLAN-020 bug'ının ürettiği fantom exit'leri geri aldım.
  - Zvezda trade (exit $16.67): tam silindi, pozisyon restore edildi
  - Rotherham trade (partial $6.01 + full $9.30 = $15.31): tam silindi, pozisyon 48.46 share / $31.50 orijinal boyuta restore edildi
  - Her iki pozisyonun `match_start_iso` geçici olarak `2026-04-23T00:00:00Z` → near_resolve pre-match guard aktif kalır → PLAN-020 fix edilene kadar tekrar fantom exit fire etmez
  - realized_pnl: $31.98 → **$0.00**, CB zeroed, equity_history snapshots 3-5 retrospektif düzeltildi
- **Doğrulama**: ✓ 11 positions, realized=0, CB=0, trade_history 9 satır kaldı

---

### PLAN-015 Sonuç (tespit tamam): Dashboard $ etiketi partial notional, bug değil.
### Opsiyonel takip: (A) gate clipping'e min_size kontrolü (1 satır), (B) dashboard etiket "(partial)" suffix.

---

### PLAN-019 Sonuç (DONE — 2026-04-21):
- monitor.py: `_hold_revocation_exit` → `_hold_revocation_should_revoke` (state-only, exit yapmaz)
- HOLD_REVOKED dispatch silindi; revoke = `pos.favored=False`, SL (price_cap) karar verir
- 3 yeni test (revoke+SL kombo); PRD §F7 + TDD §6.14 güncel; HOLD_REVOKED enum geriye dönük uyum için kalır

---

### PLAN-010: NHL Score-Based Exit System
- **Durum**: DONE
- **Tarih**: 2026-04-17
- **Öncelik**: P1
- **SPEC**: SPEC-004
- **Etki**: infrastructure (1 yeni) → orchestration (1 yeni, 1 güncelleme) → strategy/exit (1 yeni, 1 güncelleme) → models (2 güncelleme) → config (2 güncelleme)
- **Açıklama**: Hockey maçlarında canlı skor ile A-conf hold kayıplarını azaltmak. 9 trade backtest: -$23 → +$4 (kazançlara sıfır dokunma).

#### Adımlar

**Adım 1 — Config & Model Temeli** (bağımlılık yok)
- [ ] 1a. `config.yaml`'a `score:` ve `exit:` bölümleri ekle
- [ ] 1b. `src/config/settings.py`'ye `ScoreConfig` ve `ExitConfig` Pydantic modelleri ekle
- [ ] 1c. `src/config/sport_rules.py`'ye NHL score exit config key'leri ekle (`late_deficit`, `late_elapsed_gate`, `score_price_confirm`, `final_elapsed_gate`)
- [ ] 1d. `src/models/enums.py`'ye `SCORE_EXIT` ve `CATASTROPHIC_BOUNCE` ExitReason ekle
- [ ] 1e. `src/models/position.py`'ye `catastrophic_watch: bool = False` ve `catastrophic_recovery_peak: float = 0.0` ekle
- [ ] 1f. Mevcut testlerin geçtiğini doğrula (`pytest -q`)

**Adım 2 — Score Client** (Adım 1'e bağlı)
- [ ] 2a. `src/infrastructure/apis/score_client.py` yaz — `MatchScore` dataclass + `fetch_scores(sport_key)` fonksiyonu
- [ ] 2b. Eski projeyi referans oku (Odds API scores endpoint formatı)
- [ ] 2c. Unit testler yaz: parse, API error, boş response
- [ ] 2d. `pytest -q` geçtiğini doğrula

**Adım 3 — Score Exit Kuralları** (Adım 1'e bağlı, Adım 2'den bağımsız)
- [ ] 3a. `src/strategy/exit/score_exit.py` yaz — `check(pos, score_info, elapsed_pct) → ExitSignal | None` (K1-K4, pure fonksiyon)
- [ ] 3b. `src/strategy/exit/catastrophic_watch.py` yaz — `check(pos) → ExitSignal | None` + `tick(pos)` (K5, pure fonksiyon)
- [ ] 3c. Unit testler yaz: 10 score_exit test + 4 catastrophic_watch test
- [ ] 3d. `pytest -q` geçtiğini doğrula

**Adım 4 — Score Enricher** (Adım 1 + 2'ye bağlı)
- [ ] 4a. `src/orchestration/score_enricher.py` yaz — `get_scores_if_due(positions) → dict[cid, score_info]`
- [ ] 4b. Team matching: mevcut `question_parser.py` kullanarak Polymarket question → Odds API team eşleştirme
- [ ] 4c. Rate limit: `match_window_hours` kontrolü, sport_key gruplama
- [ ] 4d. Unit testler yaz: polling zamanlama, gruplama, team matching, unavailable fallback
- [ ] 4e. `pytest -q` geçtiğini doğrula

**Adım 5 — Monitor + Exit Processor Entegrasyonu** (Adım 3 + 4'e bağlı)
- [ ] 5a. `src/strategy/exit/monitor.py` güncelle:
  - A-conf hold dalında market_flip'ten ÖNCE score_exit çağrısı ekle (sadece hockey)
  - Near-resolve + scale-out'tan SONRA, a_hold dalından ÖNCE catastrophic_watch çağrısı ekle (tüm sporlar)
- [ ] 5b. `src/orchestration/exit_processor.py` güncelle:
  - `run_light()` içinde score_enricher periyodik çağrı
  - `score_info` dict'ini `evaluate(pos, score_info=...)` olarak geçir
- [ ] 5c. Entegrasyon testleri yaz: score_exit override market_flip, fallback to market_flip
- [ ] 5d. `pytest -q` geçtiğini doğrula

**Adım 6 — TDD/Doc Güncelleme + Final Doğrulama**
- [ ] 6a. TDD §6.9 tablosunu güncelle (hockey score_exit eklendi)
- [ ] 6b. TDD §7.2 NHL satırını güncelle
- [ ] 6c. `positions.json` backward compat doğrula (bot'u başlat, mevcut pozisyonlar yüklensin)
- [ ] 6d. Tüm testler geçiyor: `pytest -q`
- [ ] 6e. SPEC-004 durumunu IMPLEMENTED yap ve sil

#### Adım Bağımlılık Grafiği
```
Adım 1 (config/model temeli)
  ├── Adım 2 (score client)
  │     └── Adım 4 (enricher) ──┐
  └── Adım 3 (score exit rules) ──┤
                                   └── Adım 5 (entegrasyon)
                                         └── Adım 6 (doc + final)
```
Adım 2 ve 3 paralel çalışabilir.

#### Kabul Kriterleri
- [ ] 15 yeni test geçiyor
- [ ] Mevcut testler kırılmadı
- [ ] Tüm eşikler config'den okunuyor (magic number yok)
- [ ] Yeni dosyalar <400 satır
- [ ] Katman kuralları korunuyor (infra → orch → strategy)
- [ ] `positions.json` eski formatta yükleniyor (backward compat)
- [ ] TDD §6.9 ve §7.2 güncellendi
- [ ] SPEC-004 silindi

#### Mimari Uyumluluk
- ARCH K1 (katman): ✓ infra → orch → strategy
- ARCH K2 (domain I/O): ✓ score_exit.py pure, I/O yok
- ARCH K3 (dosya boyutu): ✓ tümü <100 satır tahmini
- ARCH K6 (magic number): ✓ tüm eşikler config'den
- ARCH K7 (P_YES): ✓ dokunulmuyor
- ARCH K11 (test): ✓ 15+ test planlandı

#### TDD Referansı
- §6.9 (A-conf hold) — score_exit dalı ekleniyor
- §6.8 (graduated SL) — score_info otomatik aktif oluyor (yan etki)
- §7.2 (sport rules) — NHL satırı güncelleniyor

