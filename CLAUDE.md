<!-- profile: full -->

# CLAUDE.md — Optimus Claudeus (Polymarket Agent)

## Development Workflow (MANDATORY — follow exactly)

### 1. Change Size Protocol

**Small** (<50 lines, single file, bug fix, API key addition):
→ Direkt implement → test → next task

**Medium** (50-200 lines, 2-3 dosya, yeni feature):
→ Taslak plan yaz → kullanıcı onayı al → implement et → mevcut kodla uyum kontrolü (ilgili dosyaları oku) → 2 paralel audit agent çalıştır → 0 hata olana kadar düzelt → next task

**Large** (yeni modül, mimari değişiklik, strateji kararı):
→ Diğer AI'lara danışmak için prompt hazırla → kullanıcı diğer AI'lardan tavsiye toplar → taslak çıkar → kullanıcı onayı → implement et → GERİ KALAN KOD İLE UYUMSUZLUK YARATMAYACAK ŞEKİLDE entegre et (gerekirse ilgili dosyaları baştan oku) → 2 paralel audit agent → 0 hata → next task

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

### 3. Integration Protocol

- Yeni kodu entegre etmeden ÖNCE: çevresindeki kodu oku, uyum sağla
- Entegre ettikten SONRA: 2 paralel audit agent çalıştır
  - Agent 1: Import + syntax validation (`python -c "from src.main import ..."`)
  - Agent 2: Logic review (yeni kod mevcut kodla doğru etkileşiyor mu? Edge case'ler?)
- İkisinde de 0 hata olana kadar düzelt
- **Death spiral'a GİRME**: Cosmetic linter uyarıları, IDE type-inference sorunları, non-breaking formatlar → ATLA
- Sadece runtime error ve logic bug düzelt
- Her iki agent da temiz dönünce → task'i tamamla, bir sonrakine geç

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
