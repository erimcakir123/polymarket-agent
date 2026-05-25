# MLB Submarket Entry Yolu Sağlamlaştırması — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MLB submarket trade'lerini ana botun Normal entry'sinden çekip MLB submarket engine'ine yönlendirmek (slug parser fix) + bimodal market'lerdeki riskli/anlamsız girişleri kapıda kesmek (min fiyat + LIVE yasağı).

**Architecture:** İki nokta düzenleme. (1) `mlb_submarket_engine.py` regex'lerini gerçek Polymarket slug formatına (`spread-(home|away)-{N}pt5`) çekmek — değişken `Npt5` desteği dahil. (2) `gate.py`'da bimodal market'ler için iki yeni reject branch'ı: `entry_price < 0.20` ve `match_live=True`. Skip reason'lar dashboard yardım metnine yansır. Domain dokunulmaz.

**Tech Stack:** Python 3.12, pytest, pydantic v2 (config). Frontend: vanilla JS (skip_reason_help.js).

---

## File Structure

**Modify:**
- `src/strategy/entry/mlb_submarket_engine.py:40-48,294-300` — `_SLUG_RUN_LINE_RE` regex + `_parse_slug_static` line yorumu
- `src/strategy/entry/gate.py:58-80` — `GateConfig` dataclass'a `bimodal_min_entry_price` alanı; `131-213` `_evaluate_one`'da iki yeni kontrol
- `src/config/settings.py:63-79` — `RiskConfig`'e `bimodal_min_entry_price` alanı (pydantic)
- `config.yaml` (risk bloğu) — `bimodal_min_entry_price: 0.20`
- `src/orchestration/factory.py:201-220` — `GateConfig(...)` çağrısına yeni alan
- `src/presentation/dashboard/static/js/skip_reason_help.js` — `GENERAL` bloğuna iki yeni anahtar
- `tests/unit/strategy/entry/test_mlb_engine_parse_slug.py` — eski `pos|neg` testlerini home/away'e güncelle, yeni line varyasyonları için test ekle
- `tests/unit/strategy/entry/test_gate.py` — bimodal floor + bimodal live test'leri
- `DECISIONS.md` — §6.X yeni alt başlık + §B kronolojik log

**Create:** (yok — mevcut dosyalara eklenir)

---

## Task 1: MLB Submarket Slug Parser — Eski Format Testlerini Güncelle

**Bağlam:** `test_mlb_engine_parse_slug.py` şu an eski `spread-pos1pt5` / `spread-neg1pt5` formatını test ediyor. Gerçek slug'lar `spread-(home|away)-{N}pt5`. Önce testleri **yeni davranışı bekleyecek** şekilde güncelliyoruz (RED).

**Files:**
- Modify: `tests/unit/strategy/entry/test_mlb_engine_parse_slug.py`

- [ ] **Step 1: Eski iki testi yeni davranışa göre değiştir + yeni varyasyon testleri ekle**

`tests/unit/strategy/entry/test_mlb_engine_parse_slug.py` içeriğini **tamamen** şu hâle getir:

```python
"""Unit tests for MlbSubmarketEngine._parse_slug_static.

SPEC-X (2026-05-24): slug parser gerçek Polymarket formatına çekildi.
Eski `spread-(pos|neg)1pt5` formatı artık desteklenmez.
Yeni format: `spread-(home|away)-{N}pt5` — değişken N.
"""
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def test_parse_totals_slug_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-total-8pt5"
    )
    assert result == ("2026-05-22", "totals", 8.5, "cle", "phi")


def test_parse_totals_slug_variable_line_10pt5():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-23-total-10pt5"
    )
    assert result == ("2026-05-23", "totals", 10.5, "cle", "phi")


def test_parse_run_line_home_1pt5_returns_negative_home_line():
    # spread-home-1pt5 = home team -1.5 covers (yes_token)
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-23-spread-home-1pt5"
    )
    assert result == ("2026-05-23", "run_line", -1.5, "cle", "phi")


def test_parse_run_line_away_1pt5_returns_positive_home_line():
    # spread-away-1pt5 = away team -1.5 covers → home team gets +1.5
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-lad-mil-2026-05-23-spread-away-1pt5"
    )
    assert result == ("2026-05-23", "run_line", 1.5, "lad", "mil")


def test_parse_run_line_home_3pt5_returns_negative_3pt5():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-wsh-atl-2026-05-23-spread-home-3pt5"
    )
    assert result == ("2026-05-23", "run_line", -3.5, "wsh", "atl")


def test_parse_run_line_home_2pt5_variable_line_supported():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cws-sf-2026-05-23-spread-home-2pt5"
    )
    assert result == ("2026-05-23", "run_line", -2.5, "cws", "sf")


def test_parse_run_line_old_pos_format_returns_none():
    # SPEC-X: eski format artık desteklenmez — backward-incompatible (kasıtlı)
    assert MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-spread-pos1pt5"
    ) is None


def test_parse_run_line_old_neg_format_returns_none():
    assert MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-spread-neg1pt5"
    ) is None


def test_parse_unknown_returns_none():
    assert MlbSubmarketEngine._parse_slug_static("nba-okc-sas-2026-05-22") is None


def test_parse_moneyline_slug_returns_teams():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22"
    )
    assert result == ("2026-05-22", "moneyline", 0.0, "cle", "phi")


def test_parse_moneyline_with_unknown_suffix_rejected():
    result = MlbSubmarketEngine._parse_slug_static(
        "mlb-cle-phi-2026-05-22-foo"
    )
    assert result is None
```

- [ ] **Step 2: Testleri çalıştır, kırmızıyı doğrula**

```bash
pytest tests/unit/strategy/entry/test_mlb_engine_parse_slug.py -v
```

Expected: `test_parse_run_line_home_*` ve `test_parse_run_line_away_*` testleri **FAIL** (regex hâlâ eski). `test_parse_run_line_old_pos_format` ve `test_parse_run_line_old_neg_format` **FAIL** (eski regex hâlâ kabul ediyor).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/strategy/entry/test_mlb_engine_parse_slug.py
git commit -m "test(mlb-submarket): SPEC-X — slug parser yeni format testleri (RED)"
```

---

## Task 2: MLB Submarket Slug Parser — Regex'i Düzelt

**Files:**
- Modify: `src/strategy/entry/mlb_submarket_engine.py:40-48` (regex sabiti) ve `294-300` (parse case yorumu)

- [ ] **Step 1: `_SLUG_RUN_LINE_RE` regex'ini değiştir**

`src/strategy/entry/mlb_submarket_engine.py` satır 40-48 — şu blok:

```python
_SLUG_TOTALS_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})-total-(\d+)pt5$"
)
_SLUG_RUN_LINE_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})-spread-(pos|neg)1pt5$"
)
_SLUG_MONEYLINE_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})$"
)
```

Şu hâle getir:

```python
_SLUG_TOTALS_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})-total-(\d+)pt5$"
)
# SPEC-X (2026-05-24): gerçek Polymarket spread slug formatı.
# Eski "spread-(pos|neg)1pt5" formatı 2026-05 öncesi bir varsayımdı; üretimde
# karşılaşılan slug'lar "spread-(home|away)-{N}pt5" — değişken N (1, 2, 3...).
_SLUG_RUN_LINE_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})-spread-(home|away)-(\d+)pt5$"
)
_SLUG_MONEYLINE_RE = re.compile(
    r"^mlb-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})$"
)
```

- [ ] **Step 2: `_parse_slug_static` içindeki run_line case'ini güncelle**

`src/strategy/entry/mlb_submarket_engine.py:294-300` — şu blok:

```python
        m_r = _SLUG_RUN_LINE_RE.match(slug)
        if m_r:
            away, home, date, sign = m_r.groups()
            line = -1.5 if sign == "neg" else 1.5
            return date, "run_line", line, away, home
```

Şu hâle getir:

```python
        m_r = _SLUG_RUN_LINE_RE.match(slug)
        if m_r:
            away, home, date, side, n_str = m_r.groups()
            # SPEC-X: "spread-home-Npt5" = home team -N.5 covers (yes_token);
            # "spread-away-Npt5" = away team -N.5 covers → home team gets +N.5.
            # spread_pricer perspective: home_line = home team's handicap.
            magnitude = float(n_str) + 0.5
            line = -magnitude if side == "home" else +magnitude
            return date, "run_line", line, away, home
```

- [ ] **Step 3: Testleri çalıştır, yeşili doğrula**

```bash
pytest tests/unit/strategy/entry/test_mlb_engine_parse_slug.py -v
```

Expected: Tüm 11 test **PASS**.

- [ ] **Step 4: Regression — diğer MLB engine testleri hâlâ geçiyor mu?**

```bash
pytest tests/unit/strategy/entry/ -v
```

Expected: Tüm dosyalardaki testler PASS. Eğer `test_mlb_submarket_engine.py` veya başka bir dosya eski slug'a (örn. `spread-pos1pt5`) refer ediyorsa o testleri de yeni formata güncelle (Task adımı içinde aynı commit'e dahil et).

- [ ] **Step 5: Commit**

```bash
git add src/strategy/entry/mlb_submarket_engine.py
git commit -m "fix(mlb-submarket): SPEC-X — slug parser gerçek Polymarket formatına çekildi"
```

---

## Task 3: GateConfig'e `bimodal_min_entry_price` Alanı + Pydantic Config

**Files:**
- Modify: `src/strategy/entry/gate.py:58-80` (dataclass)
- Modify: `src/config/settings.py:63-79` (`RiskConfig`)
- Modify: `config.yaml` (risk bloğu)
- Modify: `src/orchestration/factory.py:201-220` (`GateConfig(...)` çağrısı)

- [ ] **Step 1: `GateConfig` dataclass'a yeni alan ekle**

`src/strategy/entry/gate.py:58-80` — `GateConfig` dataclass içindeki `max_entry_price: float = 0.88` satırının hemen altına:

```python
    max_entry_price: float = 0.88
    # SPEC-X (2026-05-24): bimodal market'lerde (totals + spreads) entry alt sınır.
    # Bu fiyatın altındaki entry'ler "piyasa kararını vermiş" sayılır — ultra-low guard
    # zaten anında tetikleneceği için baştan reddedilir.
    bimodal_min_entry_price: float = 0.20
```

- [ ] **Step 2: `RiskConfig` pydantic modeline yeni alan ekle**

`src/config/settings.py:63-79` — `RiskConfig` içindeki `max_entry_price: float = 0.88` satırının hemen altına:

```python
    max_entry_price: float = 0.88
    # SPEC-X (2026-05-24): bimodal market'ler için entry alt sınır.
    bimodal_min_entry_price: float = 0.20
```

- [ ] **Step 3: `config.yaml`'a yeni alan ekle**

`config.yaml` içinde `risk:` bloğunda `max_entry_price: 0.88` satırının hemen altına:

```yaml
  max_entry_price: 0.88    # 88¢+ girişlerde R/R kötü (max payout 0.99-entry)
  # SPEC-X (2026-05-24): bimodal (totals + spreads) entry alt sınır — ultra-low fiyat
  # bu market'lerde "piyasa kararını vermiş" sayılır.
  bimodal_min_entry_price: 0.20
```

- [ ] **Step 4: `factory.py`'da `GateConfig(...)` çağrısına yeni alanı geçir**

`src/orchestration/factory.py:201-220` içindeki `GateConfig(...)` çağrısında, `max_entry_price=cfg.risk.max_entry_price,` satırının hemen altına:

```python
        max_entry_price=cfg.risk.max_entry_price,
        bimodal_min_entry_price=cfg.risk.bimodal_min_entry_price,
```

- [ ] **Step 5: Smoke test — config yüklenmesi sağlam mı?**

```bash
python -c "from src.config.settings import load_config; c = load_config('config.yaml'); print('bimodal_min:', c.risk.bimodal_min_entry_price)"
```

Expected output: `bimodal_min: 0.2`

- [ ] **Step 6: Commit**

```bash
git add src/strategy/entry/gate.py src/config/settings.py config.yaml src/orchestration/factory.py
git commit -m "feat(config): SPEC-X — bimodal_min_entry_price config alanı (0.20)"
```

---

## Task 4: Gate — Bimodal Min Entry Price (Faz 2A) — RED test

**Files:**
- Modify: `tests/unit/strategy/entry/test_gate.py`

- [ ] **Step 1: Mevcut `test_gate.py`'daki helper'ı oku**

`tests/unit/strategy/entry/test_gate.py` dosyasının ilk 80 satırını oku (test fixture'ları, gate instance oluşturma helper'ı için). Bu plan helper isimlerini bilmiyor — testlerini mevcut dosyanın **kendi pattern'ine uyacak şekilde** yaz.

Aşağıdaki test gövdesini mevcut dosyanın **sonuna** ekle. Eğer fixture/helper isimleri farklıysa, mevcut testlerden kopyala-uyarla.

```python
# ============================================================================
# SPEC-X (2026-05-24): Bimodal entry kapısı testleri
# ============================================================================

def test_gate_bimodal_market_entry_below_floor_skipped(
    gate, portfolio, make_market, make_bm_prob
):
    """Bimodal (totals/spreads) market'e 4¢'den entry → bimodal_entry_below_floor."""
    market = make_market(
        slug="mlb-wsh-atl-2026-05-23-spread-home-3pt5",
        yes_price=0.04,
        sport_tag="baseball",
        sports_market_type="spreads",
        match_live=False,
    )
    bm_prob = make_bm_prob(probability=0.59, confidence="A", num_bookmakers=29)
    result = gate._evaluate_one(market)
    # Strateji edge bulabilir; gate sonradan floor ile reddeder
    assert result.signal is None
    assert result.skipped_reason == "bimodal_entry_below_floor"
    assert "0.040" in result.skip_detail or "0.04" in result.skip_detail


def test_gate_bimodal_market_entry_at_floor_not_blocked_by_floor(
    gate, portfolio, make_market, make_bm_prob
):
    """Sınır: entry_price = 0.20 → floor blokuna takılmaz (strict less-than).
    
    NOT: Bu test sadece floor kuralının çalışmadığını gösterir — başka kurallar
    (örn. no_edge) signal'i reddedebilir. Burada doğruladığımız tek şey: skipped_reason
    'bimodal_entry_below_floor' DEĞİL.
    """
    market = make_market(
        slug="mlb-cle-phi-2026-05-23-spread-home-1pt5",
        yes_price=0.20,
        sport_tag="baseball",
        sports_market_type="spreads",
        match_live=False,
    )
    bm_prob = make_bm_prob(probability=0.30, confidence="A", num_bookmakers=29)
    result = gate._evaluate_one(market)
    assert result.skipped_reason != "bimodal_entry_below_floor"


def test_gate_moneyline_market_low_entry_not_blocked_by_bimodal_floor(
    gate, portfolio, make_market, make_bm_prob
):
    """Moneyline 4¢ entry → bimodal floor TETİKLENMEZ (sadece bimodal market'ler için)."""
    market = make_market(
        slug="mlb-cle-phi-2026-05-23",  # moneyline (suffix yok)
        yes_price=0.04,
        sport_tag="baseball",
        sports_market_type="moneyline",
        match_live=False,
    )
    bm_prob = make_bm_prob(probability=0.59, confidence="A", num_bookmakers=29)
    result = gate._evaluate_one(market)
    assert result.skipped_reason != "bimodal_entry_below_floor"
```

- [ ] **Step 2: Testleri çalıştır, kırmızıyı doğrula**

```bash
pytest tests/unit/strategy/entry/test_gate.py -v -k bimodal
```

Expected: 3 yeni test, hepsi başlangıçta **FAIL** (`bimodal_entry_below_floor` skip reason hâlâ kodda yok).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/strategy/entry/test_gate.py
git commit -m "test(gate): SPEC-X — bimodal min entry floor testleri (RED)"
```

---

## Task 5: Gate — Bimodal Min Entry Price (Faz 2A) — Implementation

**Files:**
- Modify: `src/strategy/entry/gate.py:131-213` (`_evaluate_one`)

- [ ] **Step 1: `_evaluate_one` içinde, mevcut `max_entry_price` kontrolünün hemen ALTINA yeni kontrol ekle**

`src/strategy/entry/gate.py` `_evaluate_one` metodu içinde, şu blok:

```python
        # 6. Entry price cap — 88¢+ girişlerde R/R kötü (max payout 0.99-entry)
        entry_price = effective_price(signal.market_price, signal.direction)
        if entry_price >= self.config.max_entry_price:
            detail = f"price={entry_price:.3f}, cap={self.config.max_entry_price}"
            return GateResult(cid, None, "entry_price_cap", skip_detail=detail, manipulation=manip)
```

şu hâle getir (mevcut blok değişmez, **altına** yeni blok eklenir):

```python
        # 6. Entry price cap — 88¢+ girişlerde R/R kötü (max payout 0.99-entry)
        entry_price = effective_price(signal.market_price, signal.direction)
        if entry_price >= self.config.max_entry_price:
            detail = f"price={entry_price:.3f}, cap={self.config.max_entry_price}"
            return GateResult(cid, None, "entry_price_cap", skip_detail=detail, manipulation=manip)

        # 6b. Bimodal entry floor (SPEC-X 2026-05-24) — totals/spreads market'lerinde
        # 20¢ altı entry "piyasa kararını vermiş" sayılır; ultra-low guard zaten
        # anında tetikleneceği için baştan reddet.
        if _is_bimodal_market(market) and entry_price < self.config.bimodal_min_entry_price:
            detail = f"price={entry_price:.3f}, min={self.config.bimodal_min_entry_price}"
            return GateResult(cid, None, "bimodal_entry_below_floor", skip_detail=detail, manipulation=manip)
```

- [ ] **Step 2: Testleri çalıştır, yeşili doğrula**

```bash
pytest tests/unit/strategy/entry/test_gate.py -v -k bimodal
```

Expected: 3 test (Task 4'tekiler) **PASS**.

- [ ] **Step 3: Tüm gate testleri hâlâ geçiyor mu?**

```bash
pytest tests/unit/strategy/entry/test_gate.py -v
```

Expected: tüm testler PASS.

- [ ] **Step 4: Commit**

```bash
git add src/strategy/entry/gate.py
git commit -m "feat(gate): SPEC-X — bimodal market entry min floor (20¢)"
```

---

## Task 6: Gate — Bimodal LIVE Yasağı (Faz 2B) — RED test

**Files:**
- Modify: `tests/unit/strategy/entry/test_gate.py`

- [ ] **Step 1: Yeni testleri dosyanın sonuna ekle**

```python
def test_gate_bimodal_market_live_entry_blocked(
    gate, portfolio, make_market, make_bm_prob
):
    """Bimodal market LIVE → bimodal_entry_live."""
    market = make_market(
        slug="mlb-lad-mil-2026-05-23-spread-away-1pt5",
        yes_price=0.42,
        sport_tag="baseball",
        sports_market_type="spreads",
        match_live=True,
    )
    bm_prob = make_bm_prob(probability=0.52, confidence="A", num_bookmakers=54)
    result = gate._evaluate_one(market)
    assert result.signal is None
    assert result.skipped_reason == "bimodal_entry_live"


def test_gate_bimodal_market_not_live_entry_allowed_by_live_rule(
    gate, portfolio, make_market, make_bm_prob
):
    """Bimodal market pre-match → bimodal_entry_live TETİKLENMEZ."""
    market = make_market(
        slug="mlb-cle-phi-2026-05-23-spread-home-1pt5",
        yes_price=0.42,
        sport_tag="baseball",
        sports_market_type="spreads",
        match_live=False,
    )
    bm_prob = make_bm_prob(probability=0.52, confidence="A", num_bookmakers=54)
    result = gate._evaluate_one(market)
    assert result.skipped_reason != "bimodal_entry_live"


def test_gate_moneyline_market_live_entry_not_blocked_by_bimodal_live_rule(
    gate, portfolio, make_market, make_bm_prob
):
    """Moneyline LIVE entry → bimodal_entry_live TETİKLENMEZ (kural sadece bimodal)."""
    market = make_market(
        slug="wnba-por-tor-2026-05-23",
        yes_price=0.65,
        sport_tag="wnba",
        sports_market_type="moneyline",
        match_live=True,
    )
    bm_prob = make_bm_prob(probability=0.75, confidence="A", num_bookmakers=10)
    result = gate._evaluate_one(market)
    assert result.skipped_reason != "bimodal_entry_live"


def test_gate_bimodal_market_match_live_none_treated_as_not_live(
    gate, portfolio, make_market, make_bm_prob
):
    """Sınır: match_live alanı None/eksik → 'canlı değil' kabul, blok yok."""
    market = make_market(
        slug="mlb-cle-phi-2026-05-23-spread-home-1pt5",
        yes_price=0.42,
        sport_tag="baseball",
        sports_market_type="spreads",
        match_live=None,
    )
    bm_prob = make_bm_prob(probability=0.52, confidence="A", num_bookmakers=54)
    result = gate._evaluate_one(market)
    assert result.skipped_reason != "bimodal_entry_live"
```

- [ ] **Step 2: Testleri çalıştır, kırmızıyı doğrula**

```bash
pytest tests/unit/strategy/entry/test_gate.py -v -k live
```

Expected: yeni testler **FAIL** (`bimodal_entry_live` skip reason hâlâ kodda yok).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/strategy/entry/test_gate.py
git commit -m "test(gate): SPEC-X — bimodal LIVE entry yasağı testleri (RED)"
```

---

## Task 7: Gate — Bimodal LIVE Yasağı (Faz 2B) — Implementation

**Files:**
- Modify: `src/strategy/entry/gate.py` (_evaluate_one, Faz 2A kontrolünün hemen altına)

- [ ] **Step 1: Faz 2A kontrolünün hemen ALTINA yeni kontrol ekle**

`src/strategy/entry/gate.py` `_evaluate_one` içinde, Task 5'te eklediğin "6b. Bimodal entry floor" bloğunun hemen **altına**:

```python
        # 6c. Bimodal LIVE yasağı (SPEC-X 2026-05-24) — bimodal market'lerde
        # AI/model olasılığı pre-match hesaplanır; LIVE'da market durumu değişmiş
        # olur → tahmin bayatlamış → asimetrik risk. match_live None/eksik = canlı değil.
        if _is_bimodal_market(market) and bool(getattr(market, "match_live", False)):
            return GateResult(
                cid, None, "bimodal_entry_live",
                skip_detail="market is live",
                manipulation=manip,
            )
```

- [ ] **Step 2: Testleri çalıştır, yeşili doğrula**

```bash
pytest tests/unit/strategy/entry/test_gate.py -v -k live
```

Expected: 4 test (Task 6'dakiler) **PASS**.

- [ ] **Step 3: Tüm gate testleri geçiyor mu?**

```bash
pytest tests/unit/strategy/entry/ -v
```

Expected: tüm testler PASS.

- [ ] **Step 4: Commit**

```bash
git add src/strategy/entry/gate.py
git commit -m "feat(gate): SPEC-X — bimodal market'lere LIVE entry yasağı"
```

---

## Task 8: Dashboard — skip_reason_help.js'e Yeni Anahtarları Ekle

**Files:**
- Modify: `src/presentation/dashboard/static/js/skip_reason_help.js` (GENERAL bloğu)

- [ ] **Step 1: `GENERAL` objesinin sonuna iki yeni anahtar ekle**

`src/presentation/dashboard/static/js/skip_reason_help.js` içindeki `GENERAL` constant'ında, `"SAME_MARKET_TYPE_PER_EVENT":` satırından hemen sonra şu iki anahtarı ekle:

```javascript
    "SAME_MARKET_TYPE_PER_EVENT": "Bu maçta aynı tür markette (ML/totals/spread) zaten açık pozisyon var.",
    // SPEC-X (2026-05-24): bimodal entry kapısı
    "bimodal_entry_below_floor": "Spread/total market'inde fiyat 20¢ altında — piyasa kararını vermiş sayıldı, giriş atlandı.",
    "BIMODAL_ENTRY_BELOW_FLOOR": "Spread/total market'inde fiyat 20¢ altında — piyasa kararını vermiş sayıldı, giriş atlandı.",
    "bimodal_entry_live": "Maç başladıktan sonra spread/total market'e giriş yapılmıyor (model tahmini bayat olabilir).",
    "BIMODAL_ENTRY_LIVE": "Maç başladıktan sonra spread/total market'e giriş yapılmıyor (model tahmini bayat olabilir).",
```

(Hem lowercase hem UPPERCASE varyantları eklendi çünkü dosyada her iki konvansiyonu da görüyoruz — `event_already_held` / `EVENT_ALREADY_HELD`).

- [ ] **Step 2: Manuel doğrulama notu**

Dashboard frontend testi yok. Dashboard reload sonrası skip reason rozetine hover edince Türkçe metin görünmeli. Bu adım otomatik doğrulanmaz — kullanıcıya not.

- [ ] **Step 3: Commit**

```bash
git add src/presentation/dashboard/static/js/skip_reason_help.js
git commit -m "feat(dashboard): SPEC-X — skip_reason yardım metinleri (bimodal floor + live)"
```

---

## Task 9: DECISIONS.md — Kalıcı Karar Kaydı

**Files:**
- Modify: `DECISIONS.md` (§6 ve §B)

- [ ] **Step 1: DECISIONS.md'nin §6 sonuna yeni alt başlık ekle**

`DECISIONS.md` içinde §6.17 (Liquidity Check) sonrasını bul; eğer §6.18 yoksa onu ekle, varsa boş bir sonraki numara kullan:

```markdown
### 6.18 Bimodal Entry Floor + LIVE Yasağı

Bimodal market'lerde (totals + spreads — `_is_bimodal_market(sport, market_type)`) entry kapısında iki ek kontrol:

1. **Min entry floor:** `effective_entry < 0.20` → reject (`bimodal_entry_below_floor`)
   - Gerekçe: ultra-low guard (§6.12) zaten `effective_entry < 0.09 AND elapsed ≥ 0.75 AND current < 0.05`'de anında çıkış yapıyor. 20¢ altı entry'de bu üç şart yüksek ihtimalle başlangıçta sağlanıyor → mikro-trade üretiyor. Floor entry'de keser, runtime'da hiç slot açılmaz.
2. **LIVE yasağı:** `match_live == True` → reject (`bimodal_entry_live`)
   - Gerekçe: Bimodal market'lerde model olasılığı pre-match (MLB için Marcel/TTO/bullpen; diğer sporlar için bookmaker). LIVE'da skor/kalan-süre değişmiş → tahmin bayatlamış → asimetrik risk (küçük yukarı, büyük aşağı). Konkre vaka: 2026-05-23 WSH-ATL spread (entry 4¢, 9s sonra ultra_low_guard exit) + LAD-MIL/STL-CIN spread (entry 40-42¢, LIVE, yüksek risk profili).

Config: `risk.bimodal_min_entry_price: 0.20`. Mevcut MLB submarket engine içindeki `mlb_min_polymarket_price: 0.20` kuralı korunur (defense-in-depth).
```

- [ ] **Step 2: §B kronolojik log'a 2026-05-24 SPEC-X kaydı ekle**

`DECISIONS.md` §B'nin BAŞINA (en yeni üstte):

```markdown
### 2026-05-24 — SPEC-X: MLB Submarket Entry Yolu Sağlamlaştırması

**Problem:** 2026-05-23 üretim verisinde 3 problemli MLB spread trade'i tespit edildi:
- `mlb-wsh-atl-2026-05-23-spread-home-3pt5`: entry 4¢ → 9s sonra ultra_low_guard exit, $0 zarar (gereksiz mikro-trade)
- `mlb-lad-mil-2026-05-23-spread-away-1pt5`: entry 42¢, LIVE, asimetrik risk
- `mlb-stl-cin-2026-05-23-spread-away-1pt5`: entry 40¢, LIVE, benzer profil

**Root cause:** `mlb_submarket_engine.py`'daki `_SLUG_RUN_LINE_RE` regex'i eski varsayım (`spread-(pos|neg)1pt5`) ile yazılmış; gerçek Polymarket slug formatı `spread-(home|away)-{N}pt5` (değişken N). Eşleşme olmadığı için MLB submarket engine `None` döndürdü → trade ana botun Normal entry'sine düştü → bookmaker pre-match prob ile market price farkı edge sanıldı.

**Çözüm (3 faz):**
1. Slug parser regex'i gerçek formata çekildi (`spread-(home|away)-(\d+)pt5`); line yorumu: home → -N.5, away → +N.5.
2. Bimodal entry floor: `effective_entry < 0.20` → reject.
3. Bimodal LIVE yasağı: `match_live=True` → reject.

**Etki:** MLB spread/total trade'leri artık MLB submarket engine'den geçer (Marcel + TTO + spread_pricer). Bimodal market'lere baytalı tahmin + asimetrik risk profili olan girişler kapıda kesilir.

**Kapsam dışı:** Moneyline min/max price, diğer sporların submarket engine'leri (yok), bookmaker prob clamp.
```

- [ ] **Step 3: Commit**

```bash
git add DECISIONS.md
git commit -m "docs(DECISIONS): SPEC-X — MLB submarket entry yolu sağlamlaştırması"
```

---

## Task 10: SPEC.md Temizliği

**Files:**
- Modify: `SPEC.md`

- [ ] **Step 1: SPEC-X bölümünü SPEC.md'den sil**

`SPEC.md` içinde `## SPEC-X: MLB Submarket Entry Yolu Sağlamlaştırması` başlığından `---` ayraçına kadar olan tüm bölümü sil. (CLAUDE.md kuralı: spec entegre edildikten sonra SPEC.md'den silinir.)

- [ ] **Step 2: Commit**

```bash
git add SPEC.md
git commit -m "docs(SPEC): SPEC-X — implemented, removed (DECISIONS'a taşındı)"
```

---

## Task 11: Final Verification

- [ ] **Step 1: Tüm test suite'i çalıştır**

```bash
pytest -q
```

Expected: tüm testler PASS, yeni başarısızlık yok.

- [ ] **Step 2: Grep ile eski format kalmamış mı doğrula**

```bash
git grep -nE "spread-(pos|neg)1pt5" src/ tests/
```

Expected: çıktı boş (eski format referansı kalmamalı). `docs/superpowers/plans/` içindeki bu plan dosyası hariç — orada tarihsel referans OK.

- [ ] **Step 3: Yeni skip reason'lar gerçekten kodda var mı**

```bash
git grep -nE "bimodal_entry_below_floor|bimodal_entry_live" src/
```

Expected: hem `gate.py` hem `skip_reason_help.js` listelenir.

- [ ] **Step 4: Restart sonrası canlı doğrulama (manuel)**

Bot zaten çalışıyorsa, kullanıcıya restart önerisi:

> "Fix implemented. Botu yeniden başlatmak ister misin (reload)? Reboot yetkisi sende, ben sadece reload öneriyorum."

Kullanıcı onayıyla:
```bash
python scripts/reboot.py reload
```

- [ ] **Step 5: Final commit yoksa skip; varsa**

(Adım 1-4 yalnızca doğrulama — yeni commit gerekmez.)

---

## Self-Review (plan yazıldıktan sonra)

**Spec coverage (SPEC.md SPEC-X):**
- ✓ Faz 1 (slug parser) → Task 1-2
- ✓ Faz 2A (bimodal floor) → Task 3-5
- ✓ Faz 2B (bimodal LIVE) → Task 6-7
- ✓ Faz 3 (dashboard) → Task 8
- ✓ DECISIONS.md güncelleme → Task 9
- ✓ Test senaryoları → her task'in RED step'i + Task 11

**Placeholder scan:** Yok.

**Type consistency:** `_is_bimodal_market(market)` helper'ı zaten `gate.py`'da tanımlı (satır 43-55). `GateConfig.bimodal_min_entry_price` field'ı dataclass'a Task 3'te eklendi, Task 5'te kullanıldı. `getattr(market, "match_live", False)` Task 7'de None-safe.
