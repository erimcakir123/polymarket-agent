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

### PLAN-010: NHL Score-Based Exit System
- **Durum**: DONE
- **Tarih**: 2026-04-17
- **Öncelik**: P1
- **SPEC**: SPEC-004
- **Etki**: infrastructure (1 yeni) → orchestration (1 yeni, 1 güncelleme) → strategy/exit (1 yeni, 1 güncelleme) → models (2 güncelleme) → config (2 güncelleme)
- **Açıklama**: Hockey maçlarında canlı skor ile A-conf hold kayıplarını azaltmak. 9 trade backtest: -$23 → +$4 (kazançlara sıfır dokunma).

#### Adımlar

**Adım 1 — Config & Model Temeli** (bağımlılık yok)
- [ ] 1a. `config.yaml`'a `score:` ve `exit:` bölümleri ekle
- [ ] 1b. `src/config/settings.py`'ye `ScoreConfig` ve `ExitConfig` Pydantic modelleri ekle
- [ ] 1c. `src/config/sport_rules.py`'ye NHL score exit config key'leri ekle (`late_deficit`, `late_elapsed_gate`, `score_price_confirm`, `final_elapsed_gate`)
- [ ] 1d. `src/models/enums.py`'ye `SCORE_EXIT` ve `CATASTROPHIC_BOUNCE` ExitReason ekle
- [ ] 1e. `src/models/position.py`'ye `catastrophic_watch: bool = False` ve `catastrophic_recovery_peak: float = 0.0` ekle
- [ ] 1f. Mevcut testlerin geçtiğini doğrula (`pytest -q`)

**Adım 2 — Score Client** (Adım 1'e bağlı)
- [ ] 2a. `src/infrastructure/apis/score_client.py` yaz — `MatchScore` dataclass + `fetch_scores(sport_key)` fonksiyonu
- [ ] 2b. Eski projeyi referans oku (Odds API scores endpoint formatı)
- [ ] 2c. Unit testler yaz: parse, API error, boş response
- [ ] 2d. `pytest -q` geçtiğini doğrula

**Adım 3 — Score Exit Kuralları** (Adım 1'e bağlı, Adım 2'den bağımsız)
- [ ] 3a. `src/strategy/exit/score_exit.py` yaz — `check(pos, score_info, elapsed_pct) → ExitSignal | None` (K1-K4, pure fonksiyon)
- [ ] 3b. `src/strategy/exit/catastrophic_watch.py` yaz — `check(pos) → ExitSignal | None` + `tick(pos)` (K5, pure fonksiyon)
- [ ] 3c. Unit testler yaz: 10 score_exit test + 4 catastrophic_watch test
- [ ] 3d. `pytest -q` geçtiğini doğrula

**Adım 4 — Score Enricher** (Adım 1 + 2'ye bağlı)
- [ ] 4a. `src/orchestration/score_enricher.py` yaz — `get_scores_if_due(positions) → dict[cid, score_info]`
- [ ] 4b. Team matching: mevcut `question_parser.py` kullanarak Polymarket question → Odds API team eşleştirme
- [ ] 4c. Rate limit: `match_window_hours` kontrolü, sport_key gruplama
- [ ] 4d. Unit testler yaz: polling zamanlama, gruplama, team matching, unavailable fallback
- [ ] 4e. `pytest -q` geçtiğini doğrula

**Adım 5 — Monitor + Exit Processor Entegrasyonu** (Adım 3 + 4'e bağlı)
- [ ] 5a. `src/strategy/exit/monitor.py` güncelle:
  - A-conf hold dalında market_flip'ten ÖNCE score_exit çağrısı ekle (sadece hockey)
  - Near-resolve + scale-out'tan SONRA, a_hold dalından ÖNCE catastrophic_watch çağrısı ekle (tüm sporlar)
- [ ] 5b. `src/orchestration/exit_processor.py` güncelle:
  - `run_light()` içinde score_enricher periyodik çağrı
  - `score_info` dict'ini `evaluate(pos, score_info=...)` olarak geçir
- [ ] 5c. Entegrasyon testleri yaz: score_exit override market_flip, fallback to market_flip
- [ ] 5d. `pytest -q` geçtiğini doğrula

**Adım 6 — TDD/Doc Güncelleme + Final Doğrulama**
- [ ] 6a. TDD §6.9 tablosunu güncelle (hockey score_exit eklendi)
- [ ] 6b. TDD §7.2 NHL satırını güncelle
- [ ] 6c. `positions.json` backward compat doğrula (bot'u başlat, mevcut pozisyonlar yüklensin)
- [ ] 6d. Tüm testler geçiyor: `pytest -q`
- [ ] 6e. SPEC-004 durumunu IMPLEMENTED yap ve sil

#### Adım Bağımlılık Grafiği
```
Adım 1 (config/model temeli)
  ├── Adım 2 (score client)
  │     └── Adım 4 (enricher) ──┐
  └── Adım 3 (score exit rules) ──┤
                                   └── Adım 5 (entegrasyon)
                                         └── Adım 6 (doc + final)
```
Adım 2 ve 3 paralel çalışabilir.

#### Kabul Kriterleri
- [ ] 15 yeni test geçiyor
- [ ] Mevcut testler kırılmadı
- [ ] Tüm eşikler config'den okunuyor (magic number yok)
- [ ] Yeni dosyalar <400 satır
- [ ] Katman kuralları korunuyor (infra → orch → strategy)
- [ ] `positions.json` eski formatta yükleniyor (backward compat)
- [ ] TDD §6.9 ve §7.2 güncellendi
- [ ] SPEC-004 silindi

#### Mimari Uyumluluk
- ARCH K1 (katman): ✓ infra → orch → strategy
- ARCH K2 (domain I/O): ✓ score_exit.py pure, I/O yok
- ARCH K3 (dosya boyutu): ✓ tümü <100 satır tahmini
- ARCH K6 (magic number): ✓ tüm eşikler config'den
- ARCH K7 (P_YES): ✓ dokunulmuyor
- ARCH K11 (test): ✓ 15+ test planlandı

#### TDD Referansı
- §6.9 (A-conf hold) — score_exit dalı ekleniyor
- §6.8 (graduated SL) — score_info otomatik aktif oluyor (yan etki)
- §7.2 (sport rules) — NHL satırı güncelleniyor

