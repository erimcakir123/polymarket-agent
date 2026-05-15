# İyi Dönem Strateji Geri Dönüşü — Tasarım Belgesi

> **Tarih**: 2026-05-15
> **Durum**: APPROVED (kullanıcı onayı alınmıştır, implementation hazır)
> **Bağlam**: Bot 2.0, mevcut realized PnL −$4.16, peak +$326 (18 Apr 23:31)

---

## Sorun

Bot 2.0, **15 Apr** doğdu, **18 Apr 23:31** peak'inde (+$326.57, 96 trade, %84 winrate, peak HWM $1417) en iyi performansını gösterdi. Sonraki 1 ayda art arda eklenen SPEC'ler (SPEC-008/011/013/014/015/016/J/K/L) bot'u tersine çevirdi; bugün net **−$4.16**.

Veri analizi (112 closed trade) en büyük zarar kaynağını belirledi:
- **`market_flip` kuralı**: −$310.37 (0W/14L), post-peak'te bot'un en büyük katili
- A-conf hold dalında **tek SL** olduğu için pozisyonlar 0.50 altına çakılana kadar tek koruma olmadan yandı

Aynı analizde kâr motoru da netleşti:
- **`near_resolve`** (94¢ kâr lock): +$482 toplam (50+W/3L), bot'un para basma kuralı

---

## Hedef

Peak performans formülünü geri getir, post-peak'te biriken **kanıtlı zararlı modüllerle dead code'u** temizle, mimari (ARCH_GUARD/lean refactor/reboot/dashboard) **dokunulmaz şekilde koru**.

## Başarı Kriterleri

1. `pytest -q` tüm dashboard + domain + strategy + orchestration testleri PASS
2. ARCH_GUARD ihlali yok (5-katman, <400 satır, domain I/O yok, magic number yok)
3. Dead code kalıntısı yok (silinen modüllerin tüm import + test + reference'ları temizlenir)
4. Bot fresh state ile başlar, ilk 24 saatte bot.log'da Exception/Traceback yok
5. Kanıt: 7 gün gözlem sonunda **near_resolve trade'leri pozitif kalmalı**, bot win rate ≥%60 ve net PnL ≥ +$20 hedef

---

## Veri Analizi Özeti (Kararların Temeli)

### Exit reason bazında PnL (112 trade)

| Reason | Net PnL | Kâr motoru mu? |
|---|---:|---|
| `near_resolve` + `near_resolve_profit` | **+$482.69** | ✅ Tek pozitif kaynak |
| Diğer kâr (scale_out, stale_cleanup vs) | +$95.05 | ✅ Yardımcı |
| `market_flip` + `match_exit_a_conf_market_flip` | **−$358.32** | ❌ En büyük katil |
| Diğer SL (graduated_sl, stop_loss, catastrophic) | −$112.81 | Kontrollü kayıp |

### Sport bazında PnL

| Sport | Net PnL |
|---|---:|
| NBA (ML + totals) | **+$61.88** |
| KBO, MLB, AHL | toplam **+$70.00** |
| NHL, baseball generic, WNBA, MMA, UFC, Boxing | toplam **−$164.81** |

### Market type bazında

| Market | Trade | Net PnL |
|---|---|---:|
| Moneyline | 109 | +$75.86 |
| Totals (NBA O/U) | 3 | **+$21.16** |
| Spread | **0** | $0 (dead code) |

---

## Mimari ilkeler (Korunacaklar)

Bu spec **sadece strateji + dead code temizlemesi** yapar. Aşağıdakilere DOKUNULMAZ:

- `ARCHITECTURE_GUARD.md`, `CLAUDE.md`, `TDD.md`, `PRD.md`, `DECISIONS.md`
- `scripts/reboot.py` mekanizması (state/audit ayrımı, archive rotation)
- PortfolioManager / TradeLogger split + `_rewrite_matching` + partial_exits
- Reconcile GUARD-1/2/3/4 (startup phantom-aware reconcile)
- WebSocket SPEC-I reliability (ping watchdog + REST snapshot)
- Process lock, dashboard FMT modülü, period-aware x-axis
- 5-archive sistemi (reboot/wipe veri koruma)
- equity_history mirror + audit/session ayrımı

---

## Stratejik Değişiklikler

### A. KORUNUR (Veri kanıtlı kazandıranlar, peak'te zaten vardı)

| Modül | Kanıt |
|---|---|
| `near_resolve` exit kuralı (94¢ kâr lock) | +$482 toplam, %94+ winrate |
| `scale_out` (partial exit) | Kâr lock partial |
| `graduated_sl` (elapsed-aware SL) | Eski projede çoklu SL portföyünde aktifti |
| `stop_loss` (flat SL %30) | Eski projede aktifti |
| `nba_totals_exit` (SPEC-J totals dispatcher) | +$21 kanıt (T-Wolves 225.5 +$31.76 büyük kazanç) |
| `odds_enricher` base + h2h enrichment | 15 Apr initial, peak'te vardı |
| `SPEC-001 EnrichResult` refactor | 16 Apr, peak'te vardı |
| `night_interval` cycle config | 18 Mart'tan beri |

### B. KALDIRILACAKLAR (Veri kanıtlı zararlı veya dead code)

| Değişiklik | Sebep | Etki |
|---|---|---|
| `a_conf_hold.py` + monitor.py dispatch | Tek SL = market_flip → −$310 katil | Diğer pozisyonlar gibi graduated_sl + flat SL ile yönetilir |
| `nba_spread_exit.py` (SPEC-J spread) | 0 trade dead code | İmport + test + nba_dispatch dalı temizlenir |
| `cricket_score_exit.py` + cricket modülleri (SPEC-011) | 0 trade dead code | Tüm cricket cluster silinir |
| `soccer_score_exit.py` + EventGrouper + three_way (SPEC-015) | 0 trade dead code | Soccer 3-way infrastructure silinir |
| `odds_enricher` SPEC-K eklemeleri (spread/totals enrichment, 10 May) | Peak'te yoktu, NBA totals zaten h2h ile çalışıyor | Sadece h2h dalı kalır |
| `config.yaml` `allowed_sport_tags` daraltma (11 May SPEC-J/L) | Apr peak'te 25 spor açıktı, kâr buradan geldi | 19 Apr commit'inin tag listesi geri (Hockey için NHL ML-only istisnası korunur) |
| `config.yaml` `confidence_multipliers.A: 1.25` → **1.00** | Peak değeri | %6 edge eşiği eski hal |
| `config.yaml` `max_bet_pct: 1.0` (disabled) → **0.05** + `confidence_bet_pct {A:0.05, B:0.04}` | Peak sizing | Risk yönetimi geri |
| `scale_out` tier'ları 19 Apr orijinal değerlerine | Peak'in scale_out davranışı | %25/%40 + %50/%50 |

### C. BELİRSİZ (1. faz uygulamasından sonra 7 gün gözlem → 2. fazda değerlendir)

Bunlar **dokunulmaz**, mevcut hallerinde kalır. Veri toplandıktan sonra:

| Parametre | Neden belirsiz |
|---|---|
| `min_favorite_probability` (SPEC-013) | Peak'in 30 dk sonrası eklendi; WNBA −$55 kayıpları için koruyucu olabilir |
| `max_positions_per_event=2` | Peak'te 1'di ama T-Wolves event +$31 bu gevşemeyle geldi |
| `max_post_start_hours=8.0` | Peak'te yoktu, bot reboot sonrası geç-giriş koruyucusu |
| `min_scale_out_realized_usdc=$7` | Küçük kârları engelliyor, etkisi net değil |
| `SPEC-014` baseball_score_exit | Baseball spor durumuna bağlı |

### D. Hockey istisna (Kullanıcı tercihi)

19 Apr config'inde Hockey için AHL/Liiga/SHL/Mestis/Allsvenskan vardı. **Kullanıcı kararı**: bu alt ligler AÇILMAZ, sadece NHL kalır. Bot'un Mayıs'taki SPEC-L "NHL moneyline-only" davranışını korumak için scanner katmanında sport_rules'a flag eklenir (lean, tek yer, magic number yok).

---

## Dosya Etki Listesi

### Silinecek dosyalar (tamamen kaldırılır, dead code yaratmamak için)

- `src/strategy/exit/a_conf_hold.py`
- `src/strategy/exit/cricket_score_exit.py` (ve tüm cricket modülleri)
- `src/strategy/exit/soccer_score_exit.py`
- `src/strategy/entry/three_way.py`
- `src/orchestration/event_grouper.py`
- `src/strategy/exit/nba_spread_exit.py`
- (Test dosyaları aynı şekilde: `tests/unit/strategy/exit/test_a_conf_hold.py` vb)

### Değiştirilecek dosyalar

- `config.yaml` (sport_tags + confidence + sizing + scale_out)
- `src/config/settings.py` (kaldırılan parametre alanları temizlenir)
- `src/config/sport_rules.py` (NHL "moneyline_only: true" flag eklenir)
- `src/strategy/exit/monitor.py` (a_conf_hold import + dispatch satırları silinir, `else` dalı tüm pozisyonlara uygulanır)
- `src/strategy/exit/nba_dispatch.py` (spread dispatch silinir, sadece totals kalır)
- `src/strategy/enrichment/odds_enricher.py` (SPEC-K spread/totals path silinir, h2h korunur)
- `src/orchestration/scanner.py` veya `entry_processor.py` (cricket/soccer dispatch silinir, NHL moneyline_only filtresi sport_rules üzerinden uygulanır)
- Test dosyaları (silenler için temizleme, modify edilenler için yeni davranışa adaptasyon)

### Korunan dosyalar (dokunulmaz)

- `src/strategy/exit/near_resolve.py`
- `src/strategy/exit/graduated_sl.py`
- `src/strategy/exit/stop_loss.py`
- `src/strategy/exit/scale_out.py`
- `src/strategy/exit/nba_totals_exit.py`
- `src/strategy/exit/favored.py`
- Tüm `src/domain/`, `src/infrastructure/`, `src/orchestration/agent.py`, dashboard kodu, reboot scripti

---

## State Geçiş Akışı

Implementasyon sırası (her adım ayrı commit, her birinden sonra `pytest -q`):

1. **State yedek**: mevcut audit'i `logs/audit/trade_history.archive.YYYYMMDD_HHMMSS.jsonl` benzeri timestamp arşivine kopyala
2. **Config rollback**: `config.yaml` + `src/config/settings.py` + `src/config/sport_rules.py`
3. **A-conf hold kaldır**: dosya sil + monitor.py dispatch güncelle + testleri uyarla
4. **SPEC-J spread temizliği**: nba_spread_exit + nba_dispatch'in spread dalı sil
5. **SPEC-K eklemeleri temizliği**: odds_enricher spread/totals path sil
6. **SPEC-011 cricket cluster sil**: cricket_*.py + ilgili importlar + testler
7. **SPEC-015 soccer 3-way sil**: soccer_score_exit + EventGrouper + three_way + testler
8. **NHL moneyline_only flag eklemesi** (lean entegrasyon): sport_rules + scanner filter
9. **State temizle + bot reload**: positions/circuit_breaker/stock_queue/bot_status sıfırla, audit current ARCHIVE'a taşı, fresh start
10. **Gözlem + doğrulama**: 24 saat trend takibi, hata kaydı yoksa 7 gün sürdür

Her adım test PASS olmadan sonrakine geçilmez. Bot reload yalnızca adım 9'da.

---

## Risk Yönetimi

- Her adımdan önce `git status` temiz olmalı
- Her adım tek commit, kötü giderse `git revert <hash>`
- Tüm test suite (`pytest -q`) PASS şartı
- Bot start sonrası ilk 10 dk'da Exception yoksa devam, varsa rollback

## Geri Çıkış Planı

- Plan kötü giderse: `git reset --hard <pre-rollback-commit>` ile 1 adımda geri
- State'te bozulma olursa: archive'lardan recovery script ile geri yükle (mevcut audit archive sistemi sağlar)
- Hiçbir veri kaybı yok: archive dosyaları tüm tarih boyunca korunur

---

## Faz 2 (Bu plan tamamlandıktan 7 gün sonra)

Bu spec'i takip edecek **ayrı bir spec** ile "Belirsiz" kararlar değerlendirilir:
- 7 günlük yeni veri ile SPEC-013 / max_positions / max_post_start etkileri ölçülür
- Min favorite probability filter'ın WNBA tipi pozisyonları nasıl etkilediği görülür
- min_scale_out_realized_usdc=$7 küçük kâr engelleme etkisi

---

## Not — Kullanıcı sorusu: "Erken çıkarsa ve maç dönerse?"

Multi-SL yaklaşımı kâr kaçırma riski taşır (örn. Wild'da SL erken tetiklense −$10 yerine resolved'a kadar tutulan +$20 kaçabilirdi). Veri analizi gösteriyor ki:
- Bot'un en büyük zararı **geç çıkış** (market_flip −$310)
- Erken çıkış zararı (graduated_sl + flat) eski projede −$50 toplam
- **Net beklenti**: erken çıkışla kayıp önleme, geç çıkış zararından çok daha fazla kazandırır

7 günlük gözlem bu hipotezi test edecek; veri tersini gösterirse Faz 2'de SL eşiği yumuşatılabilir.
