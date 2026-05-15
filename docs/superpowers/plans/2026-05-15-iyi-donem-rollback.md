# İyi Dönem Strateji Rollback — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bot 2.0'ı peak performans (18 Apr +$326) strateji konfigürasyonuna geri al, dead code (NBA spread, cricket, soccer 3-way, SPEC-K eklemeleri) temizle, Hockey için NHL ML-only istisnası ekle. Mimari (ARCH_GUARD/lean refactor/reboot/dashboard) dokunulmaz.

**Architecture:** Selective rollback — `config.yaml` peak değerlerine + zararlı modülleri (a_conf_hold tek-SL pattern, dead-code SPEC'ler) tamamen sil. `monitor.py` dispatch zinciri sadeleşir, tüm pozisyonlar graduated_sl + flat SL ile yönetilir (eski projede başarılı pattern). Hockey kısıtı sport_rules üzerinden flag olarak girer.

**Tech Stack:** Python 3.12, pytest, mevcut ARCH_GUARD 5-katman mimari, JSONL atomic write, git per-task commit

**Spec:** [`docs/superpowers/specs/2026-05-15-iyi-donem-rollback-design.md`](../specs/2026-05-15-iyi-donem-rollback-design.md)

---

## File Structure

### Silinecek dosyalar (dead code temizliği)

```
src/strategy/exit/a_conf_hold.py                      → SİL
src/strategy/exit/nba_spread_exit.py                  → SİL
src/orchestration/cricket_score_builder.py            → SİL (varsa)
src/orchestration/soccer_score_builder.py             → SİL (varsa)
src/infrastructure/apis/cricket_client.py             → SİL (varsa)
src/strategy/entry/three_way.py                       → SİL (varsa)
src/domain/matching/event_grouper.py                  → SİL
src/domain/matching/three_way_title.py                → SİL
src/strategy/exit/soccer_score_exit.py                → SİL (varsa)
src/strategy/exit/cricket_score_exit.py               → SİL (varsa)
src/strategy/exit/baseball_score_exit.py              → SİL (SPEC-014, Faz 2'ye kadar bırakılabilir — Task 8'de ele alınır)
tests/unit/strategy/exit/test_a_conf_hold.py          → SİL
tests/unit/strategy/exit/test_nba_spread_exit.py      → SİL
tests/unit/strategy/entry/test_three_way.py           → SİL (varsa)
tests/unit/orchestration/test_event_grouper.py        → SİL (varsa)
tests/unit/domain/matching/test_three_way_title.py    → SİL (varsa)
```

### Modify edilecek dosyalar

```
config.yaml                                  → sport_tags + edge + sizing + scale_out 19 Apr değerlerine
src/config/settings.py                       → kaldırılan parametre alanları temizlenir
src/config/sport_rules.py                    → NHL için "moneyline_only: true" flag eklenir
src/strategy/exit/monitor.py                 → a_conf_hold import + dispatch satırları (251-260) silinir; "else" bloğu (262-299) tüm pozisyonlara uygulanır (if'siz)
src/strategy/exit/_nba_dispatch.py           → SPREAD dalı silinir, totals dispatch korunur
src/strategy/enrichment/odds_enricher.py     → SPEC-K spread/totals enrichment path silinir, h2h korunur
src/orchestration/factory.py                 → cricket/soccer/three_way DI yapısı temizlenir
src/orchestration/scanner.py                 → NHL moneyline_only filtresi sport_rules üzerinden uygulanır
src/orchestration/score_enricher.py          → cricket/soccer dispatch silinir (varsa)
src/models/market.py                         → three_way ilişkili alan/yorum varsa temizlenir
```

### Korunan (dokunulmaz) dosyalar

```
src/strategy/exit/near_resolve.py
src/strategy/exit/graduated_sl.py
src/strategy/exit/stop_loss.py
src/strategy/exit/scale_out.py
src/strategy/exit/nba_totals_exit.py
src/strategy/exit/favored.py
src/strategy/exit/_nba_score_mapper.py
src/orchestration/agent.py / reboot.py / process_lock.py / startup.py
ARCHITECTURE_GUARD.md / CLAUDE.md / TDD.md / PRD.md
```

---

## Pre-flight Checklist

Tüm task'lardan ÖNCE bir kez yapılır:

- [ ] **Pre-1: ARCH_GUARD oku** (dosya boyutu limiti, katman kuralları)

Read: `ARCHITECTURE_GUARD.md`
Expected: 15 kural + 8 anti-pattern tablosu bilinir hale gelir

- [ ] **Pre-2: Mevcut test durumunu doğrula (baseline PASS)**

Run: `pytest -q`
Expected: tüm testler PASS — bilinen başarısız test varsa not düşülür, plan sonu beklenen sonuç bu baseline değiştirilmiş hali olur

- [ ] **Pre-3: Git working tree temiz**

Run: `git status`
Expected: "nothing to commit, working tree clean" — değilse stash veya commit

- [ ] **Pre-4: State yedeği al (logs/audit zaten arşivlenmiş ama ek güvenlik)**

Run:
```bash
DATE=$(date +%Y%m%d_%H%M%S)
cp -r logs/audit "logs/_pre_rollback_backup_${DATE}"
cp data/positions.json "data/positions.pre_rollback_${DATE}.bak"
```
Expected: backup dosyaları oluşur, hiçbir veri kaybı riski yok

- [ ] **Pre-5: Bot durduruldu mu doğrula**

Run: `tasklist | grep -i python || echo "no python"`
Expected: bot çalışıyorsa `python scripts/reboot.py` ile durdur (state için Task 9 öncesi gerekli, kod değişiklikleri için zorunlu değil)

---

## Task 1: Config Rollback (config.yaml + settings.py)

**Hedef:** `config.yaml` 19 Apr peak değerlerine geri alınır. `settings.py` schema'sı uyarlanır.

**Files:**
- Modify: `config.yaml`
- Modify: `src/config/settings.py`
- Test: `tests/unit/config/test_settings.py`

- [ ] **Step 1: 19 Apr 14:01 commit'inden referans config'i al**

Run:
```bash
git show 98e8dc9:config.yaml > /tmp/iyi_donem_config.yaml
diff /tmp/iyi_donem_config.yaml config.yaml | head -120
```
Expected: 4 alan grubunda fark görülür (sport_tags, confidence_multipliers, sizing, scale_out)

- [ ] **Step 2: config.yaml `allowed_sport_tags` rollback**

Modify `config.yaml` — `scanner.allowed_sport_tags` listesi şu hale gelir (Hockey için NHL hariç tüm alt ligler hariç tutulur):

```yaml
scanner:
  # ...
  allowed_sport_tags:
    # Baseball
    - mlb
    - milb
    - npb
    - kbo
    - baseball
    # Basketball
    - nba
    - wnba
    - ncaab
    - wncaab
    - cbb
    - euroleague
    - nbl
    # Hockey — SADECE NHL (kullanıcı kararı, AHL/Liiga/SHL/Mestis/Allsvenskan EKLENMEZ)
    - nhl
    # American Football
    - ncaaf
    - cfl
    - ufl
    # Tennis
    - tennis
    - "atp*"
    - "wta*"
    # Combat sports
    - mma
    - ufc
    - boxing
    # Golf
    - "lpga*"
    - "liv*"
    - "pga*"
```

- [ ] **Step 3: config.yaml `edge.confidence_multipliers` rollback**

Modify `config.yaml` — `edge` bloğu:

```yaml
edge:
  min_edge: 0.06
  confidence_multipliers:
    A: 1.00    # 19 Apr peak değer (önceki 1.25)
    B: 1.00
  # mevcut diğer alanlar dokunulmaz
```

- [ ] **Step 4: config.yaml `risk.sizing` rollback**

Modify `config.yaml` — `risk` bloğu:

```yaml
risk:
  initial_bankroll: 1000
  max_single_bet_usdc: 50
  max_bet_pct: 0.05                # disabled (1.0) yerine peak %5
  confidence_bet_pct:
    A: 0.05
    B: 0.04
  exposure_cap_pct: 0.30
  # mevcut diğer alanlar dokunulmaz
```

- [ ] **Step 5: config.yaml `scale_out` tier'lar rollback**

Modify `config.yaml` — `scale_out` bloğu (yorumda 19 Apr orijinal değerlerine işaret):

```yaml
scale_out:
  tiers:
    - threshold: 0.25    # 19 Apr — agresif erken kâr kilitle
      sell_pct: 0.40
    - threshold: 0.50    # 19 Apr orijinal
      sell_pct: 0.50
  # min_scale_out_realized_usdc parametresi KALDIRILIR (Task 1.6'da settings.py'da temizlenir)
```

- [ ] **Step 6: settings.py — kaldırılan parametre alanlarını temizle**

Modify `src/config/settings.py`:
- `scale_out.min_scale_out_realized_usdc` alanını **sil** (varsa)
- `risk.max_bet_pct` default 1.0 → 0.05 yap
- `risk.confidence_bet_pct` Pydantic alanını **ekle** (yoksa)
- Eğer `agent.max_positions_per_event` 2 default ise **dokunulmaz** (Faz 2'ye bırakılır)
- Eğer `scanner.max_post_start_hours` varsa **dokunulmaz** (Faz 2'ye bırakılır)

- [ ] **Step 7: pytest çalıştır (config + settings testleri)**

Run: `pytest -q tests/unit/config/ -v`
Expected: PASS — eğer min_scale_out_realized_usdc'ye bağlı test varsa o silinir (Task 1.6 kapsamı içinde)

- [ ] **Step 8: Tam test suite (ARCH_GUARD doğrulama)**

Run: `pytest -q`
Expected: PASS (a_conf_hold/cricket/soccer kısımları henüz dokunulmadı — Task 2-7'de düşecekler)

- [ ] **Step 9: Commit**

```bash
git add config.yaml src/config/settings.py
git commit -m "feat(rollback): config 19 Apr peak — sport_tags + edge + sizing + scale_out

- allowed_sport_tags: 25 spor geri açık (Hockey için sadece NHL)
- confidence_multipliers.A: 1.25 → 1.00 (eşik %6)
- max_bet_pct: 1.0 → 0.05; confidence_bet_pct {A:0.05, B:0.04}
- scale_out tier'lar 19 Apr orijinal (%25/%40 + %50/%50)
- min_scale_out_realized_usdc kaldırıldı

Faz 1/10 (iyi-donem-rollback spec)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: A-conf Hold Mantığını Kaldır

**Hedef:** `a_conf_hold.py` silinir, `monitor.py` dispatch düzeltilir — tüm pozisyonlar graduated_sl + flat SL ile yönetilir.

**Files:**
- Delete: `src/strategy/exit/a_conf_hold.py`
- Delete: `tests/unit/strategy/exit/test_a_conf_hold.py`
- Modify: `src/strategy/exit/monitor.py` (satır 251-260 sil, 262-299 if'siz çalışsın)

- [ ] **Step 1: Mevcut monitor.py'da a_conf_hold import + dispatch satırlarını lokalize et**

Read: `src/strategy/exit/monitor.py`
Bul:
- `from src.strategy.exit import ... a_conf_hold ...` import satırı (~satır 23)
- `a_hold = a_conf_hold.is_a_conf_hold(pos) or pos.favored` (satır 253)
- `if a_hold: ... market_flip_exit ...` bloğu (satır 254-260)
- `else:` bloğu (satır 261-299) — bu blok "if'siz" olarak kalmalı

- [ ] **Step 2: monitor.py'dan a_conf_hold import'unu çıkar**

Edit `src/strategy/exit/monitor.py`:
```python
# ÖNCESİ:
from src.strategy.exit import a_conf_hold, favored, graduated_sl, near_resolve, scale_out, stop_loss

# SONRASI:
from src.strategy.exit import favored, graduated_sl, near_resolve, scale_out, stop_loss
```

- [ ] **Step 3: monitor.py satır 251-260 (a_conf_hold dispatch) sil + else bloğunu if'siz çalıştır**

Edit `src/strategy/exit/monitor.py`. Eski mantık:
```python
    # 3. A-conf hold dalı — flat SL + graduated SL'den MUAF (TDD §6.9)
    # Sadece near-resolve (yukarıda) + scale-out (yukarıda) + market-flip aktif.
    a_hold = a_conf_hold.is_a_conf_hold(pos) or pos.favored
    if a_hold:
        if elapsed_pct >= 0 and a_conf_hold.market_flip_exit(pos, elapsed_pct):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.MARKET_FLIP, detail="eff < 0.50 at elapsed >= 0.85"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
    else:
        # 4. Non-A-hold flat stop-loss
        if stop_loss.check(pos):
            ...
        # 5. Non-A-hold: graduated SL + never-in-profit + hold-revocation + ultra-low
        if elapsed_pct >= 0:
            ...
```

Yeni mantık (a_conf_hold dalı tamamen kaldırılır, else bloğunun içeriği TÜM pozisyonlara uygulanır):

```python
    # 3. Flat stop-loss (tüm pozisyonlar için aktif — 19 Apr peak pattern)
    if stop_loss.check(pos):
        return MonitorResult(
            exit_signal=ExitSignal(reason=ExitReason.STOP_LOSS, detail="flat SL hit"),
            fav_transition=_fav_transition(pos),
            elapsed_pct=elapsed_pct,
        )
    # 4. Graduated SL + never-in-profit + hold-revocation + ultra-low (elapsed >= 0)
    if elapsed_pct >= 0:
        if _ultra_low_guard_exit(pos, elapsed_pct):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.ULTRA_LOW_GUARD, detail="ultra-low dead"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
        exit_grad, max_loss = graduated_sl.check(pos, elapsed_pct, pos.entry_price, score_info)
        if exit_grad:
            return MonitorResult(
                exit_signal=ExitSignal(
                    reason=ExitReason.GRADUATED_SL,
                    detail=f"pnl < -{max_loss:.1%} (elapsed {elapsed_pct:.0%})",
                ),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
        if _never_in_profit_exit(pos, elapsed_pct, score_info):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.NEVER_IN_PROFIT, detail="never profited + late + dropped"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
        if _hold_revocation_exit(pos, elapsed_pct, score_info):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.HOLD_REVOKED, detail="hold revoked + exit"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
```

NOT: `ExitReason.MARKET_FLIP` enum değeri **enum'da kalır** (Faz 2'de değerlendirilir, ama dispatch silinir). `a_conf_hold.market_flip_exit` çağrısı tamamen kaldırılır — bot artık geç-tetik market_flip'i kullanmaz.

- [ ] **Step 4: a_conf_hold.py ve test dosyasını sil**

Run:
```bash
rm src/strategy/exit/a_conf_hold.py
rm tests/unit/strategy/exit/test_a_conf_hold.py
```

- [ ] **Step 5: monitor.py'a `near_resolve_threshold_cents` ve `near_resolve_guard_min` parametreleri yerinde mi kontrol et**

Read: `src/strategy/exit/monitor.py` — `evaluate()` fonksiyonu signature'ı dokunulmadığından emin ol (a_conf_hold içindeki `DEFAULT_MIN_ENTRY_PRICE = 0.60` kullanılmıyor artık → öteki çağrılar yoksa OK).

Run: `grep -rn "DEFAULT_MIN_ENTRY_PRICE\|is_a_conf_hold\|market_flip_exit\|a_conf_hold" src/ tests/ 2>&1`
Expected: hiç eşleşme yok (silinen referanslar tamamen temizlenmiş)

- [ ] **Step 6: pytest çalıştır**

Run: `pytest -q tests/unit/strategy/exit/`
Expected: a_conf_hold test'leri yok (silindi); monitor.py test'leri yeni mantığa göre PASS. Eğer test'lerde a_conf_hold dispatch assertion'ı varsa o adapte edilir (örn. A-conf pos için graduated_sl tetiklenmeli — beklenen davranış)

- [ ] **Step 7: Tam test suite**

Run: `pytest -q`
Expected: PASS (hâlâ cricket/soccer kalıntıları olabilir, sonraki task'larda silinecek)

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(rollback): a_conf_hold dalı kaldırıldı — graduated_sl + flat SL tüm pozisyonlara

A-conf hold mantığı tek SL = market_flip bağımlı, post-peak -\$310 katil oldu.
Veri: 14 trade hepsi kayıp (0W/14L). 19 Apr peak'te eski projedeki çoklu SL
pattern (graduated + flat + a_conf_market_flip + catastrophic) net pozitif.

Kaldırılan: a_conf_hold.py + test + monitor.py dispatch (satır 251-260).
Korunan: near_resolve (kâr motoru +\$482), scale_out, graduated_sl, stop_loss.
Eklenen: graduated_sl + flat SL artık TÜM pozisyonlara uygulanır.

Faz 2/10 (iyi-donem-rollback spec)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: NBA Spread Exit Silme (Dead Code)

**Hedef:** `nba_spread_exit.py` ve dispatch dalı silinir. NBA totals exit modülü dokunulmaz.

**Files:**
- Delete: `src/strategy/exit/nba_spread_exit.py`
- Delete: `tests/unit/strategy/exit/test_nba_spread_exit.py`
- Modify: `src/strategy/exit/_nba_dispatch.py` (spread dal silinir)

- [ ] **Step 1: nba_spread_exit import + dispatch satırlarını lokalize et**

Read: `src/strategy/exit/_nba_dispatch.py`
Bul:
- `from src.strategy.exit import nba_spread_exit` (veya benzer import)
- `if pos.sports_market_type == SportsMarketType.SPREADS: return nba_spread_exit.check(...)` benzeri dispatch
- `from src.strategy.exit import nba_totals_exit` ve totals dispatch — **dokunulmaz**

- [ ] **Step 2: _nba_dispatch.py'dan spread dispatch + import kaldır**

Edit `src/strategy/exit/_nba_dispatch.py`. Spread dispatch dalı silinir, totals dispatch korunur. Örnek:

```python
# ÖNCESİ:
from src.strategy.exit import nba_spread_exit, nba_totals_exit

def check_nba_exit(pos, score_info, _elapsed_pct, basketball_exit_cfg):
    if pos.sports_market_type == SportsMarketType.SPREADS:
        return nba_spread_exit.check(pos, score_info, basketball_exit_cfg)
    if pos.sports_market_type == SportsMarketType.TOTALS:
        return nba_totals_exit.check(pos, score_info, basketball_exit_cfg)
    return None

# SONRASI:
from src.strategy.exit import nba_totals_exit

def check_nba_exit(pos, score_info, _elapsed_pct, basketball_exit_cfg):
    if pos.sports_market_type == SportsMarketType.TOTALS:
        return nba_totals_exit.check(pos, score_info, basketball_exit_cfg)
    return None
```

- [ ] **Step 3: nba_spread_exit.py + test dosyasını sil**

Run:
```bash
rm src/strategy/exit/nba_spread_exit.py
rm -f tests/unit/strategy/exit/test_nba_spread_exit.py
```

- [ ] **Step 4: monitor.py'da SPEC-J basketball dispatch hâlâ totals için aktif**

Read: `src/strategy/exit/monitor.py` satır 227-249 (Basketball spread/totals dispatch)
Doğrula: dispatch hâlâ `sports_market_type in (SportsMarketType.SPREADS, SportsMarketType.TOTALS)` kontrolü yapıyor.

NOT: Eğer SPREADS değeri artık desteklenmiyorsa kontrolü `(SportsMarketType.TOTALS,)` tuple'ına daraltabilirsin — DRY için her durumda `check_nba_exit` dispatch'in kendisi None döndüğü için zarar yok, ama explicit olarak daraltmak temiz olur.

Edit `src/strategy/exit/monitor.py` satır ~227-232:

```python
# ÖNCESİ:
    if (
        sport_tag_lc in BASKETBALL_TAGS
        and pos.sports_market_type in (SportsMarketType.SPREADS, SportsMarketType.TOTALS)
    ):

# SONRASI:
    if (
        sport_tag_lc in BASKETBALL_TAGS
        and pos.sports_market_type == SportsMarketType.TOTALS
    ):
```

- [ ] **Step 5: Spread referans aramaları**

Run: `grep -rn "nba_spread_exit\|SPREADS_EXIT\|NbaSpreadExit" src/ tests/ 2>&1`
Expected: hiç eşleşme yok

- [ ] **Step 6: pytest çalıştır**

Run: `pytest -q tests/unit/strategy/exit/`
Expected: PASS — nba_totals_exit testleri etkilenmez

- [ ] **Step 7: Tam test suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(rollback): NBA spread exit modülü silindi (0 trade dead code)

Veri: 112 trade taramasında NBA spread için 0 trade. Modül 25 Apr'da eklendi
ama hiç kullanılmadı. NBA totals exit (+\$21 kanıt) DOKUNULMADI.

Silindi: nba_spread_exit.py + test + _nba_dispatch spread dalı.
monitor.py dispatch SportsMarketType.TOTALS'a daraltıldı (DRY).

Faz 3/10 (iyi-donem-rollback spec)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: SPEC-K Spread/Totals Enrichment Temizliği

**Hedef:** `odds_enricher.py` içindeki SPEC-K spread/totals enrichment path silinir. h2h enrichment (peak'te aktifti) dokunulmaz.

**Files:**
- Modify: `src/strategy/enrichment/odds_enricher.py`
- Modify: `src/strategy/enrichment/__init__.py` (varsa public API güncellemesi)
- Test: `tests/unit/strategy/enrichment/test_odds_enricher.py`

- [ ] **Step 1: odds_enricher.py'da SPEC-K kısmını lokalize et**

Read: `src/strategy/enrichment/odds_enricher.py` (commit `b730810` ile referans karşılaştır)

Run: `git show 6fbe3cd:src/strategy/enrichment/odds_enricher.py > /tmp/odds_enricher_pre_specK.py`
Run: `diff /tmp/odds_enricher_pre_specK.py src/strategy/enrichment/odds_enricher.py | head -100`

Aranan: spread/totals enrichment path'leri (SPEC-K 10 May commit'leri ile gelmiş)

- [ ] **Step 2: odds_enricher'dan spread/totals enrichment kodu kaldır**

Edit `src/strategy/enrichment/odds_enricher.py`:
- `enrich_market` veya benzeri fonksiyonda `markets="h2h,spreads,totals"` parametresi → sadece `"h2h"` olur
- `_parse_spreads`, `_parse_totals`, spread_line/total_line ekleyen kod blokları **silinir**
- `EnrichResult`'a spread/totals metadata ekleyen alanlar **silinir** (eğer Pydantic alanı varsa)
- vig_bounds için ayrı dosya açıldıysa (`_vig_bounds.py` gibi) ihtiyaç yoksa SİL — yoksa dokunma

- [ ] **Step 3: EnrichResult model temizliği**

Read: `src/strategy/enrichment/result.py` veya `EnrichResult` tanımının olduğu dosya
Sil: `spread_line`, `total_line`, `total_side`, `spread_team` benzeri alanlar (SPEC-K eklemesi)

- [ ] **Step 4: entry_processor wiring temizliği**

Read: `src/orchestration/entry_processor.py`
Bul: `position.spread_line = enrich_result.spread_line` benzeri SPEC-K wiring satırları → SİL
Position modelinde `spread_line` alanı varsa Task 5 kapsamında değerlendirilir (market.py / position.py)

- [ ] **Step 5: SPEC-K test'lerini temizle**

Run: `grep -rn "spread_line\|total_line\|total_side\|spreads.*totals\|h2h,spreads" tests/ 2>&1`
Edit: SPEC-K behavior test'eden test'leri **sil** (yalnızca enrichment, dispatch değil). h2h test'leri korunur.

- [ ] **Step 6: pytest çalıştır**

Run: `pytest -q tests/unit/strategy/enrichment/`
Expected: h2h enrichment test'leri PASS; spread/totals test'leri yok (silindi)

- [ ] **Step 7: Tam test suite**

Run: `pytest -q`
Expected: PASS — eğer entry_processor / position.py'da spread_line referansı kaldıysa o adımlar Task 5'te ele alınır

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(rollback): SPEC-K bookmaker spread/totals enrichment temizlendi

SPEC-K 10 May'da eklendi, peak'te yoktu. NBA totals trade'leri h2h enrichment
ile zaten çalışıyor (+\$21 kanıt). Spread enrichment için 0 trade üretildi.

Silindi: odds_enricher spread/totals path + EnrichResult metadata alanları
+ entry_processor SPEC-K wiring + SPEC-K test'leri.
Korunan: h2h enrichment (peak'te aktifti, +\$482 near_resolve kâr motoru bunu kullanır).

Faz 4/10 (iyi-donem-rollback spec)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: SPEC-011 Cricket Cluster Silme (Dead Code)

**Hedef:** Cricket-ilgili tüm modüller silinir (0 trade dead code).

**Files:**
- Delete (varsa): `src/infrastructure/apis/cricket_client.py`
- Delete (varsa): `src/orchestration/cricket_score_builder.py`
- Delete (varsa): `src/strategy/exit/cricket_score_exit.py`
- Modify: `src/orchestration/score_enricher.py` (cricket dispatch sil)
- Modify: `src/orchestration/factory.py` (cricket DI sil)
- Modify: `src/config/sport_rules.py` (cricket lig'leri sil)
- Modify: `src/config/_sport_aliases.py` (cricket aliases sil)
- Modify: `src/domain/matching/sport_classifier.py` (cricket sport_key sil)

- [ ] **Step 1: Cricket referanslarını tara**

Run: `grep -rln "cricket\|cric_\|CricketAPI\|CricAPI" src/ tests/ 2>&1`
Expected: aday dosya listesi

- [ ] **Step 2: cricket modüllerini sil**

Run:
```bash
rm -f src/infrastructure/apis/cricket_client.py
rm -f src/orchestration/cricket_score_builder.py
rm -f src/strategy/exit/cricket_score_exit.py
rm -f tests/unit/infrastructure/apis/test_cricket_client.py
rm -f tests/unit/orchestration/test_cricket_score_builder.py
rm -f tests/unit/strategy/exit/test_cricket_score_exit.py
rm -f tests/integration/test_cricket_*.py
```

- [ ] **Step 3: factory.py'dan cricket DI temizle**

Edit `src/orchestration/factory.py`:
- `from src.infrastructure.apis.cricket_client import CricketAPIClient` import sil
- `cricket_client = CricketAPIClient(...)` instantiation sil
- `cricket_score_builder` parametresi olan DI satırları sil
- AgentDeps modeline `cricket_client` veya `cricket_builder` alanı varsa SİL

- [ ] **Step 4: score_enricher.py'dan cricket dispatch temizle**

Edit `src/orchestration/score_enricher.py`:
- Cricket için `if sport_tag in CRICKET_TAGS:` benzeri dispatch sil
- Cricket import'larını sil

- [ ] **Step 5: monitor.py'dan cricket exit dispatch kontrol et**

Read: `src/strategy/exit/monitor.py`
Bul: cricket için ayrı bir branch varsa (örn. `if sport_tag in CRICKET_TAGS: return cricket_score_exit.check(...)`) → SİL

- [ ] **Step 6: sport_rules.py'dan cricket sport tag'leri sil**

Edit `src/config/sport_rules.py`:
- `"cricket"`, `"ipl"`, `"odi"`, `"t20"` vb. cricket lig'leri sil
- CRICKET_TAGS sabiti varsa SİL

- [ ] **Step 7: _sport_aliases.py'dan cricket aliases sil**

Edit `src/config/_sport_aliases.py`:
- Cricket sport_key aliases (`cricket_*` mapping) sil

- [ ] **Step 8: domain/matching'den cricket'i temizle**

Run: `grep -rln "cricket" src/domain/ 2>&1`
Edit: bulunan dosyalardan cricket referanslarını sil (genelde sport_classifier.py + matching helpers)

- [ ] **Step 9: dashboard cricket ikonunu sil**

Edit `src/presentation/dashboard/static/js/icons.js`:
- Cricket sport icon entry'sini sil (sport listesinden)

- [ ] **Step 10: Cricket referans son tarama**

Run: `grep -rn "cricket\|CricketAPI" src/ tests/ 2>&1 | grep -v ".bak\|__pycache__"`
Expected: hiç eşleşme yok

- [ ] **Step 11: pytest çalıştır**

Run: `pytest -q`
Expected: PASS (cricket test'leri silindi, hiçbir import error olmamalı)

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat(rollback): SPEC-011 cricket cluster tamamen silindi (0 trade dead code)

Peak'te yoktu (19 Apr 18:40 eklendi). Veri: 112 trade taramasında 0 cricket
trade. ARCH_GUARD Kural 11 (test zorunluluğu) ihlal etmemek için dead code
tutmaktansa tamamen kaldırıldı.

Silindi: cricket_client + cricket_score_builder + cricket_score_exit + tüm
test'ler + factory DI + score_enricher dispatch + sport_rules cricket lig'leri
+ sport_aliases + sport_classifier + dashboard cricket ikonu.

Faz 5/10 (iyi-donem-rollback spec)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: SPEC-015 Soccer 3-way Cluster Silme

**Hedef:** Soccer 3-way modülleri silinir (0 trade dead code).

**Files:**
- Delete (varsa): `src/strategy/entry/three_way.py`
- Delete (varsa): `src/strategy/exit/soccer_score_exit.py`
- Delete (varsa): `src/orchestration/soccer_score_builder.py`
- Delete (varsa): `src/orchestration/event_grouper.py`
- Delete (varsa): `src/domain/matching/event_grouper.py`
- Delete (varsa): `src/domain/matching/three_way_title.py`
- Modify: `src/orchestration/factory.py` (three_way DI sil)
- Modify: `src/strategy/entry/gate.py` (three_way dispatch sil)
- Modify: `src/orchestration/scanner.py` (3-way filter sil)

- [ ] **Step 1: Soccer 3-way referanslarını tara**

Run: `grep -rln "three_way\|3.way\|soccer_score\|event_grouper\|EventGrouper\|3way" src/ tests/ 2>&1`

- [ ] **Step 2: 3-way ve soccer modüllerini sil**

Run:
```bash
rm -f src/strategy/entry/three_way.py
rm -f src/strategy/exit/soccer_score_exit.py
rm -f src/orchestration/soccer_score_builder.py
rm -f src/orchestration/event_grouper.py
rm -f src/domain/matching/event_grouper.py
rm -f src/domain/matching/three_way_title.py
rm -f tests/unit/strategy/entry/test_three_way.py
rm -f tests/unit/strategy/exit/test_soccer_score_exit.py
rm -f tests/unit/orchestration/test_event_grouper.py
rm -f tests/unit/domain/matching/test_event_grouper.py
rm -f tests/unit/domain/matching/test_three_way_title.py
```

- [ ] **Step 3: gate.py'dan 3-way dispatch temizle**

Edit `src/strategy/entry/gate.py`:
- `from src.strategy.entry import three_way` import sil
- `if is_3way_market: return three_way.evaluate(...)` dispatch dalı sil

- [ ] **Step 4: scanner.py'dan 3-way filter temizle**

Edit `src/orchestration/scanner.py`:
- `_3way_sum_filter` veya benzeri fonksiyonları sil
- 3-way sum kontrolü dispatch sil

- [ ] **Step 5: factory.py'dan event_grouper DI temizle**

Edit `src/orchestration/factory.py`:
- `event_grouper` instantiation + AgentDeps alanı sil
- `EventGrouper` import sil

- [ ] **Step 6: score_enricher.py'dan soccer dispatch temizle**

Edit `src/orchestration/score_enricher.py`:
- Soccer minute/regulation_state parse dispatch sil (SPEC-015 Task 2 ekleme idi)

- [ ] **Step 7: sport_rules.py'dan soccer lig'leri sil**

Edit `src/config/sport_rules.py`:
- 60+ soccer lig (epl, ucl, mls vs) — Tüm "soccer" tag'lı entry'leri sil
- SOCCER_TAGS sabiti varsa sil

- [ ] **Step 8: market.py / position.py'dan 3-way alanları temizle**

Read: `src/models/market.py` + `src/models/position.py`
Bul: `outcomes` (3-element list), `draw_price`, `is_3way` alanları
SİL (3-way modelleri artık desteklenmiyor)

- [ ] **Step 9: dashboard soccer ikonu sil**

Edit `src/presentation/dashboard/static/js/icons.js`:
- Soccer sport entry'sini sil

- [ ] **Step 10: 3-way referans son tarama**

Run: `grep -rn "three_way\|EventGrouper\|soccer_score" src/ tests/ 2>&1 | grep -v "__pycache__"`
Expected: hiç eşleşme yok

- [ ] **Step 11: pytest çalıştır**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat(rollback): SPEC-015 soccer 3-way cluster silindi (0 trade dead code)

Peak'te yoktu (20 Apr eklendi). Veri: 112 trade taramasında 0 soccer 3-way
trade. ARCH_GUARD Kural 4 (god object) için three_way entry + event_grouper
+ soccer_score_exit + tüm 3-way model alanları tamamen kaldırıldı.

Silindi: three_way.py + soccer_score_exit + event_grouper + three_way_title
+ tüm test'ler + factory DI + gate dispatch + scanner 3-way filter
+ sport_rules soccer lig'leri + dashboard soccer ikonu.

Faz 6/10 (iyi-donem-rollback spec)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: SPEC-014 Baseball Score Exit Değerlendirmesi

**Hedef:** Baseball score exit modülü Faz 2'ye ertelenir (baseball spor durumu config rollback ile değişti, modülün etkisi 7 günlük gözlem sonrası değerlendirilir).

**Files:** Bu task'ta dosya değişikliği YOK — sadece doğrulama.

- [ ] **Step 1: Baseball spor aktif mi doğrula**

Read: `config.yaml` (Task 1 sonrası)
Bul: `allowed_sport_tags` listesinde `mlb`, `milb`, `npb`, `kbo`, `baseball` var mı

Expected: var (Task 1 Step 2'de eklendi)

- [ ] **Step 2: baseball_score_exit.py mevcut mu kontrol et**

Run: `ls src/strategy/exit/baseball_score_exit.py 2>&1`
Expected: dosya var (Faz 1'de silinmedi, Faz 2'ye bırakıldı)

- [ ] **Step 3: monitor.py'da baseball dispatch hâlâ aktif mi**

Read: `src/strategy/exit/monitor.py`
Bul: `if sport_tag in BASEBALL_TAGS: return baseball_score_exit.check(...)` benzeri dispatch
Expected: dispatch hâlâ var (Faz 2'ye bırakıldı)

- [ ] **Step 4: Faz 2 TODO ekle**

Edit `TODO.md`:
```markdown
### TODO-FAZ2-001: SPEC-014 baseball_score_exit değerlendirmesi
- **Durum**: DEFERRED
- **Sebep**: Peak haftası verisi yok, Mayıs'ta baseball net -$46. Faz 1 rollback sonrası 7 gün gözlem yapılır. Eğer baseball moneyline pozitif gidiyorsa SPEC-014 modülü tutulur; aksi halde sport kapatılır veya modül kaldırılır.
- **Önkoşul**: Faz 1 rollback tamamlanır, bot 7 gün çalışır, dashboard veri toplanır.
```

- [ ] **Step 5: Commit**

```bash
git add TODO.md
git commit -m "docs(rollback): SPEC-014 baseball_score_exit Faz 2'ye ertelendi

Veri: Mayıs'ta baseball moneyline -\$46.62 (1W/2L). Peak haftası verisi
diskte yok. Spor portföyü değişimi (Task 1) sonrası 7 günlük gözlem
gerekli — TODO-FAZ2-001 olarak işaretlendi.

Faz 7/10 (iyi-donem-rollback spec)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: NHL Moneyline-Only Flag (Lean Entegrasyon)

**Hedef:** Hockey için NHL ML-only kuralı **sport_rules üzerinden flag** olarak girer. Magic number yok, DRY tek yer, scanner bu flag'i okur.

**Files:**
- Modify: `src/config/sport_rules.py` (NHL'e `moneyline_only: true` flag ekle)
- Modify: `src/orchestration/scanner.py` veya `entry_processor.py` (flag'i kontrol et)
- Test: `tests/unit/orchestration/test_scanner.py`

- [ ] **Step 1: sport_rules.py'da NHL girdisini bul**

Read: `src/config/sport_rules.py`
Bul: `"nhl"` anahtarı

- [ ] **Step 2: NHL girdisine `moneyline_only: true` ekle**

Edit `src/config/sport_rules.py`:

```python
SPORT_RULES: dict[str, dict] = {
    # ...
    "nhl": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 2.5,
        "period_exit": True,
        "period_exit_deficit": 3,
        "score_source": "espn",
        "espn_sport": "hockey",
        "espn_league": "nhl",
        "moneyline_only": True,   # YENİ — kullanıcı kararı (eski projede 4 günde 13W/2L +$126 ML-only kanıt)
    },
    # ...
}
```

- [ ] **Step 3: get_moneyline_only helper ekle (DRY)**

Edit `src/config/sport_rules.py` — `get_match_duration_hours` benzeri pattern'le:

```python
def is_moneyline_only(sport_tag: str) -> bool:
    """Sport için yalnızca moneyline market'leri kabul edilir mi?"""
    return bool(get_sport_rule(sport_tag, "moneyline_only", False))
```

- [ ] **Step 4: Failing test yaz**

Edit `tests/unit/config/test_sport_rules.py`:

```python
def test_is_moneyline_only_nhl_returns_true():
    from src.config.sport_rules import is_moneyline_only
    assert is_moneyline_only("nhl") is True

def test_is_moneyline_only_nba_returns_false():
    from src.config.sport_rules import is_moneyline_only
    assert is_moneyline_only("nba") is False

def test_is_moneyline_only_unknown_returns_false():
    from src.config.sport_rules import is_moneyline_only
    assert is_moneyline_only("unknown_sport") is False
```

- [ ] **Step 5: Test fail edip etmediğini doğrula**

Run: `pytest -q tests/unit/config/test_sport_rules.py::test_is_moneyline_only_nhl_returns_true -v`
Expected: PASS (Step 2-3 ile fonksiyon eklendi)

- [ ] **Step 6: scanner'da flag uygulanır mı doğrula**

Read: `src/orchestration/scanner.py` veya `entry_processor.py`
Bul: market filtreleme yapılan yer (sports_market_type kontrolü)

Edit (uygun yere):

```python
from src.config.sport_rules import is_moneyline_only
from src.models.market import SportsMarketType

# Market filtreleme:
def _filter_by_sport_rules(market: MarketData) -> bool:
    """Sport-specific market type filtresi (moneyline_only flag uygulaması)."""
    if is_moneyline_only(market.sport_tag):
        if market.sports_market_type != SportsMarketType.MONEYLINE:
            return False
    return True

# Mevcut filter chain'e ekle (her market için bir kez çağrılır)
```

- [ ] **Step 7: Integration test yaz**

Edit `tests/unit/orchestration/test_scanner.py`:

```python
def test_scanner_filters_nhl_non_moneyline_markets():
    # NHL totals market verilir, filter False döndürmeli
    market = MarketData(
        condition_id="0xtest",
        sport_tag="nhl",
        sports_market_type=SportsMarketType.TOTALS,
        # ... diğer required alanlar
    )
    assert _filter_by_sport_rules(market) is False

def test_scanner_passes_nhl_moneyline_markets():
    market = MarketData(
        condition_id="0xtest",
        sport_tag="nhl",
        sports_market_type=SportsMarketType.MONEYLINE,
        # ...
    )
    assert _filter_by_sport_rules(market) is True

def test_scanner_passes_nba_totals_markets():
    """NBA totals dokunulmaz (moneyline_only yok)."""
    market = MarketData(
        condition_id="0xtest",
        sport_tag="nba",
        sports_market_type=SportsMarketType.TOTALS,
        # ...
    )
    assert _filter_by_sport_rules(market) is True
```

- [ ] **Step 8: pytest çalıştır**

Run: `pytest -q tests/unit/orchestration/test_scanner.py tests/unit/config/test_sport_rules.py -v`
Expected: 4 yeni test PASS, mevcut testler PASS

- [ ] **Step 9: Tam test suite**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat(rollback): NHL moneyline-only kısıtı sport_rules flag'i ile entegre

Lean entegrasyon: SPEC-L cruft'ı (allowed_sport_tags yorum + scanner özel
mantığı) yerine sport_rules.nhl.moneyline_only=True tek-yer flag. DRY, magic
number yok, ARCH_GUARD Kural 6 uyumlu.

Kullanıcı kararı: eski projede 4 günde 13W/2L +\$126 kanıt — NHL spread/totals
veri yok, açılması kanıt-temelli karar gerektirir (TODO-FAZ2 kapsamı).

Eklenen: is_moneyline_only() helper + scanner _filter_by_sport_rules + testler.

Faz 8/10 (iyi-donem-rollback spec)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: State Temizleme + Bot Reload

**Hedef:** Mevcut audit'i timestamp arşivine taşı, fresh state ile bot başlat.

**Files:**
- Modify: `data/positions.json` (silinir veya boş yazılır)
- Modify: `data/circuit_breaker_state.json` (silinir)
- Modify: `data/stock_queue.json` (silinir)
- Modify: `data/bot_status.json` (silinir)
- Move: `logs/audit/trade_history.jsonl` → `logs/audit/trade_history.archive.YYYYMMDD_HHMMSS.jsonl`
- Move: `logs/audit/equity_history.jsonl` → benzer arşiv
- Modify: `logs/session/trade_history.jsonl` (boş)
- Modify: `logs/session/equity_history.jsonl` (boş)

- [ ] **Step 1: Bot'u durdur (eğer çalışıyorsa)**

Run: `tasklist | grep -i python || echo "no python"`
Eğer çalışıyorsa: `python scripts/reboot.py` (graceful stop) veya taskkill ile

- [ ] **Step 2: Bot kapandı mı doğrula**

Run: `tasklist | grep -i python || echo "stopped"`
Expected: "stopped"

- [ ] **Step 3: Audit current'ı timestamp arşivine taşı**

Run:
```bash
TS=$(date +%Y%m%d_%H%M%S)
mv logs/audit/trade_history.jsonl "logs/audit/trade_history.archive.${TS}.jsonl"
mv logs/audit/equity_history.jsonl "logs/audit/equity_history.archive.${TS}.jsonl"
touch logs/audit/trade_history.jsonl
touch logs/audit/equity_history.jsonl
```

- [ ] **Step 4: Session'ı boşalt**

Run:
```bash
> logs/session/trade_history.jsonl
> logs/session/equity_history.jsonl
```

- [ ] **Step 5: State dosyalarını sil (fresh start)**

Run:
```bash
rm -f data/positions.json
rm -f data/circuit_breaker_state.json
rm -f data/stock_queue.json
rm -f data/bot_status.json
```

NOT: `data/blacklist.json` kalır (öğrenilmiş bilgi, dokunulmaz).

- [ ] **Step 6: Bot reload**

Run: `python scripts/reboot.py reload`
Expected: "Reload complete." — bot ve dashboard yeniden başlar

- [ ] **Step 7: Bot başlangıç sağlık kontrolü**

Run: `sleep 8 && tail -20 logs/runtime/bot.log`
Expected:
- "Process lock acquired" satırı var
- "Bootstrap complete: mode=dry_run bankroll=$1000.00 positions=0 realized=$0.00" var
- "Agent starting: mode=dry_run" var
- Hiç Exception/Traceback yok

- [ ] **Step 8: Dashboard sağlık kontrolü**

Run: `curl -s http://127.0.0.1:5050/api/balance 2>&1 | head -c 300`
Expected: JSON cevap, bankroll=1000, realized=0, open_positions=0

- [ ] **Step 9: 10 dakika gözlem**

Run: `sleep 600 && grep -E "ERROR|CRITICAL|Traceback|Exception" logs/runtime/bot.log | head -20`
Expected: 0 hata satırı

- [ ] **Step 10: Commit (state dosyaları git'te değil ama config rollback için marker)**

```bash
git add -A
git commit --allow-empty -m "feat(rollback): state temizlendi + bot reload (Faz 1 tamamlandı)

Audit current'ı timestamp arşivine taşındı, positions.json silindi, bot fresh
state ile başlatıldı. 19 Apr peak strateji parametreleri + temiz kod tabanı.

10 dk gözlem: 0 hata. Bot dry_run modunda yeni trade aramaya başladı.

Faz 9/10 (iyi-donem-rollback spec)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: 24-Saat Gözlem + Faz 2 Hazırlık

**Hedef:** Bot'un yeni davranışını doğrula, Faz 2 spec'i için veri topla.

**Files:** Bu task'ta dosya değişikliği YOK — gözlem + dokümantasyon.

- [ ] **Step 1: PLAN-001 DONE → PLAN.md temizliği**

Edit `PLAN.md` — `## Aktif Planlar` bölümü:

```markdown
## Aktif Planlar

*Tamamlanan planlar silinir.*

### PLAN-FAZ2-001 (gözlem aşaması)
- **Durum**: OBSERVATION (24-168 saat veri toplama)
- **Tarih başlangıç**: 2026-05-15
- **Hedef**: Faz 1 rollback sonrası 7 günlük performans gözlemi. Aşağıdaki belirsiz parametrelerin etkisi ölçülür:
  - SPEC-013 min_favorite_probability filter
  - max_positions_per_event (1 vs 2)
  - max_post_start_hours=8.0
  - SPEC-014 baseball_score_exit
  - min_scale_out_realized_usdc=$7
- **Beklenti**: 7 gün sonunda net PnL ≥ +$20, win rate ≥ %60, near_resolve trade'leri pozitif
```

- [ ] **Step 2: 24 saat sonra trade gözlemi**

Run (24 saat sonra):
```bash
PYTHONIOENCODING=utf-8 python3 -c "
import json
trades = [json.loads(l) for l in open('logs/audit/trade_history.jsonl') if l.strip()]
closed = [t for t in trades if t.get('exit_price') is not None or (t.get('partial_exits') or [])]
print(f'Total trades: {len(trades)} | Closed: {len(closed)}')
total = 0
for t in closed:
    p = sum(float(pe.get('realized_pnl_usdc') or 0) for pe in (t.get('partial_exits') or []))
    if t.get('exit_price') is not None:
        p += float(t.get('exit_pnl_usdc') or 0)
    total += p
    print(f'  {t[\"slug\"]:35} | reason={t.get(\"exit_reason\",\"\"):20} | pnl={p:+.2f}')
print(f'TOTAL: {total:+.2f}')
"
```

- [ ] **Step 3: Faz 2 değerlendirmesine veri topla**

Beklenen pattern'ler (eğer görülürse Faz 2 spec'inde ele alınır):
- WNBA pozisyonları açık ve pnl negatif → SPEC-013 min_favorite_probability tekrar açılabilir
- Aynı event'te 2+ pozisyon → max_positions_per_event=2 etki kanıt
- Maç başladıktan sonra entry'ler → max_post_start_hours etki kanıt
- $7 altı scale_out skip → min_scale_out_realized_usdc etki kanıt

- [ ] **Step 4: 7 gün sonra Faz 2 spec yaz**

Brainstorming skill → yeni spec → `docs/superpowers/specs/2026-05-22-faz2-belirsizler.md`

- [ ] **Step 5: Spec/Plan dosyalarını sil (tamamlandı)**

```bash
rm docs/superpowers/specs/2026-05-15-iyi-donem-rollback-design.md  # OPSİYONEL: spec'i tut, archive olarak kalsın
# PLAN'ı içeride güncellemek yeterli
```

NOT: Spec dosyasını **silmek önerilmez** — Faz 2'de referans olur. Sadece PLAN.md temizlenir.

- [ ] **Step 6: Commit**

```bash
git add PLAN.md
git commit -m "docs(rollback): Faz 1 tamamlandı, Faz 2 OBSERVATION başlatıldı

24-168 saat veri toplama. 7 gün sonunda Faz 2 spec'i yazılır (5 belirsiz
parametre değerlendirmesi).

Faz 10/10 (iyi-donem-rollback spec)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Risk & Rollback

**Plan kötü giderse:**
- Her task ayrı commit, `git revert <hash>` ile 1 adımda geri
- State tamamen yedeklendi (Pre-4 + Task 9 arşivleri)
- Tüm archive'lar dokunulmadan kalır

**Tek sefer rollback:**
```bash
git log --oneline | head -15  # commit'leri gör
git reset --hard <pre-rollback-commit-hash>  # tüm değişiklikleri geri al
cp data/positions.pre_rollback_*.bak data/positions.json  # state'i geri yükle
python scripts/reboot.py reload
```

## Doğrulama Kontrol Listesi (Plan Sonu)

- [ ] `git log --oneline | head -15` 10 task commit'i görünüyor
- [ ] `pytest -q` PASS (bilinen baseline ile aynı veya üstü)
- [ ] `grep -rn "a_conf_hold\|nba_spread\|cricket\|three_way\|event_grouper\|soccer_score" src/ tests/` boş döner
- [ ] `python scripts/reboot.py reload` exit 0 + bot.log'da Exception yok
- [ ] `curl -s http://127.0.0.1:5050/api/balance` bankroll=$1000, realized=$0
- [ ] `config.yaml` 25 sport_tag açık (Hockey için sadece NHL)
- [ ] `src/config/sport_rules.py` NHL `moneyline_only: True`
- [ ] PLAN.md PLAN-001 silindi, PLAN-FAZ2-001 eklendi
- [ ] Archive dosyaları (logs/audit/*.archive.*.jsonl) DOKUNULMADI — toplam 6 archive görünür

---
