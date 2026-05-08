# SPEC — Spesifikasyonlar

> Bu dosya aktif teknik spesifikasyonları içerir.
> Bir spec entegre edilip onaylandıktan sonra bu dosyadan **SİLİNİR**.
> Sadece aktif, henüz koda dönüşmemiş spec'ler burada durur.

---

## Nasıl Kullanılır

### Spec Ekleme
```
1. Bir özellik veya modül için detaylı spec yaz (aşağıdaki formata uy)
2. Durum: DRAFT
3. Review + onay → durum: APPROVED
4. Kod yazılıp test edildikten sonra → durum: IMPLEMENTED → sil
```

### Spec Formatı
```
### SPEC-XXX: [Modül/Özellik adı]
- **Durum**: DRAFT | APPROVED | IMPLEMENTED
- **Tarih**: YYYY-MM-DD
- **İlgili Plan**: PLAN-XXX
- **Katman**: domain | strategy | infrastructure | orchestration | presentation
- **Dosya**: src/katman/modul.py

#### Amaç
Modülün ne yaptığı, tek cümle.

#### Girdi/Çıktı
- Girdi: ...
- Çıktı: ...

#### Davranış Kuralları
1. ...
2. ...

#### Sınır Durumları (Edge Cases)
- ...

#### Test Senaryoları
- ...
```

---

## Aktif Spesifikasyonlar

---

## SPEC-B: ESPN Score Client Wire (Faz 2)

> **Tarih:** 2026-05-08
> **Durum:** DRAFT — onay + SPEC-A tamamlandıktan sonra başlanır
> **Referans:** `pre-rollback-2026-05-04` tag'inde `docs/superpowers/specs/2026-04-17-espn-score-client-wire-design.md` (SPEC-005)
> **Bağımlılık:** SPEC-A tamamlanmış olmalı (sessiz bug yok ki ESPN entegrasyonu temiz çıksın)

### Amaç

3, 4, 5 numaralı sorunları çözen ESPN score client'ı 16 Nisan baseline'a getir:

- **3**: `evaluate(pos)` çağrısına `score_info` parametresi geçilsin (skor-aware exit guard'lar aktifleşsin: never_in_profit, hold_revocation, graduated_sl)
- **4**: `match_start_iso` parse edilemezse ESPN'den canlı durum (period, clock, in-progress) çekip elapsed_pct türet
- **5**: Scanner'da magic 8.0 → config'e + bozuk match_start için ESPN game state ile filter

### Kapsam Önizleme (detaylı SPEC-A onayından sonra yazılır)

- `src/infrastructure/apis/espn_client.py` — pre-rollback'ten migrate (382 satır, NBA/MLB/NHL/Soccer scoreboards)
- `src/orchestration/score_enricher.py` — sport-dispatch (espn primary, odds API fallback)
- `src/strategy/exit/monitor.py:evaluate` — score_info parametresi entry-processor'da populate edilsin
- Cache stratejisi: TTL 30s (light cycle ile uyumlu)
- Sport coverage: NBA, MLB, NHL (futbol kapsam dışı çünkü genel olarak futbol kapalı)

### Bu SPEC Şu An Yazılmadı

SPEC-A onayından sonra SPEC-B detaylandırılacak. Kapsam daha büyük (yeni infrastructure katmanı + 4-6 dosya + 20-30 yeni test) — kendi PLAN'ı olacak.

---

## SPEC-C: 3-Way Bookmaker Sanity (LOW PRIORITY — Bekliyor)

> **Tarih:** 2026-05-08
> **Durum:** PARKLA — futbol kapatılana kadar etkisiz

Soccer için draw outcome eksik bookmaker silent skip + 3-way prob sum sanity (0.95-1.05) yok. Futbol açılmadan etkisiz, **futbol açılmadan ÖNCE** bu spec yazılır.
