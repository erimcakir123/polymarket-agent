# Calibration Sport Filter — Design

**Tarih:** 2026-06-07
**Durum:** APPROVED (kullanıcı onayı: "go", 2026-06-07)

## Problem

Dashboard "Model Accuracy" (calibration) grafiği tüm sporları tek karnede karıştırıyor
([routes.py:141](../../../src/presentation/dashboard/routes.py) — `read_trades` spor filtresi yok).
"Predicted" değeri botun karar anchor'ı (`anchor_probability`): basketbolda bahisçi
konsensüsü, tenniste yer yer bahisçi yer yer kendi model — farklı motorlar tek grafikte.
Sapma görülürse hangi sporun/motorun bozuk olduğu ayırt edilemiyor.

## Çözüm

Grafiğin üstüne spor sekmesi: "Hepsi" (varsayılan) + veride bulunan her spor (dinamik).
Sekme seçimi hem scatter matrisini hem 4 kovayı süzer. 30-işlem eşiği değişmez.

## Kapsam

**Dahil:**
- `computed_calibration.calibration_report(trades, sport="all")` — sport param + `available_sports` çıktısı
- `/api/calibration` route — `?sport=` query param okuma
- Frontend: dinamik sekme çizimi, tıklama → refetch, seçili sekme state

**Dışında (YAGNI):** Eşik düşürme, ayrı 2. grafik, diğer bölümlere filtre.

## Davranış

### Backend — `calibration_report(trades, sport="all")`
1. `available_sports`: TÜM trade'lerden (filtreden ÖNCE) branş kümesi.
   `computed._sport_category(t)` ile (aynı paket/katman, lig→branş map'inin SAHİBİ —
   kopyalamak drift riski, DRY için yeniden kullanılır). "unknown" hariç, sıralı liste.
2. `sport != "all"` ise trade'ler `_sport_category(t) == sport` ile süzülür, sonra
   mevcut bin mantığı aynen.
3. Yanıta eklenir: `available_sports: list[str]`, `selected_sport: str`.

### Route — `/api/calibration`
- `sport = request.args.get("sport", "all")` → `calibration_report(trades, sport)`.

### Frontend — `dashboard.js`
- `API.calibration(sport)` → `/api/calibration?sport=<sport>`.
- Sekme şeridi `available_sports`'tan çizilir; başa "all" = "Hepsi".
- Tıklama → seçili spor state'e yazılır, calibration yeniden çekilip render edilir.
- Otomatik yenilemede (Promise.all) seçili spor korunur.
- Spor etiketi gösterimi: ilk harf büyük (tennis → Tennis, basketball → Basketball).

### HTML/CSS — `dashboard.html`
- Calibration kartı başlığının altına sekme konteyneri + aktif sekme stili.

## Layer / ARCH_GUARD doğrulaması
- computed_calibration → computed `_sport_category`: aynı paket (presentation/dashboard),
  katman ihlali yok. computed, computed_calibration'ı import etmez → circular yok.
- Eşik (`_MIN_TRADES_PER_BIN=30`) sabit kalır — magic number yok (Kural 6).
- Dosya boyutu: computed_calibration ~125 satır (<400, Kural 3).
- Sessiz hata yok: eksik sport_tag açıkça atlanır (Kural 12).

## Test (TDD)
- `test_calibration_report_sport_all_returns_available_sports`
- `test_calibration_report_sport_filter_excludes_other_sports`
- `test_calibration_report_unknown_sport_returns_empty_bins`
- `test_calibration_report_missing_sport_tag_skipped_from_available`

## Dokunulan dosyalar
- `src/presentation/dashboard/computed_calibration.py`
- `src/presentation/dashboard/routes.py`
- `src/presentation/dashboard/static/js/dashboard.js`
- `src/presentation/dashboard/templates/dashboard.html`
- `tests/unit/presentation/dashboard/test_computed_calibration.py` (yeni/güncel)
