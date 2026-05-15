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



