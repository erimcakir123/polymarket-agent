# Chart Period Tabs + Adaptive Bucketing — Design Spec

**Status:** DRAFT
**Date:** 2026-04-16
**Scope:** Dashboard Total Equity + Per Trade PnL charts

---

## 1. Problem

Her iki chart zamanla sıkışıyor: Per Trade PnL bar'ları incelerek okunmaz hale
geliyor; Total Equity her realized event'te yeni basamak eklediği için yıllar
içinde canvas onbinlerce pixel genişliğe ulaşır. Mevcut çözüm yok — bar sayısı
`waterfallMaxBars = 40` ile sessizce kesiliyor, eski trade'ler erişilemez.

Hedef: **zaman-dilim tabs** + **adaptif bucketing** (dilim genişledikçe rezolüsyon
kabalaşır) + **yoğun dilimlerde CSS native scroll**. Yeni dependency yok, kod
yüzeyi minimum.

---

## 2. Mimari Karar

**Seçim:** Tab grubu (period filter) + adaptive bucketing + CSS `overflow-x: auto`.

**Red edilenler:**
- Chart.js zoom/pan plugin → yeni dep, drift riski.
- JS-based drag/scroll state → bug yüzeyi.
- Sadece scroll (tabsız) → "tüm zamana git" için keşif gerektirir.
- Sadece tabs (bucketing'siz) → 1y event-based = 5,000+ nokta, browser boğulur.
- "All" tab → sınırsız tarih, sonsuz scroll; yıllar içinde kullanılamaz hâle gelir.

**Seçilen kombinasyon:**
1. **4 tab** (bounded period): `24h / 7d / 30d / 1y`
2. **Adaptif bucketing** (her tab'a uygun rezolüsyon): event → hour → day → week
3. **CSS scroll** (yoğun dilimde fallback)

**ARCH_GUARD uyumu:** yalnızca `presentation/dashboard/static/` dokunulur.

---

## 3. Period → Resolution tablosu

Profesyonel trading dashboard pattern'i (Robinhood/TradingView): period genişledikçe
granularity logaritmik kabalaşır. Her tab ekran-dostu nokta sayısı verir.

| Tab | Granularity | Her nokta ne? | Tipik max nokta | Ekran fit |
|-----|------------|----------------|-----------------|-----------|
| **24h** | Event-based | Her exit = 1 basamak | ~50 | ✓ |
| **7d** | Hourly bucket | Saat sonu kümülatif | ~168 | Scroll gerekli |
| **30d** | Daily bucket | Gün sonu kümülatif | 30 | ✓ Tam sığar |
| **1y** | Weekly bucket | Hafta sonu kümülatif (ISO week) | 52 | ✓ Tam sığar |

**Default:** `30d` — "son ay nasıldım" en sık sorulan, monthly trend en bilgilendirici.

**Identity korunuyor:** her bucket, bucket sonu kümülatif realized PnL'i tutar →
son bucket = toplam realized. Filtre yalnızca görünürlüğü değiştirir, matematik
bozulmaz.

---

## 4. Components

### 4.1 `trade_filter.js` (yeni, presentation)

Tek pure module, iki export.

```js
// static/js/trade_filter.js
(function (global) {
  "use strict";

  const HOURS_BY_PERIOD = { "24h": 24, "7d": 168, "30d": 720, "1y": 8760 };
  const RESOLUTION_BY_PERIOD = {
    "24h": "event", "7d": "hour", "30d": "day", "1y": "week",
  };

  function filterByPeriod(trades, period) {
    if (!trades) return [];
    const hours = HOURS_BY_PERIOD[period];
    if (!hours) return trades;
    const cutoff = Date.now() - hours * 3600 * 1000;
    return trades.filter((t) => {
      const ts = t && t.exit_timestamp ? Date.parse(t.exit_timestamp) : NaN;
      return Number.isFinite(ts) && ts >= cutoff;
    });
  }

  function _isoWeekKey(isoTs) {
    const d = new Date(isoTs);
    if (Number.isNaN(d.getTime())) return null;
    // ISO week: Thursday-based → yıl+hafta
    const tmp = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    const dayNum = tmp.getUTCDay() || 7;
    tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
    const week = Math.ceil(((tmp - yearStart) / 86400000 + 1) / 7);
    return `${tmp.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
  }

  function _bucketKey(isoTs, resolution) {
    if (!isoTs) return null;
    if (resolution === "event") return isoTs;
    if (resolution === "hour")  return isoTs.slice(0, 13);  // YYYY-MM-DDTHH
    if (resolution === "day")   return isoTs.slice(0, 10);  // YYYY-MM-DD
    if (resolution === "week")  return _isoWeekKey(isoTs);
    return isoTs;
  }

  /**
   * Kronolojik sıraya çevirip kümülatif toplar; resolution'a göre bucket'lar.
   * Her bucket'in son kümülatif değeri kazanır (Map overwrite).
   * @returns [{timestamp, value}]
   */
  function cumulativeByResolution(trades, initial, resolution) {
    const chron = [...(trades || [])].reverse();
    const byKey = new Map();
    let running = Number(initial) || 0;
    for (const t of chron) {
      running += Number(t.exit_pnl_usdc || 0);
      const key = _bucketKey(t.exit_timestamp, resolution);
      if (!key) continue;
      byKey.set(key, { timestamp: t.exit_timestamp, value: running });
    }
    return Array.from(byKey.values());
  }

  function periodSum(trades) {
    return (trades || []).reduce(
      (acc, t) => acc + Number(t.exit_pnl_usdc || 0),
      0,
    );
  }

  global.FILTER = {
    filterByPeriod,
    cumulativeByResolution,
    periodSum,
    RESOLUTION_BY_PERIOD,
  };
})(window);
```

**Tüketiciler:**
- `CHARTS.setEquity` → `filterByPeriod` + `cumulativeByResolution` + `periodSum`
- `CHARTS.setWaterfall` → `filterByPeriod` yalnız (bucketing yok; her bar zaten bir trade)

### 4.2 Tab HTML

`templates/dashboard.html` iki `panel-header`'a tab grubu ekler. Total Equity'de
ayrıca tab altı PnL satırı.

```html
<!-- Total Equity -->
<div class="chart-panel">
  <div class="panel-header">
    <span class="card-icon">📈</span> Total Equity
    <div class="chart-tabs" data-chart="equity">
      <button class="chart-tab" data-period="24h">24h</button>
      <button class="chart-tab" data-period="7d">7d</button>
      <button class="chart-tab active" data-period="30d">30d</button>
      <button class="chart-tab" data-period="1y">1y</button>
    </div>
  </div>
  <div class="chart-summary" id="equity-period-summary"></div>
  <div class="chart-fixed">
    <div class="chart-scroll">
      <canvas id="equity-chart"></canvas>
    </div>
  </div>
</div>

<!-- Per Trade PnL -->
<div class="chart-panel">
  <div class="panel-header">
    <span class="card-icon">📊</span> Per Trade PnL
    <div class="chart-tabs" data-chart="pnl">
      <button class="chart-tab" data-period="24h">24h</button>
      <button class="chart-tab" data-period="7d">7d</button>
      <button class="chart-tab active" data-period="30d">30d</button>
      <button class="chart-tab" data-period="1y">1y</button>
    </div>
  </div>
  <div class="chart-fixed">
    <div class="chart-scroll">
      <canvas id="waterfall-chart"></canvas>
    </div>
  </div>
</div>
```

Default aktif: `30d`.

### 4.3 CSS

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
.chart-summary {
  padding: 6px 0 8px;
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.02em;
}
.chart-summary .pnl-pos { color: var(--green); }
.chart-summary .pnl-neg { color: var(--red); }
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

**Palette:** `--panel-hover`, `--muted`, `--text`, `--blue`, `--border-soft`,
`--green`, `--red` hepsi mevcut token (`dashboard.css :root`). Yeni CSS var
eklenmez.

### 4.4 JS state + binding (`dashboard.js`)

```js
const CHART_STATE = { equityPeriod: "30d", pnlPeriod: "30d" };
const LAST = { trades: [] };

const CHART_TAB_BINDING = {
  equity: {
    stateKey: "equityPeriod",
    render: () => CHARTS.setEquity(LAST.trades, INITIAL_BANKROLL),
  },
  pnl: {
    stateKey: "pnlPeriod",
    render: () => CHARTS.setWaterfall(LAST.trades),
  },
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

`_bindChartTabs()` DOMContentLoaded'da tek kez çağrılır.

### 4.5 `setEquity` (Total Equity — bucketing + summary)

```js
setEquity(trades, initialBankroll) {
  const period = CHART_STATE.equityPeriod;
  const resolution = global.FILTER.RESOLUTION_BY_PERIOD[period] || "event";
  const windowTrades = global.FILTER.filterByPeriod(trades, period);
  const points = global.FILTER.cumulativeByResolution(
    windowTrades, initialBankroll, resolution
  );

  this.equity.data.labels = [""].concat(points.map((p) => p.timestamp));
  this.equity.data.datasets[0].data = [Number(initialBankroll) || 0].concat(
    points.map((p) => p.value)
  );

  // Canvas min-width — yoğun ise scroll
  const minWidth = (points.length + 1) * CONFIG.equityBarMinPx;
  this.equity.canvas.style.minWidth = minWidth + "px";

  // Tab-altı özet: "30d  PnL +$123.45  (42 trades)"
  const sum = global.FILTER.periodSum(windowTrades);
  const sumEl = document.getElementById("equity-period-summary");
  if (sumEl) {
    const cls = sum >= 0 ? "pnl-pos" : "pnl-neg";
    const sign = sum >= 0 ? "+" : "−";
    sumEl.innerHTML =
      `${period.toUpperCase()} PnL ` +
      `<span class="${cls}">${sign}$${Math.abs(sum).toFixed(2)}</span> ` +
      `· ${windowTrades.length} trade${windowTrades.length === 1 ? "" : "s"}`;
  }

  this.equity.update("none");
},
```

### 4.6 `setWaterfall` (Per Trade PnL — event filter yalnız)

```js
setWaterfall(trades) {
  const period = CHART_STATE.pnlPeriod;
  const windowTrades = global.FILTER.filterByPeriod(trades, period);
  // En yeni waterfallMaxBars kadar göster (period içinde daha fazlaysa scroll ile gerisi)
  const visible = windowTrades.slice(0, CONFIG.waterfallMaxBars).reverse();
  const MIN_SLOTS = 12;
  const slots = Math.max(visible.length, MIN_SLOTS);
  const labels = new Array(slots).fill("");
  const data = new Array(slots).fill(null);
  visible.forEach((t, i) => {
    labels[i] = FMT.teamsText(t.question, t.slug);
    data[i] = Number(t.exit_pnl_usdc || 0);
  });
  this.waterfall.data.labels = labels;
  this.waterfall.data.datasets[0].data = data;
  this.waterfall.data.datasets[0].backgroundColor =
    data.map((v) => (v == null ? "transparent" : (v >= 0 ? COLORS.green : COLORS.red)));
  this.waterfall.data.datasets[0].hoverBackgroundColor = this.waterfall.data.datasets[0].backgroundColor;

  const minWidth = slots * CONFIG.pnlBarMinPx;
  this.waterfall.canvas.style.minWidth = minWidth + "px";

  // (Mevcut tooltip bloğu olduğu gibi korunur)
  this.waterfall.update("none");
},
```

### 4.7 Refresh akışı

```js
async refresh() {
  try {
    const [status, summary,
           positions, trades, skipped, stock, stats, sportRoi] = await Promise.all([
      API.status(), API.summary(),
      API.positions(), API.trades(), API.skipped(), API.stock(),
      API.stats(), API.sportRoi(),
    ]);
    LAST.trades = trades;  // cache for tab clicks
    RENDER.status(status);
    // ...
    CHARTS.setEquity(LAST.trades, INITIAL_BANKROLL);
    CHARTS.setWaterfall(LAST.trades);
    // ...
  } catch (e) { console.error("Refresh error:", e); }
}
```

### 4.8 CONFIG ekleri

```js
const CONFIG = {
  pollIntervalMs: 5000,
  waterfallMaxBars: 40,     // (mevcut) Per Trade bar üst limiti
  equityBarMinPx: 18,       // (yeni) Total Equity per-point min genişlik
  pnlBarMinPx: 14,          // (yeni) Per Trade per-bar min genişlik
  // ...
};
```

Magic number yok (ARCH Kural 6).

---

## 5. Data Flow

```
refresh() her 5 sn
  ├─ LAST.trades = API.trades()
  ├─ CHARTS.setEquity(LAST.trades, INITIAL_BANKROLL)
  │     ├─ filterByPeriod(trades, CHART_STATE.equityPeriod)
  │     ├─ cumulativeByResolution(windowTrades, initial, resolution)
  │     ├─ canvas.style.minWidth = (pts+1) × equityBarMinPx
  │     └─ chart-summary: periodSum → "30D PnL +$X.XX · N trades"
  └─ CHARTS.setWaterfall(LAST.trades)
        ├─ filterByPeriod(trades, CHART_STATE.pnlPeriod)
        ├─ slice(0, waterfallMaxBars)
        └─ canvas.style.minWidth = slots × pnlBarMinPx

tab click
  ├─ CHART_STATE[key] = period
  └─ binding.render()   ← LAST.trades cache, yeni fetch yok
```

---

## 6. Testing

### 6.1 Pure function tests (manual Jest-pattern, tarayıcı konsolunda)

**`filterByPeriod`:**
- `period="24h"` → yalnız son 24h exit'leri
- `period="1y"` → son 365 gün
- bilinmeyen period → tüm trades (güvenli fallback)
- malformed `exit_timestamp` → o trade elenir

**`cumulativeByResolution`:**
- `resolution="event"` → her trade ayrı nokta, uzunluk = input length
- `resolution="hour"` → aynı saate düşen trade'ler tek noktaya collapse, değer = o saatin son kümülatif'i
- `resolution="day"` → aynı YYYY-MM-DD'ye düşenler tek nokta
- `resolution="week"` → ISO week grouping, yıl geçişlerinde doğru
- Boş input → boş output
- Son nokta value = initial + Σ exit_pnl_usdc (identity test)

**`periodSum`:**
- Boş array → 0
- Karışık pos/neg → doğru toplam
- null exit_pnl_usdc → 0 olarak sayılır

### 6.2 Manual QA checklist

- [ ] Default: her iki chart "30d" tab aktif
- [ ] Tab tıklama → aktif class doğru değişir, diğerleri deaktif
- [ ] 24h: son 24h event-based, her exit bir basamak (Total Equity) / bir bar (Per Trade)
- [ ] 7d: hourly bucket (Total Equity), aynı saatteki exit'ler tek noktaya collapse
- [ ] 30d: daily bucket (Total Equity) → max 30 nokta, ekrana sığar
- [ ] 1y: weekly bucket (Total Equity) → max 52 nokta, ekrana sığar
- [ ] Per Trade 7d/30d/1y'de bar sayısı waterfallMaxBars'ı aşarsa scroll görünür
- [ ] Total Equity tab-altı özet: `30D PnL ±$X.XX · N trades` formatı
- [ ] Özet pozitif → yeşil, negatif → kırmızı, 0 → muted default
- [ ] Boş dönemde chart boş; özet `0D PnL +$0.00 · 0 trades`
- [ ] İki chart bağımsız tab state tutar
- [ ] Refresh (5sn) aktif tab'ı sıfırlamaz
- [ ] Identity: 30d tab'ında chart son y-değeri = initial + sum(exit_pnl in last 30d)

---

## 7. Migration / Compatibility

- Backend değişmez; `/api/trades` mevcut response aynı.
- `equity_history.jsonl` dokunulmaz (chart zaten trade'den besleniyor).
- TDD §5.7.7 güncellenecek: period tab'ları + bucketing pattern notu.

---

## 8. ARCH_GUARD Checklist

- ✓ Katman: yalnızca `presentation/dashboard/static/` + template
- ✓ Domain I/O yok (filter pure function, tarayıcıda çalışır)
- ✓ Dosya boyutu: `trade_filter.js` ~70 satır; `dashboard.js` +~60 satır (mevcut ~400 altında kalır)
- ✓ Magic number yok: HOURS_BY_PERIOD, RESOLUTION_BY_PERIOD, CONFIG token
- ✓ utils/helpers/misc yok: dosya adı `trade_filter.js` (rolü belirgin)
- ✓ Sessiz hata yok: NaN/null timestamp explicit guard, unknown period fallback
- ✓ P(YES) etkilenmez
- ✓ Event-level guard etkilenmez
- ✓ Yeni dependency yok

---

## 9. Risks

- **R1:** Canvas `style.minWidth` Chart.js resize'ıyla çakışabilir → plan'da
  `maintainAspectRatio: false` ve mevcut height constraint'i doğrula.
- **R2:** Chart.js `update("none")` mevcut pattern'i — tab değiştirmede flicker
  olmaması için korunur.
- **R3:** `LAST.trades` cache refresh arası stale olabilir (5sn). Tab tıklaması
  eski cache'i filtreler, yeni refresh'te güncel veri gelir — kabul edilebilir.
- **R4:** ISO week hesabı timezone'a duyarlı — UTC bazında sabit (Date'in UTC
  method'ları) → bot'un all-UTC timestamp konvansiyonuyla tutarlı.
- **R5:** 7d tab'ı hâlâ ~168 nokta → scroll gerekir ama bounded; kullanıcı
  gerçekten haftalık intraday pattern'i görmek için zoom istemiyor mu diye
  kontrol edilecek (ilk kullanım sonrası feedback).

---

## 10. Out of Scope

- **"All" tab**: tarihi sınırsız → ölçeklenemez; lifetime PnL zaten Balance/
  Realized PnL kart(lar)ında var.
- **Custom date range picker**: YAGNI.
- **Export chart as image**: ayrı feature.
- **Peak/drawdown'ın period'a göre yeniden hesaplanması**: ayrı concern.
- **Total Equity starting value per period**: her tab'da `initial=$1000`'dan
  başlar + o dilimdeki cumsum. "Son 7 günde $1000'dan $X'e ne kazandım" mental
  modeli kullanıcıya uygun.
- **Per Trade PnL bucketing** (daily net PnL mode): bar'lar zaten per-trade
  semantiğe sahip; bucketing çizginin anlamını değiştirir → ayrı chart olarak
  gerekiyorsa gelecekte eklenir.

---

## 11. Lokasyon özeti

**Yeni:**
- `src/presentation/dashboard/static/js/trade_filter.js`

**Modify:**
- `src/presentation/dashboard/templates/dashboard.html` — iki panel header + tab grubu; Total Equity için `#equity-period-summary` + chart-scroll sarmal
- `src/presentation/dashboard/static/css/dashboard.css` — `.chart-tabs`, `.chart-tab`, `.chart-scroll`, `.chart-summary` + `.panel-header` space-between
- `src/presentation/dashboard/static/js/dashboard.js` — CONFIG ek (equityBarMinPx, pnlBarMinPx), `CHART_STATE`, `LAST`, `_bindChartTabs`, `setEquity` (bucketing + summary), `setWaterfall` (filter + scroll min-width), refresh akışında `LAST.trades` cache
- `TDD.md §5.7.7` — period tabs + adaptif bucketing pattern notu
