# CLAUDE.md
> Polymarket autonomous trading bot — geliştirme asistanı kuralları.
> Proje sahibi teknik değil. Kritik kararlar onay bekler. Türkçe iletişim.

---

## DOSYA HARİTASI

| Dosya | Ne zaman okunur | İçerik |
|---|---|---|
| `ARCHITECTURE_GUARD.md` | Her edit/write öncesi — zorunlu | Mimari kurallar, katman yapısı |
| `DECISIONS.md` | Threshold değişince / "neden bu sayı" sorusunda | Kalibrasyon değerleri, "neden" notları |
| `PRD.md §2` | Iron rule sorusunda | event-guard, P(YES), circuit breaker |
| `config.yaml` | Config değeri gerekince | Tüm sayısal config |
| `TODO.md` | Kullanıcı "todoya yaz/bak" deyince | Ertelenmiş işler |
| `PLAN.md` | Plan yazılacak/okunacaksa | In-flight planlar |
| `src/config/_sport_aliases.py` | sport_rules.py kullanır | Odds API → internal sport tag aliases |
| `src/domain/matching/team_resolver.py` | NBA edge enricher team ID ihtiyacında | ESPN team ID static dict + resolve_nba_espn_id() |

Başka dosyayı kullanıcı söylemeden okuma.

---

## EDIT / WRITE ÖNCESI — ZORUNLU SELF-CHECK

Her edit veya write tool'u kullanmadan önce şunu yaz, sonra devam et:

> `ARCH: katman✓ domain-IO-yok✓ <400satır✓ magic-number-yok✓ P(YES)-anchor✓ test-var✓`

Self-check yazılmadan edit/write yapma. Kullanıcı görmezse dur, yaz, devam et.

---

## MİMARİ KURALLAR (özet — tam liste ARCHITECTURE_GUARD.md'de)

```
Presentation → Orchestration → Strategy → Domain → Infrastructure

- Alt katman üst katmanı çağıramaz. Katman atlama yasak.
- Domain'de I/O yasak (requests, file, socket, os.path, pathlib)
- Tek dosya max 400 satır. Aşınca böl.
- Tek class max 10 public method, max 5 constructor param.
- Magic number yasak — her değer config.yaml'dan gelir.
- utils / helpers / misc dizini açma.
- Sessiz hata yutma yasak (bare except: pass)
- God object / god function yasak.
```

**Veri kuralları:**
- P(YES) her zaman anchor — direction-adjusted asla saklanmaz, asla yazılmaz.
- Event-level guard: aynı event_id'ye iki pozisyon açılamaz.
- Exposure cap + circuit breaker her zaman aktif, devre dışı bırakılamaz.

**Kod stili:**
- Python 3.12+, type hints zorunlu (tüm imzalar)
- Enum'lar str(Enum) mixin (JSON serializable)
- Docstring sadece karmaşık mantık için

**Test:**
- Domain fonksiyonları: unit test zorunlu
- Strategy karar noktaları: unit test zorunlu
- `test_{ne}_{senaryo}_{beklenen}` isimlendirme
- Test olmadan merge yasak

---

## DRİFT KORUMA TABLOSU

X değiştiğinde şunları da güncelle — eksik = veri tutarsızlığı.

| Ne değişirse | Zorunlu güncelleme |
|---|---|
| Threshold / kalibrasyon değeri | `config.yaml` + `DECISIONS.md` + ilgili test assertion'ları |
| Yeni spor eklendi | `config.yaml active_sports` + `DECISIONS.md` (sport section) + exit dosyası + test |
| Spor çıkarıldı | `config.yaml active_sports` + `config.yaml slug_prefix_sport_map` + `sport_rules.py` + score adapter + DECISIONS.md |
| Exit kuralı değişti | `DECISIONS.md` (rationale güncelle) + test |
| Iron rule değişti | `PRD.md §2` + `ARCHITECTURE_GUARD.md` |
| Yeni dosya eklendi | Katmanı `ARCHITECTURE_GUARD.md`'ye göre doğrula, `DECISIONS.md`'e kayıt gerekmez |
| Restart protokolü değişti | Bu dosyanın "Restart Protokolü" bölümü |
| Score API kaynağı değişti | `DECISIONS.md` (score source section) + score_enricher adapter |

---

## SPORT YÖNETİMİ

**Aktif spor eklemek için:**
1. `config.yaml → entry.active_sports` listesine ekle
2. `DECISIONS.md` → o spor için threshold'ları belgele
3. `src/strategy/exit/` altına exit kuralını yaz
4. Testini yaz
5. Dry-run'da doğrula — `pytest -q` geçmeli

**Sport hazır olmadan `active_sports`'a girme.**
Scanner bulur, matching çalışır, entry gate'de `active_sports` kontrolünde takılır.

```yaml
# config.yaml
entry:
  active_sports: []   # başlangıçta boş, hazır oldukça ekle
```

---

## KURAL / THRESHOLD DEĞİŞİKLİĞİ PROTOKOLÜ

1. İş niyetini somut parametreye çevir
2. Tek satırda doğrulat: *"X → Y yapıyorum, doğru mu?"* — onay alınmadan devam etme
3. Grep: `config.yaml`, `src/`, `tests/`, `DECISIONS.md`
4. Etkilenen dosya + satır listesini göster, onaylat
5. Tek seferde uygula — yarım bırakma yasak
6. `pytest -q` → geçmeli, grep'te eski değer kalmamalı

Grep'te beklenmedik dosya çıkarsa → dur, kullanıcıya sor.

---

## MİMARİ DEĞİŞİKLİK PROTOKOLÜ

`PLAN.md`'ye yaz → onay al → uygula → `DECISIONS.md` güncelle → `PLAN.md`'den sil.

Mimari değişiklik = katman ekleme/kaldırma, dizin yapısı, yeni pattern.
Mimari değişiklik DEĞİL = yeni dosya (mevcut dizine), bug fix, feature.

---

## YENİ DOSYA EKLEME

1. `src/` dizin yapısını kontrol et (Glob)
2. Katmanını belirle (5-katman kuralı)
3. Belirsizse → `PLAN.md`'ye yaz, onay al
4. `utils/`, `helpers/`, `misc/` yasak

---

## RESTART PROTOKOLÜ

"Restart" deyince sor: **Reload mu, Reboot mu?**

**Reload** — kod güncellenir, veri korunur.

**Reboot** — onay zorunlu. Sıfırlananlar:
- `logs/positions.json`
- `logs/trade_history.jsonl`
- `logs/equity_history.jsonl`
- `logs/circuit_breaker_state.json`
- `logs/stock_queue.json`
- `logs/skipped_trades.jsonl`

**Asla silinmez:**
- `logs/archive/` (exits.jsonl, score_events.jsonl, match_results.jsonl) — audit trail
- `logs/bot.log` — audit trail

---

## TRADE SİLME / DÜZELTME PROTOKOLÜ

Sırayla, hepsini yap — eksik dosya = veri tutarsızlığı:

| # | Dosya | İşlem |
|---|---|---|
| 1 | `logs/positions.json` | Açık pozisyonsa sil, `realized_pnl` düzelt |
| 2 | `logs/trade_history.jsonl` | İlgili satırı sil |
| 3 | `logs/equity_history.jsonl` | Timestamp sonrası retroaktif düzelt |
| 4 | `logs/positions.json → high_water_mark` | Yeniden hesapla |
| 5 | `logs/circuit_breaker_state.json` | PnL toplamlarından çıkar |
| 6 | `logs/archive/*` | **DOKUNMA** |

Doğrulama: `SUM(trade_history pnl) == positions.json realized_pnl`

---

## YASAKLAR

- Edit/write öncesi self-check atlamak
- Domain'de I/O
- 400+ satır dosya oluşturmak
- Magic number kullanmak
- Test yazmadan bırakmak
- Onaysız mimari değişiklik
- `utils/helpers/misc` dizini açmak
- P(YES) dışında olasılık saklamak
- Sessiz hata yutmak (bare `except: pass`)
- Scope creep (istenmeyeni ekleme)
- Eski projeden kod kopyalamak — referans okunur, taze yazılır
