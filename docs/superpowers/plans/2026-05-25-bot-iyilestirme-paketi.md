# Bot İyileştirme Paketi — 2026-05-25 (Yarın için Plan)

> Bu plan SPEC-Z fix turunun ardından kalan yarım/açık konuları topluyor. Her task ayrı brainstorming → spec → TDD geçişi gerektirir.

---

## Task A: Otomatik Archive Trigger Tespiti

**Problem:** `archive_audit_logs` her ~1 saatte bir tetikleniyor (DECISIONS satır 1137 "TODO investigate"). Kim çağırıyor bilinmiyor. SPEC-Z7 yan etkiyi düzeltti (audit kopyalanıyor, silinmiyor) ama trigger hâlâ aktif.

**Yapılacak:**
1. Process tree audit — bot başlatan parent PID'leri kaydet (PID 12812 gibi)
2. `scripts/reboot.py` import edenleri grep'le (cron benzeri çağrılar)
3. Windows Task Scheduler tam dökümü (`schtasks /Query /V /FO CSV`)
4. Eğer bot içinde çağrı yoksa: agent.py'a bir mtime-watcher logger ekle (kim ne zaman archive_audit_logs çağırdı izle)

**Etki:** Trigger'ı bulunca **kaldır** veya **kontrollü hale getir** (kullanıcının onayladığı zamanlarda).

**Tahmini süre:** 1-2 saat.

---

## Task B: MLB Bimodal Analizi + SL Replay (Geriye Dönük)

**Soru (kullanıcının):** MLB'de tek skor değişiminden bot çok mu kaybediyor (bimodal mi)? SL oranını sıkılaştırsak (%30 → %25 veya %20) net realized P&L ne olurdu?

**Yapılacak:**
1. **Veri toplama:** Son 7 günlük trade_history archive'lerinden TÜM MLB exit'leri çıkar (stop_loss/graduated_sl reason'lı)
2. **Inning analizi:** Bot.log'dan score_enricher kayıtlarını eşleştir — exit anındaki inning + skor (eğer varsa)
3. **Bimodal görsel:** entry_price → exit_price serisi histogram. Eğer çok düşük (örn 0.20-0.30) ve çok yüksek (0.70-0.80) iki tepe varsa → bimodal kanıtlandı
4. **SL replay simülasyonu:**
   - Mevcut: `risk.stop_loss_pct: 0.30` → entry × 0.70'te exit
   - %25 replay: entry × 0.75'te exit varsayım (gerçek price serisi yoksa proxy)
   - %20 replay: entry × 0.80'de exit
   - Her senaryoda toplam realized hesapla
5. **Karar tablosu:** %30 / %25 / %20 için kayıp azalma + kâr kaçırma riski

**Etki:** Eğer %25 net realized'i artırıyorsa config değişikliği önerilir (brainstorm + spec).

**Tahmini süre:** 2-3 saat. SL kararını kullanıcı verecek (config değişikliği = onay gerek).

---

## Task C: SPEC-Z5 — ESPN match_live Refresh (Yarım Kaldı)

**Problem:** Tenis dışı sporlarda (MLB/NBA/WNBA) bot pozisyonun `match_live` alanını ESPN'den güncellemiyor. Polymarket `event.live` gecikmesinde yanlış mantık tetiklenebilir (near_resolve guard, vs.).

**Yapılacak:**
1. `ScoreEnricher.refresh_match_status` metodu (kodu yazılmış ama commit yok)
2. `Agent.run` light cycle'da çağrı (kod yazılmış ama commit yok)
3. Test: `ScoreEnricher.refresh_match_status` için unit test
4. Reload (kullanıcı onayıyla) ile bot'a yansıt

**Etki:** Pozisyonların match_live alanı her light cycle'da ESPN'den tazelenir, dashboard LIVE rozeti tutarlı olur (SPEC-Z4'ün backend tamamlayıcısı).

**Tahmini süre:** 30 dk (kod yazılmış, sadece test + commit + reload).

---

## Task D: Dashboard Widget Tutarlılığı

**Problem:**
- **Peak Balance** state'te $1000 sabit, gerçek peak yansımıyor
- **Balance widget alt satırı** ("5 open · $821.62" gibi) yanlış formül (peak ile karışıyor)
- **Realized P&L** trade_history bazlı, positions.json `realized_pnl` ile uyumsuzluk ($22 fark)

**Yapılacak:**
1. Peak balance bot tarafından güncellensin (her cycle equity_history yazılırken max'i takip et)
2. Balance widget alt satırı "open positions × ortalama" değil, gerçek "invested value" göstersin
3. Realized hesap source tek kaynak (ya trade_history ya positions.json) — DECISIONS karar

**Tahmini süre:** 1 saat.

---

## Task E: SPEC-X Cleanup Sonrası Tutarsızlık

**Problem:** Trade_history toplam realized ($21.82) ≠ positions.json realized_pnl ($26+). 13 "orphan position" warning (SPEC-Z6 ile kısmen çözüldü ama mevcut fark duruyor).

**Yapılacak:**
1. `_reconcile_realized_pnl` startup fonksiyonu — eski state ile yeni trade_history arasındaki tutarsızlığı yakala + tek kaynaktan al
2. Test: cleanup + reload sonrası realized hesabı doğru kalmalı

**Tahmini süre:** 1 saat.

---

## Öncelik Sırası

| # | Task | Aciliyet | Süre |
|---|---|---|---|
| 1 | A (archive trigger) | YÜKSEK — Z7 yarım çözüm, kaynak hâlâ aktif | 1-2h |
| 2 | C (ESPN refresh) | YÜKSEK — kod yazılmış, commit/test yeter | 30dk |
| 3 | B (MLB bimodal + SL replay) | ORTA — analiz, karar sonucu config değişikliği | 2-3h |
| 4 | D (Dashboard tutarlılığı) | DÜŞÜK — kozmetik | 1h |
| 5 | E (realized reconcile) | DÜŞÜK — mevcut state OK, gelecek için | 1h |

---

## Notlar

- **Her task için brainstorming → spec → TDD** akışı zorunlu (CLAUDE.md kuralı)
- **ARCH_GUARD** her Edit/Write öncesi self-check
- **Reload izni** her seferde kullanıcıdan ayrıca alınır (memory kuralı)
- **Drift/dead code** her commit öncesi grep'le kontrol edilir
