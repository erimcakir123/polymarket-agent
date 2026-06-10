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

### PLAN-DATA1: Sackmann Güncellik Paketi (homojen çift-karne + günlük tazeleme)

- **Durum**: APPROVED (kullanıcı 2026-06-10: "sackmann güncel kalmalı bunu çöz")
- **Tarih**: 2026-06-10
- **Öncelik**: P1
- **Etki**: scripts/build_tennis_ratings.py, src/infrastructure/data/tennis_surface_ratings_store.py (save eklenir), src/infrastructure/data/sackmann_refresher.py (eşik config), src/config/settings.py + config.yaml (tennis.sackmann_max_age_days), src/orchestration/factory_refresh_hooks.py + agent.py (günlük periyodik kontrol), testler
- **Adımlar**:
  1. Store'a `save_all_surfaces` (infra, TDD): lab formatıyla aynı JSON (overall/Hard/Clay/Grass + serve) — `load_all_surfaces` round-trip testi.
  2. `build_tennis_ratings.build_ratings`: TEK veri yüklemesiyle hem flat `tennis_ratings.json` hem `tennis_ratings_surface.json` yazar (homojen fotoğraf). Per-surface Glicko fit (sim'deki `_fit_glicko` deseni; lab scriptinden bilgi-migrasyonu, kod kopyalanmaz). Test: sentetik maçlarla iki dosya tutarlı.
  3. Tazelik eşiği config'e: `tennis.sackmann_max_age_days: 1` (default 1; settings + config.yaml + refresher parametre zinciri). Test: eşik config'den okunuyor.
  4. Günlük periyodik kontrol: `factory_refresh_hooks.maybe_refresh_sackmann_periodic(cache_dir, max_age_days)` — agent heavy cycle'da günde en fazla 1 kez `refresh_if_stale` + çift-rebuild çağırır (saf zaman-karar fonksiyonu `should_check_again(last_iso, now_iso, period_h)` TDD). Network fail → WARNING + devam (mevcut davranış).
  5. `pytest -q` yeşil + commit. Reload AYRICA sorulur (kullanıcı kuralı).
- **Kabul**: iki karne dosyası aynı anda, aynı veriden kurulur; eşik 1 gün; bot reload'suz da günlük kontrol eder; Odds API kullanılmaz.

### PLAN-DATA2: Zemin Becerisi Kalıcılık Testi (2024→2025 çim, tek seferlik araştırma)

- **Durum**: APPROVED (kullanıcı: "geçen seneki çim hâlâ geçerli mi bayat mı kontrol et")
- **Tarih**: 2026-06-10
- **Öncelik**: P2
- **Etki**: scripts/research_surface_persistence.py (yeni, salt-okunur araştırma) + data/sackmann_research/ (2024 CSV'leri — ÜRETİM cache'ine DOKUNULMAZ, ayrı klasör)
- **Adımlar**:
  1. 2024 CSV'lerini `refresh_cache(data/sackmann_research, years=[2024])` ile indir (ücretsiz GitHub).
  2. Walk-forward test: 2024+2025 maçları kronolojik işle; her 2025 ÇİM maçı öncesinde üç tahminci ile öngör: (a) genel karne, (b) sadece-çim karnesi (2024 çimi + o ana dek 2025 çimi), (c) harman (ters-varyans). `glicko.win_probability` kullanılır. Tahmin sonrası reyting güncelle.
  3. Metrik: doğruluk + log-loss, üç tahminci yan yana; 2025 çim maç sayısı raporlanır.
  4. Yorum: (b)/(c) ≥ (a) ise geçen yıl çimi BAYAT DEĞİL → harman kararına girdi sağlar.
- **Kabul**: rapor konsola; üretim dosyaları değişmez; sonuç kullanıcıya sade dille sunulur.

---

> NOT (2026-06-07): PLAN-DRYRUN-CLEANUP uygulandı AMA **GERİ ALINDI** — hatalıydı.
> Watson moneyline'ı $50'lık (116 pay) gerçek bir kazanandı; dry-run penceresinde
> yaptığı scale-out kâr-almaları (+$20.93 @88¢, +$17.09 @92¢) LİKİT fiyatlarda olduğu
> için paper'da da gerçekleşirdi → gerçek kârdı. Yanlışlıkla "hayalî" sanılıp silindi.
> Tüm dosyalar yedekten geri yüklendi (realized 259.16, Watson +$57.90). Ders: dry-run
> satışı "hayalî" sadece paper'ın REDDEDECEĞİ fiyatlarda (0¢) geçerli; likit fiyatta
> yapılan satış paper'da da dolardı → gerçek say.
