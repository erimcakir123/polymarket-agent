# Tasarım — Tenis Taze Sonuç Hasadı + Bayatlık Koruması

**Tarih:** 2026-06-13
**Durum:** ONAYLANDI (brainstorm)
**Karar veren:** Erim (kullanıcı)

---

## Problem

Tenis Glicko reytingleri tek kaynaktan (Sackmann CSV) besleniyor; kaynak 2-3 haftada bir güncelleniyor. 13 Haz itibarıyla reyting verisi **11-19 gün bayat** (tur en yeni maç 25 May, Challenger 1 Haz). Sonuç: model, son 10 günde formda olan oyuncuyu (sıcak elemeci, kariyer-yılı yaşayan) göremiyor; piyasa görüyor.

**Kanıt (4-13 Haz otopsisi, web araştırması ile):** Model-kaynak ML 15W-25L net -$357.6. Bizi yenen oyuncuların ~%70'i "son 10 günün formda oyuncusu" (Taro Daniel elemeden 2 seribaşı devirdi, Kasintseva kariyer yılı, Cigarran sıcak eleme serisi). Bu oyuncuların reytingi VAR (phi koruması geçiyor — ince veri değil) ama BAYAT. Kalan ~%30: varyans (Trungelliti rakibi 5 maç puanı kurtardı) + olası gerçek model hataları (Kicker).

**Kritik ayrım:** İnce veri (az maç → güvenilmez reyting) zaten phi koruması ile engelli. Bu tasarım **bayat veri** (bol maç → güvenilir ama eski reyting) sorununu çözer.

---

## Kapsam

**Bu tasarım:** Model tahmin mantığını DEĞİŞTİRMEZ. Sadece reytingleri besleyen veriyi güncel tutar. Motor aynı motor; gözlüğü temizlenir.

**Bu bir tedavi değil, bir sınav:** Taze veri, kanıtlanmış tek sebebi (bayatlık) kaldırır. Modelin gerçekten edge'i olup olmadığı HÂLÂ kanıtsız — tamir sonrası "model piyasayla ters düştüğünde kim haklı" ölçümü ile sınanır. Düzelmezse model kapatılır.

---

## Yaklaşım — A (Polymarket sonuç hasadı)

**Seçilen:** Botun gördüğü tenis maçlarının sonuçlarını Polymarket'in çözülmüş marketlerinden topla.

**Neden A:**
- Glicko reytingi sadece kazanan/kaybeden ister — **skor gerekmez**. Polymarket çözümü kazananı verir.
- Tam bizim bahis evrenimizi kapsar — **Challenger dahil** (bizi en çok yakan yer).
- Yeni dış bağımlılık yok; Polymarket/gamma bedava (Odds API'ye DOKUNULMAZ).

**Reddedilen B (ESPN geçmiş skor):** Skor da verir ama ESPN Challenger/125'leri kapsamaz → en çok kanadığımız yeri düzeltmez.

**Reddedilen C (ikisi birden):** YAGNI; karmaşıklık artışı şu an değmez.

---

## Mimari (5 katman)

| Parça | Katman | Sorumluluk | Yeniden kullanım |
|---|---|---|---|
| **Sonuç hasatçısı** | Infrastructure | Verilen tenis condition_id listesi için gamma'dan çözülmüş marketi çek, kazanan tarafı oku | Mevcut `GammaClient.fetch_closed_market_by_condition` + `polymarket_resolution.check_resolution` deseni |
| **Sonuç deposu** | Infrastructure/data | Toplanan sonuçları jsonl'e yaz/oku, maç-anahtarıyla dedupe | Yeni: `tennis_results_store.py` + `data/tennis_recent_results.jsonl` |
| **Maç çıkarımı** | Domain | Çözülmüş market dict → (kazanan_adı, kaybeden_adı) saf dönüşüm | Yeni saf fonksiyon |
| **İsim çözme** | Strategy/enrichment | Polymarket adı → Sackmann adı; çözülemeyen atlanır | Mevcut `_resolve_player_name` |
| **Reyting birleştirme** | Build script | `build_tennis_ratings` taze sonuçları Glicko fit'ine ekler (genel + zemin), servis istatistiğine SOKMAZ | Mevcut `fit_ratings` |
| **Günlük tetik + geri-doldurma** | Orchestration | Günde 1: hasat → depo → yeniden kur. İlk çalıştırma: son ~14 günü geri-doldur | Mevcut `factory_refresh_hooks` günlük-kontrol deseni |

### Condition_id kaynağı (hangi maçları hasat edeceğiz)

Botun zaten gördüğü tenis maçları: `data/stock_queue.json` + `logs/runtime/skipped_trades.jsonl` + `logs/audit/trade_events.jsonl`. Bunlardan tenis sport_tag'li, match_start geçmiş, henüz hasat edilmemiş condition_id'ler toplanır. Bu liste = tam bizim değerlendirdiğimiz evren (Challenger dahil).

### Zemin çözümü

Taze maçın zemini, mevcut `tennis_surface_map` + Wikipedia çözücüyle turnuva adından bulunur (mevcut altyapı). Zemin çözülemezse maç genel (overall) reytinge katılır, yüzey reytingine katılmaz.

---

## Veri akışı

**Günlük (her 24 saatte 1, Sackmann kontrolüyle aynı kadans):**
1. Görülen tenis condition_id'lerinden geçmiş + hasat edilmemiş olanları topla
2. Her biri için gamma'dan çözülmüş marketi çek → kazanan tarafı oku
3. İsimleri Sackmann'a çöz (çözülemeyen atla + logla)
4. Zemini çöz → (kazanan, kaybeden, zemin, tarih) deposuna yaz (dedupe)
5. Reytingleri yeniden kur (Sackmann CSV + taze sonuç deposu)

**İlk çalıştırma (geri-doldurma):** Adım 1'de pencere son ~14 gün → 11 günlük boşluk ilk günde kapanır.

---

## Korumalar (üç katman)

1. **Az veri koruması (mevcut, korunur):** `max_phi_for_trade=100` — güvenilmez reytingli oyuncuda oynamaz.
2. **Bayatlık koruması (YENİ):** Reyting verisi N günden eskiyse (hasat başarısız/çevrimdışı) model bahsi yapılmaz — bot bahisçi şeritlerine düşer. Bugünkü "11 gün kör oynama" durumunu imkânsız kılan emniyet kemeri. Hasat günlük çalışınca normalde hiç tetiklenmez.
3. **Servis kirliliği önleme:** Taze sonuçlar (skorsuz) yalnız Glicko fit'ine girer, servis istatistik motoruna girmez → mevcut Sackmann boru hattı bozulmaz.

---

## Hata yönetimi (ARCH_GUARD Kural 12)

- Gamma erişilemezse: o maç atlanır, mevcut reytingle devam (bayatlık koruması gerekirse devreye girer).
- İsim çözülemezse: maç atlanır + WARNING log.
- Tekrar eden sonuç: depoda maç-anahtarıyla dedupe.
- Domain saf fonksiyonları exception fırlatmaz (None/skip döner).

---

## Test

- **Hasatçı:** sahte gamma istemcisi → çözülmüş market dict → doğru kazanan; çözülmemiş → atla; HTTP hata → graceful skip.
- **Depo:** yaz-oku turu, dedupe, bozuk satır atla.
- **Maç çıkarımı (domain):** market dict → (kazanan, kaybeden); belirsiz/yarım dict → None.
- **Reyting birleştirme:** örnek taze sonuç → ilgili oyuncunun reytingi değişir; servis istatistiği DEĞİŞMEZ.
- **Bayatlık koruması:** reyting yaşı > eşik → model skip; ≤ eşik → normal.
- **Günlük tetik + geri-doldurma:** pencere kararı (saf), ilk çalıştırma geniş pencere.

---

## Kapsam dışı (YAGNI)

- ESPN skor hasadı (B) — şu an değmez.
- Skor-bazlı serve modeli güncellemesi — serve modeli çoğunlukla kapalı.
- İncremental Glicko (tam yeniden kurma yeterli ve kanıtlı).
- Model edge ispatı — bu ayrı bir test işi (tamir sonrası ölçüm).

---

## Açık uçlar (uygulama planında netleşecek)

- Bayatlık eşiği N gün kaç olsun? (öneri: 4 gün — günlük hasat 1 gün, 2-3 gün tampon)
- Hasat başına gamma çağrı tavanı (yüzlerce maç → rate limit nezaketi)
- Geri-doldurma penceresi tam kaç gün (öneri: 14)
