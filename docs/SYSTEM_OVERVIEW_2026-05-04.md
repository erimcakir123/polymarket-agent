# Bot Genel Bakış (2026-05-04 sonrası)

> Bu dosya teknik olmayanlar için. Bot şu an ne yapıyor, neye giriyor, neye girmiyor — sade dilde.

---

## 1. Şu an bot ne yapıyor?

Bot, Polymarket adlı bahis pazarında spor maçlarına **otomatik bahis** koyuyor. Mantık şu:

1. Polymarket'taki açık spor maçlarını **tarıyor** (her 30 dakikada bir derin tarama).
2. Her maç için, bookmaker odds'larından **gerçek olasılığı** hesaplıyor.
3. Polymarket fiyatı bookmaker'a göre **ucuz** ise (en az %6 fark = "edge"), pozisyon açıyor.
4. Pozisyonu açtıktan sonra **fiyatı izliyor**: kâra geçince satıyor, çok düşerse stop-loss yapıyor.

Şu an `dry_run` modunda — yani gerçek para harcanmıyor, sadece kararlar simüle ediliyor.

---

## 2. Hangi sporlara giriyor?

Tarayıcı şu spor etiketlerine bakıyor (`config.yaml` → `allowed_sport_tags`):
- **Basketbol**: NBA, WNBA, NCAA-B, EuroLeague, NBL
- **Beyzbol**: MLB, MiLB, NPB, KBO
- **Buz hokeyi**: NHL, AHL, Liiga, Mestis, SHL, Allsvenskan
- **Amerikan futbolu**: NCAA-F, CFL, UFL
- **Golf**: PGA, LPGA, LIV
- **Dövüş**: MMA, UFC, boks

> **Not (2026-05-05)**: Tenis (ATP/WTA) tarama tag'lerinden kaldırıldı. Matching/slug eşleştirme katmanı korundu — tekrar açmak istenirse `config.yaml → allowed_sport_tags`'a 3 satır geri eklemek yeterli.

Ama **kararı veren mantık (16 Nisan kuralları)** sadece moneyline/3-way pazarları kabul ediyor — spread, totals (over/under), puck line gibi karmaşık pazarlar **şu anda dışarıda**. Sadece "X kazanır mı?" tipi basit bahisler.

---

## 3. Kararı nasıl alıyor? (16 Nisan kural seti — basit, kanıtlanmış)

**Giriş için 4 zorunlu şart:**
1. **Edge ≥ %6** — Polymarket bookmaker'a göre en az 6 puan ucuz olmalı.
2. **A confidence + sharp bookmaker desteği** — sadece güvenilir kanıt zinciri varsa açıyor (Pinnacle gibi keskin bookmaker'lar dahil).
3. **Maç başlangıcına 24 saat kala veya canlı** — daha erken pencere yok.
4. **Risk limitleri** — günlük max kayıp %8, saatlik %5, art arda 4 kayıpta cooldown.

**Pozisyon büyüklüğü**:
- Tek bahis maksimum **75 USDC** veya bankroll'un **%5'i**, hangisi düşükse.
- Toplam exposure **%50** ile sınırlı (hard cap %52).
- Aynı anda max **50 pozisyon** açık olabilir (pratikte 12-15).

**Çıkış için 3 ana mekanizma:**
- **Scale-out**: %25 kâra ulaşınca pozisyonun %40'ını sat, %50 kârda %50 daha sat.
- **Stop-loss**: Fiyat girişten %30 düşerse kapat.
- **Near-resolve**: Maç bitmek üzereyken (çoğunluk fiyatı oturmuşsa) likidasyon.

---

## 4. Altyapı eklemeleri (bu güncellemede ne katıldı?)

Trading kararına dokunmadan, sadece bot'un veriyi nasıl topladığı/sakladığı/gösterdiğini iyileştirdik:

### A — Dashboard görsel iyileştirmeleri
- **Tab'lı equity grafiği**: 1 saat / 1 gün / 1 hafta / hepsi periyotları arasında geçiş.
- **Trade history modal**: Geçmiş bahislerin detaylı görünümü.
- **Skip reason help overlay**: Hangi maçların neden atlandığını açıklayan tooltip.
- **Ses efektleri**: Win, Loss, market entry sesleri.
- **Sticky y-axis + smooth scroll** — büyük grafiklerde rahat gezinti.

### B — Slug + market eşleştirme
- **3-way pazar desteği**: Futbol, AFL, handball, rugby gibi beraberlikli pazarlarda toplam olasılık 0.95-1.05 aralığında olmalı (anomali filtresi).
- **MLB/NHL takım takma adları**: Gamma slug'larından doğru takımı bulmak için genişletilmiş alias tablosu.
- **Tennis turnuva resolver**: ATP/WTA turnuvaları için dinamik tier + zemin + format çıkarımı (Magnus modeli için altyapı, **şu an aktif değil**).
- **Sport_tag override**: `mlb` slug'ları otomatik `baseball` Odds API key'ine map ediliyor.
- **Excluded competitions**: Friendly/preseason maçlar tarama dışı.

### C — Log mimarisi (3 katmanlı)
- **logs/audit/** — kalıcı güvenlik yedeği. Bot yazar, **hiçbir şey silmez**. Trade history, equity, exits, score events.
- **logs/runtime/** — reboot'ta temizlenir (bot.log, dashboard.log, skipped_trades).
- **logs/session/** — reboot'ta silinir; dashboard'un tek kaynağı (audit'in bir aynası).
- **scripts/reboot.py** — `reload` (state korunur) veya `reboot` (state sıfırlanır, audit dokunulmaz) komutları. PID dosyalarıyla **1 bot + 1 dashboard tekillik garantisi**.

### H — Slippage koruması
- Order fill olduktan sonra **fiyat tekrar kontrol** ediliyor: edge hala yeterli mi? Değilse `STALE_PRICE_REJECT` ile reddedildi sayılıyor (gerçek para korunmuş).

---

## 5. Yapılmayan / atlanan şeyler (bilinçli)

Bu güncellemede dokunulmayan ve **şu an aktif olmayan** şeyler:

- **In-match olasılık modelleri**: NHL empirical win probability, MLB Pythagorean expectancy + log5 + pitcher adjustment, Tennis Magnus modeli, NBA safe lead — hiçbiri çalışmıyor. 16 Nisan kararı: bunlar fazla karmaşık olduğu için canlı maç sırasında olasılık güncelleme yapılmıyor.
- **Sport-specific exit dispatcher'lar**: MLB run line / totals exit, NHL puck line / totals exit, Tennis score exit, Cricket exit — yok. Çıkış mantığı **sport-agnostic** (genel kurallar tüm sporlara uygulanıyor).
- **Yeni API client'ları**: `mlb_stats_client`, `openweather_client`, `sackmann_client`, `espn_*` — entegre edilmedi.
- **Tenis tarama dışı (2026-05-05)** — `allowed_sport_tags`'den çıkarıldı, in-match modeli olmadan riskli olduğu için. Matching katmanı duruyor, geri açmak için config-only.
- **MLB sporu aktif değil** — pazar tarama tag'lerinde olsa da, in-match modelleri olmadığı için entry gate aslında ona izin vermiyor.

---

## 6. Riskler + sınırlar

**Sertçe limitler (asla aşılmaz):**
- Günlük kayıp **%8** → bot durur, 120 dk cooldown.
- Saatlik kayıp **%5** → 60 dk cooldown.
- Art arda 4 kayıp → 60 dk cooldown.
- Toplam exposure **%52** (hard cap).
- Tek bahis max **75 USDC**.

**Trading riskleri:**
- Bot dry_run'da → gerçek para risk yok. Live moda geçmek için `config.yaml` → `mode: live` ve onay gerekli.
- Slippage koruması var ama gerçek piyasa şartlarında fill quality değişebilir.
- Polymarket API'sinin downtime'ı bot'u yavaşlatabilir; circuit breaker bu durumda kendini kapatır.

**Mimari kısıtlar:**
- Aynı maça (event_id) **iki pozisyon açılamaz** (event-level guard).
- Domain katmanında I/O yasak — saf hesaplama. Pre-game olasılık hesaplamaları reproducible.

---

## 7. Şu anki durum özeti

- **HEAD**: `2ea6426` (slippage migration üstü)
- **Test durumu**: 967 pass / 0 fail
- **Mode**: `dry_run`
- **Aktif bahis kuralları**: 16 Nisan baseline (edge ≥ %6, A confidence + sharp shart, moneyline only)
- **Açık entry portları**: NBA + benzer 2-way moneyline pazarları
- **Sound efekt**, **3-tier log**, **slippage koruması**: aktif
- **In-match modelleri**, **sport-specific exit'ler**: pasif (yok)

---

> Detay için: `DECISIONS.md` (kalibrasyon ve "neden bu sayı" notları), `config.yaml` (canlı parametreler), `CLAUDE.md` (geliştirme kuralları).
