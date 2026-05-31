# Basketball Faz 2 — College (NCAAB + WNCAAB) Scope Dokümanı

> **STATUS:** SCOPE NOTLARI — full spec ileride yazılır
> Tarih: 2026-06-01
> Bağımlılık: Faz 1 (Plan 1.A/B/C/D) DONE
> Tahmini süre: 4-6 hafta

---

## 1. Amaç

NCAAB (NCAA Erkek Basket) + WNCAAB (Kadın Basket) için Faz 1 NBA/WNBA çatısının üzerine üniversite ligini ekle. Polymarket'te `cbb` slug ile aktif (NCAAB = CBB aynı şey, whitelist temizliği yapılır).

---

## 2. Mevcut Faz 1 Çatısının Yeniden Kullanımı

**Aynı kalır (kopya değil, doğrudan kullanılır):**
- `src/domain/pricing/basketball/team_elo.py` — Elo aynı
- `src/domain/pricing/basketball/pace_efficiency.py` — KenPom formülü aynı
- `src/domain/pricing/basketball/efficiency_metrics.py` — outlier guard aynı
- `src/domain/pricing/basketball/match_pricer.py` — market dispatch aynı
- `src/strategy/enrichment/basketball_anchor_enricher.py` — wrapper aynı
- `src/domain/calibration/*` — kalibrasyon altyapısı aynı (lig-başına eğri)

**Faz 2'de eklenir:**
- `src/infrastructure/data/basketball/espn_cbb_refresher.py` — birincil veri kaynağı
- Possessions katsayısı: 0.475 (Dean Oliver 2003 college kabul)
- Lig-spesifik tuning: `home_advantage=130` (kalabalık seyirci), `k_factor=25`

---

## 3. Veri Kaynakları

| Lig | Birincil | Yedek | Risk |
|---|---|---|---|
| NCAAB | `hoopR-py` (sportsdataverse, ESPN scrape) | `nba_api` college endpoint (kısıtlı) | Orta — ESPN HTML değişebilir |
| WNCAAB | ESPN scoreboard JSON (manuel) | Yok | Orta-yüksek — kapsam doğrulanmalı |

**WNCAAB için Plan 2.A başında spike test** (NBA spike paterni):
- 2024 NCAA Kadın sezonunu çek
- 350+ takım, ~5000 maç beklenir
- Eşik: ≥%80 maç kapsama (vs %90 NBA çünkü college daha gürültülü)

---

## 4. Lig-Spesifik Farklar (Tuning)

| Parametre | NBA | WNBA | NCAAB | WNCAAB |
|---|---|---|---|---|
| home_advantage | 100 | 95 | **130** | **120** |
| k_factor | 20 | 22 | **25** | **25** |
| possessions_factor | 0.44 | 0.44 | **0.475** | **0.475** |
| margin_std | 11 | 9.5 | **13** | **12** |
| total_std | 20 | 16 | **22** | **20** |
| blend_elo | 0.55 | 0.55 | **0.60** (college'da Elo daha güçlü) | 0.60 |

`config.yaml`'a 2 yeni lig blok eklenir.

---

## 5. Plan Zinciri Önerisi

| Plan | Kapsam | Süre |
|---|---|---|
| **Plan 2.A** — Veri katmanı + WNCAAB spike | hoopR-py / ESPN scrape, possessions 0.475 | 2 hafta |
| **Plan 2.B** — Faz 1 model adaptasyonu + lig tuning | config + possessions_factor parametre | 1 hafta |
| **Plan 2.C** — Strateji entegrasyon + backtest | dispatcher genişletme, NCAAB 2024 backtest | 1-2 hafta |

---

## 6. Riskler ve Önlemler

| Risk | Önlem |
|---|---|
| ESPN HTML değişikliği | Pydantic schema validation (Faz 1 pattern) + ikincil kaynak hazır |
| 350+ takım slug fuzzy matching | basketball_team_resolver'a NCAAB tabloları ekle (büyük lookup) |
| Üniversite takımlarının yıllık roster %50+ değişimi | Sezon başı %35 reversion (NBA %25'ten yüksek — daha çok değişim) |
| WNCAAB veri yetersizliği | Spike test sonucuna göre kapsam dışı bırakılabilir |

---

## 7. Onay Noktası

Faz 2'ye başlamadan önce:
1. Faz 1 (Plan 1.D) backtest %66+ veya kabul edildi
2. Canlı bot 2+ hafta NBA/WNBA tradinginde stabil
3. Trade history yeterli (≥1000 closed trade) → kalibrasyon eğrisi anlamlı

---

## 8. Out of Scope (Faz 2'de yapılmaz)

- Conference tournaments özel modelleme (basit average yeterli)
- Player-level model (takım seviyesi)
- Live in-game update (cycle başı yenileme yeter)
- NCAAB DII / DIII ligler
