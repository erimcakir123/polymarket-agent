# Active Card Progress Bar Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Active card progress bar'ında $ PnL rakamını fill'in sağına "yerleştir", yüzdelik parantez içinde bar'ın sağ ucuna sabitle.

**Architecture:** HTML template + CSS selector değişikliği. İki CSS değişkeni (`--fill`, `--dollar-left`) inline style ile geçer. Fill/dollar konumu JS'de hesaplanır, CSS sadece apply eder.

**Tech Stack:** Vanilla JS, CSS3 (custom properties, absolute positioning).

**Spec:** [docs/superpowers/specs/2026-04-16-active-card-progress-bar-layout-design.md](../specs/2026-04-16-active-card-progress-bar-layout-design.md)

---

## File Structure

| Dosya | Rol | Değişiklik |
|---|---|---|
| `src/presentation/dashboard/static/js/feed.js` | `_activeCard` template | Modify (4 satır) |
| `src/presentation/dashboard/static/css/feed.css` | Progress bar layout | Modify (~25 satır) |

---

## Task 1 — HTML template (feed.js)

**Files:**
- Modify: `src/presentation/dashboard/static/js/feed.js:112-116`

- [ ] **Step 1.1 — `.feed-impact` bloğunu güncelle**

`src/presentation/dashboard/static/js/feed.js` satır 112-116'yı bul:

```javascript
        <div class="feed-impact">
          <div class="feed-impact-bar"><div class="feed-impact-bar-fill${pnl < 0 ? " neg" : ""}"
            style="width:${Math.min(100, Math.abs(pnlPct))}%"></div></div>
          <span class="${FMT.unrealizedClass(pnl)}">${FMT.usdSignedHtml(pnl)} <span class="feed-pnl-pct">${FMT.pctSigned(pnlPct, 1)}</span></span>
        </div>
```

Şununla değiştir:

```javascript
        <div class="feed-impact">
          <div class="feed-impact-bar" style="--fill:${Math.min(100, Math.abs(pnlPct))}%;--dollar-left:${Math.min(75, Math.abs(pnlPct))}%">
            <div class="feed-impact-bar-fill${pnl < 0 ? " neg" : ""}"></div>
            <span class="feed-pnl-dollar ${FMT.unrealizedClass(pnl)}">${FMT.usdSignedHtml(pnl)}</span>
            <span class="feed-pnl-pct ${FMT.unrealizedClass(pnl)}">(${FMT.pctSigned(pnlPct, 1)})</span>
          </div>
        </div>
```

**Değişiklikler:**
- `.feed-impact-bar` element'ine `style="--fill:X%;--dollar-left:Y%"` eklendi
- `.feed-impact-bar-fill` artık inline width taşımıyor (CSS var'dan alır)
- Eski `<span class="unr-*">` dışarıdaki wrapper kaldırıldı
- `.feed-pnl-dollar` yeni class — sadece $ rakamı, bar içinde absolute
- `.feed-pnl-pct` — parantez içinde `(X%)`, bar içinde absolute (sağda)
- İkisi de `FMT.unrealizedClass(pnl)` alır (renk için)

- [ ] **Step 1.2 — Sentaks hatası var mı kontrolü**

```bash
node --check src/presentation/dashboard/static/js/feed.js
```

Expected: Çıktı yok (sentaks OK). Hata varsa düzelt.

---

## Task 2 — CSS layout (feed.css)

**Files:**
- Modify: `src/presentation/dashboard/static/css/feed.css:172-198`

- [ ] **Step 2.1 — `.feed-impact-bar` bloğunu güncelle**

`src/presentation/dashboard/static/css/feed.css` satır 172-178'i bul:

```css
.feed-impact-bar {
  flex: 1;
  height: 4px;
  background: var(--border-soft);
  border-radius: 2px;
  overflow: hidden;
}
```

Şununla değiştir:

```css
.feed-impact-bar {
  flex: 1;
  height: 14px;
  position: relative;
  display: block;
}

.feed-impact-bar::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 4px;
  background: var(--border-soft);
  border-radius: 2px;
}
```

**Neden:** Yükseklik 14px'e çıkarıldı (text host edebilsin); track background `::before` pseudo'ya taşındı (overflow:hidden kaldırıldı çünkü text bar dışına taşabilir).

- [ ] **Step 2.2 — `.feed-impact-bar-fill` bloğunu güncelle**

`src/presentation/dashboard/static/css/feed.css` satır 180-186'yı bul:

```css
.feed-impact-bar-fill {
  height: 100%;
  background: var(--green);
  transition: width 0.25s ease;
}

.feed-impact-bar-fill.neg { background: var(--red); }
```

Şununla değiştir:

```css
.feed-impact-bar-fill {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 4px;
  width: var(--fill, 0%);
  background: var(--green);
  border-radius: 2px;
  transition: width 0.25s ease;
}

.feed-impact-bar-fill.neg { background: var(--red); }
```

**Neden:** Fill artık absolute — bar yüksekliği 14px olsa da fill 4px kalır ve track üzerinde oturur. Width CSS var'dan okunur.

- [ ] **Step 2.3 — `.feed-pnl-pct` bloğunu güncelle ve `.feed-pnl-dollar` ekle**

`src/presentation/dashboard/static/css/feed.css` satır 194-198'i bul:

```css
.feed-pnl-pct {
  font-size: 10px;
  font-weight: 500;
  margin-left: 2px;
}
```

Şununla değiştir:

```css
.feed-pnl-dollar {
  position: absolute;
  left: var(--dollar-left, 0%);
  top: 50%;
  transform: translate(6px, -50%);
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  pointer-events: none;
}

.feed-pnl-pct {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
}
```

**Neden:**
- `.feed-pnl-dollar`: yeni, bar içinde absolute, `--dollar-left`'ten pozisyonu gelir, `translate(6px, -50%)` ile fill'in hemen sağında ve dikeyde ortalanır.
- `.feed-pnl-pct`: artık bar içinde absolute (sağda sabit), `margin-left:2px` kaldırıldı (artık flex değil).
- `pointer-events: none` — tıklamalar alt `<a>`a geçsin (kart link'i).

---

## Task 3 — Visual verification

- [ ] **Step 3.1 — Dashboard'ı başlat**

```bash
python -m src.main --mode dry_run
```

Bir terminal'de, bu background çalışmalı. Dashboard port 5000 (veya config'de tanımlı) açılır.

- [ ] **Step 3.2 — Tarayıcıda aç, active sekmesine bak**

Browser: `http://localhost:5000` (veya config port)

**Kontrol et:**
- [ ] Pozitif kart: yeşil fill + fill'in sağında yeşil `+$X.XX` + bar'ın sağında yeşil `(+X.X%)`
- [ ] Negatif kart: kırmızı fill + fill'in sağında kırmızı `-$X.XX` + bar'ın sağında kırmızı `(-X.X%)`
- [ ] Sıfır PnL kart (varsa): boş bar, sol tarafta `+$0.00`, sağda `(+0.0%)`
- [ ] Fill yüksek (>%75) olan kart: $ rakamı %75'te clamp, % ile çakışmıyor
- [ ] Kart tıklanınca Polymarket açılıyor (pointer-events:none $/% spanları engellemesin)

**Başarısız kontrol varsa:** CSS veya JS'de ilgili alanı düzelt, tekrar test et.

- [ ] **Step 3.3 — Console'da JS hatası var mı**

Browser DevTools → Console. Expected: hata yok.

- [ ] **Step 3.4 — Exited / Skipped sekmelerinde regression var mı**

Exited/Skipped kartlar ETKİLENMEMELİ (farklı class'lar kullanıyorlar). Hızlı göz at, regresyon yoksa devam.

---

## Task 4 — Commit

- [ ] **Step 4.1 — git diff özeti**

```bash
git diff --stat src/presentation/dashboard/static/
```

Expected: 2 dosya (feed.js, feed.css).

- [ ] **Step 4.2 — Commit**

```bash
git add src/presentation/dashboard/static/js/feed.js src/presentation/dashboard/static/css/feed.css
git commit -m "feat(feed): progress bar \$ follows fill edge, pct parenthesized at right"
```

---

## Self-Review

**Spec coverage:**
- ✓ $ rakamı fill'in sağına (Task 1.1 + Task 2.3)
- ✓ Yüzdelik parantez içinde (Task 1.1)
- ✓ Yüzdelik sağda sabit (Task 2.3)
- ✓ Clamp %75 (Task 1.1)
- ✓ Renk: hem $ hem % unr-pos/neg class alır (Task 1.1)

**Placeholder scan:** yok — tüm kod blokları tam.

**Type consistency:**
- `--fill`, `--dollar-left` CSS var adları feed.js ve feed.css arasında tutarlı ✓
- `.feed-pnl-dollar`, `.feed-pnl-pct` class adları tutarlı ✓
- `FMT.unrealizedClass(pnl)` mevcut API, değişmiyor ✓

**ARCH_GUARD:**
- Presentation-only ✓
- Magic number: 14px, 4px, 6px, %75 — styling parametreleri, biz mantığı değil ✓
- Test: frontend JS için harness yok, görsel test yeterli ✓

---

## Execution Handoff

Plan complete ve `docs/superpowers/plans/2026-04-16-active-card-progress-bar-layout.md`'a kaydedildi.

İki seçenek:

1. **Subagent-Driven (önerilen)** — her task için fresh subagent, aralarında review
2. **Inline Execution** — bu session'da sıralı yap

Hangisi?
