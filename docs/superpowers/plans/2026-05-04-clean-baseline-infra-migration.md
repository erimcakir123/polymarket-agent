# Clean Baseline + Infra Migration Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to execute task-by-task with tight review.

**Goal:** 16 Nisan baseline (`baseline-2026-04-16`) üstüne sadece **altyapısal** parçaları (dashboard + slug/market + log mimarisi + slippage + DECISIONS) entegre et. Entry/exit kuralları, in-match olasılık modelleri, sport-specific exit dispatcher'lar, API client'lar — bunlara DOKUNMA. Tüm pytest %100 geçer durumda olmalı. Hiçbir şey bozulmamış olmalı.

**Architecture:** Mevcut HEAD = baseline-2026-04-16 (clean). Hedef: aynı baseline + 4 altyapı paket (A: dashboard, B: slug/market, C: log mimarisi, H: slippage). Kaynaklar: `pre-rollback-2026-05-04` tag (mevcut snapshot). Plus `foundation-v1` (2026-04-25, 833 test geçen stable infrastructure baseline) referans.

**Tech Stack:** Python 3.12+, pytest, Pydantic, Flask (dashboard), git tags + git checkout (cherry-style migration).

**Yasaklar:**
- Entry kuralları (gate.py logic): DOKUNMA
- Exit kuralları (price_cap, scale_out, *_score_exit, monitor.py): DOKUNMA
- In-match olasılık modelleri (src/domain/math/): DOKUNMA
- Sport-specific exit dispatcher'lar (_*_dispatch.py): DOKUNMA
- MLB Pythagorean+log5+pitcher (mlb_*.py math): DOKUNMA
- Tennis Magnus, NHL empirical: DOKUNMA
- Yeni API client'lar (mlb_stats_client, openweather, sackmann, espn_*): DOKUNMA

---

## Task 0: Pre-flight kontroller (READ-ONLY)

**Files:** Yok (sadece okuma)

- [ ] **Step 1:** HEAD doğrula = baseline-2026-04-16 (commit `11d0954`)
- [ ] **Step 2:** Mevcut pytest baseline geçiş sayısı: `pytest -q` → kaç pass / kaç fail not al
- [ ] **Step 3:** İki tag varlığı: `git tag | grep -E "baseline-2026-04-16|pre-rollback-2026-05-04|foundation-v1"`

---

## Task 1: pre-rollback'ten ALTYAPI dosyalarını kategorize et

**Files:** Yok (sadece kategorize)

- [ ] **Step 1:** `git diff baseline-2026-04-16..pre-rollback-2026-05-04 --name-only` ile değişen dosyaları al
- [ ] **Step 2:** Her dosyayı kategorize et:
  - `ALTYAPI`: dashboard, slug/market, log, executor (slippage)
  - `ENTRY/EXIT`: gate, _gate_helpers, exit kuralları, monitor logic
  - `MODEL`: src/domain/math/, sport-specific in-match
  - `API_CLIENT`: yeni API'lar (mlb_stats, openweather, sackmann)
  - `SUPPORT`: tests, docs, config
- [ ] **Step 3:** Sadece `ALTYAPI` + onların `SUPPORT` test dosyalarını migrate listesine al

---

## Task 2: A — Dashboard migrate

**Files:**
- Modify/Add: `src/presentation/dashboard/` (tüm dosyalar pre-rollback'ten)
- Modify/Add: `tests/unit/presentation/dashboard/`
- Add: `Sound/` (mp3 dosyaları)

- [ ] **Step 1:** `git checkout pre-rollback-2026-05-04 -- src/presentation/dashboard/ tests/unit/presentation/dashboard/ Sound/`
- [ ] **Step 2:** `pytest tests/unit/presentation/dashboard/ -q` çalıştır
- [ ] **Step 3:** Fail varsa: dashboard testleri `logs/audit/`, `logs/runtime/`, `logs/session/` bekliyor olabilir → log mimarisi (Task 4) ile birlikte fix
- [ ] **Step 4:** Geçmezse Task 4 sonrası tekrar test
- [ ] **Step 5:** Commit: "feat(dashboard): migrate visual improvements from pre-rollback"

---

## Task 3: B — Slug + market eşleştirme migrate

**Files (sport parsers + matching + scanner):**
- Add: `src/domain/sports/` (mlb_question_parser, mlb_team_aliases, nhl_question_parser, nhl_team_aliases, nhl_match_clock)
- Add/Modify: `src/domain/matching/` (pair_matcher, three_way_title, sport_mapping, cricket_mapping, tennis_*_resolver, odds_sport_keys, team_resolver)
- Modify: `src/infrastructure/apis/gamma_client.py` (sport_tag override mlb→baseball)
- Modify: `src/orchestration/scanner.py` (SMT NBA/NHL/MLB spread+total kabul)
- Add/Modify: `src/config/_sport_aliases.py`, `sport_rules.py`
- Test: `tests/unit/domain/sports/`, `tests/unit/domain/matching/`, `tests/domain/sports/`

- [ ] **Step 1:** `git checkout pre-rollback-2026-05-04 -- src/domain/sports/ src/domain/matching/ src/infrastructure/apis/gamma_client.py src/orchestration/scanner.py src/config/_sport_aliases.py src/config/sport_rules.py tests/unit/domain/sports/ tests/unit/domain/matching/ tests/domain/`
- [ ] **Step 2:** `pytest tests/unit/domain/ -q` çalıştır
- [ ] **Step 3:** Fail varsa: model dosyaları (`src/models/market.py` vs.) `match_title` field'ı bekliyorsa modelleri pre-rollback'ten al ama SADECE field eklemeleri (entry/exit kural değil)
- [ ] **Step 4:** `pytest tests/unit/orchestration/test_scanner.py -q`
- [ ] **Step 5:** Commit: "feat(slug-market): migrate Polymarket Spread/O-U format support + sport_tag override"

---

## Task 4: C — Log mimarisi (audit/runtime/session) migrate

**Files:**
- Modify: `src/infrastructure/persistence/trade_logger.py` (mirror self-heal + log_partial_exit)
- Add/Modify: `src/infrastructure/persistence/archive_logger.py` (audit dual-write)
- Modify: `src/infrastructure/persistence/skipped_trade_logger.py`, `equity_history.py`
- Add: `src/orchestration/_factory_loggers.py`
- Add: `src/orchestration/operational_writers.py` (skip_reason+detail)
- Add: `scripts/reboot.py`
- Add: `data/.gitignore`
- Test: `tests/integration/test_reboot.py`, `tests/unit/infrastructure/persistence/test_trade_logger.py`

- [ ] **Step 1:** `git checkout pre-rollback-2026-05-04 -- src/infrastructure/persistence/trade_logger.py src/infrastructure/persistence/archive_logger.py src/infrastructure/persistence/skipped_trade_logger.py src/infrastructure/persistence/equity_history.py src/orchestration/_factory_loggers.py src/orchestration/operational_writers.py scripts/reboot.py data/.gitignore tests/integration/test_reboot.py tests/unit/infrastructure/persistence/test_trade_logger.py`
- [ ] **Step 2:** `pytest tests/unit/infrastructure/persistence/ tests/integration/test_reboot.py -q`
- [ ] **Step 3:** Fail varsa: factory.py'a logger wiring eklenmesi gerekebilir (entry/exit logic'e dokunmadan SADECE logger DI)
- [ ] **Step 4:** Commit: "feat(logs): migrate 3-tier audit/runtime/session architecture + reboot script"

---

## Task 5: H — Slippage + executor migrate

**Files:**
- Modify: `src/infrastructure/executor.py` (post-fill edge check + STALE_PRICE_REJECT)
- Test: `tests/unit/infrastructure/test_executor.py`

- [ ] **Step 1:** `git checkout pre-rollback-2026-05-04 -- src/infrastructure/executor.py tests/unit/infrastructure/test_executor.py`
- [ ] **Step 2:** `pytest tests/unit/infrastructure/test_executor.py -q`
- [ ] **Step 3:** Fail varsa: entry_processor.py'a parametre eklenmesi gerekebilir (`fair_price`, `min_edge`) ama 16 Nisan entry_processor entry kuralı içerir → DOKUNMA. Executor'ı 16 Nisan signature'ıyla geri uyumlu yap (yeni parametreler optional default None)
- [ ] **Step 4:** Commit: "feat(executor): migrate slippage protection (post-fill edge check)"

---

## Task 6: DECISIONS.md güncelle (PRD/TDD yerine)

**Files:**
- Modify: `DECISIONS.md`

- [ ] **Step 1:** Mevcut `DECISIONS.md`'yi oku (16 Nisan'da var)
- [ ] **Step 2:** Yeni section ekle: "## Altyapı Migration (2026-05-04 baseline rollback + selective infra)"
  - Hangi paketler migrate edildi (A, B, C, H)
  - Hangi paketler atlandı (E, F, sport-specific in-match modeller)
  - Sebep: "16 Nisan entry/exit kurallarına geri dön + altyapı koru"
- [ ] **Step 3:** `git add DECISIONS.md && git commit -m "docs(decisions): record infra migration scope"`

---

## Task 7: Tüm test suite doğrulama

**Files:** Yok (sadece test çalıştır)

- [ ] **Step 1:** `pytest -q --no-header` çalıştır
- [ ] **Step 2:** Fail sayısı not al
- [ ] **Step 3:** Fail varsa kategorize:
  - Migrate paketleriyle alakalı → fix (test'i pre-rollback'ten al ya da 16 Nisan style'ına uydur)
  - Entry/exit ile alakalı → SİL (kullanılmayacak in-match modeller'in eski testleri olabilir)
- [ ] **Step 4:** Hedef: **0 fail** (skip OK)
- [ ] **Step 5:** Commit: "test: align test suite with infra-only migration"

---

## Task 8: Bot başlatma + smoke test

**Files:** Yok

- [ ] **Step 1:** Eski python process'leri kill (`Stop-Process -Id <pid> -Force`)
- [ ] **Step 2:** `python scripts/reboot.py reboot` (yeni reboot script Task 4'te geldi)
- [ ] **Step 3:** Bot başladı mı: `Get-Process python` ve `data/bot_status.json` okuma
- [ ] **Step 4:** İlk heavy cycle 30 dk içinde — gözlem

---

## Task 9: Sistem özeti dosyası (TEKNİK OLMAYAN dilde)

**Files:**
- Add: `docs/SYSTEM_OVERVIEW_2026-05-04.md`

- [ ] **Step 1:** Yeni model özet dosyası yaz (sade dil, kullanıcı için):
  - "Şu an bot ne yapıyor"
  - "Hangi sport'lara giriyor (NBA moneyline default, sadece moneyline kabul ediliyor)"
  - "Kararları nasıl alıyor (16 Nisan kural seti — basit, kanıtlanmış)"
  - "Altyapı eklemeleri ne katıyor (dashboard, log, slug eşleşme, slippage)"
  - "Yapılmayan şeyler (in-match modeller, sport-specific exit, MLB/Tennis aktif değil)"
  - "Riskler + sınırlar"
- [ ] **Step 2:** Commit: "docs: system overview (post-baseline-rollback)"

---

## Self-Review Notes

- **Spec coverage:** A, B, C, H paketleri + DECISIONS + test alignment + reboot smoke + özet — tüm kullanıcı isteği var
- **Placeholder scan:** Task 3 step 3, Task 4 step 3, Task 5 step 3 "Fail varsa" branch'leri var — bu **gerçek karar noktaları**, agent her birinde uygun davranır
- **Type consistency:** N/A (cherry-pick işi, yeni type tanımı yok)
- **Yasak listesi:** her task'a "DOKUNMA" listesi eklenmeli — eklendi (header)

## Risk

- pre-rollback'ten getirilen dosyalar 16 Nisan logic'iyle uyumsuz olabilir → Task 7 her şeyi yakalar
- Geri dönüş: `git reset --hard baseline-2026-04-16 && git clean -fd`
