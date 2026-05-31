# Basketball Faz 3 — International (Euroleague) Scope Dokümanı

> **STATUS:** SCOPE NOTLARI — full spec ileride yazılır
> Tarih: 2026-06-01
> Bağımlılık: Faz 1 + Faz 2 DONE
> Tahmini süre: 4-6 hafta
> Kapsam: **Euroleague yalnız.** NBL kapsam dışı (Python verisi yok, riskli).

---

## 1. Amaç

Avrupa Basket Ligi (Euroleague) Polymarket marketlerini Faz 1 çatısına ekle. EuroCup ve diğer Avrupa ligleri Faz 3 sonrası değerlendirilir.

---

## 2. Faz 1 Çatısının Yeniden Kullanımı

Faz 2 ile aynı pattern — domain mantığı (Elo + Pace × AdjO/AdjD + match_pricer + kalibrasyon) **birebir aynı**. Sadece veri kaynağı ve lig parametreleri farklı.

---

## 3. Veri Kaynağı

| Lig | Birincil | Yedek |
|---|---|---|
| Euroleague | `euroleague-api` (giasemidis, PyPI sustainable, 210 weekly download, 3 ay önce güncellenmiş) | euroleague.net Swagger doğrudan HTTP |

**Veri spike test (Plan 3.A başında):**
- 2024 Euroleague sezonu çek (~300 maç)
- 18 takım kapsama
- Possessions kolonları (EUL FGA + FT + OR + TO) hesaplamaya uygun mu

---

## 4. Lig-Spesifik Farklar

| Parametre | NBA | Euroleague | Sebep |
|---|---|---|---|
| home_advantage | 100 | **90** | Avrupa salonları daha küçük + yabancı seyirci az etki |
| k_factor | 20 | 20 | NBA seviyesi profesyonel |
| possessions_factor | 0.44 | **0.46** | Euroleague FIBA kuralları farklı (24sn shot clock, free throw kuralları) |
| margin_std | 11 | **10** | Daha dar margin (denkler arası rekabet) |
| total_std | 20 | **16** | Daha düşük skor (NBA 220 vs EUL 160) |
| blend_elo | 0.55 | 0.50 | Pace×Eff daha güçlü, Elo daha az ağırlık |

---

## 5. Plan Zinciri Önerisi

| Plan | Kapsam | Süre |
|---|---|---|
| **Plan 3.A** — Veri katmanı (euroleague-api wrapper) | nba_api wrapper paterni, 2024 spike test | 2 hafta |
| **Plan 3.B** — FIBA kuralları + possessions 0.46 + lig tuning | config + match_pricer FIBA dispatch | 1 hafta |
| **Plan 3.C** — Entegrasyon + backtest | dispatcher genişletme, Euroleague 2024 backtest | 1-2 hafta |

---

## 6. Riskler ve Önlemler

| Risk | Önlem |
|---|---|
| `euroleague-api` tek-kişi maintained → terkedilirse | euroleague.net Swagger doğrudan HTTP yedek wrapper hazırla |
| FIBA kural farkları (24sn shot clock, free throw) modeli yanıltır | Possessions formülünü 0.46 kullan + kalibrasyon eğrisi düzeltir |
| Düşük market liquidity (Polymarket EUL maçları az) | Min liquidity filtresi mevcut scanner'da (config) |
| EuroCup karışıklığı (aynı API farklı kompetisyon) | Schema validator competition alanını filtreler |

---

## 7. NBL Neden Hariç

| Durum | Detay |
|---|---|
| Python paketi | YOK (sadece R'da `nblR`) |
| Ücretli API | Highlightly 100 req/gün ücretsiz, üzeri paid |
| Risk | Tek-kaynak + ücretli + bizim için marjinal volume |
| Karar | Polymarket'te NBL maçları **bahisçi konsensüsünde kalır** (mevcut Odds API). Faz 3+'ta tekrar değerlendirilir |

---

## 8. Onay Noktası

Faz 3'e başlamadan önce:
1. Faz 1 + Faz 2 DONE ve canlıda stabil
2. Polymarket'te Euroleague market volume yeterli (≥10 trade/hafta)
3. `euroleague-api` paket maintenance hâlâ aktif (PyPI son release < 3 ay)

---

## 9. Out of Scope (Faz 3'de yapılmaz)

- NBL (yukarıda)
- EuroCup (ileri faza)
- Türkiye BSL, Yunanistan A1, İspanya ACB (yerel ligler, Polymarket volume düşük)
- FIBA milli takım turnuvaları (kısa dönem, kalibrasyon eğrisi anlamsız)
