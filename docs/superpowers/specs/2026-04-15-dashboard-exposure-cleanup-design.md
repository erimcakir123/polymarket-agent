# Dashboard + Exposure Consolidation — Design Spec

**Tarih:** 2026-04-15
**Kapsam:** Son oturumdaki değişiklikleri clean state'e çek — kod + test + TDD + PRD senkron, ARCH_GUARD'a uygun, modüler, dead code yok.

---

## Amaç

Son ~4 saatlik iteratif değişiklikler (palette refactor, treemap branş, exposure bug fix, NO odds, match-start sort, etc.) hâlâ dokümanlara yansımadı, JS bundle şişti, test eksikleri var. Bu spec o borcu kapatır ve bir sonraki işe (yakın-maç bug'ı) temiz bir zeminden başlanmasını sağlar.

**Kapsam dışı:** Bug 2 (yakın maçları bulamıyor). Ayrı spec.

---

## Faz 1 — AUDIT: Neyi Tutuyoruz

Bu değişiklikler **doğru, test yeşil, kalacak**:

1. `src/domain/portfolio/exposure.py` — param rename `bankroll → total_portfolio_value` + docstring
2. `src/strategy/entry/gate.py` + `src/orchestration/agent.py` — caller fix (pass `bankroll + total_invested()`)
3. `src/presentation/dashboard/computed.py` — `_LEAGUE_TO_SPORT` + `_sport_category()` helper; treemap league→branş grouping
4. `src/presentation/dashboard/static/css/*` — palette `:root` tek kaynak, tüm renkli hex `var(--*)` kullanıyor, hover kuralları CSS-driven
5. `src/presentation/dashboard/static/js/dashboard.js` — FMT.teamsText, FMT.sideCode, _fromSlug, _fromQuestion, _expandCode, TEAM_NAMES, direction-adjusted odds, match-start ASC sort
6. `src/presentation/dashboard/static/js/branches.js` — `.tree-red/blue/green` class-driven hover, tooltip edge-aware
7. `src/presentation/dashboard/static/js/feed.js` — `_marketTitle()` tek helper, tüm tab'ler aynı format, team-code badge
8. `src/infrastructure/persistence/trade_logger.py` + `skipped_trade_logger.py` — `question` alanı eklendi

**Silme yok.** Her değişiklik kasıtlı.

---

## Faz 2 — DOCS: TDD + PRD Güncelleme

### TDD.md eklemeleri

**§6.15 (Circuit Breaker) içine — alt-başlık "Exposure Cap":**
> Exposure cap = (toplam_yatırılan + aday_size) / **toplam_portföy_değeri** > max_exposure_pct.
> Toplam portföy = nakit (`portfolio.bankroll`) + açık pozisyonların `size_usdc` toplamı.
> Nakit payda olarak kullanılmaz (pozisyon açıldıkça küçülür → cap erken tetiklenir).
> **Pure function:** `domain/portfolio/exposure.py::exceeds_exposure_limit`.
> **Caller invariantı:** `total_portfolio_value = portfolio.bankroll + portfolio.total_invested()`.

**§5 (Dashboard & Observability) altına YENİ bölüm — "§5.7 Dashboard Display Rules":**

```
§5.7.1 Treemap Branş Gruplaması
- Gruplama anahtarı: sport_category (yeni) veya sport_tag'den türetilmiş branş.
- LEAGUE_TO_SPORT map'i `presentation/dashboard/computed.py::_LEAGUE_TO_SPORT`:
  mlb→baseball, nhl/ahl/khl→hockey, nba/wnba→basketball, nfl/cfl→football,
  epl/ucl/mls/seriea→soccer, wta/atp→tennis, pga/lpga/rbc→golf.
- Eski kayıt (sport_tag="mlb" direkt) → map ile branşa çevrilir.

§5.7.2 Direction-Adjusted Odds Display
- Saklama kuralı (ARCH Kural 7): anchor_probability = P(YES), entry_price/current_price = token-native.
- Display kuralı:
  - Active card "Odds X%" BUY_YES → anchor_probability; BUY_NO → 1−anchor_probability.
  - Entry/Now fiyatları zaten token-native (BUY_NO → NO token fiyatı). Ek çevrim YOK.
- Badge metni: BUY_YES → slug yes-code uppercase; BUY_NO → slug no-code uppercase.
  Slug team-pattern eşleşmezse fallback "YES"/"NO".

§5.7.3 Feed Sort
- Her tab (Active/Exited/Skipped/Stock): match_start_iso ASC. Boşlar sona.

§5.7.4 CSS Palette — Tek Kaynak
- Renkli hex literal SADECE `static/css/dashboard.css:root` içinde. Başka yerde YASAK.
- Değişken isimleri: --green/--red/--blue/--orange + -dim/-dark/-hover/-strong türevleri.
- `:root` değişmeden palette'in tamamı tek yerden değişir.
- JS tarafı palette'i runtime'da `getComputedStyle(document.documentElement)` ile okur
  (chart renkleri için). Literal hex JS'te de yok.
```

### PRD.md — §3.3 altına tek cümle ekleme

> Exposure cap enforcement: hem gate-time (entry öncesi) hem execution-time (order öncesi) kontrol edilir, payda toplam portföy değeridir — nakit değil (bkz. TDD §6.15).

---

## Faz 3 — TESTS: Eksik Coverage

### 3.1 `tests/unit/presentation/test_computed_sport_category.py` (yeni)

Test case'leri:
- `test_sport_category_from_split_tag`: "baseball_mlb" → "baseball"
- `test_sport_category_from_league_map`: sport_tag="nhl" → "hockey"
- `test_sport_category_unknown_fallback`: sport_tag="xyz" → "xyz"
- `test_sport_category_empty`: hiç field yok → "unknown"
- `test_treemap_merges_league_and_sport`: nhl record + hockey record → tek "hockey" grubu

### 3.2 FMT helpers — contract doc (JS test zor, YAGNI)

`docs/dashboard-fmt-contract.md` — her helper'ın girdi/çıktı kontratı + örnek case'ler. Breaking change yapılırsa update edilir.

### 3.3 Exposure regression testi ✅ zaten eklendi

---

## Faz 4 — MODÜLLER: dashboard.js Bölünmesi

### Mevcut yapı

`src/presentation/dashboard/static/js/dashboard.js` (520 satır):
- CONFIG (~10 satır)
- API (~15 satır)
- FMT (~80 satır) + helpers
- TEAM_NAMES (~22 satır)
- ICONS (~35 satır)
- CHARTS (~100 satır)
- RENDER (~180 satır)
- Bootstrap (~30 satır)

### Hedef yapı

```
static/js/
├─ fmt.js           # FMT namespace + TEAM_NAMES
├─ icons.js         # ICONS namespace
├─ branches.js      # (mevcut)
├─ feed.js          # (mevcut)
└─ dashboard.js     # CONFIG + API + CHARTS + RENDER + bootstrap (~300 satır)
```

### Bağımlılık sırası (script tag order)

1. `fmt.js` — bağımsız
2. `icons.js` — bağımsız
3. `branches.js` — FMT kullanır
4. `feed.js` — FMT + ICONS kullanır
5. `dashboard.js` — hepsini orchestrate eder

`templates/dashboard.html` script tag'leri güncellenecek.

### Global namespace convention

Her modül tek global yazar: `window.FMT`, `window.ICONS`. Mevcut desene (`global.BRANCHES`, `global.FEED`) uyar.

---

## Faz 5 — BUG 2 Brainstorm (Ayrı Spec)

Bu faz **bu spec kapsamında değil**. Onaylandıktan sonra:
- `docs/superpowers/specs/2026-04-15-near-term-matches-design.md` ayrı spec
- Root cause analizi: scanner priority, bookmaker availability, team matching
- Faz 6'dan sonra başlar

---

## Faz 6 — RESTART + VALIDATION

1. Bot + dashboard stop (her iki port temiz)
2. `logs/*` tümüyle sil
3. Agent + dashboard start (dry_run)
4. 1 heavy cycle bekle (≤90 sn)
5. Rapor (yukarıdaki son rapor formatı)

---

## Commit Stratejisi

Her faz sonunda 1 commit:

| # | Commit | İçerik |
|---|---|---|
| 1 | `fix(risk): exposure cap formula uses total portfolio value` | Faz 1 mevcut — yeniden commit |
| 2 | `docs: update TDD + PRD for exposure, dashboard display, palette` | Faz 2 |
| 3 | `test(presentation): add computed sport_category coverage` | Faz 3 |
| 4 | `refactor(dashboard): split fmt + icons out of dashboard.js` | Faz 4 |

Faz 5 ayrı branch/spec. Faz 6 commit değil, runtime doğrulama.

---

## ARCH_GUARD Uyumluluk Checklist

- ✓ DRY: palette tek `:root`, helpers FMT'de tek yerde, LEAGUE_TO_SPORT tek mapping
- ✓ <400 satır: dashboard.js 520 → <320 (Faz 4 sonrası)
- ✓ Domain I/O yok: exposure.py pure function, computed.py stdlib only
- ✓ Katman düzeni: presentation→orchestration→strategy→domain→infra (değişiklik yok)
- ✓ Magic number yok: threshold'lar config, palette `:root`, map named
- ✓ utils/helpers/misc yok: fmt.js ve icons.js anlamlı isim (namespace)
- ✓ Sessiz hata yok: exposure.py explicit `<= 0` guard
- ✓ P(YES) anchor: ARCH Kural 7 korundu, display layer'da çevrim

---

## Başarı Kriteri

- Tüm 627+ test yeşil
- Hardcoded renkli hex 0 (palette dışında)
- dashboard.js < 350 satır
- TDD.md + PRD.md güncel + kod referansları hiçbir yerde stale değil
- `grep -r "bankroll=.*exceeds_exposure"` → 0 match (rename tam)
- 1 heavy cycle sonrası: entry sayısı > 7 (exposure fix etkisi), skip dağılımında `exposure_cap_reached` minimum
