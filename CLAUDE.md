<!-- profile: full -->

# CLAUDE.md — Optimus Claudeus (Polymarket Agent)

## Temel Kurallar (İSTİSNASIZ)
- **Kod değiştirmeden ÖNCE kullanıcıya SOR.** İzinsiz değişiklik yapma.
- **Her değişiklik öncesi planning skill kullan.** Direkt koda dalma.
- **Tek-seferlik analiz raporları (HTML/MD) `docs/` veya `plans/` altında biriktirilmez.** Üretildikten ve kullanıcı okuduktan sonra Claude tarafından silinir. Sadece kalıcı dokümantasyon `docs/` altında kalır (bot-flowchart, testing-plan, espn-api-reference vb.). Eski "rapor görmek istiyorum" çıktıları çöpe — kod tarafında bağlı değiller, runtime'da kullanılmıyorlar.
- **Plan/spec dosyaları kod docstring'lerinden referans verilmez.** `/write-plan` ve `/brainstorm` çıktıları implement bittikten sonra silinir, dolayısıyla source kodda `Spec: docs/superpowers/...` veya benzeri referans satırı yazma. Modülün ne yaptığını docstring'in kendisi anlatır, "doğum belgesi" linki tutmanın faydası yok ve dangling reference yaratır.

## Development Workflow (MANDATORY — follow exactly)

### 0. Plan-First Rule (KESİN KURAL — İSTİSNASIZ)

**Her kullanıcı talebinde, aksiyon almadan ÖNCE:**

1. Talebi küçük somut adımlara böl
2. Her adım için belirt:
   - Hangi dosya(lar) etkilenir
   - Ne değişecek (özet)
   - Risk / kırılma ihtimali
3. Planı kullanıcıya sun
4. **Onay BEKLE** — "ok/evet/yap" gelmeden kodlama başlamaz
5. Onay gelince sırayla uygula, her adımda raporla
6. Scope genişlerse (başka agent tavsiyesi, yeni bulgu vb.) → **yeni plan, yeni onay**. Bir önceki onay, yeni scope'u kapsamaz.

**İstisna (plan gerekmez):**
- READ-ONLY bilgi talebi (log okuma, grep, dosya okuma, durum sorgusu)
- Tek satır/dosya soru cevaplama (kod yazmadan)
- Kullanıcının explicit "şimdi yap" talebi (ama yine de ne yapacağını tek cümle özetle)

**İstisna DEĞİL (plan mutlaka):**
- Kod yazma/değiştirme (1 satır bile)
- Dosya silme/taşıma
- Bot start/stop/restart/reset
- Git commit/push/branch operasyonları
- Başka AI/agent çağırma

### 1. Change Size Protocol

**Small** (<50 lines, single file, bug fix, API key addition):
→ Direkt implement → test → next task

**Medium** (50-200 lines, 2-3 dosya, yeni feature):
→ Taslak plan yaz → kullanıcı onayı al → implement et → mevcut kodla uyum kontrolü (ilgili dosyaları oku) → audit (method §3 karar matrisine göre — default manual) → **2 ARDIŞIK CLEAN audit dönene kadar düzelt** (aşağıda açıklanmış) → next task

**Large** (yeni modül, mimari değişiklik, strateji kararı):
→ Diğer AI'lara danışmak için prompt hazırla → kullanıcı diğer AI'lardan tavsiye toplar → taslak çıkar → kullanıcı onayı → implement et → GERİ KALAN KOD İLE UYUMSUZLUK YARATMAYACAK ŞEKİLDE entegre et (gerekirse ilgili dosyaları baştan oku) → audit (method §3 karar matrisine göre) → **2 ARDIŞIK CLEAN audit** → dry_run smoke test → next task

### 2. Anti-Spaghetti Rules (HER ZAMAN GEÇERLİ)

- **Yeni feature ≥50 satır → AYRI DOSYA oluştur**, main.py'den import et
- **Fonksiyon >80 satır → böl**, küçük fonksiyonlara ayır
- **main.py = SADECE orchestration** — iş mantığı modüllerde yaşar
- main.py'ye kod eklemeden önce: bu mantık mevcut bir modüle ait mi kontrol et
- Aynı mantık 2+ yerde varsa → ortak fonksiyona çıkar
- Yeni modül oluştururken mevcut modüllerle interface'i düşün

### 2.5. "Önce Neyi Bozar?" Kuralı (KESİN KURAL — İSTİSNASIZ)

**Herhangi bir dosyaya herhangi bir değişiklik yapmadan ÖNCE:**

1. **Dosyanın TAMAMINI oku** — sadece değişecek satırları değil, dosyanın tüm mantığını anla
2. **Grep ile tüm projeyi tara** — değişen değişken/fonksiyon/threshold/sabit kim tarafından kullanılıyor?
3. **Kırılma analizi yap** — bu değişiklik:
   - Bu dosyadaki başka bir fonksiyonu bozar mı?
   - Başka dosyalardaki tüketicileri bozar mı?
   - Test assertion'larını kırar mı?
   - Disk'teki cache/log formatıyla çakışır mı?
   - Validation/sanity check katmanlarını tetikler mi?
4. **Kırılma bulursan → ÖNCE kullanıcıya sor:** "Bu değişiklik şurayı bozacak, önce onu fix'leyelim mi?"
5. **Kullanıcı onayladıktan sonra** → önce kırılmayı fix'le, sonra asıl değişikliği yap

**Bu kural istisnasızdır:**
- 1 satır değişiklik bile olsa uygula
- "Basit threshold" bile olsa uygula
- "Sadece log ekliyorum" bile olsa uygula
- Kısacası: **kod dokunacaksan, önce neyi bozacağını bil ve sor**

### 3. Audit Protocol (KESİN KURAL)

#### Ne Zaman Audit Yapılır?
- Medium/Large değişiklik tamamlandıktan sonra (≥50 satır veya 2+ dosya)
- Small değişikliklerde audit YAPILMAZ

#### Audit Nasıl Yapılır? — Manual = Default, Agent = İstisna

**Pre-audit context budget check (ZORUNLU — audit başlatmadan önce sor):**
1. Bu session'da kaç Read + Edit yaptım? (mental sayım)
2. Bot çalışıyor mu? (`tasklist | grep python`)
3. Bu session'da zaten bir audit agent spawn edildi mi?

**Karar matrisi:**

| Durum | Method |
|---|---|
| Medium change (50-200 satır, 2-3 dosya) | **Manual audit** |
| Large change + pre-audit <30 Read/Edit + bot idle + 0 agent bu session | Agent spawn OK |
| Large change + pre-audit ≥30 Read/Edit | **Manual audit** (context bloated) |
| Large change + pre-audit ≥50 Read/Edit | **Session-split öner** — "cleanup'ı commit'leyip yeni session'da audit yapalım mı?" |
| Kullanıcı "agent ile audit yap" dediyse | Agent spawn (budget check atla) |

**Manual audit adımları:**
1. `git diff --name-only` → değişen dosya listesi
2. Her değişen dosya için: Read (offset+limit ile sadece değişen region'lar, küçük dosyalar full)
3. Her değişen symbol için: Grep ile consumer'ları bul
4. Sadece grep'in döndürdüğü consumer dosyalarını oku (blind Read YOK)
5. Aşağıdaki "Agent Prompt Şablonu"ndaki PHASE 1 + PHASE 2 checklist'ini zihinsel uygula
6. Bulguları rapor et: `file:line — description — severity`

**Agent audit adımları:**
1. `git diff --name-only` → değişen dosya listesi
2. **TEK bir audit agent başlat** — aşağıdaki "Agent Prompt Şablonu"nu kullan

#### Agent Prompt Şablonu:
Audit agent spawn edilecekse → `plans/audit-template.md` dosyasını oku ve kullan.

#### Kilitlenme Koruması:
- Paralel agent YASAK — aynı anda max 1 agent
- Agent 3 dakikadan uzun sürerse → kullanıcıya bildir
- **Death spiral koruması: max 3 FIX turu**, sonra kullanıcıya sor
  (1 FIX turu = non-clean audit + kod düzeltme. CLEAN audit'ler sayılmaz.)
- Cosmetic issue (linter, type-inference, format) → ATLA, sayaç sıfırlanmaz

#### Terminasyon Kuralı — 2 Ardışık CLEAN:
Audit'in tek seferlik CLEAN sonucu yeterli DEĞİLDİR. İlk CLEAN bir false negative
olabilir (agent bir şeyi kaçırmış olabilir). Bu yüzden:

1. **Audit 1 koş** → bulgular var mı?
2. Bulgular varsa → düzelt → **Audit 2 koş**
3. Audit 2 CLEAN ise → **mutlaka bir Audit 3 daha koş**
4. Audit 3 de CLEAN ise → **iş biter** (2 ardışık CLEAN sağlandı)
5. Audit 3 bulgu bulursa → düzelt → Audit 4 → Audit 5 (yine 2 ardışık CLEAN ara)
6. 3 FIX turunda hâlâ 2 ardışık CLEAN yakalanamadıysa → kullanıcıya sor

#### Entegrasyon Kuralları:
- Yeni kodu entegre etmeden ÖNCE: çevresindeki kodu oku, uyum sağla
- **2 ardışık CLEAN audit** dönünce → task'i tamamla, bir sonrakine geç

#### Güvenlik Zinciri Özeti:
1. §2.5 "Önce Neyi Bozar?" → değişiklik öncesi koruma (grep + kırılma analizi)
2. Audit (manual default / agent istisna — karar matrisine bak) → değişiklik sonrası koruma (değişen dosyalar + grep-verified consumers)
3. Large changes → dry_run smoke test (bot'u çalıştırıp hata kontrolü)

### 4. Multi-AI Consultation (Large changes only)

Kullanıcı mimari konularda diğer AI'lara (Gemini, ChatGPT) danışmak istiyor:
1. Kullanıcıya kopyalayıp yapıştırabileceği detaylı prompt hazırla
2. Prompt: mevcut mimariyi açıkla, ne yapmak istediğimizi belirt, spesifik sorular sor
3. Kullanıcı tavsiyeleri getirir → birlikte değerlendir → en iyi yaklaşımı seç
4. Onaylanan yaklaşımı implement et

### 5. Bot Process Kuralları (KESİN KURAL)

- **SADECE 1 BOT çalışabilir** — birden fazla instance yasak
- Bot başlatmadan ÖNCE: `tasklist | grep python` → tüm src.main process'lerini bul → hepsini kill et → sonra başlat
- Bot başlatma iznini kullanıcıdan al — izinsiz başlatma yasak
- Restart = önce kill, sonra izin al, sonra başlat

### 6. Task Management

- **TodoWrite tool'u KULLAN** her zaman — task'leri sadece text olarak listeleme
- TODO comment'leri kodda bırakıyorsan → aynısını TodoWrite'a da ekle
- Bir task bitince hemen `completed` işaretle, biriktirme
- Aynı anda sadece 1 task `in_progress` olabilir

## API Guides
API guide'ları büyük. Lazım olunca: önce index oku, sonra offset+limit ile ilgili bölümü oku. Full okuma YASAK.

## Environment
- Python 3.11+, Windows 11
- `.env` for all secrets (NEVER hardcode)
- `logs/` for runtime data (portfolio, trades, exits)
- Bot runs from project root: `python -m src.main`

## Key Constraints
- NEVER restart/kill/start bot without explicit user permission
- NEVER spend AI (Anthropic) credits without explicit permission
- Default to dry_run mode — never suggest live without confirmation
- Risk manager has VETO power — no trade bypasses risk checks
- Type hints on all functions, Pydantic for models
- Log every decision
- Esports: NEVER filter by volume, only liquidity (volume spikes 2h before match)
- Only moneyline/series winner bets — filter spread/totals/props
- "Reset/yeniden başlat" = clear all data; "botu baştan başlat" = restart process only
