# Active Card Progress Bar Layout — Design

**Tarih:** 2026-04-16
**Durum:** DRAFT → user review
**Amaç:** Active trade kartında $ PnL rakamını progress bar fill'inin sağına "yerleştir"; yüzdelik değeri parantez içinde bar'ın sağ ucuna sabitle.

---

## Problem

Şu an active card progress bar'ı ([feed.js:112-116](../../src/presentation/dashboard/static/js/feed.js#L112-L116)):

```
[██ fill ................................] $-0.91 -5.5%
                                           ^ $ ve % hep aynı yerde, fill'den bağımsız
```

İstenen (referans görseller: tabela görselleri 2026-04-16):

```
[██ fill +$3.36 .....................(+27.2%)]
         ^ $, fill'in sağına yapışık    ^ % sağa sabit
```

- $ rakamı fill'in bittiği yere bağlı hareket eder
- Yüzdelik **parantez içinde** bar'ın sağ ucunda sabit
- Büyük fill'de $ ile % çakışmasın (clamp)

## Hedef

Görsellerdeki layout: $ rakamı dinamik (fill ile hareket), % parantezli ve sağda sabit.

---

## Tasarım

### HTML yapısı ([feed.js:112-116](../../src/presentation/dashboard/static/js/feed.js#L112-L116))

**Eski:**
```html
<div class="feed-impact">
  <div class="feed-impact-bar"><div class="feed-impact-bar-fill [neg]" style="width:X%"></div></div>
  <span class="unr-pos/neg">$±X <span class="feed-pnl-pct">±X%</span></span>
</div>
```

**Yeni:**
```html
<div class="feed-impact">
  <div class="feed-impact-bar" style="--fill:X%;--dollar-left:CLAMPED%">
    <div class="feed-impact-bar-fill [neg]"></div>
    <span class="feed-pnl-dollar unr-pos/neg">$±X</span>
    <span class="feed-pnl-pct unr-pos/neg">(±X%)</span>
  </div>
</div>
```

**İki CSS değişkeni inline:**
- `--fill`: `min(100, |pnlPct|)` — fill bar genişliği
- `--dollar-left`: `min(75, |pnlPct|)` — $ rakamı pozisyonu (%75'te clamp, böylece % ile çakışmaz)

### CSS değişiklikleri ([feed.css:172-198](../../src/presentation/dashboard/static/css/feed.css#L172-L198))

1. `.feed-impact-bar` — `position: relative`, yükseklik `14px` (text host edebilsin), flex:1 korunur.
2. Track görünümü `::before` pseudo'ya taşınır (mevcut background kalıbı korunur).
3. `.feed-impact-bar-fill` — `position: absolute`, `left:0`, `top:50%`, `transform: translateY(-50%)`, `height: 4px`, `width: var(--fill)`. Eski width:inline kaldırıldı.
4. `.feed-pnl-dollar` (yeni class) — `position: absolute`, `left: var(--dollar-left)`, `transform: translate(6px, -50%)`, `top:50%`, font-weight 600, 11px.
5. `.feed-pnl-pct` (güncellenir) — `position: absolute`, `right: 4px`, `top:50%`, `transform: translateY(-50%)`, font-size 10px. Eski `margin-left: 2px` kaldırılır (artık flex içinde değil, absolute).

Renklendirme: `unr-pos` / `unr-neg` class'ları hem `.feed-pnl-dollar` hem `.feed-pnl-pct` üzerinde → ikisi de yeşil/kırmızı aynı anda.

### Edge case davranışı (clamp)

- **pnlPct = 0**: fill=0%, $ at 0% (bar'ın sol iç kenarında, "+$0.00"). % sağda.
- **pnlPct = 27**: fill=27%, $ at 27% (fill'in ucunda). Görselle uyumlu.
- **pnlPct = 50**: fill=50%, $ at 50%.
- **pnlPct = 80**: fill=80%, $ at **75%** (clamped). Fill $ arasında hafif overlap görsel — kabul edilebilir çünkü % ile çakışma önlenir.
- **pnlPct > 100**: fill=100%, $ at 75% (clamped).
- **pnlPct = -5.5**: fill=5.5% (negatif de absolute value), fill kırmızı, $ at 5.5%, % (-5.5%) sağda kırmızı.

Clamp değeri %75 — `+$123.45` gibi uzun metinler için yeterli alan bırakır. Daha uzun PnL'lerde (%100+) bile görsel bozulmaz.

---

## Dosya değişiklikleri

| Dosya | Değişiklik |
|---|---|
| `src/presentation/dashboard/static/js/feed.js` | `_activeCard` template 4 satır değişir |
| `src/presentation/dashboard/static/css/feed.css` | `.feed-impact-bar` + `.feed-impact-bar-fill` + `.feed-pnl-dollar` (yeni) + `.feed-pnl-pct` |

Hiçbir Python dosyasına, domain/strategy/orchestration'a dokunulmaz.

## Test stratejisi

Frontend JS için unit test harness projede yok (kontrol: `tests/**/test_feed*.py` = 0 sonuç). **Görsel doğrulama** yeterli:

1. Dashboard'ı aç
2. Active sekmesine bak
3. Beklenen:
   - Pozitif kart (kârda): yeşil bar + yeşil `+$X.XX` fill'in sağında + yeşil `(+X.X%)` sağda
   - Negatif kart (zararda): kırmızı bar + kırmızı `-$X.XX` fill'in sağında (fill küçük) + kırmızı `(-X.X%)` sağda
   - Sıfır PnL: bar boş, `+$0.00` solda, `(+0.0%)` sağda
   - Yüksek PnL (>%75): $ rakamı 75% pozisyonunda kalır, % çakışmaz

## ARCH_GUARD uyum

- **Kural 1 (katman)**: presentation/static değişikliği. ✓
- **Kural 2 (domain I/O)**: domain dokunulmuyor. ✓
- **Kural 3 (400 satır)**: feed.js ~200 satır, feed.css ~300 satır — limit içinde. ✓
- **Kural 6 (magic number)**: CSS değerleri (14px, 4px, %75 clamp) → styling parametresi, biz mantığı değil. Kabul. ✓
- **Kural 11 (test)**: frontend için test harness yok — görsel test yeterli. ✓

## Kapsam dışı (YAGNI)

- Exited/Skipped kartların layout'u (şu an farklı yapılar, gerek yok)
- Dark/light tema değişkenleri (mevcut --green / --red korunur)
- Animasyon tweaks (transition mevcut, değiştirilmiyor)

## Risk

- `feed.css` içinde `.feed-impact-bar-fill` selector'u başka bir kart tipinde kullanılıyor mu? **Hayır** — grep'le kontrol edildi, sadece active card.
- Browser render tutarsızlığı: `transform: translateY(-50%)` modern browser'larda sorunsuz.

---

## Onay

Spec onaylanınca:
1. `writing-plans` skill ile implementation plan yazılır.
2. Plan onaylanınca kod yazımı başlar (feed.js → feed.css → görsel test → commit).
