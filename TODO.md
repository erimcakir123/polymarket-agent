# Polymarket Agent — TODO

## Şimdi Yapılacak (Match-Aware Exit System v2)
- [ ] Layer 1: Catastrophic Floor (entry×50%, underdog <25¢ muaf)
- [ ] Layer 2: Progress-based graduated stop loss (elapsed_pct bazlı)
- [ ] Layer 2: Entry-price-adjusted tiers (düşük entry=geniş, yüksek entry=sıkı tolerans)
- [ ] Layer 3: Never-in-profit guard (70% ilerleme, göreceli eşikler entry×0.90/×0.75)
- [ ] Layer 4: Hold-to-resolve revocation matrix
- [ ] Layer 4: Hold-to-resolve restore (geçici iptal, recover ederse geri ver)
- [ ] Score entegrasyonu — match_score parse et, tüm layer'larda kullan (direction-aware)
- [ ] Game-specific duration (CS2/Valorant/LoL/Dota2 × BO1/BO3/BO5)
- [ ] Momentum alert — 3+ consecutive down cycle + min 5¢ delta
- [ ] Son faz toleransı -15% (eskisi -10%)
- [ ] Yeni Position field'ları: ever_in_profit, consecutive_down_cycles, previous_cycle_price, hold_revoked_at, hold_was_original, cumulative_drop
- [ ] Price history toplama (CLOB API, pozisyon kapanınca kaydet)
- [ ] Ultra-low <9¢ guard — elapsed>90% + price<5¢ ise çık (şu an hiç SL yok)
- [ ] Pending resolution fix — pending pozisyonlar exit logic'i atlamamalı (kârdaysa hold, zarardaysa da hold ama bypass değil)

## Gelecek Geliştirmeler
- [ ] WebSocket live prices — CLOB WebSocket ile gerçek zamanlı fiyat akışı (polling yerine), anlık SL/TP tetikleme
- [ ] Price movement tracking — Her cycle fiyat değişimini kaydet, momentum/trend analizi, spike detection, entry/exit kararlarına veri sağla
- [ ] Odds API 20K plan ($30/mo) — Live trading için gerçek zamanlı oran verisi, PandaScore'a ek olarak

## Test Sürecinde Eklenecek (Live Öncesi)
- [ ] Partial exit — binary çıkış yerine %50/%75 kademeli çıkış (CLOB partial sell)
- [ ] Kelly rebalance — maç sırasında pozisyon boyutu güncelleme
- [ ] Liquidity check — order book derinliği kontrol, slippage önleme (entry + exit)
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
