# Polymarket Agent — TODO

## Şimdi Yapılacak (Match-Aware Exit System v2)
- [x] Layer 1: Catastrophic Floor (entry×50%, underdog <25¢ muaf) — match_exit.py
- [x] Layer 2: Progress-based graduated stop loss (elapsed_pct bazlı) — match_exit.py
- [x] Layer 2: Entry-price-adjusted tiers (düşük entry=geniş, yüksek entry=sıkı tolerans) — match_exit.py get_entry_price_multiplier()
- [x] Layer 3: Never-in-profit guard (70% ilerleme, göreceli eşikler entry×0.90/×0.75) — match_exit.py
- [x] Layer 4: Hold-to-resolve revocation matrix — match_exit.py lines 332-368
- [x] Layer 4: Hold-to-resolve restore (geçici iptal, recover ederse geri ver) — match_exit.py
- [x] Score entegrasyonu — match_score parse et, tüm layer'larda kullan (direction-aware) — match_exit.py
- [x] Game-specific duration (CS2/Valorant/LoL/Dota2 × BO1/BO3/BO5) — match_exit.py _DURATION_TABLE + _SPORT_DURATION
- [x] Momentum alert — 3+ consecutive down cycle + min 5¢ delta — match_exit.py lines 307-314
- [x] Son faz toleransı -15% (eskisi -10%) — match_exit.py
- [x] Yeni Position field'ları: ever_in_profit, consecutive_down_cycles, previous_cycle_price, hold_revoked_at, hold_was_original, cumulative_drop — models.py
- [x] Price history toplama (CLOB API, pozisyon kapanınca kaydet) — price_history.py
- [x] Ultra-low <9¢ guard — elapsed>75% + price<5¢ ise çık — match_exit.py line 322-326
- [x] Pending resolution fix — pending + kârdaysa hold (oracle bekle), zarardaysa normal exit — portfolio.py check_take_profits/check_match_aware_exits/check_scale_outs

## Data API Entegrasyonu (Cascade Sistemi)
### Şimdi (Free Tier Test)
- [x] HLTV scraper (hltv-async-api) — CS2 tier-2/3 takım istatistikleri — hltv_data.py
- [x] VLR scraper (vlrdevapi) — Valorant tier-2/3 maç geçmişi — vlr_data.py
- [x] Cascade sırası: PandaScore → HLTV/VLR → The Odds API (fallback) — esports_data.py
- [ ] Dashboard API kullanım kartı — Claude API + The Odds API bar'ları

### API Karşılaştırma & İleride Karar Verilecek
| API | Free | İlk Ücretli | Not |
|-----|------|-------------|-----|
| ~~OddsPapi~~ | ~~250 req/ay~~ | ~~$49/ay~~ | ❌ İptal — 250 req yetersiz, ücretli pahalı |
| The Odds API | 500 credit/ay | $30/ay (20K) | ✅ Zaten entegre, esports zayıf ama fallback olarak iyi |
| PandaScore | 1000 req/saat | €150/ay | Mevcut, tier-1 iyi ama tier-2/3 zayıf |
| SportsGameOdds | 2500 obj/ay | $99/ay (100K) | Key var, sadece geleneksel spor (esports yok), 8 lig, 9 bookmaker |
| HLTV scraper | Sınırsız | — | CS2 tüm tier'lar, Cloudflare riski, proxy gerekebilir |
| VLR scraper | Sınırsız | — | Valorant tüm tier'lar |
| Riot Games API | Sınırsız | — | LoL/Valorant resmi API, key gereksiz |
| OpenDota API | 60 req/dk | — | Dota2 open source API, key gereksiz |
- [ ] SportsGameOdds entegrasyonu — key var (.env), geleneksel spor odds fallback olarak kullan
- [ ] SportsGameOdds vs The Odds API karşılaştır — $99/ay Rookie plan (17 lig, 77 bookmaker) değer mi?
- [ ] Bot kârlı olunca: The Odds API 20K ($30/ay) veya SportsGameOdds Rookie ($99/ay) upgrade değerlendir
- [ ] RapidAPI Dota2 API + Valorant Esports API free tier test et

## Mimari İyileştirme: Polymarket-First Pipeline
- [ ] **Pipeline tersine çevir** — Şu an: ESPN scout → Polymarket eşleştir. Hedef: Polymarket market'ler → ESPN/Odds API enrichment. Scout bonus olarak kalsın.
  - Pipeline: Polymarket H2H market'ler → chrono + pre-filter → enrichment (Odds API + ESPN paralel) → data quality gate → AI analiz → entry
  - ESPN match bulursa → confidence boost (A eligible). Sadece Odds API bulursa → B+ eligible. Hiçbiri bulamazsa → skip
  - Scout'un 60+ lig tarama maliyetini ortadan kaldırır
- [ ] **Composite selection score** — Sadece zamana göre sıralama yerine: zaman (0-40p) + mispricing sinyali (0-30p, toss-up=en çok edge potansiyeli) + novelty (0-20p) + liquidity (0-10p)
- [ ] **Esports damage-ladder exit stratejisi** — Plan hazır: `plans/nifty-snacking-hearth.md`. Skor bazlı kademeli pozisyon küçültme (trailing TP/SL yerine). Esports açıldığında implemente et.

## Gelecek Geliştirmeler
- [ ] Dynamic hold-to-resolve promotion — kâr %50+ ve AI certainty >60% ise scouted'a promote et, %50 altına düşünce geri al (30+ sample sonrası kalibre)
- [ ] Maç sonucu log'lama — pozisyon kapanınca Gamma API'den final sonucu çek, logs/match_outcomes.jsonl'e kaydet (AI tahmin vs gerçek sonuç karşılaştırma)
- [ ] Pool dolu iken AI skip — slot açık yoksa Claude API çağırma, kredi harcama (şu an 0 slot olsa bile analiz yapıyor)
- [x] WebSocket live prices — CLOB WebSocket ile gerçek zamanlı fiyat akışı — websocket_feed.py
- [x] Price movement tracking — Her cycle fiyat değişimini kaydet — price_history.py + websocket_feed.py
- [x] PandaScore live match state — Canlı maç durumu, skor, map break detection — esports_data.py
- [x] Map break detection — Harita arası tespit, re-entry pause — reentry_farming.py
- [x] Score-aware re-entry — Skor farkına göre AI probability ayarlama — reentry_farming.py
- [x] Halftime exit with live state — Canlı skor ile devre arası çıkış — portfolio.py

## Test Sürecinde Eklenecek (Live Öncesi)
- [ ] **Market Filter: `sportsMarketType` field-based whitelist** — Polymarket her market'te `sportsMarketType` field'ı döndürüyor (canlı teyit 2026-04-05 via `GET /sports/market-types` → 97 tip). `MarketData` ([src/models.py:25-47](src/models.py)) bu field'ı okumuyor. Filter ([src/market_scanner.py:283-298](src/market_scanner.py)) slug-pattern matching yapıyor — `-first-half-` var ama `-first-set-` yok. Sonuç: Friedsam vs Kalinina `tennis_first_set_winner` marketi sızdı, pozisyon -$4.65 kaybettirdi (doğru yön, yanlış market tipi). **Fix:** (1) `MarketData`'ya `sports_market_type: str = ""` ekle, (2) Gamma parser'da aktarımı yap, (3) filter başına whitelist `{"moneyline", ""}`, (4) slug pattern fallback koru, (5) ikinci hat: `-first-set-`, `-set-1-`, `-set-2-`, `-set-winner-`, `-match-totals-`, `-set-totals-`, `-set-handicap-`, `-total-games-` ekle.
- [ ] **`child_moneyline` araştırması** — Polymarket 97 tipin arasında `child_moneyline` var. Parlay altı mı, player-specific mi, sub-event mi bilinmiyor. Whitelist kararı bu araştırmaya bağlı. **Komut:** `curl -s "https://gamma-api.polymarket.com/markets?closed=false&limit=200" | python -c "import json,sys; [print(m.get('slug'), '|', m.get('question')) for m in json.load(sys.stdin) if m.get('sportsMarketType')=='child_moneyline']"` → 2-3 örnek incele, whitelist'e ekle veya bırak.
- [ ] **Dual-prompt (Devil's Advocate) geri ekle** — Şu an tek prompt ile olasılık tahmini yapıyor, ucuz olsun diye kaldırıldı. İkinci prompt belirsizlik filtresi sağlıyordu (iki tahminin farkı büyükse "belirsiz" → giriş eşiği yükseliyordu). Haiku ucuz model olarak kullanılabilir. **Bak:** `src/probability_engine.py:get_edge_threshold_adjustment()` (hazır fonksiyon, sadece bağlantısı kopuk), `src/ai_analyst.py` (prompt logic)
- [ ] **CLOB orderbook depth check (entry + exit)** — `src/liquidity_check.py` hazır ama entry/exit pipeline'a bağlı değil. Live öncesi wire-up et.
- [ ] **Esports ücretli odds API bul** — Şu an esports'ta sadece PandaScore (match history) var, bookmaker odds yok. AI tek kaynak ile karar veriyor (B+ confidence). Ücretli esports odds API bul ve entegre et (örn: Pinnacle API, Betfair Exchange, veya esports-specific odds provider). Olmazsa esports'ta sadece consensus bet'lere izin ver.
- [ ] **Claude API spend limit ayarla** — config.yaml'da monthly_budget_usd + sprint_budget_usd (şu an 0=unlimited), Anthropic console'da da spend limit koy. Simulation bitmeden önce MUTLAKA ayarla!
- [ ] Partial exit — binary çıkış yerine %50/%75 kademeli çıkış (CLOB partial sell)
- [ ] Kelly rebalance — maç sırasında pozisyon boyutu güncelleme
- [ ] Liquidity check — order book derinliği kontrol (entry + exit). **Bak:** `src/liquidity_check.py` (hazır, wire-up bekliyor)
- [ ] Bayesian calibrator — otomatik threshold kalibrasyonu (30+ sample sonrası)
- [ ] Portfolio circuit breaker — günlük -%8, saatlik -%5 devre kesici
- [ ] ATR-based dynamic catastrophic floor — volatiliteye göre floor ayarlama
- [ ] Momentum → position sizing — 3+ down cycle aktifken sonraki bet %20 küçült
- [ ] Adaptive duration — gerçek elapsed'e göre tahmini süreyi runtime'da güncelle
- [ ] EMA trend overlay — momentum alert'e EMA-5 bazlı trend doğrulama ekle

## Tamamlanan
- [x] ESPN matcher threshold (matched < 2)
- [x] Trailing stop min_profit_floor (kayıptayken trailing stop tetiklenmesin)
- [x] Scout re-entry (TP/trailing sonrası %15 düşüşte tekrar gir)
- [x] Scouted hold-to-resolve guard (B+ confidence + >60% AI certainty)
- [x] Gamma slug-based price updates (conditionId broken, slug çalışıyor)
- [x] Match timing from Gamma API (startTime, live, ended, score, period)
- [x] Dashboard: match time, countdown, live status, score
- [x] Pending positions: Active tab'dan filtrele, live_on_clob=False
- [x] Stale Gamma event data fallback (elapsed time estimation)
- [x] Match-aware 4-layer exit system (catastrophic floor, graduated SL, never-in-profit guard, hold-to-resolve)
- [x] Game-specific duration table (CS2/Val/LoL/Dota2 × BO1/BO3/BO5 + 20 geleneksel spor)
- [x] Entry-price-adjusted tiers (get_entry_price_multiplier)
- [x] Momentum tightening (3+/5+ consecutive down cycles)
- [x] Ultra-low guard (<9¢ entry, >90% elapsed, <5¢ current)
- [x] Price history collection (CLOB API, position close'da kaydet)
- [x] Position tracking fields (ever_in_profit, consecutive_down_cycles, cumulative_drop, etc.)
- [x] Hold-to-resolve revocation & restore
- [x] WebSocket CLOB price feed (real-time streaming)
- [x] PandaScore live match state (running matches, score, map break)
- [x] Score-aware re-entry farming (map break pause, score-adjusted probability)
- [x] Halftime exit with live state (actual map score vs time-based fallback)
- [x] HLTV + VLR scrapers (CS2/Valorant tier-2/3 data)
- [x] Data cascade: PandaScore → HLTV/VLR → The Odds API
- [x] Fix 3: Underdog entry guard — elapsed-based graduated sizing (<20¢ entry) — entry_gate.py `_underdog_elapsed_size_multiplier()`
- [x] Fix 4: Pending resolution — kârdaysa hold (oracle bekle), zarardaysa normal exit — portfolio.py
- [x] Upset/penny forced exit 90% → 75% — match_exit.py line 298-309
- [x] Trail distance 8% → 15% — config.py + trailing_tp.py
- [x] 10-dakika momentum snapshot (WS modunda revoke tracking) — agent.py light cycle
