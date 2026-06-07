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

*Şu an aktif plan yok — boş duruyor.*

> NOT (2026-06-07): PLAN-DRYRUN-CLEANUP uygulandı AMA **GERİ ALINDI** — hatalıydı.
> Watson moneyline'ı $50'lık (116 pay) gerçek bir kazanandı; dry-run penceresinde
> yaptığı scale-out kâr-almaları (+$20.93 @88¢, +$17.09 @92¢) LİKİT fiyatlarda olduğu
> için paper'da da gerçekleşirdi → gerçek kârdı. Yanlışlıkla "hayalî" sanılıp silindi.
> Tüm dosyalar yedekten geri yüklendi (realized 259.16, Watson +$57.90). Ders: dry-run
> satışı "hayalî" sadece paper'ın REDDEDECEĞİ fiyatlarda (0¢) geçerli; likit fiyatta
> yapılan satış paper'da da dolardı → gerçek say.
