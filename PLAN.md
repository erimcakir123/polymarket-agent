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

### PLAN-009: Chart Period Tabs + Adaptive Bucketing
- **Durum**: APPROVED
- **Tarih**: 2026-04-16
- **Öncelik**: P1 (UX scalability; veri bozulması yok)
- **Etki**:
  - `src/presentation/dashboard/static/js/trade_filter.js` (yeni)
  - `src/presentation/dashboard/templates/dashboard.html`
  - `src/presentation/dashboard/static/css/dashboard.css`
  - `src/presentation/dashboard/static/js/dashboard.js`
  - `TDD.md §5.7.7`
- **Açıklama**:
  Total Equity + Per Trade PnL chart'larına 4 period tab (24h/7d/30d/1y) +
  adaptif bucketing (event/hour/day/week) + CSS overflow-x scroll. Total Equity
  tab-altı PnL özeti. "All" kaldırıldı (sınırsız scroll sorunu). Yeni dep yok,
  yalnız presentation katmanı.
- **Detay**: `docs/superpowers/specs/2026-04-16-chart-period-tabs-design.md` + `docs/superpowers/plans/2026-04-16-chart-period-tabs.md`
- **Kabul Kriterleri**:
  - [ ] 4 tab her iki chart'ta görünür, default 30d aktif
  - [ ] Total Equity: 24h event, 7d hourly, 30d daily, 1y weekly bucketing
  - [ ] Per Trade: event-filter yalnız, bucketing yok
  - [ ] Yoğun dilimde yatay scroll görünür, seyrek dilimde scrollsuz
  - [ ] Tab-altı özet Total Equity kartında; Per Trade'de yok
  - [ ] Identity: son nokta = initial + Σ exit_pnl_usdc (period içi)
  - [ ] Tüm browser QA checklist geçer
- **Mimari Uyumluluk**: ✓ Kural 1 (presentation), ✓ Kural 3 (<400 satır), ✓ Kural 6 (magic number yok), ✓ Kural 10 (yeni dep yok)
- **TDD Referansı**: §5.7.7 (güncellenecek)

