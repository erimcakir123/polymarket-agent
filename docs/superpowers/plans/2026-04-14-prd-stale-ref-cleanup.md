# PRD Stale TDD Reference Cleanup Plan

> **For agentic workers:** Use superpowers:executing-plans to implement. Steps use checkbox (`- [ ]`) syntax.

**Goal:** PRD.md'deki 11 adet "silinmiş TDD bölümüne" referansı düzelt. Her referans ya tamamen silinir ya da geçerli bir bölüme/koda yönlendirilir.

**Architecture:** Tek dosya değişir (PRD.md). 11 surgical Edit. Kod/TDD/config dokunulmaz.

**Dependency:** Önceki TDD refactor (Faz A+B+C) tamamlandıktan sonra yapılır. PRD'nin TDD referansları artık dangling.

---

## File Structure

**Değişen:** `PRD.md` — 11 satır/blok güncellenir
**Değişmeyen:** TDD, CLAUDE, config, src, tests

---

## Task 1: PRD.md stale ref cleanup (11 edit)

**Files:**
- Modify: `PRD.md`

### Edit 1: Satır 23 — §5.2 stale

- [ ] Edit:

`old_string`:
```
Olasılık her zaman P(YES) olarak saklanır. BUY_YES de BUY_NO da olsa, `anchor_probability = P(YES)` değişmez. Yön ayarlaması karar mantığında yapılır, saklama yapılmaz. (bkz. ARCHITECTURE_GUARD Kural 7, TDD §5.2)
```

`new_string`:
```
Olasılık her zaman P(YES) olarak saklanır. BUY_YES de BUY_NO da olsa, `anchor_probability = P(YES)` değişmez. Yön ayarlaması karar mantığında yapılır, saklama yapılmaz. (bkz. ARCHITECTURE_GUARD Kural 7)
```

### Edit 2: Satır 45 — §4 stale

- [ ] Edit:

`old_string`:
```
Heavy cycle içinde light cycle interleave eder (heavy uzun sürerse light yine tetiklenir). Gece modunda (UTC 08-13) heavy 60 dk'ya uzar. (bkz. TDD §4)
```

`new_string`:
```
Heavy cycle içinde light cycle interleave eder (heavy uzun sürerse light yine tetiklenir). Gece modunda (UTC 08-13) heavy 60 dk'ya uzar.
```

### Edit 3: Satır 75 — §9 stale

- [ ] Edit:

`old_string`:
```
1. **Scan**: `scanner.py` Polymarket Gamma'dan `allowed_sport_tags` filtreli market'ler çeker (TDD §9).
```

`new_string`:
```
1. **Scan**: `scanner.py` Polymarket Gamma'dan `allowed_sport_tags` filtreli market'ler çeker (bkz. `config.yaml` scanner bölümü).
```

### Edit 4: Satır 110 — §3.4 + §9 stale

- [ ] Edit:

`old_string`:
```
Bot Polymarket Gamma API'dan canlı market'leri keşfeder. `allowed_sport_tags` filtresi uygular. Max `max_markets_per_cycle=300` limitiyle sınırlı. (bkz. TDD §3.4, §9 scanner config)
```

`new_string`:
```
Bot Polymarket Gamma API'dan canlı market'leri keşfeder. `allowed_sport_tags` filtresi uygular. Max `max_markets_per_cycle=300` limitiyle sınırlı. (bkz. `config.yaml` scanner bölümü, `src/orchestration/scanner.py`)
```

### Edit 5: Satır 116 — §11 stale (§6.4 korunur)

- [ ] Edit:

`old_string`:
```
`strategy/entry/gate.py` giriş kararını orchestrate eder. 4 entry stratejisi: normal, early_entry (6+ saat öncesi), volatility_swing (düşük fiyatlı underdog), consensus (bookmaker+market aynı favori). Her strateji edge + confidence + guards'tan geçer. (bkz. TDD §6.4, §11 Faz 3 ve Faz 6)
```

`new_string`:
```
`strategy/entry/gate.py` giriş kararını orchestrate eder. 4 entry stratejisi: normal, early_entry (6+ saat öncesi), volatility_swing (düşük fiyatlı underdog), consensus (bookmaker+market aynı favori). Her strateji edge + confidence + guards'tan geçer. (bkz. TDD §6.4)
```

### Edit 6: Satır 122 — §8 stale

- [ ] Edit:

`old_string`:
```
`executor.py` 3 modda çalışır: `dry_run` (log-only), `paper` (mock fills), `live` (gerçek CLOB emri). Her emir trade log'a JSONL formatında yazılır. (bkz. TDD §8)
```

`new_string`:
```
`executor.py` 3 modda çalışır: `dry_run` (log-only), `paper` (mock fills), `live` (gerçek CLOB emri). Her emir trade log'a JSONL formatında yazılır. (bkz. `src/infrastructure/executor.py`)
```

### Edit 7: Satır 125 — §4 stale

- [ ] Edit:

`old_string`:
```
3 katmanlı izleme: WS tick (anlık), Light cycle (5 sn), Heavy cycle (30 dk). Pozisyon durumu JSON store'da tutulur, dashboard anlık okur. (bkz. TDD §4)
```

`new_string`:
```
3 katmanlı izleme: WS tick (anlık), Light cycle (5 sn), Heavy cycle (30 dk). Pozisyon durumu JSON store'da tutulur, dashboard anlık okur.
```

### Edit 8: Satır 128 — §5.4 stale (§6.6-§6.14 korunur)

- [ ] Edit:

`old_string`:
```
Çıkış kararı birden fazla mekanizmanın değerlendirmesiyle verilir: flat SL, graduated SL, scale-out, never-in-profit, market_flip, near-resolve, hold_revoked, ultra_low_guard, circuit_breaker, manual. İlk tetiklenen sinyal uygulanır. Tam liste ve öncelik sırası TDD §5.4 ExitReason enum + §6.6–§6.14'te. (bkz. TDD §5.4)
```

`new_string`:
```
Çıkış kararı birden fazla mekanizmanın değerlendirmesiyle verilir: flat SL, graduated SL, scale-out, never-in-profit, market_flip, near-resolve, hold_revoked, ultra_low_guard, circuit_breaker, manual. İlk tetiklenen sinyal uygulanır. Tam liste ve öncelik sırası TDD §6.6–§6.14'te; ExitReason enum `src/models/` altında.
```

### Edit 9: Satır 131 — §11 stale

- [ ] Edit:

`old_string`:
```
3 sunum kanalı: Flask dashboard (localhost:5050), Telegram bildirim (entry/exit/CB), JSONL trade log (audit). (bkz. TDD §11 Faz 7)
```

`new_string`:
```
3 sunum kanalı: Flask dashboard (localhost:5050), Telegram bildirim (entry/exit/CB), JSONL trade log (audit).
```

### Edit 10: Satır 150 — §3.5.1 stale

- [ ] Edit:

`old_string`:
```
Teknik detaylar: TDD §3.5.1 Dashboard UI Spec.
```

`new_string`:
```
Teknik detaylar: `src/presentation/dashboard/` kod tabanı.
```

### Edit 11: Satır 163 — §12 stale

- [ ] Edit:

`old_string`:
```
- WebSocket disconnect → 30 sn içinde reconnect (TDD §12)
```

`new_string`:
```
- WebSocket disconnect → 30 sn içinde reconnect
```

### Edit 12: Satır 215 — §9 stale

- [ ] Edit:

`old_string`:
```
- Allowed sport_tags: `baseball_*`, `basketball_*`, `icehockey_*`, `americanfootball_ncaaf|cfl|ufl`, `tennis_*` (dinamik), `golf_lpga_tour|liv_tour` (TDD §9)
```

`new_string`:
```
- Allowed sport_tags: `baseball_*`, `basketball_*`, `icehockey_*`, `americanfootball_ncaaf|cfl|ufl`, `tennis_*` (dinamik), `golf_lpga_tour|liv_tour` (bkz. `config.yaml` scanner bölümü)
```

---

## Task 2: Doğrulama

**Files:** (yok — sadece kontrol)

- [ ] **Stale ref taraması**

Run: `grep -nE "TDD §(1|2|3|4|5|8|9|10|11|12)[^0-9]" PRD.md`

Expected: Boş (hiç eşleşme). §6 ve §7 referansları kalır, bunlar geçerli.

- [ ] **Geçerli ref spot-check**

Run: `grep -nE "TDD §(6|7)" PRD.md`

Expected: Satır 26 (§6.4), 75 (→kaldırıldı ama §6'da değişmedi), 91-95 (§6.8-§6.13), 113 (§6.1), 116 (§6.4), 119 (§6.5), 128 (§6.6-§6.14) görünür.

- [ ] **Test**

Run: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m pytest -q`

Expected: `595 passed`

- [ ] **Özet rapor**

- Değişen dosya: `PRD.md`
- Silinen/düzeltilen stale ref sayısı: 12 (11 satır + Edit 4'te iki ref birden)
- Kalan stale ref: 0
- pytest: 595/595
- Kod/TDD/config dokunulmadı

---

## Self-Review

**Kapsam tam:** 11 orijinal bulgudaki tüm stale ref edit'te kapsanıyor. Edit 4 iki ref içeriyor (§3.4 + §9), o yüzden 12 edit değil 11 edit; ama her biri ayrı satır.

**Placeholder yok:** Her edit için tam old_string ve new_string verildi.

**Tutarlılık:** Yeni new_string'ler geçerli (kod var olan) veya nötr (referans tamamen çıkarılmış).

**Risk:** Eğer subagent bir Edit'te `old_string` eşleşmezse, muhtemelen PRD yazarken bir boşluk/punctuation farkı var. Subagent Read ile önce tam satırı okur, gerekirse düzeltir.
