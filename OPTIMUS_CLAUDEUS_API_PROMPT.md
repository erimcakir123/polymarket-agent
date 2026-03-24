# OPTIMUS CLAUDEUS — API Altyapısı Karar Sistemi Analizi

Aşağıda bir Polymarket prediction market trading botunun **tam karar sistemi** var. Bu botu "Optimus Claudeus" olarak adlandırıyoruz. Amacım bu botun **veri altyapısını (API stack)** optimize etmek. Senden istediğim: bu sistemi tamamen anla, eksiklikleri tespit et, ve hangi API'lerin/veri kaynaklarının eklenmesi/değiştirilmesi gerektiğini öner.

---

## 1. MİMARİ GENEL BAKIŞ

Bot iki tip döngü çalıştırır:
- **Light cycle** (~1-5 dk): Sadece fiyat güncelleme + exit kontrolleri (AI yok, tarama yok)
- **Full/Hard cycle** (~10-30 dk): Pazar tarama → veri toplama → AI analiz → giriş kararları → exit kontrolleri

### Dosya Yapısı
| Dosya | Görev |
|-------|-------|
| `src/main.py` | Agent class, ana döngü, tüm karar orkestasyonu |
| `src/config.py` | YAML config, Pydantic modeller, tüm eşikler |
| `src/market_scanner.py` | Gamma API market keşfi + ön filtreleme |
| `src/ai_analyst.py` | Claude Sonnet API çağrıları, prompt oluşturma, bütçe takibi |
| `src/edge_calculator.py` | Edge hesaplama, confidence çarpanları |
| `src/risk_manager.py` | Kelly boyutlandırma + risk kapıları |
| `src/adaptive_kelly.py` | Dinamik Kelly fraksiyonu (confidence/kategori bazlı) |
| `src/reentry_farming.py` | 3 kademeli yeniden giriş havuzu |
| `src/reentry.py` | Kademeli kara liste, yeniden giriş uygunluğu |
| `src/odds_api.py` | Bookmaker oranları (The Odds API) |
| `src/news_scanner.py` | NewsAPI → GNews → RSS fallback zinciri |
| `src/sports_data.py` | ESPN API (ücretsiz, key gerektirmez) |
| `src/outcome_tracker.py` | Çıkış sonrası market takibi |
| `src/sanity_check.py` | AI sonrası mantık doğrulaması |

---

## 2. KONFİGÜRASYON — TÜM EŞİKLER

### Genel
- **Mod:** `dry_run` | `paper` | `live`
- **Başlangıç bankroll:** $60 (simülasyonda $1000)

### Cycle Zamanlama
| Parametre | Değer |
|-----------|-------|
| Varsayılan aralık | 30 dk |
| Breaking news aralığı | 10 dk |
| Stop-loss yakın aralık | 15 dk |
| Gece aralığı | 60 dk |
| Gece saatleri | 00:00-06:00 UTC |

### Market Tarama
| Parametre | Değer |
|-----------|-------|
| Min 24h hacim | $1,000 (düşük — hacim maç yakınında patlar) |
| Min likidite | $1,000 |
| Cycle başına max market | 20 |
| Max süre | 14 gün (seçimler 30 gün) |
| Kısa süre tercihi | Evet |

### AI Konfigürasyonu
| Parametre | Değer |
|-----------|-------|
| Model | claude-sonnet-4-20250514 |
| Max tokens | 1024 |
| Cache TTL | 15 dk |
| Cache invalidation | %5 fiyat hareketi |
| Batch boyutu | 5 market/cycle |
| Aylık bütçe | $48 |
| Sprint bütçesi (2 hafta) | $24 |
| Input maliyeti | $3/Mtok |
| Output maliyeti | $15/Mtok |

### Edge Konfigürasyonu
| Parametre | Değer |
|-----------|-------|
| Minimum edge | %6 |
| Confidence çarpanları | C: 1.5x, B-: 1.0x, B+: 0.85x, A: 0.75x |
| Varsayılan spread | %2 |
| Slot upgrade min edge | %8.5 |

**Efektif edge eşikleri (min_edge × çarpan + spread):**
| Confidence | Eşik |
|------------|-------|
| C | %11 (zaten otomatik skip) |
| B- | %8 |
| B+ | %7.1 |
| A | %6.5 |

### Risk Konfigürasyonu
| Parametre | Değer |
|-----------|-------|
| Kelly fraksiyonu | 0.25 (çeyrek Kelly) |
| Max tek bahis | $75 |
| Max bahis % bankroll | %5 |
| Max pozisyon sayısı | 15 (normal) + 5 VS + 5 FAV + 2 FAR |
| Korelasyon cap | %30 |
| Stop-loss | %30 (normal), %50 (esports), %20 (VS) |
| Take-profit | %40 (normal), %60 (VS) |
| Drawdown halt | %50 (HWM'den) |
| Max günlük yeniden giriş | 5 |
| Max market yeniden giriş | 2 |
| Max maç exposure | %15 |
| Fiyat drift reanaliz | %15 |

### FAR (Uzak Maç) Konfigürasyonu
| Parametre | Değer |
|-----------|-------|
| Max slot | 2 |
| Min edge | %10 |
| Min AI olasılık | %55 |
| Min confidence | B- |
| Min saat (başlangıç) | 6 saat |
| Max saat | 336 saat (14 gün) |
| Penny max fiyat | $0.02 |
| 1¢ hedef çarpan | 5x |
| 2¢ hedef çarpan | 2x |

### FAV (Favori Time Gate) Konfigürasyonu
- AI ≥ %65, confidence A veya B+
- Maç >12 saat uzakta (veya >24 saat fiyat <10¢ ise)
- Edge ≥ %15 gerekli
- 5 ayrılmış slot, 4 saat TTL, %8 staleness toleransı

---

## 3. MARKET TARAMA PIPELINE'I

### Adım 1: Gamma API'den Çekme
- Parent tag ID'leri: sports=1, esports=64
- Sayfalı çekme (200 event/sayfa)
- Hacim sıralı fallback desteği

### Adım 2: Market Ayrıştırma
- condition_id, fiyatlar, token_id'ler, tag'ler, slug, sport_tag
- event_live/ended flag'leri, match_start_iso

### Adım 3: Filtre Zinciri (sıralı)
1. **Kategori filtresi:** sports/esports dışı atla
2. **Hacim filtresi:** min $1,000 (esports için BYPASS — hacim geç patlar)
3. **Likidite filtresi:** min $1,000
4. **Tag filtresi:** yapılandırılmışsa eşleşmeli
5. **Alt-market bloğu:** "Map 1", "Game 2", "first blood" vb. (O/U geçer)
6. **Resolve-yakın filtresi:** YES fiyat > %95 hariç
7. **Süre filtresi:** > max_duration_days
8. **Live/ended filtresi:** Gamma flag'lerinden canlı/bitmiş event'leri atla

### Adım 4: end_date'e göre sıralama (en yakın önce)

---

## 4. ANA CYCLE PIPELINE'I (run_cycle)

### Faz 0: Temizlik
- Milestone hatırlatmaları, self-reflection, scout çalıştırma

### Faz 1: Bankroll & Güvenlik
- Bakiye güncelleme
- Drawdown kontrolü: HWM'den >%50 → tam durdurma
- Circuit breaker kontrolü

### Faz 2: Resolve Olmuş Market Kalibrasyon Kontrolü

### Faz 3: CLOB'dan Pozisyon Fiyat Güncelleme

### Faz 4: Çıkış Kontrolleri (4 katman)
- **Maç-bilinçli çıkışlar** (portfolio.check_match_aware_exits)
- **Stop-loss:** %30 normal, %20 VS, %50 esports
- **Take-profit:** %40 normal, %60 VS (taban %30, tavan %100)
- **Trailing stop:** kademeli (yapılandırılabilir min_peak + drop_pct)
- **VS zorunlu çıkış:** resolve'dan 30 dk önce
- **FAR penny çıkışları:** çarpan hedefleri
- **Farming re-entry kontrolü:** (AI maliyeti yok)

### Faz 4b-4e: Stock'tan Doldurma
- `_fill_from_stock()` — normal adaylar (max 10, 1 saat TTL, %5 fiyat staleness)
- `_fill_from_fav_stock()` — FAV adayları (max 5, 4 saat TTL, %8 staleness)
- `_fill_from_far_stock()` — FAR adayları (max 5, 6 saat TTL, %10 staleness)

### Faz 5: Tüm Slotlar Doluysa Erken Çıkış
- `open_slots == 0` → AI harcanmaz, sadece exit/fiyat kontrolleri

### Faz 5b: Market Tarama
- Eligible cache: 30 dk TTL, pointer bazlı batch işleme
- Cache bayatsa/tükenmişse taze Gamma taraması

### Faz 6: Yeni Market Algılama
- Yeni çıkan marketler öncelik alır (AI cache invalidate)

### Faz 7: AI-Öncesi Filtreler (API maliyeti tasarrufu)
1. Portföyde olanları, cooldown'dakileri, aynı event'tekileri, kara listedekileri çıkar
2. Zaten analiz edilmişleri veya stock'takileri atla (4 saat cache)
3. Alt bahisleri filtrele (spread, handicap, totals, props) — sadece moneyline
4. LIVE maçları filtrele
5. Akıllı batch boyutlandırma: `total_need = open_slots + stock_empty`

### Faz 7f: Yakın-Önce Batch Tahsisi
- Yakın (0-6 saat) > Orta (6-24 saat) > Keşif (>24 saat)
- Pozisyon-bilinçli: az pozisyon açıkken uzak marketleri de keşfet

### Faz 8: Haber Çekme
- Market başına anahtar kelimeler (sorudan top 5 non-stopword token)
- Konu bazlı gruplama (API çağrı tasarrufu)
- **Kaynak zinciri: NewsAPI → GNews → RSS fallback**
- Breaking news → hızlı cycle aralığı + cache invalidation

### Faz 9: Spor Verisi Çekme
- Scout kuyruğu enjeksiyonu (PandaScore/ESPN'den önceden çekilmiş)
- Market başına kaskad: **ESPN → PandaScore → VLR → HLTV**
- Bookmaker oranları (The Odds API, 1 saat cache, sadece ESPN/PandaScore verisi varken)

### Faz 9d: DATA GATE (kritik tasarruf mekanizması)
- Spor verisi YOK VE haber verisi YOK → AI'ı TAMAMEN ATLA
- Neden: AI sadece "Question: X vs Y" ile C/0.50 döndürür — para israfı
- Atlanan market sayısı ve ölü API'ler Telegram cycle raporuna yazılır

---

## 5. AI ANALİZ SİSTEMİ (ai_analyst.py)

### System Prompt Yapısı
- Birleşik FOR/AGAINST/Synthesize framework'ü
- Spor marketleri → `_SPORTS_RULES` (form > all-time, H2H önemli, BO1 volatil)
- Politik marketler → `_POLITICS_RULES` (base rate > narrative, incumbent avantajı)
- Slug rehberi (market slug'larını decode etmek için)

### User Prompt İçeriği
| Veri | Kaynak | Durum |
|------|--------|-------|
| Bugünün tarihi | Sistem | ✅ Her zaman |
| Soru metni | Gamma API | ✅ Her zaman |
| Market slug | Gamma API | ✅ Her zaman |
| Açıklama | Gamma API | ✅ Her zaman |
| Resolution tarihi | Gamma API | ✅ Her zaman |
| Esports/spor maç verisi | ESPN/PandaScore | ⚠️ Sadece spor marketleri |
| Haber makaleleri | NewsAPI/GNews | ❌ Şu an down |
| Bookmaker oranları | Odds API | ❌ Şu an down (1 Nisan'a kadar) |
| Geçmiş dersler | ai_lessons.md | ✅ Varsa |
| **Market fiyatı** | **KASITLI OLARAK HARİÇ** | **Anchoring bias önlemi** |

### AI Çıktısı (JSON)
```json
{
  "probability": 0.XX,        // AI'ın olasılık tahmini
  "confidence": "C|B-|B+|A",  // Güven seviyesi
  "reasoning_pro": "...",      // Lehte argümanlar
  "reasoning_con": "...",      // Aleyhte argümanlar
  "key_evidence_for": [...],   // Destekleyen kanıtlar
  "key_evidence_against": [...] // Karşı kanıtlar
}
```

### Confidence Seviyeleri
| Seviye | Anlam | Davranış |
|--------|-------|----------|
| A | Güçlü veri, yüksek inanç | Min edge %6.5 yeterli |
| B+ | İyi veri, sağlam inanç | Min edge %7.1 |
| B- | Orta veri, orta inanç | Min edge %8, pozisyon boyutu %1.5 bankroll ile sınırlı |
| C | Zayıf/sıfır veri, düşük inanç | Otomatik SKIP — pozisyon açılmaz |

### Bütçe Sistemi
- Aylık: $48, Sprint (2 hafta): $24
- API çağrıları arası 1 sn rate limit
- %50, %75, %90 kullanımda uyarılar
- Tükenince hard stop (C/0.50 döner)
- 15 dk cache, %5 fiyat hareketiyle invalidate

---

## 6. ADAY PUANLAMA & DEĞERLENDİRME

### Edge Hesaplama
```
raw_edge = ai_probability - market_yes_price
threshold = min_edge × confidence_multiplier + spread
```
- `raw_edge > threshold` → BUY_YES
- `raw_edge < -threshold` → BUY_NO
- Arada → HOLD (skip)

### Fill-Ratio Ölçekleme
- Portföy <%30 dolu → `min_edge × 0.8` (daha agresif)
- Portföy >%70 dolu → `min_edge × 1.3` (daha seçici)

### AI Sonrası Kapılar (giriş öncesi tüm kontroller)
1. **Bütçe tükenme kontrolü**
2. **ESPN doğrulama kapısı** — maçın in_progress/completed olmadığını doğrula
3. **Canlı maç bloğu** — maç ortasında pre-match edge geçersiz
4. **Bookmaker güven modifiyeri** — Odds API aynı fikirde: confidence +1 seviye; zıt: -1 seviye
5. **Confidence kapısı:** C = skip; B- için edge ≥ %15 gerekli
6. **Manipülasyon koruması** — likidite, kaynak sayısı, açıklama kontrolü
7. **Ignorance edge koruması:** Confidence bazlı max edge {C: %15, B-: %35, B+: %40}. Aşarsa piyasa muhtemelen daha çok biliyor → ULTI kurtarma
8. **ULTI kurtarma:** %60 bookmaker + %40 AI blend, confidence B+'ya yükselt
9. **Risk yöneticisi:** max_positions, korelasyon cap, Kelly boyutlandırma
10. **Pozisyon boyutu ayarları:** B- → bankroll'un %1.5 ile sınırlı, min $5
11. **Mantık kontrolü:** edge >%40 blokla, AI olasılık >%95 veya <%5 blokla, gap >%25 uyarı
12. **Resolution yakınlık:** resolve'a <20 dk → skip

### Aday Sıralama Skoru
```python
rank_score = edge × CONF_SCORE[confidence] × (1 + time_bonus + freshness_bonus + price_uncertainty_bonus)
```

| Çarpan | Koşul | Bonus |
|--------|-------|-------|
| CONF_SCORE | A: 4, B+: 3, B-: 2, C: 1 | — |
| time_bonus | ≤2 saat: +0.50, ≤6 saat: +0.25, ≤12 saat: +0.10 | Yakın maçlar öncelikli |
| freshness_bonus | ≤2 saat: +0.40, ≤12 saat: +0.20, ≤24 saat: +0.10 | Yeni marketler öncelikli |
| price_uncertainty | mid ≥0.35: +0.15, mid ≥0.20: +0.05 | Belirsiz fiyat daha çok edge potansiyeli |

**Sıralama:** Birincil: confidence seviyesi (A>B+>B-), İkincil: rank_score

---

## 7. GİRİŞ YOLLARI

### Normal Giriş
- En iyi adaylar açık normal slotları doldurur
- max_positions - VS_reserved = 15 normal slot

### FAV (Favori Time Gate)
- AI ≥ %65, confidence A veya B+
- Maç >12 saat uzakta: FAV stock'a kaydet (edge ≥ %15)
- 5 ayrılmış slot, 4 saat TTL
- Pozisyon boyutu: bankroll'un %5'i

### FAR (Uzak Maç Swing)
- >6 saat, edge ≥%10, AI ≥%55
- 2 ayrılmış slot
- Penny ($0.01-$0.02): %5 bankroll, 5x/2x çarpan hedefi
- Swing: %5 bankroll, normal TP/SL

### Volatility Swing (VS)
- Normal giriş sanity/ignorance ile bloklandığında tetiklenir
- Underdog token'ı al (en ucuz taraf)
- Token fiyatı 10-50¢, maç <24 saat
- 5 ayrılmış slot, %20 SL, %60 TP

### Live Dip Girişi
- Kural bazlı, AI maliyeti yok
- Her 5 dk canlı maçlarda >%10 fiyat düşüşü tara
- Sabit $25 veya %5 bankroll

### Slot Upgrade
- Portföy doluyken, kalan adayları en zayıf pozisyonlarla karşılaştır
- Aday 2x daha iyi score gerekli
- Edge ≥ %8.5 (spread maliyetini karşılamalı)
- Asla takas edilmez: hold-to-resolve, kayıptaki, >%5 kârlı, resolve'a <2 saat

### Stock Sistemi (3 katmanlı bekleme havuzu)
| Tip | Max | TTL | Staleness |
|-----|-----|-----|-----------|
| candidate_stock | 10 | 1 saat | %5 |
| fav_stock | 5 | 4 saat | %8 |
| far_stock | 5 | 6 saat | %10 |

- Slot açılınca stock'tan doldurma (AI maliyeti yok)
- Çıkışta pozisyon stock'a indirgenebilir (score = edge × conf_multiplier)
- Mutex: aynı market hem stock'ta hem re-entry'de olamaz

---

## 8. ÇIKIŞ SİSTEMİ

### Çıkış Sebepleri ve Kara Liste Kuralları

| Çıkış Sebebi | Kara Liste Tipi | Cooldown (cycle) |
|---------------|-----------------|------------------|
| catastrophic_floor | Kalıcı | ∞ |
| hold_revoked | Kalıcı | ∞ |
| score_terminal_loss | Kalıcı | ∞ |
| graduated_sl | Zamanlı | 10-30 (elapsed%'ye göre) |
| never_in_profit | Zamanlı | 20 |
| stop_loss | Zamanlı | 25 |
| ultra_low_guard | Zamanlı | 15 |
| take_profit | Re-entry | 5 |
| trailing_stop | Re-entry | 5 |
| spike_exit | Re-entry | 3 |
| scale_out_final | Re-entry | 5 |
| resolved_win | Yok | 0 |
| resolved_loss | Zamanlı | 20 |
| resolved_void | Yok | 0 |
| slot_upgrade | Zamanlı | 10 |
| far_penny | Yok | 0 |
| vs_take_profit | Re-entry | 5 |
| vs_mandatory_exit | Zamanlı | 15 |

### Çıkış Sonrası Akış
1. Pozisyonu portföyden kaldır
2. Cooldown ayarla (varsayılan 3 cycle)
3. **Kârlı çıkış** (TP, trailing, spike, vs_tp): re-entry farming havuzuna ekle
4. **Zararlı çıkış:** stock'a indirgemeyi dene; başarısızsa kara listeye
5. Likidite kontrolü
6. Satış emri çalıştır
7. Realized PnL kaydet, circuit breaker güncelle
8. Analiz cache'inden kaldır (yeniden değerlendirmeye izin ver)
9. outcome_tracker'a ekle (24 saate kadar final resolution izle)
10. price_history, match_outcomes, trade_reasoning logla

### Stock'a İndirgeme Kuralları
- `resolved_*` ve `far_penny*` çıkışları ASLA stock'a giremez
- Diğer tüm çıkışlar (stop_loss, graduated_sl dahil) score bazlı girebilir
- Score > en kötü stock item → yer değiştirir

---

## 9. FARMING RE-ENTRY SİSTEMİ (reentry_farming.py)

AI maliyeti yok — kayıtlı olasılığı kullanır.

### 3 Kademeli Sistem
| Kademe | Min Dip (¢) | Min Dip (%) | Boyut Çarpanı | Min Edge | Stabilize Cycle |
|--------|-------------|-------------|---------------|----------|-----------------|
| 1 | 4¢ | %6 | %80 | %7 | 2 |
| 2 | 7¢ | %10 | %60 | %7 | 3 |
| 3 | 11¢ | %15 | %40 | %10 | 3 |

### Sert Bloklar
- Maç >%66 geçmiş
- AI kaybeden tarafta (eff_ai < %50)
- Zaten portföyde veya aynı event'te
- Max yeniden giriş aşılmış (BO1:2, BO3:3, BO5:3, NBA:3, NHL:2)
- Analiz >4 saat eski
- Fiyat aşırı (>%85 veya <%15)
- Tez kırılmış (fiyat < orijinal_entry - 5¢)
- Günlük re-entry cap: 8
- Kâr koruması: toplam re-entry riski ≥ realized kârın %50'si
- Serbest düşüş: esports 5 cycle'da %15, sports 8 cycle'da %20 düşüş
- Max 3 eşzamanlı re-entry pozisyonu

### Dinamik Elapsed Eşikleri (oyun tipine göre)
| Oyun | BO1 | BO3 | BO5 |
|------|-----|-----|-----|
| CS2/Valorant | %55 | %70 | %75 |
| LoL/Dota2 | %40 | %55 | %65 |
| Futbol | %70 | — | — |
| Basketbol | %75 | — | — |

### Snowball Ban (MOBA)
- LoL/Dota2: maçın %30'undan sonra skor gerideyse re-entry yasak

---

## 10. ADAPTIVE KELLY BOYUTLANDIRMA

### Confidence Bazlı Kelly
| Confidence | Base Kelly |
|------------|-----------|
| C | 0.08 |
| B- | 0.12 |
| B+ | 0.20 |
| A | 0.25 |

### Modifiyerler
- AI olasılık > %80: +0.05 (max 0.30)
- Esports: × 0.90
- Re-entry: × 0.80
- FAR: × 0.70
- Aralık: [0.05, 0.30]

### Kelly Formülü
```python
full_kelly = max(0, (p * b - q) / b)  # b = (1-cost)/cost
actual = full_kelly * adaptive_fraction
bet = min(bankroll * actual, max_bet_usdc, bankroll * max_bet_pct)
```

---

## 11. MEVCUT VERİ KAYNAKLARI — DETAYLI ANALİZ

### ESPN (sports_data.py) — ✅ AKTİF
- **Maliyet:** Ücretsiz, API key gerektirmez
- **Veri:** Takım kayıtları, son 5 maç, sıralamalar, seeding
- **Ek:** Scoreboard kontrolü (canlı/tamamlanmış + gerçek başlangıç saatleri)
- **Cache:** 30 dk, 1 req/sn rate limit
- **Kapsam:** NBA, NFL, MLB, NHL, NCAA, EPL, La Liga, UCL, vb.
- **Kısıt:** Geçmiş istatistik verir ama "kim kazanır?" sorusuna güçlü cevap veremez

### PandaScore — ✅ AKTİF
- **Maliyet:** API key gerekli (mevcut)
- **Veri:** Esports takım istatistikleri, son form, H2H
- **Ek:** Maç başlangıç saatleri
- **Kapsam:** CS2, LoL, Dota2, Valorant, vb.

### The Odds API — ❌ KAPALI (1 Nisan'a kadar)
- **Maliyet:** 500 req/ay ücretsiz
- **Veri:** Bookmaker implied olasılıklar (h2h odds, vig-removed)
- **Kullanım:** "Ultimate ability" — ULTI kurtarma için
- **Cache:** 1 saat
- **Kapsam:** Tüm büyük ABD sporları + futbol ligleri
- **KRİTİK ETKİ:** Olmayınca AI'ın edge tespiti dramatik düşüyor. Bookmaker oranları en güçlü çapa.

### NewsAPI — ❌ GÜN LİMİTİ DOLMUŞ (yarın reset)
- **Maliyet:** Ücretsiz tier, 100 req/gün
- **Veri:** Haber makaleleri, sakatlık haberleri, kadro değişiklikleri
- **Cache:** 45 dk

### GNews — ❌ 403 FORBIDDEN
- **Maliyet:** Ücretsiz tier, 100 req/gün
- **Veri:** NewsAPI ile benzer, fallback olarak kullanılır
- **Cache:** 45 dk

### RSS — ⚠️ SON FALLBACK
- Sınırlı kapsam, yavaş, güvenilmez

### VLR.gg — ⚠️ SCRAPING
- Valorant-spesifik fallback
- Fragile (HTML parsing)

### HLTV.org — ⚠️ SCRAPING
- CS2-spesifik fallback
- Fragile (HTML parsing)

---

## 12. DATA GATE MEKANİZMASI (AI bütçe koruması)

```python
for market in prioritized:
    has_sports = market.condition_id in esports_contexts
    has_news = bool(news_context_by_market.get(market.condition_id))
    if has_sports or has_news:
        has_data_markets.append(market)
    else:
        no_data_markets.append(market)  # AI'a gönderilmez
```

- **Mantık:** Spor verisi VEYA haber verisi olan marketler AI'a gider, olmayanlar atlanır
- **Sonuç:** Data gate atlanan marketler + ölü API'ler Telegram cycle raporunda gösterilir
- **Sorun:** Odds API ve haber API'leri ölüyken, sadece ESPN/PandaScore kapsamındaki marketlere bakılıyor. Diğer tüm marketler (politika, ekonomi, kültür vb.) tamamen kör.

---

## 13. SELF-IMPROVEMENT DÖNGÜSÜ

- **Her 3 günde:** AI self-reflection
  - Son 20 kalibrasyon sonucunu incele
  - 3-5 ders üret (max 400 karakter)
  - `logs/ai_lessons.md`'ye kaydet, gelecek AI prompt'larına enjekte et

- **Her 15 yeni resolved prediction:** Telegram bildirimi

- **Outcome Tracker:** Çıkış sonrası marketi 24 saate kadar izle
  - "Masada para bıraktık mı?" analizi
  - `match_outcomes.jsonl`'a logla

---

## 14. MEVCUT KISITLAMALAR VE SORUNLAR

1. **endDate güvenilmezliği:** Gamma'nın endDate'i settlement buffer, maç bitiş zamanı değil. Scout queue + ESPN/PandaScore ile hafifletilmiş ama tam çözülmemiş.

2. **Canlı skor entegrasyonu yok:** Bot sadece pre-match edge'e sahip, gerçek zamanlı maç içi analiz yok. Maç başlayınca "kör" kalıyor.

3. **Esports hacim paradoksu:** Hacim maçtan ~2 saat önce patlar — hacim filtresini bypass etmek zorundayız, sadece likidite kontrolü.

4. **Bütçe kısıtı:** $48/ay AI bütçesi, cycle başına ~5 market analiz edebiliyor. Daha fazla market = daha fazla maliyet.

5. **WebSocket yok:** Tüm fiyat kontrolleri polling bazlı (Gamma HTTP). Gerçek zamanlı fiyat akışı eksik.

6. **Orderbook derinlik kontrolü yok:** Mevcut likiditeden büyük emir verebilir.

7. **Tahmini maç süreleri:** Gerçek başlangıç saati yoksa hardcoded ortalamalar kullanılıyor.

8. **API'ler ölüyken AI kör:** Odds API + haber API'leri yokken AI'ın elinde sadece "Team A vs Team B, BO3" var → C/0.50 dönüyor, para israfı.

9. **Void/Draw resolution:** 50-50 resolve olan marketler (berabere/iptal) algılanamıyordu — yeni düzeltildi.

10. **Politika/ekonomi marketleri tamamen kör:** Spor dışı marketler için hiçbir yapısal veri kaynağı yok.

---

## 15. SORU — SENİN GÖREVİN

Bu sistemi tamamen anladığını varsayarak:

1. **API Stack Önerisi:** Bu bot için ideal veri kaynağı stack'i ne olmalı? Hangi API'ler eklenmeli, hangileri değiştirilmeli? Her öneri için:
   - Ne veri sağlar?
   - Karar sisteminin hangi noktasına girer?
   - Maliyet/ücretsiz tier limitleri
   - Beklenen etki (confidence artışı, edge tespiti, vb.)

2. **Mevcut API'lerin Optimizasyonu:** Şu anki ESPN, PandaScore, Odds API, NewsAPI/GNews kullanımı nasıl iyileştirilebilir?

3. **Eksik Veri Boyutları:** Şu an hiç karşılanmayan hangi veri boyutları var? (örn: canlı skor, orderbook derinlik, sosyal medya sentiment, vb.)

4. **Maliyet-Etki Matrisi:** Her önerini maliyet vs beklenen etki olarak sırala. Sınırlı bütçeyle ($48/ay AI + API maliyetleri) en çok değeri nereden alabiliriz?

5. **Öncelik Sırası:** "Yarın uygula" → "Bu hafta uygula" → "Gelecek ay uygula" şeklinde önceliklendir.

Cevaplarını somut, uygulanabilir ve teknik olarak detaylı ver. "X yapılabilir" değil, "X'i şu endpoint'ten şu formatta çekip, karar pipeline'ının şu noktasına enjekte et" seviyesinde.
