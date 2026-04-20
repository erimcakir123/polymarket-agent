# SPEC — Spesifikasyonlar

> Bu dosya aktif teknik spesifikasyonları içerir.
> Bir spec entegre edilip onaylandıktan sonra bu dosyadan **SİLİNİR**.
> Sadece aktif, henüz koda dönüşmemiş spec'ler burada durur.

---

## Nasıl Kullanılır

### Spec Ekleme
```
1. Bir özellik veya modül için detaylı spec yaz (aşağıdaki formata uy)
2. Durum: DRAFT
3. Review + onay → durum: APPROVED
4. Kod yazılıp test edildikten sonra → durum: IMPLEMENTED → sil
```

### Spec Formatı
```
### SPEC-XXX: [Modül/Özellik adı]
- **Durum**: DRAFT | APPROVED | IMPLEMENTED
- **Tarih**: YYYY-MM-DD
- **İlgili Plan**: PLAN-XXX
- **Katman**: domain | strategy | infrastructure | orchestration | presentation
- **Dosya**: src/katman/modul.py

#### Amaç
Modülün ne yaptığı, tek cümle.

#### Girdi/Çıktı
- Girdi: ...
- Çıktı: ...

#### Davranış Kuralları
1. ...
2. ...

#### Sınır Durumları (Edge Cases)
- ...

#### Test Senaryoları
- ...
```

---

## Aktif Spesifikasyonlar

### SPEC-007: Trade History Modal (All Trades)
- **Durum**: DRAFT
- **Tarih**: 2026-04-18
- **Katman**: presentation
- **Dosyalar**:
  - `src/presentation/dashboard/static/js/trade_history_modal.js` (YENİ)
  - `src/presentation/dashboard/static/css/modal.css` (YENİ)
  - `src/presentation/dashboard/templates/dashboard.html` (GÜNCELLEME)
  - `src/presentation/dashboard/routes.py` (GÜNCELLEME)
  - `src/presentation/dashboard/readers.py` (GÜNCELLEME)

#### Amaç
Tüm trade geçmişini tarihsel sırayla görüntüleyen, haftalık pagination ile lazy-load eden full-screen modal. Mevcut chart tab'larındaki zaman filtrelemesi özet grafikler için yeterli; tek tek trade detayı bu modal'dan görülür.

#### Kullanıcı Akışı

1. Chart panel header'ında (Total Equity veya Per Trade PnL başlığının yanında, tab butonlarından önce) küçük bir **"All" butonu** (mavi daire ikonu ile tutarlı konum)
2. Tıklayınca **full-screen modal** açılır:
   - Arka plan koyu overlay (`rgba(0,0,0,0.85)`)
   - Modal neredeyse ekran genişliğinde (`width: 94vw, max-width: 1400px`)
   - Üst başlık: "Trade History" + `[X]` kapat butonu
   - Hafta navigasyonu: `◄ Önceki Hafta | Bu Hafta (14-18 Nis 2026) | Sonraki Hafta ►`
   - PnL bar chart (full-width, event-level — her bar bir trade)
   - Altında trade tablosu (her trade bir satır)
3. Sola kaydırma / `◄` tıklama: önceki haftayı yükler (lazy load)
4. `►` butonu en güncel haftadayken gizli
5. `X` veya overlay tıklama veya `Escape` ile kapat

#### UI Layout (Modal İçi)

```
┌──────────────────────────────────────────────────────────────┐
│  Trade History                                          [X]  │
│  ◄  Bu Hafta (14 - 18 Nis 2026)                          ►  │
│─────────────────────────────────────────────────────────────│
│  ██ █ ██ █ ██ █ ██ █   (PnL bar chart — full width)        │
│─────────────────────────────────────────────────────────────│
│  Tarih        Maç                    PnL      Reason        │
│  18 Nis 15:42  Boston vs NY Yankees  +$12.30  tp_hit        │
│  18 Nis 14:10  Tampa Bay vs Toronto  -$8.50   sl_hit        │
│  18 Nis 11:05  LA vs San Diego       +$22.10  near_resolve  │
│  17 Nis 20:30  Chicago vs Detroit    +$5.80   scale_out_t1  │
│  ...                                                        │
│  Toplam: +$31.70 (12 trade, 8W/4L)                         │
└──────────────────────────────────────────────────────────────┘
```

#### Backend: Paginated Trades Endpoint

**Yeni endpoint**: `GET /api/trades/history?week_offset=0`

- `week_offset=0` → bu hafta (Pazartesi 00:00 UTC — Pazar 23:59 UTC)
- `week_offset=1` → geçen hafta
- `week_offset=N` → N hafta öncesi

**Response**:
```json
{
  "trades": [...],
  "week_label": "14 - 18 Apr 2026",
  "week_offset": 0,
  "has_older": true,
  "total_in_week": 35
}
```

**Backend logic** (`readers.py`):
- `read_trades_by_week(logs_dir, week_offset)` — trade_history.jsonl'den ilgili haftanın kayıtlarını filtreler
- Mevcut `_read_jsonl_tail` yetersiz (sadece son N satır okuyabiliyor); yeni fonksiyon dosyanın **tamamını** okumaz — önce tail ile yeterince büyük pencere çeker, sonra timestamp filtresi uygular
- Haftalık trade sayısı genelde 50-150 arası — performans sorunu yok
- `computed.exit_events()` ile partial scale-out'lar flatten edilir (mevcut mantık)

**Readers.py değişiklik**:
```python
def read_trades_by_week(logs_dir: Path, week_offset: int = 0) -> tuple[list[dict], str, bool]:
    """Belirtilen haftanın trade'lerini döner.
    
    Returns: (trades, week_label, has_older)
    """
```

**Routes.py değişiklik**:
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

#### Frontend: trade_history_modal.js (YENİ dosya)

**Namespace**: `TRADE_HISTORY` (global)

**Sorumluluklar**:
1. Modal DOM oluşturma + overlay
2. PnL bar chart (Chart.js, mevcut COLORS kullanır)
3. Trade tablosu render
4. Haftalık navigation + lazy load
5. Keyboard (Escape) + overlay click close

**Chart**: Mevcut `CHARTS._initBar` ile aynı config — ancak modal'ın kendi Chart instance'ı (ana sayfadakiyle karışmaz). Full-width, scroll yok (haftalık trade sayısı 50-150 = ekrana sığar).

**Trade tablosu**: Her satır:
- Tarih/saat (UTC → local)
- Maç adı (FMT.teamsText kullanır)
- Branş ikonu (ICONS kullanır)
- PnL (yeşil/kırmızı, FMT.usdSignedHtml)
- Exit reason (human-readable)
- Direction badge (YES/NO)

**Hafta navigasyonu**:
- `◄` butonu: `week_offset++`, API çağrısı, re-render
- `►` butonu: `week_offset--`, API çağrısı, re-render (offset=0'da gizli)
- Hafta label'ı API'dan gelir

**Dependency**: `FMT`, `ICONS`, `COLORS` (dashboard.js'ten expose edilen) kullanır. Yeni bağımlılık yok.

#### Frontend: modal.css (YENİ dosya)

CSS ayrı dosya — dashboard.css zaten 417 satır (sınırda). Modal stilleri:
- `.modal-overlay`: fixed, full screen, `rgba(0,0,0,0.85)`, z-index: 1000
- `.modal-container`: `94vw`, `max-height: 90vh`, koyu panel arka plan
- `.modal-header`: flex, başlık + close butonu
- `.modal-nav`: hafta navigasyonu
- `.modal-chart`: chart alanı
- `.modal-table`: trade tablosu (scrollable)
- Renk referansları `var(--*)` ile (hex literal yasak, TDD §5.7.4)

#### dashboard.html Değişiklik

1. Modal CSS link'i eklenir (`<link>` tag)
2. `trade_history_modal.js` script tag'i eklenir (dashboard.js'ten sonra)
3. Chart panel header'larına "All" butonu eklenir:

```html
<div class="panel-header">
  <span>Per Trade PnL</span>
  <button class="modal-trigger" id="btn-trade-history" title="All trades">All</button>
  <div class="chart-tabs" data-chart="pnl">...</div>
</div>
```

"All" butonu sadece **bir** chart panel'e konur (Per Trade PnL — daha doğal konum). Total Equity panel'ine koymaya gerek yok.

#### dashboard.js Değişiklik

`COLORS` objesini `window.COLORS` olarak expose et (modal JS'in kullanması için):
```javascript
// MAIN.init() içinde, _initColors() sonrasında:
global.COLORS = COLORS;
```

Bu tek satırlık değişiklik — dashboard.js'e yeni fonksiyon eklenmez.

#### Sınır Durumları

1. **Trade yok (boş hafta)**: "Bu haftada trade yok" mesajı gösterilir, chart gizli
2. **İlk hafta (en eski veri)**: `has_older=false` → `◄` butonu disabled
3. **Çok fazla trade (>100/hafta)**: Haftalık bazda 100+ trade olası değil (bot max 50 slot × 30dk cycle) — UI sınırı gereksiz
4. **Modal açıkken poll refresh**: Ana sayfa poll devam eder ama modal kendi verisini yönetir — çakışma yok
5. **Partial scale-out**: `exit_events()` ile flatten — her partial ayrı satır, "scale_out_t1/t2" reason ile gösterilir
6. **Escape tuşu**: Modal kapatır (global keydown listener, modal açıkken aktif)

#### Test Senaryoları

**Backend (unit)**:
- `test_read_trades_by_week_current_week`: Bu haftanın trade'lerini doğru filtreler
- `test_read_trades_by_week_past_week`: Geçmiş haftayı doğru filtreler
- `test_read_trades_by_week_empty`: Trade olmayan haftada boş liste döner
- `test_read_trades_by_week_has_older_flag`: Daha eski trade varsa `has_older=True`
- `test_trades_history_endpoint_returns_json`: `/api/trades/history` doğru format döner

**Frontend (manual test):**
- Modal açılıp kapanır (X, Escape, overlay click)
- Hafta navigasyonu çalışır (◄ ► butonları)
- Trade tablosu doğru render edilir
- PnL bar chart barları doğru renkte
- Responsive — dar ekranda table scroll
- Ana sayfa poll modal açıkken çalışmaya devam eder

#### Satır Tahminleri

| Dosya | Değişiklik | Satır |
|---|---|---|
| `static/js/trade_history_modal.js` | YENİ | ~200 satır |
| `static/css/modal.css` | YENİ | ~80 satır |
| `templates/dashboard.html` | GÜNCELLEME (+3 satır: CSS link, JS script, All butonu) | +3 |
| `routes.py` | GÜNCELLEME (+1 endpoint) | +8 |
| `readers.py` | GÜNCELLEME (+1 fonksiyon: `read_trades_by_week`) | +30 |
| `dashboard.js` | GÜNCELLEME (COLORS expose — 1 satır) | +1 |
| **Test** | `tests/unit/presentation/test_readers_week.py` | ~60 satır |
| **Toplam yeni kod** | | ~380 satır |

Tüm dosyalar 400 satır altında. Katman kuralları korunuyor (sadece presentation).

