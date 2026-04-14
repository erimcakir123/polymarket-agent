# ARCHITECTURE GUARD — Mimari Koruma Kuralları

> Bu dosya **DEĞİŞTİRİLEMEZ**. Projenin mimari bütünlüğünü korur.
> İhlal eden herhangi bir değişiklik reddedilmelidir.
> Tarih: 2026-04-12

---

## Neden Bu Dosya Var?

Bu proje daha önce spagetti koda dönüştü (70KB agent.py, 60KB entry_gate.py).
Proje sahibi teknik ortak değil — mimari bozulursa fark edemez.
Bu kurallar, projenin **kontrol altında kalmasını** garanti eder.

---

## DEMIR KURALLAR (İhlal = Red)

### Kural 1: Katman İhlali Yasak

```
PRESENTATION → ORCHESTRATION → STRATEGY → DOMAIN → INFRASTRUCTURE

✅ Üst katman alt katmanı çağırabilir
❌ Alt katman üst katmanı ASLA çağıramaz
❌ Katlan atlama YASAK (Presentation doğrudan Domain'i çağıramaz)

Tek istisna: Domain katmanı içindeki modüller birbirini çağırabilir.
```

**Test**: Her dosyanın import'larını kontrol et. Eğer:
- `infrastructure/` altındaki bir dosya `strategy/` import ediyorsa → RED
- `domain/` altındaki bir dosya `orchestration/` import ediyorsa → RED
- `strategy/` altındaki bir dosya `infrastructure/` import ediyorsa → RED

### Kural 2: Domain Katmanında I/O Yasak

```
domain/ dizini altındaki HİÇBİR dosyada şunlar OLMAZ:
- import requests
- import httpx
- import websockets
- import flask
- open() (dosya okuma/yazma)
- os.path / pathlib (dosya sistemi)
- socket / urllib
- subprocess

Domain sadece saf hesaplama yapar. Veri dışarıdan verilir.
```

### Kural 3: Dosya Boyutu Limiti

```
Tek bir .py dosyası MAX 400 satır olabilir.

Eğer 400 satırı geçiyorsa:
1. Dosyayı iki veya daha fazla modüle böl
2. Her modül tek bir sorumluluk taşısın
3. TDD.md'deki dizin yapısına uygun şekilde yerleştir

ASLA "sadece biraz daha ekleyeyim" deme. 400 satır = dur ve böl.
```

### Kural 4: God Object Yasak

```
Hiçbir class 10'dan fazla public method'a sahip olamaz.
Hiçbir class 5'ten fazla dependency'ye (constructor parameter) sahip olamaz.

Eğer bir class büyüyorsa:
1. Sorumlulukları analiz et
2. Alt class'lara böl
3. Composition kullan (inheritance değil)
```

### Kural 5: Tek Giriş Noktası

```
Bot tek yerden başlar: src/main.py

main.py sadece:
1. Argümanları parse eder
2. Config'i yükler
3. Agent'ı oluşturur
4. Agent.run() çağırır

main.py'de İŞ MANTIĞI OLMAZ. Max 50 satır.
```

### Kural 6: Config Sabitliği

```
Tüm konfigürasyon config.yaml'dan gelir.
Hardcoded magic number YASAK.

YANLIŞ:
  if edge > 0.05:  # ❌ Magic number

DOĞRU:
  if edge > self.config.edge.min_edge:  # ✅ Config'den
```

### Kural 7: P(YES) Kuralı

```
Olasılık HER ZAMAN P(YES) olarak saklanır.
Direction-adjusted probability ASLA saklanmaz.

Position.anchor_probability = P(YES), BUY_YES olsa da BUY_NO olsa da.
Karar mantığı direction'a göre ayarlama yapar, saklama yapmaz.

Bu kural ihlal edilirse tüm edge hesapları bozulur.
```

### Kural 8: Event-Level Guard

```
Aynı event_id'ye sahip iki pozisyon ASLA açılamaz.
Bu kural entry_gate seviyesinde kontrol edilir.

Örnek: "Man City vs Brighton" maçı event_id=12345
- BUY_YES "City wins" açıldıysa
- BUY_NO "Brighton wins" AÇILAMAZ (aynı event)
```

---

## YAPI KURALLARI

### Kural 9: Yeni Dosya Ekleme Protokolü

```
Yeni bir .py dosyası eklemeden ÖNCE:

1. TDD.md'deki dizin yapısına bak
2. Dosyanın hangi katmana ait olduğunu belirle
3. Eğer dizin yapısında yoksa → PLAN.md'ye yaz, onay al
4. ASLA "misc/", "utils/", "helpers/" gibi catch-all dizinler oluşturma
5. Her dosya TEK BİR sorumluluk taşımalı

İstisna: constants.py ve enums.py gibi veri tanım dosyaları
```

### Kural 10: Yeni Bağımlılık Ekleme Protokolü

```
Yeni bir pip paketi eklemeden ÖNCE:

1. Gerçekten gerekli mi? Standart kütüphane ile yapılamaz mı?
2. Bakımı aktif mi? Son commit ne zaman?
3. Güvenlik açığı var mı?
4. requirements.txt'e ekle, sebebini yorum olarak yaz

ASLA "bunu da ekleyelim, belki lazım olur" deme.
```

### Kural 11: Test Zorunluluğu

```
Domain katmanındaki her fonksiyon için test ZORUNLU.
Strategy katmanındaki her karar noktası için test ZORUNLU.

Test olmadan merge YASAK.

Test isimlendirme: test_{ne_test_ediliyor}_{senaryo}_{beklenen_sonuç}
Örnek: test_confidence_grading_5_bookmakers_returns_A
```

### Kural 12: Hata Yönetimi Katman Kuralı

```
Infrastructure: try/except ile sarmalayıp, anlamlı hata döndür
Domain: Exception fırlatma, None/default döndür
Strategy: Domain sonucuna göre karar ver
Orchestration: Infrastructure hatalarını yakala, logla, devam et

ASLA sessizce hata yutma (bare except: pass)
ASLA domain'de try/except kullanma (saf fonksiyonlar hata vermez)
```

### Kural 13: Logging Konvansiyonu

```
Her katmanın logging davranışı sabittir:

INFRASTRUCTURE:
- API çağrısı başarı → INFO
- API hata / connection loss → WARNING + retry/reconnect bilgisi
- Kalıcı API hatası → ERROR
- WebSocket disconnect → WARNING

ORCHESTRATION:
- Cycle başlangıç/bitiş → INFO (Scanner özet, cycle type)
- Entry/exit kararı → INFO (slug, reason, PnL)
- Circuit breaker trigger → WARNING
- Kritik akış hatası → ERROR + exc_info=True

STRATEGY:
- Gate red (skip) → log yok (sayaç/istatistik yeterli)
- Exit signal üretimi → INFO (yalnızca gerçekten çıkış kararı için)

DOMAIN:
- LOG YOK — saf fonksiyonlar kendi başlarına log etmez.
  Çağıran orchestration/strategy gerekirse loglar.

ASLA loglanmayacaklar:
- API secret keys
- Wallet private key
- Ham bookmaker API response (çok büyük, secret'a yakın)
- Wallet adresi (çoğu durumda PII)

Format: Python standart logging. RotatingFileHandler 10MB × 5 backup.
```

### Kural 14: Periyodik Mimari Audit Protokolü

```
Aşağıdaki durumlarda proje mimari-sağlık taraması yapılır:
- Major feature tamamlandıktan sonra
- Her ~10 fix sonrası
- Ayda bir (aktif geliştirme varsa)
- Kullanıcı "audit yap" dediğinde
- Şüphe varsa (kullanıcı "emin misin?" dediğinde)

Audit tarama komutları (Claude çalıştırır, raporlar):

1. Dosya boyutu ihlalleri:
   wc -l src/**/*.py | sort -n | tail -10
   → 400+ satır olan her dosya PLAN.md'ye bölme önerisi ile yazılır

2. DRY ihlali pattern taraması (projeye özel):
   grep -rn "shares \* " src/
   grep -rn "1 - .*current_price\|1 - .*entry_price" src/
   → aynı pattern 2+ yerde varsa ortak fonksiyon öner

3. Test kapsama:
   pytest --cov=src --cov-report=term-missing
   → Kural 15'teki katman hedeflerinin altındakiler → TODO/PLAN

4. God object (method sayısı):
   grep -cE "^    def " src/**/*.py | sort -t: -k2 -n | tail -5
   → 10+ method sayısı varsa alt class'lara bölme önerisi

5. Magic number taraması:
   grep -rnE "(==|<|>|>=|<=|\*)\s*(0\.[0-9]{2,}|[0-9]{3,})" src/ | grep -v test
   → Config'e taşınabilir magic number'lar

Audit sonucu kullanıcıya özet rapor + bulunan ihlaller + öneri planı sunulur.
Kullanıcı onay verirse fix planına dönüşür.
```

### Kural 15: Test Kapsama Hedefi

```
Katman başına minimum test kapsama (coverage):

Domain:         %80+   (saf fonksiyonlar, test kolay)
Strategy:       %75+   (karar noktaları, mocked input)
Orchestration:  %60+   (I/O heavy, integration mocked)
Infrastructure: %50+   (çoğu HTTP client, mock'lanır)

Ölçüm: pytest --cov=src --cov-report=term-missing

Eğer bir katman hedefin altındaysa:
- Periyodik Audit (Kural 14) bunu yakalar
- TODO.md'ye "coverage-gap-<layer>" maddesi eklenir
- Yeni kod eklenirken eksik testler de yazılır

Test zorunluluğu (Kural 11) ihlal edilmese de kapsama drift eder — bu kural
drift'i sayısal bir eşikle yakalar.
```

---

## YAPMAMASI GEREKENLER (Anti-Pattern'ler)

### ❌ Spagetti Koda Giden Yol

| Anti-Pattern | Neden Tehlikeli | Çözüm |
|-------------|----------------|-------|
| "Şimdilik buraya yazayım" | Geçici çözümler kalıcılaşır | Doğru katmana yaz, PLAN.md'ye not düş |
| "Bu küçük bir değişiklik" | Küçük ihlaller birikerek dev sorun olur | Her değişiklik mimari kontrolden geçer |
| "Tek dosyada olsun daha kolay" | 70KB agent.py böyle oluştu | 400 satır limiti, aş → böl |
| "Utils/helpers klasörü açalım" | Catch-all = çöp kutusu | Her fonksiyon ait olduğu katmana |
| "Circular import sorun değil" | Mimari bozulmanın ilk belirtisi | Katman kurallarına uy |
| "Global state kullanalım" | Test edilemez, öngörülemez | Dependency injection veya parameter passing |
| "Bu fonksiyon hem veri çeksin hem hesap yapsın" | Tek sorumluluk ihlali | Infrastructure (çek) + Domain (hesapla) |
| "Copy-paste edip düzenleyeyim" | DRY ihlali, bakım kabusu | Ortak mantığı domain'e çıkar |

### ❌ Tehlikeli Kod Kalıpları

```python
# ❌ YASAK: God function
def process_market(market):
    data = requests.get(...)      # I/O
    prob = calculate_prob(data)    # Domain
    if prob > 0.5:                # Strategy
        execute_trade(...)        # I/O
        send_telegram(...)        # Presentation
    # 500 satır daha...

# ✅ DOĞRU: Her katman kendi işini yapar
# infrastructure: data = api_client.fetch(market)
# domain: prob = probability.calculate(data)
# strategy: signal = entry_gate.evaluate(market, prob)
# orchestration: if signal: executor.execute(signal)
```

```python
# ❌ YASAK: Gizli bağımlılık
class ExitMonitor:
    def check(self):
        from src.infrastructure.apis.odds_client import OddsClient  # ❌ Lazy import = gizli bağımlılık
        odds = OddsClient()
        odds_data = odds.fetch(...)  # ❌ Strategy katmanı doğrudan infra çağırıyor

# ✅ DOĞRU: Bağımlılık dışarıdan verilir
class ExitMonitor:
    def check(self, match_state: MatchState):  # Veri parametre olarak gelir
        if match_state.score_deficit > 15:
            return ExitSignal(reason=ExitReason.HALFTIME_EXIT)
```

```python
# ❌ YASAK: Magic string/number
if confidence == "A":
    size = bankroll * 0.05

# ✅ DOĞRU: Config + Enum
if confidence == Confidence.A:
    size = bankroll * config.risk.sizing[Confidence.A]
```

---

## MİMARİ DEĞİŞİKLİK PROTOKOLÜ

Mimaride herhangi bir değişiklik yapmak için:

```
1. PLAN.md'ye değişiklik önerisini yaz
2. Sebep belirt: neden gerekli?
3. Etki analizi: hangi katmanlar/dosyalar etkilenir?
4. TDD.md'deki mevcut yapı ile karşılaştır
5. ARCHITECTURE_GUARD.md kurallarını ihlal etmediğini doğrula
6. Onay al
7. Uygula
8. TDD.md'yi güncelle
9. PLAN.md'den sil
```

Mimari değişiklik = katman ekleme/kaldırma, dizin yapısı değiştirme, yeni kalıp ekleme.
Mimari değişiklik DEĞİL = yeni dosya ekleme (mevcut dizine), bug fix, feature ekleme.

---

## KONTROL LİSTESİ (Her PR/Commit İçin)

Her kod değişikliğinde bu listeyi mental olarak kontrol et:

- [ ] Dosya doğru katmanda mı?
- [ ] Katman ihlali var mı? (import kontrolü)
- [ ] Domain'de I/O var mı?
- [ ] Dosya 400 satırı aşıyor mu?
- [ ] Class 10+ public method'a sahip mi?
- [ ] Magic number var mı?
- [ ] P(YES) kuralı korunuyor mu?
- [ ] Event-level guard aktif mi?
- [ ] Test yazıldı mı?
- [ ] Hata sessizce yutulmuyor mu?

Tek bir "evet" bile → düzelt, sonra merge.

---

## SON SÖZ

```
Bu kurallar seni kısıtlamak için değil, seni korumak için var.

Eski proje 50+ dosya, 70KB god object, test edilemez modüller,
karışık sorumluluklar ve spagetti bağımlılıklarla bitti.

Bu kurallar, aynı kaderi yaşamamanın garantisidir.

Bir kural seni engelliyorsa → kuralı değiştir (protokolle).
Kuralı ASLA görmezden gelme.
```
