# Polymarket Bot — Testing & Iteration Plan

> Bu dosya bot'un test sürecini ve iterasyon checkpoint'lerini tanımlar.
> Her checkpoint'te kullanıcı Claude'u çağırır, birlikte analiz ve optimizasyon yapılır.

## Genel Mantık

```
Bot çalışır → 2 checkpoint yapar → DURUR → kullanıcıya sorar
→ Claude analiz eder → optimizasyon yapar → bot tekrar başlar
→ 2 checkpoint daha → DURUR → tekrar sorar → ...
→ Win rate arttıkça güven artar → gerçek paraya geçiş kararı
```

## Bütçe

- API: $48/ay ($24 × 2 sprint)
- Her checkpoint: ~350 prediction = ~$6 API maliyeti
- 2 checkpoint = 1 iterasyon = ~$12
- Ayda 4 iterasyon yapılabilir

---

## FAZA 1: Baseline (Gün 1-5)

### Checkpoint 1 — İlk Veri (Gün 3)
- **Hedef:** ~350 prediction topla
- **Bot:** 7/24 çalışır, dry_run mode
- **Checkpoint'te yapılacak:**
  - [ ] Win rate hesapla (overall + kategori bazlı)
  - [ ] Brier score hesapla
  - [ ] Hangi kategorilerde iyi/kötü?
  - [ ] En büyük hatalar neler? (en yanlış 5 prediction)
  - [ ] Token israfı var mı? (gereksiz analiz edilen marketler)
  - [ ] İlk ai_lessons.md oluşmuş mu?

### Checkpoint 2 — Baseline Tamamlandı (Gün 5)
- **Hedef:** ~700 prediction topla (kümülatif)
- **Checkpoint'te yapılacak:**
  - [ ] Checkpoint 1 ile karşılaştır — trend var mı?
  - [ ] Kategori bazlı win rate tablosu
  - [ ] Kötü kategorileri tespit et (win rate < %45)

**→ BOT DURUR. Claude çağrılır.**

### İterasyon 1 — İlk Optimizasyon
- [ ] Kötü kategorileri filtrele (scanner config'den çıkar veya skip listesi ekle)
- [ ] AI prompt'unu kalibre et (öğrenilen bias'lara göre)
- [ ] Gereksiz market analizlerini azalt (pre-filter iyileştir)
- [ ] Config parametreleri tune et (min_edge, batch_size, vb.)
- [ ] Bot tekrar başlatılır

---

## FAZA 2: Optimizasyon (Gün 6-12)

### Checkpoint 3 — Optimizasyon Sonrası (Gün 8-9)
- **Hedef:** ~350 yeni prediction (optimizasyonlu)
- **Checkpoint'te yapılacak:**
  - [ ] Win rate değişimi: iyileşti mi?
  - [ ] Filtrelenen kategoriler doğru muydu?
  - [ ] Yeni hatalar ortaya çıktı mı?
  - [ ] API maliyeti düştü mü? (gereksiz analizler azaldı mı?)

### Checkpoint 4 — İkinci Karşılaştırma (Gün 11-12)
- **Hedef:** ~700 yeni prediction (kümülatif optimizasyonlu)
- **Checkpoint'te yapılacak:**
  - [ ] Faz 1 vs Faz 2 karşılaştırması
  - [ ] Win rate trendi (artıyor mu, sabit mi, düşüyor mu?)
  - [ ] PnL simülasyonu: bu tahminlerle gerçek para koysaydık ne olurdu?

**→ BOT DURUR. Claude çağrılır.**

### İterasyon 2 — İkinci Optimizasyon
- [ ] İkinci tur bias düzeltmeleri
- [ ] Edge threshold ayarı (çok mu agresif? çok mu pasif?)
- [ ] Confidence multiplier tune etme
- [ ] Bot tekrar başlatılır

---

## FAZA 3: Doğrulama (Gün 13-20)

### Checkpoint 5 — Stabil mi? (Gün 15-16)
- **Hedef:** Optimizasyonların tutarlı olup olmadığını doğrula
- **Checkpoint'te yapılacak:**
  - [ ] Son 3 checkpoint'in win rate trendi
  - [ ] Overfitting var mı? (optimize ettiğimiz şeyler başka yerde bozuldu mu?)
  - [ ] Simüle PnL: kârlı mı?

### Checkpoint 6 — Karar Noktası (Gün 19-20)
- **Hedef:** Gerçek paraya geçiş kararı
- **Checkpoint'te yapılacak:**
  - [ ] Overall win rate
  - [ ] Simüle toplam PnL (tüm süreç boyunca)
  - [ ] Risk metrikleri: max drawdown, en kötü kayıp serisi
  - [ ] Maliyet analizi: API cost vs simüle kâr

**→ KARAR:**

| Win Rate | Simüle PnL | Karar |
|----------|-----------|-------|
| > %57 | Pozitif | ✅ Gerçek para ($100-200) ile başla |
| %53-57 | Marjinal | ⚠️ 1 iterasyon daha, sonra tekrar karar |
| < %53 | Negatif | ❌ Temel değişiklik gerek veya dur |

---

## FAZA 4: Gerçek Para (Gün 21+, eğer onay varsa)

### Checkpoint 7 — İlk Gerçek Trade'ler (Gün 24-25)
- Paper veya live mode ($100-200 bankroll)
- [ ] Gerçek execution sorunları var mı? (slippage, fill rate)
- [ ] Simülasyonla gerçek sonuçlar örtüşüyor mu?

### Checkpoint 8 — İlk Hafta Gerçek (Gün 28-30)
- [ ] Gerçek PnL
- [ ] Gerçek win rate vs dry_run win rate
- [ ] Scale kararı: bankroll artır mı, aynı mı kalsın?

---

## Checkpoint Prosedürü

Her checkpoint'te şu adımlar:

```
1. Bot'u durdur
2. Claude'u çağır: "Checkpoint X — analiz et"
3. Claude logları okur, rapor yazar
4. Birlikte karar: ne değişecek?
5. Claude kod değişikliği yapar
6. Bot tekrar başlar
7. Sonraki checkpoint'e kadar bekle
```

## Otomatik Durdurma Kuralları

Bot şu durumlarda KENDİ KENDİNE durur:
- API bütçesi bitti
- Drawdown breaker tetiklendi (%50 kayıp)
- 3 ardışık cycle hatası

## Başarı Kriteri

Test süreci BAŞARILI sayılır eğer:
- 20 gün sonunda win rate > %55
- Simüle PnL pozitif
- Kötü kategoriler filtrelenmiş
- AI kalibrasyon iyileşme trendi gösteriyor
- Bot stabil çalışıyor (crash yok, budget aşımı yok)

## Takvim Özeti

| Gün | Ne olur | Kim |
|-----|---------|-----|
| 1 | Bot başlar (dry_run) | Otomatik |
| 3 | Checkpoint 1 — ilk veri | Claude analiz |
| 5 | Checkpoint 2 — baseline | Claude analiz + optimize |
| 8-9 | Checkpoint 3 — optimizasyon sonrası | Claude analiz |
| 11-12 | Checkpoint 4 — karşılaştırma | Claude analiz + optimize |
| 15-16 | Checkpoint 5 — doğrulama | Claude analiz |
| 19-20 | Checkpoint 6 — KARAR | Birlikte |
| 21+ | Gerçek para (eğer onay) | Birlikte |
| 28-30 | Checkpoint 8 — ilk hafta gerçek | Claude analiz |

---

*Oluşturulma: 2026-03-19 | Son güncelleme: 2026-03-19*
