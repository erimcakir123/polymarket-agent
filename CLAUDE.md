<!-- profile: full -->

# CLAUDE.md — Optimus Claudeus (Polymarket Agent)

## Temel Kurallar (İSTİSNASIZ)
- **Kod değiştirmeden ÖNCE kullanıcıya SOR.** İzinsiz değişiklik yapma.
- **Her değişiklik öncesi planning skill kullan.** Direkt koda dalma.

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

**Neden:** Önceki sessionda scope creep ile plansız eklenen değişiklikler tekrar iş çıkardı. Plan-first = hata minimizasyonu + şeffaflık.

### 1. Change Size Protocol

**Small** (<50 lines, single file, bug fix, API key addition):
→ Direkt implement → test → next task

**Medium** (50-200 lines, 2-3 dosya, yeni feature):
→ Taslak plan yaz → kullanıcı onayı al → implement et → mevcut kodla uyum kontrolü (ilgili dosyaları oku) → 1 audit agent (sadece değişen dosyalar + bağımlılıkları) → 0 hata olana kadar düzelt → next task

**Large** (yeni modül, mimari değişiklik, strateji kararı):
→ Diğer AI'lara danışmak için prompt hazırla → kullanıcı diğer AI'lardan tavsiye toplar → taslak çıkar → kullanıcı onayı → implement et → GERİ KALAN KOD İLE UYUMSUZLUK YARATMAYACAK ŞEKİLDE entegre et (gerekirse ilgili dosyaları baştan oku) → 1 audit agent (değişen dosyalar + bağımlılıkları) → 0 hata → dry_run smoke test → next task

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

#### Audit Nasıl Yapılır?
1. **Değişen dosya listesini hazırla** — `git diff --name-only` ile
2. **TEK bir audit agent başlat** — aşağıdaki şablonu kullan

#### Agent Prompt Şablonu:
```
PHASE 1 — Scoped Context (grep-first, RAM-aware):

1. Read ONLY the files listed as CHANGED in PHASE 2 below.
2. For each changed file, discover external consumers via grep (not Read):
     Grep pattern: "from src.<module>|import.*<module_name>"
     Grep pattern: "<exported_function_name>|<exported_class_name>"
   Look at the grep output as a LIST of candidate files — do not open them blindly.
3. Read ONLY the consumer files that grep actually returned. These are the
   files that could be broken by the change. Nothing else is relevant.
4. For huge consumer files (>1000 lines), read only the relevant function/region
   via Read(..., offset=X, limit=Y). Do not load entire large files.

BANNED patterns (cause RAM crashes, wasted context):
- "Read ALL src/*.py files" — blind glob-and-read. This is the #1 audit crash cause.
- Reading files that grep did not return as consumers.
- Reading API Guides/, docs/, logs/, tests/, .env, config YAML that is unchanged.
- Spawning sub-agents (subagent_type=Agent).

PREFERRED patterns:
- Grep over Read for symbol-level flow understanding.
- Targeted Read with offset+limit for huge files.
- Early "CLEAN" exit if grep shows no broken references in consumers.

PHASE 2 — Focused Audit: Check these CHANGED files for issues:
Files: [liste]
Changes: [her dosyada ne değişti, 1 cümle]

Look for:
- Runtime errors (missing imports, wrong args, undefined vars)
- Logic bugs (wrong conditions, broken control flow, edge cases)
- Breaking changes (değişiklik başka dosyaları bozuyor mu? — grep-verified)
- Interface mismatches (fonksiyon signature değişti ama caller güncellenmedi mi?)
- Dead code (kullanılmayan fonksiyon, import, değişken — RAPORLA ama silme, kullanıcıya sor)
- Spaghetti code (fonksiyon >80 satır mı? aynı mantık 2+ yerde mi? iş mantığı main.py'de mi?)

Rules:
- Do NOT spawn sub-agents
- Do NOT read API Guides or docs/ — bunlar büyük, kilitler
- IGNORE: cosmetic issues, type hints, docstrings, formatting, naming style
- Report format: file:line — description — severity (critical/warning)
```

#### Kilitlenme Koruması:
- Paralel agent YASAK — aynı anda max 1 agent
- Agent 3 dakikadan uzun sürerse → kullanıcıya bildir
- Death spiral koruması: max 3 audit turu, sonra kullanıcıya sor
- Cosmetic issue (linter, type-inference, format) → ATLA, sayaç sıfırlanmaz

#### Entegrasyon Kuralları:
- Yeni kodu entegre etmeden ÖNCE: çevresindeki kodu oku, uyum sağla
- Temiz audit dönünce → task'i tamamla, bir sonrakine geç

#### Güvenlik Zinciri Özeti:
1. §2.5 "Önce Neyi Bozar?" → değişiklik öncesi koruma (grep + kırılma analizi)
2. Audit agent → değişiklik sonrası koruma (değişen dosyalar + grep-verified consumers)
3. Large changes → dry_run smoke test (bot'u çalıştırıp hata kontrolü)

**Neden grep-first PHASE 1?**
Eski şablon "Read ALL src/*.py" diyordu → 60+ dosya belleğe yükleniyor → Windows RAM
doygunluğu → audit sırasında hard crash / Windows restart (2026-04-09 tespit edildi).
Grep-first yaklaşımda sadece *alakalı* consumer'lar okunur, kapsam otomatik olarak
değişikliğin gerçek etki alanına daralır. Kalite kaybı yok — çünkü grep 20 consumer
bulursa agent 20'yi de okur, sadece alakasız dosyalar eleniyor.

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

## Project Structure
```
src/
  main.py            — Entry point, logging setup
  agent.py           — Agent class, cycle orchestration (KEEP LEAN)
  config.py          — YAML config, Pydantic models, all thresholds
  market_scanner.py  — Gamma API market discovery + pre-filtering
  ai_analyst.py      — Claude API calls, prompt building, budget tracking
  edge_calculator.py — Edge computation, direction detection
  risk_manager.py    — Confidence-based sizing + risk gates
  portfolio.py       — Position tracking, PnL, equity snapshots
  executor.py        — Order execution (dry/paper/live) + fetch_order_book
  exit_monitor.py    — Exit detection (SL, trailing TP, match exit)
  exit_executor.py   — Exit execution + reentry/blacklist routing
  trailing_tp.py     — Trailing take-profit with peak tracking
  match_exit.py      — Match-aware exits (score, time, upset forced)
  news_scanner.py    — Tavily → NewsAPI → GNews → RSS fallback chain
  odds_api.py        — Bookmaker odds (The Odds API)
  sports_data.py     — ESPN API (free, no key)
  liquidity_check.py — CLOB orderbook depth (PRE-LIVE: not yet wired)
  reentry_farming.py — 3-tier re-entry pool
  reentry.py         — Graduated blacklist + re-entry eligibility
  outcome_tracker.py — Post-exit market tracking
  price_history.py   — CLOB price history on close
  notifier.py        — Telegram notifications + command polling
  circuit_breaker.py — Consecutive loss / PnL halt
  self_improve.py    — Parameter tuning from trade history
```

## API Guides (MANDATORY — read index first)
API guide'ları çok büyük (18K-78K satır). **Asla full okuma — önce index oku, sonra lazım olan bölümü offset+limit ile oku.**

```
API Guides/
  ESPN API/
    espn-api-index.md              ← ÖNCE BUNU OKU (284 satır)
    Public-ESPN-API-FULL.md        ← 18,617 satır — sadece index'ten bulunan bölümü oku
  Pandascore API/
    pandascore-complete-index.md   ← ÖNCE BUNU OKU (164 satır)
    pandascore-complete-reference.md ← 2,354 satır
  Polymarket API/
    polymarket-api-index.md        ← ÖNCE BUNU OKU (211 satır)
    polymarket-full-api-reference.md ← 78,024 satır — KESİNLİKLE full okuma
```

Kullanım: Index'te bölüm bul → `Read("API Guides/.../full-ref.md", offset=START, limit=SIZE)`

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
