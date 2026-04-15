# Dashboard + Exposure Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Son oturum değişikliklerini clean state'e çek — TDD + PRD güncel, testler tam, JS modüler, ARCH_GUARD uyumlu.

**Architecture:** Phased execution — docs first (formalize what code already does), tests next (regression coverage), refactor last (JS module split). Her faz bağımsız commit edilir.

**Tech Stack:** Python 3.12, pytest, Flask (dashboard), vanilla JS (ES2022, `:has()` CSS selector).

**Spec reference:** [docs/superpowers/specs/2026-04-15-dashboard-exposure-cleanup-design.md](../specs/2026-04-15-dashboard-exposure-cleanup-design.md)

---

## Task 1: Commit Exposure Fix (Faz 1)

Current working tree has the exposure fix from earlier in this session — test_exposure.py, exposure.py, gate.py, agent.py, test_agent_heavy_stages.py. Commit it atomically.

**Files:**
- Modify: `src/domain/portfolio/exposure.py` — rename param + docstring
- Modify: `src/strategy/entry/gate.py:161-166` — caller passes total_portfolio
- Modify: `src/orchestration/agent.py:213-225` — same
- Modify: `tests/unit/domain/portfolio/test_exposure.py` — renames + regression test
- Modify: `tests/unit/orchestration/test_agent_heavy_stages.py:16` — mock fix

- [ ] **Step 1: Verify tests pass with current changes**

Run: `python -m pytest tests/unit -q`
Expected: `627 passed`

- [ ] **Step 2: Review diff**

Run: `git diff --stat`
Expected: 5 files modified.

- [ ] **Step 3: Commit**

```bash
git add src/domain/portfolio/exposure.py \
        src/strategy/entry/gate.py \
        src/orchestration/agent.py \
        tests/unit/domain/portfolio/test_exposure.py \
        tests/unit/orchestration/test_agent_heavy_stages.py
git commit -m "$(cat <<'EOF'
fix(risk): exposure cap formula uses total portfolio value

Caller (gate.py, agent.py) now passes bankroll + total_invested() as the
denominator, matching the original semantic. Previous bug: payda nakit
olunca pozisyon açıldıkça küçülüp cap erken tetikleniyordu (ör. $340
invested + $50 candidate → 59% yerine 39% olmalıydı).

Param rename: bankroll → total_portfolio_value (unambiguous).
Regression test: test_exposure_real_scenario_regression.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: Commit created.

---

## Task 2: TDD.md — Exposure Cap Formula (Faz 2.1)

**Files:**
- Modify: `TDD.md` — §6.15'e alt-başlık ekle

- [ ] **Step 1: Find §6.15 end**

Run: `grep -n "^### 6\.1[56]" TDD.md`
Expected: §6.15 ve §6.16 başlıkları.

- [ ] **Step 2: Insert Exposure Cap subsection before §6.16**

Edit TDD.md — §6.15 sonunda (§6.16'dan ÖNCE) şunu ekle:

```markdown

**Exposure Cap (entry blok):**

Formül:
```
exposure = (toplam_yatırılan + aday_size) / toplam_portföy_değeri
toplam_portföy_değeri = portfolio.bankroll (nakit) + portfolio.total_invested()
```

`max_exposure_pct` (config `risk.max_exposure_pct`, default 0.50) aşılırsa
entry reddedilir (`skip_reason: exposure_cap_reached`).

**Kritik invariant:** payda TOPLAM portföy değeri — nakit değil. `portfolio.bankroll`
açık pozisyonlar düşülmüş kullanılabilir nakit olduğundan, doğrudan payda
yapılırsa pozisyon açıldıkça küçülüp cap erken tetikler.

**Pure function:** `domain/portfolio/exposure.py::exceeds_exposure_limit`.
**Caller:** `strategy/entry/gate.py` + `orchestration/agent.py` her ikisi de
`pm.bankroll + pm.total_invested()` hesaplayıp geçer.
**Test:** `tests/unit/domain/portfolio/test_exposure.py::test_exposure_real_scenario_regression`
```

- [ ] **Step 3: Commit**

```bash
git add TDD.md
git commit -m "$(cat <<'EOF'
docs(tdd): document exposure cap formula + invariant

§6.15'e "Exposure Cap" alt-başlığı: formül, payda=toplam portföy kuralı,
pure function + caller + test referansları.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: TDD.md — §5.7 Dashboard Display Rules (Faz 2.2)

**Files:**
- Modify: `TDD.md` — yeni §5.7 bölümü

- [ ] **Step 1: Find insertion point (after §5.6)**

Run: `grep -n "^### 5\." TDD.md`
Expected: §5.1 ... §5.6 başlıkları.

- [ ] **Step 2: Append §5.7 after §5.6**

`### 5.6 Test Kapsamı` bölümünün sonuna (sonraki §6 başlamadan ÖNCE) şunu ekle:

```markdown

### 5.7 Dashboard Display Rules

Dashboard presentation katmanı — kurallar domain kurallarından ayrı.
`presentation/dashboard/computed.py` + `static/js/*` sınırında enforce edilir.

#### 5.7.1 Treemap Branş Gruplaması

Gruplama anahtarı = **sport category** (baseball, hockey, tennis, ...).
Lig kodları (mlb, nhl, vb.) branşa map edilir:

```python
_LEAGUE_TO_SPORT = {
    "mlb": "baseball",
    "nhl": "hockey", "ahl": "hockey", "khl": "hockey",
    "nba": "basketball", "wnba": "basketball",
    "nfl": "football", "cfl": "football",
    "epl": "soccer", "ucl": "soccer", "mls": "soccer", "seriea": "soccer",
    "wta": "tennis", "atp": "tennis",
    "pga": "golf", "lpga": "golf", "rbc": "golf",
}
```

Öncelik: `sport_category` field → `sport_tag` split (`baseball_mlb`→baseball) →
lig map (eski kayıt: `mlb`→baseball) → sport_tag as-is → `unknown`.

Lokasyon: `presentation/dashboard/computed.py::_sport_category`.

#### 5.7.2 Direction-Adjusted Odds Display

**Saklama invariantı** (ARCH Kural 7): `anchor_probability = P(YES)`;
`entry_price`/`current_price` = token-native (BUY_YES→YES, BUY_NO→NO).

**Display kuralları:**
- Active card `Odds X%`: `direction == "BUY_NO" ? 1 − anchor : anchor`.
- `Entry/Now` fiyatları zaten token-native → ek çevrim YOK.
- YES/NO badge metni = slug team-code:
  - BUY_YES → slug pattern'deki ilk takım (yes-side).
  - BUY_NO → ikinci takım (no-side).
  - Slug eşleşmezse fallback `"YES"` / `"NO"`.

Lokasyon: `static/js/feed.js::_activeCard` + `static/js/dashboard.js::FMT.sideCode`.

#### 5.7.3 Feed Sort

Her tab (Active/Exited/Skipped/Stock): `match_start_iso` ASC (en yakın maç
yukarıda). Boş değerler sona.

Lokasyon: `static/js/feed.js::FEED.render`.

#### 5.7.4 CSS Palette — Tek Kaynak

Renkli hex literal **sadece** `static/css/dashboard.css:root` içinde tanımlı.
Başka CSS/JS dosyasında renkli hex YASAK — hep `var(--*)`.

Değişken ailesi:
- Ana: `--green`, `--red`, `--blue`, `--orange`
- Türev: `-dim`, `-dark`, `-hover`, `-strong` (opacity/shade varyantları)
- Nötr: `--bg`, `--panel*`, `--text`, `--muted*`, `--border-soft`

JS chart renkleri (Chart.js canvas) runtime'da okur:
```js
getComputedStyle(document.documentElement).getPropertyValue("--green")
```

Böylece palette değişimi tek yerden (`:root`).
```

- [ ] **Step 3: Commit**

```bash
git add TDD.md
git commit -m "$(cat <<'EOF'
docs(tdd): add §5.7 Dashboard Display Rules

4 alt-bölüm: treemap branş mapping, direction-adjusted odds, feed sort
(match_start ASC), CSS palette single-source invariantı. Kod referansları
dahil (computed.py, feed.js, FMT.sideCode, :root).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: PRD.md — Exposure Clarification (Faz 2.3)

**Files:**
- Modify: `PRD.md` — §3.3'e tek cümle

- [ ] **Step 1: Find §3.3**

Run: `grep -n "^### 3\.3\|Circuit Breaker" PRD.md | head -5`

- [ ] **Step 2: Add exposure semantic sentence**

§3.3 (Circuit Breaker / Risk Yönetimi) bölümünün sonuna şunu ekle:

```markdown

**Exposure cap enforcement:** hem gate-time (entry öncesi) hem execution-time
(order öncesi) kontrol edilir, payda **toplam portföy değeri** (nakit + açık
pozisyonlar) — nakit değil. Detay: TDD §6.15.
```

- [ ] **Step 3: Commit**

```bash
git add PRD.md
git commit -m "$(cat <<'EOF'
docs(prd): clarify exposure cap uses total portfolio as denominator

§3.3'e tek satır: payda = nakit + açık pozisyonlar, nakit değil. TDD §6.15
referansı.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Tests — `_sport_category` Coverage (Faz 3.1)

**Files:**
- Create: `tests/unit/presentation/test_computed_sport_category.py`

- [ ] **Step 1: Write failing test file**

Create file with this content:

```python
"""computed.py::_sport_category ve treemap branş gruplaması testleri."""
from __future__ import annotations

from src.presentation.dashboard.computed import _sport_category, sport_roi_treemap


def _trade(**kwargs):
    base = {
        "slug": "x",
        "exit_price": 0.5,  # kapalı trade (treemap'e dahil)
        "exit_pnl_usdc": 0.0,
        "size_usdc": 10.0,
    }
    base.update(kwargs)
    return base


def test_sport_category_from_underscore_tag():
    assert _sport_category({"sport_tag": "baseball_mlb"}) == "baseball"


def test_sport_category_from_league_map_mlb():
    assert _sport_category({"sport_tag": "mlb"}) == "baseball"


def test_sport_category_from_league_map_nhl():
    assert _sport_category({"sport_tag": "nhl"}) == "hockey"


def test_sport_category_from_league_map_ahl():
    assert _sport_category({"sport_tag": "ahl"}) == "hockey"


def test_sport_category_tennis():
    assert _sport_category({"sport_tag": "wta"}) == "tennis"
    assert _sport_category({"sport_tag": "atp"}) == "tennis"


def test_sport_category_prefers_explicit_category_when_not_league_code():
    # sport_category "hockey" gerçek branş — döner.
    assert _sport_category({"sport_tag": "", "sport_category": "hockey"}) == "hockey"


def test_sport_category_ignores_category_if_it_is_a_league_code():
    # sport_category "mlb" aslında lig → map'ten branşa.
    assert _sport_category({"sport_tag": "mlb", "sport_category": "mlb"}) == "baseball"


def test_sport_category_unknown_fallback():
    assert _sport_category({"sport_tag": "xyz"}) == "xyz"


def test_sport_category_empty_defaults_unknown():
    assert _sport_category({}) == "unknown"


def test_treemap_merges_nhl_and_hockey_records():
    """Regression: nhl lig kodu + hockey branşı kayıtları tek 'hockey' grubunda."""
    trades = [
        _trade(sport_tag="nhl", exit_pnl_usdc=-10.0, size_usdc=50.0),
        _trade(sport_tag="hockey", exit_pnl_usdc=5.0, size_usdc=25.0),
        _trade(sport_tag="ahl", exit_pnl_usdc=-3.0, size_usdc=20.0),
    ]
    result = sport_roi_treemap(trades)
    leagues = {g["league"]: g for g in result["leagues"]}
    assert "hockey" in leagues
    assert "nhl" not in leagues  # ham lig kodu görünmemeli
    assert "ahl" not in leagues
    assert leagues["hockey"]["trades"] == 3
    assert leagues["hockey"]["invested"] == 95.0
    assert leagues["hockey"]["net_pnl"] == -8.0
```

- [ ] **Step 2: Run test — expect pass (implementation already exists)**

Run: `python -m pytest tests/unit/presentation/test_computed_sport_category.py -v`
Expected: All tests PASS (implementation done earlier).

- [ ] **Step 3: Verify full suite still green**

Run: `python -m pytest tests/unit -q`
Expected: `637 passed` (627 + 10 new).

- [ ] **Step 4: Commit**

```bash
git add tests/unit/presentation/test_computed_sport_category.py
git commit -m "$(cat <<'EOF'
test(presentation): add sport_category + treemap merge coverage

10 test: _sport_category'nin tüm öncelik dallları (split → category →
league map → as-is → unknown) + treemap'in nhl/ahl/hockey kayıtlarını
tek grupta toplaması için regression.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: FMT Contract Doc (Faz 3.2)

**Files:**
- Create: `docs/dashboard-fmt-contract.md`

- [ ] **Step 1: Write contract doc**

Create file:

```markdown
# Dashboard FMT Namespace Contract

`static/js/fmt.js` (Task 9+ sonrası; öncesi `dashboard.js`) global `window.FMT`.

Tüm helper'lar **pure** (I/O yok, side-effect yok). Çıktı hep HTML-escape'li
string — `innerHTML`'e güvenle yazılabilir.

## Helpers

### `FMT.escapeHtml(s: string): string`
HTML meta karakterleri (`& " < >`) escape eder.

### `FMT.usdSignedHtml(n: number): string`
`+$10.00` / `-$5.25` formatında, decimal kısmı `<span class="dec">` içinde.

### `FMT.pctSigned(n: number, digits?: number): string`
Yüzde değeri, işaretli. `null/undefined/NaN` → `"--"`.

### `FMT.cents(price: number): string`
`65¢` formatında (0-1 aralığı × 100 yuvarlanır).

### `FMT.relTime(iso: string): string`
`"just now" | "Xm ago" | "Xh ago" | "Xd ago"`.

### `FMT.time(iso: string): string`
Lokal saat `HH:MM` (geçersiz → `""`).

### `FMT.polyUrl(slug: string): string`
`https://polymarket.com/event/<slug>` (slug yoksa `"#"`).

### `FMT.pnlClass(n: number): string`
`"pnl-pos" | "pnl-neg" | "pnl-zero"` — 0.001 eşiği.

### `FMT.unrealizedClass(n: number): string`
`"unr-pos" | "unr-neg" | "pnl-zero"` — open PnL renk sınıfı (pozitif mavi).

### `FMT.teamsText(question: string, slug: string): string`
Market başlığını insana okunur yapar (HTML-escape'li).

**Öncelik:**
1. `question` varsa "X vs Y" pattern'inden iki yanı çıkar (ör. "Arizona Diamondbacks vs Baltimore Orioles").
2. Yoksa slug pattern'i:
   - `"{sport}-{t1}-{t2}-YYYY-MM-DD"` → `TEAM_NAMES[t1] + " vs " + TEAM_NAMES[t2]`.
     Map yoksa: kısa kod → uppercase, uzun kod → Title-Case.
   - `"...winner-{first}-{last}"` → "First Last" (golf-style).
3. Hiçbiri eşleşmezse slug olduğu gibi.

### `FMT.sideCode(direction: "BUY_YES"|"BUY_NO", slug: string): string`
Badge metni: slug yes-code veya no-code (uppercase).
Slug eşleşmezse fallback `"YES"` / `"NO"`.

## TEAM_NAMES Map

Lokasyon: `fmt.js` içinde `const TEAM_NAMES`. Anahtar = lowercase kısa kod.
İçerik: 30+ MLB + 25+ NHL takım şehir/isim eşlemesi.

Eklenecek spor (NBA/NFL/soccer/tennis) için `TEAM_NAMES`'e giriş eklenir —
`FMT.teamsText` otomatik kullanır.

## Breaking Change Protokolü

Bu dosya **kontrat**. Helper imzası/davranışı değişirse:
1. Bu dosyayı güncelle.
2. Tüm tüketicileri (`branches.js`, `feed.js`, `dashboard.js`) gözden geçir.
3. Regression testi (mümkünse) ekle.
```

- [ ] **Step 2: Commit**

```bash
git add docs/dashboard-fmt-contract.md
git commit -m "$(cat <<'EOF'
docs: add FMT namespace contract for dashboard JS

Pure helper'ların imzaları, öncelik kuralları (teamsText fallback chain),
TEAM_NAMES map lokasyonu, breaking-change protokolü.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: JS Modül Bölme — `fmt.js` Ayrıştırma (Faz 4.1)

Amaç: `dashboard.js`'ten FMT + TEAM_NAMES'i ayrı dosyaya al.

**Files:**
- Create: `src/presentation/dashboard/static/js/fmt.js`
- Modify: `src/presentation/dashboard/static/js/dashboard.js` — FMT + TEAM_NAMES sil
- Modify: `src/presentation/dashboard/templates/dashboard.html` — script tag ekle

- [ ] **Step 1: Create fmt.js**

Create `src/presentation/dashboard/static/js/fmt.js`:

```javascript
/* FMT namespace — pure display helpers + TEAM_NAMES map.
 *
 * Tüm fonksiyonlar pure (I/O yok). Döndürülen string'ler HTML-escape'li.
 * Kontrat: docs/dashboard-fmt-contract.md
 */
(function (global) {
  "use strict";

  // Team code → full city/team adı. Slug'dan title üretimi için kullanılır.
  const TEAM_NAMES = {
    // MLB
    ari: "Arizona", atl: "Atlanta", bal: "Baltimore", bos: "Boston",
    chc: "Chi. Cubs", cws: "Chi. Sox", chw: "Chi. Sox", cin: "Cincinnati",
    cle: "Cleveland", col: "Colorado", det: "Detroit", hou: "Houston",
    kc: "Kansas City", kcr: "Kansas City", laa: "LA Angels", lad: "LA Dodgers",
    mia: "Miami", mil: "Milwaukee", min: "Minnesota", nym: "NY Mets",
    nyy: "NY Yankees", oak: "Oakland", phi: "Philadelphia", pit: "Pittsburgh",
    sd: "San Diego", sdp: "San Diego", sf: "San Francisco", sfg: "San Francisco",
    sea: "Seattle", stl: "St. Louis", tb: "Tampa Bay", tbr: "Tampa Bay",
    tex: "Texas", tor: "Toronto", was: "Washington", wsh: "Washington",
    // NHL (çakışan kodlar MLB ile aynı şehir)
    ana: "Anaheim", buf: "Buffalo", cgy: "Calgary", car: "Carolina",
    chi: "Chicago", cbj: "Columbus", dal: "Dallas", edm: "Edmonton",
    fla: "Florida", lak: "LA Kings", mon: "Montreal", mtl: "Montreal",
    nsh: "Nashville", nj: "NJ Devils", njd: "NJ Devils", nyi: "NY Islanders",
    nyr: "NY Rangers", ott: "Ottawa", sj: "San Jose", sjs: "San Jose",
    tbl: "Tampa Bay", van: "Vancouver", vgk: "Vegas", wpg: "Winnipeg",
  };

  const FMT = {
    _splitDecimal(n, digits) {
      const d = digits == null ? 2 : digits;
      const parts = Math.abs(n).toFixed(d).split(".");
      return { intPart: parts[0], decPart: parts[1] || "" };
    },
    usd(n, digits) {
      const { intPart, decPart } = this._splitDecimal(n, digits);
      return `$${intPart}<span class="dec">.${decPart}</span>`;
    },
    usdSigned(n, digits) {
      const sign = n < 0 ? "-" : "+";
      const { intPart, decPart } = this._splitDecimal(n, digits);
      return `${sign}$${intPart}<span class="dec">.${decPart}</span>`;
    },
    usdSignedHtml(n) { return this.usdSigned(n, 2); },
    pctSignedHtml(n, digits) {
      if (n === null || n === undefined || isNaN(n)) return "--";
      const { intPart, decPart } = this._splitDecimal(n, digits);
      const sign = n < 0 ? "-" : "";
      return `${sign}${intPart}<span class="dec">.${decPart}</span>%`;
    },
    pnlClass(n) {
      if (n > 0.001) return "pnl-pos";
      if (n < -0.001) return "pnl-neg";
      return "pnl-zero";
    },
    unrealizedClass(n) {
      if (n > 0.001) return "unr-pos";
      if (n < -0.001) return "unr-neg";
      return "pnl-zero";
    },
    time(iso) {
      if (!iso) return "";
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    },
    relTime(iso) {
      if (!iso) return "";
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      const diffMin = Math.floor((Date.now() - d.getTime()) / 60000);
      if (diffMin < 1) return "just now";
      if (diffMin < 60) return diffMin + "m ago";
      const h = Math.floor(diffMin / 60);
      if (h < 24) return h + "h ago";
      return Math.floor(h / 24) + "d ago";
    },
    polyUrl(slug) {
      if (!slug) return "#";
      return "https://polymarket.com/event/" + encodeURIComponent(slug);
    },
    cents(price) { return Math.round(price * 100) + "¢"; },
    pctSigned(n, digits) {
      if (n === null || n === undefined || isNaN(n)) return "--";
      const d = digits == null ? 0 : digits;
      return (n >= 0 ? "+" : "") + n.toFixed(d) + "%";
    },
    escapeHtml(s) {
      return String(s)
        .replace(/&/g, "&amp;").replace(/"/g, "&quot;")
        .replace(/</g, "&lt;").replace(/>/g, "&gt;");
    },
    // Market başlığı — question > slug pattern > slug fallback. HTML-escape'li.
    teamsText(question, slug) {
      return this.escapeHtml(
        this._fromQuestion(question) || this._fromSlug(slug) || (slug || "--")
      );
    },
    _fromQuestion(q) {
      if (!q) return null;
      const parts = String(q).split(/\s+vs\.?\s+/i);
      if (parts.length !== 2) return null;
      return `${parts[0].trim()} vs ${parts[1].trim()}`;
    },
    _fromSlug(slug) {
      if (!slug) return null;
      const s = String(slug);
      const team = s.match(/^[a-z]+-([a-z0-9]{2,15})-([a-z0-9]{2,15})-\d{4}-\d{2}-\d{2}$/i);
      if (team) return `${this._expandCode(team[1])} vs ${this._expandCode(team[2])}`;
      const winner = s.match(/winner-([a-z-]+)$/i);
      if (winner) {
        return winner[1].split("-").map(
          (w) => w.charAt(0).toUpperCase() + w.slice(1)
        ).join(" ");
      }
      return null;
    },
    _expandCode(code) {
      const key = code.toLowerCase();
      if (TEAM_NAMES[key]) return TEAM_NAMES[key];
      return code.length <= 4 ? code.toUpperCase()
        : code.charAt(0).toUpperCase() + code.slice(1).toLowerCase();
    },
    // BUY_YES → slug yes-code; BUY_NO → no-code. Slug eşleşmezse "YES"/"NO".
    sideCode(direction, slug) {
      const m = String(slug || "").match(
        /^[a-z]+-([a-z0-9]{2,15})-([a-z0-9]{2,15})-\d{4}-\d{2}-\d{2}$/i
      );
      if (!m) return direction === "BUY_YES" ? "YES" : "NO";
      return (direction === "BUY_YES" ? m[1] : m[2]).toUpperCase();
    },
  };

  global.FMT = FMT;
})(window);
```

- [ ] **Step 2: Remove FMT + TEAM_NAMES from dashboard.js**

Edit `src/presentation/dashboard/static/js/dashboard.js`:
- `const FMT = { ... };` bloğunu sil (approx line 55-150).
- `const TEAM_NAMES = { ... };` bloğunu sil (approx line 155-180).
- `global.FMT = FMT;` satırını da sil.

- [ ] **Step 3: Add fmt.js script tag to dashboard.html (before other scripts)**

Edit `src/presentation/dashboard/templates/dashboard.html`:
- `<script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>` ÖNCESİNE ekle:

```html
<script src="{{ url_for('static', filename='js/fmt.js') }}"></script>
```

Sıra: `fmt.js` → diğer scriptler → `dashboard.js`.

- [ ] **Step 4: Manual verify — dashboard start**

Run: `python -m src.presentation.dashboard.app &` then `curl -s http://127.0.0.1:5050/static/js/fmt.js | head -20`
Expected: FMT JavaScript served correctly.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/unit -q`
Expected: `637 passed` (JS moves don't affect Python tests).

- [ ] **Step 6: Commit**

```bash
git add src/presentation/dashboard/static/js/fmt.js \
        src/presentation/dashboard/static/js/dashboard.js \
        src/presentation/dashboard/templates/dashboard.html
git commit -m "$(cat <<'EOF'
refactor(dashboard): extract FMT + TEAM_NAMES into fmt.js module

dashboard.js ~150 satır kısaldı. FMT namespace + TEAM_NAMES map ayrı dosyada,
script sırası fmt.js → branches/feed → dashboard.js. Kontrat:
docs/dashboard-fmt-contract.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: JS Modül Bölme — `icons.js` Ayrıştırma (Faz 4.2)

**Files:**
- Create: `src/presentation/dashboard/static/js/icons.js`
- Modify: `src/presentation/dashboard/static/js/dashboard.js` — ICONS sil
- Modify: `src/presentation/dashboard/templates/dashboard.html` — script tag

- [ ] **Step 1: Find current ICONS block in dashboard.js**

Run: `grep -n "ICONS\|getSportEmoji" src/presentation/dashboard/static/js/dashboard.js | head -5`

- [ ] **Step 2: Copy ICONS to new file**

Create `src/presentation/dashboard/static/js/icons.js`:

```javascript
/* ICONS — sport_tag/slug → emoji veya <img> HTML (dashboard feed cards).
 *
 * Tüm fonksiyonlar pure. Çıktı HTML string — innerHTML'e yazılır.
 */
(function (global) {
  "use strict";

  const ICONS = {
    // ... (exact content from dashboard.js ICONS block — copy verbatim)
  };

  global.ICONS = ICONS;
})(window);
```

**Not:** Step'in kod içeriği `dashboard.js`'teki mevcut ICONS objesiyle AYNI — 1:1 kopyala.

- [ ] **Step 3: Remove ICONS from dashboard.js**

Edit `src/presentation/dashboard/static/js/dashboard.js`: ICONS bloğunu + `global.ICONS = ICONS;` satırını sil.

- [ ] **Step 4: Add icons.js script tag**

Edit `templates/dashboard.html` — `fmt.js`'ten sonra, `branches.js`/`feed.js`'den önce:

```html
<script src="{{ url_for('static', filename='js/icons.js') }}"></script>
```

- [ ] **Step 5: Run tests + manual dashboard check**

Run: `python -m pytest tests/unit -q`
Expected: `637 passed`.

Run dashboard + load page — feed kartlarında emoji/ikon görünmeli.

- [ ] **Step 6: Commit**

```bash
git add src/presentation/dashboard/static/js/icons.js \
        src/presentation/dashboard/static/js/dashboard.js \
        src/presentation/dashboard/templates/dashboard.html
git commit -m "$(cat <<'EOF'
refactor(dashboard): extract ICONS into icons.js module

dashboard.js ~35 satır daha kısaldı. Script sırası: fmt → icons → branches/feed
→ dashboard. Her modül tek global.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Verify File Sizes + ARCH_GUARD

- [ ] **Step 1: Count dashboard.js lines**

Run: `wc -l src/presentation/dashboard/static/js/*.js`
Expected: `dashboard.js < 350`, `fmt.js ≈ 150`, `icons.js ≈ 50`, others unchanged.

- [ ] **Step 2: Grep hardcoded hex in CSS/JS (should be zero in color names)**

Run: `grep -rn "#[0-9a-fA-F]\{6\}" src/presentation/dashboard/static/ | grep -v "dashboard.css" | grep -iv "panel\|bg\|text\|muted\|border"`
Expected: 0 matches (only palette `:root` in dashboard.css, neutrals allowed).

- [ ] **Step 3: Confirm full test suite**

Run: `python -m pytest tests/unit -q`
Expected: `637 passed`.

- [ ] **Step 4: No commit — this is a verification gate**

---

## Task 10: Full Restart + Monitor (Faz 6)

**Files:** Runtime only, no code changes.

- [ ] **Step 1: Kill existing bot + dashboard**

Run:
```bash
for p in $(netstat -ano | grep ":5050" | awk '{print $5}' | sort -u); do taskkill //F //PID $p 2>/dev/null; done
if [ -f logs/agent.pid ]; then taskkill //F //PID $(cat logs/agent.pid) 2>/dev/null; fi
```

- [ ] **Step 2: Wipe logs**

Run: `rm -f logs/*.jsonl logs/*.json logs/*.pid logs/*.bak-* logs/bot.log`

- [ ] **Step 3: Start bot**

Run: `python -m src.main &`
Expected: Agent starts; `logs/agent.pid` appears.

- [ ] **Step 4: Start dashboard**

Run: `python -m src.presentation.dashboard.app &`
Expected: Dashboard on `127.0.0.1:5050`.

- [ ] **Step 5: Wait 90s for first heavy cycle**

- [ ] **Step 6: Report**

Report format:
- Bot alive, mode, PID
- Heavy cycle çıktısı: markets scanned, fresh batch, skip dağılımı
- Açık pozisyon sayısı, exposure pct
- Dashboard erişilebilir mi, JS konsol error var mı (not: manuel test)

---

## Self-Review Sonucu

**Spec coverage:**
- Faz 1 (Audit) → Task 1 ✓
- Faz 2.1 (Exposure TDD) → Task 2 ✓
- Faz 2.2 (Dashboard §5.7) → Task 3 ✓
- Faz 2.3 (PRD) → Task 4 ✓
- Faz 3.1 (sport_category test) → Task 5 ✓
- Faz 3.2 (FMT contract) → Task 6 ✓
- Faz 4.1 (fmt.js) → Task 7 ✓
- Faz 4.2 (icons.js) → Task 8 ✓
- Faz 6 (Restart) → Task 10 ✓
- Task 9 ek: file size + ARCH_GUARD verification gate

**Placeholder scan:** ✓ Hiçbir TBD/TODO yok. Her kod bloğu tam.

**Type consistency:** `total_portfolio_value` hem test hem implementation'da tutarlı; `FMT.teamsText`/`FMT.sideCode`/`FMT._fromSlug`/`FMT._expandCode` her yerde aynı isim.

**Faz 5 (Bug 2):** Bu plandan çıkarıldı — kullanıcı onayıyla ayrı spec açılacak.
