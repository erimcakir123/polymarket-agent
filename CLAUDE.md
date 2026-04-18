# CLAUDE.md — Geliştirme Asistanı Kuralları

> Bu dosya geliştirme asistanının bu projede nasıl davranacağını belirler.
> Her conversation başında otomatik yüklenir.

---

## ⚠️ MIMARI UYUM ZORUNLULUĞU (ATLANMAZ)

**Edit veya Write tool'u kullanmadan ÖNCE:**

1. Read ile `ARCHITECTURE_GUARD.md` dosyasını aç ve oku (bu görevde daha önce okuduysan tekrar etmesine gerek yok, hatırla).
2. Kullanıcıya **self-check satırını yaz** (görünür olmak zorunda):
   > "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."
3. Self-check YAZILMADAN Edit/Write yapma.

Kullanıcı self-check görmezse "self-check nerede?" diyebilir — o zaman dur, Read, self-check yaz, sonra devam.

**Tam kurallar:** [ARCHITECTURE_GUARD.md](ARCHITECTURE_GUARD.md) (15 kural + anti-pattern tablosu).

---

## Proje Bağlamı

Polymarket tahmin piyasalarında otonom trading botu.
Spor maçlarında bookmaker konsensüsü üzerinden edge tespiti + çok katmanlı risk yönetimi.
**Veri kaynağı**: Odds API bookmaker probability (bkz. TDD §6.1). MVP spor kapsamı TDD §7.1'de tanımlı; ertelenmiş branşlar için TODO.md'ye bakın. Bu dosyalarda ve PRD/ARCHITECTURE_GUARD'da tanımlı olmayan teknolojiyi kullanma.

**Proje Sahibi**: Teknik olmayan ortak. Mimari kararları anlayabilir ama kodu satır satır takip edemez.
Açıklamalar net, jargonsuz olmalı. Kritik kararlar onay beklemeli.

---

## Dosya Rolleri (Tek Doğruluk Kaynağı)

Her bilgi türü TEK yerde yaşar. Tekrar yasak.

| Bilgi türü | Tek yeri |
|---|---|
| Fonksiyon imzası, import, dosya yolu, class yapısı | **Kod** (`src/`) |
| Yapısal invariantlar (5-katman, I/O yasağı, max satır) | **ARCHITECTURE_GUARD.md** |
| Ürün vizyonu + demir kurallar (bankroll, event-guard) | **PRD.md** |
| Formül, eşik, kalibrasyon sayıları, "neden" notları | **TDD.md** (§0 + §6 + §7 + §13) |
| Config değerleri | **config.yaml** |
| Testler | **tests/** |
| Ertelenmiş işler | **TODO.md** |
| İn-flight plan | **PLAN.md** |
| Tek kullanımlık spec | **SPEC.md** |

Aynı bilgi iki yerde görünüyorsa: DRIFT riski. Birini sil, doğru kaynaktan referans ver.

---

## Okuma Kuralları

### Her kod görevinden ÖNCE (zorunlu)
1. **ARCHITECTURE_GUARD.md** — İhlal edilemez mimari kurallar
2. **PRD.md** — Ürün gereksinimleri ve demir kurallar

### Göreve göre (TDD.md)
TDD.md'nin başındaki **İçindekiler** tablosuna bak.
- §0 her zaman okunur (temel ilkeler). §6 (formüller/kalibrasyonlar) ve §7 (sport rules) göreve göre okunur.
- Diğer bölümleri görev katmanına göre oku — gizli bağımlılıklar için TDD.md başındaki "Güvenlik Ağı" kurallarına uy.
- Şüphe varsa TDD'nin tamamını oku. Token tasarrufu doğruluğun üstüne çıkamaz.

### İhtiyaç doğduğunda oku
- **PLAN.md** — yeni plan yazılması/güncellenmesi/okunması gerekiyorsa (kullanıcı söylemese de)
- **SPEC.md** — yeni spec yazılması/güncellenmesi/okunması gerekiyorsa (kullanıcı söylemese de)

### Sadece kullanıcı isteyince oku
- **TODO.md** — kullanıcı "todo'ya kaydet/todoya bak/ertele" derse

### Eski Proje Referansı (selective migration)
Eski projeden dosya okurken:
- Önce **Grep** ile ilgili bölümü bul
- Sonra **Read** tool'una `offset` + `limit` parametreleriyle SADECE o bölümü oku
- Hangi bölümü okuyacağından emin değilsen veya bağlam geniş gerekiyorsa tamamını oku — varsayılan kısmi okumadır ama doğruluk öncelikli

---

## TODO Yönetimi

- **Tek TODO dosyası**: `TODO.md` — başka yere TODO yazılmaz.
- Kullanıcı "TODOYA YAZ" / "todo'ya ekle" gibi bir şey söylerse → `TODO.md`'ye madde eklenir, başka dosyaya değil.
- Her TODO: başlık (TODO-XXX) + durum (DEFERRED / IN_PROGRESS / BLOCKED) + sebep + önkoşul.

---

## Kod Yazma Kuralları

### Mimari
- 5 katmanlı mimari: Presentation → Orchestration → Strategy → Domain → Infrastructure
- Üst katman alt katmanı çağırır. ALT KATMAN ÜST KATMANI ASLA ÇAĞIRMAZ
- Domain katmanında I/O (requests, file, socket) YASAK
- Tek dosya MAX 400 satır — aşarsa böl
- Tek class MAX 10 public method, MAX 5 constructor dependency
- God object / god function YASAK

### Stil
- Python 3.12+
- Type hints zorunlu (tüm fonksiyon imzaları)
- Pydantic modeller için dataclass veya BaseModel
- Enum'lar str(Enum) mixin ile (JSON serializable)
- Config'den oku, magic number YASAK
- Docstring: sadece karmaşık mantık için, bariz fonksiyonlara yazma

### Veri Kuralları
- P(YES) her zaman anchor — direction-adjusted ASLA saklanmaz
- Event-level guard: aynı event_id'ye iki pozisyon açılamaz
- Bankroll koruması: exposure cap, circuit breaker, SL her zaman aktif

### Test
- Domain fonksiyonları: unit test ZORUNLU
- Strategy karar noktaları: unit test ZORUNLU  
- Test isimlendirme: `test_{ne}_{senaryo}_{beklenen}`
- Test olmadan merge YASAK

---

## Dosya Yönetimi

### Yeni Dosya Eklerken
1. `src/` altındaki mevcut dizin yapısını kontrol et (Glob ile)
2. Doğru katmana yerleştir (5-katman kuralı — ARCHITECTURE_GUARD)
3. Katman belirsizse → PLAN.md'ye öner, onay bekle
4. `utils/`, `helpers/`, `misc/` dizinleri YASAK

### Mimari Değişiklik Yaparken
1. PLAN.md'ye yaz (PROPOSED)
2. Onay bekle
3. Uygula
4. TDD.md'yi güncelle
5. PLAN.md'den sil

### Spec Yazdırırken
1. SPEC.md'ye yaz (DRAFT)
2. Girdi/çıktı, davranış kuralları, sınır durumları, test senaryoları dahil et
3. Onay alınca koda dönüştür
4. Kod + test yazıldıktan sonra SPEC.md'den sil

### ⚠️ Her Edit/Write Öncesi Zorunluluk
ARCHITECTURE_GUARD.md okundu + self-check mesajı yazıldı mı? **Yoksa dur.** (Dosyanın başındaki "Mimari Uyum Zorunluluğu" bölümüne bak.)

---

## Kural Değişikliği Protokolü

Kullanıcı iş diliyle bir kural değişikliği söylediğinde (örn. "daha seçici olalım", "bu spor kapsam dışı", "o eşiği artır"):

### Adım 1 — Somutlaştır
İş niyetini tek/birkaç somut parametreye çevir.
Örnek: "Daha seçici olalım" → `min_edge` artışı (0.06 → 0.08?)

### Adım 2 — Tek satırda doğrulat
Kullanıcıya tek soru:
> "min_edge 0.06 → 0.08 yapıyorum, doğru mu?"

Onay alınmadan Adım 3'e geçme.

### Adım 3 — Tüm geçtiği yerleri grep'le bul
Tipik lokasyonlar:
- `config.yaml`
- `src/` (default değerler, kullanım)
- `tests/` (eşik assertion'ları)
- `TDD.md` (formül/neden notu)
- `PRD.md` (demir kural değişikliğiyse)

`docs/superpowers/plans/*` tarihsel kayıttır — dokunma.

### Adım 4 — Değişim planını sun
Etkilenen dosya + satır listesi göster, onaylat.

### Adım 5 — Tek seferde uygula
Tüm dosyaları aynı turda güncelle. Yarım bırakma yasak.

### Adım 6 — Doğrulama
- `pytest -q` → tümü geçmeli
- Grep'te eski değer kalmamalı (alakasız eşleşmeler hariç)
- Rapor: değişen dosya sayısı, test sonucu, artık referans var mı

**Kritik kural:** Grep'te bir dosyada eski değer görülüyor ama Adım 4 listesinde yoktu → DURDUR, kullanıcıya sor.

---

## Eski Kod Referansı (Selective Migration)

Eski proje dizini: `../Polymarket Agent_Eski/`. Bu dizin kod yazımı sırasında **referans** olarak okunur — **asla kopyalanmaz**.

Her PLAN adımında:
1. İlgili eski dosyayı Read ile oku.
2. İki ayrım yap:
   - **Migrate edilecek** (değerler + kanıtlanmış formüller): sayısal sabitler, lookup tabloları (slug→sport_tag, bookmaker_weights), edge-case mantığı (9-katman SL, elapsed-gated market_flip)
   - **Sıfırdan yazılacak** (mimari farklı): orchestration, entry_gate, model'ler, infrastructure katmanı
3. Değerleri/mantığı çıkar, **yeni dosyayı TAZE yaz** (TDD + ARCH_GUARD + SPEC'e göre).
4. Test yaz, eski davranışı yeni kodda doğrula.

**Kural**: 0 satır copy-paste. Knowledge migration ≠ code migration.

**Yedek**: `../Polymarket Agent 2.0 -YEDEK/` — bu klasöre dokunma, acil recovery için.

---

## İletişim

- Türkçe iletişim (kullanıcı Türk)
- Teknik terimleri açıkla (kullanıcı teknik değil)
- Kritik kararlar için onay iste
- "Bunu da eklersek iyi olur" yerine sadece istenen şeyi yap
- Mimari ihlal fark edersen HEMEN uyar

---

## Yasaklar

- [ ] **Edit/Write öncesi ARCH_GUARD self-check atlama** (hook uyarısı + 3 noktada tekrarlanan kural)
- [ ] Mimari kuralları görmezden gelme
- [ ] 400+ satırlık dosya oluşturma
- [ ] Domain'de I/O yapma
- [ ] Magic number kullanma
- [ ] Test yazmadan bırakma
- [ ] Onay almadan mimari değişiklik yapma
- [ ] utils/helpers/misc dizini oluşturma
- [ ] P(YES) dışında olasılık saklama
- [ ] Sessiz hata yutma (bare except: pass)
- [ ] Scope creep (istenmeyeni ekleme)
- [ ] Eski projeden kod kopyalama (referans okunur, taze yazılır)

---

## Restart Protokolü

Kullanıcı "restart" dediğinde **her seferinde** sor: **Reload mu Reboot mu?**
- **Reload**: Kod güncellenir, veri korunur
- **Reboot**: Her şey sıfırlanır — **onay zorunlu** (uyarı mesajı göster)

Her ikisi de bot + dashboard'u kapsar. Adımlar: TDD §5.8.
