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

### PLAN-CLEAN1: graduated_sl + circuit_breaker tam kaldırma (kapalı özellikler)

- **Durum**: PROPOSED (kullanıcı 2026-06-10 silmeyi onayladı; uygulama AYRI oturuma
  ertelendi — kapsam beklenenden geniş çıktı, "çalışanı bozma" önceliği)
- **Tarih**: 2026-06-10
- **Öncelik**: P2 (acil değil — ikisi de kapalı/etkisiz, zarar vermiyor)
- **Etki (haritalandı)**: graduated_sl 24 dosyaya dokunuyor: monitor.evaluate imzası
  (graduated_sl_enabled parametresi) → exit_processor, sim_realistic_replay(+testleri),
  tennis_champion_audit, scripts/_espn_verify_grad_sl.py, 8+ test dosyası, enums
  (ExitReason.GRADUATED_SL), settings/config. circuit_breaker: startup.py restore/save,
  reboot.py state listesi, gate testi (skip), config.
- **DİKKAT**: ExitReason.GRADUATED_SL enum'u ESKİ ARŞİV kayıtlarında geçiyor —
  dashboard/readers arşiv okurken enum değerine ihtiyaç duyabilir; kaldırmadan önce
  reader'ların ham string'le çalıştığı doğrulanmalı (yoksa enum "tarihsel değer" olarak kalır).
- **Adımlar**: (1) reader/arşiv uyumluluk analizi; (2) circuit_breaker önce (küçük);
  (3) graduated_sl: testleri sil → imza zincirini güncelle → suite; (4) reload.
- **Kabul**: suite yeşil + arşiv sekmesi eski graduated_sl exit'lerini hâlâ doğru gösterir.

---

> NOT (2026-06-07): PLAN-DRYRUN-CLEANUP uygulandı AMA **GERİ ALINDI** — hatalıydı.
> Watson moneyline'ı $50'lık (116 pay) gerçek bir kazanandı; dry-run penceresinde
> yaptığı scale-out kâr-almaları (+$20.93 @88¢, +$17.09 @92¢) LİKİT fiyatlarda olduğu
> için paper'da da gerçekleşirdi → gerçek kârdı. Yanlışlıkla "hayalî" sanılıp silindi.
> Tüm dosyalar yedekten geri yüklendi (realized 259.16, Watson +$57.90). Ders: dry-run
> satışı "hayalî" sadece paper'ın REDDEDECEĞİ fiyatlarda (0¢) geçerli; likit fiyatta
> yapılan satış paper'da da dolardı → gerçek say.
