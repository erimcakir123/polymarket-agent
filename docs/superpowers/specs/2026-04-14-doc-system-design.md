# Doküman Sistemi Tasarımı — Anti-Spagetti, Token-Optimize

> Tarih: 2026-04-14
> Durum: APPROVED (user onayladı — Yaklaşım 1)
> Amaç: Proje büyüdükçe dokümantasyon ile kod arasında drift oluşmayacak, token-verimli, her conversation'da aynı güvenlik kurallarını garanti eden bir sistem.

---

## 1. Prensipler

1. **Tek doğruluk kaynağı** — her bilgi TEK bir yerde yaşar, tekrar yasak.
2. **Kod = "ne yapıyor"** — fonksiyon, imza, import, dosya yolu sadece kodda.
3. **Doküman = "neden + kalibrasyon + invariant"** — koddan çıkmayan bilgiler.
4. **Sistem Claude'un doğru çalışması için tasarlanır** — kullanıcı anlaması ikincil. Kullanıcı iş diliyle yön verir, Claude somutlaştırır.
5. **Drift yasak** — bir konsept iki yerde yazılıysa birinin silinmesi gerekir.

---

## 2. Doküman Rolleri (tek doğruluk kaynağı matrisi)

| Bilgi türü | Tek yeri | Örnek |
|---|---|---|
| Fonksiyon imzası, import, dosya yolu, class yapısı | **Kod** | `src/domain/guards/manipulation.py` |
| Yapısal invariantlar (5-katman, domain'de I/O yok, max satır) | **ARCHITECTURE_GUARD.md** | "Domain katmanı requests/file/socket import edemez" |
| Ürün vizyonu + demir kurallar (bankroll cap, event-guard) | **PRD.md** | "Aynı event_id'ye iki pozisyon açılamaz" |
| Formül, eşik, kalibrasyon sayıları, "neden bu değer" notları | **TDD.md** (§0 + §6 + §7) | "min_edge = 0.06, neden: empirik test" |
| Proje config değerleri | **config.yaml** | `min_liquidity: 1000` |
| Test case'leri | **tests/** | `test_manipulation.py` |
| Yönlendirme ("nereyi oku ne zaman") | **CLAUDE.md** | Okuma kuralları, rule-change protokolü |
| Ertelenmiş işler | **TODO.md** | `TODO-001: NFL regular-season` |
| İn-flight plan/öneri | **PLAN.md** | `PROPOSED: scanner 8h-past fix` |
| Tek kullanımlık spec (kod yazılınca silinir) | **SPEC.md** | `DRAFT: yeni exit rule` |

**Kural**: Aynı bilgi iki yerde varsa, birisi silinmek zorundadır. Hangi yer doğru kaynaksa oradan okunur.

---

## 3. TDD'den Silinecek Bölümler (LAYER 2)

Aşağıdaki bölümler "kod aynası" — kod zaten source of truth, TDD'de tekrar edilmeleri drift yaratıyor. Silinir.

| § | Başlık | Neden silinir |
|---|---|---|
| 1 | Mimari Genel Bakış | ARCHITECTURE_GUARD.md duplicate |
| 2 | Dizin Yapısı | `src/` zaten var, her yeni dosyada update gerek |
| 3.1 | Infrastructure Layer açıklaması | Kod zaten orada |
| 3.2 | Domain Layer açıklaması | Kod zaten orada |
| 3.3 | Strategy Layer açıklaması | Kod zaten orada |
| 3.4 | Orchestration Layer açıklaması | Kod zaten orada |
| 3.5 | Presentation Layer açıklaması | Kod zaten orada |
| 3.5.1 | Dashboard UI Spec | Kod + `src/static/` |
| 4 | Cycle Mimarisi (implementation flow) | `src/orchestration/` |
| 5 | Domain Modelleri | `src/models/` |
| 6.4 | Consensus Entry (Case A/B — sadece implementation kısmı) | Kod. Eşik değerleri/kurallar kalır. |
| 6.16 | Manipulation Guard (implementation) | Kod. Risk skor eşikleri kalır. |
| 8 | API Entegrasyonları | `src/infrastructure/apis/` |
| 9 | Konfigürasyon örneği | `config.yaml` duplicate |
| 10 | Test Stratejisi | `pytest.ini` + `tests/` |
| 11 | Uygulama Sırası | Geçmiş plan kaydı, işi bitti |
| 12 | Başarı Kriterleri | Bir kerelik sign-off checklist |

## 4. TDD'de Kalacak Bölümler (LAYER 1 — source of truth)

Bu bölümler koddan çıkmaz, sadece doğru kod yazmak için Claude'un bilmesi gereken "neden + sayı + kural" bilgisi.

- **§0 Temel İlkeler** — 7 invariant (bookmaker-driven, 3-cycle, sizing %, P(YES) anchor, event-guard)
- **§6.1 Bookmaker Probability formülü** — no-vig method, 3-stage fallback
- **§6.2 Confidence grading** — A/B/C eşikleri, tie-break sıralaması
- **§6.3 Edge calculation** — formül + min_edge default
- **§6.4 Consensus entry** — kuralları/eşikleri (Case A/B mantığı), implementation kod
- **§6.5 Position sizing** — %5/%4/blok yüzdeleri
- **§6.6 Scale-out 3-tier** — tier yüzdeleri ve eşikleri
- **§6.7 Flat SL 9-Katman** — her katman sayıları ve tetikleyicileri
- **§6.8 Graduated SL** — formül ve eşikler
- **§6.9-6.12** — exit kuralları sayıları
- **§6.13-6.14** — FAV promotion / Hold revocation kuralları
- **§6.15 Circuit Breaker** — DD %, günlük/haftalık limit sayıları
- **§6.17 Liquidity check** — entry min depth, halve eşik, exit fill ratio
- **§7 Sport Rules** — spor→tag mapping, bookmaker_weights değerleri
- **§13 Açık Noktalar** — referans, cevaplanmamış sorular

**Kural**: Bir §6.X bölümüne bakıldığında sadece "değer tabloları + neden notları + karar ağacı mantığı" olmalı. Python syntax'lı implementation kodu olmamalı.

---

## 5. Rule-Change Protokolü (CLAUDE.md'ye eklenecek)

Kullanıcı iş diliyle bir kural değişikliği söylediğinde Claude şu adımları uygular:

### Adım 1 — Somutlaştır
İş niyetini tek ve net parametre(ler)e çevir.

> Örnek: "Bahislerde daha seçici olalım" → `min_edge` artışı (6% → 8%?)

### Adım 2 — Tek satırda doğrulat
Kullanıcıya tek soru:

> "min_edge 0.06 → 0.08 yapıyorum, doğru mu?"

Onay alınmadan devam yok.

### Adım 3 — Tüm geçtiği yerleri bul
Grep ile ara. Tipik lokasyonlar:
- `config.yaml` (değer)
- `src/` (parametre default, kullanım)
- `tests/` (test eşikleri)
- `TDD.md` §6.X (formül/neden)
- `PRD.md` (demir kuralsa)
- `docs/superpowers/plans/*` (önceki plan kayıtları — tarihsel, dokunulmaz)

### Adım 4 — Değişim planını sun
Etkilenen dosya + satır listesi:
```
config.yaml:56            min_edge: 0.06 → 0.08
src/config/settings.py:45 min_edge: float = 0.06 → 0.08
TDD.md §6.3              "default 6%" → "default 8%"
tests/strategy/...       3 test eşiği güncellenir
```

### Adım 5 — Tek seferde uygula
Tüm dosyaları aynı turda edit et. Yarım bırakma yasak.

### Adım 6 — Doğrulama
- `pytest -q` → tümü geçmeli
- Kalan grep'te eski değer olmamalı (`grep "0.06" src/` boş dönmeli veya sadece alakasız olmalı)
- Rapor: "değiştirilen dosya sayısı, test sonucu, kalan referans var mı"

### Kritik kural
**Eğer grep'te bir dosyada eski değer görülür ama listede yoktu → bu bir drift potansiyeli.** Durdur, kullanıcıya sor.

---

## 6. Senaryo Örnekleri

### Senaryo A — Kalibrasyon değişikliği
**Kullanıcı:** "Min edge'i yükseltelim, çok bet açıyor"
**Claude:**
1. Somutlaştır: `min_edge` 0.06 → 0.08 (2 puan artış makul)
2. Doğrulat: "min_edge 0.06 → 0.08 yapıyorum?"
3. (Onay alınır)
4. Grep: `config.yaml`, `settings.py`, `TDD §6.3`, 2 test dosyası
5. Tek turda update + pytest + rapor

### Senaryo B — Kapsam daraltma
**Kullanıcı:** "Tennis'i çıkaralım"
**Claude:**
1. Somutlaştır: `scanner.allowed_sport_tags` listesinden `tennis, atp*, wta*` silinir
2. Doğrulat: "Tennis scanner kapsamından çıkarıyorum, doğru mu?"
3. Grep: `config.yaml`, `PRD.md §6.4`, `TDD.md §7`, ilgili test'ler
4. Update + pytest
5. Rapor

### Senaryo C — Yeni invariant
**Kullanıcı:** "Artık hiçbir A-conf pozisyon 95¢'ten yüksekte girmesin"
**Claude:**
1. Bu yeni bir demir kural → PRD §2 + TDD §6.X alanına eklenmeli
2. Somutlaştır: A-conf entry cap 95¢
3. Doğrulat + onay
4. PRD'ye ekle, TDD'ye ekle, kodun ilgili yerine koy, test yaz
5. Tek turda → pytest + rapor

---

## 7. Uygulama Planı (özet)

Bu spec onaylanınca:

1. **CLAUDE.md** — "Rule-Change Protokolü" bölümü eklenir; "Okuma Kuralları" LAYER 1/LAYER 2 ayrımına göre güncellenir.
2. **TDD.md** — LAYER 2 olarak listelenen bölümler silinir. §6.4 ve §6.16'daki implementation syntax'ı temizlenir, sadece kural/eşik kalır. İçindekiler tablosu güncellenir.
3. **PRD.md** — değişmez (zaten LAYER 1).
4. **ARCHITECTURE_GUARD.md** — değişmez.

Uygulama sadece dokümanları değiştirir (TDD, CLAUDE.md) — kod dokunulmaz, bu yüzden test kırılması beklenmez. Yine de her adımdan sonra `pytest -q` sanity check çalıştırılır.

---

## 8. Başarı Kriterleri

Bu sistem başarılıdır eğer:

- [ ] Bir kural değişikliği → Claude tek tura tüm dosyaları doğru günceller, drift bırakmaz
- [ ] Yeni bir conversation → CLAUDE.md + ARCH_GUARD + PRD yüklenir, kurallar aynıdır
- [ ] TDD token maliyeti eski hâlinden %40+ azalır
- [ ] Aynı bilgiyi iki ayrı dosyadan öğrenebiliyorsak (kod + TDD), birisi silinir
- [ ] Claude "TDD diyor ama kod başka" durumuyla karşılaşmaz

---

## 9. Kapsam Dışı (bu tasarımda yapılmayacak)

- Tagged rule-ID sistemi (Yaklaşım 2) — reddedildi: gizli duplikasyon
- Konsept indeksi (Yaklaşım 3) — reddedildi: bakım yükü
- PRD içeriği değişikliği
- ARCHITECTURE_GUARD içeriği değişikliği
- Kod mimarisinde refactor
