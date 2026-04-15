# Dashboard FMT Namespace Contract

`static/js/fmt.js` (Task 9+ sonrası; öncesi `dashboard.js`) global `window.FMT`.

Tüm helper'lar **pure** (I/O yok, side-effect yok). Çıktı hep HTML-escape'li
string — `innerHTML`'e güvenle yazılabilir.

## Helpers

### `FMT.escapeHtml(s: string): string`
HTML meta karakterleri (`& " < >`) escape eder.

### `FMT.usdSignedHtml(n: number): string`
`+$10.00` / `-$5.25` formatında, decimal kısmı `<span class="dec">` içinde.

### `FMT.pctSigned(n: number, digits?: number): string`
Yüzde değeri, işaretli. `null/undefined/NaN` → `"--"`.

### `FMT.cents(price: number): string`
`65¢` formatında (0-1 aralığı × 100 yuvarlanır).

### `FMT.relTime(iso: string): string`
`"just now" | "Xm ago" | "Xh ago" | "Xd ago"`.

### `FMT.time(iso: string): string`
Lokal saat `HH:MM` (geçersiz → `""`).

### `FMT.polyUrl(slug: string): string`
`https://polymarket.com/event/<slug>` (slug yoksa `"#"`).

### `FMT.pnlClass(n: number): string`
`"pnl-pos" | "pnl-neg" | "pnl-zero"` — 0.001 eşiği.

### `FMT.unrealizedClass(n: number): string`
`"unr-pos" | "unr-neg" | "pnl-zero"` — open PnL renk sınıfı (pozitif mavi).

### `FMT.teamsText(question: string, slug: string): string`
Market başlığını insana okunur yapar (HTML-escape'li).

**Öncelik:**
1. `question` varsa "X vs Y" pattern'inden iki yanı çıkar (ör. "Arizona Diamondbacks vs Baltimore Orioles").
2. Yoksa slug pattern'i:
   - `"{sport}-{t1}-{t2}-YYYY-MM-DD"` → `TEAM_NAMES[t1] + " vs " + TEAM_NAMES[t2]`.
     Map yoksa: kısa kod → uppercase, uzun kod → Title-Case.
   - `"...winner-{first}-{last}"` → "First Last" (golf-style).
3. Hiçbiri eşleşmezse slug olduğu gibi.

### `FMT.sideCode(direction: "BUY_YES"|"BUY_NO", slug: string): string`
Badge metni: slug yes-code veya no-code (uppercase).
Slug eşleşmezse fallback `"YES"` / `"NO"`.

## TEAM_NAMES Map

Lokasyon: `fmt.js` içinde `const TEAM_NAMES`. Anahtar = lowercase kısa kod.
İçerik: 30+ MLB + 25+ NHL takım şehir/isim eşlemesi.

Eklenecek spor (NBA/NFL/soccer/tennis) için `TEAM_NAMES`'e giriş eklenir —
`FMT.teamsText` otomatik kullanır.

## Breaking Change Protokolü

Bu dosya **kontrat**. Helper imzası/davranışı değişirse:
1. Bu dosyayı güncelle.
2. Tüm tüketicileri (`branches.js`, `feed.js`, `dashboard.js`) gözden geçir.
3. Regression testi (mümkünse) ekle.
