# SPEC — Spesifikasyonlar

> Bu dosya aktif teknik spesifikasyonları içerir.
> Bir spec entegre edilip onaylandıktan sonra bu dosyadan **SİLİNİR**.
> Sadece aktif, henüz koda dönüşmemiş spec'ler burada durur.

---

## Nasıl Kullanılır

### Spec Ekleme
```
1. Bir özellik veya modül için detaylı spec yaz (aşağıdaki formata uy)
2. Durum: DRAFT
3. Review + onay → durum: APPROVED
4. Kod yazılıp test edildikten sonra → durum: IMPLEMENTED → sil
```

### Spec Formatı
```
### SPEC-XXX: [Modül/Özellik adı]
- **Durum**: DRAFT | APPROVED | IMPLEMENTED
- **Tarih**: YYYY-MM-DD
- **İlgili Plan**: PLAN-XXX
- **Katman**: domain | strategy | infrastructure | orchestration | presentation
- **Dosya**: src/katman/modul.py

#### Amaç
Modülün ne yaptığı, tek cümle.

#### Girdi/Çıktı
- Girdi: ...
- Çıktı: ...

#### Davranış Kuralları
1. ...
2. ...

#### Sınır Durumları (Edge Cases)
- ...

#### Test Senaryoları
- ...
```

---

## Aktif Spesifikasyonlar

---

## SPEC-C: 3-Way Bookmaker Sanity (LOW PRIORITY — Bekliyor)

> **Tarih:** 2026-05-08
> **Durum:** PARKLA — futbol kapatılana kadar etkisiz

Soccer için draw outcome eksik bookmaker silent skip + 3-way prob sum sanity (0.95-1.05) yok. Futbol açılmadan etkisiz, **futbol açılmadan ÖNCE** bu spec yazılır.

---

## SPEC-SIM: Geriye Dönük Gerçekçi Çıkış Simülasyonu (Faz 1 — salt-okunur döküm)

- **Durum**: DRAFT
- **Tarih**: 2026-06-08
- **Katman**: `scripts/` (üretim-dışı araç — `src/` HİÇ değiştirilmez)
- **Dosya**: `scripts/sim_realistic_replay.py` + `tests/unit/scripts/test_sim_realistic_replay.py`

### Amaç
Bugünün tüm pozisyonlarını (16 açık + bağlanınca tek seferde ~1.00'a satılan 3 kazanan = 19) gerçek dakika-dakika fiyat geçmişine karşı yeniden oynatıp, bağlı olunsaydı tetiklenecek **kademeli kâr-alma / stop / final** olaylarını ortaya çıkarmak; "gerçekte olan" ile "gerçekçi olan"ı yan yana göstermek. Salt-okunur.

### Girdi/Çıktı
- **Girdi**:
  - Açık 16 pozisyon: `data/positions.json`.
  - Kapanan 3 pozisyon: giriş durumu en güncel positions yedeğinden (`data/positions.json.bak.realistic_close_20260608_025345` — 3'ünü de içerir) okunur.
  - Eşik/config: gerçek bot config'i (`config.yaml`) → scale_out tier'ları, partial_sl tier+enabled, graduated_sl enabled, near_resolve eşikleri, high_entry sınırları.
  - Fiyat geçmişi: Polymarket `prices-history` (her `token_id` için, fidelity=60s).
- **Çıktı**: pozisyon başı olay zaman çizelgesi (gerçekte-olan vs gerçekçi-olan) + toplam: gerçek realized $327.89 vs gerçekçi realized $X + fark. Konsola yazılır (bot state dosyalarına YAZILMAZ).

### Davranış Kuralları
1. **Botun kendi beyni çağrılır (DRY)**: her tick'te `lifecycle.tick_position_state(pos)` + `strategy.exit.monitor.evaluate(pos, <config eşikleri>)`. Çıkış mantığı kopyalanmaz.
2. **Pozisyon giriş anına sıfırlanır**: `current_price=entry_price`, peak/ever_in_profit/momentum sayaçları=0, tier'lar=0, shares/size_usdc=orijinal.
3. **Fiyat tabanı**: `prices-history` `market=token_id` ile çekilir → sahip olunan jetonun (BUY_NO ise NO) fiyat serisi. `entry_price`/`current_price` ile aynı taban; realized her iki yön için tek formülle çalışır.
4. **Realized formülü** (`exit_processor._book_sale` ile birebir): `realized = satılan_hisse × (fiyat − entry_price)`. Tek satırlık formül; metodun kendisi `ExitProcessor`/deps'e bağlı olduğu için sim içinde inline kopyalanır, kaynak yorumda belirtilir.
5. **Tetiklenen her çıkış bir olaydır**: partial → hisse küçült + tier artır + olay kaydet; full → kalanı sat + final olay + dur.
6. **Saat enjeksiyonu**: `monitor.evaluate` içindeki `compute_elapsed_pct` gerçek saate bakar. Sim sürecinde monitor modülünün saat kaynağı geçici olarak o tick'in zamanına sabitlenir (yalnızca sim sürecinin belleğinde). Çalışan bot ayrı süreç → etkilenmez, üretim dosyası değişmez.
7. **Çözülme**: seri ~0/~1'e ulaşıp pozisyon hâlâ açıksa, son fiyattan final çıkış (payout) işlenir.

### Sınır Durumları
- Fiyat geçmişi boş/çekilemezse: o pozisyon "veri yok — atlandı" olarak loglanır (sessiz yutma yok), diğerleri devam eder.
- Maçı henüz başlamamış açık pozisyon: seri kısa → muhtemelen hiç tetik yok → "olay yok, hâlâ açık" gösterilir.
- Fill yaklaşıklığı: satış o dakikanın fiyatından modellenir (gerçek emir defteri yok); kayıp-kesme satışları gerçek botta bid/market'ten ~1 tık daha kötü olabilir. Rapor bunu "±~1 tık iyimser" notuyla belirtir.

### Test Senaryoları (pure `replay_position` fonksiyonu, ağ yok)
- `test_replay_rising_curve_triggers_scaleout_tiers_in_order`
- `test_replay_realized_matches_book_sale_formula`
- `test_replay_winner_staged_sum_not_greater_than_single_dump`
- `test_replay_falling_curve_triggers_partial_sl`
- `test_replay_flat_curve_near_entry_no_exit`

### Güvenlik Sınırı (DEMİR)
`positions.json`, `trade_events.jsonl`, `equity_history.jsonl`, `paper_executions.jsonl` ve diğer bot-state dosyalarına **YAZMAZ**. Ağ erişimi yalnızca `prices-history` GET. Çalışan bota dokunmaz. (Faz 2 = uygula; ayrı spec + yedek + onay.)

---

## SPEC-SIM2: Önceki Session'ı Bugünkü Kurallarla Yeniden Oynatma (zemin counterfactual)

- **Durum**: DRAFT
- **Tarih**: 2026-06-10
- **Katman**: `scripts/` (üretim-dışı araç — `src/` HİÇ değiştirilmez; tek istisna aşağıda*)
- **Dosya**: `scripts/sim_surface_counterfactual.py` + `tests/unit/scripts/test_sim_surface_counterfactual.py`

### Amaç
Reboot ile arşivlenen önceki session'ın (2026-06-06 → 06-09, 79 tenis trade) her trade'ini
**bugünkü tüm kurallardan** geçirip "o gün bu kurallar olsaydı: girer miydi / hangi yönde /
hangi tahminle / kâr-zarar ne olurdu" sorusuna trade-trade + toplam cevap vermek. Salt-okunur.

### Bugünkü kurallar = neler değişti (sim bunları uygular)
1. **Zemin tespiti**: SurfaceResolver (Sackmann harita + override dosyası + Wikipedia +
   event-linking). Zemin bulunamazsa trade **GİRİLMEZ** (eski kod sessizce "Hard" varsayardı).
2. **Match O/U kaldırıldı** (SPEC-Z28): arşivdeki 1 totals trade'i → GİRİLMEZ.
3. **Force-close kapalı**: stop/kâr kademesi tetiklenmezse pozisyon çözüme kadar tutulur,
   ödeme Polymarket çözümünden gelir.
4. **Çıkış beyni**: scale_out (0.40/0.70) + partial_sl (3 kademe, AÇIK) + near_resolve —
   mevcut config değerleriyle, SPEC-SIM altyapısı (`replay_position`) yeniden kullanılır.
5. **Boyutlandırma**: bugünkü config (moneyline A=$50/B=$30; set handikap bimodal A=$15/B=$10;
   bimodal taban fiyat 0.20).

### Girdi
- `logs/audit/trade_events.archive.20260609_203215.jsonl` → 85 entry (79 tenis): slug,
  question, entry_price, direction, size, confidence, has_sharp, bookmaker_prob,
  anchor_probability (eski tahmin), entry_timestamp, condition_id.
- `logs/audit/paper_executions.archive.20260609_203215.jsonl` → token_id eşleme
  (zaman+boyut yakınlığıyla BUY kayıtlarından; positions yedekleri ek kaynak).
- `data/sackmann_cache/` → **reytingler 2026-06-06 öncesi maçlarla yeniden kurulur**
  (cutoff: tourney_date < 20260606). Lookahead yasak: bugünkü reyting dosyası o maçların
  sonuçlarını içerir, kullanılamaz. Mevcut loader + glicko fonksiyonları yeniden kullanılır.
- `data/tennis_calibration.json` (mevcut), `data/tennis_surface_map.json` +
  `data/tennis_surface_overrides.json` (mevcut), `config.yaml` (mevcut).
- Fiyat geçmişi: Polymarket `prices-history` (token_id, fidelity=60).

*Tek istisna notu: reyting kurucusunun (`scripts/build_tennis_ratings.py`) cutoff parametresi
yoksa SADECE bu script'e opsiyonel `cutoff_date` parametresi eklenir (varsayılan davranış
değişmez) — `src/` yine dokunulmaz.

### Davranış Kuralları (karar zinciri, her tenis entry için, kronolojik sıra)
1. **Market tipi**: gerçek koddan `_infer_market_type`. totals → KARAR=GİRMEZ (O/U kaldırıldı).
2. **Low-tier filtresi**: gerçek koddan `_is_low_tier_tennis` → elenirse GİRMEZ.
3. **Moneyline BM-first**: kayıtlı `source=bookmaker` olan trade'ler (8 adet) → tahmin
   DEĞİŞMEZ (P(YES)=kayıtlı bookmaker_prob; bahisçi tahtası geri getirilemez, o gün BM verisi
   vardı demektir). `source=model` olanlar (71) → model yolu yeniden çalıştırılır (zemin etkisi
   burada). Not: arşivde num_bookmakers/bookmaker_prob alanlarında bilinen sahte-etiket sorunu
   var; yol seçimi yalnızca `source` alanına dayanır.
4. **Model yolu**: SurfaceResolver.resolve → zemin None ise GİRMEZ (SURFACE_UNKNOWN).
   Set-handikap/set-winner event-linking: aynı gün + aynı iki oyuncunun moneyline trade'inden
   turnuva alınır (player-name eşleme). **Ek (2026-06-10 koşu bulgusu):** arşivde yalnız
   girilen trade'ler var; canlı bot turnuvayı TARANAN (girilmemiş dahil) moneyline'dan alır.
   Sadakat için eşlenemeyen event'lerde Polymarket Gamma'dan (mevcut
   `GammaClient.fetch_closed_market_by_condition`, ücretsiz, Odds API DEĞİL) event başlığı
   çekilir → `_extract_location` → turnuva. Ağ beyaz listesine Gamma GET eklendi.
   Zemin bulunduysa cutoff-reytingler + kalibrasyonla model → yeni P(YES); **güven notu +
   sharp bilgisi de YENİ sonuçtan gelir** (bugünkü kural: model sonucu kendi confidence'ını
   üretir; kayıtlı değerler yalnız source=bookmaker yolunda kullanılır).
5. **Giriş kapısı (bugünkü)**: edge = P(YES) − entry_price (YES yönü) veya entry_price − P(YES)
   (NO yönü); edge ≥ min_edge (0.06) + confidence A + has_sharp şartı (kayıtlı değerler) +
   bimodal taban fiyat (0.20) + event-level guard (aynı event aynı tip max 1; sim portföyü
   kronolojik işlendiği için uygulanabilir). Sonuç: GİRMEZ / AYNI YÖN / TERS YÖN.
6. **Fiyat tabanı**: AYNI YÖN → gerçek dolum fiyatı (entry_price) + gerçek token fiyat serisi.
   TERS YÖN → karşı taraf: fiyat = 1 − p yaklaşımı (seri ve giriş fiyatı ters çevrilir; rapor
   bunu "yaklaşım" olarak işaretler).
7. **PnL oynatma**: SPEC-SIM `replay_position` (bot'un gerçek çıkış beyni; FrozenClock;
   liquidity_floor 0.05 "alıcı yok → satmaz"; çözüm yerleşimi resolved_hi/lo). Boyut bugünkü
   config'den; hisse = boyut / giriş fiyatı.
8. **Rapor** (konsol, bot dosyalarına yazılmaz):
   - Trade başına: soru, eski tahmin (kayıtlı anchor) vs yeni tahmin, yeni zemin, karar,
     gerçek PnL vs counterfactual PnL.
   - Toplam: gerçek toplam PnL vs counterfactual toplam + karar kırılımı
     (girmez/aynı/ters sayıları, zemin-bulunamadı listesi).
   - Tenis-dışı 6 trade kapsam dışı (zemin etkisi yok), raporda not düşülür.

### Sınır Durumları
- Fiyat geçmişi çekilemeyen trade → "veri yok, atlandı" listesi (sessiz yutma yok).
- Oyuncu cutoff-reytinglerde yok / phi ≥ eşik → model fiyatlayamaz → GİRMEZ (gerçek bot
  davranışıyla aynı; rapor sebep gösterir).
- TERS YÖN + 1−p yaklaşımı: spread kuruş farkı olabilir — rapor dipnotu.
- Wikipedia erişilemezse (ağ): yalnızca harita+override+event-linking ile devam, etkilenen
  trade'ler raporda işaretlenir.
- Aynı condition_id'ye birden çok entry (re-entry) → her biri ayrı satır, kronolojik.

### Test Senaryoları (saf fonksiyonlar, ağ yok)
- `test_decide_totals_market_always_skipped`
- `test_decide_surface_unknown_skipped`
- `test_decide_same_direction_when_edge_holds`
- `test_decide_flips_direction_when_model_favors_other_side`
- `test_decide_below_min_edge_skipped`
- `test_invert_series_no_side_prices_and_entry`
- `test_event_link_set_handicap_gets_tournament_from_moneyline_same_players`
- `test_ratings_cutoff_excludes_matches_on_or_after_date`
- `test_bimodal_floor_blocks_low_price_entry`

### Güvenlik Sınırı (DEMİR)
Bot-state dosyalarına YAZMAZ; ağ yalnızca `prices-history` + Wikipedia GET (ücretsiz, Odds
API kotası KULLANILMAZ). Çalışan bota dokunmaz. Arşiv dosyaları salt-okunur açılır.

---
