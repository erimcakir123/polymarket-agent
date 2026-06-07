# SPEC — Zararla-çıkış sonrası tekrar-giriş yasağı + test verisi temizliği

**Tarih:** 2026-06-07
**Durum:** DRAFT (onay sonrası plana dönüşür)
**Bağlam:** Basketbol model kaldırma sonrası (SPEC-Z21) bahisçi-konsensüsü
moddayken canlı session'da bulunan iki kusur.

---

## Kök neden (kanıtlanmış)

1. **Tekrar-giriş ("düşen bıçağı tutma"):** Bot bir markete girip canlı maçta
   stop-loss ile (`exit_reason="partial_sl"`) çıktıktan sonra, **aynı condition_id'ye
   dakikalar içinde tekrar giriyor.** Piyasa fiyatı aleyhe düştükçe bot, yavaş
   güncellenen bahisçi çapasına göre "fırsat büyüdü" sanıp tekrar alıyor ve kaybı
   katlıyor.
   - Kanıt: `wnba-ind-nyl-2026-06-06` moneyline — 1. pozisyon −$10.56, kapanıştan
     6 dk sonra 2. giriş −$24.93. Aynı desen `atp-poling-ilagan` teniste de var
     (1. −$9.77, tekrar +$16.88).
   - Mevcut `cooldown` (`src/domain/risk/cooldown.py`) bunu yakalayamaz: **portföy
     geneli** + **art arda 3 kayıp** eşikli; markete-özel ve ilk-zarardan değil.

2. **Kontaminasyon:** Bu session'da, bugün getirilen kurallarla (max_entry 0.75,
   tekrar-giriş yasağı) **hiç açılmayacak** 5 işlem var. Bunlar kâr/zarar fark
   etmeksizin test sonucunu kirletiyor.

---

## Kapsam (iki bağımsız iş)

### İŞ A — Yeni production kuralı: tekrar-giriş yasağı
### İŞ B — Tek-seferlik veri temizliği (dashboard)

---

## İŞ A — Tekrar-giriş yasağı

### Davranış
- Bir pozisyon **net realized PnL < 0** ile (kısmi satışlar + son çıkış toplamı)
  tamamen kapandığında, o `condition_id` "bu session'da zararla kapandı" olarak
  işaretlenir.
- İşaretli bir `condition_id` için **yeni giriş engellenir** (kâr eden çıkışlar
  engellemez — gerekmiyor: kârlı çıkış maç bitince oluyor, market kalmıyor; ayrıca
  0.75 cap zaten keser).
- Kapsam = **tam market (condition_id)**, event değil. Aynı maçın başka marketi
  (moneyline kaybetti → totals) etkilenmez.

### Mimari yerleşim (ARCH_GUARD uyumlu)
- **Kayıp listesi (state):** `set[str]` — domain `PortfolioManager` içinde saf state
  (`closed_at_loss: set[str]`). I/O yok. Pozisyon kapanışında
  (`remove_position`, net realized < 0) eklenir.
- **Reload dayanıklılığı:** Bot açılışında liste, mevcut okuyucularla
  (`trade_events.jsonl` replay → net realized < 0 olan condition_id'ler) yeniden
  kurulur. Okuma orchestration/infra'da; domain'e hazır set verilir. **Reboot'ta**
  defter arşivlenir → liste doğal sıfırlanır (yeni session).
- **Guard fonksiyonu:** `src/orchestration/entry_guards.py` içine
  `check_loss_reentry(deps, market) -> bool` (mevcut `check_duplicate_condition`
  kalıbının aynısı). `True` → girişi blokla, `skip_reason="loss_reentry_blocked"`.
- **Hook noktası:** `src/orchestration/entry_processor.py::_execute_entry`,
  `executor.place_order` öncesi diğer guard'ların yanı.
- **Config:** `config.yaml > risk > block_reentry_after_loss: true` (varsayılan açık;
  magic yok, kapatılabilir).

### Skip gözlemlenebilirliği
- Bloklanan giriş `skipped_trades.jsonl`'a `loss_reentry_blocked` sebebiyle yazılır
  (mevcut skip-log kalıbı).

### Testler (TDD — yazılmadan kod yok)
- `test_check_loss_reentry_condition_closed_at_loss_blocks` → True
- `test_check_loss_reentry_condition_closed_at_profit_allows` → False
- `test_check_loss_reentry_never_traded_allows` → False
- `test_portfolio_marks_condition_closed_at_loss_on_negative_exit`
- `test_portfolio_does_not_mark_on_positive_exit`
- Reload-rebuild: `test_loss_set_rebuilt_from_trade_events_on_startup`

---

## İŞ B — Veri temizliği

### Silinecek işlemler (5) — onaylı: "tüm session, tutarlı"
| Spor | slug | Sebep | PnL |
|---|---|---|---|
| tenis | atp-poling-ilagan-2026-06-06 (1. giriş) | 0.75 üstü (0.77) | −$9.77 |
| tenis | atp-poling-ilagan-2026-06-06 (tekrar giriş) | tekrar-giriş | +$16.88 |
| tenis | wta-vekic-monnet-2026-06-06-set-handicap-home-1pt5 | 0.75 üstü (0.79) | +$2.94 |
| wnba | wnba-ind-nyl-2026-06-06 (tekrar giriş, 2. entry) | tekrar-giriş | −$24.93 |
| wnba | wnba-wsh-atl-2026-06-06 (moneyline) | 0.75 üstü (0.81) | +$5.56 |

> Not: `poling-ilagan` ve `ind-nyl` moneyline aynı condition_id altında 2 giriş
> içeriyor. Temizlikte poling-ilagan'ın **her iki** girişi (0.75 üstü + tekrar) gider;
> ind-nyl moneyline'da **sadece 2. giriş** (tekrar) gider, 1. giriş kalır. ind-nyl
> **totals** ayrı market, dokunulmaz.

### Nereden silinir
- **`logs/audit/trade_events.jsonl`:** hedef işlemlerin tüm event'leri
  (entry + partial + final) çıkarılır. Bu dosya dashboard'da realized PnL toplamını,
  işlem listesini ve exited/pozisyon sekmesini besler
  (`computed.realized_pnl_from_trades`) → otomatik temizlenir.
- **`logs/audit/equity_history.jsonl`:** eğri yeniden hesaplanır — silinen işlemlerin
  realized/invested/bankroll izi çıkarılır.
  - **Kabul edilen sınır (onaylı):** işlemler açıkken oluşan **anlık (unrealized)
    titreme** birebir silinemeyebilir (o anki canlı fiyatlar kayıtlı değil).
    Realized çizgisi + toplamlar + nihai bakiye **tam doğru** olur.

### Mimari (ARCH_GUARD uyumlu)
- **Saf dönüşüm fonksiyonu (test edilir):** `(events, remove_condition_or_entry_keys)
  -> cleaned_events` ve `(cleaned_events, initial_bankroll) -> rebuilt_equity`.
  Saf, I/O yok. Mevcut `event_replay` / equity hesap mantığıyla hizalı.
- **Script (I/O orchestrasyonu):** `scripts/` altında tek-seferlik temizlik scripti:
  1. İki dosyanın da **yedeğini** al (`.bak.<ts>`).
  2. Oku → saf fonksiyonu çağır → yaz.
  3. **Doğrula:** silinen event sayısı, yeni realized toplamı, kalan işlem sayısı
     raporlanır.
- "Sadece 2. giriş" gibi seçimler için condition_id + entry_timestamp ile event grubu
  hedeflenir (aynı condition_id'nin tüm event'leri değil).

### Testler
- `test_cleanup_removes_targeted_entry_group_keeps_first_entry` (ind-nyl: 1. kalır,
  2. gider)
- `test_cleanup_removes_full_market_when_both_entries_targeted` (poling-ilagan)
- `test_rebuilt_realized_pnl_excludes_removed_trades`
- `test_backup_created_before_write`

---

## Yapılmayacaklar (YAGNI / scope)
- Mevcut `cooldown` mekanizması değiştirilmez (ayrı sorumluluk; sadece yetersizliği
  not edildi).
- Event-level (aynı maçın tüm marketleri) yasak EKLENMEZ — sadece condition_id.
- Kârlı-çıkış sonrası tekrar-giriş yasağı EKLENMEZ (gereksiz, kanıtlandı).
- Geçmiş arşiv dosyalarına (`*.archive.*`) dokunulmaz — yalnız canlı session.

---

## DECISIONS.md etkisi (uygulama sonrası)
- §A'ya kısa kural notu + §B'ye SPEC-Z24 (tekrar-giriş yasağı) log girişi.
- config.yaml `block_reentry_after_loss` notu.
