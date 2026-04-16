# Chart Period Tabs + Overflow Scroll — Design Spec

**Status:** DRAFT
**Date:** 2026-04-16
**Scope:** Dashboard Total Equity + Per Trade PnL charts

---

## 1. Problem

Her iki chart zamanla sıkışıyor: Per Trade PnL bar'lar incelerek okunmaz hale
geliyor; Total Equity de benzer şekilde yoğunlaşıyor. Mevcut çözüm yok — bar
sayısı `waterfallMaxBars = 40` ile sessizce kesiliyor, kullanıcı daha eski
trade'leri göremiyor.

Hedef: **her iki chart için ortak** bir zaman-dilim filtresi + dilim yoğunsa
yatay kaydırma; yeni dependency eklemeden, kod yüzeyi minimum.

---

## 2. Mimari Karar

**Seçim:** Tab grubu (period filter) + CSS native `overflow-x: auto`.

**Red edilenler:**
- Chart.js zoom/pan plugin → yeni dep, drift riski.
- JS-based drag/scroll state → bug yüzeyi, gereksiz karmaşıklık.
- Sadece scroll (tabsız) → "tüm zamana git" için keşif gerektirir, mental
  model zayıf.
- Sadece tabs (scroll'suz) → yoğun bir günde 24h tab'ı hâlâ sıkışır.

**Seçilen kombinasyon:**
- **Tabs = birincil** (kaba seçim)
- **CSS overflow = fallback** (ince ayar, tarayıcı yönetir)

**ARCH_GUARD uyumu:** yeni dosya presentation katmanında (`static/js/`); domain/
orchestration/infrastructure katmanlarına dokunulmuyor.

---

## 3. Components

### 3.1 `trade_filter.js` (yeni, presentation)

Tek pure function modülü. Global namespace'e `FILTER` koyar (mevcut `FMT`, `ICONS`,
`FEED` kalıbıyla simetrik).

```js
// static/js/trade_filter.js
(function (global) {
  "use strict";
  const HOURS_BY_PERIOD = { "24h": 24, "7d": 168, "30d": 720 };

  function filterByPeriod(trades, period) {
    if (period === "all" || !trades) return trades || [];
    const hours = HOURS_BY_PERIOD[period];
    if (!hours) return trades;
    const cutoff = Date.now() - hours * 3600 * 1000;
    return trades.filter((t) => {
      const ts = t && t.exit_timestamp ? Date.parse(t.exit_timestamp) : NaN;
      return Number.isFinite(ts) && ts >= cutoff;
    });
  }

  global.FILTER = { filterByPeriod };
})(window);
```

**Tüketiciler:** `CHARTS.setEquity`, `CHARTS.setWaterfall`. Test için pure (input → output).

### 3.2 Tab HTML

`templates/dashboard.html` iki `panel-header`'a tab grubu ekler:

```html
<div class="panel-header">
  <span class="card-icon">📈</span> Total Equity
  <div class="chart-tabs" data-chart="equity">
    <button class="chart-tab active" data-period="all">All</button>
    <button class="chart-tab" data-period="30d">30d</button>
    <button class="chart-tab" data-period="7d">7d</button>
    <button class="chart-tab" data-period="24h">24h</button>
  </div>
</div>
```

Benzeri Per Trade PnL için `data-chart="pnl"`.

### 3.3 CSS (`dashboard.css` içine)

```css
.chart-panel .panel-header {
  justify-content: space-between;
}
.chart-tabs {
  display: flex;
  gap: 4px;
  margin-left: 12px;
}
.chart-tab {
  padding: 3px 8px;
  font-size: 10px;
  font-family: inherit;
  color: var(--muted);
  background: transparent;
  border: none;
  border-radius: 100px;
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
}
.chart-tab:hover { color: var(--text); }
.chart-tab:focus-visible { outline: 1px solid var(--border-soft); }
.chart-tab.active {
  color: var(--blue);
  background: var(--panel-hover);
}
.chart-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  width: 100%;
  height: 100%;
}
.chart-scroll::-webkit-scrollbar { height: 6px; }
.chart-scroll::-webkit-scrollbar-thumb {
  background: var(--border-soft);
  border-radius: 3px;
}
```

**Palette:** `--panel-hover` (#151C30) aktif tab background için kullanılır;
`--muted`, `--text`, `--blue`, `--border-soft` hepsi mevcut token'lardır
(dashboard.css :root bloğunda). Yeni CSS var yaratılmaz.

### 3.4 Canvas wrapper

`.chart-fixed` içindeki canvas bir kat daha sarılır:

```html
<div class="chart-fixed">
  <div class="chart-scroll">
    <canvas id="equity-chart"></canvas>
  </div>
</div>
```

### 3.5 Chart state + tab binding (`dashboard.js`)

```js
const CHART_STATE = { equityPeriod: "all", pnlPeriod: "all" };

const CHART_TAB_BINDING = {
  equity: { stateKey: "equityPeriod", render: () => CHARTS.setEquity(LAST.trades, INITIAL_BANKROLL) },
  pnl:    { stateKey: "pnlPeriod",    render: () => CHARTS.setWaterfall(LAST.trades) },
};

function _bindChartTabs() {
  document.querySelectorAll(".chart-tabs").forEach((group) => {
    const chart = group.dataset.chart;
    const binding = CHART_TAB_BINDING[chart];
    if (!binding) return;
    group.addEventListener("click", (e) => {
      const btn = e.target.closest(".chart-tab");
      if (!btn) return;
      group.querySelectorAll(".chart-tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      CHART_STATE[binding.stateKey] = btn.dataset.period;
      binding.render();
    });
  });
}
```

`LAST.trades` = son refresh'teki trades cache (yeni state container; refresh
her çağrısında güncellenir). Böylece tab tıklamasında yeni fetch yok, mevcut
veri filtrelenir.

### 3.6 Chart tüketicileri filter kullanır

```js
setEquity(trades, initialBankroll) {
  const period = CHART_STATE.equityPeriod;
  const filtered = global.FILTER.filterByPeriod(trades, period);
  // ... mevcut cumsum mantığı, ama `trades` yerine `filtered` üzerinde
  // ...
  // Canvas min-width: bars × 18px
  const minWidth = filtered.length * 18;
  this.equity.canvas.style.minWidth = minWidth + "px";
},

setWaterfall(trades) {
  const period = CHART_STATE.pnlPeriod;
  const filtered = global.FILTER.filterByPeriod(trades, period).slice(0, CONFIG.waterfallMaxBars);
  // ... mevcut waterfall mantığı, `filtered` üzerinden
  // Canvas min-width: bars × 14px
  const minWidth = filtered.length * 14;
  this.waterfall.canvas.style.minWidth = minWidth + "px";
},
```

**Önemli:** `CONFIG.waterfallMaxBars = 40` cap'i kalıyor — 24h'de 80 trade olursa
son 40 gösterilir + scroll ile geriye gidilir. "All" tab'ında da cap aynı →
aşırı uzak tarihler scroll ile erişilir.

### 3.7 Config sabitleri

`CONFIG`'e ekleme (magic number → config, ARCH Kural 6):

```js
const CONFIG = {
  pollIntervalMs: 5000,
  waterfallMaxBars: 40,
  equityBarMinPx: 18,
  pnlBarMinPx: 14,
  // ...
};
```

Chart'lar bu token'ları okur.

---

## 4. Data Flow

```
refresh()
  └─ API.trades()  → LAST.trades = data
  └─ CHARTS.setEquity(LAST.trades, INITIAL_BANKROLL)
        └─ FILTER.filterByPeriod(trades, CHART_STATE.equityPeriod)
        └─ cumsum → canvas update
        └─ canvas.style.minWidth = bars × equityBarMinPx
  └─ CHARTS.setWaterfall(LAST.trades)
        └─ FILTER.filterByPeriod(trades, CHART_STATE.pnlPeriod)
        └─ slice(0, waterfallMaxBars) → bar update
        └─ canvas.style.minWidth = bars × pnlBarMinPx

tab click
  └─ CHART_STATE[key] = period
  └─ binding.render()  → filter → re-draw
  └─ (no network fetch; uses LAST.trades cache)
```

---

## 5. Testing

**Pure function (`FILTER.filterByPeriod`):** Browser console veya ileride Jest.
Test senaryoları:
- `period = "all"` → tüm trades döner
- `period = "24h"` → son 24 saat içindekiler
- `period = "7d"` → son 7 gün
- `period = "30d"` → son 30 gün
- Bilinmeyen period → tüm trades döner (güvenli fallback)
- Boş array → boş array
- `exit_timestamp` null/malformed → o trade elenir (Number.isFinite guard)

**Manual QA checklist:**
- [ ] Default: her iki chart "All" tab aktif, eski davranışla aynı
- [ ] Tab tıklama → aktif class doğru kayıyor, diğer tab'lar deaktif
- [ ] "24h" sadece son 24 saatlik exit'leri gösteriyor
- [ ] Yoğun dönem (>container) seçiminde scroll bar görünüyor
- [ ] Seyrek dönem (küçük) seçiminde scroll yok, canvas container'a sığıyor
- [ ] Boş dönemde chart boş ama kart görünür
- [ ] İki chart bağımsız seçim tutuyor (biri 7d, diğeri all olabilir)
- [ ] Refresh (5sn) tab seçimini sıfırlamıyor

---

## 6. Migration / Compatibility

- Backend değişmiyor → no TDD §5.7.7 update needed for data source.
- `equity_history.jsonl` formatı değişmiyor.
- Mevcut chart render tests (eğer varsa) etkilenmez; `setEquity` imzası aynı
  kalır (trades, initialBankroll), sadece içeride filter ekleniyor.

---

## 7. ARCH_GUARD Checklist

- ✓ Katman: yalnızca `presentation/dashboard/static/` (HTML/CSS/JS) + template
- ✓ Domain I/O yok (filter pure function, browser-only)
- ✓ Dosya boyutu: `trade_filter.js` ~20 satır; `dashboard.js` mevcut ~400 sınır,
  ~40 satır eklenecek → 400 cap'te kalacak, taşarsa split gereği plan aşaması
- ✓ Magic number yok: bar min-width, period hours config/constant
- ✓ utils/helpers/misc yok: yeni dosya adı `trade_filter.js`
- ✓ Sessiz hata yok: malformed timestamp explicit guard (Number.isFinite)
- ✓ P(YES) etkilenmez
- ✓ Event-level guard etkilenmez

---

## 8. Risks

- **R1:** Canvas `style.minWidth` ayarı Chart.js responsive resize'ıyla
  çakışabilir → plan aşamasında önce chart options'ta `maintainAspectRatio:
  false` zaten var mı kontrol et (büyük ihtimalle var). Varsa minWidth
  canvas'ın CSS height'ını bozmaz.
- **R2:** Chart.js yeni veriyle update ederken animate ederse tab switch
  sırasında flicker olur → `update("none")` çağrısı mevcut pattern'de var,
  korunacak.
- **R3:** `LAST.trades` cache refresh arasında stale olabilir (5sn interval).
  Tab tıklamasında eski cache filtrelenir, yeni refresh'te canlı veri gelir.
  Kabul edilebilir (5sn lag).

---

## 9. Out of Scope

- Custom date range picker (YAGNI — 4 tab yeterli)
- Export chart as image (ayrı özellik)
- Peak/drawdown'ın period'a göre yeniden hesaplanması (separate concern)
- Total Equity'nin period'a göre başlangıç değerini değiştirmesi — "All"da
  initial=$1000; "7d"de 7 gün önceki bankroll'dan başlasın mı? → **Hayır, MVP:
  her period initial=$1000'dan başlar, yalnız o pencere içindeki exit'leri
  cumsum eder**. Relatif performansı "son 7 günde ne kazandım" olarak gösterir
  — kullanıcı mental modeline uygun.

---

## 10. Lokasyon özeti

**Yeni:**
- `src/presentation/dashboard/static/js/trade_filter.js`

**Modify:**
- `src/presentation/dashboard/templates/dashboard.html` (iki panel header'a tab HTML)
- `src/presentation/dashboard/static/css/dashboard.css` (.chart-tabs, .chart-scroll, header space-between)
- `src/presentation/dashboard/static/js/dashboard.js` (CONFIG ek, CHART_STATE, LAST.trades, bindings, setEquity/setWaterfall filter çağrısı + minWidth)
