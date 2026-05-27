# Force-Close Stuck Losing Positions — Design

**Date:** 2026-05-27
**Status:** APPROVED (user, 2026-05-27)
**Applies to:** Polymarket Agent 2.0 (main bot), tennis-lab, tennis-paper-lab

---

## Problem

Bazı pozisyonlar `-%90'dan büyük zarara` düştükten sonra paper bot çıkamıyor:

- Mevcut SL kuralı (`strategy/exit/stop_loss.py:36-37`) `current_price <= 0.001` durumunda
  "stale price, WS tick gelmedi" varsayımıyla SL'i bypass ediyor — gerçek -%99 düşüş
  de aynı koşulu tetikliyor.
- `exit_processor.py` "no bids within slippage" sebebiyle satışı reddediyor. Pozisyon
  açıkta kalıyor, retry sayacı sonsuza büyüyor (`exit_retry_count: 71` gözlemlendi).
- Concrete example: `atp-humbert-halys-2026-05-27-first-set-winner-Humbert-vs-Halys`
  pozisyonu entry 0.5668 → current 0.0005, bid 0.01, 71 retry sonra hâlâ açık.
  Set 1 fiilen bitmiş, alıcı yok, gerçek hayatta da satılamaz, ama bot realize
  etmiyor → dashboard'da "açık pozisyon" olarak karışık görüntü.

## Goal

Maç bittikten sonra hâlâ açık olan kayıp pozisyonları **zorla realize et**:
- Eğer bid varsa, bid fiyatından sat (slippage tolerance'ı bypass).
- Bid yoksa, pozisyonu `0` fiyatla realize et (kayıp resmiyleşir).

## Non-Goals (YAGNI)

- Kazançlı pozisyonlar için zorla kapatma — sadece kayıp pozisyonlar.
- Risk/reward asimetrisinin (bimodal SL muafiyeti, TP yapısı) düzeltilmesi — ayrı bir tasarımda.
- Match-level confidence revizyonu — kapsam dışı.

---

## Architecture

5-katmanlı mimariye uygun, üç katmanda eklenti:

| Katman | Değişiklik | Sorumluluk |
|---|---|---|
| **Infrastructure** | `apis/espn_client.py`'a `get_match_status(event_id)` method eklenir | ESPN'den maç durumu çek: `FINAL`, `END_PERIOD`, `IN_PROGRESS`, `NOT_STARTED` |
| **Strategy** | Yeni dosya: `strategy/exit/time_force_close.py` | Saf karar: bir pozisyon için force-close sinyali ver mi vermesin mi |
| **Orchestration** | `exit_processor.py`'a 1 çağrı eklenir (SL/TP/near_resolve sonrası) | Sinyal varsa override satış — slippage tolerance bypass, bid yoksa 0 realize |

Domain'e dokunmaz. Domain yine veri-temelli (`Position`, `MatchState`).

---

## Decision Logic (Hybrid C)

Her exit cycle, her açık pozisyon için sırayla:

1. **ESPN-first kontrol:**
   - `espn_client.get_match_status(event_id)` çağır
   - Sport-specific eşleme (tennis: set bitti mi, basketbol: çeyrek bitti mi, vb.)
   - ESPN net "bu market_type'ın olayı bitti" diyorsa → **sinyal:** `force_close_espn_event_ended`

2. **Time-based fallback (ESPN cevap vermiyorsa):**
   - `now - match_start_iso` hesapla (dakika)
   - Eğer `force_close_timeouts[market_type]`'tan büyükse → **sinyal:** `force_close_time_expired`
   - `market_type` tabloda yoksa `force_close_timeouts.default` kullan

3. **Hiçbir sinyal yoksa:** Normal SL/TP akışına devam et. Force-close devreye girmez.

---

## Force-Close Execution

Sinyal aldıktan sonra `exit_processor`:

1. Mevcut `paper_fill.walk_book_sell` çağırır AMA `max_slippage_pct` parametresi olarak
   **1.0** (yani %100 tolerans) verir. Bu, herhangi bir bid ile fill demek.
2. Eğer hâlâ `REJECTED` ise (bid listesi gerçekten boş):
   - Pozisyonu `current_price=0` ile manuel realize et
   - `exit_reason` = `force_close_no_bids`
   - Realized PnL = `-size_usdc` (tam kayıp)
3. Audit'e yazılır, dashboard günceller.

---

## Config

3 bot'un kendi `config*.yaml` dosyasına eklenir:

```yaml
risk:
  force_close_timeouts:
    # market_type -> match_start'tan kaç dakika sonra zorla kapat
    # Tennis
    tennis_first_set_winner: 60        # set 1 ~30-45 dk, 60 dk güvenli
    tennis_set_handicap: 60
    tennis_first_set_totals: 60
    tennis_match_winner: 200            # bo3 maç ~2-3 saat
    tennis_match_totals: 200
    tennis_set_totals: 200
    # Ana bot (mevcut destekli sporlar)
    nba_quarter_1_winner: 35
    nba_match_winner: 180
    nfl_quarter_1: 45
    nfl_match_winner: 240
    nhl_match_winner: 200
    mlb_match_winner: 240
    wnba_match_winner: 180
    # Fallback
    default: 300
```

**Yeni spor eklenince:**
- ESPN o sporu destekliyorsa → otomatik çalışır (yukarı eşleme ESPN status'a düşer)
- ESPN desteklemiyorsa → bu tabloya 1-2 satır ekle (sport+market_type başına timeout)

---

## Error Handling (ARCH_GUARD Kural 12)

| Durum | Davranış | Katman |
|---|---|---|
| ESPN API down (HTTPError/Timeout) | Logla WARNING, fallback time-based check | Infrastructure |
| ESPN cevap döner ama parse hatası | `None` döner, fallback time-based check | Infrastructure |
| `market_type` tabloda yok | `default: 300` kullan, INFO log | Strategy |
| `match_start_iso` boş veya invalid | Force-close skip (normal SL/TP devam) | Strategy |
| Force-close bid satışı reddedilir | `force_close_no_bids` ile 0 realize | Orchestration |
| Force-close trigger ama sonra pozisyon yok (race) | Skip, INFO log | Orchestration |

Sessiz hata yutma yok. Her başarısız ESPN call WARNING'le loglanır.

---

## Testing (ARCH_GUARD Kural 11)

**Unit tests (Strategy katmanı — zorunlu):**
- `test_time_force_close_espn_says_final_returns_signal`
- `test_time_force_close_espn_says_in_progress_returns_none`
- `test_time_force_close_no_espn_time_expired_returns_signal`
- `test_time_force_close_no_espn_time_not_expired_returns_none`
- `test_time_force_close_missing_match_start_returns_none`
- `test_time_force_close_unknown_market_type_uses_default`

**Unit tests (Infrastructure — ESPN client method):**
- `test_get_match_status_tennis_set_ended`
- `test_get_match_status_match_final`
- `test_get_match_status_in_progress`
- `test_get_match_status_api_down_returns_none`

**Integration test (Orchestration — exit_processor):**
- `test_exit_processor_force_close_overrides_slippage`
- `test_exit_processor_force_close_no_bids_realizes_zero`

---

## Rollout

3 bot'a uygulanır:

1. **Polymarket Agent 2.0** (ana bot)
2. **tennis-lab**
3. **tennis-paper-lab**

Üçü de aynı 5-katmanlı yapıya sahip, kod tekrarı kaçınılmaz değil ama her bot kendi
config'inde timeout tablosuna sahip olacak. ESPN client zaten 3 projede de var.

**Sıra:**
1. Önce tennis-paper-lab'da uygula + test et (paper mode, risksiz)
2. Tennis-lab'a kopyala (paper, gerçek olmayan)
3. Ana bot'a kopyala (dry_run, hâlâ paper)

---

## Open Questions

- ESPN'in `STATUS_END_PERIOD` event'i tenis için "set bitti" anlamında mı yoksa
  başka anlam taşıyor mu? İlk implementasyonda doğrulanmalı (espn_client testi).
- Polymarket'in market_type isimleri (örn. `tennis_first_set_winner`) config tablosundaki
  isimle birebir aynı mı, yoksa normalization gerek mi? Gamma client'ı incelenmeli.

Bu sorular implementation planı yazılırken cevaplanır.

---

## Acceptance Criteria

- [ ] 3 bot'ta `force_close_timeouts` config'i mevcut
- [ ] `time_force_close.check()` saf fonksiyon, tüm edge case'ler unit testli
- [ ] ESPN client `get_match_status` method'u mevcut, mock'lı testli
- [ ] `exit_processor` force-close akışını uygular, slippage tolerance bypass eder
- [ ] Bid yoksa 0 ile realize eder (audit'e doğru reason yazar)
- [ ] Yeni `exit_reason` değerleri (`force_close_espn_event_ended`,
      `force_close_time_expired`, `force_close_no_bids`) dashboard'da görünür
- [ ] Pytest -q tümü geçer
- [ ] Humbert-halys benzeri test pozisyonu üzerinde davranış doğrulandı (manuel test)
