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

### PLAN-FAZ2-001: İyi-Donem Rollback Gözlem Aşaması

- **Durum**: OBSERVATION
- **Tarih başlangıç**: 2026-05-15
- **Süre**: 24-168 saat (1-7 gün)
- **Öncelik**: P1

**Bağlam:**
İyi-donem strateji rollback Faz 1 tamamlandı (10 task, commit'ler `f353955` → `1176ad2`). Bot 19 Apr peak config + temiz strateji ile fresh state'te çalışıyor (bankroll $1000, realized $0).

**Hedef:**
Bot'un yeni davranışını 7 gün gözle, Faz 2 spec'i için veri topla.

**Gözlem kriterleri (7 gün sonu):**
- Net realized PnL ≥ +$20 (hedef)
- Win rate ≥ %60
- `near_resolve` trade'leri pozitif kalmalı (peak'in kâr motoru)
- `graduated_sl` + `flat SL` (yeni multi-SL pattern) çalışıyor mu — büyük kayıp önleme

**Faz 2 spec'inde ele alınacak belirsiz kararlar (TODO-FAZ2-001/002 başvur):**
- SPEC-014 baseball_score_exit: baseball moneyline pozitif mi negatif mi?
- `agent.max_positions_per_event=2` (1'e geri inelim mi?)
- `scanner.max_post_start_hours=8.0` (kalksın mı?)
- SPEC-013 `min_favorite_probability` filter (WNBA tipi korumacı mı?)
- `min_scale_out_realized_usdc=$7` gate (kaldırıldı ama Faz 2'de geri ekleme analizi)

**Sonraki adım:**
- 24 saat sonra: ilk trade panoraması (kaç trade, exit reason dağılımı, near_resolve vs market_flip vs graduated_sl ratio'ları)
- 7 gün sonra: tam analiz + Faz 2 spec yaz (`docs/superpowers/specs/2026-05-22-faz2-belirsizler.md`)
- Faz 2 spec onaylanırsa → writing-plans → implementation

**Geri çıkış kapısı:**
İlk 48 saatte trend belirgin negatifse (realized < −$30) Faz 1 rollback'ı sorgula. State yedeği `data/positions.pre_rollback_20260515_160958.bak` mevcut, `logs/_pre_rollback_backup_20260515_160958/` audit yedeği var.

---

*Faz 1 tamamlandı 2026-05-15 — yukarıdaki plan + ilgili spec aktif tek planımız.*

---

### PLAN-TENNIS-001: Tennis Lab Full Paper Trading Wire-Up

- **Durum**: APPROVED
- **Tarih**: 2026-05-20
- **Öncelik**: P0
- **Branch**: feature/tennis-lab (worktree — main repo'ya sıfır risk)

**Bağlam:**
Tennis lab şu an sadece prediction üretip JSONL'e log atıyor — pozisyon açmıyor, exit yapmıyor, dashboard widget'larını beslemiyor. Kullanıcı baştan beri ana botun **birebir aynısı**ni istiyor: entry + SL/TP + exit + dashboard görselleştirme — tek fark edge kaynağı (bookmaker konsensüsü değil Glicko + Klaassen-Magnus).

**Hedef:**
Ana bottaki sport-agnostic `EntryProcessor` + `ExitProcessor` + sizing + state machinery'sini tennis tarafına bağla. Tennis tahminleri (mevcut EdgeCandidate akışı) → Signal'a çevrilip aynı pipeline'a beslenecek. Bittiğinde:
- positions.json tennis pozisyonlarını tutacak
- trade_history.jsonl entry+exit'leri kaydedecek
- equity_history.jsonl her cycle sonunda snapshot atacak
- Dashboard'ta tüm widget'lar (Balance, Open P&L, Realized, Positions, Loss Protection, Branches, Charts, Trade feed) çalışacak

**Mimari karar:**
- Ana botun `EntryProcessor`, `ExitProcessor`, `Gate`, `exit_monitor`, `confidence_position_size`, `EquityHistoryLogger`, `TradeLogger`, `PositionsStore` aynen REUSE — yeniden yazmak yasak (DRY).
- Yeni dosya: `src/strategy/entry/tennis_signal_adapter.py` — EdgeCandidate + MarketData → Signal dönüşümü.
- Yeni enum değeri: `EntryReason.TENNIS` (entry attribution için).
- `tennis_factory.py` genişler: entry_processor + exit_processor + state stores'u kompose eder.
- `tennis_agent.run_one_cycle` HEAVY + LIGHT iş yapar: scan→enrich→adapt→entry→exit→equity_snapshot.

**Yapılmayacaklar (YAGNI):**
- Tennis-specific exit rules (set-boundary, time-to-start, vs.) — V2'ye ertelenir.
- Tennis için ayrı CycleManager — basit while loop yeter (tennis maçları sık değil).
- Live-score tracking — paper mode için fiyat takibi yeterli.

---

#### Stage 0: Scanner Tennis Match Filter Fix

**Sorun:**
`python scripts/tennis_main.py --once` 24245 market tarayıp 0 sonuç döndü. `polymarket.com/sports/tennis/games` aktif tennis maçları gösteriyor — scanner filtreleri çok dar.

**Hipotez (öncelik sırasıyla):**
1. `allowed_sports_market_types: [tennis_first_set_winner, tennis_set_handicap, tennis_set_totals]` — Polymarket'in gerçek sports_market_type değerleriyle eşleşmiyor olabilir.
2. `max_hours_to_start: 24.0` — yarından sonraki maçları atıyor olabilir (ATP turnuvalarında bracket önceden açılır).
3. `singles-only` filter doubles dışında maç bırakmıyor olabilir.

**Adımlar:**
- [ ] Debug script: `scripts/debug_tennis_markets.py` — Polymarket'ten tennis tag'li tüm market'leri çek, `sport_tag` + `sports_market_type` + `match_start_iso` + `slug` bas.
- [ ] Çıktıya bak: gerçek sports_market_type değerleri ne? (ör. `tennis_match_winner`, `tennis_total_games`, vs.)
- [ ] `config_tennis.yaml` güncelle:
  - `allowed_sport_tags: [tennis]` (atp ölü kayıt, gamma_client zaten "tennis" normalize ediyor)
  - `allowed_sports_market_types: [<gerçek değerler>]`
  - `max_hours_to_start: 72.0` (3 güne çıkar — tennis bracket'ları erken açılır)
- [ ] Test: `python scripts/tennis_main.py --once` ≥1 tennis market bulmalı.
- [ ] Commit.

**Kabul kriterleri:**
- [ ] Scanner 0'dan fazla tennis market döndürüyor.
- [ ] Debug script `scripts/` altında çalışıyor.

---

#### Stage 1: EntryReason.TENNIS Enum Değeri

**Bağlam:**
Main bot `EntryReason` enum'unu entry attribution için kullanıyor (`NORMAL`, `EARLY`, `CONSENSUS_FORCE`, vs.). Tennis pozisyonlarının kaynak fark edilsin diye `TENNIS` değeri eklenecek.

**Adımlar:**
- [ ] Test: `tests/models/test_entry_reason.py` — `EntryReason.TENNIS.value == "tennis"` assert et.
- [ ] Run test → fail (enum değeri yok).
- [ ] Implement: `src/models/<entry_reason_file>` — `TENNIS = "tennis"` ekle.
- [ ] Run test → pass.
- [ ] Commit.

**Kabul kriterleri:**
- [ ] `EntryReason.TENNIS` import edilebilir, value = `"tennis"`.
- [ ] Mevcut entry tests bozulmadı.

---

#### Stage 2: Tennis Signal Adapter

**Sorun:**
EntryProcessor.gate.run() `Signal` bekliyor; tennis akışı `EdgeCandidate` üretiyor. Aradaki adapter eksik.

**Adapter signature:**
```python
def tennis_candidate_to_signal(
    candidate: EdgeCandidate,
    market: MarketData,
    tier: str,  # "A" | "B"
) -> Signal
```

**Mapping (research'ten):**
| Signal field | Kaynak |
|---|---|
| condition_id | market.condition_id |
| direction | Direction.BUY_YES if candidate.edge > 0 else BUY_NO |
| anchor_probability | candidate.model_p (P(YES) anchor — tennis enricher zaten yes_price ile mapliyor) |
| market_price | candidate.market_p (= market.yes_price) |
| edge | candidate.edge (signed) |
| confidence | tier ("A" / "B") |
| size_usdc | 0.0 (gate sizing'i hesaplar) |
| entry_reason | EntryReason.TENNIS |
| bookmaker_prob | 0.0 (tennis bookmaker konsensüsü kullanmıyor) |
| num_bookmakers | 0 |
| has_sharp | False |
| sport_tag | market.sport_tag or "tennis" |
| event_id | market.event_id or "" |

**Adımlar:**
- [ ] Test: `tests/strategy/entry/test_tennis_signal_adapter.py`:
  - `test_adapter_buy_yes_when_edge_positive`
  - `test_adapter_buy_no_when_edge_negative`
  - `test_adapter_preserves_anchor_probability`
  - `test_adapter_sets_tennis_entry_reason`
  - `test_adapter_zeroes_bookmaker_fields`
- [ ] Run tests → fail.
- [ ] Implement: `src/strategy/entry/tennis_signal_adapter.py` (~50 satır).
- [ ] Run tests → pass.
- [ ] Commit.

**Kabul kriterleri:**
- [ ] Adapter, EdgeCandidate edge işaretine göre direction seçer.
- [ ] anchor_probability = candidate.model_p korunur.
- [ ] entry_reason = EntryReason.TENNIS.
- [ ] Tüm bookmaker alanları sıfır/False (tennis konsensüs kullanmıyor).

---

#### Stage 3: Tennis Sizing Config

**Bağlam:**
Kullanıcı kararı: bankroll $500, max bet $50, A/B tier sizing.

**Adımlar:**
- [ ] `config_tennis.yaml` güncelle:
  ```yaml
  initial_bankroll: 500
  risk:
    confidence_bet_pct:
      A: 0.10   # %10 bankroll = $50 (max)
      B: 0.08   # %8 bankroll = $40
    max_bet_usdc: 50.0
    max_bet_pct: 0.10
  ```
- [ ] Test: `tests/config/test_tennis_sizing.py` — config yüklenince bu değerler okunmalı.
- [ ] Run test → pass (sadece config okuma).
- [ ] Commit.

**Kabul kriterleri:**
- [ ] config_tennis.yaml tier A → $50, tier B → $40 verir.
- [ ] max_bet $50 cap aktif.

---

#### Stage 4: Wire EntryProcessor (Heavy Cycle)

**Bağlam:**
tennis_agent.run_one_cycle scan + enrich yaptıktan sonra adayları EntryProcessor üzerinden geçirmesi gerek.

**Karar — kompozisyon:**
- `tennis_factory.build_tennis_deps` genişletilir, içine `entry_processor` + `exit_processor` + state stores eklenir.
- EntryProcessor zaten kendi içinde scanner çağrısı yapıyor (run_heavy → scan → gate → execute). Tennis'te scan + enrich AYRI yapılıp `EntryProcessor._execute_entry(signal)` direkt çağrılabilir.
- Daha temiz yol: EntryProcessor'un `process_signals(signals: list[Signal])` public API'ı varsa onu kullan; yoksa private metoda dokunmadan kendi mini executor'umuzu yaz.

**Adımlar:**
- [ ] EntryProcessor'un signal-injection API'ını araştır (entry_processor.py). Public API yoksa **yeni public method ekle**: `process_signals(markets: list[MarketData], signals: list[Signal])`.
- [ ] Test: `tests/orchestration/test_entry_processor_tennis_signals.py`:
  - `test_process_signals_creates_position` — fake market+signal verilince positions.json'a yazılmalı.
  - `test_process_signals_respects_max_positions` — max_positions cap'i aşılmazsa.
- [ ] Run tests → fail.
- [ ] Implement: EntryProcessor.process_signals (~30 satır).
- [ ] Run tests → pass.
- [ ] tennis_factory'a entry_processor ekle.
- [ ] tennis_agent.run_one_cycle güncelle: enrich sonrası adapter→signals→entry_processor.process_signals çağır.
- [ ] Test: `tests/orchestration/test_tennis_agent_entry_wiring.py` — fake deps ile cycle koşunca positions.json güncelleniyor mu.
- [ ] Run tests → pass.
- [ ] Commit.

**Kabul kriterleri:**
- [ ] Tennis cycle sonrası positions.json'da tennis pozisyonu (condition_id, size, entry_price) var.
- [ ] trade_history.jsonl'da entry kaydı atıldı.
- [ ] EntryReason = "tennis" olarak kaydedildi.

---

#### Stage 5: Wire ExitProcessor (Light Cycle)

**Bağlam:**
ExitProcessor sport-agnostic — tennis pozisyonlarını da işliyor. Tek yapacağımız tennis cycle'a ExitProcessor.run_light() eklemek.

**Adımlar:**
- [ ] tennis_factory'a exit_processor ekle (dependency wire-up).
- [ ] tennis_agent: light cycle ayrı bir interval'da koşacak. Karar — basit yol:
  - Heavy cycle: 30dk (mevcut --interval).
  - Light cycle: 60sn (her dakika exit check).
  - Loop: her saniye uyan, son heavy'den 30dk geçtiyse heavy çalıştır, son light'tan 60sn geçtiyse light çalıştır.
- [ ] Test: `tests/orchestration/test_tennis_agent_exit_wiring.py`:
  - `test_light_cycle_calls_exit_processor` — fake exit_processor.run_light çağrıldı mı.
  - `test_heavy_and_light_independent_schedules` — heavy interval ile light interval ayrı tetikleniyor.
- [ ] Run tests → fail.
- [ ] Implement: tennis_agent.run_forever loop'unu interval-based yap.
- [ ] Run tests → pass.
- [ ] Commit.

**Kabul kriterleri:**
- [ ] Light cycle her 60sn'de ExitProcessor.run_light() çağırıyor.
- [ ] Açık tennis pozisyonu varken SL/TP koşulu sağlanırsa exit gerçekleşiyor (trade_history.jsonl'a exit kaydı düşüyor).

---

#### Stage 6: Equity Snapshot Writes

**Bağlam:**
Dashboard'un Balance/Open P&L/Realized P&L/Peak Balance widget'ları `equity_history.jsonl`'i okuyor. Şu an tennis bu dosyayı yazmıyor.

**Adımlar:**
- [ ] Main bot'un EquityHistoryLogger'ını incele (snapshot signature).
- [ ] Test: `tests/orchestration/test_tennis_equity_snapshot.py`:
  - `test_snapshot_after_heavy_cycle` — heavy sonrası equity_history.jsonl'a yeni satır eklenmiş mi.
  - `test_snapshot_after_exit_cycle` — light sonrası exit varsa snapshot atılıyor mu.
- [ ] Implement: tennis_agent — heavy sonrası ve exit gerçekleştiyse light sonrası equity_logger.log(snapshot) çağır.
- [ ] Run tests → pass.
- [ ] Commit.

**Kabul kriterleri:**
- [ ] tennis-lab/logs/session/equity_history.jsonl her cycle sonrası entry artıyor.
- [ ] Snapshot'ta bankroll + realized_pnl + unrealized_pnl + invested + open_positions doğru.

---

#### Stage 7: State File Isolation Verification

**Bağlam:**
Tennis state ana bottan tamamen ayrı yerde olmalı (worktree dizini doğal izolasyon sağlıyor ama factory dependencies absolute path'lerle bağlanmalı).

**Adımlar:**
- [ ] tennis_factory'da state path'leri config_tennis.yaml'dan oku, absolute path'e çevir (_ROOT anchor):
  - `data_dir`: tennis-lab/data
  - `logs_dir`: tennis-lab/logs
- [ ] tennis_main.py'dan data_dir + logs_dir absolute path olarak run_forever'a geçir.
- [ ] Verification script: `scripts/verify_tennis_isolation.py` — tennis-lab/{logs,data} dosyalarının ana bot ile aynı path'i kullanmadığını kanıtla.
- [ ] Run script → assert passes.
- [ ] Commit.

**Kabul kriterleri:**
- [ ] Tennis cycle ana botun positions.json'ına dokunmuyor.
- [ ] Tennis trade_history ana bot trade_history'sinden ayrı.

---

#### Stage 8: Full Cycle Wiring + Persist

**Bağlam:**
Tüm parçalar bağlandıktan sonra tennis_agent.run_one_cycle akışı şöyle olmalı:

```
HEAVY (30dk):
  1. Load ratings + matches
  2. scanner.scan() → tennis markets
  3. enrich each → EdgeCandidate list
  4. select_best_2_per_event → top candidates
  5. min_edge filtresi (≥%5)
  6. tennis_signal_adapter ile Signal list
  7. entry_processor.process_signals(markets, signals)
  8. equity_snapshot.log()
  9. diagnostic_logger.log_prediction (mevcut diagnostic kaydı korunur)
  10. bot_status.json güncelle (stage="idle")

LIGHT (60sn):
  1. exit_processor.run_light()
  2. Eğer exit gerçekleştiyse equity_snapshot.log()
  3. bot_status.json güncelle (stage="light")
```

**Adımlar:**
- [ ] Test: `tests/orchestration/test_tennis_full_cycle.py`:
  - `test_full_heavy_cycle_e2e` — fake scanner + enricher + entry_processor + equity_logger mock, akış sırası ve idempotency.
  - `test_full_light_cycle_e2e` — fake exit_processor + equity_logger mock.
- [ ] Implement: tennis_agent.run_one_cycle + run_forever revize.
- [ ] Run tests → pass.
- [ ] Commit.

**Kabul kriterleri:**
- [ ] Tüm bağlı bileşenler doğru sırada çağrılıyor.
- [ ] Persistence (positions, trade_history, equity) doğru dizinlere yazıyor.

---

#### Stage 9: End-to-End Smoke Test + Dashboard Verification

**Adımlar:**
- [ ] `python scripts/tennis_main.py --once` — gerçek Polymarket data ile cycle koştur.
- [ ] Beklenti: ≥1 tennis market scan edilir, ≥0 candidate yakalanır (canlı tennis maçı yoksa 0 normal).
- [ ] Force-test: `scripts/inject_fake_tennis_position.py` — sahte bir tennis pozisyonu positions.json'a enjekte et, dashboard'un Active sekmesinde göründüğünü doğrula.
- [ ] Force-test: pozisyonu manuel kapat (exit_processor'a fake exit signal), Exited sekmesine geçmesini doğrula.
- [ ] Dashboard refresh → tüm widget'lar doğru veri gösteriyor mu çek-listesi:
  - [ ] Balance: $500 (initial)
  - [ ] Open P&L: sahte pozisyon varken hesaplanıyor
  - [ ] Realized P&L: sahte exit sonrası güncelleniyor
  - [ ] Locked in Bets: pozisyon size'ı
  - [ ] Peak Balance: max görülen bankroll
  - [ ] Loss Protection gauge: bankroll değişimine tepki
  - [ ] Positions gauge: open count
  - [ ] Branches: closed trade sonrası dolar
  - [ ] Total Equity chart: snapshot'lar grafiğe işliyor
  - [ ] Per Trade PnL: kapanmış trade'ler bar olarak çiziliyor
  - [ ] Trade feed Active: open positions
  - [ ] Trade feed Exited: closed positions
  - [ ] Cycle göstergesi: "Cycle: idle / next in MM:SS"
- [ ] Çıktılarını ekran görüntüleri yerine `scripts/dashboard_audit.py` ile API endpoint'lerden kontrol et (kullanıcı sabah görsel kontrolü kendi yapacak).
- [ ] Commit.

**Kabul kriterleri:**
- [ ] Sahte pozisyon enjekte edilince dashboard'un her widget'ı tepki veriyor.
- [ ] Gerçek cycle çalıştığında pipeline crash etmiyor.

---

#### Stage 10: DECISIONS.md Güncellemesi + Final Commit

**Adımlar:**
- [ ] Ana repo (master branch) DECISIONS.md'ye yeni SPEC entry ekle:
  - **SPEC-O — Tennis Lab Full Paper Trading Wire-Up (2026-05-20)**
  - Karar: Tennis sandbox artık ana botun entry/exit/state machinery'sini paper modda kullanır; edge kaynağı = Glicko + Klaassen-Magnus.
  - Neden: Kullanıcı diagnostic-only yetmediğini söyledi; dashboard widget'larını besleyecek paper trading mantığı zorunlu.
  - Yeni dosyalar: tennis_signal_adapter.py, debug_tennis_markets.py, verify_tennis_isolation.py, dashboard_audit.py, inject_fake_tennis_position.py.
  - Modified: tennis_agent.py (heavy+light cycle), tennis_factory.py (state stores), config_tennis.yaml (sizing+filters), EntryReason enum, EntryProcessor.process_signals.
  - Mitigation: Tüm tennis state tennis-lab/ altında, master state'e dokunulmaz.
  - Sonraki: 4 hafta paper, accuracy ≥%53 ise canlı geçiş.
- [ ] DECISIONS.md ana repo'ya master branch'te commit.
- [ ] tennis-lab worktree'de PLAN-TENNIS-001 entry'sini PLAN.md'den sil (DONE).
- [ ] Final tennis-lab branch summary mesajı: tüm aşamalar yeşil, X test geçti, dashboard çalışıyor.

**Kabul kriterleri:**
- [ ] DECISIONS.md SPEC-O master'da committed.
- [ ] PLAN.md tennis entry'si silindi.
- [ ] Tüm testler geçiyor (`pytest -q` her iki repo'da).

---

**Toplam tahmini iş:**
- 10 aşama, her biri TDD (test→fail→impl→pass→commit).
- ~15-25 test eklenir.
- ~3-5 yeni dosya.
- ~5-8 mevcut dosya modifiye.
- Sıfır main bot dosyası tehlikede (master'a SADECE Stage 10'da DECISIONS.md güncellenir).

**Yürütme:** Subagent-driven development. Her stage için fresh implementer subagent + spec compliance reviewer + code quality reviewer.



