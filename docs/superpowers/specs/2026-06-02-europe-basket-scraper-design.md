# Avrupa Basket Scraper'lar (SPEC)

> Tarih: 2026-06-02
> Spec ID: SPEC-EUROBASKET-001
> Status: DRAFT (plan onaylanınca aktif)

---

## Problem

Polymarket'te aktif Avrupa basket maçları var (Türkiye BSL Fenerbahçe-Anadolu Efes, İspanya Liga Endesa Valencia-Bilbao, Rusya VTB Zenit-Lokomotiv Kuban, İtalya Lega vs.) ama bot **trade edemiyor** çünkü:

1. **`allowed_sport_tags`'a eklenmemiş** (sadece nba, wnba, ncaab, euroleague, vs.)
2. **Model rating'i yok** — Sackmann-tipi geçmiş maç veritabanı bu ligler için kurulmamış
3. **Odds API yedeği yok** — The Odds API basketball_nba/wnba/ncaab/euroleague destekliyor ama BSL/ACB/Lega/VTB yok (kanıt: `src/domain/matching/odds_sport_keys.py`)
4. **BRScraper denedi başarısız** — 29 May `436c0d7` commit'i BRScraper Python paketi ile denedi, paket `[]` (sahte placeholder) dönüyordu, aynı gün `d93edc7` ile silindi

Şu an Polymarket'te bu maçlar TRADE EDİLEMİYOR. Aktif Haziran finalleri kaçırılıyor.

## Hedef

Aşağıdaki Avrupa basket ligleri için **kendi scraper'larımızı yaz** + **NO_DATA_NO_TRADE prensibi** + **Telegram health alert entegrasyonu**:

| Lig | Ülke | Kaynak (planlanmış) | Sezon |
|---|---|---|---|
| **Liga ACB / Endesa** | İspanya | `acb.com` HTML scrape | Eylül-Haziran (final Haziran) |
| **Türkiye BSL** | Türkiye | `tbf.org.tr` veya `tblstat.com` HTML scrape | Ekim-Haziran (final Haziran) |
| **Lega Basket Serie A** | İtalya | `legabasket.it` HTML scrape | Ekim-Haziran (final Haziran) |
| **VTB United League** | Rusya | `vtb-league.com` HTML scrape | Eylül-Haziran |

## Kritik Prensipler

### 1. NO_DATA_NO_TRADE

Scraper'ın **hiçbir hatalı koşulda** bot'a yanlış veri geçirmesine izin verme:

| Senaryo | Davranış |
|---|---|
| Site ban / 403 / 429 | Cache son veri (≤ 48h) kullan; > 48h → SCRAPER_STALE → tüm o lig trade SKIP |
| HTTP timeout (3 retry sonrası) | Cache fallback (yukarıdaki kural) |
| HTML format değişti (parser fail) | Health flag "broken" → telegram critical alert + tüm trade SKIP |
| 0 game data (sezon dışı varsayım) | Lig SKIP (silent — sezon dışı durumlar için normal) |
| Eksik takım (yeni promosyon) | Sadece o takım için `MODEL_TEAM_NOT_IN_RATINGS` fail; diğer takımlar trade edilebilir |
| Şüpheli data (örn. rating < 800 veya > 2400) | Outlier filter → alert + o takım için trade SKIP |

### 2. Health Monitor Entegrasyonu (Plan 2 sayesinde)

Her scraper `data/basketball_cache/_health/sources_status.json`'a state yazar:

```json
{
  "acb": {"state": "healthy", "last_success": "2026-06-02T15:00", "last_fail": null, "rating_count": 18},
  "bsl": {"state": "broken", "last_success": "2026-06-01T08:00", "last_fail": "2026-06-02T18:00", "error": "HTML parse fail"},
  "lega": {"state": "stale", "last_success": "2026-05-31T10:00", "last_fail": "2026-06-02T17:30", "error": "HTTP 429"},
  "vtb": {"state": "healthy", "last_success": "2026-06-02T14:00", "last_fail": null, "rating_count": 12}
}
```

HealthMonitor (Plan 2) bu dosyayı 5dk'da bir okur. State `broken` veya `stale` ise telegram critical alert gönderir.

### 3. Pattern Sport-Agnostic

Yeni lig eklemek 1 günlük iş olmasın:
- Her scraper aynı base class'tan türer (`EuropeanBasketScraper`)
- Override sadece: `_fetch_html()`, `_parse_teams()`, `_parse_games()`
- Refresh, retry, health update, rating update generic

### 4. Odds API Yedek YOK Bu Ligler İçin

The Odds API bu ligleri vermiyor. Bizim modelimiz **tek kaynak**. Scraper başarısız olursa **trade YOK** (Odds yedeği yok, fallback yok).

## Mimari

### Bileşenler

```
src/infrastructure/data/basketball/
  base_scraper.py              (YENİ — abstract base class)
  acb_scraper.py               (YENİ — İspanya Liga Endesa)
  bsl_scraper.py               (YENİ — Türkiye BSL)
  lega_scraper.py              (YENİ — İtalya Lega)
  vtb_scraper.py               (YENİ — Rusya VTB)
  data_source_health.py        (mevcut, broken state'e set genişletme)
  refresh_runner.py            (mevcut, yeni scraper'lar register)

src/domain/matching/
  basketball_team_resolver.py  (mevcut, yeni ligler için _TEAMS dict ekle)

src/strategy/enrichment/
  basketball_dispatch.py       (mevcut, _BASKETBALL_LEAGUES'a yeni ligler ekle)

src/orchestration/
  factory_basketball.py        (mevcut, ratings build hook'a yeni ligler)

config.yaml
  basketball.enabled_leagues   (acb, bsl, lega, vtb ekle)
  basketball.leagues           (her lig için home_advantage, k_factor, vs.)

scripts/
  build_european_basket_ratings.py  (YENİ — manuel build script)
```

### Veri Akışı

1. **Bootstrap** (factory_basketball._maybe_invoke_basketball_refresh):
   - Her enabled lig için: scraper.refresh() çağır
   - Başarılı → rating cache güncelle + health "healthy"
   - Başarısız → health "broken" (3 fail sonra) veya "stale" (cache var ama eski)
   - HealthMonitor periyodik kontrol → telegram alert

2. **Scanner** (eligible filter):
   - Polymarket slug `acb-rea-la-2026-06-15` veya `bsl-fb-efes-2026-06-15` geldi
   - `_SLUG_PREFIX_SPORT` mapping: `acb → liga_acb`, `bsl → turkey_bsl`, `lega → italy_lega`, `vtb → vtb`
   - `allowed_sport_tags` kontrol → kabul

3. **Dispatch** (basketball_dispatch):
   - Sport_tag basketball lig → `enrich_basketball_from_model` çağır
   - Ratings yüklenmiş ise model çalışır
   - Cache stale veya broken → ratings boş → `MODEL_BASKETBALL_DATA_MISSING` skip
   - Trade edilmez (Odds API yedeği YOK — kasıtlı)

### Glicko Rating Build (her lig için)

Sackmann pattern paralel:
- Son 2 sezon maç sonuçları (HTML scrape veya CSV)
- Her maç için K-factor güncellemesi (Elo)
- Output: `data/basketball_cache/<lig>_ratings.json` (mevcut format, JSON list)

K-factor + home_advantage liglere göre kalibre edilir (Avrupa basket NBA'dan farklı pace).

## Out of Scope

- Live score scraper (sadece pre-match rating; live score ESPN üzerinden zaten ayrı)
- Player-level stats (sadece team Elo)
- In-season trade rumor parsing (sadece son maç sonuçları)
- Selenium / browser automation (sadece HTTP + HTML parse — requests + BeautifulSoup)

## Risk

| Risk | Mitigation |
|---|---|
| Site DDoS protection / ban | User-Agent rotation, polite rate limit (1 req/2sec), retry exponential backoff |
| HTML değişimi | Schema versioning, parser fail → broken state → alert + skip |
| Veri yanlışlığı (örn. yanlış sonuç) | Outlier filter (Elo rating < 800 veya > 2400 → reject) |
| Sezon başlangıcı (yeni takım) | "Rating yok" → MODEL_TEAM_NOT_IN_RATINGS skip (kasıtlı) |
| Maintenance window | 48h cache TTL — kısa süre düşüş tolere edilir |

## Telegram Alert Senaryoları

- 🔴 **Critical**: Scraper 3 ardışık fail (broken state) → "ACB scraper 3 saattir down, trade yapılmıyor"
- ⚠️ **Warning**: Cache > 24h (stale state) → "BSL cache 30 saattir güncelenmedi"
- 🟢 **Info**: Bootstrap'ta her scraper sonucu → "Avrupa basket scraper sonuçları: ACB ✓, BSL ✓, Lega ✗, VTB ✓"

## Done Definition

- 4 scraper (ACB, BSL, Lega, VTB) yazılmış + test
- Her biri NO_DATA_NO_TRADE prensibine uyar (test ile doğrulanmış)
- Health alert Plan 2 (telegram) ile entegre
- Polymarket'te Avrupa basket maçı açılırsa bot trade etmeye başlar
- Outlier filter aktif (yanlış rating reject)
- 1894+ pytest passed
- Sezon dışı (0 game) silent skip
- DECISIONS.md'ye "SPEC-EUROBASKET-001 done" notu eklenmiş
