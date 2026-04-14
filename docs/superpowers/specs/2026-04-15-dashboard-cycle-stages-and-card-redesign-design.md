# Dashboard: Cycle Aşamaları + Pozisyon Kartı Yeniden Tasarımı

**Tarih:** 2026-04-15
**Kapsam:** Presentation katmanı (dashboard) + agent.py cycle stage sinyali

---

## 1. Problem

1. **Cycle status belirsiz:** Dashboard'da Hard/Light cycle ya "Waiting" ya "Running" diyor — kullanıcı hangi aşamada olduğumuzu (scan/enrich/gate/exec) göremiyor.
2. **Pozisyon kartı okunmuyor:** Başlıkta slug (`mlb-ari-bal-2026-04-14`) görünüyor, takım ismi değil. Maç saati yok. Confidence detay satırında boğuluyor. Odds hiç gösterilmiyor.

---

## 2. Hedef

- Hard cycle'ın her aşamasını real-time göster (`Scanning` → `Analyzing` → `Executing` → `Idle - next MM:SS`). `Analyzing` bookmaker enrichment + entry gate değerlendirmesini kapsar.
- Light cycle için yalnızca `Online`/`Offline`.
- Pozisyon kartında takım isimleri, maç countdown'u, confidence rozeti (renk kodlu) ve odds.

---

## 3. Tasarım

### 3.1 Cycle Stage Sinyali (backend)

**Mevcut durum:** `agent.py::_write_bot_status` cycle sonunda tek snapshot yazıyor:
```json
{"mode": "dry_run", "last_cycle": "heavy", "last_cycle_at": "…", "reason": "cold_start"}
```

**Değişiklik:** Heavy cycle içinde **aşama başında** ek snapshot yazılır. Aşamalar:

| Aşama | Ne zaman yazılır |
|---|---|
| `scanning` | `scanner.scan()` / `scanner.drain_eligible()` çağrısından hemen önce |
| `analyzing` | `gate.run()` çağrısından hemen önce (enrichment gate içinde market-by-market yapıldığından ayrı etiketi yok, analyzing kapsar) |
| `executing` | İlk `_execute_entry` çağrısından hemen önce (signal üretilmişse) |
| `idle` | Heavy cycle bitişinde (cycle interval bilgisiyle) |

**JSON şeması:**
```json
{
  "mode": "dry_run",
  "cycle": "heavy",
  "stage": "enriching",
  "stage_at": "2026-04-15T00:25:58.265Z",
  "next_heavy_at": "2026-04-15T00:35:00.000Z",
  "light_alive": true
}
```

**Kritik kurallar (ARCH_GUARD):**
- `_write_bot_status` metodu `agent.py` içinde kalır (orchestration katmanı).
- Domain/strategy katmanları bot_status'a yazmaz — agent wrapper metotla çağırır.
- Scanner'ın enrichment aşamasına sinyal vermesi için `agent.py` scanner'ı **inline** sarar veya scanner bir callback alır. **Tercih:** callback (scanner interface temiz kalır).

### 3.2 Dashboard Frontend — Cycle Status

**`routes.py::/api/status`** — yeni alanlar döner: `cycle`, `stage`, `stage_at`, `next_heavy_at`, `light_alive`.

**`dashboard.js::RENDER.status()`** — yeniden yazılır:

- **Hard cycle label map:**
  ```
  scanning   → "Scanning"
  analyzing  → "Analyzing"
  executing  → "Executing"
  idle       → "Idle - next MM:SS"  (next_heavy_at - now'dan hesaplanır)
  null       → "Waiting"            (bot_status.json yoksa)
  ```
- **Light cycle label:**
  - `light_alive: true` → `Online` (yeşil nokta)
  - `light_alive: false` veya `bot_alive: false` → `Offline` (gri nokta)

**"Stage taze mi" kontrolü:** `stage_at` 15 saniyeden eskiyse Hard etiketi `Idle` kabul edilir (bot aşamadayken takılı kaldıysa yanıltmasın).

**Idle countdown hesabı:** Frontend `setInterval(1s)` ile `next_heavy_at - Date.now()` değerini MM:SS formatında render eder. Next_heavy_at null ise sadece "Idle".

### 3.3 Pozisyon Kartı Yeniden Tasarımı

**Mevcut (`feed.js::_activeCard`):**
```
⚾ mlb-ari-bal-2026-04-14                                          [YES]
Entry 41¢   Now 41¢   A
[bar] +$0.00
$50   volatility_swing
```

**Yeni:**
```
⚾ Diamondbacks vs Orioles                          [A] [YES]
Entry 41¢    Now 41¢    Odds 40.9%
[bar] +$0.00
$50  volatility_swing                                [54m]
```

**Değişiklikler:**

| Alan | Yeni değer |
|---|---|
| Başlık | `question`'dan takım isimleri (kısa form) — fallback `slug` |
| Conf rozeti | Başlıkta YES'in solunda pill. A=yeşil (`#16c784`), B=lime (`#a4d45a`), C=sarı (`#e6c94d`) |
| Details satırı | `Entry X¢  Now X¢  Odds Y%` (Odds = `anchor_probability × 100`, Conf buradan kaldırıldı) |
| Alt satır | `$50  volatility_swing   [countdown]` — gap'ler eşit (`$50` ↔ `volatility_swing` = `A` ↔ `YES`) |
| Countdown | Alt satırda en sağda. YES pill ile **aynı vertical axis** (kartın sağ kenarına sıfır padding). Mavi pill, düşük opacity (`#3b82f6` @ opacity 0.5). Format: `54m` veya `1h 3m`, `LIVE` (kırmızı pill). Maç bitmişse gösterilmez (exited tab'e geçer). |

**Başlık kısa form kuralı:**
- `question` = "Arizona Diamondbacks vs. Baltimore Orioles"
- Parse: " vs. " veya " vs " ile böl, her tarafı son kelimeye indir → "Diamondbacks vs Orioles"
- Eğer parse tutmazsa `question` olduğu gibi gösterilir
- Fallback: `question` yoksa `slug`

**Countdown format kuralı:**
```
delta = match_start_iso - now
delta > 3600s  → "Xh Ym"  (örn. "1h 3m")
0 < delta ≤ 3600s → "Xm"   (örn. "54m")
delta ≤ 0 AND match_live → "LIVE" (kırmızı pill)
delta ≤ 0 AND NOT match_live → pill gizlenir (maç başlamış, ws flag henüz set edilmemiş)
```

---

## 4. Etkilenen Dosyalar

**Backend:**
- `src/orchestration/agent.py` — `_write_bot_status` genişletilir; `scanning`/`analyzing`/`executing`/`idle` aşama snapshot'ları eklenir
- `src/orchestration/cycle_manager.py` — `next_heavy_at_iso()` helper eklenir (bir sonraki heavy cycle'ın ISO timestamp'i)

**Dashboard routes/readers (presentation):**
- `src/presentation/dashboard/routes.py` — `/api/status` yeni alanlar
- `src/presentation/dashboard/readers.py` — `read_bot_status` dönüşü değişmez (şema genişler, geriye uyumlu)

**Dashboard frontend:**
- `src/presentation/dashboard/static/js/dashboard.js` — `RENDER.status()` yeniden yazılır, idle countdown interval
- `src/presentation/dashboard/static/js/feed.js` — `_activeCard` yeniden yazılır, yeni helper'lar (`_teamsTitle`, `_countdownPill`, `_confPill`)
- `src/presentation/dashboard/static/css/feed.css` — conf pill renkleri, countdown pill, layout gap'leri
- `src/presentation/dashboard/templates/dashboard.html` — değişiklik minimal (mevcut `#cg-hard-status` vs. yeterli)

**Tests:**
- `tests/unit/presentation/dashboard/test_routes.py` — yeni alanlar
- `tests/unit/orchestration/test_agent_stages.py` — cycle aşama sinyalleri JSON'a doğru yazılıyor mu
- Frontend (js): test altyapısı yok, manuel doğrulama

---

## 5. Hata Toleransı

- `bot_status.json` eksik/bozuk → frontend "Waiting" / "Offline" gösterir, hata fırlatmaz
- `question` null/eksik → `slug` fallback
- `match_start_iso` null → countdown pill gizlenir
- `stage_at` eski (> 15 sn) → `Idle` göster (takılı kaldıysa yanıltma)

---

## 6. Yapılmayacaklar (Scope Out)

- Entry stratejilerinin re-brainstorm'u (ayrı iş — kullanıcı onayladı, sonraki oturum)
- Volatility_swing'in logic değişikliği
- Light cycle iç aşamaları (Ticking/Monitoring/Exiting) — sade Online/Offline
- Ended state (maç biten pozisyon zaten exited tab'ine geçer)

---

## 7. Başarı Kriterleri

- [ ] Bot çalışırken dashboard Hard cycle etiketi 5 aşamayı da gerçek zamanlı gösteriyor
- [ ] Idle sırasında MM:SS countdown azalıyor
- [ ] Light cycle sadece Online/Offline gösteriyor
- [ ] Pozisyon kartları takım ismi + countdown + renk kodlu conf + odds gösteriyor
- [ ] Kart kenarına yapışık countdown, YES ile aynı dikey eksende
- [ ] Mevcut testler geçiyor + yeni unit testler yazıldı
- [ ] ARCH_GUARD 8 anti-pattern taraması: ihlal yok
