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

## Dashboard UX
- [ ] **Pozisyon kartlarında "kime oynadık" göster** — "Will Club Atletico de Madrid win? NO" yerine "FC Barcelona kazanır" gibi. BUY_NO ise karşı takım adını göster. Oranlar da kazanacağını düşündüğümüz tarafın oranı olsun.
- [ ] **Same-event guard fix** — event_id boş geliyor, aynı maçın iki tarafına girilebiliyor. Gamma event_id parse edilmeli.

## Temizlik
- [ ] **News scanner kodunu sil** — Tavily, NewsAPI, GNews, RSS. %96 fail rate, 15 dk cycle uzatıyordu. `src/news_scanner.py` + entry_gate referansları + agent.py init. Şu an disable edildi, tamamen kaldırılacak.

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

## Data Coverage Gaps (Tracked 2026-04-09)

Following the tennis TML + chess (Lichess/Chess.com) integration, these gaps remain:

### WTA (Women's tennis)
- TML-Database only publishes ATP data (verified empirically 2026-04-09: all WTA file paths return 404)
- ESPN WTA scoreboard data is sparse
- Options evaluated:
  - (a) Skip WTA entirely — safest, current state
  - (b) api-tennis.com 14-day trial — vendor lock-in risk
  - (c) sportdevs 300 req/day trial
  - (d) tennis-data.co.uk weekly CSVs — site had timeout issues during testing
- Decision: deferred pending user choice

### Low-coverage football leagues
- Egypt Premier League (egypt-1): ESPN does not cover (10 markets/cycle skipped)
- Europa Conference League (europa-conference-league): ESPN does not cover (8 markets/cycle skipped)
- Saudi Professional League (saudi-professional-league): ESPN partial coverage (4 markets/cycle skipped)
- Potential sources:
  - api-football (RapidAPI) — free tier limited
  - football-data.org — unclear coverage for these leagues
- Action: monitor frequency of skips; if >10 markets/cycle consistently, investigate paid source

### Future chess features
- Polymarket chess events contain 3-way markets (Player A win / Player B win / Draw)
- Currently we fetch draw market prices as signal, but bot only enters player-win markets
- Future: add direct draw-market entry strategy when both players have high historical draw rates
- Future: track chess tournament round number (already in slug) for fatigue modeling
- Future: if Magnus Carlsen's Lichess account (DrNykterstein) cannot be auto-resolved (no realName set, skipped by bulk lookup), Chess.com-only resolution is acceptable fallback

## Clean-code refactors (last priority)

### Chess cache persistence hygiene (from Task 10 audit, 2026-04-11)
- **W1 — chess_username_resolver.py:83-94** `_persist_cache()` writes two files sequentially (`username_map.json` + `unresolved.json`). If the first `replace` succeeds and the second `write_text` fails mid-write, disk ends up with orphan `.tmp` + divergent state (resolved names fresh, failed cache stale). No runtime break — next successful persist re-sync's — but a crash between the two writes leaves a dangling `.tmp`. Fix options: merge both dicts into a single JSON file, or add orphan-`.tmp` cleanup on startup. Severity: low.
- **W2 — chess_data.py:358-359** `_persist_cache()` is called inside `_lock` after every successful `_get_player_stats()`. One chess-heavy cycle with 5 markets = 5 full `stats_cache.json` serializations + disk syncs back-to-back. Correctness is fine (lock guards iteration), just redundant I/O. Fix options: dirty-flag + single cycle-end persist, or 30s throttled persist. Severity: low (perf, not correctness).
- **Why deferred**: Both are low severity. Chess/tennis area is new and will see more iteration — revisit during the next refactor pass in this area rather than opening a dedicated fix PR.

### Remove pos.scouted field — duplicate of confidence == "A"
- **Problem**: `Position.scouted` bool field and `confidence == "A"` carry the same meaning in the exit path. Exit monitor already ignores `pos.scouted` and dispatches hold-to-resolve behavior purely off confidence. `pos.scouted` is only used for post-hoc logging annotations and one `handle_hold_revokes` branch in exit_executor.py that toggles the flag without affecting exit decisions.
- **Scope** (~35 lines, 9 files):
  - `src/models.py` — remove `Position.scouted` field definition
  - `src/portfolio.py` — stop constructing/serializing the field
  - `src/exit_executor.py` — replace revoke branch with `confidence = "B-"` demotion (so hold-to-resolve naturally stops)
  - `src/match_exit.py`, `src/match_outcomes.py`, `src/outcome_tracker.py`, `src/reentry_farming.py`, `src/live_strategies.py`, `src/price_updater.py` — drop `scouted` / `was_scouted` parameters (pass-through logging annotations only)
- **Do NOT touch**: `src/scout_scheduler.py`, `src/agent.py` scout cycles, `src/matching/__init__.py`, `src/entry_gate.py:mark_entered`, `src/cycle_timer.py`, `logs/scout_queue.json`. These belong to the separate "ScoutScheduler" match-calendar system, which is critical and must keep working.
- **Risk**: Medium. Multi-file, affects in-flight positions (revoke branch behavior changes). Requires Medium-change protocol: plan → audit → 2 consecutive CLEAN rounds.
- **Why deferred**: Dashboard badge was the only user-visible symptom (already removed). Dead code underneath bot is benign. Prioritize revenue-relevant fixes first.
