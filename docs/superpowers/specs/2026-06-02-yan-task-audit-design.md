# Yan Task Audit — Genel Pattern Sağlamlaştırma (SPEC)

> Tarih: 2026-06-02
> Spec ID: SPEC-AUDIT-001
> Status: DRAFT (plan onaylanınca aktif)

---

## Problem

2026-06-02 oturumunda yapılan 14 fix'in 4'ünde **yan task atlama riski** tespit edildi. Bu fix'ler dar kapsamda uygulandı (sadece spesifik bir maç/lig/durum için) ama altta yatan pattern **tüm bot'u (eklenmiş ve eklenecek tüm sporlar/dispatch'ler)** etkiliyor. Yan task'lar atlanırsa:

- Aynı bug başka spor/lig için sessizce devam eder
- Yeni eklemeler aynı hataya düşer
- Drift birikir → spagetti

## ORTA-Risk Fix'ler (audit kapsamı)

### 1. UI Etiket — Kar/Zarar PnL Bazlı (dar)
- Uygulanan: `fmt.js::exitReasonLabel` sadece `scale_out_tier_N` için PnL bazlı etiket (`Take Profit` veya `Partial sell`)
- Yan task: `near_resolve` da zararla bitebilir (resolve_no kaybeden taraf için), `stop_loss`, `graduated_sl`, `partial_sl` — bu exit reason'lar **her zaman** "negatif tone" alıyor olabilir ama label adı PnL'ye göre değişmiyor
- **Genel pattern**: Her PARTIAL exit_reason için PnL işaretine göre tone + label seçilmeli; FULL exit'ler için exit reason adı zaten anlamı yansıttığı için yeterli

### 2. Position.source Field — Tek Constructor (dar)
- Uygulanan: `entry_processor.py:198` Position(...) constructor'a `source=signal.source` eklendi
- Yan task: `lifecycle.py`, `startup.py`, `bootstrap.py`, dashboard reconcile, vs. başka yerlerde Position oluşturuluyorsa source eksik kalır
- **Genel pattern**: TÜM Position(...) constructor'larında source field açıkça set edilmeli; default `"bookmaker"` kalıyorsa fallback davranış net olmalı

### 3. Lab Auto-Sync — Eksik Liste (dar)
- Uygulanan: `lab_v2/start.py::_sync_reference_data` sadece `tennis_calibration.json + tennis_ratings_surface.json` sync
- Yan task: `tennis_ratings.json` (3MB), `basketball_cache/nba_ratings.json`, `basketball_cache/wnba_ratings.json`, `g_league_ratings.json`, `summer_league_ratings.json`, eklenecek diğer ligler — sync edilmiyor
- **Genel pattern**: Lab dizininde sync edilecek tüm "shared reference data" tek bir liste/glob ile belirlenmeli; yeni rating dosyaları otomatik dahil olmalı

### 4. Team Resolver Alias — Sadece WNBA (dar)
- Uygulanan: `basketball_team_resolver.py::_WNBA_TEAMS` yeni takımlar (GSV, POR) + alias (conn, wsh, la, las↔LVA fix)
- Yan task: NBA Charlotte Bobcats→Hornets, Seattle SuperSonics expansion 2025 söylentisi, NCAAB ekspansiyon, Euroleague yeni promosyon, **tüm ligler için aynı tip eksik alias riski**
- **Genel pattern**: Resolver alias listeleri **canlı veri kaynağından** (nba_api / ESPN team list) auto-generate edilmeli; manuel hardcoded liste drift eder

## Hedef Mimari (genel pattern)

Her audit kategorisi için:

- **Kapsama testi**: tüm potansiyel call site'ları, sport_tag'ler, alias varyantları taranır
- **Genelleştirilmiş çözüm**: spesifik fix yerine, gelecekteki eklemelere otomatik adapte olan pattern
- **Regression testi**: kapsama testi merkezi (örn. `tests/regression/test_position_source_coverage.py`)
- **Hata fark edilse alarm**: telegram alert (Plan 2 sayesinde)

## Out of Scope

- Bug düzeltme dışı refactor
- Performans iyileştirme
- Yeni feature

## Risk

- Audit sırasında dispatch'leri değiştirmek scanner davranışını etkileyebilir → her değişiklik test + reload önce
- Resolver auto-generate iyi niyetli ama yan etkileri olabilir (gizli alias'lar kaybolur) → manuel override imkanı korunur

## Done Definition

- 4 ORTA-risk fix için **kapsama testi** + **genel pattern** uygulanmış
- 1894+ test geçer
- Yeni eklenen spor/lig/exit_reason için yan task atlama riski **sıfır** (pattern auto-kapsar)
- Plan 3 (scraper) entegrasyonu için zemin hazır
