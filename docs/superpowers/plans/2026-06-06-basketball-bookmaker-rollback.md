# Basketbol → Bahisçi-Only Rollback (model tamamen kaldırma + totals restore) Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** Basketbolu kazandığı döneme (Mayıs, +$573) döndür: **bahisçi konsensüsü ML + totals**, in-house model TAMAMEN kaldırılmış (dead code yok). Tenis kendi modelini korur.

**Architecture:** (1) SPEC-K bahisçi totals/spreads parser'ı git'ten geri getir + odds_enricher'a bağla → bahisçi totals'ı fiyatlar. (2) basketball_dispatch sadece bahisçiye yönlendir. (3) Model kodunu (domain/pricing/basketball, infra/data/basketball, anchor enricher, ratings builder, factory wiring, config, testler) tamamen sil.

**Kanıt:** Mayıs basketbol totals num_bookmakers=56 (bahisçi fiyatlı), model YOK, +$573. Model 1-2 Haz geldi → −$82. SPEC-Z19 (config gate) yetersiz: dead code bırakıyor + bahisçi h2h-only olduğu için totals kayıp.

---

## Faz A — Bahisçi totals/spreads enrichment geri getir (additive)

**Files:**
- Create: `src/strategy/enrichment/_spread_totals_parser.py` (git `26f2500`'den restore, 104 satır)
- Modify: `src/strategy/enrichment/odds_enricher.py` (totals/spreads market type → ilgili markets fetch + parser)
- Test: `tests/unit/strategy/enrichment/test_spread_totals_parser.py` (git'ten restore) + odds_enricher totals testi

- [ ] A1. `git show 26f2500:src/strategy/enrichment/_spread_totals_parser.py` → restore dosya
- [ ] A2. `git show 26f2500:tests/.../test_spread_totals_parser.py` → restore test; çalıştır PASS
- [ ] A3. RED: odds_enricher totals market_type için bahisçi prob döndürmeli (failing test)
- [ ] A4. GREEN: enrich_market'a market_type-aware dal: totals/spreads → markets="totals"/"spreads" fetch + parser + line match. h2h davranışı korunur.
- [ ] A5. Tam suite + commit

## Faz B — basketball_dispatch sadece bahisçi

**Files:** Modify `src/strategy/enrichment/basketball_dispatch.py`

- [ ] B1. RED: nba totals market → bookmaker_enricher çağrılmalı (model değil)
- [ ] B2. GREEN: dispatch'i sadeleştir — basketbol (ML+totals+spreads) → `bookmaker_enricher(market)`. Model yolu (ratings/efficiency/resolve/enrich_basketball_from_model) tamamen çıkar. Futures/non-match filtre korunur (bahisçi zaten None döner ama temiz).
- [ ] B3. SPEC-Z19 `model_enabled` gate'i kaldır (artık gereksiz — model yok)
- [ ] B4. Tam suite + commit

## Faz C — Model kodunu tamamen sil (dead code yok)

**Sil (src):**
- `src/domain/pricing/basketball/` (efficiency_metrics, match_pricer, pace_efficiency, rest_days, season_reset, team_elo, __init__)
- `src/strategy/enrichment/basketball_anchor_enricher.py`, `basketball_model_anchor.py`
- `src/domain/matching/basketball_team_resolver.py`
- `src/infrastructure/data/basketball/` (tüm scraper/refresher/store/schema/health)
- `src/orchestration/basketball_ratings_builder.py`, `factory_basketball.py`
- `src/config/basketball_settings.py`

**Edit (referansları temizle):**
- `src/orchestration/factory.py` — `_maybe_invoke_basketball_refresh`, `_maybe_build_basketball_ratings`, ratings/efficiencies build + dispatch'e model arg geçişi sil; dispatch çağrısını yalın bookmaker_enricher'a indir
- `src/orchestration/roster_drift_monitor.py` — team_elo bağımlılığı varsa basketbol kısmını çıkar (tenis/diğer korunur) ya da monitör model-only ise sil
- `src/config/settings.py` — `BasketballConfig` import/field + `__all__` çıkar
- `config.yaml` — `basketball:` model bölümü sadeleştir (sadece whitelist gerekiyorsa allowed_sport_tags'te kalır; model params sil)

**Sil (tests):** yukarıdaki modüllerin tüm test dosyaları + basketball_dispatch model testleri

- [ ] C1. Dispatch + factory'den model importlarını kes (kırılma yüzeyini kapat)
- [ ] C2. Model src dosyalarını sil (leaf-first)
- [ ] C3. İlgili test dosyalarını sil
- [ ] C4. `pytest -q` → kalan referansları (ImportError) tek tek temizle
- [ ] C5. Commit

## Faz D — Doğrulama
- [ ] D1. `pytest -q` tümü yeşil (1 alakasız calibration-flaky hariç)
- [ ] D2. `python -c "from src.orchestration.factory import build_agent_deps"` import smoke (factory bozulmadı)
- [ ] D3. DECISIONS.md SPEC-Z21 girişi + commit

## Faz E — State temizliği (kod sonrası)
- [ ] E1. Reload (paper) → yeni kod aktif
- [ ] E2. positions.json'dan açık BASKETBOL pozisyonlarını sil (eski model/karışık mantık girişleri) — kullanıcı kararı
- [ ] E3. Doğrula: dashboard'da basketbol pozisyonu yok, bot bahisçi-only basketbol tarıyor

---

## ARCH_GUARD notları
- Katman: odds_enricher (strategy) → odds_client (infra) zaten var; yeni I/O eklenmez (mevcut fetch kullanılır)
- DRY: _spread_totals_parser tek modül; dispatch sadeleşir (DRY artışı)
- <400 satır: silme ağırlıklı, dosyalar küçülür
- Dead code: model tamamen silinir (hedef)
