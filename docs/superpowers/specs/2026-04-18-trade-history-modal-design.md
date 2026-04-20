# SPEC-007: Trade History Modal (All Trades)

> **Durum**: APPROVED
> **Tarih**: 2026-04-18
> **Katman**: presentation
> **Scope**: dashboard-only — bot core'a dokunmaz

---

## 1. Amaç

Tüm trade geçmişini tarihsel sırayla görüntüleyen, haftalık pagination ile
lazy-load eden full-screen modal. Mevcut chart tab'larındaki zaman filtrelemesi
özet grafikler için yeterli; tek tek trade detayı bu modal'dan görülür.

**Ek görev**: `dashboard.js` 412 satır → ARCH_GUARD Kural 3 ihlali. Idle
countdown bloğunu `chart_tabs.js`'e taşıyarak her iki dosyayı 400 altında tut.

---

## 2. Kullanıcı Akışı

1. Per Trade PnL panel header'ında "All" butonu (tab'lardan önce).
2. Tıklayınca full-screen modal açılır:
   - Koyu overlay (`rgba(0,0,0,0.85)`)
   - Geniş modal (`94vw`, `max-height: 90vh`)
   - Üst: "Trade History" başlık + `[X]` kapat
   - Hafta nav: `◄ | Bu Hafta (14 - 18 Nis 2026) | ►`
   - PnL bar chart (full-width, event-level — her bar bir trade)
   - Trade tablosu (her trade bir satır)
   - Haftalık özet satırı
3. `◄` tıklama: önceki haftayı yükler (API call)
4. `►` en güncel haftadayken gizli
5. Kapatma: `X`, `Escape`, overlay click

---

## 3. Modal UI Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Trade History                                          [X]  │
│  ◄  Bu Hafta (14 - 18 Nis 2026)                          ►  │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ +$31.70  │  │   67%    │  │    12    │                   │
│  │ Weekly PnL│  │ Win Rate │  │  Trades  │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
│                                                              │
│  ██ █ ██ █ ██ █ ██ █   (PnL bar chart — full width)        │
│─────────────────────────────────────────────────────────────│
│  Tarih        Maç               Hold   PnL    Reason        │
│  18 Nis 15:42  BOS vs NYY       4h 12m +$12   🎯 Take Profit│
│  18 Nis 14:10  TB vs TOR        1h 05m -$8    🛑 Stop Loss  │
│  18 Nis 11:05  LA vs SD         6h 30m +$22   ⏰ Near Resolv│
│  17 Nis 20:30  CHI vs DET       2h 14m +$5    📊 Scale T1   │
│  ...                                                        │
└──────────────────────────────────────────────────────────────┘
```

### Hero Metrikler (3 kart)

Chart'ın üstünde, hafta nav'ın altında. Haftalık veriden hesaplanır (client-side).

| Kart | Hesaplama | Format |
|---|---|---|
| Weekly PnL | `Σ exit_pnl_usdc` | `FMT.usdSignedHtml()`, yeşil/kırmızı |
| Win Rate | `wins / total × 100` | `XX%`, yeşil (≥50) / kırmızı (<50) |
| Trades | `trades.length` | sayı |

### Trade Tablosu Kolonları

| Kolon | Kaynak | Format |
|---|---|---|
| Tarih | `exit_timestamp` | `DD Mon HH:MM` (local) |
| Branş | `sport_tag` | ICONS emoji |
| Maç | `question` + `slug` | `FMT.teamsText()` |
| Yön | `direction` | YES/NO badge |
| Hold | `exit_timestamp - entry_timestamp` | `Xh Ym` (saat+dakika) |
| PnL | `exit_pnl_usdc` | `FMT.usdSignedHtml()`, yeşil/kırmızı |
| Reason | `exit_reason` | emoji + label + renk (badge) |

### Exit Reason Badge Mapping

| Raw value | Badge | Renk |
|---|---|---|
| `tp_hit` | 🎯 Take Profit | yeşil |
| `sl_hit` | 🛑 Stop Loss | kırmızı |
| `graduated_sl` | 🛑 Grad. SL | kırmızı |
| `scale_out_tier_1` | 📊 Scale T1 | sarı (orange) |
| `scale_out_tier_2` | 📊 Scale T2 | sarı (orange) |
| `near_resolve` | ⏰ Near Resolve | mavi |
| `market_flip` | 🔄 Market Flip | kırmızı |
| `score_exit` | ⚡ Score Exit | kırmızı |
| `hold_revoked` | ⚠️ Hold Revoked | kırmızı |
| `catastrophic_bounce` | 💥 Catastrophic | kırmızı |
| `manual` | ✋ Manual | muted |
| (diğer) | raw value as-is | muted |

Badge renkleri `var(--green)`, `var(--red)`, `var(--orange)`, `var(--blue)`,
`var(--muted)` ile — hex literal yasak.

---

## 4. Backend: Paginated Trades Endpoint

### Yeni endpoint: `GET /api/trades/history?week_offset=0`

- `week_offset=0` → bu hafta (Pazartesi 00:00 UTC — Pazar 23:59 UTC)
- `week_offset=1` → geçen hafta
- `week_offset=N` → N hafta öncesi

### Response

```json
{
  "trades": [...],
  "week_label": "14 - 18 Apr 2026",
  "week_offset": 0,
  "has_older": true,
  "total_in_week": 35
}
```

### readers.py — `read_trades_by_week()`

```python
def read_trades_by_week(
    logs_dir: Path, week_offset: int = 0
) -> tuple[list[dict], str, bool]:
    """Belirtilen haftanın trade'lerini döner.

    Strateji: tail ile son N*7 haftanın olası satır sayısı kadar oku,
    timestamp filtrele. Haftalık ~100-150 trade olduğu varsayılır.

    Returns: (trades_in_week, week_label_str, has_older_data)
    """
```

Hafta sınırı ISO week (Pazartesi-Pazar, UTC). `week_label` formatı:
`"DD - DD Mon YYYY"` (ör. `"14 - 18 Apr 2026"`). Ay geçişinde:
`"28 Apr - 04 May 2026"`.

`has_older`: Filtrelenen haftanın başlangıcından ÖNCEki timestamp'li trade
var mı? Yoksa `◄` butonunu gizle.

### routes.py — endpoint

```python
@app.route("/api/trades/history")
def api_trades_history():
    offset = request.args.get("week_offset", 0, type=int)
    trades, label, has_older = readers.read_trades_by_week(logs_dir, offset)
    events = computed.exit_events(trades)
    return jsonify({
        "trades": events,
        "week_label": label,
        "week_offset": offset,
        "has_older": has_older,
        "total_in_week": len(events),
    })
```

---

## 5. Frontend: trade_history_modal.js (YENİ)

**Namespace**: `TRADE_HISTORY` (global)

### Sorumluluklar

1. Modal DOM oluşturma (overlay + container, JS ile inject)
2. Hero metrikler hesaplama + render (client-side, API'dan gelen trade'lerden)
3. PnL bar chart (Chart.js — kendi instance, `COLORS` kullanır)
4. Trade tablosu render (hold time + reason badge dahil)
5. Haftalık navigation + lazy load
6. Keyboard (Escape) + overlay click close

### Chart Detayları

- Mevcut `CHARTS._initBar` ile aynı config (bar radius, max thickness)
- Modal'ın kendi Chart instance'ı — ana sayfadakiyle karışmaz
- Full-width, scroll yok (haftalık trade sayısı 50-150 = ekrana sığar)
- Barlar: yeşil (kâr), kırmızı (zarar)

### Dependency

`FMT`, `ICONS`, `COLORS` (mevcut global namespace'ler) kullanır.
Yeni bağımlılık yok. Chart.js zaten yüklü.

### Buton Wiring

Modal kendi `DOMContentLoaded` handler'ında `#btn-trade-history`'ye click
listener bağlar. Dashboard.js'e hiçbir şey eklenmez (COLORS expose hariç).

---

## 6. Frontend: modal.css (YENİ)

Dashboard.css zaten 417 satır (sınırda). Modal stilleri ayrı dosya.

### Temel Sınıflar

| Class | Amaç |
|---|---|
| `.modal-overlay` | fixed, full screen, koyu backdrop, z-index: 1000 |
| `.modal-container` | 94vw, max-height 90vh, koyu panel, border-radius |
| `.modal-header` | flex, başlık + close butonu |
| `.modal-nav` | hafta navigasyonu, ortalı, oklar + label |
| `.modal-chart-wrap` | chart container, min-height 180px |
| `.modal-table` | trade tablosu, overflow-y auto |
| `.modal-hero` | 3-kart hero metrik satırı (flex, gap) |
| `.modal-hero-card` | tek hero kart (PnL / Win Rate / Trades) |
| `.modal-reason` | exit reason badge (emoji + label + renk) |
| `.modal-trigger` | "All" butonu stili |

Renk referansları `var(--*)` ile — hex literal yasak (TDD §5.7.4).

---

## 7. dashboard.js Fix (412 → ~399 satır)

### Taşınacak Blok

`dashboard.js` satır 400-412 (idle countdown timer):

```javascript
let _lastStatusData = null;
const _origStatus = RENDER.status.bind(RENDER);
RENDER.status = function (data) {
  _lastStatusData = data;
  _origStatus(data);
};
setInterval(() => {
  if (_lastStatusData) _origStatus(_lastStatusData);
}, CONFIG.idleTickMs);
```

### Hedef: chart_tabs.js

Bu blok RENDER.status'u wrap edip 1s timer ile re-render ediyor. `bind()`
fonksiyonunun deps parametresine `render` + `config` eklenerek chart_tabs
içinde init edilir.

### Sonuç

- `dashboard.js`: ~399 satır (COLORS expose +1, idle blok -13 = net -12)
- `chart_tabs.js`: ~108 satır (idle blok +13)
- Her ikisi 400 altında ✓

---

## 8. dashboard.html Değişiklikleri

1. `<link>` tag: `modal.css`
2. `<script>` tag: `trade_history_modal.js` (dashboard.js'ten sonra)
3. Per Trade PnL panel header'ına "All" butonu:

```html
<div class="panel-header">
  <span>Per Trade PnL</span>
  <button class="modal-trigger" id="btn-trade-history" title="All trades">All</button>
  <div class="chart-tabs" data-chart="pnl">...</div>
</div>
```

---

## 9. Sınır Durumları

| Durum | Davranış |
|---|---|
| Boş hafta (trade yok) | "Bu haftada trade yok" mesajı, chart gizli |
| En eski hafta | `has_older=false` → `◄` disabled |
| En güncel hafta | `►` gizli |
| Modal açıkken poll refresh | Ana sayfa poll devam, modal kendi verisini yönetir |
| Partial scale-out | `exit_events()` flatten — ayrı satır, "scale_out_t1/t2" reason |
| Escape tuşu | Modal kapatır (keydown listener) |
| Overlay click | Modal kapatır |

---

## 10. Test Senaryoları

### Backend (unit — `tests/unit/presentation/test_readers_week.py`)

- `test_read_trades_by_week_current_week`: Bu haftanın trade'leri doğru filtre
- `test_read_trades_by_week_past_week`: Geçmiş hafta doğru filtre
- `test_read_trades_by_week_empty`: Boş haftada `([], label, has_older)`
- `test_read_trades_by_week_has_older_flag`: Eski trade varsa `True`
- `test_read_trades_by_week_label_format`: Label formatı doğru
- `test_trades_history_endpoint_returns_json`: Endpoint doğru format döner

### Frontend (manual)

- Modal açılıp kapanır (X, Escape, overlay click)
- Hafta navigasyonu çalışır
- Trade tablosu doğru render
- PnL bar chart barları doğru renkte
- Ana sayfa poll modal açıkken çalışmaya devam eder

---

## 11. Dosya Değişiklik Özeti

| Dosya | İşlem | Satır |
|---|---|---|
| `static/js/trade_history_modal.js` | YENİ | ~250 |
| `static/css/modal.css` | YENİ | ~100 |
| `templates/dashboard.html` | GÜNCELLEME | +3 |
| `routes.py` | GÜNCELLEME (+1 endpoint) | +8 |
| `readers.py` | GÜNCELLEME (+1 fonksiyon) | +30 |
| `dashboard.js` | idle bloğu taşı + COLORS expose | -12 |
| `chart_tabs.js` | idle bloğu al | +13 |
| `tests/unit/presentation/test_readers_week.py` | YENİ | ~60 |
| **Toplam** | | ~380 |

Tüm dosyalar 400 satır altında. Sadece presentation katmanı.
